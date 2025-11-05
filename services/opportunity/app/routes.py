from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Optional

import structlog
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import PlainTextResponse
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

from .neo4j_utils import CYPHER_GAP, build_arbitrage_query, get_driver

router = APIRouter()
logger = structlog.get_logger("opportunity-api")

REQUEST_COUNTER = Counter(
    "opportunity_requests_total", "Opportunity API requests", ["endpoint", "status"]
)
REQUEST_LATENCY = Histogram(
    "opportunity_request_latency_seconds", "Opportunity API latency", ["endpoint"]
)


@router.get("/health")
def health():
    return {"status": "ok"}


@router.get("/metrics")
def metrics():
    return PlainTextResponse(generate_latest(), media_type=CONTENT_TYPE_LATEST)


def _to_epoch_millis(value: datetime) -> int:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    else:
        value = value.astimezone(timezone.utc)
    return int(value.timestamp() * 1000)


@router.get("/opportunities/arbitrage")
def arbitrage(
    j1: Optional[str] = None,
    j2: Optional[str] = None,
    concept: Optional[str] = None,
    rel_delta: float = Query(0.2, ge=0.0, le=1.0),
    limit: int = Query(50, ge=1, le=200),
    since: Optional[datetime] = Query(None),
):
    endpoint = "/opportunities/arbitrage"
    start = time.perf_counter()
    try:
        since_ms = _to_epoch_millis(since) if since else None
        query = build_arbitrage_query(
            j1, j2, concept, include_since=since_ms is not None
        )
        params = {"rel_delta": rel_delta, "limit": limit}
        if j1 and j2:
            params["j1"] = j1
            params["j2"] = j2
        if concept:
            params["concept"] = concept
        if since_ms is not None:
            params["since"] = since_ms
        with get_driver().session() as session:
            result = session.run(query, params, timeout=5)
            items = [
                {
                    "concept": record["concept"],
                    "unit": record["unit"],
                    "v1": record["v1"],
                    "v2": record["v2"],
                    "text1": record["text1"],
                    "text2": record["text2"],
                    "citation_1": {
                        "doc_id": record["doc_id_1"],
                        "start": record["start_1"],
                        "end": record["end_1"],
                        "source_url": record["source_url_1"],
                    },
                    "citation_2": {
                        "doc_id": record["doc_id_2"],
                        "start": record["start_2"],
                        "end": record["end_2"],
                        "source_url": record["source_url_2"],
                    },
                }
                for record in result
            ]
        REQUEST_COUNTER.labels(endpoint=endpoint, status="200").inc()
        REQUEST_LATENCY.labels(endpoint=endpoint).observe(time.perf_counter() - start)
        return {"items": items}
    except Exception as exc:  # pragma: no cover - requires infra
        logger.exception("arbitrage_query_failed", error=str(exc))
        REQUEST_COUNTER.labels(endpoint=endpoint, status="500").inc()
        REQUEST_LATENCY.labels(endpoint=endpoint).observe(time.perf_counter() - start)
        raise HTTPException(status_code=500, detail="Arbitrage query failed") from exc


@router.get("/opportunities/gaps")
def gaps(
    j1: str = Query(...),
    j2: str = Query(...),
    limit: int = Query(50, ge=1, le=200),
):
    endpoint = "/opportunities/gaps"
    start = time.perf_counter()
    try:
        with get_driver().session() as session:
            result = session.run(
                CYPHER_GAP, {"j1": j1, "j2": j2, "limit": limit}, timeout=5
            )
            items = [
                {
                    "concept": record["concept"],
                    "example_text": record["example_text"],
                    "citation": {
                        "doc_id": record["doc_id"],
                        "start": record["start"],
                        "end": record["end"],
                        "source_url": record["source_url"],
                    },
                }
                for record in result
            ]
        REQUEST_COUNTER.labels(endpoint=endpoint, status="200").inc()
        REQUEST_LATENCY.labels(endpoint=endpoint).observe(time.perf_counter() - start)
        return {"items": items}
    except Exception as exc:  # pragma: no cover - requires infra
        logger.exception("gap_query_failed", error=str(exc))
        REQUEST_COUNTER.labels(endpoint=endpoint, status="500").inc()
        REQUEST_LATENCY.labels(endpoint=endpoint).observe(time.perf_counter() - start)
        raise HTTPException(status_code=500, detail="Gap query failed") from exc
