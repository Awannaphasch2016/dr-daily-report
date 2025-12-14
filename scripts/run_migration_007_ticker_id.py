#!/usr/bin/env python3
"""
Run Migration 007: Make ticker_id required in precomputed_reports

This migration:
1. Changes ticker_id from INT NULL → BIGINT NOT NULL
2. Adds foreign key constraint to ticker_master(id)

Usage:
    doppler run --config dev -- python scripts/run_migration_007_ticker_id.py
"""

import json
import logging
import sys

import boto3

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Execute migration 007 via Lambda."""
    logger.info("=" * 80)
    logger.info("Migration 007: Make ticker_id required")
    logger.info("=" * 80)

    # Initialize Lambda client
    lambda_client = boto3.client('lambda', region_name='ap-southeast-1')
    function_name = 'dr-daily-report-report-worker-dev'

    logger.info(f"Invoking Lambda: {function_name}")

    # Invoke Lambda with migration event
    try:
        response = lambda_client.invoke(
            FunctionName=function_name,
            InvocationType='RequestResponse',
            Payload=json.dumps({
                'migration': 'make_ticker_id_required'
            })
        )

        # Parse response
        payload = json.loads(response['Payload'].read())

        # Parse body (might be JSON string)
        body = payload.get('body')
        if isinstance(body, str):
            try:
                body = json.loads(body)
            except:
                pass

        # Save to file for inspection
        result_file = '/tmp/migration_007_result.json'
        with open(result_file, 'w') as f:
            json.dump({'payload': payload, 'body': body}, f, indent=2)
        logger.info(f"Saved result to {result_file}")

        # Check result
        if payload.get('statusCode') == 200:
            logger.info("✅ Migration 007 completed successfully")
            if isinstance(body, dict):
                logger.info(f"   Status: {body.get('status')}")
                logger.info(f"   Message: {body.get('message')}")
                logger.info(f"   Applied: {body.get('migration_applied')}")
                if body.get('before'):
                    logger.info(f"   Before: {body['before']}")
                if body.get('after'):
                    logger.info(f"   After: {body['after']}")
            return 0
        else:
            logger.error(f"❌ Migration 007 failed")
            logger.error(f"   Status code: {payload.get('statusCode')}")
            if isinstance(body, dict):
                logger.error(f"   Error: {body.get('message')}")
            else:
                logger.error(f"   Body: {body}")
            return 1

    except Exception as e:
        logger.error(f"❌ Error invoking Lambda: {e}")
        return 1


if __name__ == '__main__':
    sys.exit(main())
