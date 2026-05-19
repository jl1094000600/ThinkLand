from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .ai_client import generate_product_plan
from .database import get_db
from .models import GenerationRecord, User, UserAIConfig
from .points import ensure_daily_points, estimate_tokens, points_out, spend_points
from .schemas import (
    AIConfigIn,
    AuthRequest,
    AuthResponse,
    ConfirmConversationRequest,
    ConfirmConversationResponse,
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
        return {"configured": False, "base_url": None, "model": None}
    return {"configured": True, "base_url": config.base_url, "model": config.model}


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


@app.get("/api/health")
def health() -> dict:
    return {"ok": True}


@app.post("/api/auth/register", response_model=AuthResponse)
def register(payload: AuthRequest, db: Session = Depends(get_db)) -> dict:
    account = payload.account.strip().lower()
    if db.scalar(select(User).where(User.account == account)) is not None:
        raise HTTPException(status_code=409, detail="账号已存在")
    user = User(account=account, password_hash=hash_password(payload.password), role="normal")
    db.add(user)
    try:
        db.flush()
        response = auth_payload(db, user)
        db.commit()
        return response
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="账号已存在")


@app.post("/api/auth/login", response_model=AuthResponse)
def login(payload: AuthRequest, db: Session = Depends(get_db)) -> dict:
    account = payload.account.strip().lower()
    user = db.scalar(select(User).where(User.account == account))
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="账号或密码错误")
    response = auth_payload(db, user)
    db.commit()
    return response


@app.get("/api/me", response_model=MeResponse)
def me(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    points = ensure_daily_points(db, current_user.id)
    db.commit()
    db.refresh(points)
    return {"user": user_out(current_user), "points": points_out(points), "ai_config": ai_config_out(current_user.ai_config)}


@app.put("/api/me/ai-config", response_model=MeResponse)
def save_ai_config(payload: AIConfigIn, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    config = db.scalar(select(UserAIConfig).where(UserAIConfig.user_id == current_user.id))
    if config is None:
        config = UserAIConfig(user_id=current_user.id, base_url=str(payload.base_url), model=payload.model, encrypted_api_key="")
        db.add(config)
    config.base_url = str(payload.base_url).rstrip("/")
    config.model = payload.model.strip()
    config.encrypted_api_key = encrypt_api_key(payload.api_key.strip())
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
        raise HTTPException(status_code=422, detail="请输入对话内容")

    account = ensure_daily_points(db, current_user.id)
    remaining = account.granted_points - account.used_points
    if remaining <= 0:
        raise HTTPException(status_code=status.HTTP_402_PAYMENT_REQUIRED, detail="今日点数已用完")

    config = db.scalar(select(UserAIConfig).where(UserAIConfig.user_id == current_user.id))
    if config is None:
        raise HTTPException(status_code=400, detail="请先保存 AI 接口配置")

    token_budget = remaining * 1000
    estimated_prompt_tokens = estimate_tokens(dialogue_text)
    if estimated_prompt_tokens >= token_budget:
        raise HTTPException(status_code=status.HTTP_402_PAYMENT_REQUIRED, detail="剩余点数不足以处理这次输入")
    max_tokens = max(256, min(2048, token_budget - estimated_prompt_tokens))

    try:
        ai_response = await generate_product_plan(
            base_url=config.base_url,
            api_key=decrypt_api_key(config.encrypted_api_key),
            model=config.model,
            messages=request_messages,
            max_tokens=max_tokens,
        )
    except Exception as exc:
        record = GenerationRecord(user_id=current_user.id, prompt=dialogue_text, model=config.model, status="failed", error_message=str(exc))
        db.add(record)
        db.commit()
        raise HTTPException(status_code=502, detail=str(exc))

    usage = ai_response["usage"]
    if usage["total_tokens"] <= 0:
        usage["total_tokens"] = estimated_prompt_tokens + usage["completion_tokens"]
    record = GenerationRecord(
        user_id=current_user.id,
        prompt=dialogue_text,
        result_json=ai_response["result"],
        model=config.model,
        prompt_tokens=usage["prompt_tokens"],
        completion_tokens=usage["completion_tokens"],
        total_tokens=usage["total_tokens"],
        status="success",
    )
    db.add(record)
    db.flush()
    record.points_used = spend_points(db, account, current_user.id, record.id, usage["total_tokens"])
    db.commit()
    db.refresh(account)
    return {"result": ai_response["result"], "usage": {**usage, "points_used": record.points_used}, "points": points_out(account)}


@app.post("/api/conversations/confirm", response_model=ConfirmConversationResponse)
def confirm_conversation(
    payload: ConfirmConversationRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    messages = [{"role": item.role, "content": item.content} for item in payload.messages]
    record = GenerationRecord(
        user_id=current_user.id,
        prompt=messages_to_text(messages),
        result_json={
            "messages": messages,
            "prd": payload.prd,
            "flow": payload.flow,
            "tasks": payload.tasks,
        },
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

