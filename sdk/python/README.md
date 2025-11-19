# RegEngine Python SDK

Official Python client for RegEngine v2 Regulatory Intelligence Platform.

## Installation

```bash
pip install regengine
```

## Quick Start

```python
from regengine import RegEngineClient

# Initialize client
client = RegEngineClient(
    base_url="https://api.regengine.io",
    username="admin",
    password="your-password"
)

# Ingest document
result = client.ingest(
    url="https://www.sec.gov/rules/final/2023/33-11143.pdf",
    source_system="SEC"
)
print(f"Document ID: {result['document_id']}")

# Query regulatory arbitrage
opportunities = client.opportunities.arbitrage(j1="US", j2="EU")
for opp in opportunities['items']:
    print(f"Concept: {opp['concept']}, Delta: {opp['v2'] - opp['v1']}")

# Compare documents
diff = client.diff.compare("doc1-id", "doc2-id")
print(diff['summary'])
```

## Documentation

See [docs.regengine.io](https://docs.regengine.io) for complete documentation.
