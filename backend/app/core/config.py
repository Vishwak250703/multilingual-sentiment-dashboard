from pydantic_settings import BaseSettings
from pydantic import AnyHttpUrl, field_validator
from typing import List, Optional
import os


class Settings(BaseSettings):
    # Application
    APP_NAME: str = "MultilingualSentimentDashboard"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    API_V1_PREFIX: str = "/api/v1"

    # Security
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Database
    DATABASE_URL: str
    DATABASE_URL_SYNC: str

    # Redis
    REDIS_URL: str = "redis://redis:6379/0"
    CELERY_BROKER_URL: str = "redis://redis:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://redis:6379/2"

    # ChromaDB
    # CHROMA_MODE=http   → separate ChromaDB container (docker-compose dev/prod)
    # CHROMA_MODE=embedded → PersistentClient inside the process (free cloud deploy)
    CHROMA_MODE: str = "http"
    CHROMA_HOST: str = "chromadb"
    CHROMA_PORT: int = 8000
    CHROMA_PATH: str = "/app/chroma_data"

    # AI / NLP
    ANTHROPIC_API_KEY: str
    CLAUDE_MODEL: str = "claude-opus-4-6"
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"

    # Translation
    TRANSLATION_PROVIDER: str = "deep_translator"

    # CORS
    ALLOWED_ORIGINS: str = "http://localhost:3000,http://localhost:5173"

    @property
    def cors_origins(self) -> List[str]:
        return [o.strip() for o in self.ALLOWED_ORIGINS.split(",")]

    # Upload
    MAX_UPLOAD_SIZE_MB: int = 50
    UPLOAD_DIR: str = "/app/uploads"

    # Alerts
    SENTIMENT_DROP_THRESHOLD: float = 0.2
    ALERT_CHECK_INTERVAL_SECONDS: int = 300

    # First Admin
    FIRST_ADMIN_EMAIL: str = "admin@sentiment.ai"
    FIRST_ADMIN_PASSWORD: str = "Admin@123456"
    FIRST_ADMIN_NAME: str = "Super Admin"

    # ─── Email / SMTP (leave empty to disable email alerts) ───────
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = "alerts@sentimentai.io"
    SMTP_TLS: bool = True
    # Comma-separated list of recipients for alert emails
    ALERT_EMAIL_RECIPIENTS: str = ""

    # ─── Slack (leave empty to disable Slack alerts) ──────────────
    SLACK_WEBHOOK_URL: str = ""

    @property
    def alert_email_recipients_list(self) -> list[str]:
        return [e.strip() for e in self.ALERT_EMAIL_RECIPIENTS.split(",") if e.strip()]

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
