# -*- coding: utf-8 -*-
"""
Data Pipeline Diagnostic Tests

Traces the entire data pipeline to identify WHERE data is missing and WHY
the UI shows empty charts.

Test Strategy:
- Test outcomes, not execution: Check actual data existence
- Explicit failure detection: Check each pipeline stage separately
- Defensive programming: Verify data before using it at each step
- Validation gates: Check prerequisites before proceeding

Usage:
    # Run all diagnostic tests
    pytest tests/e2e/test_data_pipeline_diagnostic.py -v -m e2e -s

    # Run specific test class
    pytest tests/e2e/test_data_pipeline_diagnostic.py::TestYahooFinanceDataPipeline -v -m e2e -s

    # With custom ticker
    DIAGNOSTIC_TEST_TICKER=DBS19 pytest tests/e2e/test_data_pipeline_diagnostic.py -v -m e2e -s

Environment Variables:
    DIAGNOSTIC_TEST_TICKER: Ticker to test (default: NVDA19)
    ENVIRONMENT: AWS environment (default: dev)
    PROJECT_NAME: AWS project name (default: dr-daily-report)
    TELEGRAM_API_URL: API endpoint URL (default: http://localhost:8001)
    DATA_LAKE_BUCKET: S3 bucket for fund data CSV files (auto-detected if not set)
    AURORA_HOST: Aurora database host (required for Aurora checks)
    AURORA_USER: Aurora database user (required for Aurora checks)
    AURORA_PASSWORD: Aurora database password (required for Aurora checks)
    AURORA_DATABASE: Aurora database name (required for Aurora checks)

The `-s` flag shows print statements for detailed diagnostics.
"""

import os
import json
import logging
from datetime import date, datetime, timedelta
from typing import Dict, Any, List, Optional

import pytest
import boto3
import yfinance as yf
import requests
from botocore.exceptions import ClientError

# Configure logging for diagnostics
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Test configuration
TEST_TICKER = os.environ.get('DIAGNOSTIC_TEST_TICKER', 'NVDA19')
ENVIRONMENT = os.environ.get('ENVIRONMENT', 'dev')
PROJECT_NAME = os.environ.get('PROJECT_NAME', 'dr-daily-report')
API_URL = os.environ.get('TELEGRAM_API_URL', 'http://localhost:8001')


@pytest.mark.e2e
class TestYahooFinanceDataPipeline:
    """Diagnostic test for Yahoo Finance data pipeline.

    Checks:
    1. Did scheduler Lambda run today?
    2. Does Aurora have price data for today?
    3. Does yfinance API return data for today?
    """

    def setup_method(self):
        """Set up AWS clients and test configuration."""
        self.lambda_client = boto3.client('lambda', region_name='ap-southeast-1')
        self.logs_client = boto3.client('logs', region_name='ap-southeast-1')
        self.scheduler_function_name = f"{PROJECT_NAME}-ticker-scheduler-{ENVIRONMENT}"
        self.today = date.today()
        self.errors = []

    def test_yahoo_finance_data_pipeline(self):
        """Test complete Yahoo Finance data pipeline."""
        print("\n" + "=" * 60)
        print("YAHOO FINANCE DATA PIPELINE DIAGNOSTIC")
        print("=" * 60)

        # Step 1: Check if scheduler Lambda ran today
        scheduler_ran = self._check_scheduler_ran_today()
        print(f"Scheduler ran today: {scheduler_ran}")

        # Step 2: Check Aurora for price data
        aurora_has_data = self._check_aurora_price_data()
        print(f"Data in Aurora today: {aurora_has_data}")

        # Step 3: Check yfinance API
        yfinance_works = self._check_yfinance_api()
        print(f"yfinance API works: {yfinance_works}")

        # Report errors
        if self.errors:
            print("\nErrors found:")
            for error in self.errors:
                print(f"  - {error}")
        else:
            print("\n✅ All checks passed!")

        print("=" * 60 + "\n")

    def _check_scheduler_ran_today(self) -> bool:
        """Check CloudWatch logs for scheduler Lambda execution today."""
        try:
            log_group_name = f"/aws/lambda/{self.scheduler_function_name}"

            # Check if log group exists
            try:
                self.logs_client.describe_log_groups(
                    logGroupNamePrefix=log_group_name
                )
            except ClientError as e:
                if e.response['Error']['Code'] == 'ResourceNotFoundException':
                    self.errors.append(f"Log group not found: {log_group_name}")
                    return False

            # Query logs from today (00:00 UTC)
            start_time = int(datetime.combine(self.today, datetime.min.time()).timestamp() * 1000)
            end_time = int(datetime.now().timestamp() * 1000)

            response = self.logs_client.filter_log_events(
                logGroupName=log_group_name,
                startTime=start_time,
                endTime=end_time,
                filterPattern='"[INFO]"'
            )

            events = response.get('events', [])
            if events:
                latest_event = max(events, key=lambda x: x['timestamp'])
                print(f"  Latest log: {datetime.fromtimestamp(latest_event['timestamp']/1000)}")
                return True
            else:
                self.errors.append(f"No scheduler logs found for {self.today}")
                return False

        except Exception as e:
            self.errors.append(f"Failed to check scheduler logs: {e}")
            return False

    def _check_aurora_price_data(self) -> bool:
        """Check Aurora daily_prices table for today's data."""
        try:
            from src.data.aurora.client import get_aurora_client
            from src.data.aurora.repository import TickerRepository

            client = get_aurora_client()
            repo = TickerRepository(client)

            # Check for any ticker's price data today
            with client.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT COUNT(*) as count, symbol
                        FROM daily_prices
                        WHERE price_date = %s
                        GROUP BY symbol
                        ORDER BY count DESC
                        LIMIT 5
                    """, (self.today,))
                    results = cursor.fetchall()

            if results:
                total_records = sum(row['count'] for row in results)
                print(f"  Found {total_records} price records for {self.today}")
                print(f"  Sample tickers: {[r['symbol'] for r in results[:3]]}")
                return True
            else:
                self.errors.append(f"No price data in Aurora for {self.today}")
                return False

        except Exception as e:
            self.errors.append(f"Failed to check Aurora price data: {e}")
            return False

    def _check_yfinance_api(self) -> bool:
        """Check if yfinance API returns data."""
        try:
            # Use a well-known ticker
            ticker = yf.Ticker("NVDA")
            hist = ticker.history(period="5d")

            if hist.empty:
                self.errors.append("yfinance API returned empty data")
                return False

            latest_date = hist.index[-1].date()
            print(f"  yfinance latest data: {latest_date} ({len(hist)} days)")
            return True

        except Exception as e:
            self.errors.append(f"yfinance API check failed: {e}")
            return False


@pytest.mark.e2e
class TestFundamentalDataPipeline:
    """Diagnostic test for fundamental data pipeline.

    Checks:
    1. Are there new CSV files in S3 today?
    2. Was ETL Lambda triggered?
    3. Does Aurora fund_data table have data?
    """

    def setup_method(self):
        """Set up AWS clients and test configuration."""
        self.s3_client = boto3.client('s3', region_name='ap-southeast-1')
        self.lambda_client = boto3.client('lambda', region_name='ap-southeast-1')
        self.logs_client = boto3.client('logs', region_name='ap-southeast-1')
        self.etl_function_name = f"{PROJECT_NAME}-fund-data-sync-{ENVIRONMENT}"
        self.today = date.today()
        self.errors = []

    def test_fundamental_data_pipeline(self):
        """Test complete fundamental data pipeline."""
        print("\n" + "=" * 60)
        print("FUNDAMENTAL DATA PIPELINE DIAGNOSTIC")
        print("=" * 60)

        # Step 1: Check S3 for CSV files
        s3_has_files = self._check_s3_csv_files()
        print(f"S3 has CSV files today: {s3_has_files}")

        # Step 2: Check ETL Lambda logs
        etl_triggered = self._check_etl_lambda_logs()
        print(f"ETL Lambda triggered: {etl_triggered}")

        # Step 3: Check Aurora fund_data table
        aurora_has_data = self._check_aurora_fund_data()
        print(f"Data in Aurora fund_data table: {aurora_has_data}")

        # Report errors
        if self.errors:
            print("\nErrors found:")
            for error in self.errors:
                print(f"  - {error}")
        else:
            print("\n✅ All checks passed!")

        print("=" * 60 + "\n")

    def _check_s3_csv_files(self) -> bool:
        """Check S3 for CSV files uploaded today."""
        try:
            # Get data lake bucket from environment or infer from project name
            bucket_name = os.environ.get('DATA_LAKE_BUCKET')
            if not bucket_name:
                # Try to infer bucket name
                bucket_name = f"{PROJECT_NAME}-data-lake-{ENVIRONMENT}"

            # Check if bucket exists
            try:
                self.s3_client.head_bucket(Bucket=bucket_name)
            except ClientError as e:
                if e.response['Error']['Code'] == '404':
                    self.errors.append(f"S3 bucket not found: {bucket_name}")
                    return False

            # List objects modified today
            today_start = datetime.combine(self.today, datetime.min.time())
            response = self.s3_client.list_objects_v2(
                Bucket=bucket_name,
                Prefix='fund-data/'
            )

            csv_files = [
                obj for obj in response.get('Contents', [])
                if obj['Key'].endswith('.csv') and
                obj['LastModified'].date() == self.today
            ]

            if csv_files:
                print(f"  Found {len(csv_files)} CSV files uploaded today")
                print(f"  Sample files: {[f['Key'] for f in csv_files[:3]]}")
                return True
            else:
                self.errors.append(f"No CSV files found in S3 for {self.today}")
                return False

        except Exception as e:
            self.errors.append(f"Failed to check S3 CSV files: {e}")
            return False

    def _check_etl_lambda_logs(self) -> bool:
        """Check CloudWatch logs for ETL Lambda execution."""
        try:
            log_group_name = f"/aws/lambda/{self.etl_function_name}"

            # Check if log group exists
            try:
                self.logs_client.describe_log_groups(
                    logGroupNamePrefix=log_group_name
                )
            except ClientError as e:
                if e.response['Error']['Code'] == 'ResourceNotFoundException':
                    self.errors.append(f"ETL Lambda log group not found: {log_group_name}")
                    return False

            # Query logs from last 24 hours
            start_time = int((datetime.now() - timedelta(days=1)).timestamp() * 1000)
            end_time = int(datetime.now().timestamp() * 1000)

            response = self.logs_client.filter_log_events(
                logGroupName=log_group_name,
                startTime=start_time,
                endTime=end_time,
                filterPattern='"[INFO]"'
            )

            events = response.get('events', [])
            if events:
                latest_event = max(events, key=lambda x: x['timestamp'])
                print(f"  Latest ETL log: {datetime.fromtimestamp(latest_event['timestamp']/1000)}")
                return True
            else:
                self.errors.append("No ETL Lambda logs found in last 24 hours")
                return False

        except Exception as e:
            self.errors.append(f"Failed to check ETL Lambda logs: {e}")
            return False

    def _check_aurora_fund_data(self) -> bool:
        """Check Aurora fund_data table for data."""
        try:
            from src.data.aurora.client import get_aurora_client

            client = get_aurora_client()

            with client.get_connection() as conn:
                with conn.cursor() as cursor:
                    # Check if table exists and has data
                    cursor.execute("""
                        SELECT COUNT(*) as count
                        FROM fund_data
                        WHERE d_trade >= DATE_SUB(CURDATE(), INTERVAL 7 DAYS)
                    """)
                    result = cursor.fetchone()

            if result and result['count'] > 0:
                print(f"  Found {result['count']} fund_data records in last 7 days")
                return True
            else:
                self.errors.append("No fund_data records found in Aurora (last 7 days)")
                return False

        except Exception as e:
            # Table might not exist - that's an error
            self.errors.append(f"Failed to check Aurora fund_data: {e}")
            return False


@pytest.mark.e2e
class TestAPIDataRetrieval:
    """Diagnostic test for API data retrieval.

    Checks:
    1. Can we retrieve price_history from Aurora?
    2. Does precomputed_reports cache have data?
    3. Can transformer build price_history array?
    """

    def setup_method(self):
        """Set up test configuration."""
        self.test_ticker = TEST_TICKER
        self.errors = []

    def test_api_data_retrieval(self):
        """Test API data retrieval pipeline."""
        print("\n" + "=" * 60)
        print("API DATA RETRIEVAL DIAGNOSTIC")
        print("=" * 60)

        # Step 1: Check Aurora price_history retrieval
        aurora_price_history = self._check_aurora_price_history()
        print(f"Aurora price_history: {aurora_price_history}")

        # Step 2: Check precomputed cache
        cache_has_data = self._check_precomputed_cache()
        print(f"Precomputed cache: {cache_has_data}")

        # Step 3: Check transformer (if cache exists)
        if cache_has_data:
            transformer_works = self._check_transformer()
            print(f"Transformer builds array: {transformer_works}")
        else:
            print("Transformer: Skipped (no cached report available)")

        # Report errors
        if self.errors:
            print("\nErrors found:")
            for error in self.errors:
                print(f"  - {error}")
        else:
            print("\n✅ All checks passed!")

        print("=" * 60 + "\n")

    def _check_aurora_price_history(self) -> bool:
        """Check if we can retrieve price_history from Aurora."""
        try:
            from src.data.aurora.client import get_aurora_client
            from src.data.aurora.repository import TickerRepository
            from src.api.ticker_service import get_ticker_service

            # Try to resolve ticker to get yahoo_ticker (used in Aurora)
            ticker_service = get_ticker_service()
            try:
                ticker_info = ticker_service.get_ticker_info(self.test_ticker)
                yahoo_ticker = ticker_info.get('yahoo_ticker', self.test_ticker)
            except Exception:
                # Fallback to original ticker if resolution fails
                yahoo_ticker = self.test_ticker

            client = get_aurora_client()
            repo = TickerRepository(client)

            # Try both formats
            prices = repo.get_prices(yahoo_ticker, limit=30)
            if not prices or len(prices) == 0:
                # Try original ticker format
                prices = repo.get_prices(self.test_ticker, limit=30)

            if prices and len(prices) > 0:
                print(f"  Retrieved {len(prices)} price records for {yahoo_ticker}")
                latest = prices[0]
                print(f"  Latest price: {latest.get('price_date')} - Close: {latest.get('close')}")
                return True
            else:
                self.errors.append(f"No price history found in Aurora for {yahoo_ticker} (tried {self.test_ticker})")
                return False

        except Exception as e:
            self.errors.append(f"Failed to retrieve price_history from Aurora: {e}")
            return False

    def _check_precomputed_cache(self) -> bool:
        """Check precomputed_reports cache."""
        try:
            from src.data.aurora.precompute_service import PrecomputeService
            from src.api.ticker_service import get_ticker_service

            # Try to resolve ticker to get yahoo_ticker (used in cache)
            ticker_service = get_ticker_service()
            try:
                ticker_info = ticker_service.get_ticker_info(self.test_ticker)
                yahoo_ticker = ticker_info.get('yahoo_ticker', self.test_ticker)
            except Exception:
                # Fallback to original ticker if resolution fails
                yahoo_ticker = self.test_ticker

            service = PrecomputeService()
            cached_report = service.get_cached_report(yahoo_ticker)

            if cached_report:
                print(f"  Found cached report for {yahoo_ticker}")
                print(f"  Report date: {cached_report.get('report_date')}")
                print(f"  Status: {cached_report.get('status')}")
                return True
            else:
                self.errors.append(f"No cached report found for {yahoo_ticker} (tried {self.test_ticker})")
                return False

        except Exception as e:
            self.errors.append(f"Failed to check precomputed cache: {e}")
            return False

    def _check_transformer(self) -> bool:
        """Check if transformer can build price_history array."""
        try:
            from src.api.transformer import ResponseTransformer

            transformer = ResponseTransformer()

            # Mock ticker_data with history DataFrame
            import pandas as pd
            import numpy as np

            dates = pd.date_range(start='2024-01-01', periods=30, freq='D')
            prices = 100 + np.cumsum(np.random.randn(30) * 2)

            mock_ticker_data = {
                'history': pd.DataFrame({
                    'Open': prices * 0.99,
                    'High': prices * 1.02,
                    'Low': prices * 0.98,
                    'Close': prices,
                    'Volume': np.random.randint(1000000, 10000000, 30)
                }, index=dates)
            }

            price_history = transformer._build_price_history(mock_ticker_data, initial_investment=1000.0)

            if price_history and len(price_history) > 0:
                print(f"  Transformer built {len(price_history)} price_history points")
                return True
            else:
                self.errors.append("Transformer returned empty price_history array")
                return False

        except Exception as e:
            self.errors.append(f"Transformer check failed: {e}")
            return False


@pytest.mark.e2e
class TestUIDataFlow:
    """Diagnostic test for UI data flow.

    Checks:
    1. Does API endpoint return price_history?
    2. Is price_history array non-empty?
    3. Does response match expected format?
    """

    def setup_method(self):
        """Set up test configuration."""
        self.test_ticker = TEST_TICKER
        self.api_url = API_URL
        self.errors = []

    def test_ui_data_flow(self):
        """Test complete UI data flow."""
        print("\n" + "=" * 60)
        print("UI DATA FLOW DIAGNOSTIC")
        print("=" * 60)

        # Step 1: Call API endpoint
        response_data = self._call_api_endpoint()
        if response_data is None:
            print("API endpoint call: FAILED")
            return

        print("API endpoint call: SUCCESS")

        # Step 2: Check response contains price_history
        has_price_history = self._check_price_history_in_response(response_data)
        print(f"Response contains price_history: {has_price_history}")

        # Step 3: Check price_history is non-empty
        if has_price_history:
            is_non_empty = self._check_price_history_non_empty(response_data)
            print(f"price_history is non-empty: {is_non_empty}")

        # Report errors
        if self.errors:
            print("\nErrors found:")
            for error in self.errors:
                print(f"  - {error}")
        else:
            print("\n✅ All checks passed!")

        print("=" * 60 + "\n")

    def _call_api_endpoint(self) -> Optional[Dict[str, Any]]:
        """Call API endpoint and return response."""
        try:
            url = f"{self.api_url}/api/v1/report/{self.test_ticker}"
            print(f"  Calling: {url}")

            response = requests.get(url, timeout=30)

            if response.status_code != 200:
                self.errors.append(
                    f"API returned status {response.status_code}: {response.text[:200]}"
                )
                return None

            data = response.json()
            print(f"  Response received: {len(str(data))} bytes")
            return data

        except requests.exceptions.ConnectionError:
            self.errors.append(f"Cannot connect to API at {self.api_url}")
            return None
        except Exception as e:
            self.errors.append(f"API call failed: {e}")
            return None

    def _check_price_history_in_response(self, response_data: Dict[str, Any]) -> bool:
        """Check if response contains price_history field."""
        if 'price_history' in response_data:
            print(f"  price_history field found")
            return True
        else:
            self.errors.append("Response missing 'price_history' field")
            print(f"  Available fields: {list(response_data.keys())}")
            return False

    def _check_price_history_non_empty(self, response_data: Dict[str, Any]) -> bool:
        """Check if price_history array is non-empty."""
        price_history = response_data.get('price_history', [])

        if isinstance(price_history, list) and len(price_history) > 0:
            print(f"  price_history has {len(price_history)} data points")
            # Check first item structure
            first_item = price_history[0]
            required_fields = ['date', 'close']
            missing_fields = [f for f in required_fields if f not in first_item]
            if missing_fields:
                self.errors.append(f"price_history items missing fields: {missing_fields}")
                return False
            return True
        else:
            self.errors.append(f"price_history is empty or not a list: {type(price_history)}")
            return False
