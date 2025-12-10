#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Run Fund Data Schema Migration

Purpose: Execute 003_fund_data_schema.sql migration to create fund_data table
Usage: ENV=dev doppler run -- python scripts/run_fund_data_migration.py
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.data.aurora.client import AuroraClient
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def check_table_exists(client: AuroraClient) -> bool:
    """Check if fund_data table already exists."""
    try:
        with client.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT COUNT(*) as count
                    FROM information_schema.TABLES
                    WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'fund_data'
                    """,
                    (client.database,)
                )
                result = cursor.fetchone()
                return result[0] > 0
    except Exception as e:
        logger.error(f"Error checking table existence: {e}")
        return False


def run_migration(client: AuroraClient, sql_file: Path) -> bool:
    """Run SQL migration file."""
    logger.info(f"Reading migration file: {sql_file}")
    sql_content = sql_file.read_text(encoding='utf-8')
    
    # Split by semicolons and filter out comments/empty statements
    statements = [
        stmt.strip()
        for stmt in sql_content.split(';')
        if stmt.strip() and not stmt.strip().startswith('--')
    ]
    
    logger.info(f"Executing {len(statements)} SQL statements...")
    
    try:
        with client.get_connection() as conn:
            with conn.cursor() as cursor:
                for i, statement in enumerate(statements, 1):
                    if statement:
                        logger.info(f"Executing statement {i}/{len(statements)}...")
                        cursor.execute(statement)
                conn.commit()
                logger.info("✅ Migration completed successfully")
                return True
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        return False


def verify_migration(client: AuroraClient) -> bool:
    """Verify migration by checking table structure."""
    try:
        with client.get_connection() as conn:
            with conn.cursor() as cursor:
                # Check table exists
                cursor.execute(
                    """
                    SELECT TABLE_NAME, ENGINE, TABLE_ROWS
                    FROM information_schema.TABLES
                    WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'fund_data'
                    """,
                    (client.database,)
                )
                table_info = cursor.fetchone()
                if not table_info:
                    logger.error("❌ Table fund_data not found after migration")
                    return False
                
                logger.info(f"✅ Table exists: {table_info}")
                
                # Check indexes
                cursor.execute("SHOW INDEX FROM fund_data")
                indexes = cursor.fetchall()
                logger.info(f"✅ Found {len(indexes)} indexes")
                
                # Check unique constraint
                cursor.execute(
                    """
                    SELECT CONSTRAINT_NAME
                    FROM information_schema.TABLE_CONSTRAINTS
                    WHERE TABLE_SCHEMA = %s 
                      AND TABLE_NAME = 'fund_data'
                      AND CONSTRAINT_TYPE = 'UNIQUE'
                      AND CONSTRAINT_NAME = 'uk_fund_data_composite'
                    """,
                    (client.database,)
                )
                unique_constraint = cursor.fetchone()
                if not unique_constraint:
                    logger.error("❌ Unique constraint uk_fund_data_composite not found")
                    return False
                
                logger.info("✅ Unique constraint uk_fund_data_composite exists")
                return True
    except Exception as e:
        logger.error(f"❌ Verification failed: {e}")
        return False


def main():
    """Main entry point."""
    # Get migration file path
    repo_root = Path(__file__).parent.parent
    migration_file = repo_root / "db" / "migrations" / "003_fund_data_schema.sql"
    
    if not migration_file.exists():
        logger.error(f"❌ Migration file not found: {migration_file}")
        sys.exit(1)
    
    # Initialize Aurora client
    logger.info("Connecting to Aurora...")
    client = AuroraClient()
    
    if not client.host:
        logger.error("❌ AURORA_HOST not set")
        sys.exit(1)
    
    logger.info(f"Connecting to {client.host}:{client.port}/{client.database}")
    
    # Check if table already exists
    if check_table_exists(client):
        logger.warning("⚠️  Table fund_data already exists. Skipping migration.")
        logger.info("Verifying existing table structure...")
        if verify_migration(client):
            logger.info("✅ Table structure is correct")
            sys.exit(0)
        else:
            logger.error("❌ Table exists but structure is incorrect")
            sys.exit(1)
    
    # Run migration
    logger.info("Running migration...")
    if not run_migration(client, migration_file):
        logger.error("❌ Migration failed")
        sys.exit(1)
    
    # Verify migration
    logger.info("Verifying migration...")
    if not verify_migration(client):
        logger.error("❌ Migration verification failed")
        sys.exit(1)
    
    logger.info("✅ Migration completed and verified successfully")


if __name__ == "__main__":
    main()
