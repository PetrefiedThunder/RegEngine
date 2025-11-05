from __future__ import annotations

import logging

import structlog
from fastapi import FastAPI

from app.config import settings
from app.neo4j_utils import close_driver
from app.routes import router


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

app = FastAPI(title="Opportunity API", version="0.2.0")
app.include_router(router)


@app.on_event("shutdown")
def _shutdown() -> None:
    close_driver()
