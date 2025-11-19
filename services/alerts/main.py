"""Alert Service - Send notifications on regulatory changes"""

from __future__ import annotations

import logging
import os
import sys

import structlog
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
    title="RegEngine Alert Service",
    version="2.0.0",
    description="Regulatory change alert and notification service",
)

# Add rate limiting
rate_limiter = get_rate_limiter(limit=100, window=60)
app.middleware("http")(rate_limiter.rate_limit_middleware)

app.include_router(router)
