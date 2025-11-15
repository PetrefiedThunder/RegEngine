import os

from pydantic import BaseModel


class Settings(BaseModel):
    aws_endpoint_url: str | None = os.getenv("AWS_ENDPOINT_URL")
    raw_bucket: str = os.getenv("RAW_DATA_BUCKET", "reg-engine-raw-data-dev")
    processed_bucket: str = os.getenv(
        "PROCESSED_DATA_BUCKET", "reg-engine-processed-data-dev"
    )
    kafka_bootstrap: str = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "redpanda:9092")
    topic_in: str = os.getenv("KAFKA_TOPIC_NORMALIZED", "ingest.normalized")
    topic_out: str = os.getenv("KAFKA_TOPIC_NLP", "nlp.extracted")
    log_level: str = os.getenv("LOG_LEVEL", "INFO")


settings = Settings()
