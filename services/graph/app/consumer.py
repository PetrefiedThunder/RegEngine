from __future__ import annotations

import json
import threading

import structlog
from kafka import KafkaConsumer
from kafka.admin import KafkaAdminClient, NewTopic
from kafka.errors import TopicAlreadyExistsError
from prometheus_client import Counter

from .config import settings
from .neo4j_utils import driver, upsert_from_entities

logger = structlog.get_logger("graph-consumer")

MESSAGES_COUNTER = Counter(
    "graph_consumer_messages_total", "Graph consumer messages", ["status"]
)

_shutdown_event = threading.Event()


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
    _ensure_topic(settings.topic_in)
    consumer = KafkaConsumer(
        settings.topic_in,
        bootstrap_servers=settings.kafka_bootstrap,
        value_deserializer=lambda v: json.loads(v.decode("utf-8")),
        enable_auto_commit=True,
        auto_offset_reset="earliest",
        group_id="graph-service",
    )
    with driver().session() as session:
        while not _shutdown_event.is_set():
            message = consumer.poll(timeout_ms=500)
            if not message:
                continue
            for records in message.values():
                for record in records:
                    evt = record.value
                    doc_id = evt.get("document_id")
                    entities = evt.get("entities", [])
                    source_url = evt.get("source_url")
                    if not doc_id:
                        logger.warning("missing_document_id", event=evt)
                        MESSAGES_COUNTER.labels(status="skipped").inc()
                        continue
                    try:
                        upsert_from_entities(session, doc_id, source_url, entities)
                        logger.info(
                            "graph_upsert_ok", doc_id=doc_id, entity_count=len(entities)
                        )
                        MESSAGES_COUNTER.labels(status="success").inc()
                    except Exception as exc:  # pragma: no cover - requires infra
                        logger.exception(
                            "graph_upsert_err", doc_id=doc_id, error=str(exc)
                        )
                        MESSAGES_COUNTER.labels(status="error").inc()
    consumer.close()
