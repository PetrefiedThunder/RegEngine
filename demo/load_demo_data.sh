#!/bin/bash

# Load demo dataset into RegEngine

set -e

echo "========================================="
echo "  RegEngine Demo Data Loader"
echo "========================================="
echo ""

# Check if API key exists
if [ -f ../.api-keys ]; then
    source ../.api-keys
    API_KEY=$DEMO_KEY
else
    echo "Error: .api-keys file not found. Please run scripts/init-demo-keys.sh first"
    exit 1
fi

# Configuration
INGESTION_URL="${INGESTION_URL:-http://localhost:8000}"
DOCUMENTS_DIR="./documents"

# Function to ingest a document
ingest_document() {
    local file=$1
    local filename=$(basename "$file")

    echo "Ingesting: $filename"

    # Create a temporary file with the document as a URL-accessible resource
    # For demo, we'll use the file:// protocol (in production, use actual URLs)

    # Read the JSON file and extract metadata
    title=$(jq -r '.title' "$file")
    jurisdiction=$(jq -r '.jurisdiction' "$file")
    doc_id=$(jq -r '.id' "$file")

    # For demo purposes, we'll post the JSON directly to the ingestion API
    # In production, the ingestion service would fetch from a URL

    response=$(curl -s -w "\n%{http_code}" -X POST "$INGESTION_URL/ingest/url" \
        -H "Content-Type: application/json" \
        -H "X-RegEngine-API-Key: $API_KEY" \
        -d @"$file")

    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | sed '$d')

    if [ "$http_code" = "200" ]; then
        echo "  ✓ Success: $title ($jurisdiction)"
        echo "    Document ID: $doc_id"
    else
        echo "  ✗ Failed: $title"
        echo "    HTTP $http_code: $body"
        return 1
    fi

    echo ""
}

# Wait for services to be ready
echo "Checking if RegEngine services are running..."
until curl -sf "$INGESTION_URL/health" > /dev/null 2>&1; do
    echo "Waiting for ingestion service..."
    sleep 2
done
echo "✓ Ingestion service is ready"
echo ""

# Ingest all demo documents
echo "Starting document ingestion..."
echo ""

document_count=0
success_count=0

for doc in "$DOCUMENTS_DIR"/*.json; do
    if [ -f "$doc" ]; then
        document_count=$((document_count + 1))
        if ingest_document "$doc"; then
            success_count=$((success_count + 1))
        fi
        sleep 1  # Rate limiting
    fi
done

echo "========================================="
echo "  Ingestion Complete"
echo "========================================="
echo "Total documents: $document_count"
echo "Successfully ingested: $success_count"
echo "Failed: $((document_count - success_count))"
echo ""
echo "Note: Documents are being processed in the background."
echo "NLP extraction and graph population will take 30-60 seconds."
echo ""
echo "To query the data, run:"
echo "  bash demo_queries.sh"
echo ""
