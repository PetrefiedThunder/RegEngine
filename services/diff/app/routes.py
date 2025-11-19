"""API routes for the diff service."""

from __future__ import annotations

import json
import os
import sys
import time

import boto3
import structlog
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import PlainTextResponse
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from pydantic import BaseModel

# Add common module to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../common"))
from auth import User, require_scope

from .config import get_settings
from .diff_engine import compare_documents

logger = structlog.get_logger("diff-api")
router = APIRouter()

REQUEST_COUNTER = Counter(
    "diff_requests_total", "Total diff requests", ["endpoint", "status"]
)
REQUEST_LATENCY = Histogram(
    "diff_request_latency_seconds", "Diff request latency", ["endpoint"]
)


class DiffRequest(BaseModel):
    """Request for document comparison"""

    doc1_id: str
    doc2_id: str
    include_text_diff: bool = True
    include_entity_diff: bool = True


@router.get("/health")
def health() -> dict[str, str]:
    """Health check endpoint"""
    return {"status": "ok"}


@router.get("/metrics")
def metrics() -> PlainTextResponse:
    """Prometheus metrics endpoint"""
    return PlainTextResponse(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@router.post("/diff")
def diff_documents(
    request: DiffRequest,
    current_user: User = Depends(require_scope("diff:read")),
) -> dict:
    """
    Compare two regulatory documents and detect changes.

    Requires authentication with 'diff:read' scope.

    Returns:
        Structured diff with all detected changes
    """
    endpoint = "/diff"
    start_time = time.perf_counter()

    try:
        logger.info(
            "diff_request",
            user=current_user.username,
            doc1=request.doc1_id,
            doc2=request.doc2_id,
        )

        # Fetch documents from S3
        doc1 = _fetch_document(request.doc1_id)
        doc2 = _fetch_document(request.doc2_id)

        if not doc1:
            raise HTTPException(
                status_code=404, detail=f"Document not found: {request.doc1_id}"
            )
        if not doc2:
            raise HTTPException(
                status_code=404, detail=f"Document not found: {request.doc2_id}"
            )

        # Perform comparison
        diff_result = compare_documents(doc1, doc2)

        REQUEST_COUNTER.labels(endpoint=endpoint, status="200").inc()
        REQUEST_LATENCY.labels(endpoint=endpoint).observe(
            time.perf_counter() - start_time
        )

        return diff_result.to_dict()

    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("diff_failed", error=str(exc))
        REQUEST_COUNTER.labels(endpoint=endpoint, status="500").inc()
        REQUEST_LATENCY.labels(endpoint=endpoint).observe(
            time.perf_counter() - start_time
        )
        raise HTTPException(status_code=500, detail="Document comparison failed") from exc


@router.get("/diff/compare")
def compare_by_url(
    doc1_id: str = Query(..., description="First document ID"),
    doc2_id: str = Query(..., description="Second document ID"),
    current_user: User = Depends(require_scope("diff:read")),
) -> dict:
    """
    Compare two documents using query parameters.

    Convenience endpoint for GET-based comparison.
    """
    request = DiffRequest(doc1_id=doc1_id, doc2_id=doc2_id)
    return diff_documents(request, current_user)


def _fetch_document(doc_id: str) -> dict | None:
    """Fetch normalized document from S3"""
    settings = get_settings()

    s3_client = boto3.client(
        "s3",
        endpoint_url=settings.aws_endpoint_url,
        region_name=settings.aws_region,
    )

    # Try to fetch from content-addressed location
    key = f"normalized/by-document-id/{doc_id}/current.json"

    try:
        response = s3_client.get_object(Bucket=settings.processed_bucket, Key=key)
        content = response["Body"].read().decode("utf-8")
        return json.loads(content)
    except s3_client.exceptions.NoSuchKey:
        logger.warning("document_not_found", doc_id=doc_id, key=key)
        return None
    except Exception as exc:
        logger.error("s3_fetch_failed", doc_id=doc_id, error=str(exc))
        return None
