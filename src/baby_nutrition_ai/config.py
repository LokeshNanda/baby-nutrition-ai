"""Configuration management - config-driven architecture."""

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings from environment and .env."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Server
    host: str = Field(default="0.0.0.0", description="Bind host")
    port: int = Field(default=8000, description="Bind port")

    # LLM (OpenAI-compatible)
    llm_base_url: str | None = Field(default=None, description="OpenAI-compatible API base URL")
    llm_api_key: str = Field(default="", description="API key for LLM provider")
    llm_model: str = Field(default="gpt-4o-mini", description="Model name")

    # WhatsApp Business API
    whatsapp_verify_token: str = Field(default="", description="Webhook verification token")
    whatsapp_access_token: str = Field(default="", description="Meta WhatsApp API access token")
    whatsapp_phone_id: str = Field(default="", description="WhatsApp Business phone number ID")

    # Data
    data_dir: Path = Field(default=Path("data"), description="Directory for JSON persistence")
    redis_url: str | None = Field(default=None, description="Redis URL for cloud persistence (e.g. Upstash)")


def load_yaml_config(config_path: Path) -> dict[str, Any]:
    """Load YAML config file."""
    if not config_path.exists():
        return {}
    with config_path.open() as f:
        return yaml.safe_load(f) or {}


@lru_cache
def get_settings() -> Settings:
    """Cached settings instance."""
    return Settings()


@lru_cache
def get_food_rules(config_dir_str: str = "") -> dict[str, Any]:
    """Load food rules from config. Rules override AI output."""
    if not config_dir_str:
        config_dir = Path(__file__).parent.parent.parent / "config"
    else:
        config_dir = Path(config_dir_str)
    rules_path = config_dir / "food_rules.yaml"
    return load_yaml_config(rules_path)
