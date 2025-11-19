# RegEngine v2 - Product Requirements Document

**Version:** 2.0.0
**Date:** 2025-11-18
**Status:** Implementation Complete
**Owner:** RegEngine Platform Team

---

## Executive Summary

**RegEngine v2** is an end-to-end regulatory intelligence infrastructure that automatically ingests, normalizes, extracts meaning from, and analyzes regulatory documents across jurisdictions. The system provides clause-level provenance, ML-based entity extraction, temporal graph storage, regulatory diff detection, and arbitrage opportunity identification.

### Core Value Proposition

> *"Automatically detect regulatory changes, impacts, and opportunities across jurisdictions with clause-level provenance, ML scoring, and temporal graph analytics."*

---

## Table of Contents

1. [Product Vision](#product-vision)
2. [Target Users](#target-users)
3. [System Architecture](#system-architecture)
4. [Feature Specifications](#feature-specifications)
5. [Technical Requirements](#technical-requirements)
6. [API Specifications](#api-specifications)
7. [Security & Compliance](#security--compliance)
8. [Performance Requirements](#performance-requirements)
9. [Deployment Architecture](#deployment-architecture)
10. [Success Metrics](#success-metrics)

---

## 1. Product Vision

### Mission

Empower organizations to stay ahead of regulatory change by providing real-time intelligence on obligations, compliance gaps, and competitive arbitrage opportunities.

### Strategic Goals

1. **Automate Regulatory Monitoring** - Reduce manual compliance tracking by 80%
2. **Enable Proactive Compliance** - Alert users before regulations take effect
3. **Identify Business Opportunities** - Surface regulatory arbitrage and gaps
4. **Provide Temporal Lineage** - Track every regulatory change over time
5. **Scale Globally** - Support 100+ jurisdictions with unified infrastructure

---

## 2. Target Users

### Primary Personas

#### 1. RegTech SaaS Providers
- **Need:** Embeddable regulatory inference engine
- **Use Case:** White-label compliance automation
- **Pricing:** $3k/mo developer → $150k/yr enterprise OEM

#### 2. Legal Research & Law Firms
- **Need:** Temporal regulation diff and provenance tracking
- **Use Case:** Client advisory on regulatory changes
- **Pricing:** $250k/yr + per-seat licensing

#### 3. Financial Analysts & PE Firms
- **Need:** Industry impact assessment and arbitrage detection
- **Use Case:** Investment due diligence and risk modeling
- **Pricing:** $50k–$300k/yr

#### 4. Policy Think Tanks
- **Need:** Cross-jurisdictional comparative analysis
- **Use Case:** Policy research and recommendations
- **Pricing:** Academic/non-profit tiers

#### 5. Government Agencies
- **Need:** Regulatory harmonization and impact analysis
- **Use Case:** Policy alignment across departments
- **Pricing:** Custom enterprise agreements

---

## 3. System Architecture

### High-Level Components

RegEngine v2 consists of **5 core microservices**:

1. **Ingestion Service** (Port 8000)
2. **NLP Extraction Service** (Port 8100)
3. **Graph Service** (Port 8200)
4. **Opportunity API** (Port 8300)
5. **Diff Engine** (Port 8400)

### Data Flow

```
Document URLs → Ingestion → Normalization → NLP Extraction → Graph Storage → Query APIs
                    ↓            ↓               ↓                  ↓
                  S3 Raw    S3 Normalized    Neo4j Graph    Opportunity Engine
                                                                Diff Engine
```

### Technology Stack

- **Framework:** FastAPI 0.115.0 (Python 3.11)
- **Graph Database:** Neo4j 5.24
- **Message Queue:** Redpanda (Kafka-compatible)
- **Object Storage:** AWS S3 / LocalStack
- **Auth:** JWT (python-jose)
- **Rate Limiting:** Redis
- **Observability:** Prometheus + Structlog

---

## 4. Feature Specifications

### 4.1 Document Ingestion

**Requirement:** Securely fetch and normalize regulatory documents from multiple sources.

**Acceptance Criteria:**
- ✅ Support URLs, PDFs, DOCX, HTML, XML
- ✅ SSRF-safe URL validation (block private networks)
- ✅ Size limit enforcement (25 MB max)
- ✅ OCR fallback (Tesseract) for scanned PDFs
- ✅ Content-addressed storage (SHA256-based deduplication)
- ✅ Deterministic Kafka events (`ingest.normalized` topic)

**Endpoints:**
- `POST /ingest/url` - Ingest document from URL

---

### 4.2 NLP Entity Extraction

**Requirement:** Extract regulatory meaning using ML-based models.

**Entities Extracted:**
- **Obligations** - "shall", "must", "required to"
- **Prohibitions** - "shall not", "must not", "prohibited"
- **Thresholds** - Numeric values with units (%, USD, tons, etc.)
- **Jurisdictions** - US, EU, California, etc.
- **Incentives** - Tax credits, grants, subsidies
- **Penalties** - Fines, sanctions, enforcement
- **Deadlines** - Effective dates, expiration dates

**Acceptance Criteria:**
- ✅ Legal-BERT-based extraction (enhanced regex in v2.0)
- ✅ Confidence scoring for each entity
- ✅ Intent classification (obligation vs. permission vs. prohibition)
- ✅ Provenance tracking (char offsets, page numbers)
- ✅ Schema-validated output (`nlp.extracted` topic)

**Models:**
- Legal-BERT (nlpaueb/legal-bert-base-uncased) [planned]
- Enhanced regex with confidence scoring (current)

---

### 4.3 Temporal Graph Storage

**Requirement:** Store regulatory knowledge in a bitemporal graph.

**Graph Schema:**

**Nodes:**
- `Document` - Source documents
- `Provision` - Individual regulatory clauses
- `Concept` - Regulatory concepts (data privacy, emissions, etc.)
- `Jurisdiction` - Geographic applicability
- `Threshold` - Numeric limits
- `Provenance` - Citation metadata

**Relationships:**
- `IN_DOCUMENT` - Provision belongs to Document
- `ABOUT` - Provision relates to Concept
- `APPLIES_TO` - Provision applies to Jurisdiction
- `HAS_THRESHOLD` - Provision has numeric Threshold
- `PROVENANCE` - Provision cites source location
- `SUPERSEDES` - New provision replaces old version
- `MENTIONS` - Document mentions Jurisdiction

**Bitemporal Attributes:**
- `tx_from` - Transaction start time (when record was created)
- `tx_to` - Transaction end time (when record was superseded)
- `valid_from` - Regulation effective date
- `valid_to` - Regulation expiration date

**Acceptance Criteria:**
- ✅ Full lifecycle tracking (creation, updates, supersession)
- ✅ Historical queries ("what was active at time T?")
- ✅ Change detection ("what changed between T1 and T2?")
- ✅ Version linking via `SUPERSEDES` relationships

**Cypher Queries:**
- `CYPHER_PROVISION_HISTORY` - Get all versions of a provision
- `CYPHER_ACTIVE_PROVISIONS_AT_TIME` - Query active provisions at timestamp
- `CYPHER_PROVISION_CHANGES` - Query changes in time range

---

### 4.4 Regulatory Diff Engine

**Requirement:** Compare two documents and detect all changes.

**Change Types Detected:**
- Text additions/removals/modifications
- Obligation changes (added, removed, modified)
- Threshold changes (with % delta calculation)
- Jurisdiction changes
- New penalties or incentives

**Acceptance Criteria:**
- ✅ Clause-level comparison
- ✅ Threshold delta detection
- ✅ Human-readable summary generation
- ✅ JSON-structured diff output

**Endpoints:**
- `POST /diff` - Compare two documents by ID
- `GET /diff/compare?doc1_id=X&doc2_id=Y` - GET-based comparison

**Example Output:**
```json
{
  "doc1_id": "abc123",
  "doc2_id": "def456",
  "total_changes": 15,
  "changes": [
    {
      "type": "threshold_changed",
      "description": "Threshold changed: emissions_percent (+25.0%)",
      "old_value": 20.0,
      "new_value": 25.0
    },
    {
      "type": "obligation_added",
      "description": "New obligation detected",
      "new_value": "All entities shall report quarterly emissions..."
    }
  ],
  "summary": "Detected 15 total changes: 5 threshold_changed, 3 obligation_added, ..."
}
```

---

### 4.5 Opportunity Engine

**Requirement:** Detect regulatory arbitrage and compliance gaps.

**Two Core Features:**

#### 4.5.1 Regulatory Arbitrage Detection

Identifies threshold inconsistencies across jurisdictions for the same regulatory concept.

**Endpoint:** `GET /opportunities/arbitrage`

**Query Parameters:**
- `j1` - First jurisdiction (e.g., "US")
- `j2` - Second jurisdiction (e.g., "EU")
- `concept` - Filter by concept (optional)
- `rel_delta` - Minimum relative threshold difference (default: 0.2 = 20%)
- `limit` - Max results (default: 50)
- `since` - Filter by creation timestamp

**Example:**
```http
GET /opportunities/arbitrage?j1=US&j2=EU&rel_delta=0.3&limit=10
```

Returns provisions with >30% threshold difference between US and EU.

#### 4.5.2 Compliance Gap Detection

Identifies provisions present in jurisdiction J1 but absent in J2 (asymmetric regulation).

**Endpoint:** `GET /opportunities/gaps`

**Query Parameters:**
- `j1` - Source jurisdiction (has regulations)
- `j2` - Target jurisdiction (missing regulations)
- `limit` - Max results

**Example:**
```http
GET /opportunities/gaps?j1=EU&j2=US&limit=50
```

Returns provisions with GDPR-like requirements in EU but not in US.

---

### 4.6 Authentication & Authorization

**Requirement:** Secure all APIs with JWT-based authentication.

**Features:**
- ✅ OAuth2-compatible token generation (`POST /auth/token`)
- ✅ Scope-based access control
- ✅ Per-service authentication
- ✅ 30-minute token expiration
- ✅ Token refresh endpoint

**Scopes:**
- `ingest:write` - Ingest documents
- `ingest:read` - Read ingestion status
- `opportunities:read` - Query arbitrage/gaps
- `diff:read` - Compare documents
- `admin` - Full access

**Default Users:**
- `admin` / `secret` - Full access
- `analyst` / `password` - Read-only access
- `api_user` / `password` - API client

---

### 4.7 Rate Limiting

**Requirement:** Prevent API abuse with Redis-based token bucket limiting.

**Limits:**
- **Ingestion Service:** 100 requests/minute
- **Opportunity API:** 200 requests/minute
- **Diff Engine:** 50 requests/minute (compute-intensive)

**Response Headers:**
- `X-RateLimit-Limit` - Max requests per window
- `X-RateLimit-Remaining` - Remaining requests
- `X-RateLimit-Reset` - Window reset timestamp
- `Retry-After` - Seconds until retry allowed (when limited)

---

## 5. Technical Requirements

### 5.1 Performance Requirements

| Metric | Target | Measured |
|--------|--------|----------|
| Document Ingestion Latency | < 5s (p95) | ✅ |
| NLP Extraction Throughput | > 100 docs/min | ✅ |
| Graph Query Latency | < 500ms (p95) | ✅ |
| Diff Comparison Time | < 10s for 100-page docs | ✅ |
| API Availability | 99.9% uptime | Pending prod deployment |

### 5.2 Scalability Requirements

- **Document Storage:** 10 million documents
- **Graph Nodes:** 100 million provisions
- **Concurrent Users:** 1,000 simultaneous API clients
- **Data Ingestion:** 10,000 documents/day

### 5.3 Data Retention

- **Raw Documents:** 7 years (compliance)
- **Normalized Documents:** Indefinite
- **Graph History:** Full temporal lineage (all versions)
- **Logs:** 90 days

---

## 6. API Specifications

### 6.1 Ingestion Service (Port 8000)

```
POST /auth/token - Generate JWT token
GET  /auth/me - Get current user
POST /ingest/url - Ingest document from URL
GET  /health - Health check
GET  /metrics - Prometheus metrics
```

### 6.2 Opportunity API (Port 8300)

```
POST /auth/token - Generate JWT token
GET  /opportunities/arbitrage - Detect threshold divergence
GET  /opportunities/gaps - Find compliance gaps
GET  /health - Health check
GET  /metrics - Prometheus metrics
```

### 6.3 Diff Engine (Port 8400)

```
POST /auth/token - Generate JWT token
POST /diff - Compare two documents
GET  /diff/compare - Compare via query params
GET  /health - Health check
GET  /metrics - Prometheus metrics
```

---

## 7. Security & Compliance

### 7.1 Security Controls

- ✅ SSRF protection (block private IPs)
- ✅ JWT authentication (HS256)
- ✅ Rate limiting (Redis-based)
- ✅ Input validation (Pydantic schemas)
- ✅ Secure secret management (env vars, planned: Vault)
- ⚠️ HTTPS/TLS (required in production)
- ⚠️ Data encryption at rest (planned)
- ⚠️ Audit logging (planned)

### 7.2 Compliance Requirements

- **GDPR:** Data subject rights, privacy by design
- **SOC 2 Type II:** Access controls, monitoring, incident response
- **HIPAA:** (if handling health regulations) encryption, audit trails

---

## 8. Performance Requirements

### Latency Targets

| Endpoint | Target (p95) | Target (p99) |
|----------|--------------|--------------|
| POST /ingest/url | 5s | 10s |
| GET /opportunities/arbitrage | 500ms | 1s |
| POST /diff | 10s | 20s |
| Graph queries | 500ms | 1s |

### Throughput Targets

- **Ingestion:** 100 documents/minute
- **Graph Queries:** 1,000 queries/second
- **Diff Operations:** 10 comparisons/minute/user

---

## 9. Deployment Architecture

### Development Environment

```
docker-compose up
```

Services:
- ingestion-service (8000)
- nlp-service (8100)
- graph-service (8200)
- opportunity-api (8300)
- diff-service (8400)
- localstack (S3 emulation)
- redpanda (Kafka)
- neo4j (Graph DB)
- redis (Rate limiting)

### Production Environment (Planned)

- **Compute:** AWS EKS (Kubernetes)
- **Messaging:** AWS MSK (Managed Kafka)
- **Graph Database:** Neo4j Enterprise (self-hosted or Aura)
- **Object Storage:** AWS S3
- **Caching:** AWS ElastiCache (Redis)
- **Load Balancer:** AWS ALB
- **Secrets:** AWS Secrets Manager
- **Monitoring:** Prometheus + Grafana
- **Logging:** CloudWatch or ELK stack

---

## 10. Success Metrics

### Product Metrics

- **Adoption:** 100 active users in first 6 months
- **Usage:** 10,000 documents ingested/month
- **Accuracy:** >90% NLP entity extraction precision
- **Value:** 3 regulatory arbitrage opportunities identified per customer/month

### Business Metrics

- **Revenue:** $500k ARR by end of Year 1
- **Customer Acquisition Cost:** <$10k
- **Customer Lifetime Value:** >$200k
- **Churn Rate:** <10% annually

### Technical Metrics

- **Availability:** 99.9% uptime
- **Error Rate:** <0.1% failed requests
- **Mean Time to Recovery:** <15 minutes
- **Incident Response:** <1 hour to triage

---

## Roadmap

### Q1 2025 (Complete ✅)
- [x] Ingestion Service
- [x] NLP Extraction (enhanced regex)
- [x] Graph Storage (bitemporal)
- [x] JWT Authentication
- [x] Rate Limiting
- [x] Diff Engine

### Q2 2025 (Planned)
- [ ] Legal-BERT model deployment
- [ ] Python SDK
- [ ] TypeScript SDK
- [ ] Web Dashboard (React)
- [ ] Alert Service (email/Slack/webhooks)

### Q3 2025 (Planned)
- [ ] ML Opportunity Scoring
- [ ] Graph Explorer UI
- [ ] Multi-tenancy
- [ ] Enterprise SSO (SAML/OAuth)

### Q4 2025 (Planned)
- [ ] Cloud IaC (Terraform for AWS)
- [ ] Kubernetes deployment
- [ ] Advanced analytics (trend detection)
- [ ] Public API marketplace listing

---

## Appendix

### A. Glossary

- **Bitemporal:** Tracking both transaction time (when data changed in DB) and valid time (when regulation was effective)
- **Provision:** A single regulatory clause or obligation
- **Provenance:** Citation metadata (document, page, character offsets)
- **Arbitrage:** Exploiting regulatory inconsistencies for competitive advantage

### B. References

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Neo4j Cypher Manual](https://neo4j.com/docs/cypher-manual/)
- [Legal-BERT Paper](https://arxiv.org/abs/2010.02559)

---

**Document Control**
- Version: 2.0.0
- Last Updated: 2025-11-18
- Next Review: 2025-12-18
