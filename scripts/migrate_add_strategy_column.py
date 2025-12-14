#!/usr/bin/env python3
"""
Migration: Add 'strategy' column to precomputed_reports table

This migration adds the missing 'strategy' column that worker Lambdas
expect when storing reports to Aurora cache.

Usage:
    python scripts/migrate_add_strategy_column.py
"""

import logging
import os
import sys

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.data.aurora.client import get_aurora_client

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main():
    """Run migration to add strategy column"""

    logger.info("=" * 80)
    logger.info("Migration: Add 'strategy' column to precomputed_reports")
    logger.info("=" * 80)

    # Get Aurora client
    client = get_aurora_client()

    # Check if column already exists
    check_query = """
        SELECT COUNT(*) as col_exists
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
        AND TABLE_NAME = 'precomputed_reports'
        AND COLUMN_NAME = 'strategy'
    """

    result = client.fetch_one(check_query)
    col_exists = result['col_exists'] if result else 0

    if col_exists > 0:
        logger.info("✅ Column 'strategy' already exists - migration not needed")
        return 0

    logger.info("Column 'strategy' does not exist - adding it now...")

    # Add strategy column
    # ENUM matches the values used in the code: 'single-stage' or 'multi-stage'
    # Default to 'multi-stage' for existing rows
    alter_query = """
        ALTER TABLE precomputed_reports
        ADD COLUMN strategy ENUM('single-stage', 'multi-stage')
        NOT NULL DEFAULT 'multi-stage'
        AFTER report_json
    """

    try:
        logger.info("Executing ALTER TABLE...")
        client.execute(alter_query, commit=True)
        logger.info("✅ Successfully added 'strategy' column")

        # Verify the column was added
        verify_result = client.fetch_one(check_query)
        verify_exists = verify_result['col_exists'] if verify_result else 0

        if verify_exists > 0:
            logger.info("✅ Verification passed - column exists")
            return 0
        else:
            logger.error("❌ Verification failed - column still missing!")
            return 1

    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
