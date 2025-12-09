#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Validate Precomputed Data for All Tickers

Queries Aurora to verify that precomputed data is populated correctly
for all tickers, checking for data quality issues.
"""

import json
import math
import sys
import boto3
from typing import Dict, List, Tuple

# Sample tickers from different markets to validate
SAMPLE_TICKERS = [
    'DBS19',      # Singapore (D05.SI)
    'NVDA19',     # US (NVDA)
    '0700.HK',    # Hong Kong
    '7011.T',     # Japan
    'VNM.VN',     # Vietnam
    '0050.TW',    # Taiwan
]


def invoke_lambda_query(symbol: str) -> Dict:
    """Invoke Lambda to query precomputed data for a symbol."""
    lambda_client = boto3.client('lambda', region_name='ap-southeast-1')
    
    payload = json.dumps({
        'action': 'query_precomputed',
        'symbol': symbol
    })
    
    response = lambda_client.invoke(
        FunctionName='dr-daily-report-ticker-scheduler-dev',
        InvocationType='RequestResponse',
        Payload=payload.encode('utf-8')
    )
    
    result = json.loads(response['Payload'].read())
    
    if result.get('statusCode') != 200:
        return {'error': result.get('body', {}).get('error', 'Unknown error')}
    
    return result.get('body', {})


def check_data_quality(data: Dict, symbol: str) -> List[Tuple[str, str]]:
    """Check data quality issues."""
    issues = []
    
    def check_values(obj, path=''):
        if isinstance(obj, dict):
            for key, value in obj.items():
                current_path = f'{path}.{key}' if path else key
                check_values(value, current_path)
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                check_values(item, f'{path}[{i}]')
        elif isinstance(obj, float):
            if math.isinf(obj):
                issues.append((path, f'INFINITY: {obj}'))
            elif math.isnan(obj):
                issues.append((path, f'NaN'))
        elif isinstance(obj, str) and obj == '':
            issues.append((path, 'EMPTY_STRING'))
    
    check_values(data)
    return issues


def validate_ticker(symbol: str) -> Dict:
    """Validate precomputed data for a single ticker."""
    result = {
        'symbol': symbol,
        'status': 'unknown',
        'tables': {},
        'issues': []
    }
    
    try:
        response = invoke_lambda_query(symbol)
        
        if 'error' in response:
            result['status'] = 'error'
            result['error'] = response['error']
            return result
        
        data = response.get('data', {})
        
        # Check each table
        for table_name in ['daily_indicators', 'indicator_percentiles', 'comparative_features']:
            table_data = data.get(table_name)
            
            if table_data is None:
                result['tables'][table_name] = {'exists': False, 'field_count': 0}
            elif isinstance(table_data, dict):
                field_count = len([v for v in table_data.values() if v is not None])
                result['tables'][table_name] = {
                    'exists': True,
                    'field_count': field_count,
                    'total_fields': len(table_data)
                }
                
                # Check for data quality issues
                issues = check_data_quality(table_data, symbol)
                if issues:
                    result['issues'].extend([(table_name, issue) for issue in issues])
            else:
                result['tables'][table_name] = {'exists': False, 'error': 'Unexpected type'}
        
        # Determine overall status
        all_tables_exist = all(
            result['tables'].get(t, {}).get('exists', False)
            for t in ['daily_indicators', 'indicator_percentiles', 'comparative_features']
        )
        
        if result['issues']:
            result['status'] = 'issues_found'
        elif all_tables_exist:
            result['status'] = 'valid'
        else:
            result['status'] = 'missing_data'
        
        result['yahoo_symbol'] = response.get('yahoo_symbol', 'N/A')
        result['master_id'] = response.get('master_id', 'N/A')
        
    except Exception as e:
        result['status'] = 'exception'
        result['error'] = str(e)
    
    return result


def main():
    """Main validation function."""
    print("🔍 Validating Precomputed Data for All Tickers")
    print("=" * 80)
    print(f"Sample tickers: {', '.join(SAMPLE_TICKERS)}")
    print()
    
    results = []
    for symbol in SAMPLE_TICKERS:
        print(f"Validating {symbol}...", end=' ', flush=True)
        result = validate_ticker(symbol)
        results.append(result)
        
        if result['status'] == 'valid':
            print("✅")
        elif result['status'] == 'error':
            print(f"❌ Error: {result.get('error', 'Unknown')}")
        elif result['status'] == 'issues_found':
            print(f"⚠️  Issues found: {len(result['issues'])}")
        elif result['status'] == 'missing_data':
            print("⚠️  Missing data")
        else:
            print(f"❌ {result['status']}")
    
    print()
    print("=" * 80)
    print("Validation Summary")
    print("=" * 80)
    
    # Summary statistics
    valid_count = sum(1 for r in results if r['status'] == 'valid')
    error_count = sum(1 for r in results if r['status'] == 'error')
    issues_count = sum(1 for r in results if r['status'] == 'issues_found')
    missing_count = sum(1 for r in results if r['status'] == 'missing_data')
    
    print(f"\nResults:")
    print(f"  ✅ Valid: {valid_count}/{len(results)}")
    print(f"  ⚠️  Issues: {issues_count}/{len(results)}")
    print(f"  ⚠️  Missing data: {missing_count}/{len(results)}")
    print(f"  ❌ Errors: {error_count}/{len(results)}")
    
    # Detailed results
    print(f"\nDetailed Results:")
    print("-" * 80)
    for result in results:
        print(f"\n{result['symbol']} ({result.get('yahoo_symbol', 'N/A')}):")
        print(f"  Status: {result['status']}")
        
        if result['status'] == 'error':
            print(f"  Error: {result.get('error', 'Unknown')}")
            continue
        
        for table_name, table_info in result['tables'].items():
            if table_info.get('exists'):
                print(f"  ✅ {table_name}: {table_info['field_count']}/{table_info['total_fields']} fields populated")
            else:
                print(f"  ❌ {table_name}: Missing")
        
        if result['issues']:
            print(f"  ⚠️  Issues:")
            for table_name, issue in result['issues']:
                print(f"    - {table_name}: {issue}")
    
    # Check for any critical issues
    all_valid = all(r['status'] == 'valid' for r in results)
    
    print()
    print("=" * 80)
    if all_valid:
        print("✅ All sample tickers validated successfully!")
        return 0
    else:
        print("⚠️  Some issues found. Review details above.")
        return 1


if __name__ == '__main__':
    sys.exit(main())
