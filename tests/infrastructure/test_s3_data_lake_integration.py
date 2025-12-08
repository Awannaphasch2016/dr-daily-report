"""
S3 Data Lake Integration Tests

Tests the complete data flow for Phase 1 S3 Data Lake staging:
1. Raw data storage to S3 (with tagging and metadata)
2. Data lineage tracking (S3 tags + Aurora foreign keys)
3. Round-trip: Store raw → retrieve → verify integrity

These are integration tests that run against actual AWS infrastructure.
Mark with @pytest.mark.integration to exclude from default test runs.
"""
import json
import os
from datetime import datetime, timezone
from typing import Dict, Any

import boto3
import pytest


class TestS3DataLakeIntegration:
    """Integration tests for S3 Data Lake Phase 1 implementation."""

    def setup_method(self):
        """Set up S3 client and test configuration."""
        self.s3_client = boto3.client('s3', region_name='ap-southeast-1')
        self.env = os.getenv('ENV', 'dev')
        self.bucket_name = f'dr-daily-report-data-lake-{self.env}'

    @pytest.mark.integration
    def test_store_raw_yfinance_data_with_tags(self):
        """
        GIVEN a raw yfinance API response for a ticker
        WHEN storing to S3 Data Lake with tagging
        THEN object should be stored with correct structure, tags, and metadata
        """
        # Arrange
        ticker = 'NVDA19'
        timestamp = datetime.now(timezone.utc)
        date_str = timestamp.strftime('%Y-%m-%d')
        timestamp_str = timestamp.isoformat()

        # Simulate raw yfinance data
        raw_data = {
            'symbol': ticker,
            'shortName': 'NVIDIA Corporation',
            'regularMarketPrice': 501.35,
            'regularMarketVolume': 15234567,
            'fiftyTwoWeekHigh': 520.45,
            'fiftyTwoWeekLow': 245.67,
            'fetched_at': timestamp_str
        }

        # Key structure: raw/yfinance/{ticker}/{date}/{timestamp}.json
        s3_key = f'raw/yfinance/{ticker}/{date_str}/{timestamp_str}.json'

        # Act: Store to S3 with tagging
        self.s3_client.put_object(
            Bucket=self.bucket_name,
            Key=s3_key,
            Body=json.dumps(raw_data),
            ContentType='application/json',
            Tagging=f'source=yfinance&ticker={ticker}&fetched_at={date_str}',
            Metadata={
                'fetched_at': timestamp_str,
                'source': 'yfinance',
                'ticker': ticker,
                'data_classification': 'public-api-data'
            }
        )

        # Assert: Verify object exists
        response = self.s3_client.head_object(
            Bucket=self.bucket_name,
            Key=s3_key
        )

        assert response['ResponseMetadata']['HTTPStatusCode'] == 200, \
            "Object should be stored successfully"

        # Verify content type
        assert response['ContentType'] == 'application/json', \
            "Content type should be application/json"

        # Verify metadata
        metadata = response['Metadata']
        assert metadata['fetched_at'] == timestamp_str, \
            "Metadata should contain fetched_at timestamp"
        assert metadata['source'] == 'yfinance', \
            "Metadata should contain source=yfinance"
        assert metadata['ticker'] == ticker, \
            f"Metadata should contain ticker={ticker}"

        # Cleanup
        self.s3_client.delete_object(Bucket=self.bucket_name, Key=s3_key)

    @pytest.mark.integration
    def test_retrieve_raw_data_roundtrip(self):
        """
        GIVEN raw data stored in S3
        WHEN retrieving the object
        THEN data should match exactly what was stored (integrity check)
        """
        # Arrange
        ticker = 'TEST_TICKER'
        timestamp = datetime.now(timezone.utc)
        date_str = timestamp.strftime('%Y-%m-%d')
        timestamp_str = timestamp.isoformat()

        original_data = {
            'symbol': ticker,
            'price': 123.45,
            'volume': 9876543,
            'fetched_at': timestamp_str,
            'test': True
        }

        s3_key = f'raw/yfinance/{ticker}/{date_str}/{timestamp_str}.json'

        # Act 1: Store
        self.s3_client.put_object(
            Bucket=self.bucket_name,
            Key=s3_key,
            Body=json.dumps(original_data),
            ContentType='application/json'
        )

        # Act 2: Retrieve
        response = self.s3_client.get_object(
            Bucket=self.bucket_name,
            Key=s3_key
        )

        retrieved_data = json.loads(response['Body'].read())

        # Assert: Round-trip integrity
        assert retrieved_data == original_data, \
            "Retrieved data should match original exactly (no data loss)"

        assert retrieved_data['symbol'] == ticker
        assert retrieved_data['price'] == 123.45
        assert retrieved_data['volume'] == 9876543

        # Cleanup
        self.s3_client.delete_object(Bucket=self.bucket_name, Key=s3_key)

    @pytest.mark.integration
    def test_object_tagging_for_data_lineage(self):
        """
        GIVEN raw data stored with specific tags
        WHEN querying object tags
        THEN should retrieve tags for data lineage tracking
        """
        # Arrange
        ticker = 'DBS19'
        timestamp = datetime.now(timezone.utc)
        date_str = timestamp.strftime('%Y-%m-%d')
        timestamp_str = timestamp.isoformat()

        s3_key = f'raw/yfinance/{ticker}/{date_str}/{timestamp_str}.json'

        # Act: Store with comprehensive tagging
        self.s3_client.put_object(
            Bucket=self.bucket_name,
            Key=s3_key,
            Body=json.dumps({'test': 'data'}),
            Tagging=(
                f'source=yfinance&'
                f'ticker={ticker}&'
                f'fetched_at={date_str}&'
                f'purpose=integration-test'
            )
        )

        # Retrieve tags
        tag_response = self.s3_client.get_object_tagging(
            Bucket=self.bucket_name,
            Key=s3_key
        )

        # Convert tag set to dict
        tags = {tag['Key']: tag['Value'] for tag in tag_response['TagSet']}

        # Assert: Data lineage tags present
        assert 'source' in tags, "Tag 'source' required for data lineage"
        assert tags['source'] == 'yfinance', "Source should be yfinance"

        assert 'ticker' in tags, "Tag 'ticker' required for data lineage"
        assert tags['ticker'] == ticker, f"Ticker should be {ticker}"

        assert 'fetched_at' in tags, "Tag 'fetched_at' required for reproducibility"
        assert tags['fetched_at'] == date_str, "Fetched date should match"

        # Cleanup
        self.s3_client.delete_object(Bucket=self.bucket_name, Key=s3_key)

    @pytest.mark.integration
    def test_s3_versioning_enabled(self):
        """
        GIVEN S3 Data Lake bucket
        WHEN checking versioning configuration
        THEN versioning MUST be enabled (critical for data lineage)
        """
        # Act
        response = self.s3_client.get_bucket_versioning(Bucket=self.bucket_name)

        # Assert
        assert 'Status' in response, "Bucket versioning should be configured"
        assert response['Status'] == 'Enabled', \
            "Versioning MUST be enabled for data lake (data lineage requirement)"

    @pytest.mark.integration
    def test_store_multiple_versions_same_ticker(self):
        """
        GIVEN raw data for same ticker stored at different times
        WHEN storing multiple versions
        THEN each version should be independently accessible (versioning)
        """
        # Arrange
        ticker = 'AAPL19'
        date_str = datetime.now(timezone.utc).strftime('%Y-%m-%d')

        # Version 1 (morning fetch)
        morning_time = datetime.now(timezone.utc).replace(hour=9, minute=0).isoformat()
        morning_data = {'symbol': ticker, 'price': 180.50, 'time': 'morning'}

        # Version 2 (afternoon fetch)
        afternoon_time = datetime.now(timezone.utc).replace(hour=16, minute=0).isoformat()
        afternoon_data = {'symbol': ticker, 'price': 182.75, 'time': 'afternoon'}

        s3_key_morning = f'raw/yfinance/{ticker}/{date_str}/{morning_time}.json'
        s3_key_afternoon = f'raw/yfinance/{ticker}/{date_str}/{afternoon_time}.json'

        # Act: Store both versions
        self.s3_client.put_object(
            Bucket=self.bucket_name,
            Key=s3_key_morning,
            Body=json.dumps(morning_data)
        )

        self.s3_client.put_object(
            Bucket=self.bucket_name,
            Key=s3_key_afternoon,
            Body=json.dumps(afternoon_data)
        )

        # Retrieve both
        morning_response = self.s3_client.get_object(
            Bucket=self.bucket_name,
            Key=s3_key_morning
        )
        afternoon_response = self.s3_client.get_object(
            Bucket=self.bucket_name,
            Key=s3_key_afternoon
        )

        morning_retrieved = json.loads(morning_response['Body'].read())
        afternoon_retrieved = json.loads(afternoon_response['Body'].read())

        # Assert: Both versions accessible independently
        assert morning_retrieved['price'] == 180.50, \
            "Morning version should be preserved"
        assert afternoon_retrieved['price'] == 182.75, \
            "Afternoon version should be preserved"

        assert morning_retrieved['time'] == 'morning'
        assert afternoon_retrieved['time'] == 'afternoon'

        # Cleanup
        self.s3_client.delete_object(Bucket=self.bucket_name, Key=s3_key_morning)
        self.s3_client.delete_object(Bucket=self.bucket_name, Key=s3_key_afternoon)

    @pytest.mark.integration
    def test_list_raw_data_by_ticker_prefix(self):
        """
        GIVEN multiple raw data objects for different tickers
        WHEN listing objects by ticker prefix
        THEN should retrieve only objects for that ticker (querying pattern)
        """
        # Arrange
        ticker1 = 'PTT19'
        ticker2 = 'AOT19'
        date_str = datetime.now(timezone.utc).strftime('%Y-%m-%d')
        timestamp = datetime.now(timezone.utc).isoformat()

        key1 = f'raw/yfinance/{ticker1}/{date_str}/{timestamp}-1.json'
        key2 = f'raw/yfinance/{ticker2}/{date_str}/{timestamp}-2.json'

        # Store two different tickers
        self.s3_client.put_object(
            Bucket=self.bucket_name,
            Key=key1,
            Body=json.dumps({'symbol': ticker1})
        )

        self.s3_client.put_object(
            Bucket=self.bucket_name,
            Key=key2,
            Body=json.dumps({'symbol': ticker2})
        )

        # Act: List objects for ticker1 only
        response = self.s3_client.list_objects_v2(
            Bucket=self.bucket_name,
            Prefix=f'raw/yfinance/{ticker1}/'
        )

        # Assert: Only ticker1 objects returned
        assert response['KeyCount'] >= 1, f"Should find at least 1 object for {ticker1}"

        keys = [obj['Key'] for obj in response.get('Contents', [])]
        assert any(ticker1 in key for key in keys), \
            f"Results should contain {ticker1}"
        assert not any(ticker2 in key for key in keys), \
            f"Results should NOT contain {ticker2}"

        # Cleanup
        self.s3_client.delete_object(Bucket=self.bucket_name, Key=key1)
        self.s3_client.delete_object(Bucket=self.bucket_name, Key=key2)

    @pytest.mark.integration
    def test_s3_key_structure_follows_convention(self):
        """
        GIVEN S3 Data Lake key structure convention
        WHEN storing objects
        THEN should follow pattern: raw/yfinance/{ticker}/{date}/{timestamp}.json
        """
        # Arrange
        ticker = 'STRUCTURE_TEST'
        timestamp = datetime.now(timezone.utc)
        date_str = timestamp.strftime('%Y-%m-%d')
        timestamp_str = timestamp.isoformat()

        # Act: Generate key following convention
        s3_key = f'raw/yfinance/{ticker}/{date_str}/{timestamp_str}.json'

        # Assert: Key structure validation
        assert s3_key.startswith('raw/yfinance/'), \
            "Key should start with 'raw/yfinance/' prefix"

        assert f'/{ticker}/' in s3_key, \
            "Key should contain ticker directory"

        assert f'/{date_str}/' in s3_key, \
            "Key should contain date directory for partitioning"

        assert s3_key.endswith('.json'), \
            "Key should end with .json extension"

        # Verify key is parseable (extract components)
        parts = s3_key.split('/')
        assert parts[0] == 'raw', "First component should be 'raw'"
        assert parts[1] == 'yfinance', "Second component should be 'yfinance'"
        assert parts[2] == ticker, "Third component should be ticker"
        assert parts[3] == date_str, "Fourth component should be date"

    @pytest.mark.integration
    def test_s3_encryption_enabled(self):
        """
        GIVEN S3 Data Lake bucket
        WHEN checking encryption configuration
        THEN server-side encryption MUST be enabled
        """
        # Act
        response = self.s3_client.get_bucket_encryption(Bucket=self.bucket_name)

        # Assert
        assert 'ServerSideEncryptionConfiguration' in response, \
            "Bucket must have encryption configuration"

        rules = response['ServerSideEncryptionConfiguration']['Rules']
        assert len(rules) > 0, "Bucket must have at least one encryption rule"

        algorithm = rules[0]['ApplyServerSideEncryptionByDefault']['SSEAlgorithm']
        assert algorithm in ['AES256', 'aws:kms'], \
            "Bucket must use either SSE-S3 (AES256) or SSE-KMS encryption"

    @pytest.mark.integration
    def test_store_processed_indicators_with_data_lineage(self):
        """
        GIVEN computed indicators with source raw data link
        WHEN storing to S3 Data Lake Phase 2
        THEN should store with correct structure and tags linking to raw data
        """
        # Arrange
        ticker = 'NVDA19'
        timestamp = datetime.now(timezone.utc)
        date_str = timestamp.strftime('%Y-%m-%d')
        timestamp_str = timestamp.strftime('%Y%m%d_%H%M%S')

        indicators = {
            'sma_20': 150.5,
            'sma_50': 145.2,
            'rsi_14': 65.3,
            'macd': 2.5
        }

        # Simulate source raw data key (from Phase 1)
        source_raw_key = f'raw/yfinance/{ticker}/{date_str}/{timestamp_str}.json'

        # Key structure: processed/indicators/{ticker}/{date}/{timestamp}.json
        s3_key = f'processed/indicators/{ticker}/{date_str}/{timestamp_str}.json'

        # Act: Store processed indicators with data lineage
        self.s3_client.put_object(
            Bucket=self.bucket_name,
            Key=s3_key,
            Body=json.dumps(indicators),
            ContentType='application/json',
            Tagging=(
                f'source=computed&'
                f'ticker={ticker}&'
                f'computed_at={date_str}&'
                f'computation_type=indicators&'
                f'source_raw_data={source_raw_key}'
            ),
            Metadata={
                'computed_at': timestamp.isoformat(),
                'source': 'indicators_computation',
                'ticker': ticker,
                'source_raw_data_key': source_raw_key,
                'computation_version': '1.0',
                'data_classification': 'computed-data'
            }
        )

        # Assert: Verify object exists
        response = self.s3_client.head_object(
            Bucket=self.bucket_name,
            Key=s3_key
        )

        assert response['ResponseMetadata']['HTTPStatusCode'] == 200, \
            "Processed indicators should be stored successfully"

        # Verify tags contain data lineage link
        tag_response = self.s3_client.get_object_tagging(
            Bucket=self.bucket_name,
            Key=s3_key
        )
        tags = {tag['Key']: tag['Value'] for tag in tag_response['TagSet']}

        assert tags['source'] == 'computed', \
            "Tag should indicate computed source"
        assert tags['ticker'] == ticker, \
            f"Tag should contain ticker={ticker}"
        assert tags['source_raw_data'] == source_raw_key, \
            "Tag should link to source raw data (data lineage)"

        # Verify metadata
        metadata = response['Metadata']
        assert metadata['source'] == 'indicators_computation', \
            "Metadata should indicate indicators computation"
        assert metadata['source_raw_data_key'] == source_raw_key, \
            "Metadata should contain source raw data key"

        # Cleanup
        self.s3_client.delete_object(Bucket=self.bucket_name, Key=s3_key)

    @pytest.mark.integration
    def test_store_processed_percentiles_with_data_lineage(self):
        """
        GIVEN computed percentiles with source raw data link
        WHEN storing to S3 Data Lake Phase 2
        THEN should store with correct structure and tags linking to raw data
        """
        # Arrange
        ticker = 'DBS19'
        timestamp = datetime.now(timezone.utc)
        date_str = timestamp.strftime('%Y-%m-%d')
        timestamp_str = timestamp.strftime('%Y%m%d_%H%M%S')

        percentiles = {
            'current_price_percentile': 75.5,
            'rsi_percentile': 68.2,
            'macd_percentile': 55.0
        }

        source_raw_key = f'raw/yfinance/{ticker}/{date_str}/{timestamp_str}.json'
        s3_key = f'processed/percentiles/{ticker}/{date_str}/{timestamp_str}.json'

        # Act: Store processed percentiles
        self.s3_client.put_object(
            Bucket=self.bucket_name,
            Key=s3_key,
            Body=json.dumps(percentiles),
            ContentType='application/json',
            Tagging=(
                f'source=computed&'
                f'ticker={ticker}&'
                f'computed_at={date_str}&'
                f'computation_type=percentiles&'
                f'source_raw_data={source_raw_key}'
            ),
            Metadata={
                'computed_at': timestamp.isoformat(),
                'source': 'percentiles_computation',
                'ticker': ticker,
                'source_raw_data_key': source_raw_key,
                'computation_version': '1.0'
            }
        )

        # Assert: Verify tags link to source
        tag_response = self.s3_client.get_object_tagging(
            Bucket=self.bucket_name,
            Key=s3_key
        )
        tags = {tag['Key']: tag['Value'] for tag in tag_response['TagSet']}

        assert tags['source_raw_data'] == source_raw_key, \
            "Percentiles should link to source raw data via tags"

        # Cleanup
        self.s3_client.delete_object(Bucket=self.bucket_name, Key=s3_key)

    @pytest.mark.integration
    def test_data_lineage_roundtrip(self):
        """
        GIVEN raw data stored in Phase 1
        WHEN storing processed indicators in Phase 2 with source link
        THEN should be able to trace processed data back to raw source
        """
        # Arrange: Store raw data (Phase 1)
        ticker = 'PTT19'
        timestamp = datetime.now(timezone.utc)
        date_str = timestamp.strftime('%Y-%m-%d')
        raw_timestamp = timestamp.strftime('%Y%m%d_%H%M%S')

        raw_data = {'symbol': ticker, 'price': 50.25}
        raw_key = f'raw/yfinance/{ticker}/{date_str}/{raw_timestamp}.json'

        self.s3_client.put_object(
            Bucket=self.bucket_name,
            Key=raw_key,
            Body=json.dumps(raw_data),
            ContentType='application/json'
        )

        # Act: Store processed data with link to raw (Phase 2)
        processed_timestamp = timestamp.strftime('%Y%m%d_%H%M%S')
        indicators = {'sma_20': 50.5}
        processed_key = f'processed/indicators/{ticker}/{date_str}/{processed_timestamp}.json'

        self.s3_client.put_object(
            Bucket=self.bucket_name,
            Key=processed_key,
            Body=json.dumps(indicators),
            ContentType='application/json',
            Tagging=f'source=computed&ticker={ticker}&source_raw_data={raw_key}'
        )

        # Assert: Can retrieve source raw data from processed data tags
        tag_response = self.s3_client.get_object_tagging(
            Bucket=self.bucket_name,
            Key=processed_key
        )
        tags = {tag['Key']: tag['Value'] for tag in tag_response['TagSet']}
        source_key = tags['source_raw_data']

        # Verify source raw data exists
        raw_response = self.s3_client.head_object(
            Bucket=self.bucket_name,
            Key=source_key
        )
        assert raw_response['ResponseMetadata']['HTTPStatusCode'] == 200, \
            "Should be able to retrieve source raw data via lineage link"

        # Cleanup
        self.s3_client.delete_object(Bucket=self.bucket_name, Key=raw_key)
        self.s3_client.delete_object(Bucket=self.bucket_name, Key=processed_key)
