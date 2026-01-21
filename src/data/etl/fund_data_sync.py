# -*- coding: utf-8 -*-
"""
Fund Data Sync Service

Orchestrates the complete ETL pipeline:
    S3 Event → Download CSV → Parse → Validate → Batch Upsert → Aurora

Design Principles:
- Idempotency: Can be run multiple times on same S3 object
- Fail fast: Explicit validation at each step
- Data lineage: Track S3 source through entire pipeline
- Observability: Comprehensive logging

Data Flow:
    S3 ObjectCreated event (SQS message)
    → Download CSV from S3
    → Parse CSV (encoding detection + type conversion)
    → Batch upsert to Aurora (with idempotency)
    → Success/failure response
"""

import json
import logging
from typing import Any, Dict, List, Optional

import boto3
from botocore.exceptions import ClientError

from src.data.etl.fund_data_parser import get_fund_data_parser
from src.data.aurora.fund_data_repository import get_fund_data_repository
from src.data.aurora.ticker_resolver import get_ticker_resolver

logger = logging.getLogger(__name__)


class FundDataSyncService:
    """Service for syncing fund data from S3 to Aurora.

    Orchestrates the complete ETL pipeline with proper error handling
    and data lineage tracking.

    Example:
        >>> service = FundDataSyncService()
        >>> result = service.process_s3_event({
        ...     'bucket': 'data-lake-dev',
        ...     'key': 'raw/sql_server/fund_data/2025-12-09/export.csv'
        ... })
        >>> print(f"Synced {result['records_processed']} records")
    """

    def __init__(
        self,
        s3_client: Optional[Any] = None,
        parser: Optional[Any] = None,
        repository: Optional[Any] = None,
        ticker_resolver: Optional[Any] = None,
        auto_register_tickers: bool = True
    ):
        """Initialize ETL service.

        Args:
            s3_client: boto3 S3 client (uses default if not provided)
            parser: FundDataParser instance (uses singleton if not provided)
            repository: FundDataRepository instance (uses singleton if not provided)
            ticker_resolver: TickerResolver instance (uses singleton if not provided)
            auto_register_tickers: If True, auto-register new tickers found in data
        """
        self.s3_client = s3_client or boto3.client('s3')
        self.parser = parser or get_fund_data_parser()
        self.repo = repository or get_fund_data_repository()
        self.ticker_resolver = ticker_resolver or get_ticker_resolver()
        self.auto_register_tickers = auto_register_tickers

    # =========================================================================
    # Public API
    # =========================================================================

    def process_s3_event(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Process S3 ObjectCreated event.

        Args:
            event: S3 event dictionary with 'bucket' and 'key'

        Returns:
            Result dictionary with:
                - success: bool
                - records_processed: int
                - s3_source: str
                - message: str
                - error: str (if success=False)

        Example:
            >>> event = {
            ...     'bucket': 'dr-daily-report-data-lake-dev',
            ...     'key': 'raw/sql_server/fund_data/2025-12-09/export.csv'
            ... }
            >>> result = service.process_s3_event(event)
        """
        bucket = event.get('bucket')
        key = event.get('key')

        # Validate input
        if not bucket or not key:
            return {
                'success': False,
                'error': 'Missing required fields: bucket and key',
                'records_processed': 0
            }

        logger.info(f"Processing S3 event: s3://{bucket}/{key}")

        try:
            # Step 1: Download CSV from S3
            csv_bytes = self._download_csv(bucket, key)
            logger.info(f"Downloaded {len(csv_bytes)} bytes from S3")

            # Step 2: Parse CSV
            records = self.parser.parse(csv_bytes, s3_key=key)
            logger.info(f"Parsed {len(records)} records from CSV")

            # Step 2.5: Auto-register new tickers if enabled
            registered_tickers = 0
            if self.auto_register_tickers and records:
                registered_tickers = self._ensure_tickers_registered(records)

            # Step 3: Batch upsert to Aurora
            rowcount = self.repo.batch_upsert(records)
            logger.info(f"Upserted {len(records)} records, affected {rowcount} rows")

            return {
                'success': True,
                'records_processed': len(records),
                'rows_affected': rowcount,
                'tickers_registered': registered_tickers,
                's3_source': f"s3://{bucket}/{key}",
                'message': f"Successfully synced {len(records)} records"
            }

        except Exception as e:
            logger.error(f"Failed to process S3 event: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
                'records_processed': 0,
                's3_source': f"s3://{bucket}/{key}"
            }

    def process_sqs_message(self, sqs_message: Dict[str, Any]) -> Dict[str, Any]:
        """Process SQS message containing S3 event.

        Args:
            sqs_message: SQS message body (JSON string or dict)

        Returns:
            Processing result dictionary

        Example:
            >>> message = {
            ...     'Records': [{
            ...         's3': {
            ...             'bucket': {'name': 'data-lake-dev'},
            ...             'object': {'key': 'raw/fund_data.csv'}
            ...         }
            ...     }]
            ... }
            >>> result = service.process_sqs_message(message)
        """
        # Parse SQS message body
        if isinstance(sqs_message, str):
            try:
                message_body = json.loads(sqs_message)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse SQS message JSON: {e}")
                return {
                    'success': False,
                    'error': f"Invalid JSON in SQS message: {e}",
                    'records_processed': 0
                }
        else:
            message_body = sqs_message

        # Extract S3 event from SQS message
        try:
            # S3 event notification format
            s3_records = message_body.get('Records', [])
            if not s3_records:
                return {
                    'success': False,
                    'error': 'No S3 records found in SQS message',
                    'records_processed': 0
                }

            # Process first S3 record (typically only one per SQS message)
            s3_record = s3_records[0]
            s3_info = s3_record.get('s3', {})

            bucket = s3_info.get('bucket', {}).get('name')
            key = s3_info.get('object', {}).get('key')

            if not bucket or not key:
                return {
                    'success': False,
                    'error': 'Missing bucket or key in S3 event',
                    'records_processed': 0
                }

            # Process S3 event
            return self.process_s3_event({'bucket': bucket, 'key': key})

        except Exception as e:
            logger.error(f"Failed to extract S3 event from SQS message: {e}", exc_info=True)
            return {
                'success': False,
                'error': f"Failed to parse SQS message: {e}",
                'records_processed': 0
            }

    # =========================================================================
    # Internal Methods
    # =========================================================================

    def _ensure_tickers_registered(self, records: List[Dict[str, Any]]) -> int:
        """Ensure all tickers in records are registered in ticker_master.

        Extracts unique tickers from records and registers any that are missing.

        Args:
            records: List of fund data records with 'ticker' field

        Returns:
            Number of newly registered tickers
        """
        # Extract unique tickers from records
        unique_tickers = set()
        for record in records:
            ticker = record.get('ticker')
            if ticker:
                unique_tickers.add(ticker)

        if not unique_tickers:
            return 0

        logger.info(f"Checking {len(unique_tickers)} unique tickers for registration")

        # Use ticker resolver to ensure all are registered
        results = self.ticker_resolver.ensure_tickers_registered(list(unique_tickers))

        # Count newly registered (those that succeeded and weren't already cached)
        registered_count = sum(1 for tid in results.values() if tid is not None)
        new_count = len([s for s in unique_tickers if self.ticker_resolver.resolve(s)])

        # Log results
        failed = [s for s, tid in results.items() if tid is None]
        if failed:
            logger.warning(f"Failed to register {len(failed)} tickers: {failed[:5]}...")

        return registered_count

    def _download_csv(self, bucket: str, key: str) -> bytes:
        """Download CSV file from S3.

        Args:
            bucket: S3 bucket name
            key: S3 object key

        Returns:
            CSV file content as bytes

        Raises:
            ClientError: If S3 download fails
            ValueError: If downloaded file is empty
        """
        try:
            response = self.s3_client.get_object(Bucket=bucket, Key=key)
            csv_bytes = response['Body'].read()

            # Defensive check: ensure file is not empty
            if not csv_bytes:
                raise ValueError(f"Downloaded CSV is empty: s3://{bucket}/{key}")

            return csv_bytes

        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code')
            if error_code == 'NoSuchKey':
                raise ValueError(f"S3 object not found: s3://{bucket}/{key}")
            elif error_code == 'NoSuchBucket':
                raise ValueError(f"S3 bucket not found: {bucket}")
            else:
                raise

    def validate_s3_key_format(self, key: str) -> bool:
        """Validate S3 key matches expected format.

        Expected format: raw/sql_server/fund_data/YYYY-MM-DD/*.csv

        Args:
            key: S3 object key

        Returns:
            True if format is valid

        Example:
            >>> service.validate_s3_key_format(
            ...     'raw/sql_server/fund_data/2025-12-09/export.csv'
            ... )
            True
        """
        # Expected prefix
        if not key.startswith('raw/sql_server/fund_data/'):
            logger.warning(f"S3 key does not match expected prefix: {key}")
            return False

        # Must be CSV file
        if not key.endswith('.csv'):
            logger.warning(f"S3 key is not a CSV file: {key}")
            return False

        return True


# ============================================================================
# Module-Level Singleton
# ============================================================================

_service: Optional[FundDataSyncService] = None


def get_fund_data_sync_service() -> FundDataSyncService:
    """Get or create fund data sync service singleton.

    Returns:
        FundDataSyncService instance (shared across Lambda invocations)

    Example:
        >>> service = get_fund_data_sync_service()
        >>> result = service.process_s3_event(event)
    """
    global _service
    if _service is None:
        _service = FundDataSyncService()
    return _service
