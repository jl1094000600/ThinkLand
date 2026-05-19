from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .ai_client import generate_product_plan
from .database import get_db
from .models import CommunityItem, CommunityStar, Conversation, ConversationMessage, GenerationRecord, User, UserAIConfig
from .points import ensure_daily_points, estimate_tokens, points_out, spend_points
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
        raise HTTPException(status_code=422, detail="Please enter conversation content")

    conversation = get_or_create_conversation(db, current_user.id, payload.conversation_id, request_messages)
    append_missing_messages(db, conversation, current_user.id, request_messages)
    db.commit()
    db.refresh(conversation)

    account = ensure_daily_points(db, current_user.id)
    remaining = account.granted_points - account.used_points
    if remaining <= 0:
        raise HTTPException(status_code=status.HTTP_402_PAYMENT_REQUIRED, detail="Today's points are used up")

    config = db.scalar(select(UserAIConfig).where(UserAIConfig.user_id == current_user.id))
    if config is None:
        raise HTTPException(status_code=400, detail="Please save AI settings first")

    token_budget = remaining * 1000
    estimated_prompt_tokens = estimate_tokens(dialogue_text)
    if estimated_prompt_tokens >= token_budget:
        raise HTTPException(status_code=status.HTTP_402_PAYMENT_REQUIRED, detail="Not enough points for this input")
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
    return {
        "conversation_id": conversation.id,
        "result": result,
        "usage": {**usage, "points_used": record.points_used},
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
