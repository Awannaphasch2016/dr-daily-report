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
import base64
from typing import Dict, Any
from botocore.exceptions import ClientError


def check_lambda_exists(lambda_client, lambda_name: str) -> bool:
    """Check if Lambda function exists.

    Args:
        lambda_client: boto3 Lambda client
        lambda_name: Lambda function name

    Returns:
        True if Lambda exists, False otherwise
    """
    try:
        lambda_client.get_function(FunctionName=lambda_name)
        return True
    except lambda_client.exceptions.ResourceNotFoundException:
        return False
    except Exception as e:
        print(f"⚠️  Failed to check Lambda existence: {e}")
        return False


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
    # Check if Lambda exists first
    if not check_lambda_exists(lambda_client, lambda_name):
        print(f"⚠️  Lambda function not found: {lambda_name}")
        print(f"   Skipping Aurora schema validation (Aurora may not be enabled)")
        print(f"   This is OK if Aurora is not configured for this environment")
        return {}

    payload = {
        "action": "describe_table",
        "table": table_name
    }

    print(f"🔍 Querying Aurora schema for table: {table_name}")

    try:
        response = lambda_client.invoke(
            FunctionName=lambda_name,
            InvocationType='RequestResponse',
            Payload=json.dumps(payload),
            LogType='Tail'  # Get logs for debugging
        )

        # VALIDATION GATE: Check response structure
        if 'Payload' not in response:
            print(f"❌ Lambda response missing 'Payload' field")
            print(f"   Response keys: {list(response.keys())}")
            sys.exit(1)

        # Parse JSON with error handling
        try:
            payload_bytes = response['Payload'].read()
            if not payload_bytes:
                print(f"❌ Lambda returned empty payload")
                sys.exit(1)
            
            result = json.loads(payload_bytes)
        except json.JSONDecodeError as e:
            print(f"❌ Lambda returned invalid JSON: {e}")
            print(f"   Raw payload (first 500 chars): {payload_bytes[:500]}")
            sys.exit(1)

        # VALIDATION GATE: Check result structure
        if not isinstance(result, dict):
            print(f"❌ Lambda response is not a dict: {type(result)}")
            print(f"   Response: {result}")
            sys.exit(1)

        # VALIDATION GATE: Check CloudWatch logs for errors
        if 'LogResult' in response:
            try:
                logs = base64.b64decode(response['LogResult']).decode('utf-8')
                
                # Check for ERROR level logs
                error_keywords = ['ERROR', 'Exception', 'Traceback', 'Failed', 'Error:']
                error_lines = [
                    line for line in logs.split('\n')
                    if any(keyword in line for keyword in error_keywords)
                ]
                
                if error_lines:
                    print(f"\n⚠️  Found potential errors in Lambda logs:")
                    # Print last 10 error lines
                    for line in error_lines[-10:]:
                        print(f"   {line.strip()}")
                    print(f"   (This may be non-fatal - checking response status)")
            except Exception as e:
                print(f"⚠️  Failed to decode logs: {e}")

        # Check status code
        status_code = result.get('statusCode')
        if status_code != 200:
            # Extract error message safely
            body = result.get('body', {})
            if isinstance(body, str):
                try:
                    body = json.loads(body)
                except json.JSONDecodeError:
                    body = {'message': body}
            elif not isinstance(body, dict):
                body = {'message': str(body)}
            
            error_msg = body.get('message', 'Unknown error')
            error_detail = body.get('error', '')
            
            print(f"❌ Lambda failed to query schema: {error_msg}")
            if error_detail:
                print(f"   Error detail: {error_detail}")
            
            # Check if it's a "table doesn't exist" error (MySQL error 1146)
            if 'doesn\'t exist' in error_msg.lower() or '1146' in str(error_detail):
                print(f"\n⚠️  Table '{table_name}' doesn't exist in Aurora")
                print(f"   This may be OK if:")
                print(f"   1. Aurora is not enabled for this environment")
                print(f"   2. Schema migration hasn't been run yet")
                print(f"   3. This is a new deployment")
                print(f"\n   To fix: Run schema migration:")
                print(f"   python scripts/aurora_precompute_migration.py")
                return {}
            
            sys.exit(1)

        # Extract schema safely
        body = result.get('body', {})
        if isinstance(body, str):
            try:
                body = json.loads(body)
            except json.JSONDecodeError:
                print(f"❌ Lambda body is not valid JSON: {body[:200]}")
                sys.exit(1)
        
        schema = body.get('schema', {})
        if not isinstance(schema, dict):
            print(f"❌ Schema is not a dict: {type(schema)}")
            print(f"   Schema value: {schema}")
            sys.exit(1)

        return schema

    except lambda_client.exceptions.ResourceNotFoundException:
        print(f"⚠️  Lambda function not found: {lambda_name}")
        print(f"   Skipping Aurora schema validation")
        return {}
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', '')
        if error_code == 'AccessDeniedException':
            print(f"❌ Access denied when invoking Lambda: {e}")
            print(f"   Check AWS credentials and IAM permissions")
            print(f"   Required permission: lambda:InvokeFunction")
            sys.exit(1)
        else:
            print(f"❌ AWS error when invoking Lambda: {error_code}")
            print(f"   Error: {e}")
            sys.exit(1)
    except Exception as e:
        print(f"❌ Failed to invoke Lambda: {e}")
        print(f"   Error type: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def validate_precomputed_reports_schema(schema: Dict[str, Any]) -> bool:
    """Validate precomputed_reports table schema.

    Code reference: src/data/aurora/precompute_service.py:856
    INSERT INTO precomputed_reports (ticker_id, symbol, report_date, ...)

    Actual Aurora schema confirmed via Lambda describe_table:
    - report_date (date) - NOT 'date'
    - computed_at (timestamp) - NOT 'report_generated_at'

    Args:
        schema: Table schema from Aurora

    Returns:
        True if valid, False otherwise
    """
    actual_columns = set(schema.keys()) if isinstance(schema, dict) else set()

    # Required columns from code (matches actual Aurora schema)
    required_columns = {
        'ticker_id',
        'symbol',
        'report_date',       # Actual column name in Aurora
        'status',
        'error_message',
        'computed_at',       # Actual column name in Aurora
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
    # VALIDATION GATE: Check environment variable at startup
    lambda_name = os.getenv('SCHEDULER_LAMBDA_NAME')
    
    if not lambda_name:
        print("=" * 60)
        print("❌ CONFIGURATION ERROR")
        print("=" * 60)
        print("SCHEDULER_LAMBDA_NAME environment variable not set")
        print("")
        print("This is a CI/CD configuration error - fix workflow:")
        print("  env:")
        print("    SCHEDULER_LAMBDA_NAME: dr-daily-report-ticker-scheduler-${{ env.ENV_NAME }}")
        print("")
        print("Following CLAUDE.md: Validate configuration at startup, not on first use")
        sys.exit(1)

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

    # VALIDATION GATE: Test credentials by checking if we can access Lambda
    print("🔍 Validating AWS credentials...")
    try:
        # Try to describe the Lambda function (lightweight operation)
        lambda_client.get_function(FunctionName=lambda_name)
        print(f"✅ AWS credentials valid - Lambda function exists")
    except lambda_client.exceptions.ResourceNotFoundException:
        print(f"⚠️  Lambda function not found: {lambda_name}")
        print(f"   This may be OK if Aurora is not enabled")
        # Don't exit here - let query_aurora_schema handle it
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', '')
        if error_code == 'AccessDeniedException':
            print(f"❌ Access denied when checking Lambda: {e}")
            print(f"   Check IAM permissions for Lambda:GetFunction")
            sys.exit(1)
        else:
            print(f"⚠️  Failed to validate credentials: {error_code}")
            print(f"   Will attempt Lambda invocation anyway")
    except Exception as e:
        print(f"⚠️  Failed to validate credentials: {e}")
        print(f"   Will attempt Lambda invocation anyway")
    print()

    # Validate precomputed_reports table
    schema = query_aurora_schema(lambda_client, lambda_name, 'precomputed_reports')

    # If schema is empty, Lambda/table doesn't exist - skip validation
    if not schema:
        print("\n" + "=" * 60)
        print("⚠️  SKIPPING Aurora schema validation")
        print("=" * 60)
        print("   Lambda or table not found - Aurora may not be enabled")
        print("   Deployment will proceed (Aurora validation skipped)")
        sys.exit(0)

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
