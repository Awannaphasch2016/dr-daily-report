#!/usr/bin/env python3
"""
Script to output schema of Aurora tables.

Usage:
    python scripts/check_table_schema.py precomputed_reports
    python scripts/check_table_schema.py ticker_info

Output shows column names, types, nullability, keys, defaults, and extra info.

Note: Requires SSM port forwarding to be active on port 3307.
If not already running, start it with:
    aws ssm start-session --target i-0dab21bdf83ce9aaf \
      --document-name AWS-StartPortForwardingSessionToRemoteHost \
      --parameters '{"host":["dr-daily-report-aurora-dev.cluster-c9a0288e4hqm.ap-southeast-1.rds.amazonaws.com"],"portNumber":["3306"],"localPortNumber":["3307"]}'
"""

import sys
import pymysql
from pymysql.cursors import DictCursor


def print_schema(table_name: str):
    """Print schema of specified table in readable format."""

    try:
        # Connect directly via SSM tunnel (same pattern as aurora-vd.sh)
        conn = pymysql.connect(
            host='127.0.0.1',
            port=3307,
            user='admin',
            password='AuroraDevDb2025SecureX1',
            database='ticker_data',
            cursorclass=DictCursor
        )
        cursor = conn.cursor()

        cursor.execute(f"DESCRIBE {table_name}")
        columns = cursor.fetchall()

        if not columns:
            print(f"❌ Table '{table_name}' not found or has no columns")
            cursor.close()
            conn.close()
            return

        # Print header
        print(f"\n{'=' * 100}")
        print(f"Schema for table: {table_name}")
        print(f"{'=' * 100}\n")

        # Print column headers
        header_format = "{:<25} {:<15} {:<8} {:<8} {:<20} {:<20}"
        print(header_format.format("Field", "Type", "Null", "Key", "Default", "Extra"))
        print("-" * 100)

        # Print each column
        for col in columns:
            field = col['Field']
            col_type = col['Type']
            null = col['Null']
            key = col['Key']
            default = col['Default'] if col['Default'] is not None else 'NULL'
            extra = col['Extra']

            # Highlight JSON columns
            type_display = f"**{col_type}**" if 'json' in col_type.lower() else col_type

            print(header_format.format(
                field,
                type_display,
                null,
                key,
                str(default)[:20],
                extra
            ))

        print("\n" + "=" * 100)
        print(f"Total columns: {len(columns)}\n")

        # Check for JSON columns specifically
        json_columns = [col['Field'] for col in columns if 'json' in col['Type'].lower()]
        if json_columns:
            print(f"✅ JSON columns found: {', '.join(json_columns)}")
        else:
            print("⚠️  No JSON columns found")

        cursor.close()
        conn.close()

    except Exception as e:
        print(f"❌ Error querying table schema: {e}")
        sys.exit(1)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/check_table_schema.py <table_name>")
        print("\nExample:")
        print("  python scripts/check_table_schema.py precomputed_reports")
        print("  python scripts/check_table_schema.py ticker_info")
        sys.exit(1)

    table_name = sys.argv[1]
    print_schema(table_name)
