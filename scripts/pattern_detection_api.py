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
from fastapi.responses import FileResponse
from typing import Optional, List, Dict, Any
import pandas as pd
import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from pathlib import Path

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
    Fetch OHLC data from Aurora database, with yfinance fallback for local dev

    Returns DataFrame with DatetimeIndex and columns: Open, High, Low, Close, Volume
    """
    # Check if Aurora is available by checking for AURORA_HOST env var
    aurora_host = os.environ.get('AURORA_HOST') or os.environ.get('AURORA_SECRET_ARN')

    if aurora_host and aurora_host != 'localhost':
        # Try Aurora if configured
        try:
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

            logger.info(f"Fetched {len(df)} bars for {ticker} from Aurora")

            return df

        except Exception as aurora_error:
            logger.warning(f"Aurora fetch failed: {aurora_error}")
            # Fall through to yfinance

    # Use yfinance (either as fallback or primary for local dev)
    try:
        import yfinance as yf

        # Calculate period string for yfinance
        if days <= 30:
            period = "1mo"
        elif days <= 90:
            period = "3mo"
        elif days <= 180:
            period = "6mo"
        else:
            period = "1y"

        logger.info(f"Fetching {ticker} from yfinance (period={period})")

        # Fetch from yfinance
        df = yf.download(ticker, period=period, progress=False)

        if df.empty:
            raise HTTPException(status_code=404, detail=f"No data found for {ticker}")

        # Flatten multi-index columns if needed
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [col[0] if isinstance(col, tuple) else col for col in df.columns]

        # Keep only OHLCV columns
        df = df[['Open', 'High', 'Low', 'Close', 'Volume']]

        logger.info(f"Fetched {len(df)} bars for {ticker} from yfinance")

        return df

    except Exception as yf_error:
        logger.error(f"yfinance fetch failed: {yf_error}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch data: {str(yf_error)}")


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

    # 6. Head & Shoulders
    try:
        hns_result = stock_pattern_utils.find_hns(ticker, df, pivots, config)
        if hns_result:
            patterns.append({
                'type': 'head_and_shoulders',
                'data': stock_pattern_utils.make_serializable(hns_result)
            })
            logger.info("✅ Head & Shoulders detected")
    except Exception as e:
        logger.error(f"Error detecting H&S: {e}")

    # 7. Reverse Head & Shoulders
    try:
        rhns_result = stock_pattern_utils.find_reverse_hns(ticker, df, pivots, config)
        if rhns_result:
            patterns.append({
                'type': 'reverse_head_and_shoulders',
                'data': stock_pattern_utils.make_serializable(rhns_result)
            })
            logger.info("✅ Reverse Head & Shoulders detected")
    except Exception as e:
        logger.error(f"Error detecting reverse H&S: {e}")

    # 8. Bullish VCP (Volatility Contraction Pattern)
    try:
        vcp_result = stock_pattern_utils.find_bullish_vcp(ticker, df, pivots, config)
        if vcp_result:
            patterns.append({
                'type': 'bullish_vcp',
                'data': stock_pattern_utils.make_serializable(vcp_result)
            })
            logger.info("✅ Bullish VCP detected")
    except Exception as e:
        logger.error(f"Error detecting bullish VCP: {e}")

    # 9. Bearish VCP
    try:
        vcp_result = stock_pattern_utils.find_bearish_vcp(ticker, df, pivots, config)
        if vcp_result:
            patterns.append({
                'type': 'bearish_vcp',
                'data': stock_pattern_utils.make_serializable(vcp_result)
            })
            logger.info("✅ Bearish VCP detected")
    except Exception as e:
        logger.error(f"Error detecting bearish VCP: {e}")

    logger.info(f"Detected {len(patterns)} pattern(s)")

    return patterns


@app.get("/")
def root():
    """Serve the chart viewer HTML"""
    html_path = Path(project_root) / "standalone_chart_viewer.html"
    if html_path.exists():
        return FileResponse(html_path)
    return {
        "name": "Pattern Detection API",
        "description": "Uses stock-pattern library for pattern detection",
        "endpoints": {
            "/detect-patterns": "Detect patterns for a ticker",
            "/api/chart-data/{symbol}": "Get chart data for visualization",
            "/health": "Health check"
        }
    }


@app.get("/test_chart.html")
def test_chart():
    """Serve test chart page"""
    html_path = Path(project_root) / "test_chart.html"
    if html_path.exists():
        return FileResponse(html_path)
    raise HTTPException(status_code=404, detail="test_chart.html not found")


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


@app.get("/api/chart-data/{symbol}")
def get_chart_data(
    symbol: str,
    period: str = Query("90d", description="Time period (e.g., 30d, 90d, 180d, 1y)")
):
    """
    Get chart data with patterns for standalone_chart_viewer.html

    Returns data in format expected by Chart.js:
    {
        "ohlc": [{"x": timestamp_ms, "o": open, "h": high, "l": low, "c": close}],
        "patterns": {...}
    }
    """
    try:
        # Parse period (e.g., "90d" -> 90 days, "6mo" -> 180 days)
        period_lower = period.lower()

        if period_lower.endswith('mo'):
            # Handle "6mo" format
            days = int(period_lower[:-2]) * 30
        elif period_lower.endswith('d'):
            days = int(period_lower[:-1])
        elif period_lower.endswith('m'):
            days = int(period_lower[:-1]) * 30
        elif period_lower.endswith('y'):
            days = int(period_lower[:-1]) * 365
        else:
            # Assume days if no suffix
            days = int(period_lower)

        # Fetch OHLC data
        df = fetch_ohlc_data(symbol, days)

        # Detect patterns
        raw_patterns = detect_all_patterns(symbol, df)

        # Convert OHLC to Chart.js format (timestamps in milliseconds)
        ohlc = [
            {
                "x": int(date.timestamp() * 1000),  # milliseconds
                "o": float(row['Open']),
                "h": float(row['High']),
                "l": float(row['Low']),
                "c": float(row['Close'])
            }
            for date, row in df.iterrows()
        ]

        # Transform patterns to format expected by HTML viewer
        # Viewer expects: pattern, type, start_date, end_date, confidence
        transformed_patterns = []
        for p in raw_patterns:
            pattern_type = p.get('type', '')
            data = p.get('data', {})

            # Map API pattern types to viewer pattern types
            pattern_map = {
                'bullish_flag': 'flag_pennant',
                'bearish_flag': 'flag_pennant',
                'triangle': 'triangle',
                'head_and_shoulders': 'head_and_shoulders',
                'reverse_head_and_shoulders': 'inverse_head_and_shoulders',
                'double_bottom': 'double_bottom',
                'double_top': 'double_top',
                'bullish_vcp': 'wedge_rising',  # VCP is similar to a wedge/flag
                'bearish_vcp': 'wedge_falling',
            }

            # Determine bullish/bearish
            sentiment = 'bullish' if 'bullish' in pattern_type or pattern_type in ['reverse_head_and_shoulders', 'double_bottom'] else 'bearish'

            transformed_patterns.append({
                'pattern': pattern_map.get(pattern_type, pattern_type),
                'type': sentiment,
                'start_date': data.get('start', data.get('df_start', '')),
                'end_date': data.get('end', data.get('df_end', '')),
                'confidence': 'medium',  # stock-pattern doesn't provide confidence
                'raw_pattern': data.get('pattern', ''),  # Original pattern code (e.g., VCPU, HNSD)
                'points': data.get('points', {}),
            })

        logger.info(f"Transformed {len(transformed_patterns)} pattern(s) for viewer")

        # Format patterns for visualization (match expected structure)
        patterns = {
            "chart_patterns": transformed_patterns,
            "support_resistance": {
                "support": [],
                "resistance": []
            }
        }

        return {
            "ohlc": ohlc,
            "patterns": patterns,
            "symbol": symbol,
            "period": period
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching chart data: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to fetch chart data: {str(e)}")


if __name__ == "__main__":
    import uvicorn

    logger.info("Starting Pattern Detection API on http://localhost:8001")
    logger.info("Example: http://localhost:8001/detect-patterns?ticker=DBP&days=90")

    uvicorn.run(app, host="0.0.0.0", port=8001, log_level="info")
