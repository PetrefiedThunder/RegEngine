"""Alert Service Configuration"""

from __future__ import annotations

import os

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Service configuration"""

    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    kafka_bootstrap: str = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
    smtp_host: str = os.getenv("SMTP_HOST", "smtp.gmail.com")
    smtp_port: int = int(os.getenv("SMTP_PORT", "587"))
    smtp_user: str = os.getenv("SMTP_USER", "")
    smtp_password: str = os.getenv("SMTP_PASSWORD", "")
    slack_webhook_url: str = os.getenv("SLACK_WEBHOOK_URL", "")


def get_settings() -> Settings:
    """Get settings instance"""
    return Settings()
