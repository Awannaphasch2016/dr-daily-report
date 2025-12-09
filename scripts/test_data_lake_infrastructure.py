#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Comprehensive Infrastructure Test Script

Tests both raw data and precompute data storage in S3 Data Lake infrastructure.

Tests:
1. Raw Data Storage: Fetch ticker → verify stored in S3 Data Lake
2. Precompute Storage: Invoke Lambda precompute → verify processed data stored in S3 Data Lake

Features:
- Auto-maps display symbols (e.g., 'DBS19') to Yahoo Finance tickers (e.g., 'D05.SI')
- Comprehensive logging and error handling
- Exit codes for CI/CD integration

Usage:
    export DATA_LAKE_BUCKET=dr-daily-report-data-lake-dev
    export AWS_REGION=ap-southeast-1
    python scripts/test_data_lake_infrastructure.py --ticker DBS19
"""

import os
import sys
import json
import time
import logging
import argparse
from datetime import date, datetime
from typing import Dict, Any, Optional
import boto3
from botocore.exceptions import ClientError

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.scheduler.ticker_fetcher import TickerFetcher
from src.data.aurora.ticker_resolver import TickerResolver, get_ticker_resolver
from src.data.data_lake import DataLakeStorage

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class InfrastructureTester:
    """Comprehensive infrastructure tester for data lake."""

    def __init__(
        self,
        bucket_name: str,
        lambda_function_name: Optional[str] = None,
        region: str = 'ap-southeast-1',
        qualifier: str = 'live'
    ):
        """
        Initialize infrastructure tester.

        Args:
            bucket_name: S3 Data Lake bucket name
            lambda_function_name: Lambda function name (auto-detected if None)
            region: AWS region
            qualifier: Lambda qualifier ('live' alias or '$LATEST')
        """
        self.bucket_name = bucket_name
        self.region = region
        self.qualifier = qualifier

        # Initialize AWS clients
        self.s3_client = boto3.client('s3', region_name=region)
        self.lambda_client = boto3.client('lambda', region_name=region)

        # Initialize services
        self.ticker_fetcher = TickerFetcher(data_lake_bucket=bucket_name)
        self.ticker_resolver = get_ticker_resolver()
        self.data_lake = DataLakeStorage(bucket_name=bucket_name)

        # Lambda function name
        if lambda_function_name:
            self.lambda_function_name = lambda_function_name
        else:
            # Auto-detect from environment
            env = os.environ.get('ENVIRONMENT', 'dev')
            self.lambda_function_name = f"dr-daily-report-ticker-scheduler-{env}"
            logger.info(f"Auto-detected Lambda function: {self.lambda_function_name}")

        logger.info(f"InfrastructureTester initialized:")
        logger.info(f"  Bucket: {bucket_name}")
        logger.info(f"  Lambda: {self.lambda_function_name}")
        logger.info(f"  Region: {region}")

    def resolve_ticker(self, symbol: str) -> Dict[str, str]:
        """
        Resolve display symbol to Yahoo Finance ticker.

        Args:
            symbol: Display symbol (e.g., 'DBS19') or Yahoo ticker (e.g., 'D05.SI')

        Returns:
            Dict with 'display_symbol', 'yahoo_ticker', 'company_name'
        """
        info = self.ticker_resolver.resolve(symbol)
        if not info:
            logger.warning(f"⚠️ Could not resolve symbol: {symbol}")
            # Fallback: assume it's already a Yahoo ticker
            return {
                'display_symbol': symbol,
                'yahoo_ticker': symbol,
                'company_name': symbol
            }

        return {
            'display_symbol': info.dr_symbol or symbol,
            'yahoo_ticker': info.yahoo_symbol or symbol,
            'company_name': info.company_name or symbol
        }

    def test_raw_data_storage(self, ticker: str) -> Dict[str, Any]:
        """
        Test raw data storage: Fetch ticker → verify stored in S3 Data Lake.

        Args:
            ticker: Yahoo Finance ticker symbol (e.g., 'D05.SI')

        Returns:
            Dict with test results
        """
        logger.info("=" * 80)
        logger.info("Test 1: Raw Data Storage")
        logger.info("=" * 80)
        logger.info(f"Fetching ticker: {ticker}")

        results = {
            'test': 'Raw Data Storage',
            'ticker': ticker,
            'passed': False,
            'steps': {}
        }

        try:
            # Step 1: Fetch ticker
            logger.info(f"\n📥 Step 1: Fetching ticker {ticker}...")
            fetch_result = self.ticker_fetcher.fetch_ticker(ticker)

            if fetch_result.get('status') != 'success':
                error_msg = fetch_result.get('error', 'Unknown error')
                logger.error(f"❌ Fetch failed: {error_msg}")
                results['steps']['fetch'] = {
                    'passed': False,
                    'error': error_msg
                }
                return results

            logger.info(f"✅ Fetch succeeded")
            logger.info(f"   Company: {fetch_result.get('company_name', 'N/A')}")
            logger.info(f"   Date: {fetch_result.get('date', 'N/A')}")

            results['steps']['fetch'] = {
                'passed': True,
                'company_name': fetch_result.get('company_name'),
                'date': fetch_result.get('date')
            }

            # Step 2: Verify S3 storage
            logger.info(f"\n🔍 Step 2: Verifying S3 Data Lake storage...")
            today = date.today()
            date_str = today.isoformat()
            prefix = f"raw/yfinance/{ticker}/{date_str}/"

            try:
                response = self.s3_client.list_objects_v2(
                    Bucket=self.bucket_name,
                    Prefix=prefix
                )

                if 'Contents' not in response or len(response['Contents']) == 0:
                    logger.error(f"❌ No raw data files found for {ticker} on {date_str}")
                    results['steps']['s3_verification'] = {
                        'passed': False,
                        'error': f"No files found at prefix: {prefix}"
                    }
                    return results

                # Get latest file
                latest_file = max(
                    response['Contents'],
                    key=lambda obj: obj['LastModified']
                )
                s3_key = latest_file['Key']

                logger.info(f"✅ Found raw data file: {s3_key}")

                # Verify tags
                tag_response = self.s3_client.get_object_tagging(
                    Bucket=self.bucket_name,
                    Key=s3_key
                )
                tags = {tag['Key']: tag['Value'] for tag in tag_response.get('TagSet', [])}

                # Verify metadata
                head_response = self.s3_client.head_object(
                    Bucket=self.bucket_name,
                    Key=s3_key
                )
                metadata = head_response.get('Metadata', {})

                # Verify JSON content
                obj_response = self.s3_client.get_object(
                    Bucket=self.bucket_name,
                    Key=s3_key
                )
                content = obj_response['Body'].read().decode('utf-8')
                data = json.loads(content)

                logger.info(f"✅ S3 verification passed")
                logger.info(f"   Tags: {tags}")
                logger.info(f"   Metadata keys: {list(metadata.keys())}")
                logger.info(f"   Data keys: {list(data.keys())[:5]}...")

                results['steps']['s3_verification'] = {
                    'passed': True,
                    's3_key': s3_key,
                    'tags': tags,
                    'metadata_keys': list(metadata.keys()),
                    'data_keys': list(data.keys())[:10]
                }

                # Overall result
                results['passed'] = True
                logger.info(f"\n✅ Raw Data Storage Test PASSED")

            except ClientError as e:
                logger.error(f"❌ S3 verification failed: {e}")
                results['steps']['s3_verification'] = {
                    'passed': False,
                    'error': str(e)
                }

        except Exception as e:
            logger.error(f"❌ Raw data storage test failed: {e}")
            import traceback
            traceback.print_exc()
            results['steps']['error'] = {
                'passed': False,
                'error': str(e)
            }

        return results

    def invoke_precompute_lambda(self, symbol: str, include_report: bool = False) -> Dict[str, Any]:
        """
        Invoke Lambda precompute function.

        Args:
            symbol: Display symbol (e.g., 'DBS19') - Lambda will resolve internally
            include_report: Whether to generate LLM report (default: False for faster test)

        Returns:
            Dict with invocation results
        """
        logger.info(f"🚀 Invoking Lambda function: {self.lambda_function_name}")
        logger.info(f"   Action: precompute")
        logger.info(f"   Symbol: {symbol}")
        logger.info(f"   Include report: {include_report}")

        payload = {
            'action': 'precompute',
            'symbol': symbol,
            'include_report': include_report
        }

        try:
            response = self.lambda_client.invoke(
                FunctionName=self.lambda_function_name,
                Qualifier=self.qualifier,
                InvocationType='RequestResponse',
                Payload=json.dumps(payload)
            )

            status_code = response['StatusCode']
            payload_bytes = response['Payload'].read()
            payload_str = payload_bytes.decode('utf-8')

            logger.info(f"✅ Lambda invocation completed")
            logger.info(f"   Status code: {status_code}")

            try:
                result = json.loads(payload_str)
                logger.info(f"   Response: {json.dumps(result, indent=2)}")
                return {
                    'success': status_code == 200,
                    'status_code': status_code,
                    'response': result
                }
            except json.JSONDecodeError:
                logger.warning(f"   Response is not JSON: {payload_str[:200]}")
                return {
                    'success': False,
                    'status_code': status_code,
                    'response': {'raw': payload_str}
                }

        except ClientError as e:
            logger.error(f"❌ Lambda invocation failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }
        except Exception as e:
            logger.error(f"❌ Unexpected error: {e}")
            import traceback
            traceback.print_exc()
            return {
                'success': False,
                'error': str(e)
            }

    def verify_processed_data(self, ticker: str, target_date: date) -> Dict[str, Any]:
        """
        Verify processed data (indicators, percentiles) stored in S3 Data Lake.

        Args:
            ticker: Yahoo Finance ticker symbol
            target_date: Date to check

        Returns:
            Dict with verification results
        """
        logger.info(f"🔍 Verifying processed data storage for {ticker}")

        results = {
            'ticker': ticker,
            'date': target_date.isoformat(),
            'indicators': {'found': False, 'details': {}},
            'percentiles': {'found': False, 'details': {}}
        }

        date_str = target_date.isoformat()

        # Check indicators
        indicators_prefix = f"processed/indicators/{ticker}/{date_str}/"
        try:
            indicators_response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=indicators_prefix
            )

            if 'Contents' in indicators_response and len(indicators_response['Contents']) > 0:
                latest_indicator = max(
                    indicators_response['Contents'],
                    key=lambda obj: obj['LastModified']
                )
                indicator_key = latest_indicator['Key']

                # Get tags
                tag_response = self.s3_client.get_object_tagging(
                    Bucket=self.bucket_name,
                    Key=indicator_key
                )
                tags = {tag['Key']: tag['Value'] for tag in tag_response.get('TagSet', [])}

                # Get content
                obj_response = self.s3_client.get_object(
                    Bucket=self.bucket_name,
                    Key=indicator_key
                )
                content = obj_response['Body'].read().decode('utf-8')
                indicators_data = json.loads(content)

                results['indicators'] = {
                    'found': True,
                    's3_key': indicator_key,
                    'tags': tags,
                    'data_keys': list(indicators_data.keys())[:10],
                    'size_bytes': latest_indicator.get('Size', 0)
                }

                logger.info(f"✅ Found indicators: {indicator_key}")
                logger.info(f"   Tags: {tags}")
                logger.info(f"   Data keys: {results['indicators']['data_keys']}")

            else:
                logger.warning(f"⚠️ No indicators found for {ticker} on {date_str}")
                results['indicators'] = {
                    'found': False,
                    'message': f"No indicators found at prefix: {indicators_prefix}"
                }

        except Exception as e:
            logger.error(f"❌ Error checking indicators: {e}")
            results['indicators'] = {
                'found': False,
                'error': str(e)
            }

        # Check percentiles
        percentiles_prefix = f"processed/percentiles/{ticker}/{date_str}/"
        try:
            percentiles_response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=percentiles_prefix
            )

            if 'Contents' in percentiles_response and len(percentiles_response['Contents']) > 0:
                latest_percentile = max(
                    percentiles_response['Contents'],
                    key=lambda obj: obj['LastModified']
                )
                percentile_key = latest_percentile['Key']

                # Get tags
                tag_response = self.s3_client.get_object_tagging(
                    Bucket=self.bucket_name,
                    Key=percentile_key
                )
                tags = {tag['Key']: tag['Value'] for tag in tag_response.get('TagSet', [])}

                # Get content
                obj_response = self.s3_client.get_object(
                    Bucket=self.bucket_name,
                    Key=percentile_key
                )
                content = obj_response['Body'].read().decode('utf-8')
                percentiles_data = json.loads(content)

                results['percentiles'] = {
                    'found': True,
                    's3_key': percentile_key,
                    'tags': tags,
                    'data_keys': list(percentiles_data.keys())[:10],
                    'size_bytes': latest_percentile.get('Size', 0)
                }

                logger.info(f"✅ Found percentiles: {percentile_key}")
                logger.info(f"   Tags: {tags}")
                logger.info(f"   Data keys: {results['percentiles']['data_keys']}")

            else:
                logger.warning(f"⚠️ No percentiles found for {ticker} on {date_str}")
                results['percentiles'] = {
                    'found': False,
                    'message': f"No percentiles found at prefix: {percentiles_prefix}"
                }

        except Exception as e:
            logger.error(f"❌ Error checking percentiles: {e}")
            results['percentiles'] = {
                'found': False,
                'error': str(e)
            }

        return results

    def test_precompute_storage(self, display_symbol: str) -> Dict[str, Any]:
        """
        Test precompute storage: Invoke Lambda → verify processed data in S3.

        Args:
            display_symbol: Display symbol (e.g., 'DBS19')

        Returns:
            Dict with test results
        """
        logger.info("=" * 80)
        logger.info("Test 2: Precompute Storage")
        logger.info("=" * 80)

        # Resolve to Yahoo ticker
        ticker_info = self.resolve_ticker(display_symbol)
        yahoo_ticker = ticker_info['yahoo_ticker']

        logger.info(f"Display symbol: {display_symbol}")
        logger.info(f"Yahoo ticker: {yahoo_ticker}")
        logger.info(f"Company: {ticker_info['company_name']}")

        results = {
            'test': 'Precompute Storage',
            'display_symbol': display_symbol,
            'yahoo_ticker': yahoo_ticker,
            'passed': False,
            'steps': {}
        }

        try:
            # Step 1: Invoke Lambda
            logger.info(f"\n🚀 Step 1: Invoking Lambda precompute service...")
            invocation_result = self.invoke_precompute_lambda(display_symbol, include_report=False)

            if not invocation_result.get('success'):
                error_msg = invocation_result.get('error', 'Unknown error')
                logger.error(f"❌ Lambda invocation failed: {error_msg}")
                results['steps']['lambda_invocation'] = {
                    'passed': False,
                    'error': error_msg
                }
                return results

            logger.info(f"✅ Lambda invocation succeeded")
            results['steps']['lambda_invocation'] = {
                'passed': True,
                'status_code': invocation_result.get('status_code'),
                'response': invocation_result.get('response', {})
            }

            # Wait for S3 writes to complete
            logger.info(f"\n⏳ Waiting 5 seconds for S3 writes to complete...")
            time.sleep(5)

            # Step 2: Verify processed data
            logger.info(f"\n🔍 Step 2: Verifying processed data in S3 Data Lake...")
            today = date.today()
            verification_result = self.verify_processed_data(yahoo_ticker, today)

            indicators_found = verification_result.get('indicators', {}).get('found', False)
            percentiles_found = verification_result.get('percentiles', {}).get('found', False)

            logger.info(f"\n📊 Verification Results:")
            logger.info(f"   Indicators: {'✅ FOUND' if indicators_found else '❌ NOT FOUND'}")
            logger.info(f"   Percentiles: {'✅ FOUND' if percentiles_found else '❌ NOT FOUND'}")

            results['steps']['data_verification'] = verification_result

            # Overall result
            if indicators_found and percentiles_found:
                results['passed'] = True
                logger.info(f"\n✅ Precompute Storage Test PASSED")
            else:
                logger.warning(f"\n⚠️ Precompute Storage Test PARTIAL - some data missing")
                if not indicators_found:
                    logger.warning(f"   Indicators not found")
                if not percentiles_found:
                    logger.warning(f"   Percentiles not found")

        except Exception as e:
            logger.error(f"❌ Precompute storage test failed: {e}")
            import traceback
            traceback.print_exc()
            results['steps']['error'] = {
                'passed': False,
                'error': str(e)
            }

        return results

    def run_all_tests(self, ticker: str) -> Dict[str, Any]:
        """
        Run all infrastructure tests.

        Args:
            ticker: Display symbol (e.g., 'DBS19') or Yahoo ticker

        Returns:
            Dict with all test results
        """
        logger.info("=" * 80)
        logger.info("Comprehensive Infrastructure Test")
        logger.info("=" * 80)
        logger.info(f"Bucket: {self.bucket_name}")
        logger.info(f"Lambda: {self.lambda_function_name}")
        logger.info(f"Ticker: {ticker}")
        logger.info("=" * 80)

        # Resolve ticker
        ticker_info = self.resolve_ticker(ticker)
        yahoo_ticker = ticker_info['yahoo_ticker']
        display_symbol = ticker_info['display_symbol']

        logger.info(f"\n📋 Ticker Resolution:")
        logger.info(f"   Input: {ticker}")
        logger.info(f"   Display Symbol: {display_symbol}")
        logger.info(f"   Yahoo Ticker: {yahoo_ticker}")
        logger.info(f"   Company: {ticker_info['company_name']}")

        results = {
            'ticker': ticker,
            'display_symbol': display_symbol,
            'yahoo_ticker': yahoo_ticker,
            'company_name': ticker_info['company_name'],
            'raw_data_test': {},
            'precompute_test': {},
            'overall_success': False
        }

        # Test 1: Raw Data Storage
        logger.info(f"\n{'='*80}")
        raw_data_results = self.test_raw_data_storage(yahoo_ticker)
        results['raw_data_test'] = raw_data_results

        # Test 2: Precompute Storage
        logger.info(f"\n{'='*80}")
        precompute_results = self.test_precompute_storage(display_symbol)
        results['precompute_test'] = precompute_results

        # Summary
        logger.info(f"\n{'='*80}")
        logger.info("Test Summary")
        logger.info(f"{'='*80}")

        raw_data_passed = raw_data_results.get('passed', False)
        precompute_passed = precompute_results.get('passed', False)

        logger.info(f"Raw Data Storage: {'✅ PASSED' if raw_data_passed else '❌ FAILED'}")
        logger.info(f"Precompute Storage: {'✅ PASSED' if precompute_passed else '❌ FAILED'}")

        results['overall_success'] = raw_data_passed and precompute_passed

        if results['overall_success']:
            logger.info(f"\n✅ All infrastructure tests PASSED!")
            logger.info(f"   ✅ Raw data fetched and stored correctly")
            logger.info(f"   ✅ Lambda precompute executed successfully")
            logger.info(f"   ✅ Indicators computed and stored")
            logger.info(f"   ✅ Percentiles computed and stored")
        else:
            logger.error(f"\n❌ Some infrastructure tests FAILED")
            if not raw_data_passed:
                logger.error(f"   ❌ Raw data storage test failed")
            if not precompute_passed:
                logger.error(f"   ❌ Precompute storage test failed")

        return results


def main():
    """Main test execution."""
    parser = argparse.ArgumentParser(
        description='Comprehensive infrastructure test for data lake'
    )
    parser.add_argument(
        '--ticker',
        default='DBS19',
        help='Ticker symbol to test (default: DBS19)'
    )
    parser.add_argument(
        '--bucket',
        help='S3 Data Lake bucket name (default: from DATA_LAKE_BUCKET env var)'
    )
    parser.add_argument(
        '--function-name',
        help='Lambda function name (default: auto-detect from environment)'
    )
    parser.add_argument(
        '--region',
        default='ap-southeast-1',
        help='AWS region (default: ap-southeast-1)'
    )
    parser.add_argument(
        '--qualifier',
        default='live',
        help='Lambda qualifier (default: live)'
    )

    args = parser.parse_args()

    # Get bucket name
    bucket_name = args.bucket or os.environ.get('DATA_LAKE_BUCKET')
    if not bucket_name:
        logger.error("❌ DATA_LAKE_BUCKET not set. Set it via:")
        logger.error("   export DATA_LAKE_BUCKET=dr-daily-report-data-lake-dev")
        logger.error("   or use --bucket argument")
        sys.exit(1)

    # Run tests
    tester = InfrastructureTester(
        bucket_name=bucket_name,
        lambda_function_name=args.function_name,
        region=args.region,
        qualifier=args.qualifier
    )

    results = tester.run_all_tests(args.ticker)

    # Exit with appropriate code
    sys.exit(0 if results['overall_success'] else 1)


if __name__ == '__main__':
    main()
