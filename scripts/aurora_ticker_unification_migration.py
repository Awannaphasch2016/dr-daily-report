# -*- coding: utf-8 -*-
"""
Aurora Ticker Unification Migration

Migrates data tables to use ticker_master.id as the canonical identifier
instead of raw symbol strings. This enables robust lookups regardless of
which symbol format (DR: NVDA19, Yahoo: NVDA) is used.

Phase 4.1: Add ticker_master_id column to all data tables (non-breaking)
Phase 4.2: Backfill ticker_master_id from symbol aliases
Phase 4.3: Update code to use ticker_master_id for lookups
Phase 4.4: Cleanup old symbol columns and ticker_info table

Usage (from Lambda):
    from scripts.aurora_ticker_unification_migration import run_migration
    result = run_migration(phase="4.1")  # or "4.2", "4.4"
"""

import json
import logging
from datetime import datetime
from typing import Any, Dict, List

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


# =============================================================================
# Phase 4.1: Add ticker_master_id column to all data tables
# =============================================================================

# Tables that need ticker_master_id column
TABLES_TO_UPDATE = [
    'daily_prices',
    'daily_indicators',
    'indicator_percentiles',
    'comparative_features',
    'precomputed_reports',
]

# peer_correlations needs two columns
PEER_CORRELATIONS_COLUMNS = [
    ('ticker_master_id', 'id'),
    ('peer_ticker_master_id', 'ticker_master_id'),
]


# =============================================================================
# Phase 4.2: Backfill ticker_master_id from symbol aliases
# =============================================================================

def run_phase_4_2_backfill(client) -> Dict[str, Any]:
    """Backfill ticker_master_id for all existing data rows.

    Maps existing symbol → ticker_master_id via ticker_aliases table.
    """
    results = {
        'phase': '4.2',
        'status': 'started',
        'tables': {},
        'warnings': []
    }

    # Step 1: Build symbol → ticker_master_id mapping from ticker_aliases
    mapping_query = """
        SELECT symbol, ticker_id as ticker_master_id
        FROM ticker_aliases
    """
    try:
        mappings = client.fetch_all(mapping_query)
        symbol_to_master = {m['symbol'].upper(): m['ticker_master_id'] for m in mappings}
        results['mapping_count'] = len(symbol_to_master)
        logger.info(f"Loaded {len(symbol_to_master)} symbol mappings from ticker_aliases")
    except Exception as e:
        results['status'] = 'failed'
        results['error'] = f"Failed to load mappings: {e}"
        return results

    # Step 2: Update each table
    tables_to_update = [
        'daily_prices',
        'daily_indicators',
        'indicator_percentiles',
        'comparative_features',
        'precomputed_reports'
    ]

    for table in tables_to_update:
        table_result = {'updated': 0, 'not_found': 0}

        # Get distinct symbols in this table that need updating
        symbols_query = f"""
            SELECT DISTINCT symbol
            FROM {table}
            WHERE ticker_master_id IS NULL
        """
        try:
            rows = client.fetch_all(symbols_query)
            symbols_to_update = [r['symbol'] for r in rows if r['symbol']]
        except Exception as e:
            table_result['error'] = str(e)
            results['tables'][table] = table_result
            continue

        for symbol in symbols_to_update:
            master_id = symbol_to_master.get(symbol.upper())
            if master_id:
                update_query = f"""
                    UPDATE {table}
                    SET ticker_master_id = %s
                    WHERE symbol = %s AND ticker_master_id IS NULL
                """
                try:
                    affected = client.execute(update_query, (master_id, symbol), commit=True)
                    table_result['updated'] += affected if affected else 0
                except Exception as e:
                    logger.warning(f"Failed to update {table} for {symbol}: {e}")
            else:
                table_result['not_found'] += 1
                results['warnings'].append(f"{table}: No mapping for symbol '{symbol}'")

        results['tables'][table] = table_result
        logger.info(f"Updated {table}: {table_result['updated']} rows, {table_result['not_found']} unmapped")

    # Step 3: Update peer_correlations (has two symbol columns)
    peer_result = {'updated': 0, 'peer_updated': 0}

    # Update ticker_master_id from symbol column
    for symbol, master_id in symbol_to_master.items():
        try:
            # Update source ticker
            client.execute("""
                UPDATE peer_correlations
                SET ticker_master_id = %s
                WHERE symbol = %s AND ticker_master_id IS NULL
            """, (master_id, symbol), commit=True)

            # Update peer ticker
            client.execute("""
                UPDATE peer_correlations
                SET peer_ticker_master_id = %s
                WHERE peer_symbol = %s AND peer_ticker_master_id IS NULL
            """, (master_id, symbol), commit=True)
        except Exception as e:
            logger.warning(f"Failed to update peer_correlations for {symbol}: {e}")

    results['tables']['peer_correlations'] = peer_result

    # Step 4: Verify completeness
    verification = {}
    for table in tables_to_update:
        try:
            null_count = client.fetch_one(f"""
                SELECT COUNT(*) as cnt FROM {table} WHERE ticker_master_id IS NULL
            """)
            verification[table] = null_count.get('cnt', 0) if null_count else 0
        except Exception:
            verification[table] = 'error'

    results['null_counts'] = verification
    results['status'] = 'completed'

    return results


# =============================================================================
# Phase 4.4: Cleanup old columns and ticker_info table
# =============================================================================

PHASE_4_4_CLEANUP_SQL = [
    # Step 1: Add NOT NULL constraint (only after backfill is verified complete)
    "ALTER TABLE daily_prices MODIFY ticker_master_id INT NOT NULL",
    "ALTER TABLE daily_indicators MODIFY ticker_master_id INT NOT NULL",
    "ALTER TABLE indicator_percentiles MODIFY ticker_master_id INT NOT NULL",
    "ALTER TABLE comparative_features MODIFY ticker_master_id INT NOT NULL",
    "ALTER TABLE precomputed_reports MODIFY ticker_master_id INT NOT NULL",

    # Step 2: Add foreign key constraints
    """
    ALTER TABLE daily_prices
    ADD CONSTRAINT fk_daily_prices_master
    FOREIGN KEY (ticker_master_id) REFERENCES ticker_master(id)
    """,
    """
    ALTER TABLE daily_indicators
    ADD CONSTRAINT fk_daily_indicators_master
    FOREIGN KEY (ticker_master_id) REFERENCES ticker_master(id)
    """,
    """
    ALTER TABLE indicator_percentiles
    ADD CONSTRAINT fk_indicator_percentiles_master
    FOREIGN KEY (ticker_master_id) REFERENCES ticker_master(id)
    """,
    """
    ALTER TABLE comparative_features
    ADD CONSTRAINT fk_comparative_features_master
    FOREIGN KEY (ticker_master_id) REFERENCES ticker_master(id)
    """,
    """
    ALTER TABLE precomputed_reports
    ADD CONSTRAINT fk_precomputed_reports_master
    FOREIGN KEY (ticker_master_id) REFERENCES ticker_master(id)
    """,

    # Step 3: Drop old symbol columns (DESTRUCTIVE - ensure code is updated first!)
    # "ALTER TABLE daily_prices DROP COLUMN symbol",
    # "ALTER TABLE daily_indicators DROP COLUMN symbol",
    # "ALTER TABLE indicator_percentiles DROP COLUMN symbol",
    # "ALTER TABLE comparative_features DROP COLUMN symbol",
    # "ALTER TABLE precomputed_reports DROP COLUMN symbol",
    # "ALTER TABLE peer_correlations DROP COLUMN symbol",
    # "ALTER TABLE peer_correlations DROP COLUMN peer_symbol",

    # Step 4: Drop old ticker_id columns (after code migration)
    # "ALTER TABLE daily_prices DROP COLUMN ticker_id",
    # "ALTER TABLE daily_indicators DROP COLUMN ticker_id",
    # "ALTER TABLE indicator_percentiles DROP COLUMN ticker_id",
    # "ALTER TABLE comparative_features DROP COLUMN ticker_id",
    # "ALTER TABLE precomputed_reports DROP COLUMN ticker_id",

    # Step 5: Drop old ticker_info table (after all references removed)
    # "DROP TABLE IF EXISTS ticker_info",
]


# =============================================================================
# Migration Execution
# =============================================================================

def get_aurora_client():
    """Get Aurora client (import here to avoid circular imports)."""
    from src.data.aurora.client import get_aurora_client as _get_aurora_client
    return _get_aurora_client()


def check_column_exists(client, table: str, column: str) -> bool:
    """Check if a column exists in a table."""
    result = client.fetch_one("""
        SELECT COUNT(*) as cnt
        FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = %s
          AND COLUMN_NAME = %s
    """, (table, column))
    return result and result.get('cnt', 0) > 0


def check_index_exists(client, table: str, index_name: str) -> bool:
    """Check if an index exists on a table."""
    result = client.fetch_one("""
        SELECT COUNT(*) as cnt
        FROM information_schema.STATISTICS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = %s
          AND INDEX_NAME = %s
    """, (table, index_name))
    return result and result.get('cnt', 0) > 0


def run_phase_4_1(client) -> Dict[str, Any]:
    """Run Phase 4.1: Add ticker_master_id column to all data tables."""
    results = {
        'phase': '4.1',
        'status': 'started',
        'columns_added': [],
        'indexes_added': [],
        'skipped': [],
        'errors': []
    }

    # Step 1: Add ticker_master_id column to standard tables
    for table in TABLES_TO_UPDATE:
        column = 'ticker_master_id'
        index_name = f'idx_{table}_master_id'

        # Add column if not exists
        if check_column_exists(client, table, column):
            results['skipped'].append(f"{table}.{column} already exists")
            logger.info(f"Skipping column: {table}.{column} already exists")
        else:
            try:
                client.execute(f"""
                    ALTER TABLE {table}
                    ADD COLUMN ticker_master_id INT NULL AFTER ticker_id
                """, commit=True)
                results['columns_added'].append(f"{table}.{column}")
                logger.info(f"Added column: {table}.{column}")
            except Exception as e:
                if 'Duplicate column' in str(e):
                    results['skipped'].append(f"{table}.{column}")
                else:
                    results['errors'].append({'table': table, 'column': column, 'error': str(e)})
                    logger.error(f"Failed to add column {table}.{column}: {e}")

        # Add index if not exists
        if check_index_exists(client, table, index_name):
            results['skipped'].append(f"{table}.{index_name} already exists")
            logger.info(f"Skipping index: {table}.{index_name} already exists")
        else:
            try:
                client.execute(f"""
                    CREATE INDEX {index_name} ON {table} (ticker_master_id)
                """, commit=True)
                results['indexes_added'].append(f"{table}.{index_name}")
                logger.info(f"Added index: {table}.{index_name}")
            except Exception as e:
                if 'Duplicate key name' in str(e):
                    results['skipped'].append(f"{table}.{index_name}")
                else:
                    results['errors'].append({'table': table, 'index': index_name, 'error': str(e)})
                    logger.error(f"Failed to add index {table}.{index_name}: {e}")

    # Step 2: Add columns to peer_correlations (special case - two columns)
    table = 'peer_correlations'
    for column, after_col in PEER_CORRELATIONS_COLUMNS:
        index_name = f'idx_{table}_{column}'

        # Add column if not exists
        if check_column_exists(client, table, column):
            results['skipped'].append(f"{table}.{column} already exists")
            logger.info(f"Skipping column: {table}.{column} already exists")
        else:
            try:
                client.execute(f"""
                    ALTER TABLE {table}
                    ADD COLUMN {column} INT NULL AFTER {after_col}
                """, commit=True)
                results['columns_added'].append(f"{table}.{column}")
                logger.info(f"Added column: {table}.{column}")
            except Exception as e:
                if 'Duplicate column' in str(e):
                    results['skipped'].append(f"{table}.{column}")
                else:
                    results['errors'].append({'table': table, 'column': column, 'error': str(e)})
                    logger.error(f"Failed to add column {table}.{column}: {e}")

        # Add index if not exists
        if check_index_exists(client, table, index_name):
            results['skipped'].append(f"{table}.{index_name} already exists")
            logger.info(f"Skipping index: {table}.{index_name} already exists")
        else:
            try:
                client.execute(f"""
                    CREATE INDEX {index_name} ON {table} ({column})
                """, commit=True)
                results['indexes_added'].append(f"{table}.{index_name}")
                logger.info(f"Added index: {table}.{index_name}")
            except Exception as e:
                if 'Duplicate key name' in str(e):
                    results['skipped'].append(f"{table}.{index_name}")
                else:
                    results['errors'].append({'table': table, 'index': index_name, 'error': str(e)})
                    logger.error(f"Failed to add index {table}.{index_name}: {e}")

    results['status'] = 'completed' if not results['errors'] else 'completed_with_errors'
    return results


def run_migration(phase: str = "4.1", dry_run: bool = False) -> Dict[str, Any]:
    """Run the specified migration phase.

    Args:
        phase: Migration phase to run ("4.1", "4.2", "4.4", or "verify")
        dry_run: If True, only show what would be done

    Returns:
        Dict with migration results
    """
    client = get_aurora_client()

    if phase == "4.1":
        return run_phase_4_1(client)
    elif phase == "4.2":
        return run_phase_4_2_backfill(client)
    elif phase == "4.4":
        # Phase 4.4 is destructive - require explicit confirmation
        return {
            'status': 'blocked',
            'message': 'Phase 4.4 is destructive. Uncomment SQL statements and run manually.',
            'sql': PHASE_4_4_CLEANUP_SQL
        }
    elif phase == "verify":
        return verify_migration(client)
    else:
        return {
            'status': 'error',
            'message': f"Unknown phase: {phase}. Valid phases: 4.1, 4.2, 4.4, verify"
        }


def verify_migration(client) -> Dict[str, Any]:
    """Verify migration status across all phases."""
    results = {
        'phase': 'verify',
        'timestamp': datetime.now().isoformat(),
        'checks': {}
    }

    # Check Phase 4.1: Columns exist
    tables = ['daily_prices', 'daily_indicators', 'indicator_percentiles',
              'comparative_features', 'precomputed_reports']

    phase_4_1_status = {}
    for table in tables:
        has_column = check_column_exists(client, table, 'ticker_master_id')
        phase_4_1_status[table] = 'OK' if has_column else 'MISSING'

    # Check peer_correlations separately
    phase_4_1_status['peer_correlations'] = 'OK' if (
        check_column_exists(client, 'peer_correlations', 'ticker_master_id') and
        check_column_exists(client, 'peer_correlations', 'peer_ticker_master_id')
    ) else 'MISSING'

    results['checks']['phase_4_1_columns'] = phase_4_1_status

    # Check Phase 4.2: Data backfilled
    phase_4_2_status = {}
    for table in tables:
        try:
            total = client.fetch_one(f"SELECT COUNT(*) as cnt FROM {table}")
            null_count = client.fetch_one(f"SELECT COUNT(*) as cnt FROM {table} WHERE ticker_master_id IS NULL")
            total_cnt = total.get('cnt', 0) if total else 0
            null_cnt = null_count.get('cnt', 0) if null_count else 0

            if total_cnt == 0:
                phase_4_2_status[table] = 'EMPTY'
            elif null_cnt == 0:
                phase_4_2_status[table] = 'OK'
            else:
                phase_4_2_status[table] = f'PARTIAL ({null_cnt}/{total_cnt} null)'
        except Exception as e:
            phase_4_2_status[table] = f'ERROR: {e}'

    results['checks']['phase_4_2_backfill'] = phase_4_2_status

    # Overall status
    all_columns_ok = all(v == 'OK' for v in phase_4_1_status.values())
    all_backfill_ok = all(v in ['OK', 'EMPTY'] for v in phase_4_2_status.values())

    results['overall'] = {
        'phase_4_1': 'COMPLETE' if all_columns_ok else 'INCOMPLETE',
        'phase_4_2': 'COMPLETE' if all_backfill_ok else 'INCOMPLETE',
        'phase_4_3': 'NOT_STARTED',  # Code changes - tracked separately
        'phase_4_4': 'NOT_STARTED',  # Cleanup - tracked separately
    }

    return results


def lambda_handler(event, context):
    """Lambda entry point for ticker unification migration.

    Event params:
        phase: Migration phase to run ("4.1", "4.2", "4.4", "verify")
        dry_run: If True, only show what would be done (optional)
    """
    import time

    start_time = time.time()
    phase = event.get('phase', '4.1')
    dry_run = event.get('dry_run', False)

    try:
        result = run_migration(phase=phase, dry_run=dry_run)
        duration = time.time() - start_time

        return {
            'statusCode': 200,
            'body': {
                'message': f'Ticker unification migration phase {phase} completed',
                'duration_seconds': round(duration, 3),
                **result
            }
        }
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        return {
            'statusCode': 500,
            'body': {
                'message': 'Migration failed',
                'error': str(e)
            }
        }


if __name__ == '__main__':
    import sys

    # Parse command line args
    phase = sys.argv[1] if len(sys.argv) > 1 else 'verify'

    result = run_migration(phase=phase)
    print(json.dumps(result, indent=2, default=str))
