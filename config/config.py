import os
from dataclasses import dataclass
from pathlib import Path
from dotenv import load_dotenv

# Search for .env.local first, then fall back to .env
# This supports running from root or subdirectories
ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env.local")
load_dotenv(ROOT_DIR / ".env")


@dataclass(frozen=True)
class Config:
    # LiveKit Credentials
    livekit_url: str = os.getenv("LIVEKIT_URL", os.getenv("LIVEKIT_WS_URL", ""))
    livekit_api_key: str = os.getenv("LIVEKIT_API_KEY", "")
    livekit_api_secret: str = os.getenv("LIVEKIT_API_SECRET", "")

    # AI Model Providers
    deepgram_api_key: str = os.getenv("DEEPGRAM_API_KEY", "")
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    cartesia_api_key: str = os.getenv("CARTESIA_API_KEY", "")
    eleven_api_key: str = os.getenv("ELEVEN_API_KEY", "")
    google_api_key: str = os.getenv("GOOGLE_API_KEY", "")
    sarvam_api_key: str = os.getenv("SARVAM_API_KEY", "")

    # Database (PostgreSQL)
    raw_database_url: str = os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://postgres:postgres@localhost:5432/call_engine",
    )
    db_echo: bool = os.getenv("DB_ECHO", "false").lower() in ("true", "1", "yes")
    db_pool_size: int = int(os.getenv("DB_POOL_SIZE", "10"))
    db_max_overflow: int = int(os.getenv("DB_MAX_OVERFLOW", "20"))

    # Agent / Server settings
    agent_name: str = os.getenv("AGENT_NAME", "call-engine")
    environment: str = os.getenv("ENVIRONMENT", "development")
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    debug: bool = os.getenv("DEBUG", "true").lower() in ("true", "1", "yes")
    client_endpoint = os.getenv("CLIENT_ENDPOINT" , "http://localhost:5173")

    # API Server settings
    api_host: str = os.getenv("API_HOST", "0.0.0.0")
    api_port: int = int(os.getenv("PORT", os.getenv("API_PORT", "8000")))

    run_agent_worker_with_api: bool = os.getenv(
        "RUN_AGENT_WORKER_WITH_API", "true"
    ).lower() in ("true", "1", "yes")
    run_job_worker_with_api: bool = os.getenv(
        "RUN_JOB_WORKER_WITH_API", "true"
    ).lower() in ("true", "1", "yes")
    job_worker_poll_interval: float = float(os.getenv("JOB_WORKER_POLL_INTERVAL", "2.0"))

    # JWT / Auth
    jwt_secret_key: str = os.getenv(
        "JWT_SECRET_KEY", "your-secret-key-change-in-production"
    )
    jwt_algorithm: str = os.getenv("JWT_ALGORITHM", "HS256")
    access_token_expire_minutes: int = int(
        os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440")
    )

    # Email / SMTP settings
    mail_username: str = os.getenv("MAIL_USERNAME", "").strip("\"', ")
    mail_password: str = os.getenv("MAIL_PASSWORD", "").strip("\"', ")
    mail_from: str = os.getenv("MAIL_FROM", "").strip("\"', ")
    mail_port: int = int(os.getenv("MAIL_PORT", "465").split("#")[0].strip("\"', ") or 465)
    mail_server: str = os.getenv("MAIL_SERVER", "").strip("\"', ")
    mail_starttls: bool = os.getenv("MAIL_STARTTLS", "false").split("#")[0].strip("\"', ").lower() in ("true", "1", "yes")
    mail_ssl_tls: bool = os.getenv("MAIL_SSL_TLS", "true").split("#")[0].strip("\"', ").lower() in ("true", "1", "yes")
    use_credentials: bool = os.getenv("USE_CREDENTIALS", "true").split("#")[0].strip("\"', ").lower() in ("true", "1", "yes")
    validate_certs: bool = os.getenv("VALIDATE_CERTS", "true").split("#")[0].strip("\"', ").lower() in ("true", "1", "yes")


    # Database URL properties
    @property
    def database_url(self) -> str:
        """Returns the async database URL, normalizing postgresql:// to postgresql+psycopg:// if needed."""
        url = self.raw_database_url.strip()
        if url.startswith("postgresql://"):
            return url.replace("postgresql://", "postgresql+psycopg://", 1)
        if url.startswith("postgres://"):
            return url.replace("postgres://", "postgresql+psycopg://", 1)
        return url

    @property
    def DATABASE_URL(self) -> str:
        return self.database_url

    @property
    def DB_ECHO(self) -> bool:
        return self.db_echo

    @property
    def sync_database_url(self) -> str:
        """Returns synchronous database URL (for sync tools if needed)."""
        url = self.database_url
        for prefix in ("postgresql+asyncpg://", "postgresql+psycopg://"):
            if url.startswith(prefix):
                return url.replace(prefix, "postgresql://", 1)
        return url

    def validate_livekit(self) -> None:
        """Validates that essential LiveKit credentials are present."""
        missing = []
        if not self.livekit_url:
            missing.append("LIVEKIT_URL")
        if not self.livekit_api_key:
            missing.append("LIVEKIT_API_KEY")
        if not self.livekit_api_secret:
            missing.append("LIVEKIT_API_SECRET")
        if missing:
            raise ValueError(
                f"Missing required LiveKit configuration variables: {', '.join(missing)}. "
                "Please set them in your .env or .env.local file."
            )


# Default singleton instance
config = Config()
settings = config
