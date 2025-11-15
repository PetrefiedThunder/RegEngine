from __future__ import annotations

import logging
import threading

import structlog
from app.config import settings
from app.consumer import run_consumer, stop_consumer
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


_configure_logging(settings.log_level)

app = FastAPI(title="NLP Service", version="0.2.0")
app.include_router(router)


@app.on_event("startup")
def _start_bg() -> None:  # pragma: no cover - requires infra
    thread = threading.Thread(target=run_consumer, daemon=True)
    thread.start()


@app.on_event("shutdown")
def _shutdown() -> None:
    stop_consumer()
