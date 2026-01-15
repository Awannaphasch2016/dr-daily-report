# -*- coding: utf-8 -*-
"""
Lambda handler for precomputing chart patterns for a single ticker.

Single Responsibility: Detect patterns for one ticker, store in Aurora.

Architecture: Called by Step Functions Map state (one invocation per ticker).
Similar pattern to report_worker_handler.py.

Triggered by: Step Functions precompute workflow (daily after market close)

Design:
    - Uses PatternDetectionService for detection (registry-based with fallback)
    - Stores results in chart_pattern_data table via ChartPatternRepository
    - Idempotent: ON DUPLICATE KEY UPDATE handles re-runs safely
"""

import json
import logging
import os
from datetime import date, datetime
from typing import Any, Dict

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _validate_required_config() -> None:
    """Validate required environment variables at Lambda startup.

    Defensive programming principle (CLAUDE.md #1): Validate configuration
    at startup, not on first use. Fails fast if critical config is missing.

    Raises:
        RuntimeError: If any required environment variable is missing
    
# Trigger rebuild for Step Functions pattern precompute
"""
    required_vars = {
        'TZ': 'Bangkok timezone for date handling'
    }

    missing = {var: purpose for var, purpose in required_vars.items()
               if not os.getenv(var)}

    if missing:
        error_msg = "Missing required environment variables:\n"
        for var, purpose in missing.items():
            error_msg += f"  - {var} (needed for: {purpose})\n"
        logger.error(error_msg)
        raise RuntimeError(error_msg)


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    
# Trigger rebuild for Step Functions pattern precompute
"""
    Precompute chart patterns for a single ticker.

    Event format:
        {
            "ticker": "NVDA19",
            "ticker_id": 1
        }

    Returns:
        {
            "ticker": "NVDA19",
            "patterns_found": 3,
            "patterns_stored": 3,
            "status": "success" | "error"
        }
    
# Trigger rebuild for Step Functions pattern precompute
"""
    # Validate configuration at startup
    _validate_required_config()

    start_time = datetime.now()
    ticker = event.get('ticker')
    ticker_id = event.get('ticker_id')

    logger.info(f"▶️ Pattern precompute starting: {ticker} (id={ticker_id})")

    if not ticker:
        logger.error("Missing ticker in event")
        return {
            'ticker': ticker,
            'status': 'error',
            'error': 'Missing ticker in event'
        }

    # If ticker_id not provided, look it up
    if not ticker_id:
        try:
            from src.data.aurora.repository import TickerRepository
            repo = TickerRepository()
            ticker_info = repo.get_ticker_by_symbol(ticker)
            if ticker_info:
                ticker_id = ticker_info.get('id')
            else:
                logger.warning(f"Ticker {ticker} not found in ticker_master, using placeholder")
                ticker_id = 0  # Placeholder for tickers not in master
        except Exception as e:
            logger.warning(f"Could not lookup ticker_id for {ticker}: {e}")
            ticker_id = 0

    try:
        # Import here to avoid cold start penalty if validation fails
        from src.services.pattern_detection_service import get_pattern_service
        from src.data.aurora.chart_pattern_repository import get_chart_pattern_repository

        # Detect patterns
        pattern_service = get_pattern_service()
        result = pattern_service.detect_patterns(ticker, days=180)

        patterns = result.get('patterns', [])
        logger.info(f"  Found {len(patterns)} patterns for {ticker}")

        if not patterns:
            duration = (datetime.now() - start_time).total_seconds()
            return {
                'ticker': ticker,
                'ticker_id': ticker_id,
                'patterns_found': 0,
                'patterns_stored': 0,
                'duration_seconds': duration,
                'status': 'success'
            }

        # Store patterns in Aurora
        repo = get_chart_pattern_repository()
        stored_count = 0

        for pattern in patterns:
            try:
                pattern_record = {
                    'ticker_id': ticker_id,
                    'symbol': ticker,
                    'pattern_date': date.today(),
                    'pattern_type': pattern['type'],
                    'pattern_code': _get_pattern_code(pattern['type']),
                    'implementation': pattern.get('implementation', 'custom'),
                    'impl_version': '1.0.0',
                    'confidence': pattern.get('confidence', 'medium'),
                    'start_date': pattern.get('start'),
                    'end_date': pattern.get('end'),
                    'pattern_data': {
                        'points': pattern.get('points', {}),
                        'pattern': pattern.get('pattern'),
                    }
                }

                repo.upsert(pattern_record)
                stored_count += 1
                logger.debug(f"  Stored pattern: {pattern['type']}")

            except Exception as e:
                logger.error(f"  Failed to store pattern {pattern['type']}: {e}")
                # Continue with other patterns, don't fail entire job

        duration = (datetime.now() - start_time).total_seconds()
        logger.info(f"✅ Stored {stored_count}/{len(patterns)} patterns for {ticker} in {duration:.2f}s")

        return {
            'ticker': ticker,
            'ticker_id': ticker_id,
            'patterns_found': len(patterns),
            'patterns_stored': stored_count,
            'duration_seconds': duration,
            'status': 'success'
        }

    except Exception as e:
        duration = (datetime.now() - start_time).total_seconds()
        logger.error(f"❌ Pattern precompute failed for {ticker}: {e}")
        return {
            'ticker': ticker,
            'ticker_id': ticker_id,
            'status': 'error',
            'error': str(e),
            'duration_seconds': duration
        }


def _get_pattern_code(pattern_type: str) -> str:
    """Map pattern type to short code for display.

    Args:
        pattern_type: Full pattern type string (e.g., 'bullish_flag')

    Returns:
        Short code (e.g., 'FLAGU')
    
# Trigger rebuild for Step Functions pattern precompute
"""
    codes = {
        'bullish_flag': 'FLAGU',
        'bearish_flag': 'FLAGD',
        'head_shoulders': 'HS',
        'inverse_head_shoulders': 'IHS',
        'reverse_head_shoulders': 'IHS',  # Alias
        'ascending_triangle': 'TRIU',
        'descending_triangle': 'TRID',
        'symmetrical_triangle': 'TRIS',
        'triangle': 'TRI',
        'double_top': 'DTOP',
        'double_bottom': 'DBOT',
        'ascending_wedge': 'WDGU',
        'descending_wedge': 'WDGD',
        'rising_wedge': 'WDGU',  # Alias
        'falling_wedge': 'WDGD',  # Alias
        'bullish_vcp': 'VCPU',
        'bearish_vcp': 'VCPD',
        'vcp': 'VCP',
        'cup_handle': 'CUP',
    }
    return codes.get(pattern_type, pattern_type[:4].upper())


# For local testing
if __name__ == '__main__':
    import os
    os.environ['TZ'] = 'Asia/Bangkok'

    test_event = {
        'ticker': 'NVDA19',
        'ticker_id': 1
    }
    result = lambda_handler(test_event, None)
    print(json.dumps(result, indent=2))
