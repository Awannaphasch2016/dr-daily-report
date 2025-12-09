#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Query Precomputed Values via Lambda

Creates a temporary Lambda function to query Aurora and return precomputed values.
"""

import json
import sys
import boto3
import time

def create_query_lambda():
    """Create a Lambda function to query Aurora."""
    lambda_code = '''
import json
import os
from src.data.aurora.client import get_aurora_client
from src.data.aurora.ticker_resolver import get_ticker_resolver

def lambda_handler(event, context):
    symbol = event.get('symbol', 'DBS19')
    
    try:
        client = get_aurora_client()
        resolver = get_ticker_resolver()
        ticker_info = resolver.resolve(symbol)
        
        if not ticker_info:
            return {
                'statusCode': 404,
                'body': {'error': f'Ticker {symbol} not found'}
            }
        
        yahoo_symbol = ticker_info.yahoo_symbol or symbol
        master_id = ticker_info.ticker_id
        
        results = {}
        
        # Query daily_indicators
        indicators_query = """
            SELECT * FROM daily_indicators
            WHERE symbol = %s OR ticker_id = %s OR ticker_master_id = %s
            ORDER BY indicator_date DESC
            LIMIT 1
        """
        indicators = client.fetch_one(indicators_query, (yahoo_symbol, master_id, master_id))
        results['daily_indicators'] = indicators
        
        # Query indicator_percentiles
        percentiles_query = """
            SELECT * FROM indicator_percentiles
            WHERE symbol = %s OR ticker_id = %s OR ticker_master_id = %s
            ORDER BY percentile_date DESC
            LIMIT 1
        """
        percentiles = client.fetch_one(percentiles_query, (yahoo_symbol, master_id, master_id))
        results['indicator_percentiles'] = percentiles
        
        # Query comparative_features
        features_query = """
            SELECT * FROM comparative_features
            WHERE symbol = %s OR ticker_id = %s OR ticker_master_id = %s
            ORDER BY feature_date DESC
            LIMIT 1
        """
        features = client.fetch_one(features_query, (yahoo_symbol, master_id, master_id))
        results['comparative_features'] = features
        
        # Get column schemas
        schema_query = """
            SELECT 
                TABLE_NAME,
                COLUMN_NAME,
                DATA_TYPE,
                IS_NULLABLE,
                COLUMN_TYPE
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE()
            AND TABLE_NAME IN ('daily_indicators', 'indicator_percentiles', 'comparative_features')
            ORDER BY TABLE_NAME, ORDINAL_POSITION
        """
        schemas = client.fetch_all(schema_query)
        
        return {
            'statusCode': 200,
            'body': {
                'symbol': symbol,
                'yahoo_symbol': yahoo_symbol,
                'master_id': master_id,
                'data': results,
                'schemas': schemas
            }
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'body': {'error': str(e)}
        }
'''
    
    return lambda_code


def invoke_via_existing_lambda():
    """Use existing scheduler Lambda to query data."""
    lambda_client = boto3.client('lambda', region_name='ap-southeast-1')
    
    # We can't easily add a query function to existing Lambda
    # Instead, let's use a simpler approach: query via AWS CLI using RDS Data API
    # Or create a one-time script that runs in Lambda environment
    
    print("Using AWS RDS Data API or direct MySQL connection from within AWS...")
    print("Alternative: Run this script from an EC2 instance or Lambda with VPC access")
    
    return None


def main():
    """Main function."""
    print("Querying precomputed values for DBS19...")
    print("Note: Aurora is in VPC, so we need to query from within AWS")
    print("\nOptions:")
    print("1. Run from EC2 instance with VPC access")
    print("2. Create a Lambda function with VPC configuration")
    print("3. Use AWS RDS Data API (if enabled)")
    print("\nFor now, let's try using AWS Systems Manager to run the query...")
    
    # Try using AWS CLI to execute a query via RDS Data API
    # First check if RDS Data API is available
    rds_client = boto3.client('rds', region_name='ap-southeast-1')
    
    # Get cluster identifier from environment or parameter
    # For now, let's provide instructions
    print("\n" + "="*80)
    print("To query Aurora from local machine:")
    print("="*80)
    print("1. Use AWS Systems Manager Session Manager to connect to an EC2 instance")
    print("2. Or use AWS RDS Proxy (if configured)")
    print("3. Or run the validation script from within a Lambda function")
    print("\nAlternatively, we can create a simple query script that you can")
    print("run from an EC2 instance or Lambda with VPC access.")
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
