#!/usr/bin/env python3
"""
Comprehensive Aurora Migration Script

Applies all pending migrations to bring Aurora schema up to date with code expectations.

Migrations executed:
- 001: ticker_info, daily_prices tables (if not exist)
- 003: Add computed_at, expires_at, error_message to precomputed_reports
- 004: Create daily_indicators table
- 005: Create indicator_percentiles table
- 006: Create comparative_features table

Usage:
    # Via Doppler (recommended)
    doppler run --config dev -- python scripts/run_aurora_migration_comprehensive.py

    # Direct (requires AWS credentials)
    python scripts/run_aurora_migration_comprehensive.py
"""

import json
import logging
import sys
from pathlib import Path

import boto3
from botocore.exceptions import ClientError

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def read_migration_file(filepath: str) -> str:
    """Read SQL migration file."""
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"Migration file not found: {filepath}")
    return path.read_text()


def execute_migration_via_lambda(lambda_client, function_name: str, migration_sql: str) -> dict:
    """Execute migration SQL via Lambda invocation.

    Args:
        lambda_client: boto3 Lambda client
        function_name: Lambda function name (e.g., dr-daily-report-report-worker-dev)
        migration_sql: SQL statements to execute

    Returns:
        Dict with execution result
    """
    payload = {
        'action': 'execute_sql',
        'sql': migration_sql
    }

    try:
        response = lambda_client.invoke(
            FunctionName=function_name,
            InvocationType='RequestResponse',
            Payload=json.dumps(payload)
        )

        result = json.loads(response['Payload'].read())
        return result
    except ClientError as e:
        logger.error(f"Lambda invocation failed: {e}")
        raise


def verify_table_exists(lambda_client, function_name: str, table_name: str) -> bool:
    """Check if table exists in Aurora."""
    payload = {
        'action': 'describe_table',
        'table_name': table_name
    }

    try:
        response = lambda_client.invoke(
            FunctionName=function_name,
            InvocationType='RequestResponse',
            Payload=json.dumps(payload)
        )

        result = json.loads(response['Payload'].read())
        return result.get('statusCode') == 200
    except Exception as e:
        logger.warning(f"Error checking table {table_name}: {e}")
        return False


def main():
    """Execute all migrations in order."""
    logger.info("=" * 80)
    logger.info("Comprehensive Aurora Schema Migration")
    logger.info("=" * 80)

    # Initialize AWS clients
    lambda_client = boto3.client('lambda', region_name='ap-southeast-1')

    # Determine Lambda function name (TODO: Make configurable)
    function_name = 'dr-daily-report-report-worker-dev'
    logger.info(f"Using Lambda function: {function_name}")

    # Define migrations in order
    migrations = [
        {
            'name': '001 - Initial Schema',
            'file': 'db/migrations/001_initial_schema.sql',
            'description': 'Create ticker_info, daily_prices tables'
        },
        {
            'name': '003 - Add Timestamp Columns',
            'file': 'db/migrations/003_add_computed_expires_columns.sql',
            'description': 'Add computed_at, expires_at, error_message to precomputed_reports'
        },
        {
            'name': '004 - Daily Indicators',
            'file': 'db/migrations/004_daily_indicators_schema.sql',
            'description': 'Create daily_indicators table'
        },
        {
            'name': '005 - Indicator Percentiles',
            'file': 'db/migrations/005_indicator_percentiles_schema.sql',
            'description': 'Create indicator_percentiles table'
        },
        {
            'name': '006 - Comparative Features',
            'file': 'db/migrations/006_comparative_features_schema.sql',
            'description': 'Create comparative_features table'
        }
    ]

    success_count = 0
    failed_count = 0

    for migration in migrations:
        logger.info("")
        logger.info(f"{'='*80}")
        logger.info(f"Running: {migration['name']}")
        logger.info(f"Description: {migration['description']}")
        logger.info(f"{'='*80}")

        try:
            # Read migration SQL
            sql = read_migration_file(migration['file'])
            logger.info(f"Loaded migration file: {migration['file']}")

            # Execute via Lambda
            result = execute_migration_via_lambda(lambda_client, function_name, sql)

            if result.get('statusCode') == 200:
                logger.info(f"✅ Migration successful: {migration['name']}")
                success_count += 1
            else:
                logger.error(f"❌ Migration failed: {migration['name']}")
                logger.error(f"   Error: {result.get('body', {}).get('message')}")
                failed_count += 1
        except Exception as e:
            logger.error(f"❌ Exception during migration: {migration['name']}")
            logger.error(f"   Error: {str(e)}", exc_info=True)
            failed_count += 1

    # Summary
    logger.info("")
    logger.info("=" * 80)
    logger.info("Migration Summary")
    logger.info("=" * 80)
    logger.info(f"✅ Successful: {success_count}/{len(migrations)}")
    logger.info(f"❌ Failed: {failed_count}/{len(migrations)}")

    if failed_count > 0:
        logger.error("")
        logger.error("⚠️  Some migrations failed. Check logs above for details.")
        sys.exit(1)
    else:
        logger.info("")
        logger.info("🎉 All migrations completed successfully!")
        logger.info("")
        logger.info("Next steps:")
        logger.info("  1. Run schema validation tests: pytest tests/infrastructure/test_aurora_schema_comprehensive.py")
        logger.info("  2. Re-trigger deployment if tests pass")
        logger.info("  3. Verify UI displays data correctly")
        sys.exit(0)


if __name__ == '__main__':
    main()
