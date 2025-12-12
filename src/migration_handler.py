"""
Lambda handler for running database migrations

This handler executes the ADD strategy column migration when invoked.
Can be used for one-time migrations without deploying separate infrastructure.

Invocation:
    aws lambda invoke --function-name dr-daily-report-report-worker-dev \
        --payload '{"migration": "add_strategy_column"}' /tmp/migration-result.json
"""

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def run_add_strategy_column_migration():
    """Add missing columns to precomputed_reports table

    Adds: strategy, generation_time_ms, mini_reports, chart_base64
    """
    from src.data.aurora.client import get_aurora_client

    logger.info("=" * 80)
    logger.info("Migration: Add missing columns to precomputed_reports")
    logger.info("=" * 80)

    client = get_aurora_client()

    # Check current schema
    schema_query = "DESCRIBE precomputed_reports"
    existing_columns = client.fetch_all(schema_query)
    column_names = {row['Field'] for row in existing_columns}

    logger.info(f"Current columns: {sorted(column_names)}")

    # Define columns to add (all columns used by _store_completed_report)
    columns_to_add = {
        'strategy': "ADD COLUMN strategy ENUM('single-stage', 'multi-stage') NOT NULL DEFAULT 'multi-stage' AFTER report_json",
        'generation_time_ms': "ADD COLUMN generation_time_ms INT UNSIGNED DEFAULT NULL AFTER strategy",
        'mini_reports': "ADD COLUMN mini_reports JSON DEFAULT NULL AFTER generation_time_ms",
        'chart_base64': "ADD COLUMN chart_base64 LONGTEXT DEFAULT NULL AFTER mini_reports",
        'status': "ADD COLUMN status ENUM('pending', 'completed', 'failed') NOT NULL DEFAULT 'pending' AFTER chart_base64",
        'expires_at': "ADD COLUMN expires_at DATETIME DEFAULT NULL AFTER status",
        'computed_at': "ADD COLUMN computed_at DATETIME DEFAULT CURRENT_TIMESTAMP AFTER expires_at"
    }

    # Find which columns are missing
    missing_columns = {col: stmt for col, stmt in columns_to_add.items() if col not in column_names}

    if not missing_columns:
        logger.info("✅ All columns already exist - migration not needed")
        return {
            'status': 'success',
            'message': 'All columns already exist',
            'migration_applied': False
        }

    logger.info(f"Missing columns: {list(missing_columns.keys())}")

    try:
        # Add all missing columns in one ALTER TABLE statement
        alter_statements = ', '.join(missing_columns.values())
        alter_query = f"ALTER TABLE precomputed_reports {alter_statements}"

        logger.info(f"Executing: {alter_query}")
        client.execute(alter_query, commit=True)
        logger.info("✅ Successfully added missing columns")

        # Verify all columns were added
        verify_schema = client.fetch_all(schema_query)
        verify_columns = {row['Field'] for row in verify_schema}

        added_successfully = all(col in verify_columns for col in missing_columns.keys())

        if added_successfully:
            logger.info(f"✅ Verification passed - added {len(missing_columns)} columns")
            return {
                'status': 'success',
                'message': f'Successfully added {len(missing_columns)} columns: {list(missing_columns.keys())}',
                'migration_applied': True
            }
        else:
            still_missing = [col for col in missing_columns.keys() if col not in verify_columns]
            logger.error(f"❌ Verification failed - still missing: {still_missing}")
            return {
                'status': 'error',
                'message': f'Verification failed - still missing: {still_missing}',
                'migration_applied': False
            }

    except Exception as e:
        logger.error(f"❌ Migration failed: {e}", exc_info=True)
        return {
            'status': 'error',
            'message': f'Migration failed: {str(e)}',
            'migration_applied': False
        }


def lambda_handler(event: dict, context: Any) -> dict:
    """Lambda handler for database migrations

    Args:
        event: Dict with 'migration' key specifying which migration to run
        context: Lambda context (unused)

    Returns:
        Dict with migration result

    Examples:
        >>> lambda_handler({'migration': 'add_strategy_column'}, None)
        {'statusCode': 200, 'body': {...}}
    """
    logger.info(f"Migration handler invoked with event: {json.dumps(event)}")

    migration = event.get('migration', '')

    if migration == 'add_strategy_column':
        result = run_add_strategy_column_migration()
        return {
            'statusCode': 200 if result['status'] == 'success' else 500,
            'body': json.dumps(result)
        }
    else:
        return {
            'statusCode': 400,
            'body': json.dumps({
                'status': 'error',
                'message': f'Unknown migration: {migration}',
                'available_migrations': ['add_strategy_column']
            })
        }
