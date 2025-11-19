from __future__ import annotations

import logging
import os
import sys

import structlog
from app.auth_routes import router as auth_router
from app.config import settings
from app.neo4j_utils import close_driver
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


_configure_logging(settings.log_level)

app = FastAPI(
    title="RegEngine Opportunity API",
    version="2.0.0",
    description="Secure regulatory arbitrage and compliance gap detection API with rate limiting",
)

# Add rate limiting middleware (200 requests per minute for read-heavy service)
rate_limiter = get_rate_limiter(limit=200, window=60)
app.middleware("http")(rate_limiter.rate_limit_middleware)

app.include_router(auth_router)
app.include_router(router)


@app.on_event("shutdown")
def _shutdown() -> None:
    close_driver()
