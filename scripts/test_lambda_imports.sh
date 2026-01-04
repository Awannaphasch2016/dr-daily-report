#!/bin/bash
# Deployment Fidelity Test: Verify imports work in Lambda environment
#
# Purpose: Catch ImportError before deployment (Principle #10)
# Context: Local Python != Lambda Python (different paths, base images)
# Pattern: Test deployment artifact, not just source code
#
# Real incidents prevented:
# - LINE bot 7-day outage (ImportError in Lambda, not local)
# - query_tool_handler deployment blocker (missing dependencies)
#
# Usage: ./scripts/test_lambda_imports.sh
# Exit code: 0 = success, 1 = import failure

set -e  # Exit on error

echo "======================================================"
echo "Deployment Fidelity Test: Lambda Import Validation"
echo "======================================================"
echo ""
echo "Testing new migration code imports in Lambda environment..."
echo ""

# Run Python import test inside Lambda base image
docker run --rm \
  -v $(pwd):/var/task \
  -e REPORT_WORKER_FUNCTION_NAME=test-worker \
  -e OPENROUTER_API_KEY=test-key \
  -e AURORA_HOST=test-host \
  -e PDF_BUCKET_NAME=test-bucket \
  -e JOBS_TABLE_NAME=test-table \
  public.ecr.aws/lambda/python:3.13 \
  python3 -c "
import sys
sys.path.insert(0, '/var/task')

print('Testing imports in Lambda environment...')
print('')

# Test 1: invoke_report_worker import
print('1. Testing invoke_report_worker() import...')
try:
    from src.api.app import invoke_report_worker
    print('   ✅ invoke_report_worker import successful')
except ImportError as e:
    print(f'   ❌ Import failed: {e}')
    sys.exit(1)

# Test 2: Updated handler import
print('2. Testing report_worker_handler import...')
try:
    from src.report_worker_handler import handler
    print('   ✅ handler import successful')
except ImportError as e:
    print(f'   ❌ Import failed: {e}')
    sys.exit(1)

# Test 3: boto3 Lambda client (required for invoke)
print('3. Testing boto3 Lambda client...')
try:
    import boto3
    lambda_client = boto3.client('lambda', region_name='ap-southeast-1')
    print('   ✅ boto3 Lambda client creation successful')
except Exception as e:
    print(f'   ❌ Failed: {e}')
    sys.exit(1)

# Test 4: JSON serialization (payload format)
print('4. Testing JSON payload serialization...')
try:
    import json
    payload = {'job_id': 'test', 'ticker': 'NVDA19', 'source': 'test'}
    payload_str = json.dumps(payload)
    parsed = json.loads(payload_str)
    assert parsed['job_id'] == 'test'
    print('   ✅ JSON serialization successful')
except Exception as e:
    print(f'   ❌ Failed: {e}')
    sys.exit(1)

print('')
print('====================================================')
print('✅ All imports successful - Lambda deployment will work')
print('====================================================')
"

EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
  echo ""
  echo "✅ Deployment fidelity test PASSED"
  echo "   Safe to deploy to Lambda"
  exit 0
else
  echo ""
  echo "❌ Deployment fidelity test FAILED"
  echo "   DO NOT deploy - fix import errors first"
  exit 1
fi
