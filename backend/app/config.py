import os
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # ── Environment ──
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"

    # ── Database ──
    # Docker uses PostgreSQL. For local dev without Docker, use:
    # sqlite+aiosqlite:///./unigpu.db
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://unigpu:unigpu_secret@localhost:5432/unigpu"
    )
    
    # Validate that DATABASE_URL is set for production
    @property
    def is_prod_db(self) -> bool:
        return not self.DATABASE_URL.startswith("sqlite")

    # ── Redis ──
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    # ── JWT ──
    # ⚠️  CRITICAL: In production, this MUST be set via environment variable
    # Generate with: python -c "import secrets; print(secrets.token_urlsafe(32))"
    # Default is INSECURE and only for local development
    SECRET_KEY: str = os.getenv("SECRET_KEY", "change-me-in-production-to-a-random-string")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours

    # ── Billing ──
    RATE_PER_SECOND: float = 0.002  # $0.002 per second of GPU usage

    # ── Heartbeat ──
    HEARTBEAT_TIMEOUT_SECONDS: int = 60  # GPU marked offline after 60s silence

    # ── File Storage ──
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "uploads")

    # ── CORS ──
    # In production, set to your frontend domain via .env
    # Multiple origins: "https://domain1.com,https://domain2.com"
    ALLOWED_ORIGINS: str = os.getenv("ALLOWED_ORIGINS", "*")

    class Config:
        env_file = ".env"
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Warn if using default SECRET_KEY in production
        if not self.DEBUG and self.SECRET_KEY == "change-me-in-production-to-a-random-string":
            raise ValueError(
                "⚠️  CRITICAL: SECRET_KEY must be set via environment variable in production. "
                "Generate a new key with: python -c \"import secrets; print(secrets.token_urlsafe(32))\"\n"
                "Then add to Railway: Settings → Variables → SECRET_KEY = <your-key>"
            )


@lru_cache()
def get_settings() -> Settings:
    return Settings()
