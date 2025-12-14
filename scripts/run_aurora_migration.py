#!/usr/bin/env python3
"""
Aurora Schema Migration Runner

Executes SQL migration files against Aurora MySQL database in order.
Designed for idempotency - safe to run multiple times.

Usage:
    ENV=dev doppler run -- python scripts/run_aurora_migration.py
    ENV=dev doppler run -- python scripts/run_aurora_migration.py --migration 001

Requirements:
    - AURORA_HOST environment variable set
    - AURORA_PASSWORD environment variable set
    - AURORA_DATABASE environment variable set (defaults to 'ticker_data')
    - AURORA_USER environment variable set (defaults to 'admin')
"""

import argparse
import logging
import os
import sys
from pathlib import Path
from typing import List

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.data.aurora.client import get_aurora_client

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def get_migration_files(migrations_dir: Path, specific_migration: str = None) -> List[Path]:
    """Get migration files sorted by name.

    Args:
        migrations_dir: Directory containing migration SQL files
        specific_migration: If provided, only return this migration (e.g., "001")

    Returns:
        List of Path objects sorted by filename
    """
    if specific_migration:
        pattern = f"{specific_migration}_*.sql"
        files = sorted(migrations_dir.glob(pattern))
        if not files:
            logger.error(f"Migration {specific_migration} not found in {migrations_dir}")
            return []
        return files
    else:
        # Get all .sql files, sorted by name (001_, 002_, 003_, etc.)
        return sorted(migrations_dir.glob("*.sql"))


def parse_sql_statements(sql_content: str) -> List[str]:
    """Parse SQL file into individual statements.

    Handles:
    - Multi-line statements separated by semicolons
    - Comments (-- and /* */)
    - Empty lines

    Args:
        sql_content: Raw SQL file content

    Returns:
        List of executable SQL statements
    """
    # Remove single-line comments
    lines = []
    in_multiline_comment = False

    for line in sql_content.split('\n'):
        # Handle multi-line comments
        if '/*' in line:
            in_multiline_comment = True
        if '*/' in line:
            in_multiline_comment = False
            continue
        if in_multiline_comment:
            continue

        # Remove single-line comments
        if '--' in line:
            line = line[:line.index('--')]

        # Skip empty lines
        line = line.strip()
        if line:
            lines.append(line)

    # Join lines and split by semicolons
    full_sql = ' '.join(lines)
    statements = [s.strip() for s in full_sql.split(';') if s.strip()]

    return statements


def run_migration(client, migration_file: Path) -> bool:
    """Execute a migration file.

    Args:
        client: AuroraClient instance
        migration_file: Path to SQL migration file

    Returns:
        True if successful, False otherwise
    """
    logger.info(f"Running migration: {migration_file.name}")

    try:
        # Read migration file
        with open(migration_file, 'r', encoding='utf-8') as f:
            sql_content = f.read()

        # Parse statements
        statements = parse_sql_statements(sql_content)
        logger.info(f"  Found {len(statements)} SQL statements to execute")

        # Execute each statement
        for i, statement in enumerate(statements, 1):
            # Log first 80 chars of statement for visibility
            stmt_preview = statement[:80] + '...' if len(statement) > 80 else statement
            logger.info(f"  Executing statement {i}/{len(statements)}: {stmt_preview}")

            with client.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(statement)
                    conn.commit()

                    # Log affected rows if applicable
                    if cursor.rowcount >= 0:
                        logger.info(f"    ✓ Affected {cursor.rowcount} rows")
                    else:
                        logger.info(f"    ✓ Executed successfully")

        logger.info(f"✅ Migration {migration_file.name} completed successfully")
        return True

    except Exception as e:
        logger.error(f"❌ Migration {migration_file.name} failed: {e}")
        return False


def verify_tables_created(client) -> bool:
    """Verify that expected tables exist after migrations.

    Args:
        client: AuroraClient instance

    Returns:
        True if all tables exist, False otherwise
    """
    expected_tables = ['ticker_info', 'precomputed_reports', 'fund_data']

    logger.info("\nVerifying tables created:")

    try:
        with client.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SHOW TABLES")
                existing_tables = [row[f'Tables_in_{client.database}'] for row in cursor.fetchall()]

        all_exist = True
        for table in expected_tables:
            exists = table in existing_tables
            status = "✓" if exists else "✗"
            logger.info(f"  {status} {table}")
            if not exists:
                all_exist = False

        return all_exist

    except Exception as e:
        logger.error(f"❌ Table verification failed: {e}")
        return False


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Run Aurora schema migrations')
    parser.add_argument(
        '--migration',
        type=str,
        help='Specific migration to run (e.g., "001"). If not provided, runs all migrations.'
    )
    parser.add_argument(
        '--migrations-dir',
        type=str,
        default='db/migrations',
        help='Directory containing migration files (default: db/migrations)'
    )
    args = parser.parse_args()

    # Validate environment
    required_env_vars = ['AURORA_HOST', 'AURORA_PASSWORD']
    missing_vars = [var for var in required_env_vars if not os.environ.get(var)]

    if missing_vars:
        logger.error(f"❌ Missing required environment variables: {', '.join(missing_vars)}")
        logger.error("Run with: ENV=dev doppler run -- python scripts/run_aurora_migration.py")
        sys.exit(1)

    # Get migrations directory
    migrations_dir = project_root / args.migrations_dir
    if not migrations_dir.exists():
        logger.error(f"❌ Migrations directory not found: {migrations_dir}")
        sys.exit(1)

    # Get migration files
    migration_files = get_migration_files(migrations_dir, args.migration)

    if not migration_files:
        logger.error("❌ No migration files found")
        sys.exit(1)

    logger.info(f"Found {len(migration_files)} migration(s) to run:")
    for f in migration_files:
        logger.info(f"  - {f.name}")

    # Initialize Aurora client
    logger.info("\nConnecting to Aurora...")
    client = get_aurora_client()

    # Health check
    health = client.health_check()
    if health['status'] != 'healthy':
        logger.error(f"❌ Aurora health check failed: {health.get('error')}")
        sys.exit(1)

    logger.info(f"✓ Connected to Aurora: {health['host']}/{health['database']}")
    logger.info(f"  Server time: {health['server_time']}")

    # Run migrations
    logger.info("\n" + "="*60)
    logger.info("Starting migrations")
    logger.info("="*60)

    success_count = 0
    for migration_file in migration_files:
        if run_migration(client, migration_file):
            success_count += 1
        else:
            logger.error(f"\n❌ Migration failed: {migration_file.name}")
            logger.error("Stopping execution (subsequent migrations may depend on this one)")
            sys.exit(1)

    logger.info("\n" + "="*60)
    logger.info(f"Migration Summary: {success_count}/{len(migration_files)} completed")
    logger.info("="*60)

    # Verify tables
    if verify_tables_created(client):
        logger.info("\n✅ All migrations completed successfully!")
        logger.info("Schema is ready for use.")
        sys.exit(0)
    else:
        logger.error("\n⚠️  Migrations completed but some tables are missing")
        logger.error("Please check logs and verify schema manually")
        sys.exit(1)


if __name__ == '__main__':
    main()
