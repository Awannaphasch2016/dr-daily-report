#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Integration Test: Invoke Lambda Precompute Service and Verify Data Lake Storage

Tests end-to-end integration:
1. Invokes Lambda function with precompute action for NVDA
2. Waits for Lambda completion
3. Verifies processed data (indicators, percentiles) stored in S3 Data Lake
4. Validates data structure, tags, and metadata

This is an integration test that verifies:
- Lambda function execution works
- IAM permissions (S3 Data Lake access)
- Environment variables configured correctly
- PrecomputeService works in Lambda environment
- Data flow: Lambda → compute → S3 Data Lake

Usage:
    export DATA_LAKE_BUCKET=dr-daily-report-data-lake-dev
    export AWS_REGION=ap-southeast-1
    python scripts/test_precompute_lambda_integration.py
"""

import os
import sys
import json
import time
import logging
import boto3
from datetime import date, datetime
from typing import Dict, Any, Optional
from botocore.exceptions import ClientError

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class LambdaPrecomputeTester:
    """Test Lambda precompute service integration."""

    def __init__(
        self,
        function_name: str,
        bucket_name: str,
        region: str = 'ap-southeast-1',
        qualifier: str = 'live'
    ):
        """
        Initialize tester.

        Args:
            function_name: Lambda function name (e.g., 'dr-daily-report-ticker-scheduler-dev')
            bucket_name: S3 Data Lake bucket name
            region: AWS region
            qualifier: Lambda qualifier ('live' alias or '$LATEST')
        """
        self.function_name = function_name
        self.bucket_name = bucket_name
        self.region = region
        self.qualifier = qualifier

        self.lambda_client = boto3.client('lambda', region_name=region)
        self.s3_client = boto3.client('s3', region_name=region)

    def invoke_precompute(
        self,
        symbol: str,
        include_report: bool = False
    ) -> Dict[str, Any]:
        """
        Invoke Lambda function with precompute action.

        Args:
            symbol: Ticker symbol (e.g., 'NVDA')
            include_report: Whether to generate LLM report (default: False for faster test)

        Returns:
            Dict with invocation results
        """
        logger.info(f"🚀 Invoking Lambda function: {self.function_name}")
        logger.info(f"   Action: precompute")
        logger.info(f"   Symbol: {symbol}")
        logger.info(f"   Include report: {include_report}")

        payload = {
            'action': 'precompute',
            'symbol': symbol,
            'include_report': include_report
        }

        try:
            # Invoke Lambda (synchronous - wait for response)
            response = self.lambda_client.invoke(
                FunctionName=self.function_name,
                Qualifier=self.qualifier,
                InvocationType='RequestResponse',  # Synchronous - wait for response
                Payload=json.dumps(payload)
            )

            # Parse response
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

    def verify_processed_data(
        self,
        ticker: str,
        target_date: date
    ) -> Dict[str, Any]:
        """
        Verify processed data was stored in S3 Data Lake.

        Checks:
        - processed/indicators/{ticker}/{date}/
        - processed/percentiles/{ticker}/{date}/
        - Tags and metadata

        Args:
            ticker: Ticker symbol
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

                # Get object details
                head_response = self.s3_client.head_object(
                    Bucket=self.bucket_name,
                    Key=indicator_key
                )

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
                    'metadata': head_response.get('Metadata', {}),
                    'data_keys': list(indicators_data.keys())[:10],  # Sample keys
                    'size_bytes': head_response.get('ContentLength', 0)
                }

                logger.info(f"✅ Found indicators: {indicator_key}")
                logger.info(f"   Tags: {tags}")
                logger.info(f"   Data keys: {results['indicators']['data_keys']}")

            else:
                results['indicators'] = {
                    'found': False,
                    'message': f"No indicators found at prefix: {indicators_prefix}"
                }
                logger.warning(f"⚠️ No indicators found for {ticker} on {date_str}")

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

                # Get object details
                head_response = self.s3_client.head_object(
                    Bucket=self.bucket_name,
                    Key=percentile_key
                )

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
                    'metadata': head_response.get('Metadata', {}),
                    'data_keys': list(percentiles_data.keys())[:10],  # Sample keys
                    'size_bytes': head_response.get('ContentLength', 0)
                }

                logger.info(f"✅ Found percentiles: {percentile_key}")
                logger.info(f"   Tags: {tags}")
                logger.info(f"   Data keys: {results['percentiles']['data_keys']}")

            else:
                results['percentiles'] = {
                    'found': False,
                    'message': f"No percentiles found at prefix: {percentiles_prefix}"
                }
                logger.warning(f"⚠️ No percentiles found for {ticker} on {date_str}")

        except Exception as e:
            logger.error(f"❌ Error checking percentiles: {e}")
            results['percentiles'] = {
                'found': False,
                'error': str(e)
            }

        return results

    def run_test(self, symbol: str) -> Dict[str, Any]:
        """
        Run complete integration test.

        Args:
            symbol: Ticker symbol to test

        Returns:
            Dict with test results
        """
        logger.info("=" * 80)
        logger.info("Lambda Precompute Integration Test")
        logger.info("=" * 80)
        logger.info(f"Function: {self.function_name}")
        logger.info(f"Bucket: {self.bucket_name}")
        logger.info(f"Symbol: {symbol}")
        logger.info("=" * 80)

        results = {
            'symbol': symbol,
            'lambda_invocation': {},
            'data_verification': {},
            'overall_success': False
        }

        # Step 1: Invoke Lambda
        logger.info(f"\n{'='*80}")
        logger.info("Step 1: Invoking Lambda Precompute Service")
        logger.info(f"{'='*80}")

        invocation_result = self.invoke_precompute(symbol, include_report=False)
        results['lambda_invocation'] = invocation_result

        if not invocation_result.get('success'):
            logger.error("❌ Lambda invocation failed - cannot proceed with verification")
            return results

        # Wait a moment for S3 writes to complete
        logger.info("\n⏳ Waiting 5 seconds for S3 writes to complete...")
        time.sleep(5)

        # Step 2: Verify processed data
        logger.info(f"\n{'='*80}")
        logger.info("Step 2: Verifying Processed Data in S3 Data Lake")
        logger.info(f"{'='*80}")

        today = date.today()
        verification_result = self.verify_processed_data(symbol, today)
        results['data_verification'] = verification_result

        # Step 3: Summary
        logger.info(f"\n{'='*80}")
        logger.info("Test Summary")
        logger.info(f"{'='*80}")

        lambda_success = invocation_result.get('success', False)
        indicators_found = verification_result.get('indicators', {}).get('found', False)
        percentiles_found = verification_result.get('percentiles', {}).get('found', False)

        logger.info(f"Lambda Invocation: {'✅ SUCCESS' if lambda_success else '❌ FAILED'}")
        logger.info(f"Indicators Stored: {'✅ YES' if indicators_found else '❌ NO'}")
        logger.info(f"Percentiles Stored: {'✅ YES' if percentiles_found else '❌ NO'}")

        results['overall_success'] = (
            lambda_success and
            indicators_found and
            percentiles_found
        )

        if results['overall_success']:
            logger.info("\n✅ Integration test PASSED!")
            logger.info("   All components working correctly:")
            logger.info("   - Lambda function executes successfully")
            logger.info("   - IAM permissions configured correctly")
            logger.info("   - PrecomputeService computes indicators and percentiles")
            logger.info("   - S3 Data Lake storage works")
        else:
            logger.error("\n❌ Integration test FAILED")
            if not lambda_success:
                logger.error("   - Lambda invocation failed")
            if not indicators_found:
                logger.error("   - Indicators not found in S3")
            if not percentiles_found:
                logger.error("   - Percentiles not found in S3")

        return results


def get_lambda_function_name(environment: str = 'dev') -> str:
    """
    Get Lambda function name for environment.

    Args:
        environment: Environment name (dev, staging, prod)

    Returns:
        Function name
    """
    project_name = "dr-daily-report"
    return f"{project_name}-ticker-scheduler-{environment}"


def main():
    """Main test execution."""
    import argparse

    parser = argparse.ArgumentParser(
        description='Test Lambda precompute service integration'
    )
    parser.add_argument(
        '--symbol',
        default='NVDA',
        help='Ticker symbol to test (default: NVDA)'
    )
    parser.add_argument(
        '--function-name',
        help='Lambda function name (default: auto-detect from environment)'
    )
    parser.add_argument(
        '--bucket',
        help='S3 Data Lake bucket name (default: from DATA_LAKE_BUCKET env var)'
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
    parser.add_argument(
        '--environment',
        default='dev',
        help='Environment name for auto-detecting function name (default: dev)'
    )

    args = parser.parse_args()

    # Get function name
    function_name = args.function_name
    if not function_name:
        function_name = get_lambda_function_name(args.environment)
        logger.info(f"Auto-detected function name: {function_name}")

    # Get bucket name
    bucket_name = args.bucket or os.environ.get('DATA_LAKE_BUCKET')
    if not bucket_name:
        logger.error("❌ DATA_LAKE_BUCKET not set. Set it via:")
        logger.error("   export DATA_LAKE_BUCKET=dr-daily-report-data-lake-dev")
        logger.error("   or use --bucket argument")
        sys.exit(1)

    # Run test
    tester = LambdaPrecomputeTester(
        function_name=function_name,
        bucket_name=bucket_name,
        region=args.region,
        qualifier=args.qualifier
    )

    results = tester.run_test(args.symbol)

    # Exit with appropriate code
    sys.exit(0 if results['overall_success'] else 1)


if __name__ == '__main__':
    main()
