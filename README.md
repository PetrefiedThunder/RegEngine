# RegEngine v2 🚀

**Regulatory Intelligence Infrastructure**

[![CI](https://github.com/PetrefiedThunder/RegEngine/actions/workflows/ci.yml/badge.svg)](https://github.com/PetrefiedThunder/RegEngine/actions/workflows/ci.yml)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115.0-green.svg)](https://fastapi.tiangolo.com/)

> *Automatically detect regulatory changes, impacts, and opportunities across jurisdictions with clause-level provenance, ML scoring, and temporal graph analytics.*

---

## 📋 Table of Contents

- [Overview](#overview)
- [Key Features](#key-features)
- [Quick Start](#quick-start)
- [Architecture](#architecture)
- [API Documentation](#api-documentation)
- [Use Cases](#use-cases)
- [Development](#development)
- [Deployment](#deployment)

---

## 🎯 Overview

**RegEngine v2** is an end-to-end regulatory intelligence platform that helps organizations:

- 🔍 **Monitor** regulatory changes across 100+ jurisdictions
- 📊 **Analyze** compliance gaps and arbitrage opportunities
- ⏰ **Track** temporal changes with full historical lineage
- 🤖 **Automate** entity extraction using ML-based NLP
- 🔔 **Alert** stakeholders to relevant regulatory updates

### Target Industries

- **Healthcare** - HIPAA compliance, patient data privacy
- **Financial Services** - SEC, FDIC, Federal Reserve regulations
- **Pharmaceuticals** - FDA drug safety and efficacy
- **Transportation** - FAA, DOT safety standards
- **Energy & Utilities** - EPA environmental compliance
- **Technology** - GDPR, data privacy regulations
- **Food & Beverage** - FDA food safety standards

---

## ✨ Key Features

### 1. **Secure Document Ingestion**
- Multi-format support (PDF, DOCX, HTML, XML)
- SSRF-safe URL fetching
- OCR fallback for scanned documents
- Content-addressed deduplication

### 2. **ML-Based Entity Extraction**
- Legal-BERT framework for domain-specific understanding
- Extract obligations, thresholds, jurisdictions, penalties
- Confidence scoring (0.7-0.95)
- Intent classification

### 3. **Temporal Graph Storage**
- Neo4j bitemporal model (`tx_from/tx_to`, `valid_from/valid_to`)
- Full provision versioning with `SUPERSEDES` relationships
- Historical queries ("what was active at time T?")

### 4. **Regulatory Diff Engine**
- Clause-level document comparison
- Threshold change detection with % delta
- Human-readable summaries

### 5. **Opportunity Detection**
- **Arbitrage**: Find threshold inconsistencies across jurisdictions
- **Compliance Gaps**: Identify missing obligations

### 6. **Production Security**
- JWT authentication with scope-based access control
- Redis-based rate limiting (100-200 req/min)
- API key support for programmatic access

---

## 🚀 Quick Start

### Prerequisites

- **Docker** >= 20.10
- **Docker Compose** >= 2.0
- **Python** >= 3.11 (for local development)

### 1. Clone Repository

```bash
git clone https://github.com/PetrefiedThunder/RegEngine.git
cd RegEngine
```

### 2. Start Infrastructure

```bash
# Start all services
docker-compose up -d

# Initialize S3 buckets
make init-local
```

### 3. Verify Services

```bash
# Check health endpoints
curl http://localhost:8000/health  # Ingestion Service
curl http://localhost:8300/health  # Opportunity API
curl http://localhost:8400/health  # Diff Engine

# All services running
docker-compose ps
```

### 4. Get Authentication Token

```bash
curl -X POST http://localhost:8000/auth/token \
  -d "username=admin&password=secret" \
  -H "Content-Type: application/x-www-form-urlencoded"
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

Save the token:
```bash
export TOKEN="<your-token-here>"
```

### 5. Ingest Your First Document

```bash
curl -X POST http://localhost:8000/ingest/url \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://www.sec.gov/rules/final/2023/33-11143.pdf",
    "source_system": "SEC"
  }'
```

### 6. Query for Regulatory Arbitrage

```bash
curl "http://localhost:8300/opportunities/arbitrage?j1=US&j2=EU&limit=10" \
  -H "Authorization: Bearer $TOKEN"
```

### 7. Compare Two Documents

```bash
curl -X POST http://localhost:8400/diff \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "doc1_id": "doc-2023-v1",
    "doc2_id": "doc-2024-v2"
  }'
```

---

## 🏗️ Architecture

### Microservices

| Service | Port | Purpose |
|---------|------|---------|
| **Ingestion** | 8000 | Fetch, normalize, store documents |
| **NLP** | 8100 | Extract entities (background worker) |
| **Graph** | 8200 | Persist to Neo4j (background worker) |
| **Opportunity** | 8300 | Query arbitrage & gaps |
| **Diff** | 8400 | Compare documents |

### Infrastructure

| Component | Port | Purpose |
|-----------|------|---------|
| **LocalStack** | 4566 | S3 emulation (dev) |
| **Redpanda** | 9092 | Kafka-compatible messaging |
| **Neo4j** | 7687, 7474 | Graph database |
| **Redis** | 6379 | Rate limiting & caching |

### Data Flow

```
Document URL → Ingestion → S3 (Raw) → Kafka (normalized)
                                ↓
                           NLP Service → Kafka (extracted)
                                ↓
                         Graph Service → Neo4j (temporal graph)
                                ↓
                    Opportunity API / Diff Engine → Insights
```

**See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for detailed diagrams.**

---

## 📚 API Documentation

### Authentication Endpoints

```http
POST /auth/token              # Generate JWT token
GET  /auth/me                 # Get current user info
POST /auth/refresh            # Refresh token
```

### Ingestion Service (Port 8000)

```http
POST /ingest/url              # Ingest document from URL
GET  /health                  # Health check
GET  /metrics                 # Prometheus metrics
```

### Opportunity API (Port 8300)

```http
GET /opportunities/arbitrage  # Detect threshold divergence
    ?j1=US&j2=EU&rel_delta=0.2&limit=50

GET /opportunities/gaps       # Find compliance gaps
    ?j1=EU&j2=US&limit=50
```

### Diff Engine (Port 8400)

```http
POST /diff                    # Compare two documents
GET  /diff/compare            # Compare via query params
    ?doc1_id=X&doc2_id=Y
```

**Full API specs:** See [docs/PRD.md](docs/PRD.md#6-api-specifications)

---

## 💼 Use Cases

### 1. **RegTech SaaS Providers**
Embed RegEngine as a compliance inference engine

### 2. **Legal Research Firms**
Track regulatory changes over time with full provenance

### 3. **Financial Analysts**
Identify cross-border arbitrage opportunities

### 4. **Compliance Teams**
Automate gap analysis across jurisdictions

---

## 🛠️ Development

### Local Development Setup

```bash
# Install Python dependencies
cd services/ingestion
pip install -r requirements.txt

# Run service locally
uvicorn main:app --reload --port 8000
```

### Run Tests

```bash
# Run all tests
make test

# Run specific service tests
cd services/ingestion
pytest -v
```

### Code Formatting

```bash
# Format code with black
make fmt

# Check formatting
black --check services/

# Sort imports
isort services/
```

---

## 🚀 Deployment

### Production Deployment (AWS)

```bash
cd infra
terraform init
terraform apply -var-file=production.tfvars
```

**See [docs/DEPLOYMENT_GUIDE.md](docs/DEPLOYMENT_GUIDE.md) for complete instructions.**

---

## 📖 Documentation

- **[Product Requirements Document](docs/PRD.md)** - Complete feature specs
- **[Architecture Guide](docs/ARCHITECTURE.md)** - System diagrams & data flows
- **[Deployment Guide](docs/DEPLOYMENT_GUIDE.md)** - Local & production setup
- **[Data Dictionary](docs/DATA_DICTIONARY.md)** - Schemas & entity types

---

## ⚡ Quick Commands

```bash
# Start everything
docker-compose up -d

# Stop everything
docker-compose down

# Clean everything (including volumes)
docker-compose down -v

# Rebuild services
docker-compose build

# View service status
docker-compose ps

# Initialize S3 buckets
make init-local

# View Neo4j data
docker exec -it neo4j cypher-shell -u neo4j -p letmein
```

---

## 📞 Support

- **Documentation**: [docs/](docs/)
- **Issues**: [GitHub Issues](https://github.com/PetrefiedThunder/RegEngine/issues)
- **Email**: support@regengine.io

---

## 🗺️ Roadmap

### Q1 2025 ✅ Complete
- [x] Ingestion Service
- [x] NLP Extraction
- [x] Graph Storage (bitemporal)
- [x] JWT Authentication
- [x] Rate Limiting
- [x] Diff Engine

### Q2 2025 🚧 In Progress
- [ ] Legal-BERT model deployment
- [ ] Python SDK
- [ ] TypeScript SDK
- [ ] Web Dashboard
- [ ] Alert Service

---

**Built with ❤️ by the RegEngine Team**

For questions or feedback, please [open an issue](https://github.com/PetrefiedThunder/RegEngine/issues/new).
