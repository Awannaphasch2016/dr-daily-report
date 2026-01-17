# -*- coding: utf-8 -*-
"""
Static API Generator

Generates static JSON files from Aurora data and uploads to S3 for CloudFront CDN serving.
Eliminates Lambda/Aurora load for read-heavy traffic during demo phase.

Architecture:
    Aurora (source of truth) → StaticAPIGenerator → S3 → CloudFront → Frontend

Generated Files:
    api/v1/rankings.json          - All rankings (top_gainers, top_losers, etc.)
    api/v1/reports/{ticker}.json  - Individual ticker reports
    api/v1/patterns/{ticker}.json - Chart pattern data
    api/v1/metadata.json          - Generation timestamp and ticker list

Usage:
    from src.data.static_api_generator import StaticAPIGenerator

    generator = StaticAPIGenerator()
    result = generator.generate_all()
    # Returns: {'files_generated': 48, 'upload_success': True, ...}
"""

import json
import logging
import os
from datetime import date, datetime
from typing import Any, Dict, List, Optional

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


class StaticAPIGenerator:
    """Generates and uploads static JSON API files to S3."""

    def __init__(self, bucket_name: Optional[str] = None):
        """Initialize the static API generator.

        Args:
            bucket_name: S3 bucket name. If not provided, reads from
                        STATIC_API_BUCKET environment variable.
        """
        self.bucket_name = bucket_name or os.environ.get('STATIC_API_BUCKET')
        self._s3_client = None

        if not self.bucket_name:
            logger.warning(
                "STATIC_API_BUCKET not set. Static API generation will be disabled. "
                "Set STATIC_API_BUCKET environment variable to enable."
            )

    @property
    def s3_client(self):
        """Lazy-initialize S3 client."""
        if self._s3_client is None:
            self._s3_client = boto3.client('s3')
        return self._s3_client

    def is_enabled(self) -> bool:
        """Check if static API generation is enabled."""
        return self.bucket_name is not None

    # =========================================================================
    # Data Fetchers (from Aurora)
    # =========================================================================

    def _fetch_all_tickers(self) -> List[Dict[str, Any]]:
        """Fetch all active tickers from Aurora.

        Returns:
            List of ticker info dicts with id, symbol, yahoo_symbol, name
        """
        from src.data.aurora.ticker_resolver import get_ticker_resolver

        resolver = get_ticker_resolver()

        # Get all tickers from ticker_master via TickerResolver
        ticker_infos = resolver.get_all_tickers()

        # Convert TickerInfo objects to dicts
        tickers = [
            {
                'id': t.ticker_id,
                'symbol': t.dr_symbol,
                'yahoo_symbol': t.yahoo_symbol,
                'name': t.company_name,
            }
            for t in ticker_infos
        ]
        logger.info(f"Fetched {len(tickers)} tickers from Aurora")

        return tickers

    def _fetch_rankings_data(self) -> Dict[str, Any]:
        """Fetch rankings data from Aurora precomputed reports.

        Uses precomputed comparative_features to calculate rankings
        without hitting external APIs.

        Returns:
            Dict with rankings categories
        """
        from src.data.aurora.client import get_aurora_client
        from src.data.aurora.table_names import COMPARATIVE_FEATURES, PRECOMPUTED_REPORTS

        client = get_aurora_client()
        today = date.today()

        # Query comparative features for all tickers
        # Note: COLLATE needed due to collation mismatch between tables
        query = f"""
            SELECT
                cf.symbol,
                cf.daily_return,
                cf.weekly_return,
                cf.monthly_return,
                cf.volatility_30d,
                pr.report_json
            FROM {COMPARATIVE_FEATURES} cf
            LEFT JOIN {PRECOMPUTED_REPORTS} pr
                ON cf.symbol COLLATE utf8mb4_unicode_ci = pr.symbol COLLATE utf8mb4_unicode_ci
                AND pr.report_date = %s
            WHERE cf.feature_date = %s
            ORDER BY cf.symbol
        """

        results = client.fetch_all(query, (today, today))
        logger.info(f"Fetched {len(results)} tickers for rankings")

        if not results:
            logger.warning("No comparative features found for today")
            return {'top_gainers': [], 'top_losers': [], 'volume_surge': [], 'trending': []}

        # Calculate rankings from precomputed data
        ticker_data = []
        for row in results:
            # Parse report_json if available
            report_json = row.get('report_json')
            if isinstance(report_json, str):
                try:
                    report_json = json.loads(report_json)
                except json.JSONDecodeError:
                    report_json = {}

            # Extract data for rankings
            daily_return = row.get('daily_return') or 0
            ticker_data.append({
                'ticker': row['symbol'],
                'company_name': report_json.get('company_name', row['symbol']),
                'price': report_json.get('indicators', {}).get('current_price', 0),
                'price_change_pct': round(daily_return * 100, 2),
                'currency': 'USD',  # Default, actual from report_json if available
                'volume_ratio': report_json.get('indicators', {}).get('volume_ratio', 1.0),
            })

        # Calculate each ranking category
        rankings = {
            'top_gainers': sorted(
                [t for t in ticker_data if t['price_change_pct'] > 0],
                key=lambda x: x['price_change_pct'],
                reverse=True
            )[:10],
            'top_losers': sorted(
                [t for t in ticker_data if t['price_change_pct'] < 0],
                key=lambda x: x['price_change_pct']
            )[:10],
            'volume_surge': sorted(
                [t for t in ticker_data if t['volume_ratio'] > 1.5],
                key=lambda x: x['volume_ratio'],
                reverse=True
            )[:10],
            'trending': sorted(
                ticker_data,
                key=lambda x: abs(x['price_change_pct']) + x['volume_ratio'],
                reverse=True
            )[:10],
        }

        return rankings

    def _fetch_report_data(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Fetch precomputed report for a ticker.

        Args:
            symbol: Ticker symbol

        Returns:
            Report data dict or None if not found
        """
        from src.data.aurora.precompute_service import PrecomputeService

        service = PrecomputeService()
        cached = service.get_cached_report(symbol, date.today())

        if not cached:
            logger.debug(f"No cached report for {symbol}")
            return None

        # Parse report_json
        report_json = cached.get('report_json')
        if isinstance(report_json, str):
            try:
                report_json = json.loads(report_json)
            except json.JSONDecodeError:
                report_json = {}

        return {
            'symbol': symbol,
            'report_date': str(cached.get('report_date', date.today())),
            'report_text': cached.get('report_text', ''),
            'indicators': report_json.get('indicators', {}),
            'user_facing_scores': report_json.get('user_facing_scores', {}),
            'price_history': report_json.get('price_history', []),
            'projections': report_json.get('projections', []),
            'stance': report_json.get('stance', 'neutral'),
            'chart_base64': cached.get('chart_base64', ''),
        }

    def _fetch_pattern_data(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Fetch chart pattern data for a ticker.

        Args:
            symbol: Ticker symbol

        Returns:
            Pattern data dict or None if not found
        """
        from src.data.aurora.client import get_aurora_client
        from src.data.aurora.table_names import CHART_PATTERN_DATA

        client = get_aurora_client()
        today = date.today()

        # Query chart patterns from chart_pattern_data table
        query = f"""
            SELECT pattern_type, pattern_data, pattern_date, confidence
            FROM {CHART_PATTERN_DATA}
            WHERE symbol = %s AND pattern_date = %s
        """

        try:
            results = client.fetch_all(query, (symbol, today))
        except Exception as e:
            # Table might not exist yet in some environments
            logger.warning(f"Could not fetch patterns for {symbol}: {e}")
            return None

        if not results:
            return None

        patterns = []
        for row in results:
            pattern_data = row.get('pattern_data')
            if isinstance(pattern_data, str):
                try:
                    pattern_data = json.loads(pattern_data)
                except json.JSONDecodeError:
                    pattern_data = {}

            patterns.append({
                'pattern_type': row['pattern_type'],
                'confidence_score': row.get('confidence', 0),
                'pattern_date': str(row.get('pattern_date', today)),
                'data': pattern_data,
            })

        return {
            'symbol': symbol,
            'patterns': patterns,
            'pattern_date': str(today),
        }

    # =========================================================================
    # JSON Generators
    # =========================================================================

    def generate_rankings_json(self) -> Dict[str, Any]:
        """Generate rankings.json content.

        Returns:
            Dict with all ranking categories and metadata
        """
        rankings = self._fetch_rankings_data()

        return {
            'generated_at': datetime.utcnow().isoformat() + 'Z',
            'rankings': rankings,
            'categories': list(rankings.keys()),
        }

    def generate_report_json(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Generate individual report JSON content.

        Args:
            symbol: Ticker symbol

        Returns:
            Report data dict or None if not available
        """
        report = self._fetch_report_data(symbol)

        if not report:
            return None

        report['generated_at'] = datetime.utcnow().isoformat() + 'Z'
        return report

    def generate_pattern_json(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Generate pattern JSON content for a ticker.

        Args:
            symbol: Ticker symbol

        Returns:
            Pattern data dict or None if not available
        """
        patterns = self._fetch_pattern_data(symbol)

        if not patterns:
            return None

        patterns['generated_at'] = datetime.utcnow().isoformat() + 'Z'
        return patterns

    def generate_metadata_json(self, tickers: List[Dict]) -> Dict[str, Any]:
        """Generate metadata.json content.

        Args:
            tickers: List of ticker info dicts

        Returns:
            Metadata dict
        """
        return {
            'generated_at': datetime.utcnow().isoformat() + 'Z',
            'ticker_count': len(tickers),
            'tickers': [t.get('symbol') for t in tickers],
            'version': 'v1',
            'ttl_seconds': 86400,  # 24 hours
        }

    def generate_error_json(self) -> Dict[str, Any]:
        """Generate error/not-found.json content."""
        return {
            'error': 'not_found',
            'message': 'The requested resource was not found',
            'generated_at': datetime.utcnow().isoformat() + 'Z',
        }

    # =========================================================================
    # S3 Upload
    # =========================================================================

    def _upload_json(self, key: str, data: Dict[str, Any]) -> bool:
        """Upload JSON data to S3.

        Args:
            key: S3 object key (e.g., 'api/v1/rankings.json')
            data: Dict to serialize as JSON

        Returns:
            True if upload succeeded, False otherwise
        """
        if not self.is_enabled():
            logger.warning("Static API disabled - skipping upload")
            return False

        try:
            json_content = json.dumps(data, ensure_ascii=False, indent=None)

            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=key,
                Body=json_content.encode('utf-8'),
                ContentType='application/json',
                CacheControl='public, max-age=86400',  # 24 hours
            )

            logger.debug(f"Uploaded {key} ({len(json_content)} bytes)")
            return True

        except ClientError as e:
            logger.error(f"Failed to upload {key}: {e}")
            return False

    # =========================================================================
    # Main Generation Methods
    # =========================================================================

    def generate_all(self) -> Dict[str, Any]:
        """Generate and upload all static API files.

        Returns:
            Dict with generation results:
                - files_generated: Number of files created
                - files_failed: Number of files that failed
                - upload_success: Whether all uploads succeeded
                - duration_ms: Time taken in milliseconds
        """
        import time

        if not self.is_enabled():
            return {
                'files_generated': 0,
                'files_failed': 0,
                'upload_success': False,
                'error': 'STATIC_API_BUCKET not configured',
            }

        start_time = time.time()
        files_generated = 0
        files_failed = 0

        logger.info("Starting static API generation...")

        # Fetch all tickers
        tickers = self._fetch_all_tickers()

        # 1. Generate rankings.json
        logger.info("Generating rankings.json...")
        rankings = self.generate_rankings_json()
        if self._upload_json('api/v1/rankings.json', rankings):
            files_generated += 1
        else:
            files_failed += 1

        # 2. Generate individual report JSONs
        logger.info(f"Generating reports for {len(tickers)} tickers...")
        for ticker in tickers:
            symbol = ticker.get('symbol')
            if not symbol:
                continue

            report = self.generate_report_json(symbol)
            if report:
                if self._upload_json(f'api/v1/reports/{symbol}.json', report):
                    files_generated += 1
                else:
                    files_failed += 1
            else:
                logger.debug(f"No report data for {symbol}")

        # 3. Generate pattern JSONs
        logger.info(f"Generating patterns for {len(tickers)} tickers...")
        for ticker in tickers:
            symbol = ticker.get('symbol')
            if not symbol:
                continue

            patterns = self.generate_pattern_json(symbol)
            if patterns:
                if self._upload_json(f'api/v1/patterns/{symbol}.json', patterns):
                    files_generated += 1
                else:
                    files_failed += 1

        # 4. Generate metadata.json
        logger.info("Generating metadata.json...")
        metadata = self.generate_metadata_json(tickers)
        if self._upload_json('api/v1/metadata.json', metadata):
            files_generated += 1
        else:
            files_failed += 1

        # 5. Generate error/not-found.json
        error_json = self.generate_error_json()
        if self._upload_json('api/v1/error/not-found.json', error_json):
            files_generated += 1
        else:
            files_failed += 1

        duration_ms = int((time.time() - start_time) * 1000)

        result = {
            'files_generated': files_generated,
            'files_failed': files_failed,
            'upload_success': files_failed == 0,
            'duration_ms': duration_ms,
            'ticker_count': len(tickers),
        }

        logger.info(
            f"Static API generation complete: {files_generated} files in {duration_ms}ms "
            f"({files_failed} failed)"
        )

        return result

    def invalidate_cloudfront(self, distribution_id: Optional[str] = None) -> bool:
        """Invalidate CloudFront cache after generating new files.

        Args:
            distribution_id: CloudFront distribution ID. If not provided,
                           reads from STATIC_API_CLOUDFRONT_ID env var.

        Returns:
            True if invalidation was created, False otherwise
        """
        dist_id = distribution_id or os.environ.get('STATIC_API_CLOUDFRONT_ID')

        if not dist_id:
            logger.warning("STATIC_API_CLOUDFRONT_ID not set - skipping invalidation")
            return False

        try:
            cf_client = boto3.client('cloudfront')

            cf_client.create_invalidation(
                DistributionId=dist_id,
                InvalidationBatch={
                    'Paths': {
                        'Quantity': 1,
                        'Items': ['/api/v1/*']
                    },
                    'CallerReference': f'static-api-{datetime.utcnow().timestamp()}'
                }
            )

            logger.info(f"Created CloudFront invalidation for distribution {dist_id}")
            return True

        except ClientError as e:
            logger.error(f"Failed to create CloudFront invalidation: {e}")
            return False


# Singleton instance
_generator: Optional[StaticAPIGenerator] = None


def get_static_api_generator() -> StaticAPIGenerator:
    """Get or create singleton StaticAPIGenerator instance."""
    global _generator
    if _generator is None:
        _generator = StaticAPIGenerator()
    return _generator
