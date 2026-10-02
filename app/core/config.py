# Leonardo Briquezi
# github: https://github.com/leobrqz
# linkedin: https://www.linkedin.com/in/leonardobri
from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "ERP Demo API"
    app_env: str = "local"
    database_url: str = "postgresql+psycopg://erp:erp_local_only@localhost:5432/erp"
    redis_url: str = "redis://localhost:6379/0"
    jwt_secret_key: str = "local-only-change-me"
    jwt_algorithm: str = "HS256"
    jwt_access_token_minutes: int = Field(default=60, ge=5, le=1440)
    admin_username: str = "admin"
    admin_password: str = "change-me"
    admin_email: str = "admin@example.test"
    low_stock_threshold: int = Field(default=10, ge=0, le=100_000)
    ai_provider: Literal["rules", "local"] = "rules"
    llm_base_url: str = "http://localhost:8080/v1"
    llm_api_key: str = "local-no-auth"
    llm_model: str = "MiniCPM5-2B"
    llm_timeout_seconds: float = Field(default=60.0, gt=0, le=120)


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
