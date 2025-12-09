#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Format and display precomputed values validation output.

Usage:
    # After deploying updated Lambda code, invoke:
    aws lambda invoke \
      --function-name dr-daily-report-ticker-scheduler-dev \
      --payload '{"action":"query_precomputed","symbol":"DBS19"}' \
      /tmp/response.json

    # Then format the output:
    python scripts/validate_precomputed_output.py /tmp/response.json
"""

import json
import sys
from datetime import date, datetime
from decimal import Decimal


def format_value(value, max_len=50):
    """Format value for display."""
    if value is None:
        return 'NULL'
    elif isinstance(value, (date, datetime)):
        return str(value)
    elif isinstance(value, Decimal):
        return f"{float(value):.6f}"
    elif isinstance(value, float):
        return f"{value:.6f}"
    elif isinstance(value, (dict, list)):
        json_str = json.dumps(value, indent=2, default=str)
        if len(json_str) > max_len:
            return json_str[:max_len] + "..."
        return json_str
    else:
        str_val = str(value)
        if len(str_val) > max_len:
            return str_val[:max_len] + "..."
        return str_val


def print_validation_table(table_name, data, validation, schema):
    """Print formatted validation table."""
    print(f"\n{'='*100}")
    print(f"Table: {table_name}")
    print(f"{'='*100}")
    
    if not data:
        print(f"⚠️  No data found")
        return
    
    print(f"\n📊 Data Validation:")
    print(f"{'Column Name':<35} {'Expected Type':<20} {'Actual Type':<20} {'Value':<40} {'Status'}")
    print("-" * 120)
    
    # Create validation dict for quick lookup
    validation_dict = {v['column']: v for v in validation}
    schema_dict = {s['COLUMN_NAME']: s for s in schema}
    
    # Sort by column name for consistent output
    all_columns = sorted(set(list(data.keys()) + list(schema_dict.keys())))
    
    for col_name in all_columns:
        value = data.get(col_name)
        val_info = validation_dict.get(col_name, {})
        col_info = schema_dict.get(col_name, {})
        
        expected_type = val_info.get('expected_type') or col_info.get('DATA_TYPE', 'UNKNOWN')
        actual_type = val_info.get('actual_type') or (type(value).__name__ if value is not None else 'NULL')
        is_valid = val_info.get('valid', True)
        value_str = format_value(value, max_len=40)
        
        status = "✅" if is_valid else "❌"
        
        print(f"{col_name:<35} {expected_type:<20} {actual_type:<20} {value_str:<40} {status}")
        
        if not is_valid:
            print(f"   ⚠️  Type mismatch: expected {expected_type}, got {actual_type}")


def main():
    """Main function."""
    if len(sys.argv) < 2:
        print("Usage: python validate_precomputed_output.py <response.json>")
        sys.exit(1)
    
    response_file = sys.argv[1]
    
    try:
        with open(response_file, 'r') as f:
            response = json.load(f)
        
        # Handle Lambda response format
        if 'body' in response and isinstance(response['body'], dict):
            # Lambda response format: {"statusCode": 200, "body": {...}}
            if response.get('statusCode') != 200:
                error_msg = response['body'].get('error') or response['body'].get('message') or 'Unknown error'
                print(f"❌ Error: {error_msg}")
                sys.exit(1)
            body = response['body']
        elif 'statusCode' in response:
            # Direct body format
            if response.get('statusCode') != 200:
                error_msg = response.get('error') or response.get('message') or 'Unknown error'
                print(f"❌ Error: {error_msg}")
                sys.exit(1)
            body = response
        else:
            body = response
        
        if body.get('statusCode') and body.get('statusCode') != 200:
            error_msg = body.get('error') or body.get('message') or 'Unknown error'
            print(f"❌ Error: {error_msg}")
            sys.exit(1)
        
        # Extract data
        data_section = body.get('data', {})
        validation_section = body.get('validation', {})
        schemas_section = body.get('schemas', {})
        
        symbol = body.get('symbol', 'UNKNOWN')
        yahoo_symbol = body.get('yahoo_symbol', 'UNKNOWN')
        master_id = body.get('master_id', 'UNKNOWN')
        
        print("🔍 Precomputed Values Validation for DBS19")
        print("=" * 100)
        print(f"Symbol: {symbol} -> {yahoo_symbol} (master_id: {master_id})")
        print(f"Duration: {body.get('duration_seconds', 0):.2f}s")
        
        # Display each table
        if 'daily_indicators' in data_section:
            print_validation_table(
                'daily_indicators',
                data_section['daily_indicators'],
                validation_section.get('daily_indicators', []),
                schemas_section.get('daily_indicators', [])
            )
        
        if 'indicator_percentiles' in data_section:
            print_validation_table(
                'indicator_percentiles',
                data_section['indicator_percentiles'],
                validation_section.get('indicator_percentiles', []),
                schemas_section.get('indicator_percentiles', [])
            )
        
        if 'comparative_features' in data_section:
            print_validation_table(
                'comparative_features',
                data_section['comparative_features'],
                validation_section.get('comparative_features', []),
                schemas_section.get('comparative_features', [])
            )
        
        # Summary
        print(f"\n{'='*100}")
        print("✅ Validation Complete")
        
        # Count validation issues
        total_issues = 0
        for table_name in ['daily_indicators', 'indicator_percentiles', 'comparative_features']:
            validations = validation_section.get(table_name, [])
            issues = [v for v in validations if not v.get('valid', True)]
            total_issues += len(issues)
            if issues:
                print(f"⚠️  {table_name}: {len(issues)} type validation issues")
        
        if total_issues == 0:
            print("✅ All data types are valid!")
        else:
            print(f"⚠️  Total validation issues: {total_issues}")
        
        return 0
        
    except FileNotFoundError:
        print(f"❌ File not found: {response_file}")
        return 1
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON: {e}")
        return 1
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
