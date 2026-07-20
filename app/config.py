from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Config(BaseSettings):
    """Application settings loaded from environment variables."""

    openrouter_api_key: SecretStr
    model_provider: Literal["openrouter"] = "openrouter"

    openrouter_api_base: str = "https://openrouter.ai/api/v1"
    llm_model: str = "openai/gpt-4.1-mini"
    llm_context_window: int = Field(default=128000, ge=1000)
    llm_max_tokens: int = Field(default=512, ge=1, le=4096)

    embedding_model: str = "BAAI/bge-small-en-v1.5"

    data_dir: str = "data"
    storage_dir: str = "storage"
    reports_dir: str = "reports"

    chunk_size: int = Field(default=700, ge=100, le=2000)
    chunk_overlap: int = Field(default=100, ge=0, le=500)
    top_k: int = Field(default=5, ge=1, le=20)
    max_tool_calls: int = Field(default=10, ge=1, le=20)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    agent_timeout_seconds: int = Field(
        default=120,
        ge=10,
        le=600,
    )

    multi_agent_max_iterations: int = Field(
        default=25,
        ge=5,
        le=50,
    )


config = Config()