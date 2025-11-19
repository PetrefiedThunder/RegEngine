"""RegEngine Python SDK

Official Python client for RegEngine v2 Regulatory Intelligence Platform.

Example usage:
    ```python
    from regengine import RegEngineClient

    client = RegEngineClient(
        base_url="https://api.regengine.io",
        api_key="your-api-key"
    )

    # Ingest document
    result = client.ingest("https://regulations.gov/doc.pdf", source="SEC")

    # Query arbitrage
    opps = client.opportunities.arbitrage(j1="US", j2="EU")

    # Compare documents
    diff = client.diff("doc1-id", "doc2-id")
    ```
"""

from .client import RegEngineClient
from .exceptions import RegEngineError, AuthenticationError, RateLimitError

__version__ = "2.0.0"
__all__ = ["RegEngineClient", "RegEngineError", "AuthenticationError", "RateLimitError"]
