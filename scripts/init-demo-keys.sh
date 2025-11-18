#!/bin/bash

# Initialize demo API keys for local development

set -e

echo "Waiting for admin service to be ready..."
until curl -sf http://localhost:8400/health > /dev/null 2>&1; do
  sleep 2
done

echo "Admin service is ready!"

# Create demo key
echo "Creating demo API key..."
DEMO_KEY_RESPONSE=$(curl -sf -X POST http://localhost:8400/admin/keys \
  -H "Content-Type: application/json" \
  -H "X-Admin-Key: dev-admin-key-change-in-production" \
  -d '{
    "name": "Demo Key",
    "rate_limit_per_minute": 100,
    "scopes": ["read", "ingest"]
  }')

DEMO_KEY=$(echo "$DEMO_KEY_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['api_key'])")

# Create admin key
echo "Creating admin API key..."
ADMIN_KEY_RESPONSE=$(curl -sf -X POST http://localhost:8400/admin/keys \
  -H "Content-Type: application/json" \
  -H "X-Admin-Key: dev-admin-key-change-in-production" \
  -d '{
    "name": "Admin Key",
    "rate_limit_per_minute": 1000,
    "scopes": ["read", "ingest", "admin"]
  }')

ADMIN_KEY=$(echo "$ADMIN_KEY_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['api_key'])")

echo ""
echo "========================================="
echo "  RegEngine API Keys Generated"
echo "========================================="
echo ""
echo "Demo Key (100 req/min):"
echo "  $DEMO_KEY"
echo ""
echo "Admin Key (1000 req/min):"
echo "  $ADMIN_KEY"
echo ""
echo "========================================="
echo ""
echo "Usage examples:"
echo ""
echo "# Ingest a document:"
echo "curl -X POST http://localhost:8000/ingest/url \\"
echo "  -H 'Content-Type: application/json' \\"
echo "  -H 'X-RegEngine-API-Key: $DEMO_KEY' \\"
echo "  -d '{\"url\": \"https://example.com/regulation.pdf\", \"source_system\": \"demo\"}'"
echo ""
echo "# Query opportunities:"
echo "curl 'http://localhost:8300/opportunities/gaps?j1=US&j2=EU&limit=10' \\"
echo "  -H 'X-RegEngine-API-Key: $DEMO_KEY'"
echo ""
echo "========================================="
echo ""
echo "IMPORTANT: Save these keys! They will not be shown again."
echo ""

# Write keys to a file for easy access during development
cat > .api-keys <<EOF
# RegEngine API Keys (Development Only - Do Not Commit!)
DEMO_KEY=$DEMO_KEY
ADMIN_KEY=$ADMIN_KEY
EOF

echo "Keys also saved to .api-keys (gitignored)"
