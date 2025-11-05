"""Pydantic models used by the ingestion API."""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, HttpUrl


class IngestRequest(BaseModel):
    """Request payload for URL ingestion."""

    url: HttpUrl
    source_system: str = Field(..., min_length=1, max_length=200)


class PositionMapEntry(BaseModel):
    """Mapping from normalized text offsets back to source artifacts."""

    page: int = Field(..., ge=1)
    char_start: int = Field(..., ge=0)
    char_end: int = Field(..., ge=0)
    source_start: Optional[int] = Field(default=None, ge=0)
    source_end: Optional[int] = Field(default=None, ge=0)


class TextExtractionMetadata(BaseModel):
    """Metadata about the text extraction process."""

    engine: str
    confidence_mean: float = Field(..., ge=0.0, le=1.0)
    confidence_std: float = Field(..., ge=0.0, le=1.0)


class NormalizedDocument(BaseModel):
    """Schema for normalized regulatory document payloads."""

    document_id: str
    source_url: HttpUrl
    source_system: str
    retrieved_at: datetime
    text: str
    title: Optional[str] = None
    jurisdiction: Optional[str] = None
    position_map: Optional[List[PositionMapEntry]] = None
    text_extraction: Optional[TextExtractionMetadata] = None
    content_sha256: str
    content_type: Optional[str] = None


class NormalizedEvent(BaseModel):
    """Kafka event emitted after normalization."""

    event_id: str
    document_id: str
    source_system: str
    source_url: HttpUrl
    raw_s3_path: str
    normalized_s3_path: str
    timestamp: datetime
    content_sha256: str
