"""Smoke tests for diff service."""

from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_health():
    """Test health endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
