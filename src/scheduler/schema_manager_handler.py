# -*- coding: utf-8 -*-
"""
Lambda handler for schema and migration management (Admin Layer).

Single Responsibility: Manage Aurora database schema, migrations, and one-time setup operations.

Triggered by: Manual invocation (pre-deployment, migrations)

Actions:
- execute_migration: Run SQL migration files or inline SQL
- precompute_migration: Setup precomputation tables
- aurora_setup: Create tables and import data from S3
- setup_ticker_mapping: Initialize ticker_master/ticker_aliases tables
- ticker_unification: Migrate to use ticker_master.id as canonical identifier
"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict
import traceback

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Handle schema and migration operations.

    Event format:
        {
            "action": "execute_migration|precompute_migration|aurora_setup|setup_ticker_mapping|ticker_unification",
            ...  # Action-specific parameters
        }

    Args:
        event: Lambda event with 'action' field
        context: Lambda context

    Returns:
        Response dict with operation results
    """
    start_time = datetime.now()
    action = event.get('action', 'execute_migration')  # Default action

    logger.info(f"Schema Manager Lambda invoked at {start_time.isoformat()}")
    logger.info(f"Action: {action}")
    logger.info(f"Event: {json.dumps(event)}")

    # Route to appropriate handler
    handlers = {
        'execute_migration': _handle_execute_migration,
        'precompute_migration': _handle_precompute_migration,
        'aurora_setup': _handle_aurora_setup,
        'setup_ticker_mapping': _handle_setup_ticker_mapping,
        'ticker_unification': _handle_ticker_unification
    }

    handler = handlers.get(action)
    if not handler:
        return {
            'statusCode': 400,
            'body': {
                'message': f'Unknown action: {action}',
                'error': f'Valid actions: {", ".join(handlers.keys())}'
            }
        }

    try:
        return handler(event, start_time)
    except Exception as e:
        logger.error(f"Schema manager failed: {e}")
        logger.error(traceback.format_exc())

        return {
            'statusCode': 500,
            'body': {
                'message': f'Schema manager action {action} failed',
                'error': str(e),
                'traceback': traceback.format_exc()
            }
        }


def _handle_execute_migration(event: Dict[str, Any], start_time: datetime) -> Dict[str, Any]:
    """Execute SQL migration file against Aurora database.

    Args:
        event: Lambda event with required param:
            - migration_file: Path to migration SQL file (e.g., "db/migrations/004_daily_indicators_schema.sql")
            OR
            - sql: Raw SQL statements to execute (for inline execution)
        start_time: When the Lambda was invoked

    Returns:
        Response dict with execution results

    Example usage:
        # Execute migration file
        aws lambda invoke \\
          --function-name dr-daily-report-schema-manager-dev \\
          --payload '{"action":"execute_migration","migration_file":"db/migrations/004_daily_indicators_schema.sql"}' \\
          /tmp/migration-result.json

        # Execute inline SQL
        aws lambda invoke \\
          --function-name dr-daily-report-schema-manager-dev \\
          --payload '{"action":"execute_migration","sql":"ALTER TABLE precomputed_reports ADD COLUMN test_col INT;"}' \\
          /tmp/migration-result.json
    """
    try:
        # Lazy import
        from src.data.aurora.client import get_aurora_client

        migration_file = event.get('migration_file')
        sql = event.get('sql')

        if not migration_file and not sql:
            return {
                'statusCode': 400,
                'body': {
                    'message': 'Missing required parameter: migration_file or sql',
                    'error': 'Must provide either migration_file path or sql statements'
                }
            }

        # Read SQL from file if provided
        if migration_file:
            # Convert relative path to absolute (Lambda execution context)
            if not migration_file.startswith('/var/task/'):
                migration_file = f'/var/task/{migration_file}'

            path = Path(migration_file)
            if not path.exists():
                return {
                    'statusCode': 404,
                    'body': {
                        'message': f'Migration file not found: {migration_file}',
                        'error': 'File does not exist in Lambda package'
                    }
                }

            logger.info(f"Reading migration file: {migration_file}")
            sql = path.read_text()

        # Execute SQL statements
        client = get_aurora_client()
        logger.info(f"Executing migration SQL ({len(sql)} bytes)")

        # Split by semicolon and execute each statement
        statements = [s.strip() for s in sql.split(';') if s.strip() and not s.strip().startswith('--')]

        executed_count = 0
        failed_count = 0
        errors = []

        for statement in statements:
            # Skip comments and empty lines
            if statement.startswith('--') or not statement.strip():
                continue

            try:
                logger.info(f"Executing: {statement[:100]}...")
                affected_rows = client.execute(statement, commit=True)
                executed_count += 1
                logger.info(f"  ✓ Success (affected {affected_rows} rows)")
            except Exception as stmt_error:
                failed_count += 1
                error_msg = str(stmt_error)
                logger.error(f"  ✗ Failed: {error_msg}")
                errors.append({
                    'statement': statement[:200],
                    'error': error_msg
                })

        end_time = datetime.now()
        duration_seconds = (end_time - start_time).total_seconds()

        success = failed_count == 0

        return {
            'statusCode': 200 if success else 500,
            'body': {
                'message': 'Migration completed' if success else 'Migration completed with errors',
                'migration_file': event.get('migration_file'),
                'executed_count': executed_count,
                'failed_count': failed_count,
                'errors': errors if errors else None,
                'duration_seconds': duration_seconds
            }
        }

    except Exception as e:
        logger.error(f"Migration execution failed: {e}")
        logger.error(traceback.format_exc())

        return {
            'statusCode': 500,
            'body': {
                'message': 'Migration execution failed',
                'error': str(e),
                'traceback': traceback.format_exc()
            }
        }


def _handle_precompute_migration(event: Dict[str, Any], start_time: datetime) -> Dict[str, Any]:
    """Handle precomputation tables migration.

    Args:
        event: Lambda event
        start_time: When the Lambda was invoked

    Returns:
        Response dict with migration results
    """
    logger.info("Starting precomputation tables migration...")

    try:
        # Lazy import
        from scripts.aurora_precompute_migration import run_migration

        result = run_migration()

        end_time = datetime.now()
        duration_seconds = (end_time - start_time).total_seconds()

        return {
            'statusCode': 200,
            'body': {
                'message': 'Precomputation migration completed',
                'duration_seconds': duration_seconds,
                **result
            }
        }

    except Exception as e:
        logger.error(f"Precomputation migration failed: {e}")
        logger.error(traceback.format_exc())

        return {
            'statusCode': 500,
            'body': {
                'message': 'Precomputation migration failed',
                'error': str(e),
                'traceback': traceback.format_exc()
            }
        }


def _handle_aurora_setup(event: Dict[str, Any], start_time: datetime) -> Dict[str, Any]:
    """Handle Aurora database setup: create tables and import data from S3.

    Args:
        event: Lambda event with optional create_tables_only, import_limit, cleanup_first params
        start_time: When the Lambda was invoked

    Returns:
        Response dict with setup results
    """
    logger.info("Starting Aurora setup...")

    try:
        # Lazy import
        from scripts.aurora_setup import setup_aurora

        create_tables_only = event.get('create_tables_only', False)
        import_limit = event.get('import_limit')
        cleanup_first = event.get('cleanup_first', False)

        result = setup_aurora(
            create_tables_only=create_tables_only,
            import_limit=import_limit,
            cleanup_first=cleanup_first
        )

        end_time = datetime.now()
        duration_seconds = (end_time - start_time).total_seconds()

        return {
            'statusCode': 200,
            'body': {
                'message': 'Aurora setup completed',
                'duration_seconds': duration_seconds,
                **result
            }
        }

    except Exception as e:
        logger.error(f"Aurora setup failed: {e}")
        logger.error(traceback.format_exc())

        return {
            'statusCode': 500,
            'body': {
                'message': 'Aurora setup failed',
                'error': str(e),
                'traceback': traceback.format_exc()
            }
        }


def _handle_setup_ticker_mapping(event: Dict[str, Any], start_time: datetime) -> Dict[str, Any]:
    """Setup ticker mapping tables and populate from tickers.csv.

    Creates ticker_master and ticker_aliases tables if they don't exist,
    then populates them from tickers.csv for centralized symbol resolution.

    Args:
        event: Lambda event with optional 'populate' param (default: True)
        start_time: When the Lambda was invoked

    Returns:
        Response dict with setup results
    """
    logger.info("Starting ticker mapping setup...")

    try:
        # Lazy import
        from src.data.aurora.ticker_resolver import TickerResolver

        resolver = TickerResolver()

        # Create tables
        resolver.create_tables()
        logger.info("Created ticker_master and ticker_aliases tables")

        # Populate from CSV unless explicitly disabled
        populate = event.get('populate', True)
        count = 0

        if populate:
            count = resolver.populate_from_csv()
            logger.info(f"Populated {count} tickers from CSV")

        end_time = datetime.now()
        duration_seconds = (end_time - start_time).total_seconds()

        # Test resolution
        test_results = {}
        for test_symbol in ['NVDA19', 'NVDA', 'DBS19', 'D05.SI']:
            info = resolver.resolve(test_symbol)
            if info:
                test_results[test_symbol] = {
                    'resolved': True,
                    'yahoo': info.yahoo_symbol,
                    'dr': info.dr_symbol,
                    'company': info.company_name
                }
            else:
                test_results[test_symbol] = {'resolved': False}

        return {
            'statusCode': 200,
            'body': {
                'message': 'Ticker mapping setup completed',
                'duration_seconds': duration_seconds,
                'tables_created': True,
                'tickers_populated': count,
                'test_resolution': test_results
            }
        }

    except Exception as e:
        logger.error(f"Ticker mapping setup failed: {e}")
        logger.error(traceback.format_exc())

        return {
            'statusCode': 500,
            'body': {
                'message': 'Ticker mapping setup failed',
                'error': str(e),
                'traceback': traceback.format_exc()
            }
        }


def _handle_ticker_unification(event: Dict[str, Any], start_time: datetime) -> Dict[str, Any]:
    """Handle ticker unification migration (Phase 4).

    Migrates data tables to use ticker_master.id as the canonical identifier
    instead of raw symbol strings.

    Args:
        event: Lambda event with params:
            - phase: Migration phase ("4.1", "4.2", "4.4", "verify")
            - dry_run: If True, only show what would be done (optional)
        start_time: When the Lambda was invoked

    Returns:
        Response dict with migration results
    """
    logger.info("Starting ticker unification migration...")

    try:
        # Lazy import
        from scripts.aurora_ticker_unification_migration import run_migration

        phase = event.get('phase', 'verify')
        dry_run = event.get('dry_run', False)

        result = run_migration(phase=phase, dry_run=dry_run)

        end_time = datetime.now()
        duration_seconds = (end_time - start_time).total_seconds()

        return {
            'statusCode': 200,
            'body': {
                'message': f'Ticker unification migration phase {phase} completed',
                'duration_seconds': duration_seconds,
                **result
            }
        }

    except Exception as e:
        logger.error(f"Ticker unification migration failed: {e}")
        logger.error(traceback.format_exc())

        return {
            'statusCode': 500,
            'body': {
                'message': 'Ticker unification migration failed',
                'error': str(e),
                'traceback': traceback.format_exc()
            }
        }


# For local testing
if __name__ == '__main__':
    # Test execute_migration
    test_event = {
        'action': 'execute_migration',
        'sql': 'SELECT COUNT(*) FROM ticker_info;'
    }
    result = lambda_handler(test_event, None)
    print(json.dumps(result, indent=2))
