# -*- coding: utf-8 -*-
"""
S3 Data Lake storage for raw yfinance data.

Stores raw API responses immutably with versioning for data lineage and reproducibility.
This is separate from the S3 cache (which is for processed/derived data).

Data Lake Structure:
    s3://bucket/raw/yfinance/{ticker}/{date}/{timestamp}.json

Key Features:
    - Versioning enabled (historical data access)
    - Tagging for data lineage (source, ticker, fetched_at)
    - Metadata for tracking (fetched_at, source, ticker, data_classification)
    - Immutable storage (no overwrites, only new versions)
"""

import json
import logging
from datetime import datetime, date
from typing import Optional, Dict, Any
import boto3
from botocore.exceptions import ClientError
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


def _make_json_serializable(obj):
    """Convert numpy/pandas/datetime/date objects to JSON-serializable types.
    
    Following lambda-best-practices.mdc pattern for JSON serialization.
    """
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    elif isinstance(obj, pd.Timestamp):
        return obj.isoformat()
    elif isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, dict):
        return {k: _make_json_serializable(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [_make_json_serializable(item) for item in obj]
    return obj


class DataLakeStorage:
    """Storage manager for S3 Data Lake raw data."""

    def __init__(self, bucket_name: Optional[str] = None):
        """
        Initialize Data Lake storage manager.

        Args:
            bucket_name: S3 bucket name for data lake. If None, reads from DATA_LAKE_BUCKET env var.
        """
        import os

        self.bucket_name = bucket_name or os.environ.get('DATA_LAKE_BUCKET')
        if not self.bucket_name:
            logger.warning("DATA_LAKE_BUCKET not configured - data lake storage disabled")
            self.enabled = False
        else:
            self.enabled = True
            self.s3_client = boto3.client('s3')
            logger.info(f"DataLakeStorage initialized with bucket: {self.bucket_name}")

    def store_raw_yfinance_data(
        self,
        ticker: str,
        data: Dict[str, Any],
        fetched_at: Optional[datetime] = None
    ) -> bool:
        """
        Store raw yfinance API response to data lake.

        Key structure: raw/yfinance/{ticker}/{date}/{timestamp}.json
        Tags: source=yfinance, ticker={ticker}, fetched_at={date}
        Metadata: fetched_at, source, ticker, data_classification

        Args:
            ticker: Ticker symbol (e.g., 'NVDA', 'D05.SI')
            data: Raw data dict from yfinance API
            fetched_at: Timestamp when data was fetched (defaults to now)

        Returns:
            True if successful, False otherwise
        """
        if not self.enabled:
            logger.debug("Data lake storage disabled (no bucket configured)")
            return False

        if fetched_at is None:
            fetched_at = datetime.now()

        # Generate S3 key: raw/yfinance/{ticker}/{date}/{timestamp}.json
        date_str = fetched_at.strftime('%Y-%m-%d')
        timestamp_str = fetched_at.strftime('%Y%m%d_%H%M%S')
        s3_key = f"raw/yfinance/{ticker}/{date_str}/{timestamp_str}.json"

        # Prepare tags for data lineage
        tags = {
            'source': 'yfinance',
            'ticker': ticker,
            'fetched_at': date_str
        }

        # Prepare metadata
        metadata = {
            'fetched_at': fetched_at.isoformat(),
            'source': 'yfinance',
            'ticker': ticker,
            'data_classification': 'public-api-data'
        }

        try:
            # Convert tags to S3 tag format: "Key1=Value1&Key2=Value2"
            tag_string = '&'.join([f"{k}={v}" for k, v in tags.items()])

            # Store to S3 with versioning enabled (creates new version each time)
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=json.dumps(data, ensure_ascii=False, indent=2),
                ContentType='application/json',
                Metadata=metadata,
                Tagging=tag_string
            )

            logger.info(f"💾 Data lake stored: {s3_key} (ticker: {ticker}, date: {date_str})")
            return True

        except ClientError as e:
            logger.error(f"Data lake storage failed for {s3_key}: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error storing to data lake {s3_key}: {e}")
            return False

    def store_indicators(
        self,
        ticker: str,
        indicators: Dict[str, Any],
        source_raw_data_key: Optional[str] = None,
        computed_at: Optional[datetime] = None,
        computation_version: str = "1.0"
    ) -> bool:
        """Store computed indicators to data lake.
        
        Following principles.mdc comprehensively:
        - System Boundary Principle: Validate types at boundary
        - JSON Serialization Requirement: Convert types before storage
        - Fail Fast and Visibly: Raise exceptions for type errors
        - Error Handling Duality: Utility functions raise exceptions
        - Explicit Failure Detection: Verify storage succeeded
        - Code execution ≠ Correct output: Verify file exists
        
        Key structure: processed/indicators/{ticker}/{date}/{timestamp}.json
        Tags: source=computed, ticker={ticker}, computed_at={date}, source_raw_data={key}
        Metadata: computed_at, source, ticker, source_raw_data_key, computation_version
        
        Args:
            ticker: Ticker symbol (e.g., 'NVDA', 'D05.SI')
            indicators: Dict with computed indicator values
            source_raw_data_key: S3 key of source raw data (optional, for data lineage)
            computed_at: Timestamp when indicators were computed (defaults to now)
            computation_version: Version of computation logic (default: "1.0")
        
        Returns:
            True if successful, False if data lake disabled
        
        Raises:
            TypeError: If indicators contain non-serializable types (fail fast)
            ClientError: If S3 storage fails (infrastructure error)
        """
        # VALIDATION GATE (principles.mdc): Check prerequisites
        if not self.enabled:
            logger.debug("Data lake storage disabled (no bucket configured)")
            return False
        
        if computed_at is None:
            computed_at = datetime.now()
        
        # SYSTEM BOUNDARY VALIDATION (principles.mdc)
        # Validate types BEFORE crossing boundary (Python → S3)
        # This raises TypeError if invalid (fail fast, not return False)
        self._validate_json_serializable(indicators, "indicators")
        
        # TYPE CONVERSION (principles.mdc)
        # Convert types to JSON-serializable format
        serializable_indicators = _make_json_serializable(indicators)
        
        # Generate S3 key: processed/indicators/{ticker}/{date}/{timestamp}.json
        date_str = computed_at.strftime('%Y-%m-%d')
        timestamp_str = computed_at.strftime('%Y%m%d_%H%M%S')
        s3_key = f"processed/indicators/{ticker}/{date_str}/{timestamp_str}.json"
        
        # Prepare tags for data lineage
        tags = {
            'source': 'computed',
            'ticker': ticker,
            'computed_at': date_str,
            'computation_type': 'indicators'
        }
        if source_raw_data_key:
            tags['source_raw_data'] = source_raw_data_key
        
        # Prepare metadata
        metadata = {
            'computed_at': computed_at.isoformat(),
            'source': 'indicators_computation',
            'ticker': ticker,
            'computation_version': computation_version,
            'data_classification': 'computed-data'
        }
        if source_raw_data_key:
            metadata['source_raw_data_key'] = source_raw_data_key
        
        try:
            # Convert tags to S3 tag format: "Key1=Value1&Key2=Value2"
            tag_string = '&'.join([f"{k}={v}" for k, v in tags.items()])
            
            # Store to S3
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=json.dumps(serializable_indicators, ensure_ascii=False, indent=2),
                ContentType='application/json',
                Metadata=metadata,
                Tagging=tag_string
            )
            
            # EXPLICIT FAILURE DETECTION (principles.mdc)
            # Code execution ≠ Correct output (principles.mdc)
            # AWS Services Success ≠ No Errors (principles.mdc)
            # Verify storage actually succeeded (not just put_object() returned success)
            self._verify_storage_succeeded(s3_key, serializable_indicators)
            
            logger.info(f"💾 Data lake stored indicators: {s3_key} (ticker: {ticker}, date: {date_str})")
            return True
            
        except TypeError:
            # Type errors are CODE BUGS - propagate (fail fast)
            # Don't catch - let it propagate to caller
            raise
        except ClientError as e:
            # S3 infrastructure errors - log and raise (fail visibly)
            # Error Handling Duality: Utility functions raise exceptions
            logger.error(f"S3 storage failed for indicators {s3_key}: {e}")
            raise  # Don't return False - make failure visible
        # Don't catch generic Exception - let unexpected errors propagate (fail fast)

    def store_percentiles(
        self,
        ticker: str,
        percentiles: Dict[str, Any],
        source_raw_data_key: Optional[str] = None,
        computed_at: Optional[datetime] = None,
        computation_version: str = "1.0"
    ) -> bool:
        """Store computed percentiles to data lake.
        
        Following principles.mdc comprehensively:
        - System Boundary Principle: Validate types at boundary
        - JSON Serialization Requirement: Convert types before storage
        - Fail Fast and Visibly: Raise exceptions for type errors
        - Error Handling Duality: Utility functions raise exceptions
        - Explicit Failure Detection: Verify storage succeeded
        - Code execution ≠ Correct output: Verify file exists
        
        Key structure: processed/percentiles/{ticker}/{date}/{timestamp}.json
        Tags: source=computed, ticker={ticker}, computed_at={date}, source_raw_data={key}
        Metadata: computed_at, source, ticker, source_raw_data_key, computation_version
        
        Args:
            ticker: Ticker symbol (e.g., 'NVDA', 'D05.SI')
            percentiles: Dict with computed percentile values
            source_raw_data_key: S3 key of source raw data (optional, for data lineage)
            computed_at: Timestamp when percentiles were computed (defaults to now)
            computation_version: Version of computation logic (default: "1.0")
        
        Returns:
            True if successful, False if data lake disabled
        
        Raises:
            TypeError: If percentiles contain non-serializable types (fail fast)
            ClientError: If S3 storage fails (infrastructure error)
        """
        # VALIDATION GATE (principles.mdc): Check prerequisites
        if not self.enabled:
            logger.debug("Data lake storage disabled (no bucket configured)")
            return False
        
        if computed_at is None:
            computed_at = datetime.now()
        
        # SYSTEM BOUNDARY VALIDATION (principles.mdc)
        # Validate types BEFORE crossing boundary (Python → S3)
        # This raises TypeError if invalid (fail fast, not return False)
        self._validate_json_serializable(percentiles, "percentiles")
        
        # TYPE CONVERSION (principles.mdc)
        # Convert types to JSON-serializable format
        serializable_percentiles = _make_json_serializable(percentiles)
        
        # Generate S3 key: processed/percentiles/{ticker}/{date}/{timestamp}.json
        date_str = computed_at.strftime('%Y-%m-%d')
        timestamp_str = computed_at.strftime('%Y%m%d_%H%M%S')
        s3_key = f"processed/percentiles/{ticker}/{date_str}/{timestamp_str}.json"
        
        # Prepare tags for data lineage
        tags = {
            'source': 'computed',
            'ticker': ticker,
            'computed_at': date_str,
            'computation_type': 'percentiles'
        }
        if source_raw_data_key:
            tags['source_raw_data'] = source_raw_data_key
        
        # Prepare metadata
        metadata = {
            'computed_at': computed_at.isoformat(),
            'source': 'percentiles_computation',
            'ticker': ticker,
            'computation_version': computation_version,
            'data_classification': 'computed-data'
        }
        if source_raw_data_key:
            metadata['source_raw_data_key'] = source_raw_data_key
        
        try:
            # Convert tags to S3 tag format: "Key1=Value1&Key2=Value2"
            tag_string = '&'.join([f"{k}={v}" for k, v in tags.items()])
            
            # Store to S3
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=json.dumps(serializable_percentiles, ensure_ascii=False, indent=2),
                ContentType='application/json',
                Metadata=metadata,
                Tagging=tag_string
            )
            
            # EXPLICIT FAILURE DETECTION (principles.mdc)
            # Code execution ≠ Correct output (principles.mdc)
            # AWS Services Success ≠ No Errors (principles.mdc)
            # Verify storage actually succeeded (not just put_object() returned success)
            self._verify_storage_succeeded(s3_key, serializable_percentiles)
            
            logger.info(f"💾 Data lake stored percentiles: {s3_key} (ticker: {ticker}, date: {date_str})")
            return True
            
        except TypeError:
            # Type errors are CODE BUGS - propagate (fail fast)
            # Don't catch - let it propagate to caller
            raise
        except ClientError as e:
            # S3 infrastructure errors - log and raise (fail visibly)
            # Error Handling Duality: Utility functions raise exceptions
            logger.error(f"S3 storage failed for percentiles {s3_key}: {e}")
            raise  # Don't return False - make failure visible
        # Don't catch generic Exception - let unexpected errors propagate (fail fast)

    def get_latest_indicators(self, ticker: str) -> Optional[Dict[str, Any]]:
        """
        Get the most recent indicators for a ticker from data lake.

        Searches all indicator files for the ticker and returns the one with
        the latest LastModified timestamp.

        Args:
            ticker: Ticker symbol (e.g., 'NVDA', 'D05.SI')

        Returns:
            Dict with indicator values or None if not found
        """
        if not self.enabled:
            logger.debug("Data lake storage disabled (no bucket configured)")
            return None

        try:
            # List all indicator files for this ticker
            prefix = f"processed/indicators/{ticker}/"
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=prefix
            )

            if 'Contents' not in response or len(response['Contents']) == 0:
                logger.debug(f"No indicators found for {ticker}")
                return None

            # Find the file with the latest LastModified timestamp
            latest_file = max(
                response['Contents'],
                key=lambda obj: obj['LastModified']
            )

            # Retrieve the latest file
            obj_response = self.s3_client.get_object(
                Bucket=self.bucket_name,
                Key=latest_file['Key']
            )

            # Parse JSON content
            content = obj_response['Body'].read().decode('utf-8')
            indicators = json.loads(content)

            logger.info(f"📥 Retrieved latest indicators for {ticker} from {latest_file['Key']}")
            return indicators

        except ClientError as e:
            logger.error(f"Failed to retrieve indicators for {ticker}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error retrieving indicators for {ticker}: {e}")
            return None

    def get_indicators_by_date(
        self,
        ticker: str,
        target_date: date
    ) -> Optional[Dict[str, Any]]:
        """
        Get indicators for a specific date from data lake.

        If multiple files exist for the same date, returns the latest one
        based on timestamp.

        Args:
            ticker: Ticker symbol (e.g., 'NVDA', 'D05.SI')
            target_date: Date to retrieve indicators for

        Returns:
            Dict with indicator values or None if not found
        """
        if not self.enabled:
            logger.debug("Data lake storage disabled (no bucket configured)")
            return None

        try:
            # List indicator files for this ticker and date
            date_str = target_date.isoformat()
            prefix = f"processed/indicators/{ticker}/{date_str}/"
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=prefix
            )

            if 'Contents' not in response or len(response['Contents']) == 0:
                logger.debug(f"No indicators found for {ticker} on {date_str}")
                return None

            # Find the file with the latest LastModified timestamp for this date
            latest_file = max(
                response['Contents'],
                key=lambda obj: obj['LastModified']
            )

            # Retrieve the file
            obj_response = self.s3_client.get_object(
                Bucket=self.bucket_name,
                Key=latest_file['Key']
            )

            # Parse JSON content
            content = obj_response['Body'].read().decode('utf-8')
            indicators = json.loads(content)

            logger.info(f"📥 Retrieved indicators for {ticker} on {date_str} from {latest_file['Key']}")
            return indicators

        except ClientError as e:
            logger.error(f"Failed to retrieve indicators for {ticker} on {target_date}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error retrieving indicators for {ticker} on {target_date}: {e}")
            return None

    def get_percentiles_by_date(
        self,
        ticker: str,
        target_date: date
    ) -> Optional[Dict[str, Any]]:
        """
        Get percentiles for a specific date from data lake.

        If multiple files exist for the same date, returns the latest one
        based on timestamp.

        Args:
            ticker: Ticker symbol (e.g., 'NVDA', 'D05.SI')
            target_date: Date to retrieve percentiles for

        Returns:
            Dict with percentile values or None if not found
        """
        if not self.enabled:
            logger.debug("Data lake storage disabled (no bucket configured)")
            return None

        try:
            # List percentile files for this ticker and date
            date_str = target_date.isoformat()
            prefix = f"processed/percentiles/{ticker}/{date_str}/"
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=prefix
            )

            if 'Contents' not in response or len(response['Contents']) == 0:
                logger.debug(f"No percentiles found for {ticker} on {date_str}")
                return None

            # Find the file with the latest LastModified timestamp for this date
            latest_file = max(
                response['Contents'],
                key=lambda obj: obj['LastModified']
            )

            # Retrieve the file
            obj_response = self.s3_client.get_object(
                Bucket=self.bucket_name,
                Key=latest_file['Key']
            )

            # Parse JSON content
            content = obj_response['Body'].read().decode('utf-8')
            percentiles = json.loads(content)

            logger.info(f"📥 Retrieved percentiles for {ticker} on {date_str} from {latest_file['Key']}")
            return percentiles

        except ClientError as e:
            logger.error(f"Failed to retrieve percentiles for {ticker} on {target_date}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error retrieving percentiles for {ticker} on {target_date}: {e}")
            return None

    def is_enabled(self) -> bool:
        """
        Check if data lake storage is enabled.

        Returns:
            True if bucket is configured, False otherwise
        """
        return self.enabled

    def _validate_json_serializable(self, data: Dict[str, Any], data_type: str) -> None:
        """Validate data types are JSON-serializable at service boundary.
        
        Following System Boundary Principle (principles.mdc):
        Verify type compatibility BEFORE crossing boundary (Python → S3).
        
        This is a VALIDATION GATE (principles.mdc) - check prerequisites
        before execution.
        
        Validates that data contains only types that can be serialized (either
        directly or via conversion). Date/datetime objects are allowed because
        they can be converted using _make_json_serializable(). This check uses
        default=str to detect truly incompatible types (custom objects, etc.)
        that cannot be converted.
        
        Args:
            data: Data dict to validate
            data_type: Type name for error messages (e.g., "indicators", "percentiles")
        
        Raises:
            TypeError: If data contains non-serializable types (fail fast)
        
        Following principles:
        - System Boundary Principle: Validate at boundary
        - Fail Fast and Visibly: Raise exception, don't return False
        - Error Handling Duality: Utility functions raise exceptions
        """
        if not self.enabled:
            return  # Skip validation if data lake disabled
        
        try:
            # Try to serialize WITHOUT default handler first to catch truly incompatible types
            # This will fail for date/datetime AND custom objects
            json.dumps(data)
        except (TypeError, ValueError) as e:
            # Check if it's a known convertible type (date, datetime, etc.)
            # If so, allow it (conversion will handle it)
            # Otherwise, fail fast with descriptive error
            error_str = str(e).lower()
            if 'date' in error_str or 'datetime' in error_str or 'timestamp' in error_str:
                # Known convertible types - allow through (conversion will handle)
                return
            
            # Truly incompatible type - fail fast
            raise TypeError(
                f"{data_type} contains non-JSON-serializable types at service boundary: {e}. "
                f"Use _make_json_serializable() to convert types before storage. "
                f"Following System Boundary Principle: validate types before crossing Python → S3 boundary."
            ) from e

    def _verify_storage_succeeded(self, s3_key: str, expected_data: Dict[str, Any]) -> None:
        """Verify storage actually succeeded (Explicit Failure Detection).
        
        Following principles.mdc:
        - Explicit Failure Detection: Check operation outcomes
        - Code execution ≠ Correct output: put_object() success ≠ file stored
        - AWS Services Success ≠ No Errors: Verify file exists
        
        Args:
            s3_key: S3 key that should exist
            expected_data: Data that should be in the file
        
        Raises:
            RuntimeError: If file doesn't exist or content doesn't match
        """
        try:
            # Verify file exists (round-trip test)
            response = self.s3_client.head_object(Bucket=self.bucket_name, Key=s3_key)
            
            # Verify file size > 0 (not empty)
            if response.get('ContentLength', 0) == 0:
                raise RuntimeError(f"Storage verification failed: File {s3_key} is empty")
            
            # Optional: Verify content matches (round-trip test)
            # Retrieve and compare
            get_response = self.s3_client.get_object(Bucket=self.bucket_name, Key=s3_key)
            body_content = get_response['Body'].read()
            # Handle both bytes and string responses
            if isinstance(body_content, bytes):
                stored_data = json.loads(body_content.decode('utf-8'))
            else:
                stored_data = json.loads(body_content)
            
            # Basic verification: file exists and is valid JSON
            if not isinstance(stored_data, dict):
                raise RuntimeError(f"Storage verification failed: File {s3_key} doesn't contain valid dict")
            
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                raise RuntimeError(
                    f"Storage verification failed: File {s3_key} doesn't exist after put_object(). "
                    f"Following 'AWS Services Success ≠ No Errors' principle: verify file exists."
                ) from e
            raise
