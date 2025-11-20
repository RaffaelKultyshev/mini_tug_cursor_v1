from functools import lru_cache
from pathlib import Path
from typing import Optional
import os

from pydantic_settings import BaseSettings
from pydantic import Field, field_validator, ConfigDict


class Settings(BaseSettings):
    model_config = ConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="TUG_",
    )

    # Database
    database_url: str | None = Field(
        default=None,
        description="Optional SQLAlchemy connection string. Falls back to sqlite file.",
    )

    # Document AI
    docai_project_id: Optional[str] = Field(
        default="361271679946", description="Google Cloud project id for Document AI"
    )
    docai_location: str = Field(default="eu", description="Document AI processor region")
    docai_processor_id: Optional[str] = Field(
        default="2ee67d07894fd7f1", description="Invoice parser processor id"
    )
    docai_key_path: Optional[Path] = Field(
        default=None,
        description="Path to service-account json. If none, DOC_AI_KEY_JSON env is used.",
    )
    docai_key_json: Optional[str] = Field(
        default=None,
        description="Inline JSON credentials blob (base64 or raw). Takes precedence over key_path.",
    )

    # Frontend origins - can be comma-separated string or list
    allowed_origins: str | list[str] = Field(
        default="http://localhost:3000,http://127.0.0.1:3000",
        description="Comma-separated list of allowed CORS origins",
    )

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def parse_origins(cls, v):
        if isinstance(v, str):
            # Split by comma and strip whitespace
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v


@lru_cache
def get_settings() -> Settings:
    return Settings()


