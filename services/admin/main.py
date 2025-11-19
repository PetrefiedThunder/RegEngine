"""FastAPI application entrypoint for the admin service."""

from __future__ import annotations

import logging

import structlog
from app.config import get_settings
from app.routes import router
from fastapi import FastAPI


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
    title="RegEngine Admin API",
    version="0.2.0",
    description="API key management and administration",
)
app.include_router(router)
