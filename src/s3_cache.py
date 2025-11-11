"""
S3-based persistent cache for ticker reports, PDFs, and related data.

This module provides a persistent caching layer using S3 that works across
all Lambda instances, solving the ephemeral /tmp storage limitation.

Cache Structure:
    s3://bucket/cache/reports/{ticker}/{date}/report.json
    s3://bucket/cache/reports/{ticker}/{date}/chart.b64
    s3://bucket/cache/reports/{ticker}/{date}/news.json
    s3://bucket/cache/ticker_data/{ticker}/{date}/data.json
    s3://bucket/reports/{ticker}/{date}.pdf (existing PDF storage)
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


class S3Cache:
    """Persistent S3-based cache for ticker reports and related data."""

    def __init__(self, bucket_name: str, ttl_hours: int = 24):
        """
        Initialize S3 cache manager.

        Args:
            bucket_name: S3 bucket name for cache storage
            ttl_hours: Cache TTL in hours (default: 24)
        """
        self.bucket_name = bucket_name
        self.ttl_hours = ttl_hours
        self.s3_client = boto3.client('s3')
        logger.info(f"S3Cache initialized with bucket: {bucket_name}, TTL: {ttl_hours}h")

    def _get_cache_key(self, cache_type: str, ticker: str, date: str, filename: str = None) -> str:
        """
        Generate S3 cache key.

        Args:
            cache_type: Type of cache (reports, ticker_data, etc.)
            ticker: Ticker symbol
            date: Date string (YYYY-MM-DD)
            filename: Optional filename (e.g., report.json, chart.b64)

        Returns:
            S3 key path
        """
        if filename:
            return f"cache/{cache_type}/{ticker}/{date}/{filename}"
        return f"cache/{cache_type}/{ticker}/{date}"

    def _is_expired(self, metadata: Dict[str, str]) -> bool:
        """
        Check if cached object has expired based on metadata.

        Args:
            metadata: S3 object metadata

        Returns:
            True if expired, False otherwise
        """
        expires_at_str = metadata.get('expires-at')
        if not expires_at_str:
            # No expiration metadata, assume expired for safety
            return True

        try:
            expires_at = datetime.fromisoformat(expires_at_str)
            return datetime.now() > expires_at
        except (ValueError, TypeError):
            logger.warning(f"Invalid expires-at metadata: {expires_at_str}")
            return True

    def _get_expiration_metadata(self) -> Dict[str, str]:
        """
        Generate expiration metadata for cache objects.

        Returns:
            Metadata dict with expires-at timestamp
        """
        expires_at = datetime.now() + timedelta(hours=self.ttl_hours)
        return {'expires-at': expires_at.isoformat()}

    def check_exists(self, cache_type: str, ticker: str, date: str, filename: str = None) -> bool:
        """
        Fast existence check using HEAD request (no data transfer).

        Args:
            cache_type: Type of cache
            ticker: Ticker symbol
            date: Date string
            filename: Optional filename

        Returns:
            True if exists and not expired, False otherwise
        """
        key = self._get_cache_key(cache_type, ticker, date, filename)

        try:
            response = self.s3_client.head_object(
                Bucket=self.bucket_name,
                Key=key
            )

            # Check expiration
            metadata = response.get('Metadata', {})
            if self._is_expired(metadata):
                logger.info(f"Cache expired: {key}")
                return False

            logger.debug(f"Cache exists: {key}")
            return True

        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                logger.debug(f"Cache miss: {key}")
                return False
            else:
                logger.error(f"S3 HEAD error for {key}: {e}")
                return False

    def get_json(self, cache_type: str, ticker: str, date: str, filename: str) -> Optional[Dict[str, Any]]:
        """
        Get JSON data from S3 cache.

        Args:
            cache_type: Type of cache
            ticker: Ticker symbol
            date: Date string
            filename: Filename (e.g., report.json)

        Returns:
            Cached data dict or None if not found/expired
        """
        key = self._get_cache_key(cache_type, ticker, date, filename)

        try:
            response = self.s3_client.get_object(
                Bucket=self.bucket_name,
                Key=key
            )

            # Check expiration
            metadata = response.get('Metadata', {})
            if self._is_expired(metadata):
                logger.info(f"Cache expired: {key}")
                return None

            # Parse JSON
            data = json.loads(response['Body'].read().decode('utf-8'))
            logger.info(f"✅ S3 cache hit: {key}")
            return data

        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                logger.debug(f"Cache miss: {key}")
                return None
            else:
                logger.error(f"S3 GET error for {key}: {e}")
                return None
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error for {key}: {e}")
            return None

    def put_json(self, cache_type: str, ticker: str, date: str, filename: str, data: Dict[str, Any]) -> bool:
        """
        Save JSON data to S3 cache.

        Args:
            cache_type: Type of cache
            ticker: Ticker symbol
            date: Date string
            filename: Filename (e.g., report.json)
            data: Data to cache

        Returns:
            True if successful, False otherwise
        """
        key = self._get_cache_key(cache_type, ticker, date, filename)

        try:
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=key,
                Body=json.dumps(data, ensure_ascii=False, indent=2),
                ContentType='application/json',
                Metadata=self._get_expiration_metadata()
            )
            logger.info(f"💾 S3 cache saved: {key}")
            return True

        except ClientError as e:
            logger.error(f"S3 PUT error for {key}: {e}")
            return False

    def get_text(self, cache_type: str, ticker: str, date: str, filename: str) -> Optional[str]:
        """
        Get text data from S3 cache (e.g., base64 chart).

        Args:
            cache_type: Type of cache
            ticker: Ticker symbol
            date: Date string
            filename: Filename (e.g., chart.b64)

        Returns:
            Cached text or None if not found/expired
        """
        key = self._get_cache_key(cache_type, ticker, date, filename)

        try:
            response = self.s3_client.get_object(
                Bucket=self.bucket_name,
                Key=key
            )

            # Check expiration
            metadata = response.get('Metadata', {})
            if self._is_expired(metadata):
                logger.info(f"Cache expired: {key}")
                return None

            text = response['Body'].read().decode('utf-8')
            logger.info(f"✅ S3 cache hit: {key}")
            return text

        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                logger.debug(f"Cache miss: {key}")
                return None
            else:
                logger.error(f"S3 GET error for {key}: {e}")
                return None

    def put_text(self, cache_type: str, ticker: str, date: str, filename: str, text: str) -> bool:
        """
        Save text data to S3 cache.

        Args:
            cache_type: Type of cache
            ticker: Ticker symbol
            date: Date string
            filename: Filename (e.g., chart.b64)
            text: Text data to cache

        Returns:
            True if successful, False otherwise
        """
        key = self._get_cache_key(cache_type, ticker, date, filename)

        try:
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=key,
                Body=text.encode('utf-8'),
                ContentType='text/plain',
                Metadata=self._get_expiration_metadata()
            )
            logger.info(f"💾 S3 cache saved: {key}")
            return True

        except ClientError as e:
            logger.error(f"S3 PUT error for {key}: {e}")
            return False

    # High-level convenience methods

    def get_cached_report(self, ticker: str, date: str) -> Optional[Dict[str, Any]]:
        """
        Get complete cached report for a ticker and date.

        Args:
            ticker: Ticker symbol
            date: Date string (YYYY-MM-DD)

        Returns:
            Complete report data or None
        """
        return self.get_json('reports', ticker, date, 'report.json')

    def save_report_cache(self, ticker: str, date: str, report_data: Dict[str, Any]) -> bool:
        """
        Save complete report to S3 cache.

        Args:
            ticker: Ticker symbol
            date: Date string
            report_data: Complete report data (text, context, metadata)

        Returns:
            True if successful
        """
        return self.put_json('reports', ticker, date, 'report.json', report_data)

    def get_cached_chart(self, ticker: str, date: str) -> Optional[str]:
        """
        Get cached chart image (base64).

        Args:
            ticker: Ticker symbol
            date: Date string

        Returns:
            Base64-encoded chart or None
        """
        return self.get_text('reports', ticker, date, 'chart.b64')

    def save_chart_cache(self, ticker: str, date: str, chart_b64: str) -> bool:
        """
        Save chart image to cache.

        Args:
            ticker: Ticker symbol
            date: Date string
            chart_b64: Base64-encoded chart

        Returns:
            True if successful
        """
        return self.put_text('reports', ticker, date, 'chart.b64', chart_b64)

    def get_cached_news(self, ticker: str, date: str) -> Optional[list]:
        """
        Get cached news data.

        Args:
            ticker: Ticker symbol
            date: Date string

        Returns:
            List of news items or None
        """
        return self.get_json('reports', ticker, date, 'news.json')

    def save_news_cache(self, ticker: str, date: str, news_data: list) -> bool:
        """
        Save news data to cache.

        Args:
            ticker: Ticker symbol
            date: Date string
            news_data: List of news items

        Returns:
            True if successful
        """
        return self.put_json('reports', ticker, date, 'news.json', news_data)

    def get_pdf_url(self, ticker: str, date: str) -> Optional[str]:
        """
        Generate presigned URL for existing PDF if it exists.

        Args:
            ticker: Ticker symbol
            date: Date string

        Returns:
            Presigned URL or None if PDF doesn't exist
        """
        # PDF stored in reports/ prefix (existing convention)
        pdf_key = f"reports/{ticker}/{date}.pdf"

        try:
            # Check if PDF exists
            self.s3_client.head_object(
                Bucket=self.bucket_name,
                Key=pdf_key
            )

            # Generate presigned URL (24h expiration)
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket_name, 'Key': pdf_key},
                ExpiresIn=86400  # 24 hours
            )

            logger.info(f"✅ PDF exists, generated presigned URL: {pdf_key}")
            return url

        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                logger.debug(f"PDF not found: {pdf_key}")
                return None
            else:
                logger.error(f"S3 error checking PDF {pdf_key}: {e}")
                return None
