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


def run_make_ticker_id_required_migration():
    """Make ticker_id INT NOT NULL with FK constraint

    Changes:
    1. Change ticker_id to INT NOT NULL (matches ticker_master.id type)
    2. Add foreign key constraint to ticker_master(id)

    This enforces at schema level what code already enforces:
    ticker_id is always populated before INSERT (code fails fast if ticker_info not found).

    Type Match: ticker_master.id is INT, so ticker_id must also be INT for FK compatibility.
    """
    from src.data.aurora.client import get_aurora_client

    logger.info("=" * 80)
    logger.info("Migration: Make ticker_id required in precomputed_reports")
    logger.info("=" * 80)

    client = get_aurora_client()

    try:
        # Step 1: Check current column definition
        schema_query = "DESCRIBE precomputed_reports"
        columns = client.fetch_all(schema_query)
        ticker_id_column = next((c for c in columns if c['Field'] == 'ticker_id'), None)

        if not ticker_id_column:
            logger.info("ticker_id column not found - will ADD it")
            logger.info("Step 1/2: Adding ticker_id INT NOT NULL column")
            # Add column after id column
            client.execute(
                "ALTER TABLE precomputed_reports ADD COLUMN ticker_id INT NOT NULL AFTER id",
                commit=True
            )
            logger.info("✅ Successfully added ticker_id column")
        else:
            logger.info(f"Current ticker_id definition: {ticker_id_column}")
            # Step 2: Modify existing column to INT NOT NULL (matches ticker_master.id)
            logger.info("Step 1/2: Modifying ticker_id to INT NOT NULL")
            client.execute(
                "ALTER TABLE precomputed_reports MODIFY COLUMN ticker_id INT NOT NULL",
                commit=True
            )
            logger.info("✅ Successfully modified ticker_id column")

        # Step 3: Add foreign key constraint (if not exists)
        logger.info("Step 2/2: Adding foreign key constraint")

        # Check if FK already exists
        fk_check_query = """
            SELECT CONSTRAINT_NAME FROM information_schema.KEY_COLUMN_USAGE
            WHERE TABLE_SCHEMA = DATABASE()
            AND TABLE_NAME = 'precomputed_reports'
            AND COLUMN_NAME = 'ticker_id'
            AND REFERENCED_TABLE_NAME IS NOT NULL
        """
        existing_fks = client.fetch_all(fk_check_query)

        if existing_fks:
            logger.info(f"✅ Foreign key already exists: {existing_fks[0]['CONSTRAINT_NAME']}")
        else:
            client.execute(
                """ALTER TABLE precomputed_reports
                   ADD CONSTRAINT fk_precomputed_reports_ticker_id
                   FOREIGN KEY (ticker_id) REFERENCES ticker_master(id)""",
                commit=True
            )
            logger.info("✅ Successfully added foreign key constraint")

        # Step 4: Verify changes
        verify_columns = client.fetch_all(schema_query)
        ticker_id_after = next((c for c in verify_columns if c['Field'] == 'ticker_id'), None)

        logger.info(f"ticker_id after migration: {ticker_id_after}")

        return {
            'status': 'success',
            'message': 'Successfully made ticker_id required with FK constraint',
            'migration_applied': True,
            'before': str(ticker_id_column),
            'after': str(ticker_id_after)
        }

    except Exception as e:
        logger.error(f"❌ Migration failed: {e}", exc_info=True)
        return {
            'status': 'error',
            'message': f'Migration failed: {str(e)}',
            'migration_applied': False
        }


def run_add_pdf_columns_migration():
    """Add PDF metadata columns to precomputed_reports table (Migration 019)

    Adds: pdf_s3_key, pdf_presigned_url, pdf_url_expires_at, pdf_generated_at
    All operations are idempotent (IF NOT EXISTS) for safe retry.
    """
    from src.data.aurora.client import get_aurora_client

    logger.info("=" * 80)
    logger.info("Migration 019: Add PDF columns to precomputed_reports")
    logger.info("=" * 80)

    client = get_aurora_client()

    try:
        # Check current schema
        schema_query = "DESCRIBE precomputed_reports"
        existing_columns = client.fetch_all(schema_query)
        column_names = {row['Field'] for row in existing_columns}

        logger.info(f"Current columns: {sorted(column_names)}")

        # Define PDF columns to add (idempotent)
        pdf_columns = ['pdf_s3_key', 'pdf_presigned_url', 'pdf_url_expires_at', 'pdf_generated_at']
        missing_columns = [col for col in pdf_columns if col not in column_names]

        if not missing_columns:
            logger.info("✅ All PDF columns already exist - migration not needed")
            return {
                'status': 'success',
                'message': 'All PDF columns already exist',
                'migration_applied': False
            }

        logger.info(f"Missing columns: {missing_columns}")

        # Execute migration SQL (idempotent operations with IF NOT EXISTS)
        logger.info("Executing migration 019...")

        # Add PDF columns (IF NOT EXISTS for idempotency)
        alter_table_sql = """
            ALTER TABLE precomputed_reports
                ADD COLUMN IF NOT EXISTS pdf_s3_key VARCHAR(500) DEFAULT NULL
                    COMMENT 'S3 key for uploaded PDF',
                ADD COLUMN IF NOT EXISTS pdf_presigned_url TEXT DEFAULT NULL
                    COMMENT 'Cached presigned URL (24h TTL)',
                ADD COLUMN IF NOT EXISTS pdf_url_expires_at DATETIME DEFAULT NULL
                    COMMENT 'When presigned URL expires',
                ADD COLUMN IF NOT EXISTS pdf_generated_at TIMESTAMP NULL DEFAULT NULL
                    COMMENT 'When PDF was generated'
        """

        logger.info("Adding PDF columns...")
        client.execute(alter_table_sql, commit=True)

        # Add index for PDF lookups
        index_sql = """
            CREATE INDEX IF NOT EXISTS idx_pdf_generated
                ON precomputed_reports(pdf_generated_at DESC)
        """

        logger.info("Creating index for PDF lookups...")
        client.execute(index_sql, commit=True)

        logger.info("✅ Successfully executed migration statements")

        # Verify all columns were added
        verify_schema = client.fetch_all(schema_query)
        verify_columns = {row['Field'] for row in verify_schema}

        still_missing = [col for col in pdf_columns if col not in verify_columns]

        if not still_missing:
            logger.info(f"✅ Verification passed - all 4 PDF columns exist")
            return {
                'status': 'success',
                'message': 'Successfully added PDF columns',
                'migration_applied': True,
                'columns_added': missing_columns
            }
        else:
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


def run_sql_migration(migration_name: str, sql_file: str):
    """Run an idempotent SQL migration from db/migrations/.

    Uses CREATE TABLE IF NOT EXISTS / CREATE INDEX IF NOT EXISTS
    so safe to re-run.

    Args:
        migration_name: Human label for logging
        sql_file: Filename under db/migrations/
    """
    import os
    from src.data.aurora.client import get_aurora_client

    logger.info("=" * 80)
    logger.info(f"Migration: {migration_name}")
    logger.info("=" * 80)

    client = get_aurora_client()

    sql_path = os.path.join(os.path.dirname(__file__), '..', 'db', 'migrations', sql_file)
    sql_path = os.path.normpath(sql_path)

    with open(sql_path, 'r') as f:
        sql = f.read()

    # Strip comments for cleaner logging
    statements = [s.strip() for s in sql.split(';') if s.strip() and not s.strip().startswith('--')]

    try:
        for stmt in statements:
            logger.info(f"Executing: {stmt[:120]}...")
            client.execute(stmt, commit=True)

        logger.info(f"✅ Migration '{migration_name}' completed successfully")

        # Verify table exists by extracting table name from CREATE TABLE
        import re
        match = re.search(r'CREATE TABLE IF NOT EXISTS\s+(\w+)', sql)
        if match:
            table_name = match.group(1)
            verify = client.fetch_one(
                "SELECT COUNT(*) as cnt FROM information_schema.tables "
                "WHERE table_schema = DATABASE() AND table_name = %s",
                (table_name,)
            )
            if verify and verify.get('cnt', 0) > 0:
                logger.info(f"✅ Verification passed: table '{table_name}' exists")
            else:
                logger.error(f"❌ Verification failed: table '{table_name}' not found")
                return {
                    'status': 'error',
                    'message': f'Table {table_name} not found after migration',
                    'migration_applied': False
                }

        return {
            'status': 'success',
            'message': f'Migration {migration_name} applied successfully',
            'migration_applied': True
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
        >>> lambda_handler({'migration': 'make_ticker_id_required'}, None)
        {'statusCode': 200, 'body': {...}}
        >>> lambda_handler({'migration': 'add_pdf_columns'}, None)
        {'statusCode': 200, 'body': {...}}
        >>> lambda_handler({'migration': 'create_sgx_tables'}, None)  # runs 021 + 022
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
    elif migration == 'make_ticker_id_required':
        result = run_make_ticker_id_required_migration()
        return {
            'statusCode': 200 if result['status'] == 'success' else 500,
            'body': json.dumps(result)
        }
    elif migration == 'add_pdf_columns':
        result = run_add_pdf_columns_migration()
        return {
            'statusCode': 200 if result['status'] == 'success' else 500,
            'body': json.dumps(result)
        }
    elif migration == 'create_data_acquisitions':
        result = run_sql_migration(
            'Create data_acquisitions table (021)',
            '021_create_data_acquisitions.sql'
        )
        return {
            'statusCode': 200 if result['status'] == 'success' else 500,
            'body': json.dumps(result)
        }
    elif migration == 'create_sgx_filings':
        result = run_sql_migration(
            'Create sgx_filings table (022)',
            '022_create_sgx_filings.sql'
        )
        return {
            'statusCode': 200 if result['status'] == 'success' else 500,
            'body': json.dumps(result)
        }
    elif migration == 'create_sgx_tables':
        # Convenience: run both 021 + 022 in order (FK dependency)
        result_021 = run_sql_migration(
            'Create data_acquisitions table (021)',
            '021_create_data_acquisitions.sql'
        )
        if result_021['status'] != 'success':
            return {
                'statusCode': 500,
                'body': json.dumps({
                    'status': 'error',
                    'message': f'Migration 021 failed: {result_021["message"]}',
                    'migration_applied': False
                })
            }

        result_022 = run_sql_migration(
            'Create sgx_filings table (022)',
            '022_create_sgx_filings.sql'
        )
        combined = {
            'status': result_022['status'],
            'message': 'Both tables created successfully' if result_022['status'] == 'success'
                else f'Migration 022 failed: {result_022["message"]}',
            'migration_applied': result_022['status'] == 'success',
            'details': {
                '021_data_acquisitions': result_021,
                '022_sgx_filings': result_022
            }
        }
        return {
            'statusCode': 200 if combined['status'] == 'success' else 500,
            'body': json.dumps(combined)
        }
    elif migration == 'make_sgx_ticker_nullable':
        result = run_sql_migration(
            'Make sgx_filings.ticker_id nullable + add attachment_s3_key (028)',
            '028_make_sgx_ticker_id_nullable.sql'
        )
        return {
            'statusCode': 200 if result['status'] == 'success' else 500,
            'body': json.dumps(result)
        }
    elif migration == 'create_edinet_filings':
        result = run_sql_migration(
            'Create edinet_filings table (029)',
            '029_create_edinet_filings.sql'
        )
        return {
            'statusCode': 200 if result['status'] == 'success' else 500,
            'body': json.dumps(result)
        }
    elif migration == 'create_webhook_health_checks':
        result = run_sql_migration(
            'Create webhook_health_checks table (030)',
            '030_create_webhook_health_checks.sql'
        )
        return {
            'statusCode': 200 if result['status'] == 'success' else 500,
            'body': json.dumps(result)
        }
    elif migration == 'create_ingestion_methods':
        result = run_sql_migration(
            'Create ingestion_methods table + FK on data_acquisitions (031)',
            '031_create_ingestion_methods.sql'
        )
        return {
            'statusCode': 200 if result['status'] == 'success' else 500,
            'body': json.dumps(result)
        }
    elif migration == 'create_sec_edgar_filings':
        result = run_sql_migration(
            'Create sec_edgar_filings table (032)',
            '032_create_sec_edgar_filings.sql'
        )
        return {
            'statusCode': 200 if result['status'] == 'success' else 500,
            'body': json.dumps(result)
        }
    elif migration == 'create_hkex_filings':
        result = run_sql_migration(
            'Create hkex_filings table (033)',
            '033_create_hkex_filings.sql'
        )
        return {
            'statusCode': 200 if result['status'] == 'success' else 500,
            'body': json.dumps(result)
        }
    elif migration == 'create_metric_config':
        result = run_sql_migration(
            'Create metric_config table (034)',
            '034_create_metric_config.sql'
        )
        return {
            'statusCode': 200 if result['status'] == 'success' else 500,
            'body': json.dumps(result)
        }
    elif migration == 'create_traces':
        result = run_sql_migration(
            'Create traces + trace_scores tables (037)',
            '037_create_traces.sql'
        )
        return {
            'statusCode': 200 if result['status'] == 'success' else 500,
            'body': json.dumps(result)
        }
    elif migration == 'create_model_catalog':
        result = run_sql_migration(
            'Create model_catalog table + performance view (039)',
            '039_create_model_catalog.sql'
        )
        return {
            'statusCode': 200 if result['status'] == 'success' else 500,
            'body': json.dumps(result)
        }
    elif migration == 'update_performance_view':
        result = run_sql_migration(
            'Reshape performance view for per-scorer versioning (040)',
            '040_update_performance_view.sql'
        )
        return {
            'statusCode': 200 if result['status'] == 'success' else 500,
            'body': json.dumps(result)
        }
    elif migration == 'inspect_reports_uncertainty':
        from src.data.aurora.client import get_aurora_client
        client = get_aurora_client()
        rows = client.fetch_all("""
            SELECT
                pr.ticker_id,
                ta.symbol,
                CASE
                    WHEN pr.report_text LIKE '%ความไม่แน่นอน%'
                      OR pr.report_text LIKE '%uncertainty%'
                      OR pr.report_text LIKE '%UNCERTAINTY%'
                    THEN 'HAS_UNCERTAINTY'
                    ELSE 'CLEAN'
                END as uncertainty_status,
                LEFT(CAST(pr.computed_at AS CHAR), 19) as computed_at,
                LENGTH(pr.report_text) as report_length
            FROM precomputed_reports pr
            LEFT JOIN ticker_aliases ta ON pr.ticker_id = ta.ticker_id AND ta.is_primary = 1
            WHERE pr.report_text IS NOT NULL
              AND LENGTH(pr.report_text) > 10
            ORDER BY ta.symbol
        """)
        summary = {'HAS_UNCERTAINTY': [], 'CLEAN': []}
        for row in rows:
            status = row['uncertainty_status']
            summary[status].append({
                'symbol': row.get('symbol', f"id:{row['ticker_id']}"),
                'computed_at': str(row.get('computed_at', 'N/A')),
                'report_length': row.get('report_length', 0),
            })
        return {
            'statusCode': 200,
            'body': json.dumps({
                'total_reports': len(rows),
                'clean_count': len(summary['CLEAN']),
                'has_uncertainty_count': len(summary['HAS_UNCERTAINTY']),
                'clean': summary['CLEAN'],
                'has_uncertainty': summary['HAS_UNCERTAINTY'],
            }, ensure_ascii=False)
        }
    else:
        return {
            'statusCode': 400,
            'body': json.dumps({
                'status': 'error',
                'message': f'Unknown migration: {migration}',
                'available_migrations': [
                    'add_strategy_column', 'make_ticker_id_required', 'add_pdf_columns',
                    'create_data_acquisitions', 'create_sgx_filings', 'create_sgx_tables',
                    'make_sgx_ticker_nullable', 'create_edinet_filings',
                    'create_webhook_health_checks', 'create_ingestion_methods',
                    'create_sec_edgar_filings', 'create_hkex_filings',
                    'create_metric_config',
                    'create_traces',
                    'create_model_catalog',
                    'update_performance_view'
                ]
            })
        }
