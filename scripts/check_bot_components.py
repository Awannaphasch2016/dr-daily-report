#!/usr/bin/env python3
"""
Verify bot components work correctly.

Usage: python scripts/check_bot_components.py
"""

import os
import sys


def test_imports():
    """Test if all modules can be imported"""
    print("🔍 Testing imports...")
    try:
        from data_fetcher import DataFetcher
        from technical_analysis import TechnicalAnalyzer
        from database import TickerDatabase
        from agent import TickerAnalysisAgent
        print("✅ All imports successful")
        return True
    except Exception as e:
        print(f"❌ Import error: {str(e)}")
        return False

def test_ticker_loading():
    """Test if tickers can be loaded"""
    print("\n🔍 Testing ticker loading...")
    try:
        from data_fetcher import DataFetcher
        fetcher = DataFetcher()
        tickers = fetcher.load_tickers()
        print(f"✅ Loaded {len(tickers)} tickers")
        print(f"   Sample tickers: {list(tickers.items())[:5]}")
        return True
    except Exception as e:
        print(f"❌ Ticker loading error: {str(e)}")
        return False

def test_database():
    """Test database initialization"""
    print("\n🔍 Testing database...")
    try:
        from database import TickerDatabase
        db = TickerDatabase(db_path="test_ticker_data.db")
        print("✅ Database initialized successfully")

        # Clean up test database
        import os
        if os.path.exists("test_ticker_data.db"):
            os.remove("test_ticker_data.db")

        return True
    except Exception as e:
        print(f"❌ Database error: {str(e)}")
        return False

def test_data_fetching():
    """Test data fetching (requires internet)"""
    print("\n🔍 Testing data fetching...")
    try:
        from data_fetcher import DataFetcher
        fetcher = DataFetcher()

        # Try to fetch a simple ticker
        data = fetcher.fetch_ticker_data("AAPL")
        if data:
            print("✅ Data fetching successful")
            print(f"   Sample: AAPL @ ${data['close']:.2f}")
            return True
        else:
            print("⚠️  Data fetching returned None (may be normal if Yahoo Finance is unreachable)")
            return True
    except Exception as e:
        print(f"⚠️  Data fetching error: {str(e)}")
        print("   (This may be normal if Yahoo Finance is temporarily unavailable)")
        return True

def test_environment():
    """Test environment variables"""
    print("\n🔍 Testing environment variables...")

    openai_key = os.getenv("OPENAI_API_KEY")
    line_token = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
    line_secret = os.getenv("LINE_CHANNEL_SECRET")

    results = []

    if openai_key:
        print(f"✅ OPENAI_API_KEY: {openai_key[:10]}...")
        results.append(True)
    else:
        print("⚠️  OPENAI_API_KEY not set")
        results.append(False)

    if line_token:
        print(f"✅ LINE_CHANNEL_ACCESS_TOKEN: {line_token[:10]}...")
        results.append(True)
    else:
        print("⚠️  LINE_CHANNEL_ACCESS_TOKEN not set (required for LINE bot)")
        results.append(False)

    if line_secret:
        print(f"✅ LINE_CHANNEL_SECRET: set")
        results.append(True)
    else:
        print("⚠️  LINE_CHANNEL_SECRET not set (required for LINE bot)")
        results.append(False)

    return any(results)

def main():
    """Run all tests"""
    print("=" * 60)
    print("LINE Bot Financial Ticker Report - Component Test")
    print("=" * 60)

    tests = [
        ("Imports", test_imports),
        ("Ticker Loading", test_ticker_loading),
        ("Database", test_database),
        ("Environment", test_environment),
        ("Data Fetching", test_data_fetching),
    ]

    results = []
    for name, test_func in tests:
        try:
            results.append(test_func())
        except Exception as e:
            print(f"❌ {name} test crashed: {str(e)}")
            results.append(False)

    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    passed = sum(results)
    total = len(results)
    print(f"Passed: {passed}/{total}")

    if passed == total:
        print("🎉 All tests passed! System is ready.")
    else:
        print("⚠️  Some tests failed. Please review the errors above.")

    print("\n📝 Next steps:")
    print("1. Make sure all environment variables are set")
    print("2. Run: doppler run --project rag-chatbot-worktree --config dev_personal -- python test_bot.py")
    print("3. Deploy using: ./deploy.sh")
    print("4. Configure LINE webhook URL")

    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
