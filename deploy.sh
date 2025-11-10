#!/bin/bash
# Deployment script with automatic verification
# Usage: ./deploy.sh [ticker_to_test]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TERRAFORM_DIR="$SCRIPT_DIR/terraform"
TICKER="${1:-DBS19}"

echo "=================================================================================="
echo "DEPLOYMENT WITH AUTOMATIC VERIFICATION"
echo "=================================================================================="
echo ""
echo "📦 Step 1: Deploying to Lambda..."
echo ""

cd "$TERRAFORM_DIR"

# Deploy with Terraform
terraform apply -auto-approve

echo ""
echo "=================================================================================="
echo "✅ DEPLOYMENT COMPLETE"
echo "=================================================================================="
echo ""
echo "🧪 Step 2: Verifying deployment..."
echo ""

cd "$SCRIPT_DIR"

# Wait a few seconds for Lambda to be ready
sleep 3

# Run verification
python3 verify_deployment.py --ticker "$TICKER"

echo ""
echo "=================================================================================="
echo "DEPLOYMENT PROCESS COMPLETE"
echo "=================================================================================="
