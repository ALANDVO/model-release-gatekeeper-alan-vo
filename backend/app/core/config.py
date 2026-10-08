"""Application configuration settings."""
from typing import Optional
from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration loaded from environment variables."""
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    ENVIRONMENT: str = Field(default="development")
    HOST: str = Field(default="127.0.0.1")
    PORT: int = Field(default=8000)
    DATABASE_URL: str = Field(default="sqlite:///./gatekeeper.db")

    # OIDC Configuration
    OIDC_ISSUER_URL: str = Field(default="http://127.0.0.1:8080/realms/gatekeeper-realm")
    OIDC_CLIENT_ID: str = Field(default="gatekeeper-client")
    OIDC_AUDIENCE: str = Field(default="gatekeeper-client")

    # Local Demo Mode (strictly local; refused in production)
    DEMO_MODE: bool = Field(default=False)
    DEMO_JWT_SECRET: str = Field(default="demo-secret-key-for-local-testing-only")

    # LLM Settings (LLM_API_KEY is the only credential variable)
    LLM_API_KEY: Optional[str] = Field(default=None)
    LLM_PROVIDER: str = Field(default="openai")
    LLM_MODEL: str = Field(default="gpt-4o-mini")
    LLM_BASE_URL: Optional[str] = Field(default=None)
    LLM_TIMEOUT_SECONDS: float = Field(default=10.0)

    # HMAC key for digital manifest and approval signing
    SIGNING_KEY: str = Field(default="gatekeeper-release-signing-key-internal")

    @model_validator(mode="after")
    def validate_production_safety(self) -> "Settings":
        """Ensure demo mode is never enabled in a production environment."""
        if self.ENVIRONMENT.lower() == "production" and self.DEMO_MODE:
            raise RuntimeError(
                "CRITICAL SECURITY CONFIGURATION ERROR: Demo mode cannot be enabled in production environment."
            )
        return self


settings = Settings()
