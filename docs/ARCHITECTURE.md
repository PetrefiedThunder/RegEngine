# RegEngine v2 - System Architecture

Complete architectural documentation with diagrams, data flows, and component specifications.

---

## Table of Contents

1. [System Overview](#system-overview)
2. [Component Architecture](#component-architecture)
3. [Data Flow](#data-flow)
4. [Graph Schema](#graph-schema)
5. [Deployment Architecture](#deployment-architecture)
6. [Security Architecture](#security-architecture)
7. [Scalability & Performance](#scalability--performance)

---

## 1. System Overview

### High-Level Architecture

```mermaid
graph TB
    subgraph "External Sources"
        URL[Document URLs]
        PDF[PDF Files]
        API[External APIs]
    end

    subgraph "RegEngine v2 Platform"
        subgraph "API Gateway Layer"
            ALB[Load Balancer]
            Auth[JWT Authentication]
            RateLimit[Rate Limiting - Redis]
        end

        subgraph "Core Microservices"
            Ingest[Ingestion Service<br/>:8000]
            NLP[NLP Service<br/>:8100]
            Graph[Graph Service<br/>:8200]
            Opp[Opportunity API<br/>:8300]
            Diff[Diff Engine<br/>:8400]
        end

        subgraph "Message Queue"
            Kafka[Redpanda/Kafka<br/>:9092]
        end

        subgraph "Data Storage"
            S3[S3 Object Storage]
            Neo4j[Neo4j Graph DB<br/>:7687]
            Redis[Redis Cache<br/>:6379]
        end

        subgraph "Observability"
            Prom[Prometheus Metrics]
            Logs[Structured Logs]
        end
    end

    subgraph "Client Applications"
        WebUI[Web Dashboard]
        SDK[Python/TS SDKs]
        Mobile[Mobile Apps]
    end

    URL --> ALB
    PDF --> ALB
    API --> ALB

    ALB --> Auth
    Auth --> RateLimit
    RateLimit --> Ingest
    RateLimit --> Opp
    RateLimit --> Diff

    Ingest --> S3
    Ingest --> Kafka

    Kafka --> NLP
    Kafka --> Graph

    NLP --> S3
    NLP --> Kafka

    Graph --> Neo4j

    Opp --> Neo4j
    Diff --> S3

    Ingest --> Prom
    NLP --> Prom
    Graph --> Prom
    Opp --> Prom
    Diff --> Prom

    Ingest --> Logs
    NLP --> Logs
    Graph --> Logs
    Opp --> Logs
    Diff --> Logs

    ALB --> WebUI
    ALB --> SDK
    ALB --> Mobile
```

---

## 2. Component Architecture

### 2.1 Ingestion Service

**Purpose:** Fetch, normalize, and store regulatory documents.

**Technology Stack:**
- FastAPI 0.115.0
- Boto3 (S3 client)
- kafka-python
- pdfminer.six, pytesseract (OCR)
- Pydantic (validation)

**Key Components:**

```mermaid
graph LR
    subgraph "Ingestion Service"
        API[REST API<br/>/ingest/url]
        Val[URL Validator<br/>SSRF Protection]
        Fetch[HTTP Fetcher<br/>requests]
        Norm[Document Normalizer<br/>PDF/JSON/HTML]
        OCR[OCR Engine<br/>Tesseract]
        Store[S3 Storage<br/>Content-Addressed]
        Emit[Kafka Producer<br/>ingest.normalized]
    end

    API --> Val
    Val --> Fetch
    Fetch --> Norm
    Norm --> OCR
    OCR --> Store
    Store --> Emit
```

**API Endpoints:**
- `POST /ingest/url` - Ingest document from URL
- `POST /auth/token` - Generate JWT
- `GET /health` - Health check
- `GET /metrics` - Prometheus metrics

**Event Schema:**

```json
{
  "event_id": "uuid",
  "document_id": "sha256",
  "source_system": "SEC|EPA|EU|...",
  "source_url": "https://...",
  "raw_s3_path": "s3://bucket/raw/...",
  "normalized_s3_path": "s3://bucket/normalized/...",
  "content_sha256": "hash",
  "timestamp": "ISO8601"
}
```

---

### 2.2 NLP Extraction Service

**Purpose:** Extract regulatory entities using ML-based models.

**Technology Stack:**
- FastAPI 0.115.0
- kafka-python (consumer)
- Legal-BERT (planned) / enhanced regex (current)
- jsonschema (validation)

**Key Components:**

```mermaid
graph TB
    subgraph "NLP Service"
        Consumer[Kafka Consumer<br/>ingest.normalized]
        Fetch[S3 Document Fetcher]
        Extract[ML Extractor<br/>Legal-BERT]
        Patterns[Entity Patterns<br/>Obligations, Thresholds]
        Confidence[Confidence Scorer]
        Intent[Intent Classifier]
        Validate[Schema Validator]
        Emit[Kafka Producer<br/>nlp.extracted]
    end

    Consumer --> Fetch
    Fetch --> Extract
    Extract --> Patterns
    Patterns --> Confidence
    Confidence --> Intent
    Intent --> Validate
    Validate --> Emit
```

**Entities Extracted:**

| Entity Type | Pattern | Confidence |
|-------------|---------|------------|
| OBLIGATION | "shall", "must", "required to" | 0.9 |
| PROHIBITION | "shall not", "must not", "prohibited" | 0.95 |
| THRESHOLD | Numeric + unit (%, USD, tons) | 0.7-0.9 |
| JURISDICTION | "US", "EU", "California" | 0.9-0.95 |
| INCENTIVE | "tax credit", "grant", "subsidy" | 0.75-0.9 |
| PENALTY | "fine", "penalty", "violation" | 0.75-0.9 |
| DEADLINE | "by", "before", "within X days" | 0.8-0.85 |

**Event Schema:**

```json
{
  "event_id": "uuid",
  "document_id": "sha256",
  "source_url": "https://...",
  "entities": [
    {
      "type": "OBLIGATION|THRESHOLD|...",
      "text": "extracted text",
      "start": 123,
      "end": 456,
      "attrs": {
        "confidence": 0.9,
        "concept": "emissions",
        "value": 25.0,
        "unit": "percent"
      }
    }
  ],
  "timestamp": "ISO8601"
}
```

---

### 2.3 Graph Service

**Purpose:** Persist entities into Neo4j temporal graph.

**Technology Stack:**
- FastAPI 0.115.0
- neo4j 5.25.0 (Python driver)
- kafka-python (consumer)

**Key Components:**

```mermaid
graph TB
    subgraph "Graph Service"
        Consumer[Kafka Consumer<br/>nlp.extracted]
        Parser[Entity Parser]
        Mapper[Graph Mapper<br/>Entities → Nodes]
        Temporal[Bitemporal Logic<br/>tx_from, valid_from]
        Upsert[Neo4j Upsert<br/>MERGE + Versioning]
        Index[Constraint Enforcer]
    end

    Consumer --> Parser
    Parser --> Mapper
    Mapper --> Temporal
    Temporal --> Upsert
    Upsert --> Index
```

**Cypher Queries:**

- `CYPHER_UPSERT` - Main upsert with bitemporal versioning
- `CYPHER_PROVISION_HISTORY` - Get all versions of a provision
- `CYPHER_ACTIVE_PROVISIONS_AT_TIME` - Query by timestamp
- `CYPHER_PROVISION_CHANGES` - Query changes in time range

---

### 2.4 Opportunity API

**Purpose:** Query regulatory arbitrage and compliance gaps.

**Technology Stack:**
- FastAPI 0.115.0
- neo4j 5.25.0

**Key Components:**

```mermaid
graph TB
    subgraph "Opportunity API"
        API[REST API]
        Auth[JWT Auth Middleware]
        Rate[Rate Limiter]
        Arb[Arbitrage Detector<br/>Threshold Divergence]
        Gap[Gap Detector<br/>Asymmetric Provisions]
        Query[Cypher Query Builder]
        Format[Response Formatter]
    end

    API --> Auth
    Auth --> Rate
    Rate --> Arb
    Rate --> Gap
    Arb --> Query
    Gap --> Query
    Query --> Format
```

**API Endpoints:**

- `GET /opportunities/arbitrage?j1=US&j2=EU&rel_delta=0.2`
- `GET /opportunities/gaps?j1=EU&j2=US&limit=50`

---

### 2.5 Diff Engine

**Purpose:** Compare documents and detect changes.

**Technology Stack:**
- FastAPI 0.115.0
- difflib (Python standard library)
- boto3 (S3 client)

**Key Components:**

```mermaid
graph TB
    subgraph "Diff Engine"
        API[REST API<br/>/diff]
        Auth[JWT Auth]
        Fetch[S3 Document Fetcher]
        TextDiff[Text Comparison<br/>difflib]
        EntityDiff[Entity Comparison<br/>Obligations/Thresholds]
        ThresholdCalc[Threshold Delta %]
        Summary[Human-Readable Summary]
        Format[JSON Response]
    end

    API --> Auth
    Auth --> Fetch
    Fetch --> TextDiff
    Fetch --> EntityDiff
    EntityDiff --> ThresholdCalc
    TextDiff --> Summary
    EntityDiff --> Summary
    ThresholdCalc --> Summary
    Summary --> Format
```

**Change Types:**

- `text_added` - New text sections
- `text_removed` - Deleted text
- `text_modified` - Changed text
- `obligation_added` - New obligations
- `obligation_removed` - Removed obligations
- `threshold_changed` - Threshold delta (with %)
- `jurisdiction_added` - New jurisdiction mentioned

---

## 3. Data Flow

### 3.1 End-to-End Ingestion Flow

```mermaid
sequenceDiagram
    actor User
    participant API as Ingestion API
    participant S3 as S3 Storage
    participant Kafka as Kafka/Redpanda
    participant NLP as NLP Service
    participant Graph as Graph Service
    participant Neo4j as Neo4j Graph DB

    User->>API: POST /ingest/url {url, source_system}
    API->>API: Validate URL (SSRF check)
    API->>API: Fetch document (HTTP)
    API->>API: Extract text (PDF/OCR)
    API->>S3: Store raw document
    API->>API: Normalize to JSON
    API->>S3: Store normalized document
    API->>Kafka: Publish ingest.normalized event
    API->>User: Return event_id, document_id

    Kafka->>NLP: Consume ingest.normalized
    NLP->>S3: Fetch normalized document
    NLP->>NLP: Extract entities (ML)
    NLP->>NLP: Calculate confidence scores
    NLP->>Kafka: Publish nlp.extracted event

    Kafka->>Graph: Consume nlp.extracted
    Graph->>Graph: Parse entities
    Graph->>Graph: Check for existing provisions
    Graph->>Graph: Close old versions (tx_to, valid_to)
    Graph->>Neo4j: MERGE new provision nodes
    Graph->>Neo4j: Create SUPERSEDES relationships
    Graph->>Neo4j: Link to Document, Concept, Jurisdiction
```

### 3.2 Query Flow (Arbitrage Detection)

```mermaid
sequenceDiagram
    actor User
    participant API as Opportunity API
    participant Auth as JWT Middleware
    participant Rate as Rate Limiter
    participant Neo4j as Neo4j Graph DB

    User->>API: GET /opportunities/arbitrage?j1=US&j2=EU
    API->>Auth: Validate JWT token
    Auth->>Auth: Check "opportunities:read" scope
    Auth->>Rate: Check rate limit
    Rate->>Rate: Redis token bucket
    Rate->>API: Allow request

    API->>API: Build Cypher query
    API->>Neo4j: Execute arbitrage query
    Neo4j->>Neo4j: MATCH provisions by jurisdiction
    Neo4j->>Neo4j: Filter by threshold delta
    Neo4j->>Neo4j: Return provision pairs

    Neo4j->>API: Return results
    API->>API: Format response (add provenance)
    API->>User: Return JSON {items: [...]}
```

### 3.3 Diff Flow

```mermaid
sequenceDiagram
    actor User
    participant API as Diff API
    participant S3 as S3 Storage
    participant Diff as Diff Engine
    participant Format as Response Formatter

    User->>API: POST /diff {doc1_id, doc2_id}
    API->>S3: Fetch doc1 (normalized)
    API->>S3: Fetch doc2 (normalized)
    API->>Diff: compare_documents(doc1, doc2)

    Diff->>Diff: Compare text (difflib)
    Diff->>Diff: Compare obligations
    Diff->>Diff: Compare thresholds
    Diff->>Diff: Calculate % deltas
    Diff->>Diff: Generate summary

    Diff->>Format: DocumentDiff object
    Format->>User: Return JSON {changes, summary}
```

---

## 4. Graph Schema

### 4.1 Node Types

```mermaid
graph TB
    subgraph "Core Nodes"
        Doc[Document<br/>id, source_url, created_at]
        Prov[Provision<br/>pid, version_id, text, hash<br/>tx_from, tx_to<br/>valid_from, valid_to<br/>superseded, version]
        Conc[Concept<br/>name]
        Juris[Jurisdiction<br/>name]
        Thresh[Threshold<br/>pid, version_id<br/>value, unit, unit_normalized]
        Cite[Provenance<br/>doc_id, start, end, page]
    end

    Doc -->|IN_DOCUMENT| Prov
    Prov -->|ABOUT| Conc
    Prov -->|APPLIES_TO| Juris
    Prov -->|HAS_THRESHOLD| Thresh
    Prov -->|PROVENANCE| Cite
    Prov -->|SUPERSEDES| Prov
    Doc -->|MENTIONS| Juris
```

### 4.2 Bitemporal Model

```mermaid
timeline
    title Provision Lifecycle (Bitemporal)
    section Transaction Time (tx_from → tx_to)
        2024-01-01 : Provision v1 created (tx_from)
        2024-06-01 : Provision v2 created, v1 closed (v1.tx_to, v2.tx_from)
        2024-12-01 : Provision v3 created, v2 closed (v2.tx_to, v3.tx_from)
    section Valid Time (valid_from → valid_to)
        2024-01-15 : v1 effective (valid_from)
        2024-07-01 : v2 effective, v1 expires (v1.valid_to, v2.valid_from)
        2024-12-15 : v3 effective, v2 expires (v2.valid_to, v3.valid_from)
```

**Bitemporal Attributes:**

| Field | Type | Description |
|-------|------|-------------|
| `tx_from` | timestamp | When provision was created in DB |
| `tx_to` | timestamp \| null | When provision was superseded (null = current) |
| `valid_from` | timestamp | When regulation became effective |
| `valid_to` | timestamp \| null | When regulation expires (null = still valid) |
| `superseded` | boolean | True if newer version exists |
| `version` | integer | Version number (1, 2, 3, ...) |

**Querying Historical State:**

```cypher
// Get active provisions at specific time
MATCH (p:Provision)-[:IN_DOCUMENT]->(d:Document {id: $doc_id})
WHERE p.tx_from <= $timestamp
  AND (p.tx_to IS NULL OR p.tx_to > $timestamp)
  AND p.valid_from <= $timestamp
  AND (p.valid_to IS NULL OR p.valid_to > $timestamp)
RETURN p, d
```

### 4.3 Example Graph Queries

**Find all versions of a provision:**

```cypher
MATCH (p:Provision {pid: $pid})
OPTIONAL MATCH (p)-[:SUPERSEDES*]->(older:Provision)
RETURN p, older
ORDER BY p.version DESC
```

**Detect threshold changes between jurisdictions:**

```cypher
MATCH (p1:Provision)-[:HAS_THRESHOLD]->(t1:Threshold),
      (p1)-[:ABOUT]->(c:Concept),
      (p1)-[:APPLIES_TO]->(j1:Jurisdiction {name: $j1}),
      (p2:Provision)-[:HAS_THRESHOLD]->(t2:Threshold),
      (p2)-[:ABOUT]->(c),
      (p2)-[:APPLIES_TO]->(j2:Jurisdiction {name: $j2})
WHERE t1.unit_normalized = t2.unit_normalized
  AND abs(t1.value - t2.value) / t1.value > $rel_delta
RETURN c.name AS concept,
       t1.unit_normalized AS unit,
       t1.value AS v1,
       t2.value AS v2,
       p1, p2
```

---

## 5. Deployment Architecture

### 5.1 Development Environment

```mermaid
graph TB
    subgraph "Docker Compose"
        subgraph "Services (5)"
            Ing[Ingestion:8000]
            NLP[NLP:8100]
            Gr[Graph:8200]
            Opp[Opportunity:8300]
            Diff[Diff:8400]
        end

        subgraph "Infrastructure (4)"
            LS[LocalStack:4566<br/>S3 Emulation]
            RP[Redpanda:9092<br/>Kafka]
            N4[Neo4j:7687,7474<br/>Graph DB]
            RD[Redis:6379<br/>Cache]
        end

        Ing --> LS
        Ing --> RP
        NLP --> LS
        NLP --> RP
        Gr --> RP
        Gr --> N4
        Opp --> N4
        Diff --> LS
        Ing --> RD
        Opp --> RD
        Diff --> RD
    end
```

### 5.2 Production Environment (AWS)

```mermaid
graph TB
    subgraph "AWS Cloud"
        subgraph "Public Subnet"
            ALB[Application Load Balancer<br/>HTTPS/TLS]
            NAT[NAT Gateway]
        end

        subgraph "Private Subnet - EKS Cluster"
            subgraph "Pods"
                Ing[Ingestion Pod x3]
                Opp[Opportunity Pod x2]
                Diff[Diff Pod x2]
            end

            subgraph "Background Workers"
                NLP[NLP Consumer x5]
                Graph[Graph Consumer x5]
            end
        end

        subgraph "Managed Services"
            MSK[MSK - Managed Kafka<br/>Multi-AZ]
            RDS[ElastiCache Redis<br/>Multi-AZ]
            S3[S3 Buckets<br/>Versioned + Encrypted]
        end

        subgraph "Self-Hosted"
            Neo4j[Neo4j Enterprise<br/>EC2 Auto Scaling<br/>Multi-AZ]
        end

        subgraph "Monitoring"
            CW[CloudWatch Logs]
            Prom[Prometheus<br/>EKS Pod]
            Graf[Grafana<br/>EKS Pod]
        end
    end

    Internet -->|HTTPS| ALB
    ALB --> Ing
    ALB --> Opp
    ALB --> Diff

    Ing --> S3
    Ing --> MSK
    NLP --> S3
    NLP --> MSK
    Graph --> MSK
    Graph --> Neo4j
    Opp --> Neo4j
    Diff --> S3

    Ing --> RDS
    Opp --> RDS
    Diff --> RDS

    Ing --> Prom
    Opp --> Prom
    Diff --> Prom
    NLP --> Prom
    Graph --> Prom

    Prom --> Graf

    Ing --> CW
    Opp --> CW
    Diff --> CW
```

### 5.3 Multi-Region Deployment

```mermaid
graph TB
    subgraph "Global"
        R53[Route53<br/>Geo-Routing]
        CF[CloudFront CDN]
    end

    subgraph "Region: US-EAST-1"
        ALB1[ALB]
        EKS1[EKS Cluster]
        S31[S3 Bucket]
        Neo1[Neo4j Primary]
    end

    subgraph "Region: EU-WEST-1"
        ALB2[ALB]
        EKS2[EKS Cluster]
        S32[S3 Bucket]
        Neo2[Neo4j Replica]
    end

    R53 --> CF
    CF --> ALB1
    CF --> ALB2

    ALB1 --> EKS1
    ALB2 --> EKS2

    EKS1 --> S31
    EKS2 --> S32

    EKS1 --> Neo1
    EKS2 --> Neo2

    Neo1 -->|Replication| Neo2
    S31 -->|Cross-Region Replication| S32
```

---

## 6. Security Architecture

### 6.1 Authentication Flow

```mermaid
sequenceDiagram
    actor User
    participant API as Any Service
    participant Auth as JWT Middleware
    participant Redis as Redis Cache

    User->>API: POST /auth/token {username, password}
    API->>API: Verify credentials (bcrypt)
    API->>API: Generate JWT (HS256)
    API->>User: Return {access_token, expires_in}

    User->>API: GET /endpoint (Bearer: token)
    API->>Auth: Validate token
    Auth->>Auth: Decode JWT
    Auth->>Auth: Check expiration
    Auth->>Auth: Verify signature
    Auth->>Auth: Check scopes
    Auth->>Redis: Check rate limit
    Redis->>Auth: Allow/Deny
    Auth->>API: User object
    API->>User: Protected resource
```

### 6.2 Network Security Layers

```mermaid
graph TB
    subgraph "Layer 1: Internet"
        WAF[AWS WAF<br/>DDoS Protection]
        Shield[AWS Shield]
    end

    subgraph "Layer 2: Load Balancer"
        ALB[ALB<br/>TLS Termination<br/>X-Forwarded-For]
    end

    subgraph "Layer 3: API Gateway"
        Auth[JWT Auth]
        Rate[Rate Limiting]
        Val[Input Validation]
    end

    subgraph "Layer 4: Application"
        SSRF[SSRF Protection]
        Sanitize[Input Sanitization]
        Crypto[Data Encryption]
    end

    subgraph "Layer 5: Data"
        S3Enc[S3 Encryption-at-Rest]
        Neo4jAuth[Neo4j Auth]
        KafkaACL[Kafka ACLs]
    end

    Internet --> WAF
    WAF --> Shield
    Shield --> ALB
    ALB --> Auth
    Auth --> Rate
    Rate --> Val
    Val --> SSRF
    SSRF --> Sanitize
    Sanitize --> Crypto
    Crypto --> S3Enc
    Crypto --> Neo4jAuth
    Crypto --> KafkaACL
```

### 6.3 Secrets Management

```mermaid
graph LR
    subgraph "Development"
        Env[.env file<br/>Local secrets]
    end

    subgraph "Staging"
        SSM[AWS Systems Manager<br/>Parameter Store]
    end

    subgraph "Production"
        SM[AWS Secrets Manager<br/>Auto-rotation]
        Vault[HashiCorp Vault<br/>Dynamic secrets]
    end

    Env -->|Don't commit| Git
    SSM -->|Inject at runtime| EKS
    SM -->|Inject at runtime| EKS
    Vault -->|Inject at runtime| EKS
```

---

## 7. Scalability & Performance

### 7.1 Horizontal Scaling

```mermaid
graph TB
    subgraph "Auto Scaling"
        ALB[Load Balancer]

        subgraph "Ingestion Tier"
            I1[Ingestion Pod 1]
            I2[Ingestion Pod 2]
            I3[Ingestion Pod N]
        end

        subgraph "NLP Tier (Kafka Consumer Group)"
            N1[NLP Consumer 1]
            N2[NLP Consumer 2]
            N3[NLP Consumer N]
        end

        subgraph "Graph Tier (Kafka Consumer Group)"
            G1[Graph Consumer 1]
            G2[Graph Consumer 2]
            G3[Graph Consumer N]
        end

        subgraph "Query Tier"
            O1[Opportunity Pod 1]
            O2[Opportunity Pod 2]
            O3[Opportunity Pod N]
        end
    end

    subgraph "Data Layer (Sharded)"
        Kafka[Kafka<br/>Partitioned Topics]
        Neo4j[Neo4j Cluster<br/>Read Replicas]
        Redis[Redis Cluster<br/>Sharded]
    end

    ALB --> I1
    ALB --> I2
    ALB --> I3

    I1 --> Kafka
    I2 --> Kafka
    I3 --> Kafka

    Kafka --> N1
    Kafka --> N2
    Kafka --> N3

    Kafka --> G1
    Kafka --> G2
    Kafka --> G3

    G1 --> Neo4j
    G2 --> Neo4j
    G3 --> Neo4j

    O1 --> Neo4j
    O2 --> Neo4j
    O3 --> Neo4j

    I1 --> Redis
    O1 --> Redis
```

### 7.2 Performance Optimization Strategies

| Layer | Strategy | Impact |
|-------|----------|--------|
| **API** | Redis rate limiting | Prevent abuse, ensure SLA |
| **Ingestion** | Async S3 uploads | 3x throughput |
| **NLP** | Kafka consumer group (5 workers) | 5x parallelism |
| **Graph** | Batch upserts (100 provisions/tx) | 10x write speed |
| **Queries** | Neo4j indexes (Document.id, Provision.pid) | 50x query speed |
| **Caching** | Redis cache for frequent queries | 100x read speed |

---

## Appendix: Technology Decisions

### Why Neo4j?

- **Relationship-first:** Regulatory citations are inherently graphs
- **Cypher queries:** Expressive query language for complex patterns
- **Bitemporal support:** Native timestamp indexing
- **ACID compliance:** Data integrity for compliance use cases

### Why Kafka (Redpanda)?

- **Event sourcing:** Full audit trail of all documents
- **Decoupling:** Services can evolve independently
- **Replay:** Re-process historical documents
- **Scalability:** Partition-based parallelism

### Why FastAPI?

- **Performance:** Async/await for high throughput
- **Auto-docs:** OpenAPI/Swagger generation
- **Type safety:** Pydantic validation
- **Developer experience:** Fast iteration

---

**Document Version:** 2.0.0
**Last Updated:** 2025-11-18
