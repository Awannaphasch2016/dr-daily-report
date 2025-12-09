#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Validate Precomputed Values for DBS19

Queries Aurora database to show precomputed indicators and percentiles
for DBS19, validating data types and values.
"""

import json
import os
import sys
from datetime import date

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.data.aurora.client import get_aurora_client
from src.data.aurora.ticker_resolver import get_ticker_resolver


def get_column_info(client, table_name: str, symbol: str) -> dict:
    """Get column information and sample data for a table."""
    # First, get the ticker_id or master_id
    resolver = get_ticker_resolver()
    ticker_info = resolver.resolve(symbol)
    
    if not ticker_info:
        return {'error': f'Ticker {symbol} not found'}
    
    yahoo_symbol = ticker_info.yahoo_symbol or symbol
    master_id = ticker_info.ticker_id
    
    # Get table schema
    schema_query = f"""
        SELECT 
            COLUMN_NAME,
            DATA_TYPE,
            IS_NULLABLE,
            COLUMN_TYPE,
            COLUMN_DEFAULT
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
        AND TABLE_NAME = %s
        ORDER BY ORDINAL_POSITION
    """
    
    columns = client.fetch_all(schema_query, (table_name,))
    
    # Get latest data for this ticker
    if table_name == 'daily_indicators':
        data_query = """
            SELECT * FROM daily_indicators
            WHERE symbol = %s OR ticker_id = %s OR ticker_master_id = %s
            ORDER BY indicator_date DESC
            LIMIT 1
        """
        data = client.fetch_one(data_query, (yahoo_symbol, master_id, master_id))
    elif table_name == 'indicator_percentiles':
        data_query = """
            SELECT * FROM indicator_percentiles
            WHERE symbol = %s OR ticker_id = %s OR ticker_master_id = %s
            ORDER BY percentile_date DESC
            LIMIT 1
        """
        data = client.fetch_one(data_query, (yahoo_symbol, master_id, master_id))
    elif table_name == 'comparative_features':
        data_query = """
            SELECT * FROM comparative_features
            WHERE symbol = %s OR ticker_id = %s OR ticker_master_id = %s
            ORDER BY feature_date DESC
            LIMIT 1
        """
        data = client.fetch_one(data_query, (yahoo_symbol, master_id, master_id))
    else:
        data = None
    
    return {
        'columns': columns,
        'data': data,
        'yahoo_symbol': yahoo_symbol,
        'master_id': master_id
    }


def validate_value_type(value, expected_type: str) -> dict:
    """Validate that a value matches expected type."""
    if value is None:
        return {'valid': True, 'type': 'NULL', 'note': 'NULL values allowed'}
    
    actual_type = type(value).__name__
    
    # Map MySQL types to Python types
    type_map = {
        'DECIMAL': ['float', 'Decimal'],
        'FLOAT': ['float'],
        'DOUBLE': ['float'],
        'INT': ['int'],
        'BIGINT': ['int'],
        'DATE': ['str', 'date'],
        'DATETIME': ['str', 'datetime'],
        'TIMESTAMP': ['str', 'datetime'],
        'VARCHAR': ['str'],
        'TEXT': ['str'],
        'JSON': ['dict', 'list'],
    }
    
    valid_types = type_map.get(expected_type, [])
    
    return {
        'valid': actual_type in valid_types or expected_type in ['DECIMAL', 'FLOAT', 'DOUBLE'] and isinstance(value, (int, float)),
        'expected': expected_type,
        'actual': actual_type,
        'value': value
    }


def print_table_info(table_name: str, info: dict):
    """Print formatted table information."""
    print(f"\n{'='*80}")
    print(f"Table: {table_name}")
    print(f"{'='*80}")
    
    if 'error' in info:
        print(f"❌ Error: {info['error']}")
        return
    
    print(f"Symbol: DBS19 -> {info['yahoo_symbol']} (master_id: {info['master_id']})")
    
    if not info['data']:
        print(f"⚠️  No data found for {info['yahoo_symbol']}")
        return
    
    print(f"\n📊 Column Schema:")
    print(f"{'Column Name':<30} {'Data Type':<20} {'Nullable':<10} {'Sample Value':<20}")
    print("-" * 80)
    
    for col in info['columns']:
        col_name = col['COLUMN_NAME']
        data_type = col['DATA_TYPE']
        nullable = col['IS_NULLABLE']
        value = info['data'].get(col_name)
        
        # Format value for display
        if value is None:
            value_str = 'NULL'
        elif isinstance(value, (dict, list)):
            value_str = json.dumps(value)[:50] + '...' if len(json.dumps(value)) > 50 else json.dumps(value)
        elif isinstance(value, (date,)):
            value_str = str(value)
        elif isinstance(value, float):
            value_str = f"{value:.6f}"
        else:
            value_str = str(value)[:50]
        
        print(f"{col_name:<30} {data_type:<20} {nullable:<10} {value_str:<20}")
    
    print(f"\n✅ Data Validation:")
    print(f"{'Column':<30} {'Expected Type':<20} {'Actual Type':<20} {'Status':<10}")
    print("-" * 80)
    
    for col in info['columns']:
        col_name = col['COLUMN_NAME']
        data_type = col['DATA_TYPE']
        value = info['data'].get(col_name)
        
        validation = validate_value_type(value, data_type)
        status = "✅" if validation['valid'] else "❌"
        
        print(f"{col_name:<30} {data_type:<20} {validation['actual']:<20} {status:<10}")
        
        if not validation['valid']:
            print(f"   ⚠️  Type mismatch: expected {data_type}, got {validation['actual']}")


def main():
    """Main function."""
    print("🔍 Validating Precomputed Values for DBS19")
    print("=" * 80)
    
    try:
        client = get_aurora_client()
        
        # Test connection
        health = client.health_check()
        if health['status'] != 'healthy':
            print(f"❌ Database connection failed: {health.get('error')}")
            return 1
        
        print(f"✅ Connected to Aurora: {health['host']}/{health['database']}")
        
        # Get info for each table
        tables = ['daily_indicators', 'indicator_percentiles', 'comparative_features']
        
        for table in tables:
            try:
                info = get_column_info(client, table, 'DBS19')
                print_table_info(table, info)
            except Exception as e:
                print(f"\n❌ Error querying {table}: {e}")
                import traceback
                traceback.print_exc()
        
        print(f"\n{'='*80}")
        print("✅ Validation complete")
        
        return 0
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
