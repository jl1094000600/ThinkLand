from pydantic import BaseModel, Field, HttpUrl


class AuthRequest(BaseModel):
    account: str = Field(min_length=3, max_length=191)
    password: str = Field(min_length=6, max_length=128)


class UserOut(BaseModel):
    id: int
    account: str
    role: str


class PointOut(BaseModel):
    date: str
    granted_points: int
    used_points: int
    remaining_points: int


class AIConfigIn(BaseModel):
    base_url: HttpUrl
    api_key: str = Field(min_length=8, max_length=4096)
    model: str = Field(min_length=1, max_length=128)


class AIConfigOut(BaseModel):
    configured: bool
    base_url: str | None = None
    model: str | None = None


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut
    points: PointOut
    ai_config: AIConfigOut


class MeResponse(BaseModel):
    user: UserOut
    points: PointOut
    ai_config: AIConfigOut


class ChatMessage(BaseModel):
    role: str = Field(pattern="^(user|assistant)$")
    content: str = Field(min_length=1, max_length=6000)


class GenerateRequest(BaseModel):
    idea: str | None = Field(default=None, max_length=6000)
    conversation_id: int | None = None
    messages: list[ChatMessage] = Field(default_factory=list, max_length=30)


class GenerateResponse(BaseModel):
    conversation_id: int
    result: dict
    usage: dict
    points: PointOut


class ConfirmConversationRequest(BaseModel):
    conversation_id: int | None = None
    messages: list[ChatMessage] = Field(min_length=1, max_length=60)
    prd: list[str] = Field(default_factory=list, max_length=20)
    flow: list[str] = Field(default_factory=list, max_length=20)
    tasks: list[str] = Field(default_factory=list, max_length=20)


class ConfirmConversationResponse(BaseModel):
    saved: bool
    record_id: int


class CommunityPublishRequest(BaseModel):
    conversation_id: int | None = None
    item_type: str = Field(pattern="^(prd|project)$")
    title: str = Field(min_length=1, max_length=191)
    summary: str = Field(default="", max_length=1200)
    prd: list[str] = Field(default_factory=list, max_length=40)
    flow: list[str] = Field(default_factory=list, max_length=40)
    tasks: list[str] = Field(default_factory=list, max_length=40)
    project_url: HttpUrl | None = None


class CommunityOwnerOut(BaseModel):
    id: int
    account: str


class CommunityItemOut(BaseModel):
    id: int
    item_type: str
    title: str
    summary: str
    content: dict
    project_url: str | None
    star_count: int
    starred_by_me: bool
    owner: CommunityOwnerOut
    created_at: str


class CommunityListResponse(BaseModel):
    items: list[CommunityItemOut]


class CommunityStarResponse(BaseModel):
    item_id: int
    starred: bool
    star_count: int
