"""Configuration for diff service."""

from __future__ import annotations

import os

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Service configuration"""

    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    aws_endpoint_url: str | None = os.getenv("AWS_ENDPOINT_URL")
    raw_bucket: str = os.getenv("RAW_DATA_BUCKET", "reg-engine-raw-data-dev")
    processed_bucket: str = os.getenv(
        "PROCESSED_DATA_BUCKET", "reg-engine-processed-data-dev"
    )
    aws_region: str = os.getenv("AWS_REGION", "us-east-1")


def get_settings() -> Settings:
    """Get settings instance"""
    return Settings()
