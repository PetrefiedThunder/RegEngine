# Regulatory Engine Monorepo

This repository provides a runnable scaffold for a regulatory intelligence platform covering ingestion, NLP extraction, graph persistence, opportunity surfacing, API key administration, and checklist-style compliance validation. It packages multiple Python microservices alongside local infrastructure, JSON Schemas, Terraform stubs, CI, and a Makefile workflow.

## Architecture Overview

- **Admin API** – FastAPI service for API key lifecycle management (create/list/revoke) secured by an `X-Admin-Key` master credential.
- **Ingestion Service** – Fetches regulatory documents, performs OCR-assisted normalization with content-addressed storage, and emits deterministic Kafka events keyed by document and content hash. All ingestion endpoints require a valid `X-RegEngine-API-Key`.
- **NLP Service** – Subscribes to normalized events, validates artifacts, extracts obligations/thresholds/jurisdictions with normalized units, and publishes structured entities with provenance offsets.
- **Graph Interface** – Consumes NLP outputs and upserts a bitemporal-friendly graph model into Neo4j.
- **Opportunity API** – Exposes heuristics for regulatory arbitrage and compliance gaps with inline provenance.
- **Compliance Checklist API** – Standalone FastAPI app (`services/compliance`) that loads reusable checklists from `industry_plugins/` and returns pass/fail validation details for customer configurations.
- **Shared Auth + Plugins** – `shared/auth.py` centralizes API key enforcement/rate limiting while `industry_plugins/` holds example energy, finance, gaming, healthcare, and technology checklists used by the compliance engine.
- **Local Infrastructure** – LocalStack (S3), Redpanda (Kafka), and Neo4j wired together via `docker-compose`.

## Repository Layout

```
infra/                 # Terraform stubs for cloud infrastructure
services/              # Ingestion, NLP, Graph, Opportunity, Admin, Compliance services
  admin/               # API key management service
  ingestion/
  nlp/
  graph/
  opportunity/
  compliance/
data-schemas/          # JSON Schemas for documents and events
industry_plugins/      # Multi-industry compliance checklist definitions
shared/                # Shared modules (auth helpers, etc.)
scripts/               # Developer helper scripts (API key bootstrap, secrets)
.github/workflows/     # CI pipeline for lint and smoke tests
docker-compose.yml     # Local stack orchestration
Makefile               # Developer workflow helpers
```

## Quick Start (Local)

1. Start the stack (FastAPI services + data stores):
   ```bash
   make up  # wraps docker-compose up --build -d
   ```
2. Initialize S3 buckets on LocalStack (required for ingestion/NLP pipelines):
   ```bash
   make init-local
   ```
3. Bootstrap demo API keys via the Admin API once the containers are healthy:
   ```bash
   bash scripts/init-demo-keys.sh
   source .api-keys  # exports DEMO_KEY + ADMIN_KEY for your shell
   ```
4. Trigger a sample ingestion using the issued key:
   ```bash
   curl -sS -X POST http://localhost:8000/ingest/url \
     -H 'Content-Type: application/json' \
     -H "X-RegEngine-API-Key: $DEMO_KEY" \
     -d '{"url":"https://www.federalregister.gov/api/v1/documents/2023-12345.json","source_system":"Federal Register"}' | jq .
   ```
5. Inspect outputs:
   - Kafka topic: `make consume-normalized`
   - Neo4j Browser: http://localhost:7474 (neo4j / change-me-in-production)
   - Service health: `http://localhost:{8000,8100,8200,8300,8400}/health`
   - Prometheus metrics: `http://localhost:{8000,8100,8200,8300,8400}/metrics`
6. Run the compliance checklist API locally if desired:
   ```bash
   uvicorn services.compliance.main:app --reload --port 8500
   ```

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

## API Key Management

All non-health endpoints (including ingestion, NLP callbacks, graph reads, opportunity queries, and checklist validation) require the `X-RegEngine-API-Key` header. Keys are stored in-memory for local development and enforced through `shared/auth.py` with rolling 60-second rate limits.

Use the Admin API on http://localhost:8400 to manage credentials:

```bash
# Create a new key (requires the ADMIN_MASTER_KEY via X-Admin-Key)
curl -X POST http://localhost:8400/admin/keys \
  -H 'Content-Type: application/json' \
  -H 'X-Admin-Key: dev-admin-key-change-in-production' \
  -d '{
        "name": "Partner Sandbox",
        "rate_limit_per_minute": 250,
        "scopes": ["read", "ingest"]
      }'
```

The helper script `scripts/init-demo-keys.sh` automatically creates a demo (100 req/min) and admin (1000 req/min) key and saves both values to `.api-keys` for local testing. See `AUTHENTICATION.md` for the full workflow, scope definitions, and production hardening guidance.

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
- Admin and opportunity APIs enforce API keys with rolling rate limits, while the compliance engine reuses the same guardrail for checklist access.

## Compliance Checklist API Highlights

- Loads reusable checklist definitions for energy, finance, gaming, healthcare, and technology from `industry_plugins/`.
- Endpoints include `/checklists`, `/checklists/{checklist_id}`, `/validate`, `/industries`, and `/examples/*`, all protected by `X-RegEngine-API-Key`.
- Validation responses include per-requirement PASS/FAIL/WARNING statuses, remediation notes, and next steps suitable for sharing with customers.
- Run locally on port 8500 via `uvicorn services.compliance.main:app --port 8500 --reload` or package it into your own deployment target.

## Next Steps

- Continue to replace deterministic NLP extractors with model-driven approaches.
- Extend graph writes with full bi-temporal history (`tx_to`, `valid_to`).
- Harden the API key store (Redis/Postgres) and request validation layers for production.
