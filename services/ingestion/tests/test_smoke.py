"""Smoke tests for the ingestion service."""

import pytest

pytest.importorskip("fastapi")

from fastapi.testclient import TestClient

from services.ingestion.main import app


def test_health() -> None:
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
