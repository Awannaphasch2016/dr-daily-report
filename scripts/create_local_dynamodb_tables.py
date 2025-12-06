#!/usr/bin/env python3
"""
Create DynamoDB tables in local DynamoDB for development/testing

Usage:
    doppler run -- python scripts/create_local_dynamodb_tables.py

Prerequisites:
    - Docker running with DynamoDB Local:
      docker run -d -p 8000:8000 --name dynamodb-local amazon/dynamodb-local
    - Run with doppler to use consistent AWS credentials
"""

import boto3
from botocore.exceptions import ClientError


def create_local_tables():
    """Create DynamoDB tables in local DynamoDB"""

    # Connect to local DynamoDB
    # Uses credentials from environment (doppler provides these)
    dynamodb = boto3.resource(
        'dynamodb',
        endpoint_url='http://localhost:8000',
        region_name='ap-southeast-1'
    )

    print("🔧 Creating local DynamoDB tables...")
    print("=" * 60)

    # Table 1: Watchlist
    try:
        watchlist_table = dynamodb.create_table(
            TableName='dr-daily-report-telegram-watchlist-dev',
            KeySchema=[
                {'AttributeName': 'user_id', 'KeyType': 'HASH'},  # Partition key
                {'AttributeName': 'ticker', 'KeyType': 'RANGE'}   # Sort key
            ],
            AttributeDefinitions=[
                {'AttributeName': 'user_id', 'AttributeType': 'S'},
                {'AttributeName': 'ticker', 'AttributeType': 'S'}
            ],
            BillingMode='PAY_PER_REQUEST'
        )
        print(f"✅ Created table: {watchlist_table.table_name}")
        print(f"   - Hash key: user_id (Telegram user ID)")
        print(f"   - Range key: ticker (e.g., NVDA19)")
        print(f"   - Billing: On-demand")
    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceInUseException':
            print(f"⚠️  Table 'dr-daily-report-telegram-watchlist-dev' already exists")
        else:
            raise

    print()

    # Table 2: Jobs (for async report generation)
    try:
        jobs_table = dynamodb.create_table(
            TableName='dr-daily-report-telegram-jobs-dev',
            KeySchema=[
                {'AttributeName': 'job_id', 'KeyType': 'HASH'}  # Partition key
            ],
            AttributeDefinitions=[
                {'AttributeName': 'job_id', 'AttributeType': 'S'}
            ],
            BillingMode='PAY_PER_REQUEST'
        )
        print(f"✅ Created table: {jobs_table.table_name}")
        print(f"   - Hash key: job_id (e.g., 'rpt_abc123def456')")
        print(f"   - Billing: On-demand")
        print(f"   - TTL: 24 hours (auto-expire old jobs)")
    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceInUseException':
            print(f"⚠️  Table 'dr-daily-report-telegram-jobs-dev' already exists")
        else:
            raise

    # NOTE: Cache table REMOVED - cache functionality moved to Aurora ticker_data_cache
    # See db/migrations/002_schema_redesign.sql

    print()
    print("=" * 60)
    print("✨ Setup complete!")
    print()
    print("To verify tables:")
    print("  aws dynamodb list-tables --endpoint-url http://localhost:8000")
    print()
    print("To start API with local DynamoDB:")
    print("  export USE_LOCAL_DYNAMODB=true")
    print("  export WATCHLIST_TABLE_NAME=dr-daily-report-telegram-watchlist-dev")
    print("  export JOBS_TABLE_NAME=dr-daily-report-telegram-jobs-dev")
    print("  # NOTE: CACHE_TABLE_NAME no longer needed - cache moved to Aurora")
    print("  doppler run -- python -m uvicorn src.api.app:app --reload")
    print()
    print("Or use the start script (recommended):")
    print("  ./scripts/start_local_api.sh")


def list_tables():
    """List all tables in local DynamoDB"""
    dynamodb = boto3.client(
        'dynamodb',
        endpoint_url='http://localhost:8000',
        region_name='ap-southeast-1'
    )

    response = dynamodb.list_tables()
    tables = response.get('TableNames', [])

    print("\n📋 Tables in local DynamoDB:")
    for table in tables:
        print(f"  - {table}")
    print()


if __name__ == "__main__":
    try:
        create_local_tables()
        list_tables()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nMake sure DynamoDB Local is running:")
        print("  docker run -d -p 8000:8000 --name dynamodb-local amazon/dynamodb-local")
        print("\nOr start it if container exists:")
        print("  docker start dynamodb-local")
        exit(1)
