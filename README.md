# Regulatory Engine Monorepo

This repository provides a runnable scaffold for a regulatory intelligence platform covering ingestion, NLP extraction, graph persistence, and opportunity surfacing. It packages four Python microservices alongside local infrastructure, JSON Schemas, Terraform stubs, CI, and a Makefile workflow.

## Architecture Overview

- **Ingestion Service** – Fetches regulatory documents, performs OCR-assisted normalization with content-addressed storage, and emits deterministic Kafka events keyed by document and content hash.
- **NLP Service** – Subscribes to normalized events, validates artifacts, extracts obligations/thresholds/jurisdictions with normalized units, and publishes structured entities with provenance offsets.
- **Graph Interface** – Consumes NLP outputs and upserts a bitemporal-friendly graph model into Neo4j.
- **Opportunity API** – Exposes heuristics for regulatory arbitrage and compliance gaps with inline provenance.
- **Local Infrastructure** – LocalStack (S3), Redpanda (Kafka), and Neo4j wired together via `docker-compose`.

## Repository Layout

```
infra/                 # Terraform stubs for cloud infrastructure
services/              # Ingestion, NLP, Graph, and Opportunity services
  ingestion/
  nlp/
  graph/
  opportunity/
data-schemas/          # JSON Schemas for documents and events
.github/workflows/     # CI pipeline for lint and smoke tests
docker-compose.yml     # Local stack orchestration
Makefile               # Developer workflow helpers
```

## Quick Start (Local)

1. Start the stack:
   ```bash
   docker-compose up --build -d
   ```
2. Initialize S3 buckets on LocalStack:
   ```bash
   make init-local
   ```
3. Trigger a sample ingestion:
   ```bash
   make smoke-ingest
   ```
4. Inspect outputs:
   - Kafka topic: `make consume-normalized`
   - Neo4j Browser: http://localhost:7474 (neo4j / letmein)
   - Service health: `http://localhost:{8000,8100,8200,8300}/health`
- Prometheus metrics: `http://localhost:{8000,8100,8200,8300}/metrics`

## Opportunity API Query Parameters

The Opportunity API exposes two primary endpoints at `/opportunities/arbitrage` and `/opportunities/gaps`. Useful query parameters include:

- `since` (arbitrage): Epoch-millisecond timestamp that restricts arbitrage comparisons to provisions observed on or after the provided instant. Omit the parameter to analyze the full history.
- `j1`, `j2` (gaps/arbitrage): Jurisdiction filters to scope results to specific regions.
- `concept`: Optional concept name filter for arbitrage to focus on a single regulatory topic.
- `limit`: Maximum number of rows to return (arbitrage).

Example:

```bash
curl -s "http://localhost:8300/opportunities/arbitrage?j1=United%20States&j2=European%20Union&since=$(($(date -u +%s)-604800))000" | jq .
```

## Continuous Integration

GitHub Actions (`ci` workflow) performs formatting checks with Black/Isort and runs the service smoke tests across all four services on pushes and pull requests.

## GitHub Repository Creation

Using GitHub CLI:

```bash
git init -b main
git add .
git commit -m "feat: monorepo scaffold"
gh repo create regulatory-engine --public --source . --remote origin --push
```

Alternatively, create a repository manually on GitHub and push via HTTPS/SSH as desired.

## Security & Observability Highlights

- URL ingestion enforces SSRF-safe host resolution, size caps (25 MiB), and content-type allowlisting.
- Normalized artifacts are stored under `normalized/<sha256>/current.json` with document aliases for deterministic replays.
- OCR fallback uses pdfminer first and Tesseract + pdf2image as a secondary path, preserving per-page offset metadata.
- Every service exposes `/metrics` with Prometheus counters/histograms and structured JSON logs via structlog.

## Next Steps

- Replace the deterministic NLP extractor with a model-driven approach.
- Extend graph writes with full bi-temporal history (`tx_to`, `valid_to`).
- Harden APIs with authentication and request validation suited for production.
