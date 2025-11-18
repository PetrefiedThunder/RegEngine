#!/bin/bash

# Demo queries for RegEngine

set -e

# Load API key
if [ -f ../.api-keys ]; then
    source ../.api-keys
    API_KEY=$DEMO_KEY
else
    echo "Error: .api-keys file not found"
    exit 1
fi

OPPORTUNITY_URL="${OPPORTUNITY_URL:-http://localhost:8300}"

echo "========================================="
echo "  RegEngine Demo Queries"
echo "========================================="
echo ""

# Wait for services
echo "Waiting for opportunity API..."
until curl -sf "$OPPORTUNITY_URL/health" > /dev/null 2>&1; do
    sleep 2
done
echo "✓ Opportunity API is ready"
echo ""

echo "Waiting for data processing (30 seconds)..."
sleep 30
echo ""

# Query 1: Capital adequacy threshold arbitrage
echo "========================================="
echo "Query 1: Capital Adequacy Threshold Arbitrage"
echo "========================================="
echo ""
echo "Finding differences in capital requirements between US and EU..."
echo ""

curl -s "$OPPORTUNITY_URL/opportunities/arbitrage?j1=US&j2=EU&concept=capital&limit=10" \
    -H "X-RegEngine-API-Key: $API_KEY" | jq '.'

echo ""
echo ""

# Query 2: Regulatory gaps between EU and UK
echo "========================================="
echo "Query 2: Regulatory Gaps (EU vs UK)"
echo "========================================="
echo ""
echo "Finding regulatory concepts present in EU but not in UK..."
echo ""

curl -s "$OPPORTUNITY_URL/opportunities/gaps?j1=EU&j2=UK&limit=10" \
    -H "X-RegEngine-API-Key: $API_KEY" | jq '.'

echo ""
echo ""

# Query 3: Liquidity requirement differences
echo "========================================="
echo "Query 3: Liquidity Requirement Differences"
echo "========================================="
echo ""
echo "Comparing liquidity thresholds across jurisdictions..."
echo ""

curl -s "$OPPORTUNITY_URL/opportunities/arbitrage?concept=liquidity&rel_delta=0.1&limit=10" \
    -H "X-RegEngine-API-Key: $API_KEY" | jq '.'

echo ""
echo ""

# Query 4: All gaps between US and UK
echo "========================================="
echo "Query 4: Gaps Analysis (US vs UK)"
echo "========================================="
echo ""
echo "Identifying requirements in US but missing in UK..."
echo ""

curl -s "$OPPORTUNITY_URL/opportunities/gaps?j1=US&j2=UK&limit=10" \
    -H "X-RegEngine-API-Key: $API_KEY" | jq '.'

echo ""
echo ""

# Summary
echo "========================================="
echo "  Demo Complete"
echo "========================================="
echo ""
echo "These queries demonstrate RegEngine's ability to:"
echo "  ✓ Extract obligations and thresholds from regulations"
echo "  ✓ Identify arbitrage opportunities across jurisdictions"
echo "  ✓ Detect regulatory gaps"
echo "  ✓ Provide provenance and citations"
echo ""
echo "For more complex queries, see the API documentation."
echo ""
