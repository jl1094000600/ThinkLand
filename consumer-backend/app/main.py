import asyncio
import json
from datetime import date

import httpx
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .ai_client import generate_product_plan
from .config import get_settings
from .codegen_registry import get_stack_labels, stack_registry_out
from .database import get_db
from .models import (
    CodeGenerationEvent,
    CodeGenerationFile,
    CodeGenerationJob,
    CodeGraphEdge,
    CodeGraphNode,
    CommunityItem,
    CommunityStar,
    Conversation,
    ConversationMessage,
    GenerationRecord,
    PointTransaction,
    User,
    UserAIConfig,
    UserGitHubConfig,
)
from .points import ensure_daily_points, estimate_tokens, points_for_tokens, points_out, spend_points
from .schemas import (
    AIConfigIn,
    AuthRequest,
    AuthResponse,
    ConfirmConversationRequest,
    ConfirmConversationResponse,
    CommunityItemOut,
    CommunityListResponse,
    CommunityPublishRequest,
    CommunityStarResponse,
    CodeGenerationJobCreate,
    CodeGenerationJobOut,
    GitHubConfigIn,
    GitHubConfigOut,
    GitHubPushRequest,
    GitHubPushResponse,
    GenerateRequest,
    GenerateResponse,
    MeResponse,
)
from .security import create_access_token, decrypt_api_key, encrypt_api_key, get_current_user, hash_password, verify_password

app = FastAPI(title="ThinkLand Consumer Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3100", "http://127.0.0.1:3100"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def ai_config_out(config: UserAIConfig | None) -> dict:
    if config is None:
        return {"configured": False, "provider_type": "custom", "base_url": None, "model": None}
    return {"configured": True, "provider_type": config.provider_type or "custom", "base_url": config.base_url or None, "model": config.model}


def user_out(user: User) -> dict:
    return {"id": user.id, "account": user.account, "role": user.role}


def auth_payload(db: Session, user: User) -> dict:
    points = ensure_daily_points(db, user.id)
    db.flush()
    return {
        "access_token": create_access_token(user),
        "user": user_out(user),
        "points": points_out(points),
        "ai_config": ai_config_out(user.ai_config),
    }


def messages_to_text(messages: list[dict]) -> str:
    return "\n".join(f"{item['role']}: {item['content']}" for item in messages)


def title_from_messages(messages: list[dict]) -> str:
    for item in messages:
        if item["role"] == "user":
            return item["content"].strip()[:80] or "New conversation"
    return "New conversation"


def get_or_create_conversation(db: Session, user_id: int, conversation_id: int | None, messages: list[dict]) -> Conversation:
    if conversation_id:
        conversation = db.scalar(select(Conversation).where(Conversation.id == conversation_id, Conversation.user_id == user_id))
        if conversation is None:
            raise HTTPException(status_code=404, detail="Conversation not found")
        return conversation
    conversation = Conversation(user_id=user_id, title=title_from_messages(messages), status="draft")
    db.add(conversation)
    db.flush()
    return conversation


def append_missing_messages(db: Session, conversation: Conversation, user_id: int, messages: list[dict]) -> None:
    existing_count = db.scalar(
        select(func.count()).select_from(ConversationMessage).where(ConversationMessage.conversation_id == conversation.id)
    ) or 0
    for sequence_index, item in enumerate(messages[existing_count:], start=existing_count):
        db.add(
            ConversationMessage(
                conversation_id=conversation.id,
                user_id=user_id,
                role=item["role"],
                content=item["content"],
                sequence_index=sequence_index,
            )
        )


def append_one_message(db: Session, conversation: Conversation, user_id: int, role: str, content: str) -> None:
    existing_count = db.scalar(
        select(func.count()).select_from(ConversationMessage).where(ConversationMessage.conversation_id == conversation.id)
    ) or 0
    db.add(
        ConversationMessage(
            conversation_id=conversation.id,
            user_id=user_id,
            role=role,
            content=content,
            sequence_index=existing_count,
        )
    )


def community_item_out(item: CommunityItem, owner: User, starred_by_me: bool) -> dict:
    return {
        "id": item.id,
        "item_type": item.item_type,
        "title": item.title,
        "summary": item.summary,
        "content": item.content_json or {},
        "project_url": item.project_url,
        "star_count": item.star_count,
        "starred_by_me": starred_by_me,
        "owner": {"id": owner.id, "account": owner.account},
        "created_at": item.created_at.isoformat() if item.created_at else "",
    }


def resolve_ai_runtime(config: UserAIConfig) -> dict:
    provider_type = config.provider_type or "custom"
    if provider_type == "platform":
        settings = get_settings()
        base_url = (settings.platform_ai_base_url or "").rstrip("/")
        api_key = settings.platform_ai_api_key or ""
        model = (config.model or settings.platform_ai_model or "").strip()
        if not base_url or not api_key or not model:
            raise HTTPException(status_code=500, detail="Platform AI model is not configured")
        return {"provider_type": "platform", "base_url": base_url, "api_key": api_key, "model": model, "charge_points": True}
    return {
        "provider_type": "custom",
        "base_url": config.base_url,
        "api_key": decrypt_api_key(config.encrypted_api_key),
        "model": config.model,
        "charge_points": False,
    }


def github_config_out(config: UserGitHubConfig | None) -> dict:
    if config is None:
        return {"configured": False, "default_repo": None, "default_branch": None}
    return {"configured": True, "default_repo": config.default_repo, "default_branch": config.default_branch}


def code_file_out(file: CodeGenerationFile) -> dict:
    return {
        "path": file.path,
        "language": file.language,
        "content": file.content,
        "explanation": file.explanation,
        "status": file.status,
    }


def code_node_out(node: CodeGraphNode) -> dict:
    return {
        "key": node.node_key,
        "type": node.node_type,
        "label": node.label,
        "description": node.description,
        "file_path": node.file_path,
        "position": node.position_json,
        "status": node.status,
    }


def code_edge_out(edge: CodeGraphEdge) -> dict:
    return {"source": edge.source_key, "target": edge.target_key, "type": edge.edge_type, "label": edge.label}


def code_job_out(db: Session, job: CodeGenerationJob) -> dict:
    files = db.scalars(select(CodeGenerationFile).where(CodeGenerationFile.job_id == job.id).order_by(CodeGenerationFile.path)).all()
    nodes = db.scalars(select(CodeGraphNode).where(CodeGraphNode.job_id == job.id).order_by(CodeGraphNode.id)).all()
    edges = db.scalars(select(CodeGraphEdge).where(CodeGraphEdge.job_id == job.id).order_by(CodeGraphEdge.id)).all()
    return {
        "id": job.id,
        "title": job.title,
        "target_description": job.target_description,
        "stack": job.stack_json,
        "status": job.status,
        "provider_type": job.provider_type,
        "estimated_tokens": job.estimated_tokens,
        "estimated_points": job.estimated_points,
        "actual_tokens": job.actual_tokens,
        "actual_points": job.actual_points,
        "github_repo": job.github_repo,
        "github_branch": job.github_branch,
        "github_url": job.github_url,
        "error_message": job.error_message,
        "files": [code_file_out(file) for file in files],
        "graph_nodes": [code_node_out(node) for node in nodes],
        "graph_edges": [code_edge_out(edge) for edge in edges],
    }


def add_code_event(db: Session, job_id: int, event_type: str, title: str, payload: dict | None = None) -> None:
    next_index = db.scalar(
        select(func.count()).select_from(CodeGenerationEvent).where(CodeGenerationEvent.job_id == job_id)
    ) or 0
    db.add(CodeGenerationEvent(job_id=job_id, event_type=event_type, title=title, payload_json=payload or {}, sequence_index=next_index))
    db.flush()


def selected_stack_labels(stack: dict) -> dict:
    return get_stack_labels(stack)


def build_code_artifacts(title: str, target: str, stack: dict) -> dict:
    labels = selected_stack_labels(stack)
    frontend_ext = "vue" if stack["frontend"] == "vue" else "jsx"
    backend_ext = "py" if stack["backend"] == "fastapi" else ("ts" if stack["backend"] == "nestjs" else "java")
    db_ext = "sql"
    files = [
        {
            "path": f"frontend/src/App.{frontend_ext}",
            "language": stack["frontend"],
            "explanation": "产品主界面，负责展示输入、生成结果和操作入口。",
            "content": frontend_template(stack["frontend"], title, target),
        },
        {
            "path": f"backend/src/main.{backend_ext}",
            "language": stack["backend"],
            "explanation": "后端入口，提供健康检查和核心业务 API。",
            "content": backend_template(stack["backend"], title),
        },
        {
            "path": f"database/schema.{db_ext}",
            "language": stack["database"],
            "explanation": "数据库表结构，保存用户、需求和生成记录。",
            "content": database_template(stack["database"]),
        },
        {
            "path": "README.md",
            "language": "markdown",
            "explanation": "项目说明，帮助用户理解如何启动和部署。",
            "content": readme_template(title, labels, target),
        },
    ]
    if stack["deploy"] == "docker":
        files.append(
            {
                "path": "docker-compose.yml",
                "language": "yaml",
                "explanation": "Docker 部署入口，编排前端、后端和数据库。",
                "content": docker_template(stack),
            }
        )
    else:
        files.append(
            {
                "path": "deploy/nginx.conf",
                "language": "nginx",
                "explanation": "Ubuntu/Nginx 部署配置，把前端静态文件和后端 API 连接起来。",
                "content": nginx_template(),
            }
        )

    nodes = [
        {"key": "ui", "type": "page", "label": f"{labels['frontend']} 页面", "description": "用户操作入口，展示产品核心流程。", "file_path": files[0]["path"], "position": {"x": 80, "y": 120}},
        {"key": "api", "type": "api", "label": "业务 API", "description": "连接页面和后端业务逻辑。", "file_path": files[1]["path"], "position": {"x": 330, "y": 120}},
        {"key": "service", "type": "service", "label": labels["backend"], "description": "处理业务规则、校验和数据读写。", "file_path": files[1]["path"], "position": {"x": 580, "y": 120}},
        {"key": "db", "type": "database", "label": labels["database"], "description": "保存用户、需求、生成内容和状态。", "file_path": files[2]["path"], "position": {"x": 830, "y": 120}},
        {"key": "deploy", "type": "deploy", "label": labels["deploy"], "description": "负责把生成项目运行到服务器或容器环境。", "file_path": files[-1]["path"], "position": {"x": 580, "y": 300}},
    ]
    edges = [
        {"source": "ui", "target": "api", "type": "调用", "label": "页面请求接口"},
        {"source": "api", "target": "service", "type": "路由", "label": "API 进入服务"},
        {"source": "service", "target": "db", "type": "读写", "label": "服务读写数据"},
        {"source": "deploy", "target": "ui", "type": "部署", "label": "托管前端"},
        {"source": "deploy", "target": "service", "type": "部署", "label": "运行后端"},
    ]
    return {"files": files, "nodes": nodes, "edges": edges}


def frontend_template(frontend: str, title: str, target: str) -> str:
    if frontend == "react":
        return f"""import React, {{ useState }} from 'react';

export default function App() {{
  const [idea, setIdea] = useState({target!r});

  return (
    <main className="app">
      <h1>{title}</h1>
      <textarea value={{idea}} onChange={{event => setIdea(event.target.value)}} />
      <button>生成方案</button>
    </main>
  );
}}
"""
    return f"""<template>
  <main class="app">
    <h1>{title}</h1>
    <textarea v-model="idea" />
    <button>生成方案</button>
  </main>
</template>

<script setup>
import {{ ref }} from 'vue'

const idea = ref({target!r})
</script>
"""


def backend_template(backend: str, title: str) -> str:
    if backend == "nestjs":
        return f"""import {{ Controller, Get, Module }} from '@nestjs/common';

@Controller()
class AppController {{
  @Get('/api/health')
  health() {{
    return {{ ok: true, app: '{title}' }};
  }}
}}

@Module({{ controllers: [AppController] }})
export class AppModule {{}}
"""
    if backend == "springboot":
        return f"""package com.thinkland.generated;

import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
public class AppController {{
  @GetMapping("/api/health")
  public String health() {{
    return "{title} ok";
  }}
}}
"""
    return f"""from fastapi import FastAPI

app = FastAPI(title={title!r})

@app.get("/api/health")
def health():
    return {{"ok": True, "app": {title!r}}}
"""


def database_template(database: str) -> str:
    serial = "BIGSERIAL" if database == "postgresql" else "BIGINT UNSIGNED NOT NULL AUTO_INCREMENT"
    pk = "PRIMARY KEY" if database == "postgresql" else "PRIMARY KEY"
    return f"""CREATE TABLE users (
  id {serial} {pk},
  account VARCHAR(191) NOT NULL UNIQUE,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE ideas (
  id {serial} {pk},
  user_id BIGINT NOT NULL,
  title VARCHAR(191) NOT NULL,
  content TEXT NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""


def readme_template(title: str, labels: dict, target: str) -> str:
    return f"""# {title}

## 技术栈

- 前端：{labels['frontend']}
- 后端：{labels['backend']}
- 数据库：{labels['database']}
- 部署：{labels['deploy']}

## 目标

{target}
"""


def docker_template(stack: dict) -> str:
    return """services:
  frontend:
    build: ./frontend
    ports:
      - "3100:80"
  backend:
    build: ./backend
    ports:
      - "8080:8080"
  database:
    image: mysql:8
    environment:
      MYSQL_DATABASE: thinkland_generated
"""


def nginx_template() -> str:
    return """server {
  listen 80;
  root /var/www/generated/frontend/dist;
  location / {
    try_files $uri $uri/ /index.html;
  }
  location /api/ {
    proxy_pass http://127.0.0.1:8080;
  }
}
"""


def spend_code_generation_points(db: Session, account, user_id: int, job: CodeGenerationJob, total_tokens: int) -> int:
    points = points_for_tokens(total_tokens)
    account.used_points += points
    job.actual_points = points
    db.add(
        PointTransaction(
            user_id=user_id,
            usage_date=account.usage_date,
            generation_id=None,
            delta_points=-points,
            token_count=total_tokens,
            reason="code_generation",
        )
    )
    return points


def save_code_artifacts(db: Session, job: CodeGenerationJob, artifacts: dict) -> None:
    for file in artifacts["files"]:
        db.add(
            CodeGenerationFile(
                job_id=job.id,
                path=file["path"],
                language=file["language"],
                content=file["content"],
                explanation=file["explanation"],
                status="generated",
            )
        )
        add_code_event(db, job.id, "file", f"生成文件 {file['path']}", {"path": file["path"], "language": file["language"]})
    for node in artifacts["nodes"]:
        db.add(
            CodeGraphNode(
                job_id=job.id,
                node_key=node["key"],
                node_type=node["type"],
                label=node["label"],
                description=node["description"],
                file_path=node["file_path"],
                position_json=node["position"],
                status="generated",
            )
        )
        add_code_event(db, job.id, "graph_node", f"点亮图谱节点 {node['label']}", {"node": node})
    for edge in artifacts["edges"]:
        db.add(
            CodeGraphEdge(
                job_id=job.id,
                source_key=edge["source"],
                target_key=edge["target"],
                edge_type=edge["type"],
                label=edge["label"],
            )
        )
    add_code_event(db, job.id, "checking", "完成基础结构检查", {"status": "passed"})


@app.get("/api/health")
def health() -> dict:
    return {"ok": True}


@app.post("/api/auth/register", response_model=AuthResponse)
def register(payload: AuthRequest, db: Session = Depends(get_db)) -> dict:
    account = payload.account.strip().lower()
    if db.scalar(select(User).where(User.account == account)) is not None:
        raise HTTPException(status_code=409, detail="Account already exists")
    user = User(account=account, password_hash=hash_password(payload.password), role="normal")
    db.add(user)
    try:
        db.flush()
        response = auth_payload(db, user)
        db.commit()
        return response
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Account already exists")


@app.post("/api/auth/login", response_model=AuthResponse)
def login(payload: AuthRequest, db: Session = Depends(get_db)) -> dict:
    account = payload.account.strip().lower()
    user = db.scalar(select(User).where(User.account == account))
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid account or password")
    response = auth_payload(db, user)
    db.commit()
    return response


@app.get("/api/me", response_model=MeResponse)
def me(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    points = ensure_daily_points(db, current_user.id)
    db.commit()
    db.refresh(points)
    return {"user": user_out(current_user), "points": points_out(points), "ai_config": ai_config_out(current_user.ai_config)}


@app.get("/api/me/github-config", response_model=GitHubConfigOut)
def get_github_config(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    config = db.scalar(select(UserGitHubConfig).where(UserGitHubConfig.user_id == current_user.id))
    return github_config_out(config)


@app.put("/api/me/github-token", response_model=GitHubConfigOut)
def save_github_token(payload: GitHubConfigIn, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    config = db.scalar(select(UserGitHubConfig).where(UserGitHubConfig.user_id == current_user.id))
    if config is None:
        config = UserGitHubConfig(user_id=current_user.id, encrypted_token="", default_branch=payload.default_branch)
        db.add(config)
    config.encrypted_token = encrypt_api_key(payload.token.strip())
    config.default_repo = payload.default_repo.strip() if payload.default_repo else None
    config.default_branch = payload.default_branch.strip()
    db.commit()
    db.refresh(config)
    return github_config_out(config)


@app.put("/api/me/ai-config", response_model=MeResponse)
def save_ai_config(payload: AIConfigIn, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    config = db.scalar(select(UserAIConfig).where(UserAIConfig.user_id == current_user.id))
    if config is None:
        config = UserAIConfig(user_id=current_user.id, provider_type=payload.provider_type, base_url="", model=payload.model, encrypted_api_key="")
        db.add(config)
    config.provider_type = payload.provider_type
    config.model = payload.model.strip()
    if payload.provider_type == "platform":
        config.base_url = ""
        config.encrypted_api_key = ""
    else:
        config.base_url = str(payload.base_url).rstrip("/")
        config.encrypted_api_key = encrypt_api_key((payload.api_key or "").strip())
    points = ensure_daily_points(db, current_user.id)
    db.commit()
    db.refresh(config)
    return {"user": user_out(current_user), "points": points_out(points), "ai_config": ai_config_out(config)}


@app.post("/api/generate", response_model=GenerateResponse)
async def generate(payload: GenerateRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    request_messages = [{"role": item.role, "content": item.content} for item in payload.messages]
    if not request_messages and payload.idea:
        request_messages = [{"role": "user", "content": payload.idea}]
    dialogue_text = messages_to_text(request_messages)
    if not dialogue_text.strip():
        raise HTTPException(status_code=422, detail="Please enter conversation content")

    conversation = get_or_create_conversation(db, current_user.id, payload.conversation_id, request_messages)
    append_missing_messages(db, conversation, current_user.id, request_messages)
    db.commit()
    db.refresh(conversation)

    account = ensure_daily_points(db, current_user.id)
    remaining = account.granted_points - account.used_points

    config = db.scalar(select(UserAIConfig).where(UserAIConfig.user_id == current_user.id))
    if config is None:
        raise HTTPException(status_code=400, detail="Please save AI settings first")
    ai_runtime = resolve_ai_runtime(config)

    estimated_prompt_tokens = estimate_tokens(dialogue_text)
    if ai_runtime["charge_points"]:
        if remaining <= 0:
            raise HTTPException(status_code=status.HTTP_402_PAYMENT_REQUIRED, detail="Today's points are used up")
        token_budget = remaining * 1000
        if estimated_prompt_tokens >= token_budget:
            raise HTTPException(status_code=status.HTTP_402_PAYMENT_REQUIRED, detail="Not enough points for this input")
        max_tokens = max(256, min(2048, token_budget - estimated_prompt_tokens))
    else:
        max_tokens = 2048

    try:
        ai_response = await generate_product_plan(
            base_url=ai_runtime["base_url"],
            api_key=ai_runtime["api_key"],
            model=ai_runtime["model"],
            messages=request_messages,
            max_tokens=max_tokens,
        )
    except Exception as exc:
        record = GenerationRecord(user_id=current_user.id, prompt=dialogue_text, model=ai_runtime["model"], status="failed", error_message=str(exc))
        db.add(record)
        db.commit()
        raise HTTPException(status_code=502, detail=str(exc))

    result = ai_response["result"]
    assistant_message = result.get("assistant_message") or "I have captured that. You can add more details if needed."
    append_one_message(db, conversation, current_user.id, "assistant", assistant_message)

    usage = ai_response["usage"]
    if usage["total_tokens"] <= 0:
        usage["total_tokens"] = estimated_prompt_tokens + usage["completion_tokens"]
    record = GenerationRecord(
        user_id=current_user.id,
        prompt=dialogue_text,
        result_json=result,
        model=ai_runtime["model"],
        prompt_tokens=usage["prompt_tokens"],
        completion_tokens=usage["completion_tokens"],
        total_tokens=usage["total_tokens"],
        status="success",
    )
    db.add(record)
    db.flush()
    if ai_runtime["charge_points"]:
        record.points_used = spend_points(db, account, current_user.id, record.id, usage["total_tokens"])
    else:
        record.points_used = 0
    db.commit()
    db.refresh(account)
    return {
        "conversation_id": conversation.id,
        "result": result,
        "usage": {**usage, "points_used": record.points_used, "provider_type": ai_runtime["provider_type"]},
        "points": points_out(account),
    }


@app.post("/api/conversations/confirm", response_model=ConfirmConversationResponse)
def confirm_conversation(
    payload: ConfirmConversationRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    messages = [{"role": item.role, "content": item.content} for item in payload.messages]
    conversation = get_or_create_conversation(db, current_user.id, payload.conversation_id, messages)
    append_missing_messages(db, conversation, current_user.id, messages)
    conversation.status = "confirmed"
    conversation.result_json = {
        "messages": messages,
        "prd": payload.prd,
        "flow": payload.flow,
        "tasks": payload.tasks,
    }

    record = GenerationRecord(
        user_id=current_user.id,
        prompt=messages_to_text(messages),
        result_json=conversation.result_json,
        model=None,
        prompt_tokens=0,
        completion_tokens=0,
        total_tokens=0,
        points_used=0,
        status="confirmed",
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return {"saved": True, "record_id": record.id}


@app.get("/api/code-generation/stack-registry")
def get_code_generation_stack_registry(current_user: User = Depends(get_current_user)) -> dict:
    return stack_registry_out()


@app.post("/api/code-generation/jobs", response_model=CodeGenerationJobOut)
def create_code_generation_job(
    payload: CodeGenerationJobCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    conversation = None
    if payload.conversation_id:
        conversation = db.scalar(select(Conversation).where(Conversation.id == payload.conversation_id, Conversation.user_id == current_user.id))
        if conversation is None:
            raise HTTPException(status_code=404, detail="Conversation not found")

    provider_type = current_user.ai_config.provider_type if current_user.ai_config else "custom"
    charge_points = provider_type == "platform"
    stack = payload.stack.model_dump()
    job = CodeGenerationJob(
        user_id=current_user.id,
        conversation_id=conversation.id if conversation else None,
        title=payload.title.strip(),
        target_description=payload.target_description.strip(),
        stack_json=stack,
        status="planning",
        provider_type=provider_type,
    )
    db.add(job)
    db.flush()

    add_code_event(db, job.id, "planning", "分析需求和技术栈", {"stack": stack})
    artifacts = build_code_artifacts(job.title, job.target_description, stack)
    estimated_text = job.title + job.target_description + json.dumps(stack, ensure_ascii=False)
    job.estimated_tokens = estimate_tokens(estimated_text) + 1600
    job.estimated_points = points_for_tokens(job.estimated_tokens) if charge_points else 0
    add_code_event(
        db,
        job.id,
        "points_estimate",
        "计算预计点数",
        {"estimated_tokens": job.estimated_tokens, "estimated_points": job.estimated_points, "provider_type": provider_type},
    )

    if charge_points:
        account = ensure_daily_points(db, current_user.id)
        if account.granted_points - account.used_points < job.estimated_points:
            job.status = "failed"
            job.error_message = "Not enough points for code generation"
            add_code_event(db, job.id, "failed", "点数不足，无法生成代码", {"estimated_points": job.estimated_points})
            db.commit()
            raise HTTPException(status_code=status.HTTP_402_PAYMENT_REQUIRED, detail=job.error_message)
    else:
        account = ensure_daily_points(db, current_user.id)

    job.status = "generating"
    add_code_event(db, job.id, "generating", "开始生成代码文件", {})
    save_code_artifacts(db, job, artifacts)
    job.actual_tokens = estimate_tokens("\n".join(file["content"] for file in artifacts["files"]))
    if charge_points:
        spend_code_generation_points(db, account, current_user.id, job, job.actual_tokens)
    else:
        job.actual_points = 0
    job.status = "preview_ready"
    add_code_event(
        db,
        job.id,
        "completed",
        "代码预览已准备好",
        {"actual_tokens": job.actual_tokens, "actual_points": job.actual_points, "provider_type": provider_type},
    )
    db.commit()
    db.refresh(job)
    return code_job_out(db, job)


@app.get("/api/code-generation/jobs/{job_id}", response_model=CodeGenerationJobOut)
def get_code_generation_job(job_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    job = db.scalar(select(CodeGenerationJob).where(CodeGenerationJob.id == job_id, CodeGenerationJob.user_id == current_user.id))
    if job is None:
        raise HTTPException(status_code=404, detail="Code generation job not found")
    return code_job_out(db, job)


@app.get("/api/code-generation/jobs/{job_id}/events")
def stream_code_generation_events(job_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    job = db.scalar(select(CodeGenerationJob).where(CodeGenerationJob.id == job_id, CodeGenerationJob.user_id == current_user.id))
    if job is None:
        raise HTTPException(status_code=404, detail="Code generation job not found")
    events = db.scalars(select(CodeGenerationEvent).where(CodeGenerationEvent.job_id == job.id).order_by(CodeGenerationEvent.sequence_index)).all()

    async def event_stream():
        for event in events:
            data = {
                "id": event.id,
                "type": event.event_type,
                "title": event.title,
                "payload": event.payload_json or {},
                "sequence_index": event.sequence_index,
            }
            yield f"event: update\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
            await asyncio.sleep(0.12)
        yield f"event: done\ndata: {json.dumps({'job_id': job.id, 'status': job.status}, ensure_ascii=False)}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


async def push_files_to_github(token: str, repo: str, branch: str, base_branch: str, files: list[CodeGenerationFile]) -> str:
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    api = "https://api.github.com"
    async with httpx.AsyncClient(timeout=60) as client:
        repo_response = await client.get(f"{api}/repos/{repo}", headers=headers)
        if repo_response.status_code >= 400:
            raise HTTPException(status_code=502, detail=f"GitHub repo access failed: {repo_response.text[:200]}")
        repo_data = repo_response.json()
        base = base_branch or repo_data.get("default_branch") or "main"
        ref_response = await client.get(f"{api}/repos/{repo}/git/ref/heads/{base}", headers=headers)
        if ref_response.status_code >= 400:
            raise HTTPException(status_code=502, detail=f"GitHub base branch not found: {base}")
        base_sha = ref_response.json()["object"]["sha"]
        commit_response = await client.get(f"{api}/repos/{repo}/git/commits/{base_sha}", headers=headers)
        if commit_response.status_code >= 400:
            raise HTTPException(status_code=502, detail="GitHub base commit lookup failed")
        base_tree = commit_response.json()["tree"]["sha"]

        tree = []
        for file in files:
            blob_response = await client.post(
                f"{api}/repos/{repo}/git/blobs",
                headers=headers,
                json={"content": file.content, "encoding": "utf-8"},
            )
            if blob_response.status_code >= 400:
                raise HTTPException(status_code=502, detail=f"GitHub blob create failed for {file.path}")
            tree.append({"path": file.path, "mode": "100644", "type": "blob", "sha": blob_response.json()["sha"]})

        tree_response = await client.post(
            f"{api}/repos/{repo}/git/trees",
            headers=headers,
            json={"base_tree": base_tree, "tree": tree},
        )
        if tree_response.status_code >= 400:
            raise HTTPException(status_code=502, detail="GitHub tree create failed")
        new_tree_sha = tree_response.json()["sha"]
        new_commit_response = await client.post(
            f"{api}/repos/{repo}/git/commits",
            headers=headers,
            json={"message": "Generate project with ThinkLand", "tree": new_tree_sha, "parents": [base_sha]},
        )
        if new_commit_response.status_code >= 400:
            raise HTTPException(status_code=502, detail="GitHub commit create failed")
        new_commit_sha = new_commit_response.json()["sha"]

        create_ref = await client.post(
            f"{api}/repos/{repo}/git/refs",
            headers=headers,
            json={"ref": f"refs/heads/{branch}", "sha": new_commit_sha},
        )
        if create_ref.status_code == 422:
            update_ref = await client.patch(
                f"{api}/repos/{repo}/git/refs/heads/{branch}",
                headers=headers,
                json={"sha": new_commit_sha, "force": True},
            )
            if update_ref.status_code >= 400:
                raise HTTPException(status_code=502, detail="GitHub branch update failed")
        elif create_ref.status_code >= 400:
            raise HTTPException(status_code=502, detail=f"GitHub branch create failed: {create_ref.text[:200]}")
        return f"https://github.com/{repo}/tree/{branch}"


@app.post("/api/code-generation/jobs/{job_id}/push-github", response_model=GitHubPushResponse)
async def push_code_generation_to_github(
    job_id: int,
    payload: GitHubPushRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    job = db.scalar(select(CodeGenerationJob).where(CodeGenerationJob.id == job_id, CodeGenerationJob.user_id == current_user.id))
    if job is None:
        raise HTTPException(status_code=404, detail="Code generation job not found")
    if job.status not in {"preview_ready", "completed"}:
        raise HTTPException(status_code=409, detail="Code preview is not ready")
    github_config = db.scalar(select(UserGitHubConfig).where(UserGitHubConfig.user_id == current_user.id))
    if github_config is None:
        raise HTTPException(status_code=400, detail="Please save GitHub token first")
    repo = (payload.repo or github_config.default_repo or "").strip()
    if "/" not in repo:
        raise HTTPException(status_code=422, detail="GitHub repo must be owner/name")
    branch = (payload.branch or f"thinkland/generated-{job.id}-{date.today().isoformat()}").strip()
    files = db.scalars(select(CodeGenerationFile).where(CodeGenerationFile.job_id == job.id).order_by(CodeGenerationFile.path)).all()
    if not files:
        raise HTTPException(status_code=409, detail="No generated files to push")

    job.status = "pushing"
    add_code_event(db, job.id, "pushing", "正在推送到 GitHub", {"repo": repo, "branch": branch})
    db.commit()
    try:
        url = await push_files_to_github(decrypt_api_key(github_config.encrypted_token), repo, branch, github_config.default_branch, files)
    except Exception as exc:
        job.status = "failed"
        job.error_message = str(exc)
        add_code_event(db, job.id, "failed", "GitHub 推送失败", {"error": str(exc)})
        db.commit()
        raise
    job.status = "completed"
    job.github_repo = repo
    job.github_branch = branch
    job.github_url = url
    add_code_event(db, job.id, "completed", "GitHub 推送完成", {"url": url, "repo": repo, "branch": branch})
    db.commit()
    return {"pushed": True, "repo": repo, "branch": branch, "url": url}


@app.get("/api/community/items", response_model=CommunityListResponse)
def list_community_items(
    item_type: str = "all",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    query = select(CommunityItem, User).join(User, User.id == CommunityItem.owner_user_id).where(CommunityItem.status == "published")
    if item_type in {"prd", "project"}:
        query = query.where(CommunityItem.item_type == item_type)
    rows = db.execute(query.order_by(CommunityItem.created_at.desc()).limit(80)).all()
    item_ids = [item.id for item, _owner in rows]
    starred_ids: set[int] = set()
    if item_ids:
        starred_ids = set(
            db.scalars(
                select(CommunityStar.item_id).where(
                    CommunityStar.user_id == current_user.id,
                    CommunityStar.item_id.in_(item_ids),
                )
            ).all()
        )
    return {"items": [community_item_out(item, owner, item.id in starred_ids) for item, owner in rows]}


@app.post("/api/community/items", response_model=CommunityItemOut)
def publish_community_item(
    payload: CommunityPublishRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    conversation = None
    if payload.conversation_id:
        conversation = db.scalar(
            select(Conversation).where(Conversation.id == payload.conversation_id, Conversation.user_id == current_user.id)
        )
        if conversation is None:
            raise HTTPException(status_code=404, detail="Conversation not found")

    content = {
        "prd": payload.prd,
        "flow": payload.flow,
        "tasks": payload.tasks,
    }
    if conversation and conversation.result_json:
        content = {
            "messages": conversation.result_json.get("messages", []),
            "prd": payload.prd or conversation.result_json.get("prd", []),
            "flow": payload.flow or conversation.result_json.get("flow", []),
            "tasks": payload.tasks or conversation.result_json.get("tasks", []),
        }

    if payload.item_type == "prd" and not content.get("prd"):
        raise HTTPException(status_code=422, detail="Please generate or fill PRD content before publishing")
    if payload.item_type == "project" and payload.project_url is None:
        raise HTTPException(status_code=422, detail="Project URL is required")

    summary = payload.summary.strip()
    if not summary:
        summary = (content.get("prd") or content.get("tasks") or [payload.title])[0][:240]

    item = CommunityItem(
        owner_user_id=current_user.id,
        source_conversation_id=conversation.id if conversation else None,
        item_type=payload.item_type,
        title=payload.title.strip(),
        summary=summary,
        content_json=content,
        project_url=str(payload.project_url) if payload.project_url else None,
        status="published",
        star_count=0,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return community_item_out(item, current_user, False)


@app.post("/api/community/items/{item_id}/star", response_model=CommunityStarResponse)
def toggle_community_star(
    item_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    item = db.get(CommunityItem, item_id)
    if item is None or item.status != "published":
        raise HTTPException(status_code=404, detail="Community item not found")

    star = db.scalar(select(CommunityStar).where(CommunityStar.item_id == item.id, CommunityStar.user_id == current_user.id))
    if star is None:
        db.add(CommunityStar(item_id=item.id, user_id=current_user.id))
        item.star_count += 1
        starred = True
    else:
        db.delete(star)
        item.star_count = max(0, item.star_count - 1)
        starred = False

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Star state changed, please retry")
    db.refresh(item)
    return {"item_id": item.id, "starred": starred, "star_count": item.star_count}
