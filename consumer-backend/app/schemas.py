from pydantic import BaseModel, Field, HttpUrl, field_validator, model_validator

from .codegen_registry import validate_stack_choice


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
    provider_type: str = Field(default="custom", pattern="^(platform|custom)$")
    base_url: HttpUrl | None = None
    api_key: str | None = Field(default=None, min_length=8, max_length=4096)
    model: str = Field(min_length=1, max_length=128)

    @model_validator(mode="after")
    def validate_custom_config(self) -> "AIConfigIn":
        if self.provider_type == "custom" and (self.base_url is None or not self.api_key):
            raise ValueError("Custom model requires Base URL and API Key")
        return self


class AIConfigOut(BaseModel):
    configured: bool
    provider_type: str = "custom"
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
    conversation_id: int


class PrdItemOut(BaseModel):
    id: int
    title: str
    summary: str
    prd: list[str]
    flow: list[str]
    tasks: list[str]
    updated_at: str


class PrdListResponse(BaseModel):
    items: list[PrdItemOut]


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


class TechStackIn(BaseModel):
    frontend: str
    backend: str
    database: str
    deploy: str

    @field_validator("frontend")
    @classmethod
    def validate_frontend(cls, value: str) -> str:
        return validate_stack_choice("frontend", value)

    @field_validator("backend")
    @classmethod
    def validate_backend(cls, value: str) -> str:
        return validate_stack_choice("backend", value)

    @field_validator("database")
    @classmethod
    def validate_database(cls, value: str) -> str:
        return validate_stack_choice("database", value)

    @field_validator("deploy")
    @classmethod
    def validate_deploy(cls, value: str) -> str:
        return validate_stack_choice("deploy", value)


class CodeGenerationJobCreate(BaseModel):
    conversation_id: int | None = None
    title: str = Field(min_length=1, max_length=191)
    target_description: str = Field(min_length=1, max_length=4000)
    stack: TechStackIn


class GitHubConfigIn(BaseModel):
    token: str = Field(min_length=20, max_length=4096)
    default_repo: str | None = Field(default=None, max_length=255)
    default_branch: str = Field(default="main", min_length=1, max_length=128)


class GitHubConfigOut(BaseModel):
    configured: bool
    default_repo: str | None = None
    default_branch: str | None = None


class CodeFileOut(BaseModel):
    path: str
    language: str
    content: str
    explanation: str
    status: str


class CodeGraphNodeOut(BaseModel):
    key: str
    type: str
    label: str
    description: str
    file_path: str | None = None
    position: dict | None = None
    status: str


class CodeGraphEdgeOut(BaseModel):
    source: str
    target: str
    type: str
    label: str


class CodeGenerationJobOut(BaseModel):
    id: int
    title: str
    target_description: str
    stack: dict
    status: str
    provider_type: str
    estimated_tokens: int
    estimated_points: int
    actual_tokens: int
    actual_points: int
    github_repo: str | None = None
    github_branch: str | None = None
    github_url: str | None = None
    error_message: str | None = None
    files: list[CodeFileOut]
    graph_nodes: list[CodeGraphNodeOut]
    graph_edges: list[CodeGraphEdgeOut]


class GitHubPushRequest(BaseModel):
    repo: str | None = Field(default=None, max_length=255)
    branch: str | None = Field(default=None, max_length=255)


class GitHubPushResponse(BaseModel):
    pushed: bool
    repo: str
    branch: str
    url: str
