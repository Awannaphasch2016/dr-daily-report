#!/bin/bash
set -euo pipefail

# Pre-deployment validation script
# Validates ALL required configuration before attempting operations
# Prevents wasting time on operations that will fail due to missing config

echo "=========================================="
echo "Pre-Deployment Configuration Validation"
echo "=========================================="
echo ""

ENV=${ENV:-dev}
echo "Environment: $ENV"
echo ""

# Run infrastructure tests to validate Lambda configuration
echo "1. Validating Lambda environment variables..."
ENV=$ENV doppler run -- pytest \
  tests/infrastructure/test_eventbridge_scheduler.py::TestSchedulerLambdaEnvironment \
  -m integration \
  -v \
  --tb=short

if [ $? -eq 0 ]; then
    echo "✅ Lambda environment variables validated"
else
    echo "❌ Lambda environment validation FAILED"
    echo ""
    echo "Fix required:"
    echo "  - Check AURORA_HOST, AURORA_PORT, AURORA_DATABASE, AURORA_USER"
    echo "  - Check PDF_BUCKET_NAME, ENVIRONMENT, OPENROUTER_API_KEY"
    echo "  - Check VPC configuration (subnets, security groups)"
    exit 1
fi

echo ""
echo "2. Validating Lambda can be invoked..."
ENV=$ENV doppler run -- pytest \
  tests/infrastructure/test_scheduler_lambda.py::TestSchedulerLambdaHealth::test_lambda_can_be_invoked_without_import_error \
  -m integration \
  -v \
  --tb=short

if [ $? -eq 0 ]; then
    echo "✅ Lambda invocation validated"
else
    echo "❌ Lambda invocation FAILED"
    echo ""
    echo "Fix required:"
    echo "  - Check deployment succeeded"
    echo "  - Check Lambda has latest code"
    echo "  - Check no import errors in deployed image"
    exit 1
fi

echo ""
echo "=========================================="
echo "✅ All configuration checks passed!"
echo "=========================================="
echo ""
echo "Safe to proceed with:"
echo "  - Cache population (parallel_precompute)"
echo "  - E2E test runs"
echo "  - CloudFront invalidation"
echo ""
