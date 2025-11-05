import os
from pydantic import BaseModel


class Settings(BaseModel):
    kafka_bootstrap: str = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "redpanda:9092")
    topic_in: str = os.getenv("KAFKA_TOPIC_NLP", "nlp.extracted")
    neo4j_uri: str = os.getenv("NEO4J_URI", "bolt://neo4j:7687")
    neo4j_user: str = os.getenv("NEO4J_USER", "neo4j")
    neo4j_password: str = os.getenv("NEO4J_PASSWORD", "letmein")
    log_level: str = os.getenv("LOG_LEVEL", "INFO")


settings = Settings()
