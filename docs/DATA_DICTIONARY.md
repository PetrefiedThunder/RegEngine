# RegEngine v2 - Data Dictionary

Complete reference for all data schemas, entities, and attributes across the RegEngine platform.

---

## Table of Contents

1. [Document Schemas](#document-schemas)
2. [Event Schemas](#event-schemas)
3. [Graph Node Types](#graph-node-types)
4. [API Request/Response Schemas](#api-requestresponse-schemas)
5. [Entity Types](#entity-types)
6. [Enumerations](#enumerations)

---

## 1. Document Schemas

### 1.1 NormalizedDocument

**Location:** `data-schemas/reg-document.schema.json`

**Purpose:** Standardized format for all ingested documents.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `document_id` | string | ✅ | SHA256 hash of source URL + content |
| `source_url` | string (URI) | ✅ | Original document URL |
| `source_system` | string | ✅ | System of origin (SEC, EPA, EU, etc.) |
| `retrieved_at` | string (ISO8601) | ✅ | Fetch timestamp |
| `text` | string | ✅ | Extracted full text |
| `content_sha256` | string | ✅ | Content hash for deduplication |
| `title` | string | ❌ | Document title (if available) |
| `jurisdiction` | string | ❌ | Primary jurisdiction (US, EU, etc.) |
| `content_type` | string | ❌ | MIME type (application/pdf, etc.) |
| `position_map` | object | ❌ | Per-page character offsets |
| `text_extraction` | object | ❌ | Extraction metadata |

**text_extraction Object:**

| Field | Type | Description |
|-------|------|-------------|
| `engine` | string | Extraction method (pdfminer, tesseract, json) |
| `confidence_mean` | number | Average OCR confidence (0-1) |
| `confidence_std` | number | Std dev of OCR confidence |
| `pages` | array | Per-page extraction results |

---

## 2. Event Schemas

### 2.1 ingest.normalized Event

**Topic:** `ingest.normalized`
**Producer:** Ingestion Service
**Consumers:** NLP Service

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `event_id` | string (UUID) | ✅ | Unique event identifier |
| `document_id` | string | ✅ | Document identifier |
| `source_system` | string | ✅ | Source system name |
| `source_url` | string (URI) | ✅ | Document URL |
| `raw_s3_path` | string | ✅ | S3 path to raw document |
| `normalized_s3_path` | string | ✅ | S3 path to normalized JSON |
| `content_sha256` | string | ✅ | Content hash |
| `timestamp` | string (ISO8601) | ✅ | Event timestamp |

### 2.2 nlp.extracted Event

**Topic:** `nlp.extracted`
**Producer:** NLP Service
**Consumers:** Graph Service

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `event_id` | string (UUID) | ✅ | Unique event identifier |
| `document_id` | string | ✅ | Document identifier |
| `source_url` | string (URI) | ❌ | Source URL |
| `entities` | array[Entity] | ✅ | Extracted entities |
| `timestamp` | string (ISO8601) | ✅ | Event timestamp |

**Entity Object:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `type` | string (enum) | ✅ | Entity type (see Entity Types) |
| `text` | string | ✅ | Extracted text span |
| `start` | integer | ✅ | Character offset (start) |
| `end` | integer | ✅ | Character offset (end) |
| `attrs` | object | ✅ | Type-specific attributes |

---

## 3. Graph Node Types

### 3.1 Document Node

**Label:** `Document`

| Property | Type | Required | Description |
|----------|------|----------|-------------|
| `id` | string | ✅ | Document identifier (unique) |
| `source_url` | string | ✅ | Original URL |
| `created_at` | timestamp | ✅ | Creation timestamp (milliseconds) |

**Indexes:**
- Unique constraint on `id`

**Relationships:**
- `-[:MENTIONS]->(Jurisdiction)` - Document mentions jurisdiction
- `<-[:IN_DOCUMENT]-(Provision)` - Provisions in document

---

### 3.2 Provision Node

**Label:** `Provision`

| Property | Type | Required | Description |
|----------|------|----------|-------------|
| `pid` | string | ✅ | Provision identifier (doc_id:start:end) |
| `version_id` | string | ✅ | Version identifier (pid:timestamp) |
| `text` | string | ✅ | Provision text |
| `hash` | string | ✅ | Content hash |
| `tx_from` | timestamp | ✅ | Transaction start time |
| `tx_to` | timestamp \| null | ✅ | Transaction end time (null = current) |
| `valid_from` | timestamp | ✅ | Effective date |
| `valid_to` | timestamp \| null | ✅ | Expiration date (null = still valid) |
| `superseded` | boolean | ✅ | True if newer version exists |
| `version` | integer | ✅ | Version number (1, 2, 3, ...) |

**Indexes:**
- Unique constraint on `version_id`
- Index on `pid`
- Index on `tx_from`, `tx_to` (bitemporal queries)

**Relationships:**
- `-[:IN_DOCUMENT]->(Document)` - Belongs to document
- `-[:ABOUT]->(Concept)` - Relates to concept
- `-[:APPLIES_TO]->(Jurisdiction)` - Applies to jurisdiction
- `-[:HAS_THRESHOLD]->(Threshold)` - Has numeric threshold
- `-[:PROVENANCE]->(Provenance)` - Citation metadata
- `-[:SUPERSEDES]->(Provision)` - Replaces older version

---

### 3.3 Concept Node

**Label:** `Concept`

| Property | Type | Required | Description |
|----------|------|----------|-------------|
| `name` | string | ✅ | Concept name (unique) |

**Indexes:**
- Unique constraint on `name`
- Full-text index on `name`

**Examples:**
- "emissions"
- "data privacy"
- "financial disclosure"
- "environmental impact"

**Relationships:**
- `<-[:ABOUT]-(Provision)` - Provisions about this concept

---

### 3.4 Jurisdiction Node

**Label:** `Jurisdiction`

| Property | Type | Required | Description |
|----------|------|----------|-------------|
| `name` | string | ✅ | Jurisdiction name (unique) |

**Indexes:**
- Unique constraint on `name`

**Examples:**
- "US"
- "EU"
- "California"
- "New York"
- "United Kingdom"

**Relationships:**
- `<-[:APPLIES_TO]-(Provision)` - Provisions apply here
- `<-[:MENTIONS]-(Document)` - Documents mention jurisdiction

---

### 3.5 Threshold Node

**Label:** `Threshold`

| Property | Type | Required | Description |
|----------|------|----------|-------------|
| `pid` | string | ✅ | Provision identifier |
| `version_id` | string | ✅ | Version identifier |
| `value` | float | ✅ | Numeric value |
| `unit` | string | ✅ | Original unit |
| `unit_normalized` | string | ✅ | Normalized unit |

**Indexes:**
- Unique constraint on `version_id`

**Unit Normalization:**

| Original | Normalized |
|----------|-----------|
| `%`, `percent` | `percent` |
| `bps`, `basis points` | `basis_points` |
| `$`, `USD`, `US$` | `USD` |
| `€`, `EUR`, `eur` | `EUR` |
| `£`, `GBP`, `gbp` | `GBP` |
| `tons`, `ton` | `tons` |

**Relationships:**
- `<-[:HAS_THRESHOLD]-(Provision)` - Threshold of provision

---

### 3.6 Provenance Node

**Label:** `Provenance`

| Property | Type | Required | Description |
|----------|------|----------|-------------|
| `doc_id` | string | ✅ | Document identifier |
| `start` | integer | ✅ | Character offset (start) |
| `end` | integer | ✅ | Character offset (end) |
| `page` | integer | ❌ | Page number (if available) |

**Indexes:**
- Unique constraint on `(doc_id, start, end)`

**Relationships:**
- `<-[:PROVENANCE]-(Provision)` - Citation for provision

---

## 4. API Request/Response Schemas

### 4.1 IngestRequest

**Endpoint:** `POST /ingest/url`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `url` | string (URI) | ✅ | Document URL to fetch |
| `source_system` | string | ✅ | Source system identifier |

**Validation:**
- `url` must be valid HTTP/HTTPS
- `url` cannot resolve to private networks
- `url` must respond with content < 25 MB

### 4.2 NormalizedEvent (Response)

**Endpoint:** `POST /ingest/url` response

| Field | Type | Description |
|-------|------|-------------|
| `event_id` | string (UUID) | Event identifier |
| `document_id` | string | Document identifier |
| `source_system` | string | Source system |
| `source_url` | string | Original URL |
| `raw_s3_path` | string | S3 path to raw file |
| `normalized_s3_path` | string | S3 path to normalized JSON |
| `timestamp` | string (ISO8601) | Event timestamp |
| `content_sha256` | string | Content hash |

---

### 4.3 DiffRequest

**Endpoint:** `POST /diff`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `doc1_id` | string | ✅ | First document ID |
| `doc2_id` | string | ✅ | Second document ID |
| `include_text_diff` | boolean | ❌ | Include text comparison (default: true) |
| `include_entity_diff` | boolean | ❌ | Include entity comparison (default: true) |

### 4.4 DiffResponse

**Endpoint:** `POST /diff` response

| Field | Type | Description |
|-------|------|-------------|
| `doc1_id` | string | First document ID |
| `doc2_id` | string | Second document ID |
| `total_changes` | integer | Total number of changes |
| `changes` | array[Change] | Detailed changes |
| `summary` | string | Human-readable summary |

**Change Object:**

| Field | Type | Description |
|-------|------|-------------|
| `type` | string | Change type (see Change Types) |
| `description` | string | Human-readable description |
| `old_value` | any | Previous value (if applicable) |
| `new_value` | any | New value (if applicable) |
| `location` | string | Location in document (char offsets) |

---

### 4.5 ArbitrageQuery

**Endpoint:** `GET /opportunities/arbitrage`

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `j1` | string | ❌ | null | First jurisdiction |
| `j2` | string | ❌ | null | Second jurisdiction |
| `concept` | string | ❌ | null | Filter by concept |
| `rel_delta` | float | ❌ | 0.2 | Min relative threshold difference (0.2 = 20%) |
| `limit` | integer | ❌ | 50 | Max results (1-200) |
| `since` | datetime | ❌ | null | Filter by creation time |

### 4.6 ArbitrageResponse

**Endpoint:** `GET /opportunities/arbitrage` response

```json
{
  "items": [
    {
      "concept": "emissions",
      "unit": "percent",
      "v1": 20.0,
      "v2": 25.0,
      "text1": "Provision text from jurisdiction 1",
      "text2": "Provision text from jurisdiction 2",
      "citation_1": {
        "doc_id": "abc123",
        "start": 1000,
        "end": 1200,
        "source_url": "https://..."
      },
      "citation_2": {
        "doc_id": "def456",
        "start": 500,
        "end": 700,
        "source_url": "https://..."
      }
    }
  ]
}
```

---

### 4.7 GapsQuery

**Endpoint:** `GET /opportunities/gaps`

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `j1` | string | ✅ | - | Source jurisdiction (has provisions) |
| `j2` | string | ✅ | - | Target jurisdiction (missing provisions) |
| `limit` | integer | ❌ | 50 | Max results (1-200) |

### 4.8 GapsResponse

**Endpoint:** `GET /opportunities/gaps` response

```json
{
  "items": [
    {
      "concept": "data controller obligations",
      "example_text": "Data controllers shall...",
      "citation": {
        "doc_id": "abc123",
        "start": 1000,
        "end": 1200,
        "source_url": "https://..."
      }
    }
  ]
}
```

---

### 4.9 Token Request/Response

**Endpoint:** `POST /auth/token`

**Request (form data):**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `username` | string | ✅ | Username |
| `password` | string | ✅ | Password |

**Response:**

| Field | Type | Description |
|-------|------|-------------|
| `access_token` | string | JWT token |
| `token_type` | string | "bearer" |
| `expires_in` | integer | Expiration in seconds (1800 = 30 min) |

---

## 5. Entity Types

### Entity Type Enumeration

| Type | Description | Confidence Range |
|------|-------------|------------------|
| `OBLIGATION` | Mandatory requirements ("shall", "must") | 0.7-0.9 |
| `PROHIBITION` | Prohibitions ("shall not", "must not") | 0.85-0.95 |
| `THRESHOLD` | Numeric limits with units | 0.7-0.9 |
| `JURISDICTION` | Geographic applicability | 0.9-0.95 |
| `INCENTIVE` | Tax credits, grants, subsidies | 0.75-0.9 |
| `PENALTY` | Fines, sanctions, enforcement | 0.75-0.9 |
| `DEADLINE` | Time-bound requirements | 0.8-0.85 |
| `CITATION` | References to other regulations | 0.6-0.8 |

### 5.1 OBLIGATION Entity

**Attributes:**

| Field | Type | Description |
|-------|------|-------------|
| `confidence` | float | Extraction confidence (0-1) |
| `concept` | string | Regulatory concept |
| `context` | string | Surrounding text (±100 chars) |
| `page` | integer | Page number (if available) |

**Pattern Examples:**
- "shall provide annual reports"
- "must maintain records for 7 years"
- "required to notify authorities within 72 hours"

---

### 5.2 THRESHOLD Entity

**Attributes:**

| Field | Type | Description |
|-------|------|-------------|
| `value` | float | Numeric value |
| `unit` | string | Original unit |
| `unit_normalized` | string | Normalized unit |
| `confidence` | float | Extraction confidence |

**Pattern Examples:**
- "25%" → value: 25.0, unit: "%", unit_normalized: "percent"
- "$10,000 USD" → value: 10000.0, unit: "USD", unit_normalized: "USD"
- "50 basis points" → value: 50.0, unit: "bps", unit_normalized: "basis_points"

---

### 5.3 JURISDICTION Entity

**Attributes:**

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Normalized jurisdiction name |
| `confidence` | float | Extraction confidence |

**Pattern Examples:**
- "United States" → name: "US"
- "European Union" → name: "EU"
- "California" → name: "California"

---

### 5.4 INCENTIVE Entity

**Attributes:**

| Field | Type | Description |
|-------|------|-------------|
| `confidence` | float | Extraction confidence |
| `incentive_type` | string | Type (tax_credit, grant, subsidy, etc.) |

**Pattern Examples:**
- "eligible for tax credits"
- "may receive grant funding"
- "qualify for rebates"

---

### 5.5 PENALTY Entity

**Attributes:**

| Field | Type | Description |
|-------|------|-------------|
| `confidence` | float | Extraction confidence |
| `penalty_type` | string | Type (fine, sanction, enforcement, etc.) |

**Pattern Examples:**
- "subject to fines up to $100,000"
- "violations may result in penalties"
- "enforcement actions will be taken"

---

## 6. Enumerations

### 6.1 Source Systems

| Value | Description |
|-------|-------------|
| `SEC` | US Securities and Exchange Commission |
| `EPA` | US Environmental Protection Agency |
| `EU` | European Union regulations |
| `GDPR` | General Data Protection Regulation |
| `FDA` | US Food and Drug Administration |
| `OSHA` | Occupational Safety and Health Administration |
| `Custom` | User-defined sources |

---

### 6.2 Change Types (Diff)

| Type | Description |
|------|-------------|
| `text_added` | New text section |
| `text_removed` | Deleted text section |
| `text_modified` | Changed text section |
| `text_replaced` | Replaced text section |
| `obligation_added` | New obligation |
| `obligation_removed` | Removed obligation |
| `obligation_modified` | Modified obligation |
| `threshold_added` | New threshold |
| `threshold_removed` | Removed threshold |
| `threshold_changed` | Changed threshold value |
| `jurisdiction_added` | New jurisdiction mentioned |
| `jurisdiction_removed` | Jurisdiction no longer mentioned |

---

### 6.3 User Scopes

| Scope | Description |
|-------|-------------|
| `ingest:write` | Ingest documents |
| `ingest:read` | Read ingestion status |
| `opportunities:read` | Query arbitrage/gaps |
| `opportunities:write` | Create custom opportunity definitions |
| `diff:read` | Compare documents |
| `diff:write` | Create diff snapshots |
| `admin` | Full administrative access |

---

### 6.4 HTTP Status Codes

| Code | Meaning | Usage |
|------|---------|-------|
| 200 | OK | Successful request |
| 400 | Bad Request | Invalid input |
| 401 | Unauthorized | Missing/invalid token |
| 403 | Forbidden | Insufficient permissions |
| 404 | Not Found | Resource not found |
| 413 | Payload Too Large | Document exceeds 25 MB |
| 422 | Unprocessable Entity | Validation error |
| 429 | Too Many Requests | Rate limit exceeded |
| 500 | Internal Server Error | Server error |
| 502 | Bad Gateway | Upstream fetch failed |

---

## Appendix: Sample Data

### Sample NormalizedDocument

```json
{
  "document_id": "e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0",
  "source_url": "https://www.sec.gov/rules/final/2023/33-11143.pdf",
  "source_system": "SEC",
  "retrieved_at": "2025-11-18T12:00:00Z",
  "text": "Rule 10b-5 prohibits any person from...",
  "content_sha256": "abc123def456...",
  "title": "Final Rule: Enhanced Disclosures",
  "jurisdiction": "US",
  "content_type": "application/pdf",
  "text_extraction": {
    "engine": "pdfminer",
    "confidence_mean": 0.95,
    "confidence_std": 0.02
  }
}
```

### Sample Entity

```json
{
  "type": "OBLIGATION",
  "text": "shall file quarterly reports",
  "start": 1234,
  "end": 1260,
  "attrs": {
    "confidence": 0.92,
    "concept": "financial disclosure",
    "context": "...all registrants shall file quarterly reports within 45 days...",
    "page": 5
  }
}
```

---

**Document Version:** 2.0.0
**Last Updated:** 2025-11-18
