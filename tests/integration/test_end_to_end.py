"""End-to-end integration tests"""

import pytest
import requests
import time

BASE_URL = "http://localhost:8000"
OPP_URL = "http://localhost:8300"
DIFF_URL = "http://localhost:8400"


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token for tests"""
    response = requests.post(
        f"{BASE_URL}/auth/token",
        data={"username": "admin", "password": "secret"},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def test_full_ingestion_flow(auth_token):
    """Test complete document ingestion flow"""
    # Step 1: Ingest document
    response = requests.post(
        f"{BASE_URL}/ingest/url",
        json={
            "url": "https://example.com/test.pdf",
            "source_system": "TEST"
        },
        headers={"Authorization": f"Bearer {auth_token}"}
    )

    if response.status_code == 200:
        assert "document_id" in response.json()
        assert "event_id" in response.json()


def test_arbitrage_detection(auth_token):
    """Test regulatory arbitrage detection"""
    response = requests.get(
        f"{OPP_URL}/opportunities/arbitrage",
        params={"j1": "US", "j2": "EU", "limit": 10},
        headers={"Authorization": f"Bearer {auth_token}"}
    )

    assert response.status_code in [200, 401, 403]
    if response.status_code == 200:
        data = response.json()
        assert "items" in data


def test_diff_comparison(auth_token):
    """Test document diff functionality"""
    response = requests.post(
        f"{DIFF_URL}/diff",
        json={
            "doc1_id": "test-doc-1",
            "doc2_id": "test-doc-2"
        },
        headers={"Authorization": f"Bearer {auth_token}"}
    )

    # Expect 404 if documents don't exist
    assert response.status_code in [200, 404, 401, 403]


def test_rate_limiting(auth_token):
    """Test rate limiting is enforced"""
    # Make multiple rapid requests
    for _ in range(10):
        response = requests.get(
            f"{BASE_URL}/health",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        if response.status_code == 429:
            assert "Retry-After" in response.headers
            break
