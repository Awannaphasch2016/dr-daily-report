#!/usr/bin/env python3
"""
Test LINE bot fuzzy ticker matching
"""

import json
from unittest.mock import patch
from src.line_bot import LineBot

def test_fuzzy_matching():
    """Test fuzzy ticker matching"""
    print("=" * 80)
    print("?? Testing Fuzzy Ticker Matching")
    print("=" * 80)
    print()

    with patch('src.line_bot.TickerAnalysisAgent') as mock_agent_class:
        bot = LineBot()
        
        # Mock agent to return a simple report
        mock_agent_class.return_value.analyze_ticker.return_value = "?? Report for matched ticker"
        
        # Test cases: (input, expected_behavior)
        test_cases = [
            ("DBS19", "exact_match", "Should match exactly"),
            ("dbs19", "exact_match", "Should match case-insensitive"),
            ("DBS18", "fuzzy_match", "Should correct typo (18->19)"),
            ("DBS2", "fuzzy_match", "Should match DBS19"),
            ("UOB20", "fuzzy_match", "Should match UOB19"),
            ("HONDA", "fuzzy_match", "Should match HONDA19"),
            ("TENCNET19", "fuzzy_match", "Should match TENCENT19"),
            ("INVALID123", "no_match", "Should not match"),
            ("XYZ", "no_match", "Should not match"),
        ]
        
        print("Testing ticker matching:")
        print("-" * 60)
        
        for input_ticker, expected, description in test_cases:
            print(f"\nInput: '{input_ticker}' ({description})")
            print("-" * 40)
            
            # Get match result
            match_result = bot.ticker_matcher.match_with_suggestion(input_ticker)
            matched_ticker, suggestion = match_result
            
            print(f"  Matched ticker: {matched_ticker}")
            print(f"  Suggestion: {suggestion if suggestion else 'None (auto-corrected or exact)'}")
            
            # Verify behavior
            if expected == "exact_match":
                if matched_ticker == input_ticker.upper() and suggestion is None:
                    print(f"  ? PASSED - Exact match")
                else:
                    print(f"  ? FAILED - Expected exact match")
            elif expected == "fuzzy_match":
                if matched_ticker and matched_ticker != input_ticker.upper():
                    print(f"  ? PASSED - Fuzzy match found")
                else:
                    print(f"  ? FAILED - Expected fuzzy match")
            elif expected == "no_match":
                # Check if it's a valid ticker (should still match something close)
                # or if similarity is too low
                best_match = bot.ticker_matcher.find_best_match(input_ticker, min_similarity=0.6)
                if best_match is None or best_match[1] < 0.6:
                    print(f"  ? PASSED - No good match (as expected)")
                else:
                    print(f"  ??  Found match with similarity {best_match[1]:.2f}")
        
        print()
        print("=" * 80)
        print("? Fuzzy matching test completed")
        print("=" * 80)

def test_message_handling_with_fuzzy():
    """Test message handling with fuzzy matching"""
    print("=" * 80)
    print("?? Testing Message Handling with Fuzzy Matching")
    print("=" * 80)
    print()

    with patch('src.line_bot.TickerAnalysisAgent') as mock_agent_class:
        bot = LineBot()
        
        # Mock agent to return reports
        def mock_analyze(ticker):
            return f"?? Report for {ticker}"
        
        mock_agent_class.return_value.analyze_ticker.side_effect = mock_analyze
        
        test_cases = [
            ("DBS19", "Should work normally"),
            ("DBS18", "Should auto-correct typo"),
            ("UOB20", "Should suggest correction"),
        ]
        
        for input_ticker, description in test_cases:
            print(f"Test: '{input_ticker}' - {description}")
            print("-" * 60)
            
            event = {
                "type": "message",
                "message": {
                    "type": "text",
                    "text": input_ticker
                }
            }
            
            response = bot.handle_message(event)
            
            if response:
                print(f"Response preview:")
                print(response[:150] + "..." if len(response) > 150 else response)
                print()
                
                # Check if suggestion is included for typos
                if input_ticker != "DBS19" and "??" in response:
                    print("  ? Suggestion included for typo")
                elif input_ticker == "DBS19":
                    print("  ? No suggestion for exact match")
            else:
                print("  ? No response")
            
            print()

if __name__ == '__main__':
    print()
    print("=" * 80)
    print("?? LINE Bot Fuzzy Matching Tests")
    print("=" * 80)
    print()

    # Test fuzzy matching directly
    test_fuzzy_matching()
    print()
    print()

    # Test message handling with fuzzy matching
    test_message_handling_with_fuzzy()

    print()
    print("=" * 80)
    print("?? All tests completed!")
    print("=" * 80)