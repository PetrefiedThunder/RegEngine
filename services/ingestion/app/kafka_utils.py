"""Kafka helper utilities."""

from __future__ import annotations

import atexit
import json
from typing import Optional

import structlog
from kafka import KafkaProducer

from .config import get_settings

logger = structlog.get_logger("kafka-utils")

_producer = None


def get_producer() -> KafkaProducer:
    """Return a configured Kafka producer."""

    global _producer
    if _producer is None:
        settings = get_settings()
        _producer = KafkaProducer(
            bootstrap_servers=settings.kafka_bootstrap_servers,
            key_serializer=_serialize_key,
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
            linger_ms=50,
            retries=5,
            acks="all",
        )
    return _producer


def close_producer() -> None:
    """Close the Kafka producer."""
    global _producer
    if _producer is not None:
        try:
            _producer.close()
        except Exception as exc:
            logger.warning("producer_close_failed", error=str(exc))
        _producer = None


atexit.register(close_producer)


def _serialize_key(value: Optional[str]) -> bytes | None:
    if value is None:
        return None
    if isinstance(value, bytes):
        return value
    return str(value).encode("utf-8")


def send(topic: str, payload: dict, key: Optional[str] = None) -> None:
    """Send a message to Kafka."""

    producer = get_producer()
    try:
        future = producer.send(topic, key=key, value=payload)
        record_metadata = future.get(timeout=10)
        producer.flush(timeout=1.0)
    except Exception as exc:
        logger.error("kafka_send_failed", topic=topic, error=str(exc))
        raise
