#!/usr/bin/env python3
"""
Test chart generation functionality
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.chart_generator import ChartGenerator
from src.data_fetcher import DataFetcher
from src.technical_analysis import TechnicalAnalyzer
import base64


def test_chart_generation_simple():
    """Test basic chart generation with a real ticker"""
    print("=" * 80)
    print("TEST: Chart Generation")
    print("=" * 80)
    print()

    # Initialize components
    print("🔧 Initializing components...")
    fetcher = DataFetcher()
    analyzer = TechnicalAnalyzer()
    chart_gen = ChartGenerator()

    # Test with AAPL
    ticker = "AAPL"
    print(f"📊 Testing with ticker: {ticker}")
    print()

    # Fetch data
    print("📥 Fetching data...")
    ticker_data = fetcher.fetch_ticker_data(ticker)

    if not ticker_data:
        print("❌ Failed to fetch data")
        return False

    print(f"✅ Fetched {len(ticker_data['history'])} days of data")

    # Get additional info
    info = fetcher.get_ticker_info(ticker)
    ticker_data.update(info)
    print(f"✅ Company: {ticker_data.get('company_name', 'N/A')}")
    print()

    # Calculate indicators
    print("📈 Calculating technical indicators...")
    hist_data = ticker_data.get('history')
    indicators = analyzer.calculate_all_indicators(hist_data)

    if not indicators:
        print("❌ Failed to calculate indicators")
        return False

    print(f"✅ Calculated indicators:")
    print(f"   - RSI: {indicators.get('rsi', 'N/A'):.2f}")
    print(f"   - MACD: {indicators.get('macd', 'N/A'):.2f}")
    print(f"   - SMA 20: {indicators.get('sma_20', 'N/A'):.2f}")
    print()

    # Generate chart
    print("📊 Generating chart...")
    try:
        chart_base64 = chart_gen.generate_chart(
            ticker_data=ticker_data,
            indicators=indicators,
            ticker_symbol=ticker,
            days=90
        )

        print("✅ Chart generated successfully!")
        print(f"   Base64 length: {len(chart_base64)} characters")
        print()

        # Validate base64
        try:
            decoded = base64.b64decode(chart_base64)
            print(f"✅ Valid base64 PNG ({len(decoded)} bytes)")

            # Check PNG header
            if decoded[:8] == b'\x89PNG\r\n\x1a\n':
                print("✅ Valid PNG format")
            else:
                print("⚠️  Not a valid PNG file")
                return False

        except Exception as e:
            print(f"❌ Invalid base64: {e}")
            return False

        # Save to file
        output_path = "test_chart_output.png"
        with open(output_path, 'wb') as f:
            f.write(decoded)
        print(f"💾 Chart saved to: {output_path}")
        print()

        print("=" * 80)
        print("✅ ALL TESTS PASSED!")
        print("=" * 80)
        return True

    except Exception as e:
        print(f"❌ Chart generation failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_chart_save_directly():
    """Test saving chart directly to file"""
    print("\n" + "=" * 80)
    print("TEST: Direct Chart Save")
    print("=" * 80)
    print()

    # Initialize
    fetcher = DataFetcher()
    analyzer = TechnicalAnalyzer()
    chart_gen = ChartGenerator()

    ticker = "TSLA"
    print(f"📊 Testing direct save with: {ticker}")

    # Fetch data
    ticker_data = fetcher.fetch_ticker_data(ticker)
    info = fetcher.get_ticker_info(ticker)
    ticker_data.update(info)

    # Calculate indicators
    hist_data = ticker_data.get('history')
    indicators = analyzer.calculate_all_indicators(hist_data)

    # Save chart
    output_path = "test_chart_direct.png"
    try:
        chart_gen.save_chart(
            ticker_data=ticker_data,
            indicators=indicators,
            ticker_symbol=ticker,
            filepath=output_path,
            days=90
        )

        # Check file exists
        if os.path.exists(output_path):
            file_size = os.path.getsize(output_path)
            print(f"✅ Chart saved: {output_path} ({file_size} bytes)")
            return True
        else:
            print(f"❌ File not created: {output_path}")
            return False

    except Exception as e:
        print(f"❌ Save failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    # Run tests
    result1 = test_chart_generation_simple()
    result2 = test_chart_save_directly()

    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    print(f"Chart Generation Test: {'✅ PASSED' if result1 else '❌ FAILED'}")
    print(f"Direct Save Test: {'✅ PASSED' if result2 else '❌ FAILED'}")
    print("=" * 80)

    sys.exit(0 if (result1 and result2) else 1)
