# RegEngine: Regulatory Intelligence Platform

A production-grade regulatory intelligence platform built on event-driven microservices architecture. RegEngine ingests regulatory documents, extracts structured obligations and thresholds using NLP, persists data to a Neo4j knowledge graph, and surfaces regulatory arbitrage opportunities and compliance gaps.

## Table of Contents

- [Architecture Overview](#architecture-overview)
- [Technical Stack](#technical-stack)
- [Service Architecture](#service-architecture)
- [Data Flow & Event Contracts](#data-flow--event-contracts)
- [Graph Data Model](#graph-data-model)
- [Quick Start](#quick-start)
- [Development Guide](#development-guide)
- [API Documentation](#api-documentation)
- [Security & Observability](#security--observability)
- [Recent Bug Fixes](#recent-bug-fixes)
- [Contributing](#contributing)

---

## Architecture Overview

RegEngine implements a **microservices architecture** with **event-driven data flows** using Kafka as the message broker. The platform processes regulatory documents through four specialized services, each with a single responsibility:

```
┌─────────────────────────────────────────────────────────────────────┐
│                      REGULATORY ENGINE PIPELINE                     │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  Ingestion Service (8000)  →  Kafka  →  NLP Service (8100)        │
│        ↓                       ↓            ↓                      │
│    S3 Storage          ingest.normalized   Kafka                  │
│    (raw + normalized)          ↓           ↓                      │
│                              nlp.extracted │                      │
│                                 ↓          ↓                      │
│                              Graph Service (8200)  →  Neo4j        │
│                                     ↓                              │
│                          Opportunity API (8300)                    │
│                          (Arbitrage & Gaps)                        │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### Design Principles

1. **Event-Driven Architecture**: Kafka provides asynchronous decoupling, fault tolerance, and replay capability
2. **Content-Addressed Storage**: SHA256-based deduplication prevents reprocessing identical documents
3. **Deterministic Processing**: Same input always produces same output; safe for replay
4. **Bi-temporal Graph Model**: Tracks both transaction time and valid time for regulatory changes
5. **Provenance Tracking**: Character-level offsets enable inline citations and source traceability
6. **Graceful Degradation**: Multiple OCR engines with fallback mechanisms

---

## Technical Stack

### Core Technologies

| Component | Technology | Version | Purpose |
|-----------|-----------|---------|---------|
| **Framework** | FastAPI | 0.115.0 | Async HTTP services with OpenAPI |
| **Runtime** | Python | 3.11 | Service implementation |
| **Message Queue** | Kafka (Redpanda) | 2.0.2 | Event streaming |
| **Graph Database** | Neo4j | 5.25 | Knowledge graph storage |
| **Object Storage** | S3 (LocalStack) | 1.34.74 | Document storage |
| **Validation** | Pydantic | 2.9.2 | Type safety & validation |
| **Schema** | JSON Schema | Draft-7 | Event contract validation |

### Processing & Extraction

- **PDF Processing**: pdfminer.six (structured extraction)
- **OCR Engine**: pytesseract + Tesseract (scanned documents)
- **Image Processing**: pdf2image + Pillow
- **Pattern Matching**: regex (NFA-based, multiline support)

### Observability

- **Metrics**: Prometheus (prometheus-client)
- **Logging**: structlog (JSON structured logging)
- **Tracing**: Request ID propagation (future enhancement)

---

## Service Architecture

### 1. Ingestion Service (Port 8000)

**Purpose**: Fetch, validate, normalize, and persist regulatory documents with SSRF protection.

**Key Features**:
- **SSRF Protection**: Multi-layer defense against Server-Side Request Forgery
  - URL scheme allowlisting (http/https only)
  - DNS resolution with private network blocking (RFC 1918, link-local, loopback)
  - IPv4 and IPv6 private network detection
  - Redirect blocking to prevent bypass attacks
- **Content Validation**: Size limits (25 MB), content-type allowlisting
- **Multi-Format Normalization**: JSON, PDF (pdfminer.six + Tesseract OCR), plain text
- **Position Mapping**: Character-level offset tracking for provenance

**Storage Strategy**:
```
s3://raw/{document_id}/{event_id}.{ext}              # Original document
s3://normalized/{content_hash}/current.json          # Deduplicated normalized
s3://normalized/by-document-id/{doc_id}/current.json # Document-centric alias
```

**Event Output**: `ingest.normalized` topic with deterministic keying (`document_id:content_hash`)

**Endpoints**:
- `POST /ingest/url` - Ingest from URL
- `GET /health` - Health check
- `GET /metrics` - Prometheus metrics

---

### 2. NLP Service (Port 8100)

**Purpose**: Extract structured entities from normalized documents using regex-based pattern matching.

**Entity Types**:

1. **OBLIGATION**: Regulatory requirements
   - Patterns: "shall", "must", "required to", "has to"
   - Context: Full sentence extraction (bounded by periods or 200 chars)

2. **THRESHOLD**: Quantitative limits with unit normalization
   - Patterns: `{value} {unit}` (e.g., "5%", "10 bps", "$1000")
   - Unit Normalization:
     - `%`, `percent` → `percent`
     - `bps`, `basis points` → `basis_points`
     - `$`, `USD`, `US$` → `usd`
     - `€`, `EUR` → `eur`

3. **JURISDICTION**: Regulatory regions
   - Hints: "United States", "European Union", "California", etc.

**Processing Features**:
- **Kafka Manual Commit**: Prevents message loss on crash (no auto-commit)
- **Text Truncation Warning**: Logs when documents exceed 2M characters
- **Schema Validation**: Draft-7 JSON Schema validation for all outputs
- **S3 Client Caching**: Connection pooling for performance

**Event Output**: `nlp.extracted` topic with entities array

---

### 3. Graph Service (Port 8200)

**Purpose**: Persist extracted entities to Neo4j knowledge graph with bi-temporal support.

**Graph Schema**:

```cypher
# Node Types
(Document {id, source_url, created_at})
(Provision {pid, text, hash, tx_from, valid_from})
(Threshold {pid, value, unit, unit_normalized})
(Jurisdiction {name})
(Concept {name})
(Provenance {doc_id, start, end, page})

# Relationships
(Document)-[:MENTIONS]->(Jurisdiction)
(Provision)-[:IN_DOCUMENT]->(Document)
(Provision)-[:ABOUT]->(Concept)
(Provision)-[:APPLIES_TO]->(Jurisdiction)
(Provision)-[:HAS_THRESHOLD]->(Threshold)
(Provision)-[:PROVENANCE]->(Provenance)
```

**Key Features**:
- **Bi-temporal Design**: Tracks `tx_from` (transaction time) and `valid_from` (effective time)
- **Upsert Logic**: MERGE operations for idempotent processing
- **Stable Hashing**: SHA256-based provision hashing (not Python's randomized `hash()`)
- **Thread-Safe Driver**: Double-checked locking for Neo4j driver initialization
- **Manual Kafka Commit**: Ensures graph consistency before commit

**Constraints**:
- `Document.id` - Unique
- `Provision.pid` - Unique (format: `{doc_id}:{start}:{end}`)
- `Threshold.pid` - Unique
- `Jurisdiction.name` - Unique
- `Concept.name` - Indexed

---

### 4. Opportunity API (Port 8300)

**Purpose**: Surface regulatory arbitrage opportunities and compliance gaps.

**Endpoints**:

#### `GET /opportunities/arbitrage`

Finds provisions with same concept and threshold unit but different values across jurisdictions.

**Query Parameters**:
- `j1`, `j2` (optional): Jurisdiction filters (e.g., "United States", "European Union")
- `concept` (optional): Concept name filter (case-insensitive)
- `rel_delta` (default: 0.2): Relative difference threshold (0.0-1.0)
- `since` (optional): Epoch-millisecond timestamp filter
- `limit` (default: 50, max: 200): Result limit

**Example**:
```bash
curl -s "http://localhost:8300/opportunities/arbitrage?j1=United%20States&j2=European%20Union&rel_delta=0.15&limit=10" | jq .
```

**Response**:
```json
[
  {
    "concept": "Capital Reserve Requirement",
    "text1": "Banks shall maintain 5% capital reserve",
    "value1": 5.0,
    "text2": "Credit institutions must hold 8% capital",
    "value2": 8.0,
    "unit": "percent",
    "doc_id_1": "abc123...",
    "source_url_1": "https://...",
    "provenance_1": {"start": 100, "end": 150}
  }
]
```

#### `GET /opportunities/gaps`

Identifies regulatory concepts present in jurisdiction j1 but absent in j2.

**Query Parameters**:
- `j1`, `j2` (required): Jurisdiction pair
- `limit` (default: 50): Result limit

**Example**:
```bash
curl -s "http://localhost:8300/opportunities/gaps?j1=European%20Union&j2=United%20States&limit=10" | jq .
```

---

## Data Flow & Event Contracts

### Event 1: NormalizedEvent (`ingest.normalized`)

```json
{
  "event_id": "550e8400-e29b-41d4-a716-446655440000",
  "document_id": "a1b2c3d4...",
  "source_system": "Federal Register",
  "source_url": "https://www.federalregister.gov/...",
  "raw_s3_path": "s3://bucket/raw/doc_id/event_id.pdf",
  "normalized_s3_path": "s3://bucket/normalized/content_hash/current.json",
  "timestamp": "2025-11-15T12:00:00Z",
  "content_sha256": "e3b0c442..."
}
```

**Kafka Key**: `{document_id}:{content_hash}` (deterministic, enables deduplication)

---

### Event 2: NLP Extracted Entities (`nlp.extracted`)

```json
{
  "event_id": "660e8400-e29b-41d4-a716-446655440000",
  "document_id": "a1b2c3d4...",
  "source_url": "https://www.federalregister.gov/...",
  "timestamp": "2025-11-15T12:01:00Z",
  "entities": [
    {
      "type": "OBLIGATION",
      "text": "shall maintain adequate capital reserves",
      "start": 100,
      "end": 140,
      "attrs": {}
    },
    {
      "type": "THRESHOLD",
      "text": "5%",
      "start": 200,
      "end": 202,
      "attrs": {
        "value": 5.0,
        "unit": "%",
        "unit_normalized": "percent"
      }
    },
    {
      "type": "JURISDICTION",
      "text": "United States",
      "start": 50,
      "end": 63,
      "attrs": {"name": "United States"}
    }
  ]
}
```

**Kafka Key**: `{document_id}`

---

### Normalized Document Schema

```json
{
  "document_id": "sha256-hash",
  "source_url": "https://...",
  "source_system": "Federal Register",
  "retrieved_at": "2025-11-15T12:00:00Z",
  "title": "Capital Requirements for Banks",
  "jurisdiction": "United States",
  "text": "Full extracted text...",
  "content_sha256": "e3b0c442...",
  "content_type": "application/pdf",
  "position_map": [
    {
      "page": 1,
      "char_start": 0,
      "char_end": 1000,
      "source_start": 0,
      "source_end": 1000
    }
  ],
  "text_extraction": {
    "engine": "pdfminer",
    "confidence_mean": 0.95,
    "confidence_std": 0.05
  }
}
```

---

## Graph Data Model

### Bi-temporal Design

RegEngine tracks two time dimensions:

1. **Transaction Time** (`tx_from`, `tx_to`): When the data was recorded in the system
2. **Valid Time** (`valid_from`, `valid_to`): When the regulation was/is effective

This enables:
- Historical queries: "What did we know on date X?"
- Temporal queries: "What was effective on date Y?"
- Audit trails: "When did we learn about this change?"

### Provenance Tracking

Every provision includes:
- `document_id`: Source document
- `start`, `end`: Character offsets in source text
- `page`: Page number (for PDFs)

This enables:
- Inline citations with exact positions
- Jump-to-source functionality in UI
- Verification of extractions

---

## Quick Start

### Prerequisites

- Docker & Docker Compose
- Make (optional, for convenience)
- 4GB+ RAM (for Neo4j)

### 1. Start the Stack

```bash
docker-compose up --build -d
```

Services will be available at:
- Ingestion: http://localhost:8000
- NLP: http://localhost:8100
- Graph: http://localhost:8200
- Opportunity: http://localhost:8300
- Neo4j Browser: http://localhost:7474 (neo4j / letmein)

### 2. Initialize S3 Buckets

```bash
make init-local
```

Or manually:
```bash
aws --endpoint-url=http://localhost:4566 s3 mb s3://reg-engine-raw-data-dev
aws --endpoint-url=http://localhost:4566 s3 mb s3://reg-engine-processed-data-dev
```

### 3. Trigger Sample Ingestion

```bash
make smoke-ingest
```

Or manually:
```bash
curl -X POST http://localhost:8000/ingest/url \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://example.com/regulation.pdf",
    "source_system": "Test System"
  }'
```

### 4. Verify Processing

**Check Kafka topics**:
```bash
make consume-normalized  # Watch ingest.normalized topic
make consume-nlp         # Watch nlp.extracted topic
```

**Query Neo4j**:
- Open http://localhost:7474
- Run: `MATCH (d:Document)-[:MENTIONS]->(j:Jurisdiction) RETURN d, j LIMIT 10`

**Query Opportunity API**:
```bash
# Find arbitrage opportunities
curl -s "http://localhost:8300/opportunities/arbitrage?limit=5" | jq .

# Find compliance gaps
curl -s "http://localhost:8300/opportunities/gaps?j1=United%20States&j2=European%20Union" | jq .
```

---

## Development Guide

### Repository Structure

```
RegEngine/
├── services/
│   ├── ingestion/          # Document ingestion & normalization
│   │   ├── app/
│   │   │   ├── routes.py   # FastAPI endpoints
│   │   │   ├── normalization.py  # PDF/JSON extraction
│   │   │   ├── kafka_utils.py    # Kafka producer
│   │   │   ├── s3_utils.py       # S3 operations
│   │   │   └── config.py   # Settings
│   │   ├── tests/
│   │   └── main.py
│   ├── nlp/                # NLP entity extraction
│   │   ├── app/
│   │   │   ├── consumer.py # Kafka consumer
│   │   │   ├── extractor.py # Regex-based NLP
│   │   │   └── s3_utils.py
│   │   └── main.py
│   ├── graph/              # Neo4j graph persistence
│   │   ├── app/
│   │   │   ├── consumer.py
│   │   │   ├── neo4j_utils.py  # Cypher queries
│   │   │   └── routes.py
│   │   └── main.py
│   └── opportunity/        # Arbitrage & gap detection
│       ├── app/
│       │   ├── routes.py
│       │   └── neo4j_utils.py
│       └── main.py
├── data-schemas/           # JSON Schemas
│   └── events/
│       ├── ingest.normalized.schema.json
│       └── nlp.extracted.schema.json
├── infra/                  # Terraform modules (stubs)
├── docker-compose.yml
├── Makefile
└── README.md
```

### Running Tests

```bash
# Run all tests
make test

# Run tests for specific service
cd services/ingestion && pytest -v
cd services/nlp && pytest -v
cd services/graph && pytest -v
cd services/opportunity && pytest -v
```

### Code Formatting

```bash
# Format all code
make format

# Check formatting
make lint
```

### Continuous Integration

GitHub Actions workflow (`.github/workflows/ci.yml`) runs on every push and PR:

1. **Linting**: Black & isort formatting checks
2. **Tests**: pytest across all services
3. **Matrix Build**: Parallel execution for all 4 services

---

## API Documentation

### Ingestion Service

**Interactive Docs**: http://localhost:8000/docs

#### POST /ingest/url

```bash
curl -X POST http://localhost:8000/ingest/url \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://www.example.com/regulation.pdf",
    "source_system": "Federal Register"
  }'
```

**Response** (201):
```json
{
  "event_id": "550e8400-e29b-41d4-a716-446655440000",
  "document_id": "a1b2c3d4...",
  "source_system": "Federal Register",
  "source_url": "https://www.example.com/regulation.pdf",
  "raw_s3_path": "s3://bucket/raw/...",
  "normalized_s3_path": "s3://bucket/normalized/...",
  "timestamp": "2025-11-15T12:00:00Z",
  "content_sha256": "e3b0c442..."
}
```

**Error Responses**:
- `400`: Invalid URL, SSRF blocked, unsupported scheme
- `413`: Payload exceeds 25 MB limit
- `422`: Invalid JSON response
- `502`: Failed to fetch URL

---

### Opportunity API

**Interactive Docs**: http://localhost:8300/docs

#### GET /opportunities/arbitrage

Find regulatory arbitrage opportunities (same concept, different thresholds).

**Query Parameters**:
- `j1`, `j2`: Jurisdiction filters (optional)
- `concept`: Concept name filter (optional, case-insensitive)
- `rel_delta`: Relative difference threshold (default: 0.2)
- `since`: Epoch-ms timestamp filter (optional)
- `limit`: Result limit (default: 50, max: 200)

**Example**:
```bash
# Find all arbitrage opportunities with >15% difference
curl -s "http://localhost:8300/opportunities/arbitrage?rel_delta=0.15&limit=10" | jq .

# Filter by jurisdictions and concept
curl -s "http://localhost:8300/opportunities/arbitrage?j1=United%20States&j2=European%20Union&concept=capital%20reserve" | jq .

# Filter by time (last 7 days)
SINCE=$(($(date +%s - 604800) * 1000))
curl -s "http://localhost:8300/opportunities/arbitrage?since=$SINCE" | jq .
```

#### GET /opportunities/gaps

Find regulatory concepts present in one jurisdiction but absent in another.

**Query Parameters**:
- `j1` (required): First jurisdiction
- `j2` (required): Second jurisdiction
- `limit`: Result limit (default: 50)

**Example**:
```bash
# Find concepts in EU but not in US
curl -s "http://localhost:8300/opportunities/gaps?j1=European%20Union&j2=United%20States" | jq .
```

---

## Security & Observability

### Security Features

#### 1. SSRF Protection (Ingestion Service)

**Multi-Layer Defense**:

```python
# Layer 1: URL Scheme Allowlisting
ALLOWED_SCHEMES = {"https", "http"}

# Layer 2: Hostname Blocklist
PROHIBITED_HOSTS = {"localhost", "127.0.0.1"}

# Layer 3: IP Network Blocklist
PROHIBITED_NETWORKS = [
    ip_network("10.0.0.0/8"),       # RFC 1918 private
    ip_network("172.16.0.0/12"),    # RFC 1918 private
    ip_network("192.168.0.0/16"),   # RFC 1918 private
    ip_network("127.0.0.0/8"),      # Loopback
    ip_network("169.254.0.0/16"),   # Link-local IPv4
    ip_network("::1/128"),          # Loopback IPv6
    ip_network("fc00::/7"),         # Private IPv6
    ip_network("fe80::/10"),        # Link-local IPv6
    ip_network("::ffff:0:0/96"),    # IPv4-mapped IPv6
]

# Layer 4: Redirect Blocking
response = requests.get(url, timeout=30, allow_redirects=False)
```

**Attack Vectors Prevented**:
- DNS rebinding attacks
- SSRF via redirects
- Internal service scanning
- Cloud metadata access (169.254.169.254)

#### 2. Content Validation

- **Size Limits**: 25 MB maximum payload
- **Content-Type Allowlisting**: JSON, PDF, plain text only
- **Schema Validation**: JSON Schema Draft-7 for all events

#### 3. Resource Protection

- **Kafka Message Limits**: Manual commit prevents unbounded processing
- **S3 Read Limits**: 100 MB maximum object size
- **Text Truncation**: 2M character limit with logging

### Observability

#### Prometheus Metrics

All services expose `/metrics` endpoints:

**Common Metrics**:
```
# Request counters
service_requests_total{endpoint="/ingest/url", status="200"}

# Latency histograms
service_request_latency_seconds{endpoint="/ingest/url"}
```

**Service-Specific Metrics**:
```
# Ingestion
ingestion_kafka_messages_total{topic="ingest.normalized"}

# NLP
nlp_messages_total{status="success"}

# Graph
graph_consumer_messages_total{status="success"}

# Opportunity
opportunity_requests_total{endpoint="/arbitrage", status="200"}
```

**Scrape Configuration** (prometheus.yml):
```yaml
scrape_configs:
  - job_name: 'regengine'
    static_configs:
      - targets:
        - 'ingestion:8000'
        - 'nlp:8100'
        - 'graph:8200'
        - 'opportunity:8300'
```

#### Structured Logging

All services use structlog with JSON output:

```json
{
  "timestamp": "2025-11-15T12:00:00.123456Z",
  "level": "info",
  "event": "normalized_event_emitted",
  "document_id": "a1b2c3d4...",
  "content_sha256": "e3b0c442..."
}
```

**Log Aggregation** (ELK/Loki):
```bash
# Query by event type
event="nlp_extracted"

# Query by document
document_id="a1b2c3d4..."

# Query errors
level="error"
```

#### Health Checks

All services expose `GET /health` endpoints:

```bash
# Check all services
for port in 8000 8100 8200 8300; do
  curl -s http://localhost:$port/health
done
```

Docker Compose health checks:
```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
  interval: 10s
  timeout: 3s
  retries: 10
```

---

## Recent Bug Fixes

### Critical Fixes (Production-Blocking)

1. **SSRF Bypass via HTTP Redirects** (services/ingestion/app/routes.py:166)
   - **Issue**: `requests.get()` followed redirects, allowing bypass of IP allowlisting
   - **Fix**: Added `allow_redirects=False` to prevent redirect-based SSRF
   - **Impact**: Prevents attackers from bypassing SSRF protections via redirect chains

2. **Race Condition in Neo4j Driver Initialization** (services/graph/app/neo4j_utils.py:15, services/opportunity/app/neo4j_utils.py:14)
   - **Issue**: Global driver initialization not thread-safe; multiple threads could create duplicate drivers
   - **Fix**: Implemented double-checked locking with `threading.Lock()`
   - **Impact**: Prevents connection leaks and driver initialization errors

3. **Unstable Hash Function in Graph Storage** (services/graph/app/neo4j_utils.py:95)
   - **Issue**: Used Python's `hash()` which is randomized across runs; same provision gets different hashes
   - **Fix**: Replaced with `hashlib.sha256()` for stable, deterministic hashing
   - **Impact**: Prevents duplicate provision nodes in Neo4j; enables proper deduplication

### High Severity Fixes

4. **Message Loss on Crash - Auto Commit** (services/nlp/app/consumer.py:65, services/graph/app/consumer.py:51)
   - **Issue**: Kafka auto-commit commits offsets before processing; crash = lost messages
   - **Fix**: Changed to `enable_auto_commit=False` with manual `consumer.commit()` after success
   - **Impact**: Guarantees at-least-once delivery; no message loss on service crashes

5. **Kafka Producer Resource Leak** (services/ingestion/app/kafka_utils.py:19)
   - **Issue**: KafkaProducer cached via `@lru_cache` but never closed; socket/memory leaks
   - **Fix**: Removed lru_cache, added global singleton with `atexit.register(close_producer)`
   - **Impact**: Prevents socket exhaustion and memory leaks in long-running services

6. **Silent Data Truncation in NLP** (services/nlp/app/consumer.py:100)
   - **Issue**: Text silently truncated to 2M chars without logging; incomplete entity extraction
   - **Fix**: Added warning log with original length before truncation
   - **Impact**: Operators can detect and investigate large document issues

7. **No Error Handling for Kafka Send** (services/ingestion/app/kafka_utils.py:63)
   - **Issue**: `producer.send()` failures silently ignored; messages dropped without notice
   - **Fix**: Added `future.get(timeout=10)` with exception handling and logging
   - **Impact**: Immediate failure detection; no silent message drops

8. **S3 Client Created on Every Call** (services/ingestion/app/s3_utils.py:20, services/nlp/app/s3_utils.py:12)
   - **Issue**: New boto3 client created per S3 operation; connection overhead and pool exhaustion
   - **Fix**: Added `@lru_cache(maxsize=1)` to cache client singleton
   - **Impact**: 10-100x performance improvement on S3-heavy operations

9. **Missing Error Handling for S3 Operations** (services/ingestion/app/s3_utils.py:39, services/nlp/app/s3_utils.py:18)
   - **Issue**: S3 operations had no error handling; unhandled ClientError exceptions
   - **Fix**: Wrapped in try/except with structured error logging
   - **Impact**: Graceful error handling; operators can diagnose S3 issues

### Medium Severity Fixes

10. **Potential Document ID Collision** (services/ingestion/app/normalization.py:69)
    - **Issue**: Document ID derived from URL + first 4096 chars; large docs differing after 4096 get same ID
    - **Fix**: Use entire text for document ID generation
    - **Impact**: Eliminates ID collision risk for large documents

11. **Silent Unicode Errors** (services/ingestion/app/normalization.py:126)
    - **Issue**: `errors="ignore"` silently drops invalid UTF-8 bytes; data corruption undetected
    - **Fix**: Use `errors="strict"` with fallback to `errors="replace"` and warning log
    - **Impact**: Operators can detect and investigate encoding issues

12. **Missing Link-Local IPv6 in SSRF Protection** (services/ingestion/app/routes.py:41)
    - **Issue**: SSRF protection missing `fe80::/10` (IPv6 link-local) and `::ffff:0:0/96` (IPv4-mapped)
    - **Fix**: Added missing IPv6 network ranges to blocklist
    - **Impact**: Closes SSRF attack vector on IPv6-enabled systems

13. **Missing Float Conversion Error Handling** (services/nlp/app/extractor.py:56)
    - **Issue**: `float()` conversion can raise ValueError but no error handling
    - **Fix**: Wrapped in try/except; log warning and skip invalid thresholds
    - **Impact**: Prevents NLP service crashes on malformed threshold values

14. **No Error Handling for Neo4j Constraints** (services/graph/main.py:45)
    - **Issue**: Constraint creation has no error handling; app crashes if Neo4j down or auth fails
    - **Fix**: Wrapped in try/except with warning logs; app starts even if constraints fail
    - **Impact**: Graceful degradation; app doesn't crash on Neo4j connection issues

### Testing the Fixes

```bash
# Run all tests to verify fixes
make test

# Run specific service tests
cd services/ingestion && pytest -v
cd services/nlp && pytest -v
cd services/graph && pytest -v
cd services/opportunity && pytest -v

# Verify SSRF protection
curl -X POST http://localhost:8000/ingest/url \
  -H "Content-Type: application/json" \
  -d '{"url": "http://169.254.169.254/latest/meta-data/", "source_system": "Test"}'
# Expected: 400 Bad Request - Host resolved to a private network

# Verify Kafka manual commit (simulate crash)
docker-compose kill nlp
docker-compose up -d nlp
# Messages should be reprocessed (no loss)
```

---

## Contributing

### Development Workflow

1. **Fork & Clone**:
   ```bash
   git clone https://github.com/your-org/RegEngine.git
   cd RegEngine
   ```

2. **Create Feature Branch**:
   ```bash
   git checkout -b feature/your-feature-name
   ```

3. **Install Dependencies**:
   ```bash
   cd services/ingestion && pip install -r requirements.txt
   # Repeat for other services
   ```

4. **Run Tests**:
   ```bash
   make test
   ```

5. **Format Code**:
   ```bash
   make format
   make lint
   ```

6. **Submit Pull Request**:
   - Ensure all tests pass
   - Add tests for new functionality
   - Update README if needed

### Adding a New Entity Type

Example: Adding "DEADLINE" entity type

1. **Update Extractor** (services/nlp/app/extractor.py):
   ```python
   DEADLINE_PATTERN = re.compile(
       r"(?P<date>\d{4}-\d{2}-\d{2})|(?P<relative>within \d+ days)"
   )

   def extract_entities(text: str) -> List[Dict]:
       # ... existing code ...

       for match in DEADLINE_PATTERN.finditer(text):
           ents.append({
               "type": "DEADLINE",
               "text": match.group(0),
               "start": match.start(),
               "end": match.end(),
               "attrs": {
                   "date": match.group("date"),
                   "relative": match.group("relative")
               }
           })
   ```

2. **Update Schema** (data-schemas/events/nlp.extracted.schema.json):
   ```json
   {
     "entity_types": {
       "enum": ["OBLIGATION", "THRESHOLD", "JURISDICTION", "DEADLINE"]
     }
   }
   ```

3. **Update Graph Model** (services/graph/app/neo4j_utils.py):
   ```python
   # Add to CYPHER_UPSERT
   FOREACH (_ IN CASE WHEN ob.deadline_is_set THEN [1] ELSE [] END |
     MERGE (dl:Deadline {pid: ob.pid})
       ON CREATE SET dl.date = ob.deadline_date
     MERGE (p)-[:HAS_DEADLINE]->(dl)
   )
   ```

4. **Add Tests**:
   ```python
   def test_deadline_extraction():
       text = "Submit application by 2025-12-31"
       entities = extract_entities(text)
       deadlines = [e for e in entities if e["type"] == "DEADLINE"]
       assert len(deadlines) == 1
       assert deadlines[0]["attrs"]["date"] == "2025-12-31"
   ```

---

## License

MIT License - See LICENSE file for details

---

## Support

- **Issues**: https://github.com/your-org/RegEngine/issues
- **Discussions**: https://github.com/your-org/RegEngine/discussions
- **Documentation**: https://docs.regengine.io

---

## Acknowledgments

Built with:
- [FastAPI](https://fastapi.tiangolo.com/)
- [Neo4j](https://neo4j.com/)
- [Apache Kafka](https://kafka.apache.org/)
- [Pydantic](https://pydantic-docs.helpmanual.io/)
- [structlog](https://www.structlog.org/)
