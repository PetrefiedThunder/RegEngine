"""RegEngine SDK Client"""

import requests
from typing import Optional, Dict, Any
from .exceptions import RegEngineError, AuthenticationError, RateLimitError


class RegEngineClient:
    """Main RegEngine SDK client"""

    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        api_key: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
    ):
        """
        Initialize RegEngine client

        Args:
            base_url: Base URL of RegEngine API
            api_key: API key for authentication (alternative to username/password)
            username: Username for JWT auth
            password: Password for JWT auth
        """
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.token = None

        if username and password:
            self._authenticate(username, password)

        self.opportunities = OpportunityClient(self)
        self.diff = DiffClient(self)

    def _authenticate(self, username: str, password: str):
        """Authenticate and get JWT token"""
        response = requests.post(
            f"{self.base_url}/auth/token",
            data={"username": username, "password": password},
        )
        if response.status_code == 200:
            self.token = response.json()["access_token"]
        else:
            raise AuthenticationError("Authentication failed")

    def _get_headers(self) -> Dict[str, str]:
        """Get request headers with authentication"""
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        elif self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def _request(self, method: str, endpoint: str, **kwargs) -> Any:
        """Make authenticated request"""
        url = f"{self.base_url}{endpoint}"
        headers = self._get_headers()

        response = requests.request(method, url, headers=headers, **kwargs)

        if response.status_code == 401:
            raise AuthenticationError("Unauthorized")
        elif response.status_code == 429:
            raise RateLimitError("Rate limit exceeded")
        elif response.status_code >= 400:
            raise RegEngineError(f"API error: {response.text}")

        return response.json() if response.content else None

    def ingest(self, url: str, source_system: str = "API") -> Dict[str, Any]:
        """
        Ingest a document from URL

        Args:
            url: Document URL
            source_system: Source system identifier

        Returns:
            Ingestion result with document_id and event_id
        """
        return self._request(
            "POST",
            "/ingest/url",
            json={"url": url, "source_system": source_system}
        )

    def health(self) -> Dict[str, str]:
        """Check service health"""
        return self._request("GET", "/health")


class OpportunityClient:
    """Opportunity API client"""

    def __init__(self, client: RegEngineClient):
        self.client = client
        self.base_url = client.base_url.replace(":8000", ":8300")

    def arbitrage(
        self,
        j1: Optional[str] = None,
        j2: Optional[str] = None,
        concept: Optional[str] = None,
        rel_delta: float = 0.2,
        limit: int = 50,
    ) -> Dict[str, Any]:
        """
        Detect regulatory arbitrage opportunities

        Args:
            j1: First jurisdiction
            j2: Second jurisdiction
            concept: Filter by concept
            rel_delta: Minimum relative threshold difference
            limit: Max results

        Returns:
            Dict with 'items' list of arbitrage opportunities
        """
        params = {"rel_delta": rel_delta, "limit": limit}
        if j1:
            params["j1"] = j1
        if j2:
            params["j2"] = j2
        if concept:
            params["concept"] = concept

        response = requests.get(
            f"{self.base_url}/opportunities/arbitrage",
            params=params,
            headers=self.client._get_headers(),
        )
        return response.json()

    def gaps(
        self,
        j1: str,
        j2: str,
        limit: int = 50,
    ) -> Dict[str, Any]:
        """
        Find compliance gaps between jurisdictions

        Args:
            j1: Source jurisdiction
            j2: Target jurisdiction
            limit: Max results

        Returns:
            Dict with 'items' list of gaps
        """
        params = {"j1": j1, "j2": j2, "limit": limit}

        response = requests.get(
            f"{self.base_url}/opportunities/gaps",
            params=params,
            headers=self.client._get_headers(),
        )
        return response.json()


class DiffClient:
    """Diff API client"""

    def __init__(self, client: RegEngineClient):
        self.client = client
        self.base_url = client.base_url.replace(":8000", ":8400")

    def compare(self, doc1_id: str, doc2_id: str) -> Dict[str, Any]:
        """
        Compare two documents

        Args:
            doc1_id: First document ID
            doc2_id: Second document ID

        Returns:
            Dict with changes and summary
        """
        response = requests.post(
            f"{self.base_url}/diff",
            json={"doc1_id": doc1_id, "doc2_id": doc2_id},
            headers=self.client._get_headers(),
        )
        return response.json()
