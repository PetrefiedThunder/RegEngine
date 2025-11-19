# RegEngine v2 - Deployment Guide

Complete deployment instructions for local development, staging, and production environments.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Local Development Setup](#local-development-setup)
3. [Environment Variables](#environment-variables)
4. [Running Services](#running-services)
5. [Testing the System](#testing-the-system)
6. [Production Deployment](#production-deployment)
7. [Monitoring & Observability](#monitoring--observability)
8. [Troubleshooting](#troubleshooting)

---

## 1. Prerequisites

### Required Software

- **Docker** >= 20.10
- **Docker Compose** >= 2.0
- **Python** >= 3.11 (for local development)
- **Make** (optional, for convenience commands)

### Recommended Tools

- **curl** or **httpie** - API testing
- **jq** - JSON processing
- **AWS CLI** - S3 operations (production)
- **kubectl** - Kubernetes management (production)

---

## 2. Local Development Setup

### Step 1: Clone Repository

```bash
git clone https://github.com/PetrefiedThunder/RegEngine.git
cd RegEngine
```

### Step 2: Start Infrastructure Services

```bash
docker-compose up -d localstack redpanda neo4j redis
```

This starts:
- **LocalStack** (S3 emulation) on port 4566
- **Redpanda** (Kafka) on port 9092
- **Neo4j** (Graph DB) on ports 7687 (bolt), 7474 (web UI)
- **Redis** (Rate limiting) on port 6379

### Step 3: Initialize S3 Buckets

```bash
make init-local
```

Or manually:

```bash
aws --endpoint-url=http://localhost:4566 \
    s3 mb s3://reg-engine-raw-data-dev

aws --endpoint-url=http://localhost:4566 \
    s3 mb s3://reg-engine-processed-data-dev
```

### Step 4: Start All Microservices

```bash
docker-compose up -d
```

Or start individually:

```bash
docker-compose up -d ingestion-service
docker-compose up -d nlp-service
docker-compose up -d graph-service
docker-compose up -d opportunity-api
docker-compose up -d diff-service
```

### Step 5: Verify Services

```bash
# Check all services are running
docker-compose ps

# Test health endpoints
curl http://localhost:8000/health  # Ingestion
curl http://localhost:8300/health  # Opportunity
curl http://localhost:8400/health  # Diff
```

---

## 3. Environment Variables

### Core Configuration

Create a `.env` file in the project root:

```bash
# Logging
LOG_LEVEL=INFO

# AWS / S3
AWS_ENDPOINT_URL=http://localstack:4566
AWS_REGION=us-east-1
RAW_DATA_BUCKET=reg-engine-raw-data-dev
PROCESSED_DATA_BUCKET=reg-engine-processed-data-dev

# Kafka / Redpanda
KAFKA_BOOTSTRAP_SERVERS=redpanda:9092
KAFKA_TOPIC_NORMALIZED=ingest.normalized
KAFKA_TOPIC_NLP=nlp.extracted

# Neo4j
NEO4J_URI=bolt://neo4j:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=letmein

# Redis
REDIS_URL=redis://redis:6379/0

# JWT Authentication
JWT_SECRET_KEY=your-secret-key-change-in-production-use-openssl-rand
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Rate Limiting
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_WINDOW_SECONDS=60
```

### Production Environment Variables

For production deployment, use secrets management:

```bash
# AWS Secrets Manager
aws secretsmanager create-secret \
    --name regengine/jwt-secret \
    --secret-string "$(openssl rand -base64 32)"

# Kubernetes Secrets
kubectl create secret generic regengine-secrets \
    --from-literal=jwt-secret=$(openssl rand -base64 32) \
    --from-literal=neo4j-password=<secure-password>
```

---

## 4. Running Services

### Option 1: Docker Compose (Recommended for Development)

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop all services
docker-compose down

# Clean everything (including volumes)
docker-compose down -v
```

### Option 2: Local Python (for Development)

```bash
# Terminal 1: Ingestion Service
cd services/ingestion
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000

# Terminal 2: NLP Service
cd services/nlp
pip install -r requirements.txt
python -m app.consumer

# Terminal 3: Graph Service
cd services/graph
pip install -r requirements.txt
python -m app.consumer

# Terminal 4: Opportunity API
cd services/opportunity
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8300

# Terminal 5: Diff Service
cd services/diff
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8400
```

---

## 5. Testing the System

### Step 1: Get Authentication Token

```bash
curl -X POST http://localhost:8000/auth/token \
  -d "username=admin&password=secret" \
  -H "Content-Type: application/x-www-form-urlencoded"
```

Response:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

Save the token:
```bash
export TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

### Step 2: Ingest a Document

```bash
curl -X POST http://localhost:8000/ingest/url \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://www.sec.gov/rules/final/2023/33-11143.pdf",
    "source_system": "SEC"
  }'
```

Response:
```json
{
  "event_id": "a1b2c3d4-...",
  "document_id": "e5f6g7h8...",
  "source_system": "SEC",
  "source_url": "https://www.sec.gov/rules/final/2023/33-11143.pdf",
  "raw_s3_path": "s3://reg-engine-raw-data-dev/raw/e5f6g7h8.../...",
  "normalized_s3_path": "s3://reg-engine-processed-data-dev/normalized/...",
  "content_sha256": "abc123...",
  "timestamp": "2025-11-18T12:00:00Z"
}
```

### Step 3: Query for Regulatory Arbitrage

```bash
curl "http://localhost:8300/opportunities/arbitrage?j1=US&j2=EU&limit=10" \
  -H "Authorization: Bearer $TOKEN"
```

### Step 4: Compare Two Documents

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

## 6. Production Deployment

### Architecture Overview

```
Internet → ALB → EKS Cluster → Services
                      ↓
                  MSK (Kafka)
                      ↓
                  Neo4j (Graph)
                      ↓
                  S3 (Storage)
```

### Step 1: Terraform Infrastructure

```bash
cd infra

# Initialize Terraform
terraform init

# Plan deployment
terraform plan -var-file=production.tfvars

# Apply infrastructure
terraform apply -var-file=production.tfvars
```

### Step 2: Build and Push Docker Images

```bash
# Login to ECR
aws ecr get-login-password --region us-east-1 | \
    docker login --username AWS --password-stdin <account-id>.dkr.ecr.us-east-1.amazonaws.com

# Build images
docker build -t regengine/ingestion:v2.0.0 services/ingestion
docker build -t regengine/nlp:v2.0.0 services/nlp
docker build -t regengine/graph:v2.0.0 services/graph
docker build -t regengine/opportunity:v2.0.0 services/opportunity
docker build -t regengine/diff:v2.0.0 services/diff

# Tag for ECR
docker tag regengine/ingestion:v2.0.0 <account-id>.dkr.ecr.us-east-1.amazonaws.com/regengine/ingestion:v2.0.0

# Push to ECR
docker push <account-id>.dkr.ecr.us-east-1.amazonaws.com/regengine/ingestion:v2.0.0
```

### Step 3: Deploy to Kubernetes

```bash
# Configure kubectl
aws eks update-kubeconfig --region us-east-1 --name regengine-cluster

# Apply Kubernetes manifests
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/secrets.yaml
kubectl apply -f k8s/services/
kubectl apply -f k8s/deployments/
kubectl apply -f k8s/ingress.yaml

# Verify deployments
kubectl get pods -n regengine
kubectl get svc -n regengine
```

### Step 4: Configure DNS

```bash
# Get LoadBalancer hostname
kubectl get ingress -n regengine regengine-ingress

# Update Route53
aws route53 change-resource-record-sets \
    --hosted-zone-id Z1234567890ABC \
    --change-batch file://dns-update.json
```

### Step 5: Verify Production Deployment

```bash
# Test endpoints
curl https://api.regengine.io/health
curl https://api.regengine.io/metrics

# Check TLS
openssl s_client -connect api.regengine.io:443 -servername api.regengine.io
```

---

## 7. Monitoring & Observability

### Metrics (Prometheus)

Access metrics endpoints:

```bash
curl http://localhost:8000/metrics  # Ingestion
curl http://localhost:8300/metrics  # Opportunity
curl http://localhost:8400/metrics  # Diff
```

### Grafana Dashboards

Import pre-built dashboards:

1. Navigate to `http://localhost:3000` (if Grafana installed)
2. Import `monitoring/dashboards/regengine-overview.json`
3. Import `monitoring/dashboards/service-health.json`

### Logs (Structlog)

View structured logs:

```bash
# Docker Compose
docker-compose logs -f ingestion-service | jq .

# Kubernetes
kubectl logs -f -n regengine deployment/ingestion-service | jq .
```

### Alerting

Configure alerts in `monitoring/alerts/regengine-alerts.yaml`:

```yaml
groups:
  - name: regengine
    rules:
      - alert: HighErrorRate
        expr: rate(ingestion_requests_total{status="500"}[5m]) > 0.05
        for: 5m
        annotations:
          summary: "High error rate on ingestion service"
```

---

## 8. Troubleshooting

### Issue: Services Not Starting

**Symptom:** Docker containers exiting immediately

**Solution:**

```bash
# Check logs
docker-compose logs ingestion-service

# Common issues:
# 1. Port conflicts
lsof -i :8000

# 2. Missing dependencies
docker-compose build --no-cache

# 3. Environment variables
docker-compose config
```

### Issue: Kafka Consumer Not Processing Messages

**Symptom:** Messages in Kafka but not appearing in Neo4j

**Solution:**

```bash
# Check Kafka topics
docker exec -it redpanda rpk topic list
docker exec -it redpanda rpk topic consume ingest.normalized

# Check consumer logs
docker-compose logs nlp-service
docker-compose logs graph-service

# Reset consumer group
docker exec -it redpanda rpk group delete graph-service
```

### Issue: Neo4j Connection Refused

**Symptom:** `neo4j.exceptions.ServiceUnavailable`

**Solution:**

```bash
# Check Neo4j is running
docker-compose ps neo4j

# Check Neo4j logs
docker-compose logs neo4j

# Verify connection
docker exec -it neo4j cypher-shell -u neo4j -p letmein

# Recreate container
docker-compose down neo4j
docker-compose up -d neo4j
```

### Issue: S3 403 Forbidden (LocalStack)

**Symptom:** `boto3.exceptions.S3UploadFailedError`

**Solution:**

```bash
# Check bucket exists
aws --endpoint-url=http://localhost:4566 s3 ls

# Recreate buckets
make init-local

# Check credentials
echo $AWS_ACCESS_KEY_ID
echo $AWS_SECRET_ACCESS_KEY
```

### Issue: Rate Limit Errors

**Symptom:** `429 Too Many Requests`

**Solution:**

```bash
# Check Redis
docker-compose logs redis

# Check rate limit keys
docker exec -it redis redis-cli KEYS "ratelimit:*"

# Clear rate limits (development only)
docker exec -it redis redis-cli FLUSHDB

# Adjust limits in .env
RATE_LIMIT_REQUESTS=200
```

### Issue: Authentication Failing

**Symptom:** `401 Unauthorized`

**Solution:**

```bash
# Verify token
echo $TOKEN | cut -d. -f2 | base64 -d | jq .

# Generate new token
curl -X POST http://localhost:8000/auth/token \
  -d "username=admin&password=secret"

# Check JWT secret consistency across services
docker-compose config | grep JWT_SECRET_KEY
```

---

## Quick Reference Commands

```bash
# Full system restart
docker-compose down -v && docker-compose up -d

# Watch all logs
docker-compose logs -f

# Smoke test all services
for port in 8000 8100 8200 8300 8400; do
  curl -s http://localhost:$port/health | jq .
done

# Check Prometheus metrics
curl -s http://localhost:8000/metrics | grep ingestion_requests_total

# Neo4j query
docker exec -it neo4j cypher-shell -u neo4j -p letmein \
  "MATCH (d:Document) RETURN count(d)"

# Kafka topic info
docker exec -it redpanda rpk topic describe ingest.normalized
```

---

## Support

For issues or questions:

- **Documentation:** `docs/`
- **GitHub Issues:** https://github.com/PetrefiedThunder/RegEngine/issues
- **Email:** support@regengine.io

---

**Document Version:** 2.0.0
**Last Updated:** 2025-11-18
