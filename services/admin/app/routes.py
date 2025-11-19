"""API routes for the admin service."""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, Header, status
from fastapi.responses import PlainTextResponse
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from pydantic import BaseModel

# Add shared module to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "shared"))
from auth import APIKey, get_key_store

from .config import get_settings

router = APIRouter()
logger = structlog.get_logger("admin")


class CreateKeyRequest(BaseModel):
    """Request model for creating an API key."""

    name: str
    rate_limit_per_minute: int = 60
    expires_at: Optional[datetime] = None
    scopes: list[str] = ["read", "ingest"]


class CreateKeyResponse(BaseModel):
    """Response model for API key creation."""

    api_key: str
    key_id: str
    name: str
    created_at: datetime
    expires_at: Optional[datetime]
    rate_limit_per_minute: int
    scopes: list[str]
    warning: str = "Store this key securely. It will not be shown again."


class APIKeyInfo(BaseModel):
    """API key information (without the raw key)."""

    key_id: str
    name: str
    created_at: datetime
    expires_at: Optional[datetime]
    rate_limit_per_minute: int
    enabled: bool
    scopes: list[str]


async def verify_admin_key(
    x_admin_key: Optional[str] = Header(None, alias="X-Admin-Key"),
) -> bool:
    """Verify the admin master key."""
    settings = get_settings()
    if not x_admin_key or x_admin_key != settings.admin_master_key:
        logger.warning("unauthorized_admin_access_attempt")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid admin credentials",
        )
    return True


@router.get("/health")
def health():
    """Health check endpoint."""
    return {"status": "ok"}


@router.get("/metrics")
def metrics():
    """Prometheus metrics endpoint."""
    return PlainTextResponse(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@router.post("/admin/keys", response_model=CreateKeyResponse)
def create_api_key(
    request: CreateKeyRequest,
    _: bool = Depends(verify_admin_key),
):
    """Create a new API key (requires admin authentication)."""
    key_store = get_key_store()

    raw_key, api_key = key_store.create_key(
        name=request.name,
        rate_limit_per_minute=request.rate_limit_per_minute,
        expires_at=request.expires_at,
        scopes=request.scopes,
    )

    logger.info("api_key_created_via_admin", key_id=api_key.key_id, name=request.name)

    return CreateKeyResponse(
        api_key=raw_key,
        key_id=api_key.key_id,
        name=api_key.name,
        created_at=api_key.created_at,
        expires_at=api_key.expires_at,
        rate_limit_per_minute=api_key.rate_limit_per_minute,
        scopes=api_key.scopes,
    )


@router.get("/admin/keys", response_model=list[APIKeyInfo])
def list_api_keys(
    _: bool = Depends(verify_admin_key),
):
    """List all API keys (requires admin authentication)."""
    key_store = get_key_store()
    keys = key_store.list_keys()

    return [
        APIKeyInfo(
            key_id=key.key_id,
            name=key.name,
            created_at=key.created_at,
            expires_at=key.expires_at,
            rate_limit_per_minute=key.rate_limit_per_minute,
            enabled=key.enabled,
            scopes=key.scopes,
        )
        for key in keys
    ]


@router.delete("/admin/keys/{key_id}")
def revoke_api_key(
    key_id: str,
    _: bool = Depends(verify_admin_key),
):
    """Revoke an API key (requires admin authentication)."""
    key_store = get_key_store()

    if key_store.revoke_key(key_id):
        logger.info("api_key_revoked_via_admin", key_id=key_id)
        return {"status": "revoked", "key_id": key_id}

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="API key not found",
    )
