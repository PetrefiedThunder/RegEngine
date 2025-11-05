"""Kafka helper utilities."""

from __future__ import annotations

import json
from functools import lru_cache
from typing import Optional

from kafka import KafkaProducer

from .config import get_settings


@lru_cache(maxsize=1)
def get_producer() -> KafkaProducer:
    """Return a configured Kafka producer."""

    settings = get_settings()
    return KafkaProducer(
        bootstrap_servers=settings.kafka_bootstrap_servers,
        key_serializer=_serialize_key,
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        linger_ms=50,
        retries=5,
        acks="all",
    )


def _serialize_key(value: Optional[str]) -> bytes | None:
    if value is None:
        return None
    if isinstance(value, bytes):
        return value
    return str(value).encode("utf-8")


def send(topic: str, payload: dict, key: Optional[str] = None) -> None:
    """Send a message to Kafka."""

    producer = get_producer()
    producer.send(topic, key=key, value=payload)
    producer.flush(1.0)
