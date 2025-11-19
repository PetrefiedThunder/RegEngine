"""Configuration for the admin service."""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Admin service configuration."""

    log_level: str = "INFO"
    admin_master_key: str = "change-me-in-production"

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache
def get_settings() -> Settings:
    return Settings()
