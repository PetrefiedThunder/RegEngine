from __future__ import annotations

import json
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path

import structlog
from jsonschema import Draft7Validator, ValidationError
from kafka import KafkaConsumer, KafkaProducer
from kafka.admin import KafkaAdminClient, NewTopic
from kafka.errors import KafkaTimeoutError, TopicAlreadyExistsError
from prometheus_client import Counter

from .config import settings
from .extractor import extract_entities
from .s3_utils import get_bytes

logger = structlog.get_logger("nlp-consumer")

MESSAGES_COUNTER = Counter("nlp_messages_total", "NLP messages processed", ["status"])

_shutdown_event = threading.Event()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_schema() -> Draft7Validator:
    repo_root = Path(__file__).resolve().parents[3]
    schema_path = repo_root / "data-schemas" / "events" / "nlp.extracted.schema.json"
    schema = json.loads(schema_path.read_text())
    return Draft7Validator(schema)


def _ensure_topic(topic: str) -> None:
    admin = None
    try:
        admin = KafkaAdminClient(bootstrap_servers=settings.kafka_bootstrap)
        admin.create_topics([NewTopic(topic, num_partitions=1, replication_factor=1)])
    except TopicAlreadyExistsError:
        pass
    except Exception as exc:  # pragma: no cover - infra dependent
        logger.warning("topic_creation_failed", topic=topic, error=str(exc))
    finally:
        if admin is not None:
            try:
                admin.close()
            except Exception:  # pragma: no cover
                pass


def stop_consumer() -> None:
    _shutdown_event.set()


def run_consumer() -> None:
    _ensure_topic(settings.topic_out)
    consumer = KafkaConsumer(
        settings.topic_in,
        bootstrap_servers=settings.kafka_bootstrap,
        value_deserializer=lambda v: json.loads(v.decode("utf-8")),
        enable_auto_commit=False,
        auto_offset_reset="earliest",
        group_id="nlp-service",
    )
    producer = KafkaProducer(
        bootstrap_servers=settings.kafka_bootstrap,
        key_serializer=lambda v: v.encode("utf-8"),
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        linger_ms=50,
        retries=5,
        acks="all",
    )

    validator = _load_schema()

    while not _shutdown_event.is_set():
        message = consumer.poll(timeout_ms=500)
        if not message:
            continue
        for records in message.values():
            for record in records:
                evt = record.value
                doc_id = evt.get("document_id")
                norm_path = evt.get("normalized_s3_path")
                if not (doc_id and norm_path):
                    logger.warning("skipping_event_missing_keys", event=evt)
                    MESSAGES_COUNTER.labels(status="skipped").inc()
                    consumer.commit()
                    continue

                _, _, bucket_key = norm_path.partition("s3://")
                bucket, _, key = bucket_key.partition("/")

                try:
                    payload = json.loads(get_bytes(bucket, key))
                    text = payload.get("text", "")[:2_000_000]
                    source_url = payload.get("source_url")
                    entities = extract_entities(text)
                    out = {
                        "event_id": str(uuid.uuid4()),
                        "document_id": doc_id,
                        "source_url": source_url,
                        "timestamp": _now_iso(),
                        "entities": entities,
                    }
                    validator.validate(out)
                    producer.send(settings.topic_out, key=doc_id, value=out)
                    remaining = producer.flush(timeout=1.0)
                    if remaining > 0:
                        logger.error(
                            "kafka_flush_incomplete",
                            remaining=remaining,
                            document_id=doc_id,
                        )
                        MESSAGES_COUNTER.labels(status="error").inc()
                        continue
                    logger.info(
                        "nlp_extracted", document_id=doc_id, entity_count=len(entities)
                    )
                    MESSAGES_COUNTER.labels(status="success").inc()
                    consumer.commit()
                except (ValidationError, KafkaTimeoutError) as exc:
                    logger.error(
                        "nlp_validation_or_kafka_error",
                        document_id=doc_id,
                        error=str(exc),
                    )
                    MESSAGES_COUNTER.labels(status="error").inc()
                except Exception as exc:  # pragma: no cover - requires infra
                    logger.exception(
                        "nlp_processing_error", document_id=doc_id, error=str(exc)
                    )
                    MESSAGES_COUNTER.labels(status="error").inc()
    consumer.close()
    producer.close()
