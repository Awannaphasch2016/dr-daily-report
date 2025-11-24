#!/bin/bash
#
# Verify local DynamoDB setup
#

set -e

echo "🔍 Verifying Local DynamoDB Setup"
echo "=================================="
echo ""

# Check Docker
echo "1. Checking Docker..."
if ! docker ps > /dev/null 2>&1; then
    echo "❌ Docker is not running"
    exit 1
fi
echo "✅ Docker is running"
echo ""

# Check DynamoDB Local container
echo "2. Checking DynamoDB Local container..."
if ! docker ps | grep -q dynamodb-local; then
    echo "❌ DynamoDB Local container is not running"
    echo "Run: just setup-local-db"
    exit 1
fi
echo "✅ DynamoDB Local is running on port 8000"
echo ""

# Check if port 8000 is listening
echo "3. Checking if DynamoDB Local port is accessible..."
if nc -z localhost 8000 2>/dev/null; then
    echo "✅ Port 8000 is listening (DynamoDB Local)"
else
    echo "❌ Port 8000 is not accessible"
    exit 1
fi
echo ""

# Test DynamoDB Local with Python
echo "4. Testing DynamoDB Local connection..."
python3 << 'EOF'
import boto3
from botocore.exceptions import ClientError

dynamodb = boto3.client(
    'dynamodb',
    endpoint_url='http://localhost:8000',
    region_name='us-east-1',
    aws_access_key_id='fake',
    aws_secret_access_key='fake'
)

try:
    response = dynamodb.list_tables()
    tables = response.get('TableNames', [])
    print(f"✅ Connected to DynamoDB Local")
    print(f"   Found {len(tables)} table(s):")
    for table in tables:
        print(f"   - {table}")

    # Check for required tables
    required_tables = [
        'dr-daily-report-telegram-watchlist-dev',
        'dr-daily-report-telegram-cache-dev'
    ]

    missing = [t for t in required_tables if t not in tables]
    if missing:
        print(f"\n⚠️  Missing tables: {', '.join(missing)}")
        print("   Run: python scripts/create_local_dynamodb_tables.py")
    else:
        print("\n✅ All required tables exist")

except Exception as e:
    print(f"❌ Failed to connect: {e}")
    exit(1)
EOF

echo ""
echo "=================================="
echo "✨ Local DynamoDB setup is ready!"
echo ""
echo "Next steps:"
echo "  1. Start API: just dev-api"
echo "  2. Test watchlist: just test-watchlist"
