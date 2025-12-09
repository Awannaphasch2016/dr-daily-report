#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Get Precomputed Values for DBS19

This script can be run in two ways:
1. Locally (if Aurora is accessible): python scripts/get_precomputed_dbs19.py
2. Via Lambda: Package and invoke as Lambda function
"""

import json
import os
import sys
from datetime import date, datetime
from decimal import Decimal

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

try:
    from src.data.aurora.precompute_service import PrecomputeService
    from src.data.aurora.client import get_aurora_client
    from src.data.aurora.ticker_resolver import get_ticker_resolver
except ImportError as e:
    print(f"Import error: {e}")
    print("Make sure you're running from the project root with proper PYTHONPATH")
    sys.exit(1)


def format_value(value):
    """Format value for display."""
    if value is None:
        return 'NULL'
    elif isinstance(value, Decimal):
        return f"{float(value):.6f}"
    elif isinstance(value, (date, datetime)):
        return str(value)
    elif isinstance(value, float):
        return f"{value:.6f}"
    elif isinstance(value, (dict, list)):
        return json.dumps(value, indent=2, default=str)
    else:
        return str(value)


def get_table_schema(client, table_name: str):
    """Get table schema."""
    query = """
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
    return client.fetch_all(query, (table_name,))


def validate_and_display_table(table_name: str, data: dict, schema: list):
    """Validate and display table data."""
    print(f"\n{'='*80}")
    print(f"Table: {table_name}")
    print(f"{'='*80}")
    
    if not data:
        print(f"⚠️  No data found")
        return
    
    print(f"\n📊 Data with Type Validation:")
    print(f"{'Column Name':<35} {'Expected Type':<20} {'Actual Type':<20} {'Value':<30} {'Status'}")
    print("-" * 120)
    
    schema_dict = {col['COLUMN_NAME']: col for col in schema}
    
    for key, value in data.items():
        if key in schema_dict:
            col_info = schema_dict[key]
            expected_type = col_info['DATA_TYPE']
            actual_type = type(value).__name__
            
            # Type validation
            is_valid = True
            if value is not None:
                if expected_type in ['DECIMAL', 'FLOAT', 'DOUBLE']:
                    is_valid = isinstance(value, (int, float, Decimal))
                elif expected_type in ['INT', 'BIGINT']:
                    is_valid = isinstance(value, (int,))
                elif expected_type in ['VARCHAR', 'TEXT', 'CHAR']:
                    is_valid = isinstance(value, str)
                elif expected_type == 'DATE':
                    is_valid = isinstance(value, (date, datetime, str))
                elif expected_type in ['DATETIME', 'TIMESTAMP']:
                    is_valid = isinstance(value, (datetime, str))
                elif expected_type == 'JSON':
                    is_valid = isinstance(value, (dict, list, str))
            
            status = "✅" if is_valid else "❌"
            value_str = format_value(value)
            if len(value_str) > 30:
                value_str = value_str[:27] + "..."
            
            print(f"{key:<35} {expected_type:<20} {actual_type:<20} {value_str:<30} {status}")
            
            if not is_valid:
                print(f"   ⚠️  Type mismatch: expected {expected_type}, got {actual_type}")


def lambda_handler(event=None, context=None):
    """Lambda handler function."""
    symbol = event.get('symbol', 'DBS19') if event else 'DBS19'
    
    try:
        client = get_aurora_client()
        service = PrecomputeService()
        resolver = get_ticker_resolver()
        
        # Resolve symbol
        ticker_info = resolver.resolve(symbol)
        if not ticker_info:
            return {
                'statusCode': 404,
                'body': {'error': f'Ticker {symbol} not found'}
            }
        
        yahoo_symbol = ticker_info.yahoo_symbol or symbol
        print(f"Symbol: {symbol} -> {yahoo_symbol} (master_id: {ticker_info.ticker_id})")
        
        # Get precomputed data using service methods
        indicators = service.get_latest_indicators(symbol)
        percentiles = service.get_latest_percentiles(symbol)
        
        # Get comparative features (need to query directly)
        master_id = ticker_info.ticker_id
        features_query = """
            SELECT * FROM comparative_features
            WHERE symbol = %s OR ticker_id = %s OR ticker_master_id = %s
            ORDER BY feature_date DESC
            LIMIT 1
        """
        features = client.fetch_one(features_query, (yahoo_symbol, master_id, master_id))
        
        # Get schemas
        indicators_schema = get_table_schema(client, 'daily_indicators')
        percentiles_schema = get_table_schema(client, 'indicator_percentiles')
        features_schema = get_table_schema(client, 'comparative_features')
        
        # Display results
        if indicators:
            validate_and_display_table('daily_indicators', indicators, indicators_schema)
        else:
            print(f"\n⚠️  No indicators found for {symbol}")
        
        if percentiles:
            validate_and_display_table('indicator_percentiles', percentiles, percentiles_schema)
        else:
            print(f"\n⚠️  No percentiles found for {symbol}")
        
        if features:
            validate_and_display_table('comparative_features', features, features_schema)
        else:
            print(f"\n⚠️  No comparative features found for {symbol}")
        
        return {
            'statusCode': 200,
            'body': {
                'symbol': symbol,
                'yahoo_symbol': yahoo_symbol,
                'indicators': indicators,
                'percentiles': percentiles,
                'features': features
            }
        }
        
    except Exception as e:
        import traceback
        error_msg = f"Error: {e}\n{traceback.format_exc()}"
        print(f"❌ {error_msg}")
        return {
            'statusCode': 500,
            'body': {'error': str(e)}
        }


def main():
    """Main function for local execution."""
    print("🔍 Getting Precomputed Values for DBS19")
    print("=" * 80)
    
    result = lambda_handler({'symbol': 'DBS19'})
    
    if result['statusCode'] == 200:
        print(f"\n{'='*80}")
        print("✅ Query completed successfully")
        print(f"\nFull JSON output:")
        print(json.dumps(result['body'], indent=2, default=str))
        return 0
    else:
        print(f"\n❌ Query failed: {result['body']}")
        return 1


if __name__ == '__main__':
    sys.exit(main())
