SHELL := /bin/bash

init-local:
aws --endpoint-url=$${AWS_ENDPOINT_URL:-http://localhost:4566} s3 mb s3://reg-engine-raw-data-dev || true
aws --endpoint-url=$${AWS_ENDPOINT_URL:-http://localhost:4566} s3 mb s3://reg-engine-processed-data-dev || true

up:
docker-compose up --build -d

down:
docker-compose down -v

smoke-ingest:
curl -sS -X POST http://localhost:8000/ingest/url \
  -H 'Content-Type: application/json' \
  -d '{"url":"https://www.federalregister.gov/api/v1/documents/2023-12345.json","source_system":"Federal Register"}' | jq .

consume-normalized:
docker exec -it $$(docker ps -qf name=redpanda) rpk topic consume ingest.normalized -n 1

fmt:
black services

pytest:
pytest -q services/*/tests
