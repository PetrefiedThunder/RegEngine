"""FastAPI application entrypoint for the diff service."""

from __future__ import annotations

import logging
import os
import sys

import structlog
from app.auth_routes import router as auth_router
from app.config import get_settings
from app.routes import router
from fastapi import FastAPI

# Add common module to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../common"))
from rate_limit import get_rate_limiter


def _configure_logging(level: str) -> None:
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.add_log_level,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, level.upper(), logging.INFO)
        ),
        cache_logger_on_first_use=True,
    )
    logging.basicConfig(level=getattr(logging, level.upper(), logging.INFO))


settings = get_settings()
_configure_logging(settings.log_level)

app = FastAPI(
    title="RegEngine Diff Service",
    version="2.0.0",
    description="Regulatory document comparison and change detection service",
)

# Add rate limiting middleware (50 requests per minute for compute-intensive service)
rate_limiter = get_rate_limiter(limit=50, window=60)
app.middleware("http")(rate_limiter.rate_limit_middleware)

app.include_router(auth_router)
app.include_router(router)
