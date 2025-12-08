#!/usr/bin/env python3
"""
Validate Aurora schema matches code expectations before deployment.

Following CLAUDE.md Defensive Programming:
- Validate configuration at startup, not on first use
- Fail fast and visibly when something is wrong

This script is a CI/CD gate that blocks deployment if schema doesn't match code.

Usage:
    ENV=dev doppler run -- python scripts/validate_aurora_schema.py

Exit codes:
    0 - Schema matches code expectations
    1 - Schema mismatch (blocks deployment)
"""

import sys
import os
import boto3
import json
from typing import Dict, Set, Any


def query_aurora_schema(lambda_client, lambda_name: str, table_name: str) -> Dict[str, Any]:
    """Query Aurora table schema via Lambda (has VPC access).

    Args:
        lambda_client: boto3 Lambda client
        lambda_name: Lambda function with Aurora access
        table_name: Table to describe

    Returns:
        Dict with columns and their types

    Raises:
        SystemExit: If Lambda invocation fails
    """
    payload = {
        "action": "describe_table",
        "table": table_name
    }

    print(f"🔍 Querying Aurora schema for table: {table_name}")

    try:
        response = lambda_client.invoke(
            FunctionName=lambda_name,
            InvocationType='RequestResponse',
            Payload=json.dumps(payload)
        )

        result = json.loads(response['Payload'].read())

        if result.get('statusCode') != 200:
            print(f"❌ Lambda failed to query schema: {result.get('body', {}).get('message')}")
            sys.exit(1)

        return result.get('body', {}).get('schema', {})

    except Exception as e:
        print(f"❌ Failed to invoke Lambda: {e}")
        sys.exit(1)


def validate_precomputed_reports_schema(schema: Dict[str, Any]) -> bool:
    """Validate precomputed_reports table schema.

    Code reference: src/data/aurora/precompute_service.py:856
    INSERT INTO precomputed_reports (ticker_id, symbol, date, report_date, ...)

    Args:
        schema: Table schema from Aurora

    Returns:
        True if valid, False otherwise
    """
    actual_columns = set(schema.keys()) if isinstance(schema, dict) else set()

    # Required columns from code
    required_columns = {
        'ticker_id',
        'symbol',
        'date',              # NEW SCHEMA (code expects this!)
        'report_date',       # BACKWARDS COMPAT
        'status',
        'error_message',
        'report_generated_at',  # NEW SCHEMA
        'report_json'        # Stores user_facing_scores
    }

    missing = required_columns - actual_columns

    if missing:
        print(f"\n❌ SCHEMA VALIDATION FAILED")
        print(f"   Table: precomputed_reports")
        print(f"   Missing columns: {missing}")
        print(f"   Actual columns: {sorted(actual_columns)}")
        print(f"\n   Code expects these columns (precompute_service.py:856)")
        print(f"   MUST run schema migration before deploying!")
        print(f"\n   Migration SQL:")
        for col in missing:
            if col == 'date':
                print(f"   ALTER TABLE precomputed_reports ADD COLUMN date DATE AFTER symbol;")
            elif col == 'report_generated_at':
                print(f"   ALTER TABLE precomputed_reports ADD COLUMN report_generated_at DATETIME;")
        return False

    # Validate JSON column type
    if 'report_json' in schema:
        col_type = schema['report_json'].get('Type', '')
        if 'json' not in col_type.lower():
            print(f"\n❌ Column 'report_json' has wrong type: {col_type}")
            print(f"   Expected: JSON")
            print(f"   This column stores user_facing_scores")
            return False

    print(f"✅ Schema validation passed for precomputed_reports")
    print(f"   Found all {len(required_columns)} required columns")
    return True


def main():
    """Main validation logic."""
    # Get Lambda name from environment
    lambda_name = os.getenv('SCHEDULER_LAMBDA_NAME', 'dr-daily-report-ticker-scheduler-dev')

    print("=" * 60)
    print("Aurora Schema Validation (CI/CD Gate)")
    print("=" * 60)
    print(f"Lambda: {lambda_name}")
    print()

    # Initialize boto3 client
    try:
        lambda_client = boto3.client('lambda', region_name='ap-southeast-1')
    except Exception as e:
        print(f"❌ Failed to create Lambda client: {e}")
        print(f"   Ensure AWS credentials are configured")
        sys.exit(1)

    # Validate precomputed_reports table
    schema = query_aurora_schema(lambda_client, lambda_name, 'precomputed_reports')

    if not validate_precomputed_reports_schema(schema):
        print("\n" + "=" * 60)
        print("❌ DEPLOYMENT BLOCKED - Schema validation failed")
        print("=" * 60)
        sys.exit(1)

    print("\n" + "=" * 60)
    print("✅ All schema validations passed - Safe to deploy")
    print("=" * 60)
    sys.exit(0)


if __name__ == '__main__':
    main()
