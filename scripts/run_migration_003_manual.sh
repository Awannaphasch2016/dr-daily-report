#!/bin/bash
# Manual migration execution for adding computed_at and expires_at columns
#
# This script invokes the worker Lambda's migration handler to add missing columns.
# The Lambda has VPC access to Aurora, we don't.
#
# Usage: ./scripts/run_migration_003_manual.sh

set -e

echo "🔧 Running Migration 003: Add computed_at and expires_at columns"
echo "================================================================"
echo ""

# Create payload
cat > /tmp/migration_payload.json << 'EOF'
{
  "migration": "add_strategy_column"
}
EOF

echo "📤 Invoking worker Lambda migration handler..."
aws lambda invoke \
  --function-name dr-daily-report-report-worker-dev \
  --cli-binary-format raw-in-base64-out \
  --payload file:///tmp/migration_payload.json \
  /tmp/migration_result.json

echo ""
echo "📥 Migration result:"
cat /tmp/migration_result.json | jq .

# Check result
STATUS_CODE=$(cat /tmp/migration_result.json | jq -r '.statusCode')
MESSAGE=$(cat /tmp/migration_result.json | jq -r '.body' | jq -r '.message')

if [ "$STATUS_CODE" = "200" ]; then
  echo ""
  echo "✅ Migration completed: $MESSAGE"
  echo ""
  echo "Next steps:"
  echo "  1. Run schema validation tests to verify"
  echo "  2. Push commits to trigger CI/CD"
  exit 0
else
  echo ""
  echo "❌ Migration failed: $MESSAGE"
  exit 1
fi
