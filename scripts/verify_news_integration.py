"""
Test script to verify news integration with Yahoo Finance API
"""

from src.data.news_fetcher import NewsFetcher
from src.agent import TickerAnalysisAgent

def test_news_fetcher():
    """Test the news fetcher functionality"""
    print("=" * 80)
    print("Testing News Fetcher")
    print("=" * 80)

    fetcher = NewsFetcher()

    # Test with a popular ticker
    test_ticker = "AAPL"  # Apple Inc.

    print(f"\n1. Fetching all news for {test_ticker}...")
    all_news = fetcher.fetch_news(test_ticker, max_news=10)
    print(f"   Found {len(all_news)} news items\n")

    if all_news:
        print("   First news item:")
        print(f"   - Title: {all_news[0]['title']}")
        print(f"   - Publisher: {all_news[0]['publisher']}")
        print(f"   - Timestamp: {all_news[0]['timestamp']}")

    print(f"\n2. Filtering high-impact news for {test_ticker}...")
    high_impact = fetcher.filter_high_impact_news(test_ticker, min_score=40.0, max_news=5)
    print(f"   Found {len(high_impact)} high-impact news items\n")

    if high_impact:
        for idx, news in enumerate(high_impact, 1):
            print(f"   [{idx}] {news['title']}")
            print(f"       Impact Score: {news['impact_score']:.0f}/100")
            print(f"       Sentiment: {news['sentiment'].upper()}")
            print(f"       Publisher: {news['publisher']}")
            print()

    print("3. Getting news summary...")
    summary = fetcher.get_news_summary(high_impact)
    print(f"   Total Count: {summary['total_count']}")
    print(f"   Positive: {summary['positive_count']}")
    print(f"   Negative: {summary['negative_count']}")
    print(f"   Neutral: {summary['neutral_count']}")
    print(f"   Dominant Sentiment: {summary['dominant_sentiment'].upper()}")
    print(f"   Has Recent News (< 24h): {summary['has_recent_news']}")

    print("\n4. Formatted news for report:")
    print(fetcher.format_news_for_report(high_impact))

    print("\n5. News references:")
    print(fetcher.get_news_references(high_impact))


def test_agent_with_news():
    """Test the full agent with news integration"""
    print("\n" + "=" * 80)
    print("Testing Agent with News Integration")
    print("=" * 80 + "\n")

    agent = TickerAnalysisAgent()

    # Test with a ticker from tickers.csv
    # Using a US ticker that should have news
    test_ticker = "AAPL"

    print(f"Generating report for {test_ticker}...\n")
    print("(This may take 10-20 seconds as it fetches data and generates the report)\n")

    try:
        report = agent.analyze_ticker(test_ticker)
        print("=" * 80)
        print("GENERATED REPORT:")
        print("=" * 80)
        print(report)
        print("=" * 80)
    except Exception as e:
        print(f"Error generating report: {str(e)}")
        import traceback
        traceback.print_exc()


def test_news_scoring():
    """Test the news impact scoring algorithm"""
    print("\n" + "=" * 80)
    print("Testing News Impact Scoring")
    print("=" * 80 + "\n")

    fetcher = NewsFetcher()

    # Create test news items with different characteristics
    from datetime import datetime, timedelta

    test_cases = [
        {
            'title': 'Apple reports record quarterly earnings, beats analyst expectations',
            'publisher': 'Reuters',
            'timestamp': datetime.now() - timedelta(hours=2)
        },
        {
            'title': 'Apple stock downgraded by major analyst firm',
            'publisher': 'Bloomberg',
            'timestamp': datetime.now() - timedelta(days=3)
        },
        {
            'title': 'Apple announces new product launch event',
            'publisher': 'TechCrunch',
            'timestamp': datetime.now() - timedelta(days=10)
        },
        {
            'title': 'Apple CEO discusses company vision in interview',
            'publisher': 'CNBC',
            'timestamp': datetime.now() - timedelta(hours=12)
        }
    ]

    for idx, test_news in enumerate(test_cases, 1):
        score = fetcher.calculate_impact_score(test_news)
        sentiment = fetcher.classify_sentiment(test_news)

        print(f"Test Case {idx}:")
        print(f"  Title: {test_news['title']}")
        print(f"  Impact Score: {score:.0f}/100")
        print(f"  Sentiment: {sentiment.upper()}")
        print()


if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("NEWS INTEGRATION TEST SUITE")
    print("=" * 80)

    # Test 1: News Fetcher
    try:
        test_news_fetcher()
    except Exception as e:
        print(f"\n❌ News Fetcher Test Failed: {str(e)}")
        import traceback
        traceback.print_exc()

    # Test 2: News Scoring
    try:
        test_news_scoring()
    except Exception as e:
        print(f"\n❌ News Scoring Test Failed: {str(e)}")
        import traceback
        traceback.print_exc()

    # Test 3: Full Agent Integration (commented out by default as it's slower)
    run_full_test = input("\nRun full agent integration test? (takes 10-20 seconds) [y/N]: ")
    if run_full_test.lower() in ['y', 'yes']:
        try:
            test_agent_with_news()
        except Exception as e:
            print(f"\n❌ Agent Integration Test Failed: {str(e)}")
            import traceback
            traceback.print_exc()
    else:
        print("\nSkipping full agent test. Run with 'y' to test full integration.")

    print("\n" + "=" * 80)
    print("TEST SUITE COMPLETED")
    print("=" * 80 + "\n")
