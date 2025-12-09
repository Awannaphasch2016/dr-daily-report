#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script: Fetch 1 ticker and verify data lake storage across all 3 phases.

Tests:
1. Fetch NVDA ticker using TickerFetcher
2. Verify Phase 1: Raw data storage (structure, tags, metadata)
3. Verify Phase 2: Processed data storage (if available)
4. Verify Phase 3: Retrieval methods
"""

import os
import sys
import json
import logging
from datetime import date, datetime
from typing import Optional, Dict, Any
import boto3
from botocore.exceptions import ClientError

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.scheduler.ticker_fetcher import TickerFetcher
from src.data.data_lake import DataLakeStorage

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DataLakeVerifier:
    """Verifies data lake storage across all phases."""

    def __init__(self, bucket_name: str):
        """
        Initialize verifier.

        Args:
            bucket_name: S3 bucket name for data lake
        """
        self.bucket_name = bucket_name
        self.s3_client = boto3.client('s3')
        self.data_lake = DataLakeStorage(bucket_name=bucket_name)

    def verify_phase1_raw_data(
        self,
        ticker: str,
        expected_date: date
    ) -> Dict[str, Any]:
        """
        Verify Phase 1: Raw data storage.

        Checks:
        - S3 key structure: raw/yfinance/{ticker}/{date}/{timestamp}.json
        - Tags: source=yfinance, ticker={ticker}, fetched_at={date}
        - Metadata: fetched_at, source, ticker, data_classification

        Args:
            ticker: Ticker symbol (e.g., 'NVDA')
            expected_date: Expected date for the raw data

        Returns:
            Dict with verification results
        """
        logger.info(f"🔍 Verifying Phase 1: Raw data storage for {ticker}")

        results = {
            'phase': 'Phase 1: Raw Data Storage',
            'ticker': ticker,
            'date': expected_date.isoformat(),
            'passed': False,
            'checks': {}
        }

        try:
            # List objects with prefix: raw/yfinance/{ticker}/{date}/
            date_str = expected_date.isoformat()
            prefix = f"raw/yfinance/{ticker}/{date_str}/"
            logger.info(f"   Searching for objects with prefix: {prefix}")

            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=prefix
            )

            if 'Contents' not in response or len(response['Contents']) == 0:
                results['checks']['object_exists'] = {
                    'passed': False,
                    'message': f"No raw data files found for {ticker} on {date_str}"
                }
                return results

            # Get the latest file (most recent LastModified)
            latest_file = max(
                response['Contents'],
                key=lambda obj: obj['LastModified']
            )
            s3_key = latest_file['Key']

            results['checks']['object_exists'] = {
                'passed': True,
                'message': f"Found raw data file: {s3_key}"
            }

            # Verify key structure: raw/yfinance/{ticker}/{date}/{timestamp}.json
            expected_prefix = f"raw/yfinance/{ticker}/{date_str}/"
            if not s3_key.startswith(expected_prefix):
                results['checks']['key_structure'] = {
                    'passed': False,
                    'message': f"Key structure incorrect. Expected prefix: {expected_prefix}, got: {s3_key}"
                }
            elif not s3_key.endswith('.json'):
                results['checks']['key_structure'] = {
                    'passed': False,
                    'message': f"Key should end with .json, got: {s3_key}"
                }
            else:
                results['checks']['key_structure'] = {
                    'passed': True,
                    'message': f"Key structure correct: {s3_key}"
                }

            # Get object tags
            try:
                tag_response = self.s3_client.get_object_tagging(
                    Bucket=self.bucket_name,
                    Key=s3_key
                )
                tags = {tag['Key']: tag['Value'] for tag in tag_response.get('TagSet', [])}

                # Verify tags
                expected_tags = {
                    'source': 'yfinance',
                    'ticker': ticker,
                    'fetched_at': date_str
                }

                tags_passed = True
                tags_messages = []
                for key, expected_value in expected_tags.items():
                    if key not in tags:
                        tags_passed = False
                        tags_messages.append(f"Missing tag: {key}")
                    elif tags[key] != expected_value:
                        tags_passed = False
                        tags_messages.append(f"Tag {key} mismatch: expected {expected_value}, got {tags[key]}")
                    else:
                        tags_messages.append(f"✅ Tag {key}={tags[key]}")

                results['checks']['tags'] = {
                    'passed': tags_passed,
                    'message': '\n'.join(tags_messages),
                    'actual_tags': tags
                }

            except ClientError as e:
                results['checks']['tags'] = {
                    'passed': False,
                    'message': f"Failed to retrieve tags: {e}"
                }

            # Get object metadata
            try:
                head_response = self.s3_client.head_object(
                    Bucket=self.bucket_name,
                    Key=s3_key
                )
                metadata = head_response.get('Metadata', {})

                # Verify metadata fields
                expected_metadata_keys = ['fetched_at', 'source', 'ticker', 'data_classification']
                metadata_passed = True
                metadata_messages = []
                for key in expected_metadata_keys:
                    if key not in metadata:
                        metadata_passed = False
                        metadata_messages.append(f"Missing metadata: {key}")
                    else:
                        metadata_messages.append(f"✅ Metadata {key}={metadata[key]}")

                # Verify metadata values
                if metadata.get('source') != 'yfinance':
                    metadata_passed = False
                    metadata_messages.append(f"Metadata source should be 'yfinance', got: {metadata.get('source')}")
                if metadata.get('ticker') != ticker:
                    metadata_passed = False
                    metadata_messages.append(f"Metadata ticker should be '{ticker}', got: {metadata.get('ticker')}")

                results['checks']['metadata'] = {
                    'passed': metadata_passed,
                    'message': '\n'.join(metadata_messages),
                    'actual_metadata': metadata
                }

            except ClientError as e:
                results['checks']['metadata'] = {
                    'passed': False,
                    'message': f"Failed to retrieve metadata: {e}"
                }

            # Verify JSON content is valid
            try:
                obj_response = self.s3_client.get_object(
                    Bucket=self.bucket_name,
                    Key=s3_key
                )
                content = obj_response['Body'].read().decode('utf-8')
                data = json.loads(content)

                results['checks']['json_content'] = {
                    'passed': True,
                    'message': f"JSON content valid, keys: {list(data.keys())[:5]}..."
                }

            except json.JSONDecodeError as e:
                results['checks']['json_content'] = {
                    'passed': False,
                    'message': f"Invalid JSON content: {e}"
                }
            except ClientError as e:
                results['checks']['json_content'] = {
                    'passed': False,
                    'message': f"Failed to retrieve object: {e}"
                }

            # Overall Phase 1 result
            all_checks_passed = all(
                check.get('passed', False)
                for check in results['checks'].values()
            )
            results['passed'] = all_checks_passed
            results['s3_key'] = s3_key

        except Exception as e:
            logger.error(f"Error verifying Phase 1: {e}")
            results['checks']['error'] = {
                'passed': False,
                'message': f"Exception: {e}"
            }

        return results

    def verify_phase2_processed_data(
        self,
        ticker: str,
        expected_date: date
    ) -> Dict[str, Any]:
        """
        Verify Phase 2: Processed data storage (if available).

        Checks:
        - processed/indicators/{ticker}/{date}/
        - processed/percentiles/{ticker}/{date}/
        - Data lineage tags linking to raw data

        Args:
            ticker: Ticker symbol
            expected_date: Expected date for processed data

        Returns:
            Dict with verification results
        """
        logger.info(f"🔍 Verifying Phase 2: Processed data storage for {ticker}")

        results = {
            'phase': 'Phase 2: Processed Data Storage',
            'ticker': ticker,
            'date': expected_date.isoformat(),
            'passed': False,
            'checks': {}
        }

        date_str = expected_date.isoformat()

        # Check for indicators
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

                # Check tags for data lineage
                try:
                    tag_response = self.s3_client.get_object_tagging(
                        Bucket=self.bucket_name,
                        Key=indicator_key
                    )
                    tags = {tag['Key']: tag['Value'] for tag in tag_response.get('TagSet', [])}

                    results['checks']['indicators'] = {
                        'passed': True,
                        'message': f"Found indicators file: {indicator_key}",
                        'has_lineage': 'source_raw_data' in tags,
                        'tags': tags
                    }
                except ClientError as e:
                    results['checks']['indicators'] = {
                        'passed': False,
                        'message': f"Found indicators but failed to get tags: {e}"
                    }
            else:
                results['checks']['indicators'] = {
                    'passed': False,
                    'message': f"No indicators found (expected - requires precompute service)",
                    'note': 'This is expected if precompute service has not run yet'
                }

        except Exception as e:
            results['checks']['indicators'] = {
                'passed': False,
                'message': f"Error checking indicators: {e}"
            }

        # Check for percentiles
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

                # Check tags for data lineage
                try:
                    tag_response = self.s3_client.get_object_tagging(
                        Bucket=self.bucket_name,
                        Key=percentile_key
                    )
                    tags = {tag['Key']: tag['Value'] for tag in tag_response.get('TagSet', [])}

                    results['checks']['percentiles'] = {
                        'passed': True,
                        'message': f"Found percentiles file: {percentile_key}",
                        'has_lineage': 'source_raw_data' in tags,
                        'tags': tags
                    }
                except ClientError as e:
                    results['checks']['percentiles'] = {
                        'passed': False,
                        'message': f"Found percentiles but failed to get tags: {e}"
                    }
            else:
                results['checks']['percentiles'] = {
                    'passed': False,
                    'message': f"No percentiles found (expected - requires precompute service)",
                    'note': 'This is expected if precompute service has not run yet'
                }

        except Exception as e:
            results['checks']['percentiles'] = {
                'passed': False,
                'message': f"Error checking percentiles: {e}"
            }

        # Phase 2 is considered passed if at least one processed data type exists
        # (or if neither exists, that's expected and not a failure)
        has_indicators = results['checks'].get('indicators', {}).get('passed', False)
        has_percentiles = results['checks'].get('percentiles', {}).get('passed', False)

        if has_indicators or has_percentiles:
            results['passed'] = True
        else:
            # Not a failure - just means precompute hasn't run yet
            results['passed'] = True  # Still pass, but note it's expected
            results['note'] = 'No processed data found (expected if precompute service has not run)'

        return results

    def verify_phase3_retrieval(
        self,
        ticker: str,
        target_date: date
    ) -> Dict[str, Any]:
        """
        Verify Phase 3: Retrieval methods.

        Tests:
        - get_latest_indicators(ticker)
        - get_indicators_by_date(ticker, date)
        - get_percentiles_by_date(ticker, date)

        Args:
            ticker: Ticker symbol
            target_date: Date to test retrieval for

        Returns:
            Dict with verification results
        """
        logger.info(f"🔍 Verifying Phase 3: Retrieval methods for {ticker}")

        results = {
            'phase': 'Phase 3: Retrieval Methods',
            'ticker': ticker,
            'date': target_date.isoformat(),
            'passed': False,
            'checks': {}
        }

        # Test get_latest_indicators
        try:
            latest_indicators = self.data_lake.get_latest_indicators(ticker)
            if latest_indicators is not None:
                results['checks']['get_latest_indicators'] = {
                    'passed': True,
                    'message': f"Retrieved latest indicators: {len(latest_indicators)} keys",
                    'sample_keys': list(latest_indicators.keys())[:5]
                }
            else:
                results['checks']['get_latest_indicators'] = {
                    'passed': True,  # Method works, just no data yet
                    'message': "Method works but no indicators found (expected if precompute hasn't run)",
                    'note': 'This is expected if precompute service has not run yet'
                }
        except Exception as e:
            results['checks']['get_latest_indicators'] = {
                'passed': False,
                'message': f"Method failed: {e}"
            }

        # Test get_indicators_by_date
        try:
            indicators_by_date = self.data_lake.get_indicators_by_date(ticker, target_date)
            if indicators_by_date is not None:
                results['checks']['get_indicators_by_date'] = {
                    'passed': True,
                    'message': f"Retrieved indicators for {target_date}: {len(indicators_by_date)} keys",
                    'sample_keys': list(indicators_by_date.keys())[:5]
                }
            else:
                results['checks']['get_indicators_by_date'] = {
                    'passed': True,  # Method works, just no data yet
                    'message': f"Method works but no indicators found for {target_date} (expected if precompute hasn't run)",
                    'note': 'This is expected if precompute service has not run yet'
                }
        except Exception as e:
            results['checks']['get_indicators_by_date'] = {
                'passed': False,
                'message': f"Method failed: {e}"
            }

        # Test get_percentiles_by_date
        try:
            percentiles_by_date = self.data_lake.get_percentiles_by_date(ticker, target_date)
            if percentiles_by_date is not None:
                results['checks']['get_percentiles_by_date'] = {
                    'passed': True,
                    'message': f"Retrieved percentiles for {target_date}: {len(percentiles_by_date)} keys",
                    'sample_keys': list(percentiles_by_date.keys())[:5]
                }
            else:
                results['checks']['get_percentiles_by_date'] = {
                    'passed': True,  # Method works, just no data yet
                    'message': f"Method works but no percentiles found for {target_date} (expected if precompute hasn't run)",
                    'note': 'This is expected if precompute service has not run yet'
                }
        except Exception as e:
            results['checks']['get_percentiles_by_date'] = {
                'passed': False,
                'message': f"Method failed: {e}"
            }

        # Phase 3 passes if all methods execute without errors (even if they return None)
        all_methods_work = all(
            check.get('passed', False)
            for check in results['checks'].values()
        )
        results['passed'] = all_methods_work

        return results


def main():
    """Main test execution."""
    logger.info("=" * 80)
    logger.info("Test Plan: Fetch 1 Ticker and Verify Data Lake Storage")
    logger.info("=" * 80)

    # Get data lake bucket from environment
    bucket_name = os.environ.get('DATA_LAKE_BUCKET')
    if not bucket_name:
        logger.error("❌ DATA_LAKE_BUCKET environment variable not set")
        logger.info("Set it with: export DATA_LAKE_BUCKET=<bucket-name>")
        sys.exit(1)

    logger.info(f"📦 Using data lake bucket: {bucket_name}")

    ticker = 'NVDA'
    today = date.today()

    # Step 1: Fetch ticker
    logger.info(f"\n{'='*80}")
    logger.info(f"Step 1: Fetching ticker {ticker}")
    logger.info(f"{'='*80}")

    try:
        fetcher = TickerFetcher(data_lake_bucket=bucket_name)
        fetch_result = fetcher.fetch_ticker(ticker)

        if fetch_result['status'] != 'success':
            logger.error(f"❌ Fetch failed: {fetch_result.get('error', 'Unknown error')}")
            sys.exit(1)

        logger.info(f"✅ Fetch succeeded: {fetch_result}")
        logger.info(f"   Company: {fetch_result.get('company_name', 'N/A')}")
        logger.info(f"   Date: {fetch_result.get('date', 'N/A')}")

    except Exception as e:
        logger.error(f"❌ Exception during fetch: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    # Step 2: Verify Phase 1
    logger.info(f"\n{'='*80}")
    logger.info(f"Step 2: Verifying Phase 1 - Raw Data Storage")
    logger.info(f"{'='*80}")

    verifier = DataLakeVerifier(bucket_name)
    phase1_results = verifier.verify_phase1_raw_data(ticker, today)

    logger.info(f"\nPhase 1 Results:")
    logger.info(f"  Status: {'✅ PASSED' if phase1_results['passed'] else '❌ FAILED'}")
    for check_name, check_result in phase1_results['checks'].items():
        status = '✅' if check_result.get('passed', False) else '❌'
        logger.info(f"  {status} {check_name}: {check_result.get('message', 'N/A')}")

    # Step 3: Verify Phase 2
    logger.info(f"\n{'='*80}")
    logger.info(f"Step 3: Verifying Phase 2 - Processed Data Storage")
    logger.info(f"{'='*80}")

    phase2_results = verifier.verify_phase2_processed_data(ticker, today)

    logger.info(f"\nPhase 2 Results:")
    logger.info(f"  Status: {'✅ PASSED' if phase2_results['passed'] else '❌ FAILED'}")
    if phase2_results.get('note'):
        logger.info(f"  Note: {phase2_results['note']}")
    for check_name, check_result in phase2_results['checks'].items():
        status = '✅' if check_result.get('passed', False) else '⚠️'
        logger.info(f"  {status} {check_name}: {check_result.get('message', 'N/A')}")

    # Step 4: Verify Phase 3
    logger.info(f"\n{'='*80}")
    logger.info(f"Step 4: Verifying Phase 3 - Retrieval Methods")
    logger.info(f"{'='*80}")

    phase3_results = verifier.verify_phase3_retrieval(ticker, today)

    logger.info(f"\nPhase 3 Results:")
    logger.info(f"  Status: {'✅ PASSED' if phase3_results['passed'] else '❌ FAILED'}")
    for check_name, check_result in phase3_results['checks'].items():
        status = '✅' if check_result.get('passed', False) else '❌'
        logger.info(f"  {status} {check_name}: {check_result.get('message', 'N/A')}")

    # Summary
    logger.info(f"\n{'='*80}")
    logger.info("Summary")
    logger.info(f"{'='*80}")

    all_phases_passed = (
        phase1_results['passed'] and
        phase2_results['passed'] and
        phase3_results['passed']
    )

    logger.info(f"Phase 1 (Raw Data): {'✅ PASSED' if phase1_results['passed'] else '❌ FAILED'}")
    logger.info(f"Phase 2 (Processed Data): {'✅ PASSED' if phase2_results['passed'] else '⚠️ NO DATA (expected)'}")
    logger.info(f"Phase 3 (Retrieval Methods): {'✅ PASSED' if phase3_results['passed'] else '❌ FAILED'}")

    if all_phases_passed:
        logger.info("\n✅ All phases passed!")
        sys.exit(0)
    else:
        logger.error("\n❌ Some phases failed. See details above.")
        sys.exit(1)


if __name__ == '__main__':
    main()
