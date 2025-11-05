"""Configuration for the ingestion service."""

from functools import lru_cache
from pydantic import BaseSettings, Field


class Settings(BaseSettings):
    """Environment-driven configuration values."""

    raw_bucket: str = Field(default="reg-engine-raw-data-dev", env="RAW_DATA_BUCKET")
    processed_bucket: str = Field(
        default="reg-engine-processed-data-dev", env="PROCESSED_DATA_BUCKET"
    )
    aws_endpoint_url: str | None = Field(default=None, env="AWS_ENDPOINT_URL")
    aws_region: str = Field(default="us-east-1", env="AWS_DEFAULT_REGION")
    aws_access_key_id: str | None = Field(default=None, env="AWS_ACCESS_KEY_ID")
    aws_secret_access_key: str | None = Field(default=None, env="AWS_SECRET_ACCESS_KEY")
    kafka_bootstrap_servers: str = Field(
        default="redpanda:9092", env="KAFKA_BOOTSTRAP_SERVERS"
    )
    kafka_topic_normalized: str = Field(
        default="ingest.normalized", env="KAFKA_TOPIC_NORMALIZED"
    )
    log_level: str = Field(default="INFO", env="LOG_LEVEL")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached settings instance."""

    return Settings()
