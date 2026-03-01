import os
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # ── Database ──
    # Docker uses PostgreSQL. For local dev without Docker, use:
    # sqlite+aiosqlite:///./unigpu.db
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://unigpu:unigpu_secret@localhost:5432/unigpu"
    )

    # ── Redis ──
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    # ── JWT ──
    SECRET_KEY: str = os.getenv("SECRET_KEY", "super-secret-change-me-in-prod")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours

    # ── Billing ──
    RATE_PER_SECOND: float = 0.002  # $0.001 per second of GPU usage

    # ── Heartbeat ──
    HEARTBEAT_TIMEOUT_SECONDS: int = 60  # GPU marked offline after 60s silence

    # ── File Storage ──
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "uploads")

    class Config:
        env_file = ".env"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
