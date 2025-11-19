from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Environment-driven configuration values."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    aws_endpoint_url: str | None = Field(default=None, alias="AWS_ENDPOINT_URL")
    raw_bucket: str = Field(default="reg-engine-raw-data-dev", alias="RAW_DATA_BUCKET")
    processed_bucket: str = Field(
        default="reg-engine-processed-data-dev", alias="PROCESSED_DATA_BUCKET"
    )
    kafka_bootstrap: str = Field(
        default="redpanda:9092", alias="KAFKA_BOOTSTRAP_SERVERS"
    )
    topic_in: str = Field(default="ingest.normalized", alias="KAFKA_TOPIC_NORMALIZED")
    topic_out: str = Field(default="nlp.extracted", alias="KAFKA_TOPIC_NLP")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached settings instance."""

    return Settings()


settings = get_settings()
