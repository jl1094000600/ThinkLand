from functools import lru_cache
from pathlib import Path
import os

from pydantic import BaseModel


def load_env_file() -> None:
    env_path = Path(__file__).resolve().parents[1] / ".env"
    if not env_path.exists():
        return
    for raw_line in env_path.read_text(encoding="utf-8-sig").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def require_env(name: str) -> str:
    value = os.getenv(name)
    if value:
        return value
    raise RuntimeError(f"Missing required setting {name}. Create consumer-backend/.env from .env.example.")


class Settings(BaseModel):
    database_url: str
    jwt_secret: str
    api_key_encryption_key: str
    access_token_expire_minutes: int = 10080
    openai_compat_timeout_seconds: int = 90


@lru_cache
def get_settings() -> Settings:
    load_env_file()
    return Settings(
        database_url=require_env("DATABASE_URL"),
        jwt_secret=require_env("JWT_SECRET"),
        api_key_encryption_key=require_env("API_KEY_ENCRYPTION_KEY"),
        access_token_expire_minutes=int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "10080")),
        openai_compat_timeout_seconds=int(os.getenv("OPENAI_COMPAT_TIMEOUT_SECONDS", "90")),
    )
