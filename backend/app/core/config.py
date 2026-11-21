"""Application settings. Everything comes from environment variables / .env —
nothing secret is hardcoded."""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    APP_NAME: str = "AegisBank AI"
    TAGLINE: str = "Intelligent Fraud Investigation for Modern Banking"
    ENVIRONMENT: str = "development"
    API_V1_PREFIX: str = "/api/v1"
    DATABASE_URL: str = "sqlite:///./aegisbank_dev.db"  # use postgresql+psycopg2://... in real deployments

    JWT_SECRET: str = "CHANGE_ME_IN_ENV"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480

    # LLM provider for the (not yet rebuilt) agent layer — Groq, with deterministic fallback.
    GROQ_API_KEY: str | None = None
    GROQ_MODEL: str = "llama-3.3-70b-versatile"
    LLM_PROVIDER: str = "groq"

    LLM_REQUEST_TIMEOUT_SECONDS: int = 20
    REDIS_URL: str | None = None
    CHROMA_PERSIST_DIR: str = "./data/chroma"
    RAG_EMBEDDER_PATH: str | None = None  # default: app/rag/artifacts/tfidf_embedder.joblib
    RAG_DOCUMENTS_DIR: str | None = None  # default: <repo>/rag_documents
    LOGIN_RATE_LIMIT_PER_MINUTE: int = 10
    API_RATE_LIMIT_PER_MINUTE: int = 600
    CHAT_RATE_LIMIT_PER_MINUTE: int = 20
    FRONTEND_DIST: str | None = None  # when set (single-container deploys, e.g. Hugging Face) FastAPI also serves the built React app
    ALLOW_IFRAME: bool = False  # Hugging Face shows Spaces inside an iframe; leave False everywhere else (clickjacking protection)
    CORS_ORIGINS: list[str] = ["http://localhost:5173", "http://localhost:8080", "http://localhost:3000"]

    @property
    def llm_available(self) -> bool:
        return bool(self.GROQ_API_KEY)


_PLACEHOLDER_SECRETS = {"CHANGE_ME_IN_ENV", "replace-with-a-long-random-secret", "REPLACE_ME"}


def validate_production_secrets(settings: Settings) -> None:
    """Refuse to start in production with a placeholder or short JWT secret."""
    if settings.ENVIRONMENT.lower() != "production":
        return
    s = settings.JWT_SECRET
    if s in _PLACEHOLDER_SECRETS or s.startswith("REPLACE") or len(s) < 32:
        raise RuntimeError(
            "Refusing to start: JWT_SECRET is a placeholder or shorter than 32 characters. "
            'Generate one with: python -c "import secrets; print(secrets.token_urlsafe(48))"'
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
