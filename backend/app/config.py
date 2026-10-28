from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All runtime configuration comes from the environment (or a local .env file)."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    environment: Literal["development", "test", "production"] = "development"
    database_url: str = "postgresql+psycopg://projectforge:projectforge@localhost:5432/projectforge"

    # Demo mode exposes one-click sign-in as synthetic personas. Never enable it on a
    # deployment that holds real data.
    demo_mode: bool = True

    session_ttl_hours: int = 24 * 7
    session_cookie_name: str = "pf_session"
    # Secure cookies require HTTPS; local development runs over plain HTTP.
    cookie_secure: bool = False

    login_rate_limit_attempts: int = 10
    login_rate_limit_window_seconds: int = 300


@lru_cache
def get_settings() -> Settings:
    return Settings()
