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
from datetime import datetime
from typing import Optional, Dict, Any
import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


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

    def is_enabled(self) -> bool:
        """
        Check if data lake storage is enabled.

        Returns:
            True if bucket is configured, False otherwise
        """
        return self.enabled
