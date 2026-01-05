#!/usr/bin/env python3
"""
Pattern Detection API - Uses stock-pattern library for detection
Serves detected patterns as JSON for frontend visualization

Usage:
    cd /home/anak/dev/dr-daily-report_telegram
    ENV=dev doppler run -- python scripts/pattern_detection_api.py

Then access:
    http://localhost:8001/detect-patterns?ticker=DBP&days=90
"""

import sys
import os

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# Add stock-pattern library to path
sys.path.insert(0, '/tmp/stock-pattern/src')

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, List, Dict, Any
import pandas as pd
import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

# Import stock-pattern utilities
import utils as stock_pattern_utils

# Import our Aurora connection
from src.data.aurora.repository import TickerRepository

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Pattern Detection API")

# CORS for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

bangkok_tz = ZoneInfo("Asia/Bangkok")


def fetch_ohlc_data(ticker: str, days: int = 90) -> pd.DataFrame:
    """
    Fetch OHLC data from Aurora database

    Returns DataFrame with DatetimeIndex and columns: Open, High, Low, Close, Volume
    """
    repo = TickerRepository()

    # Calculate date range
    end_date = datetime.now(bangkok_tz).date()
    start_date = end_date - timedelta(days=days)

    # Fetch data as DataFrame
    df = repo.get_prices_as_dataframe(
        symbol=ticker,
        start_date=start_date,
        end_date=end_date,
        limit=days + 10  # Add buffer for weekends/holidays
    )

    if df.empty:
        raise HTTPException(status_code=404, detail=f"No data found for {ticker}")

    logger.info(f"Fetched {len(df)} bars for {ticker} from {start_date} to {end_date}")

    return df


def find_pivot_points(df: pd.DataFrame, window: int = 5) -> pd.DataFrame:
    """
    Find pivot points (local highs and lows)

    Returns DataFrame with columns: P (price), type (high/low)
    """
    pivots_data = []

    for i in range(window, len(df) - window):
        # Check if local high
        if df['High'].iloc[i] == df['High'].iloc[i-window:i+window+1].max():
            pivots_data.append({
                'date': df.index[i],
                'P': df['High'].iloc[i],
                'type': 'high'
            })
        # Check if local low
        elif df['Low'].iloc[i] == df['Low'].iloc[i-window:i+window+1].min():
            pivots_data.append({
                'date': df.index[i],
                'P': df['Low'].iloc[i],
                'type': 'low'
            })

    if not pivots_data:
        # Return empty DataFrame with correct structure
        return pd.DataFrame(columns=['P', 'type'])

    pivots_df = pd.DataFrame(pivots_data)
    pivots_df.set_index('date', inplace=True)

    logger.info(f"Found {len(pivots_df)} pivot points")

    return pivots_df


def detect_all_patterns(ticker: str, df: pd.DataFrame) -> List[Dict[str, Any]]:
    """
    Run all pattern detection functions from stock-pattern library

    Returns list of detected patterns with metadata
    """
    patterns = []

    # Find pivot points first (required for pattern detection)
    pivots = find_pivot_points(df)

    if len(pivots) < 3:
        logger.warning("Insufficient pivot points for pattern detection")
        return patterns

    # Configuration for pattern detection
    config = {
        'FLAG_MAX_BARS': 5,
        'VCP_MAX_BARS': 10,
    }

    logger.info(f"Running pattern detection for {ticker}...")

    # 1. Bullish Flag
    try:
        flag_result = stock_pattern_utils.find_bullish_flag(ticker, df, pivots, config)
        if flag_result:
            patterns.append({
                'type': 'bullish_flag',
                'data': stock_pattern_utils.make_serializable(flag_result)
            })
            logger.info("✅ Bullish Flag detected")
    except Exception as e:
        logger.error(f"Error detecting bullish flag: {e}")

    # 2. Bearish Flag
    try:
        flag_result = stock_pattern_utils.find_bearish_flag(ticker, df, pivots, config)
        if flag_result:
            patterns.append({
                'type': 'bearish_flag',
                'data': stock_pattern_utils.make_serializable(flag_result)
            })
            logger.info("✅ Bearish Flag detected")
    except Exception as e:
        logger.error(f"Error detecting bearish flag: {e}")

    # 3. Triangles
    try:
        triangle_result = stock_pattern_utils.find_triangles(ticker, df, pivots, config)
        if triangle_result:
            patterns.append({
                'type': 'triangle',
                'data': stock_pattern_utils.make_serializable(triangle_result)
            })
            logger.info("✅ Triangle detected")
    except Exception as e:
        logger.error(f"Error detecting triangle: {e}")

    # 4. Double Bottom
    try:
        # Check if function exists
        if hasattr(stock_pattern_utils, 'find_double_bottom'):
            dbot_result = stock_pattern_utils.find_double_bottom(ticker, df, pivots, config)
            if dbot_result:
                patterns.append({
                    'type': 'double_bottom',
                    'data': stock_pattern_utils.make_serializable(dbot_result)
                })
                logger.info("✅ Double Bottom detected")
    except Exception as e:
        logger.error(f"Error detecting double bottom: {e}")

    # 5. Double Top
    try:
        if hasattr(stock_pattern_utils, 'find_double_top'):
            dtop_result = stock_pattern_utils.find_double_top(ticker, df, pivots, config)
            if dtop_result:
                patterns.append({
                    'type': 'double_top',
                    'data': stock_pattern_utils.make_serializable(dtop_result)
                })
                logger.info("✅ Double Top detected")
    except Exception as e:
        logger.error(f"Error detecting double top: {e}")

    logger.info(f"Detected {len(patterns)} pattern(s)")

    return patterns


@app.get("/")
def root():
    """API info"""
    return {
        "name": "Pattern Detection API",
        "description": "Uses stock-pattern library for pattern detection",
        "endpoints": {
            "/detect-patterns": "Detect patterns for a ticker",
            "/health": "Health check"
        }
    }


@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.now(bangkok_tz).isoformat()}


@app.get("/detect-patterns")
def detect_patterns(
    ticker: str = Query(..., description="Stock ticker symbol (e.g., DBP, DBS, AAPL)"),
    days: int = Query(90, ge=30, le=365, description="Number of days of historical data")
):
    """
    Detect chart patterns using stock-pattern library

    Args:
        ticker: Stock ticker symbol
        days: Number of days of historical data to analyze

    Returns:
        {
            "ticker": "DBP",
            "data_range": {"start": "2024-10-01", "end": "2024-12-30"},
            "bars": 90,
            "patterns": [
                {
                    "type": "bullish_flag",
                    "data": {
                        "pattern": "FLAGU",
                        "points": {"A": [...], "B": [...], "C": [...]},
                        ...
                    }
                }
            ]
        }
    """
    try:
        # Fetch OHLC data
        df = fetch_ohlc_data(ticker, days)

        # Detect patterns
        patterns = detect_all_patterns(ticker, df)

        return {
            "ticker": ticker,
            "data_range": {
                "start": df.index[0].strftime("%Y-%m-%d"),
                "end": df.index[-1].strftime("%Y-%m-%d")
            },
            "bars": len(df),
            "patterns": patterns,
            "ohlc_data": [
                {
                    "date": date.strftime("%Y-%m-%d"),
                    "open": float(row['Open']),
                    "high": float(row['High']),
                    "low": float(row['Low']),
                    "close": float(row['Close']),
                    "volume": int(row['Volume'])
                }
                for date, row in df.iterrows()
            ]
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error detecting patterns: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Pattern detection failed: {str(e)}")


if __name__ == "__main__":
    import uvicorn

    logger.info("Starting Pattern Detection API on http://localhost:8001")
    logger.info("Example: http://localhost:8001/detect-patterns?ticker=DBP&days=90")

    uvicorn.run(app, host="0.0.0.0", port=8001, log_level="info")
