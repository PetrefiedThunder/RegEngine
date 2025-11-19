"""API routes for the ingestion service."""

from __future__ import annotations

import json
import logging
import socket
import sys
import time
import uuid
from datetime import datetime, timezone
from ipaddress import ip_address, ip_network
from pathlib import Path
from typing import Iterable
from urllib.parse import urlparse

import requests
import structlog
from fastapi import APIRouter, Header, HTTPException
from fastapi.responses import PlainTextResponse
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from requests import Response

# Add shared module to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "shared"))
from auth import APIKey, require_api_key

from .config import get_settings
from .kafka_utils import send
from .models import IngestRequest, NormalizedDocument, NormalizedEvent
from .normalization import normalize_document
from .s3_utils import put_bytes, put_json

logger = structlog.get_logger("ingestion")
router = APIRouter()

ALLOWED_SCHEMES = {"https", "http"}
ALLOWED_PORTS = {80, 443, 8080, 8443}
PROHIBITED_HOSTS = {"localhost", "127.0.0.1"}
PROHIBITED_NETWORKS = [
    ip_network("10.0.0.0/8"),
    ip_network("172.16.0.0/12"),
    ip_network("192.168.0.0/16"),
    ip_network("127.0.0.0/8"),
    ip_network("169.254.0.0/16"),
    ip_network("::1/128"),
    ip_network("fc00::/7"),
]
MAX_PAYLOAD_BYTES = 25 * 1024 * 1024

REQUEST_COUNTER = Counter(
    "ingestion_requests_total", "Total ingestion requests", ["endpoint", "status"]
)
REQUEST_LATENCY = Histogram(
    "ingestion_request_latency_seconds", "Ingestion request latency", ["endpoint"]
)
KAFKA_COUNTER = Counter(
    "ingestion_kafka_messages_total", "Kafka messages produced", ["topic"]
)


@router.get("/health")
def health() -> dict[str, str]:
    """Health-check endpoint."""

    return {"status": "ok"}


@router.get("/metrics")
def metrics() -> PlainTextResponse:
    return PlainTextResponse(generate_latest(), media_type=CONTENT_TYPE_LATEST)


def _verify_api_key(x_api_key: str | None = Header(None)) -> None:
    """Verify API key if configured."""
    settings = get_settings()
    if settings.api_key is not None:
        if not x_api_key or x_api_key != settings.api_key:
            raise HTTPException(status_code=401, detail="Invalid or missing API key")


@router.post("/ingest/url", response_model=NormalizedEvent)
def ingest_url(
    payload: IngestRequest, x_api_key: str | None = Header(None)
) -> NormalizedEvent:
    """Fetch content from the given URL, normalize it, and emit an event."""

    _verify_api_key(x_api_key)
    start_time = time.perf_counter()
    endpoint = "/ingest/url"
    _validate_url(payload.url)
    settings = get_settings()

    try:
        response = _fetch(payload.url)
        raw_bytes = response.content
        _enforce_size_limit(raw_bytes)

        content_type = response.headers.get("Content-Type", "application/octet-stream")
        raw_json = None
        if "json" in content_type.lower():
            try:
                raw_json = response.json()
            except json.JSONDecodeError as exc:  # pragma: no cover - network dependent
                logger.error("failed_to_parse_json", url=payload.url, error=str(exc))
                raise HTTPException(
                    status_code=422, detail="Response is not valid JSON"
                ) from exc
        if raw_json is not None:
            raw_json["source_system"] = payload.source_system

        normalized, document_id, content_hash = normalize_document(
            raw_json, raw_bytes, payload.url, content_type
        )

        timestamp = datetime.now(timezone.utc)
        event_id = str(uuid.uuid4())

        raw_extension = _detect_extension(content_type)
        raw_key = f"raw/{document_id}/{event_id}.{raw_extension}"
        normalized_key = f"normalized/{content_hash}/current.json"
        normalized_alias_key = f"normalized/by-document-id/{document_id}/current.json"

        raw_uri = put_bytes(settings.raw_bucket, raw_key, raw_bytes)
        normalized_payload = NormalizedDocument(**normalized)
        normalized_uri = put_json(
            settings.processed_bucket,
            normalized_key,
            normalized_payload.model_dump(mode="json"),
        )
        # Maintain a document-centric alias for UX
        put_json(
            settings.processed_bucket,
            normalized_alias_key,
            normalized_payload.model_dump(mode="json"),
        )

        event = NormalizedEvent(
            event_id=event_id,
            document_id=document_id,
            source_system=payload.source_system,
            source_url=payload.url,
            raw_s3_path=raw_uri,
            normalized_s3_path=normalized_uri,
            timestamp=timestamp,
            content_sha256=content_hash,
        )

        send(
            settings.kafka_topic_normalized,
            event.model_dump(mode="json"),
            key=f"{document_id}:{content_hash}",
        )
        logger.info(
            "normalized_event_emitted",
            document_id=document_id,
            content_sha256=content_hash,
        )
        KAFKA_COUNTER.labels(topic=settings.kafka_topic_normalized).inc()
        REQUEST_COUNTER.labels(endpoint=endpoint, status="200").inc()
        REQUEST_LATENCY.labels(endpoint=endpoint).observe(
            time.perf_counter() - start_time
        )
        return event
    except HTTPException as exc:
        REQUEST_COUNTER.labels(endpoint=endpoint, status=str(exc.status_code)).inc()
        REQUEST_LATENCY.labels(endpoint=endpoint).observe(
            time.perf_counter() - start_time
        )
        raise
    except Exception as exc:  # pragma: no cover - requires infra
        logger.exception("ingest_unexpected_error", error=str(exc))
        REQUEST_COUNTER.labels(endpoint=endpoint, status="500").inc()
        REQUEST_LATENCY.labels(endpoint=endpoint).observe(
            time.perf_counter() - start_time
        )
        raise HTTPException(status_code=500, detail="Ingestion failed") from exc


def _fetch(url: str) -> Response:
    parsed = urlparse(url)
    host = parsed.hostname
    if not host:
        raise HTTPException(status_code=400, detail="Invalid URL")

    # Resolve and validate IP addresses immediately before fetch to prevent TOCTOU
    addresses = _resolve_and_validate(host)
    if not addresses:
        raise HTTPException(status_code=400, detail="No valid addresses for host")

    try:
        response = requests.get(
            url,
            timeout=10,
            allow_redirects=True,
            max_redirects=3,
        )
    except requests.RequestException as exc:  # pragma: no cover - network dependent
        logger.error("ingest_fetch_failed", url=url, error=str(exc))
        raise HTTPException(
            status_code=502, detail="Failed to fetch source URL"
        ) from exc

    # Validate the actual IP connected to prevent DNS rebinding
    try:
        if response.raw and hasattr(response.raw, "_connection"):
            conn = response.raw._connection
            if hasattr(conn, "sock") and conn.sock:
                peer_addr = conn.sock.getpeername()[0]
                peer_ip = ip_address(peer_addr)
                if any(peer_ip in network for network in PROHIBITED_NETWORKS):
                    raise HTTPException(
                        status_code=400, detail="Connection to prohibited network detected"
                    )
    except (AttributeError, OSError):
        # If we can't validate post-connection, log warning but allow
        # since pre-validation already occurred
        logger.warning("unable_to_validate_peer_address", url=url)

    if response.status_code >= 400:
        logger.warning("ingest_fetch_status", url=url, status=response.status_code)
        raise HTTPException(status_code=502, detail="Source system returned error")

    return response


def _validate_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in ALLOWED_SCHEMES:
        raise HTTPException(status_code=400, detail="Unsupported URL scheme")

    # Block URLs with embedded credentials to prevent credential leakage
    if parsed.username or parsed.password:
        raise HTTPException(status_code=400, detail="URLs with credentials not allowed")

    host = parsed.hostname
    if not host:
        raise HTTPException(status_code=400, detail="Invalid URL")
    if host.lower() in PROHIBITED_HOSTS:
        raise HTTPException(status_code=400, detail="Host not allowed")

    # Validate port to prevent access to internal services
    port = parsed.port
    if port is None:
        port = 443 if parsed.scheme == "https" else 80
    if port not in ALLOWED_PORTS:
        raise HTTPException(status_code=400, detail="Port not allowed")

    _resolve_and_validate(host)


def _resolve_and_validate(host: str) -> set[str]:
    """Resolve hostname and validate all IPs are not in prohibited networks."""
    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror as exc:  # pragma: no cover - depends on DNS
        logger.error("dns_resolution_failed", host=host, error=str(exc))
        raise HTTPException(status_code=400, detail="Failed to resolve host") from exc

    addresses = {info[4][0] for info in infos if info[4]}
    for addr in addresses:
        ip = ip_address(addr)
        if any(ip in network for network in PROHIBITED_NETWORKS):
            raise HTTPException(
                status_code=400, detail="Host resolved to a private network"
            )

    return addresses


def _enforce_size_limit(raw_bytes: bytes) -> None:
    if len(raw_bytes) > MAX_PAYLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Payload exceeds size limits")


def _detect_extension(content_type: str | None) -> str:
    if not content_type:
        return "bin"
    if "json" in content_type.lower():
        return "json"
    if "pdf" in content_type.lower():
        return "pdf"
    if "text" in content_type.lower():
        return "txt"
    return "bin"
