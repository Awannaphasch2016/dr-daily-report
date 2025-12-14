#!/usr/bin/env python3
"""
Query Aurora's current schema state to discover what tables and columns exist.

This script generates a comprehensive report of the current Aurora schema
to support data-driven migration planning.

Usage:
    ENV=dev doppler run -- python scripts/query_aurora_current_schema.py

Output:
    - Prints current schema to stdout
    - Creates docs/aurora_current_state_YYYYMMDD.md for audit trail
"""

import sys
import os
from datetime import datetime
from typing import Dict, List, Any

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.data.aurora.client import get_aurora_client


def get_all_tables(client) -> List[str]:
    """Query all tables in the current database.

    Returns:
        List of table names
    """
    query = "SHOW TABLES"
    result = client.fetch_all(query, ())

    # SHOW TABLES returns dict with key like 'Tables_in_ticker_data'
    # Extract the table name from the first value of each row
    tables = [list(row.values())[0] for row in result]
    return sorted(tables)


def get_table_schema(client, table_name: str) -> Dict[str, Any]:
    """Query detailed schema for a specific table.

    Args:
        client: Aurora client
        table_name: Table to describe

    Returns:
        Dict with column details
    """
    query = f"DESCRIBE {table_name}"
    result = client.fetch_all(query, ())

    # Transform to dict: {column_name: {Type, Null, Key, Default, Extra}}
    schema = {}
    for row in result:
        col_name = row['Field']
        schema[col_name] = {
            'Type': row['Type'],
            'Null': row['Null'],
            'Key': row.get('Key', ''),
            'Default': row.get('Default'),
            'Extra': row.get('Extra', '')
        }

    return schema


def get_full_schema_info(client) -> Dict[str, Any]:
    """Query comprehensive schema information via INFORMATION_SCHEMA.

    Returns:
        Dict with table -> columns mapping
    """
    query = """
        SELECT
            TABLE_NAME,
            COLUMN_NAME,
            DATA_TYPE,
            COLUMN_TYPE,
            IS_NULLABLE,
            COLUMN_KEY,
            COLUMN_DEFAULT,
            EXTRA
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
        ORDER BY TABLE_NAME, ORDINAL_POSITION
    """

    result = client.fetch_all(query, ())

    # Group by table
    tables = {}
    for row in result:
        table = row['TABLE_NAME']
        if table not in tables:
            tables[table] = {}

        tables[table][row['COLUMN_NAME']] = {
            'data_type': row['DATA_TYPE'],
            'column_type': row['COLUMN_TYPE'],
            'nullable': row['IS_NULLABLE'] == 'YES',
            'key': row.get('COLUMN_KEY', ''),
            'default': row.get('COLUMN_DEFAULT'),
            'extra': row.get('EXTRA', '')
        }

    return tables


def print_schema_report(tables: Dict[str, Any]):
    """Print current schema report to stdout."""
    print("\n" + "="*80)
    print(f"AURORA CURRENT SCHEMA STATE - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80 + "\n")

    print(f"📊 **Total Tables:** {len(tables)}\n")

    for table_name in sorted(tables.keys()):
        columns = tables[table_name]
        print(f"\n### Table: `{table_name}` ({len(columns)} columns)")
        print("-" * 80)

        # Print column details
        for col_name, col_info in columns.items():
            nullable = "NULL" if col_info['nullable'] else "NOT NULL"
            key_info = f" [{col_info['key']}]" if col_info['key'] else ""
            default = f" DEFAULT {col_info['default']}" if col_info['default'] else ""
            extra = f" {col_info['extra']}" if col_info['extra'] else ""

            print(f"  - {col_name:30} {col_info['column_type']:20} {nullable:10}{key_info}{default}{extra}")


def generate_markdown_report(tables: Dict[str, Any]) -> str:
    """Generate markdown report of current schema.

    Returns:
        Markdown formatted string
    """
    report = []
    report.append(f"# Aurora Current Schema State")
    report.append(f"\n**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append(f"\n**Total Tables:** {len(tables)}")
    report.append("\n---\n")

    for table_name in sorted(tables.keys()):
        columns = tables[table_name]
        report.append(f"\n## Table: `{table_name}`")
        report.append(f"\n**Column Count:** {len(columns)}")
        report.append("\n| Column | Type | Nullable | Key | Default | Extra |")
        report.append("|--------|------|----------|-----|---------|-------|")

        for col_name, col_info in columns.items():
            nullable = "YES" if col_info['nullable'] else "NO"
            key = col_info.get('key', '')
            default = col_info.get('default', '')
            extra = col_info.get('extra', '')

            report.append(f"| {col_name} | {col_info['column_type']} | {nullable} | {key} | {default} | {extra} |")

        report.append("")

    return "\n".join(report)


def main():
    """Main entry point."""
    print("🔍 Querying Aurora current schema state...")

    try:
        # Get Aurora client
        client = get_aurora_client()

        # Get all tables
        print("📋 Fetching table list...")
        table_names = get_all_tables(client)

        if not table_names:
            print("\n⚠️  No tables found in Aurora!")
            print("   Database appears to be empty")
            return

        print(f"✅ Found {len(table_names)} tables: {', '.join(table_names)}\n")

        # Get detailed schema for all tables
        print("📊 Fetching detailed schema information...")
        tables = get_full_schema_info(client)

        # Print report to stdout
        print_schema_report(tables)

        # Generate markdown report
        markdown_report = generate_markdown_report(tables)

        # Save to file
        date_str = datetime.now().strftime('%Y%m%d')
        output_file = f"docs/aurora_current_state_{date_str}.md"

        with open(output_file, 'w') as f:
            f.write(markdown_report)

        print(f"\n\n✅ Schema report saved to: {output_file}")
        print(f"📝 Found {len(tables)} tables with {sum(len(cols) for cols in tables.values())} total columns")

    except Exception as e:
        print(f"\n❌ Failed to query Aurora schema: {e}")
        import traceback
        print(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    main()
