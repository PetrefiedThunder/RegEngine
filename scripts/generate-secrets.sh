#!/bin/bash

# Generate secure secrets for production deployment

set -e

echo "========================================="
echo "  RegEngine Secret Generation"
echo "========================================="
echo ""

# Generate admin master key
ADMIN_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
echo "Admin Master Key:"
echo "  ADMIN_MASTER_KEY=$ADMIN_KEY"
echo ""

# Generate Neo4j password
NEO4J_PASS=$(python3 -c "import secrets; print(secrets.token_urlsafe(24))")
echo "Neo4j Password:"
echo "  NEO4J_PASSWORD=$NEO4J_PASS"
echo ""

# Generate random database passwords
echo "========================================="
echo ""
echo "IMPORTANT: Save these secrets securely!"
echo "Add them to your secrets manager (AWS Secrets Manager, HashiCorp Vault, etc.)"
echo ""
echo "For AWS deployment, use:"
echo "  aws secretsmanager create-secret --name regengine/admin-key --secret-string '$ADMIN_KEY'"
echo "  aws secretsmanager create-secret --name regengine/neo4j-password --secret-string '$NEO4J_PASS'"
echo ""
echo "========================================="
