#!/usr/bin/env python3
"""
Test LINE bot caching functionality
"""

import json
from datetime import date
from unittest.mock import patch, MagicMock
from src.line_bot import LineBot

def test_caching():
    """Test that responses are cached by (ticker, date)"""
    print("=" * 80)
    print("?? Testing Response Caching")
    print("=" * 80)
    print()

    with patch('src.line_bot.TickerAnalysisAgent'):
        bot = LineBot()
        
        # Mock database
        mock_db = MagicMock()
        bot.db = mock_db
        
        # Mock agent
        bot.agent.analyze_ticker = MagicMock(return_value="?? Report for DBS19")
        
        ticker = "DBS19"
        today = date.today().isoformat()
        
        # Test 1: Cache miss - should generate and cache
        print("Test 1: Cache miss - generate new report")
        print("-" * 60)
        mock_db.get_cached_report.return_value = None  # Cache miss
        
        event = {"type": "message", "message": {"type": "text", "text": ticker}}
        response1 = bot.handle_message(event)
        
        print(f"Response generated: {len(response1) > 0}")
        print(f"Agent called: {bot.agent.analyze_ticker.called}")
        print(f"Cache save called: {mock_db.save_report.called}")
        
        if mock_db.save_report.called:
            call_args = mock_db.save_report.call_args
            saved_ticker, saved_date, saved_data = call_args[0]
            print(f"? Cached: ticker={saved_ticker}, date={saved_date}")
            print(f"   Report text length: {len(saved_data.get('report_text', ''))}")
        else:
            print("? Cache save not called")
        
        print()
        
        # Test 2: Cache hit - should return cached report
        print("Test 2: Cache hit - return cached report")
        print("-" * 60)
        cached_report = "?? Cached Report for DBS19"
        mock_db.get_cached_report.return_value = cached_report  # Cache hit
        bot.agent.analyze_ticker.reset_mock()  # Reset call count
        
        response2 = bot.handle_message(event)
        
        print(f"Response returned: {response2 == cached_report}")
        print(f"Agent called: {bot.agent.analyze_ticker.called}")
        
        if not bot.agent.analyze_ticker.called:
            print("? Agent not called - cache used instead")
        else:
            print("? Agent was called despite cache hit")
        
        print()
        
        # Test 3: Different ticker - should cache miss
        print("Test 3: Different ticker - cache miss")
        print("-" * 60)
        mock_db.get_cached_report.return_value = None
        bot.agent.analyze_ticker.return_value = "?? Report for UOB19"
        bot.agent.analyze_ticker.reset_mock()
        
        event2 = {"type": "message", "message": {"type": "text", "text": "UOB19"}}
        response3 = bot.handle_message(event2)
        
        print(f"Response generated: {len(response3) > 0}")
        print(f"Agent called: {bot.agent.analyze_ticker.called}")
        print(f"Cache save called: {mock_db.save_report.called}")
        
        print()
        
        print("=" * 80)
        print("? Caching test completed")
        print("=" * 80)

def test_cache_key_format():
    """Test cache key format (ticker, date)"""
    print("=" * 80)
    print("?? Testing Cache Key Format")
    print("=" * 80)
    print()

    with patch('src.line_bot.TickerAnalysisAgent'):
        bot = LineBot()
        
        mock_db = MagicMock()
        bot.db = mock_db
        
        today = date.today().isoformat()
        print(f"Today's date: {today}")
        print()
        
        # Check cache key format
        ticker = "DBS19"
        mock_db.get_cached_report.return_value = None
        
        bot.agent.analyze_ticker = MagicMock(return_value="Test report")
        
        event = {"type": "message", "message": {"type": "text", "text": ticker}}
        bot.handle_message(event)
        
        # Verify cache was checked with correct key
        if mock_db.get_cached_report.called:
            call_args = mock_db.get_cached_report.call_args[0]
            cached_ticker, cached_date = call_args
            print(f"Cache check called with:")
            print(f"  Ticker: {cached_ticker}")
            print(f"  Date: {cached_date}")
            
            if cached_date == today:
                print("? Cache key uses today's date")
            else:
                print(f"? Cache key uses wrong date: {cached_date}")
            
            if cached_ticker == ticker:
                print("? Cache key uses correct ticker")
            else:
                print(f"? Cache key uses wrong ticker: {cached_ticker}")
        
        print()
        print("=" * 80)
        print("? Cache key format test completed")
        print("=" * 80)

if __name__ == '__main__':
    print()
    print("=" * 80)
    print("?? LINE Bot Caching Tests")
    print("=" * 80)
    print()

    # Test cache key format
    test_cache_key_format()
    print()
    print()

    # Test caching behavior
    test_caching()

    print()
    print("=" * 80)
    print("?? All tests completed!")
    print("=" * 80)