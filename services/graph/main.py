from __future__ import annotations

import logging
import threading

import structlog
from app.config import settings
from app.consumer import run_consumer, stop_consumer
from app.neo4j_utils import close_driver, driver
from app.routes import router
from fastapi import FastAPI

CONSTRAINTS = [
    "CREATE CONSTRAINT doc_id IF NOT EXISTS FOR (d:Document) REQUIRE d.id IS UNIQUE",
    "CREATE CONSTRAINT prov_pid IF NOT EXISTS FOR (p:Provision) REQUIRE p.pid IS UNIQUE",
    "CREATE CONSTRAINT thr_pid IF NOT EXISTS FOR (t:Threshold) REQUIRE t.pid IS UNIQUE",
    "CREATE CONSTRAINT jur_name IF NOT EXISTS FOR (j:Jurisdiction) REQUIRE j.name IS UNIQUE",
    "CREATE INDEX concept_name IF NOT EXISTS FOR (c:Concept) ON (c.name)",
]


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

app = FastAPI(title="Graph Interface", version="0.2.0")
app.include_router(router)


def _ensure_constraints() -> None:
    with driver().session() as session:
        for statement in CONSTRAINTS:
            session.run(statement)


@app.on_event("startup")
def _startup() -> None:
    _ensure_constraints()
    thread = threading.Thread(target=run_consumer, daemon=True)
    thread.start()


@app.on_event("shutdown")
def _shutdown() -> None:
    stop_consumer()
    close_driver()
