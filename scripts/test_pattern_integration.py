#!/usr/bin/env python3
"""
Test chart pattern integration in report API
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Ensure stock-pattern library is available
sys.path.insert(0, '/tmp/stock-pattern/src')

import logging
from src.services.pattern_detection_service import get_pattern_service
from src.api.models import ChartPattern

logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_pattern_service():
    """Test pattern detection service"""
    print("=" * 70)
    print("TEST 1: Pattern Detection Service")
    print("=" * 70)

    try:
        service = get_pattern_service()

        # Test with a ticker (will use Aurora data)
        ticker = "AAPL"
        logger.info(f"Testing pattern detection for {ticker}...")

        result = service.detect_patterns(ticker, days=180)

        print(f"\n✅ Service returned result:")
        print(f"   - Ticker: {result['ticker']}")
        print(f"   - Data range: {result.get('data_range')}")
        print(f"   - Bars: {result.get('bars', 0)}")
        print(f"   - Pivots: {result.get('pivots', 0)}")
        print(f"   - Patterns detected: {len(result['patterns'])}")

        if result['patterns']:
            print(f"\n   Patterns found:")
            for p in result['patterns']:
                print(f"   - {p['type']} ({p['confidence']} confidence)")
        else:
            print(f"\n   ℹ️  No patterns detected (this is expected - patterns are rare)")

        return True

    except Exception as e:
        print(f"\n❌ Service test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_chart_pattern_model():
    """Test ChartPattern model construction"""
    print("\n" + "=" * 70)
    print("TEST 2: ChartPattern Model")
    print("=" * 70)

    try:
        # Create a sample pattern
        pattern = ChartPattern(
            type="bullish_flag",
            pattern="FLAGU",
            confidence="medium",
            start="2024-01-01",
            end="2024-01-15",
            points={
                "A": {"date": "2024-01-01", "price": 150.0},
                "B": {"date": "2024-01-15", "price": 155.0}
            }
        )

        print(f"\n✅ ChartPattern model created successfully:")
        print(f"   - Type: {pattern.type}")
        print(f"   - Pattern: {pattern.pattern}")
        print(f"   - Confidence: {pattern.confidence}")
        print(f"   - Date range: {pattern.start} to {pattern.end}")
        print(f"   - Points: {len(pattern.points)} key points")

        # Test serialization
        pattern_dict = pattern.model_dump()
        print(f"\n✅ Model serializes to dict: {list(pattern_dict.keys())}")

        return True

    except Exception as e:
        print(f"\n❌ Model test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests"""
    print("\n" + "=" * 70)
    print("CHART PATTERN INTEGRATION TEST")
    print("=" * 70)
    print()

    results = []

    # Test 1: Pattern detection service
    results.append(("Pattern Service", test_pattern_service()))

    # Test 2: ChartPattern model
    results.append(("ChartPattern Model", test_chart_pattern_model()))

    # Summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)

    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} - {test_name}")

    all_passed = all(r[1] for r in results)

    if all_passed:
        print("\n🎉 All tests passed!")
        print("\nNext steps:")
        print("1. Deploy to dev environment")
        print("2. Test with real report generation API")
        print("3. Verify patterns appear in API response")
    else:
        print("\n⚠️  Some tests failed - review errors above")
        return 1

    return 0


if __name__ == '__main__':
    sys.exit(main())
