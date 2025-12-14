#!/usr/bin/env python3
"""
Run Aurora migration 003: Add computed_at and expires_at columns

This script executes the SQL migration file via AWS Lambda (which has VPC access to Aurora).
Cannot run locally due to Aurora being VPC-isolated.

Usage:
    python scripts/run_aurora_migration_003.py
"""

import boto3
import json
import sys

def main():
    print("=" * 80)
    print("Running Migration 003: Add computed_at and expires_at columns")
    print("=" * 80)

    # Read migration SQL
    with open('db/migrations/003_add_computed_expires_columns.sql', 'r') as f:
        sql = f.read()

    # Strip comments and get ALTER TABLE statement
    lines = [line for line in sql.split('\n') if line.strip() and not line.strip().startswith('--')]
    alter_statement = '\n'.join(lines[0:3])  # ALTER TABLE ... ADD COLUMN ...

    print(f"\nSQL to execute:\n{alter_statement}\n")

    # Invoke Lambda to execute migration
    lambda_client = boto3.client('lambda', region_name='ap-southeast-1')

    # Use worker Lambda migration handler
    payload = {
        "migration": "add_strategy_column"  # This checks for all missing columns
    }

    print("Invoking Lambda migration handler...")
    response = lambda_client.invoke(
        FunctionName='dr-daily-report-report-worker-dev',
        InvocationType='RequestResponse',
        Payload=json.dumps(payload)
    )

    result = json.loads(response['Payload'].read())
    print(f"\nLambda response: {json.dumps(result, indent=2)}")

    if result.get('statusCode') == 200:
        body = json.loads(result['body'])
        if body.get('status') == 'success':
            print(f"\n✅ Migration successful: {body['message']}")
            return 0
        else:
            print(f"\n❌ Migration failed: {body.get('message')}")
            return 1
    else:
        print(f"\n❌ Lambda invocation failed")
        return 1

if __name__ == '__main__':
    sys.exit(main())
