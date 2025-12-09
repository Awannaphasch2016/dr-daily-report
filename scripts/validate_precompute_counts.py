#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Validate Precomputed Data Counts"""

import json
import sys
import boto3

def validate_counts_via_lambda():
    """Validate counts by querying multiple tickers."""
    lambda_client = boto3.client('lambda', region_name='ap-southeast-1')
    
    sample_tickers = [
        'C6L.SI', 'S63.SI', 'V03.SI', 'GSD.SI', 'QK9.SI',
        'Y92.SI', 'U11.SI', 'S68.SI', 'U96.SI', 'N6M.SI',
        'JPM', 'PFE', 'DIS', 'COST', 'QQQM', 'GLD', 'ABBV',
        'DELL', 'ORCL', 'SPLG', 'UNH'
    ]
    
    print("🔍 Validating data counts for sample tickers...")
    print("=" * 80)
    
    success_count = 0
    missing_count = 0
    
    for symbol in sample_tickers:
        payload = json.dumps({
            'action': 'query_precomputed',
            'symbol': symbol
        })
        
        try:
            response = lambda_client.invoke(
                FunctionName='dr-daily-report-ticker-scheduler-dev',
                InvocationType='RequestResponse',
                Payload=payload.encode('utf-8')
            )
            
            result = json.loads(response['Payload'].read())
            
            if result.get('statusCode') == 200:
                data = result.get('body', {}).get('data', {})
                has_indicators = data.get('daily_indicators') is not None
                has_percentiles = data.get('indicator_percentiles') is not None
                has_features = data.get('comparative_features') is not None
                
                if has_indicators and has_percentiles and has_features:
                    success_count += 1
                    print(f"  ✅ {symbol}: All tables populated")
                else:
                    missing_count += 1
                    missing = []
                    if not has_indicators:
                        missing.append('indicators')
                    if not has_percentiles:
                        missing.append('percentiles')
                    if not has_features:
                        missing.append('features')
                    print(f"  ⚠️  {symbol}: Missing {', '.join(missing)}")
            else:
                missing_count += 1
                error = result.get('body', {}).get('error', 'Unknown error')
                print(f"  ❌ {symbol}: {error}")
        except Exception as e:
            missing_count += 1
            print(f"  ❌ {symbol}: Exception - {e}")
    
    print()
    print("=" * 80)
    print(f"Validation Results:")
    print(f"  ✅ Successfully populated: {success_count}/{len(sample_tickers)}")
    print(f"  ⚠️  Missing data: {missing_count}/{len(sample_tickers)}")
    
    if success_count == len(sample_tickers):
        print()
        print("✅ All sample tickers have complete data!")
        return 0
    else:
        print()
        print(f"⚠️  {missing_count} tickers have missing data")
        return 1

if __name__ == '__main__':
    sys.exit(validate_counts_via_lambda())
