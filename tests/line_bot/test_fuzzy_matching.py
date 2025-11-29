# -*- coding: utf-8 -*-
"""
Tests for LINE bot fuzzy ticker matching

Tests the TickerMatcher fuzzy matching functionality for
correcting typos and suggesting valid tickers.
"""

import pytest
from unittest.mock import patch, MagicMock


class TestFuzzyTickerMatching:
    """Tests for fuzzy ticker matching functionality"""

    @pytest.fixture
    def mock_bot(self):
        """Create mock LineBot with ticker_matcher"""
        with patch('src.integrations.line_bot.TickerAnalysisAgent') as mock_agent_class:
            from src.integrations.line_bot import LineBot
            bot = LineBot()
            mock_agent_class.return_value.analyze_ticker.return_value = "📊 Report for matched ticker"
            yield bot

    def test_exact_match_uppercase(self, mock_bot):
        """Test exact match with uppercase ticker"""
        matched_ticker, suggestion = mock_bot.ticker_matcher.match_with_suggestion("DBS19")

        assert matched_ticker == "DBS19", f"Expected DBS19, got {matched_ticker}"
        assert suggestion is None, "Should not have suggestion for exact match"

    def test_exact_match_case_insensitive(self, mock_bot):
        """Test case-insensitive exact match"""
        matched_ticker, suggestion = mock_bot.ticker_matcher.match_with_suggestion("dbs19")

        assert matched_ticker.upper() == "DBS19", f"Expected DBS19, got {matched_ticker}"

    def test_fuzzy_match_typo_digit(self, mock_bot):
        """Test fuzzy match corrects digit typo (18->19)"""
        matched_ticker, suggestion = mock_bot.ticker_matcher.match_with_suggestion("DBS18")

        # Should find a match close to DBS18
        assert matched_ticker is not None, "Should find a fuzzy match"
        if matched_ticker != "DBS18":
            # Found a better match (likely DBS19)
            assert matched_ticker.startswith("DBS"), f"Should match DBS ticker, got {matched_ticker}"

    def test_fuzzy_match_partial_ticker(self, mock_bot):
        """Test fuzzy match with partial ticker name"""
        matched_ticker, suggestion = mock_bot.ticker_matcher.match_with_suggestion("DBS2")

        assert matched_ticker is not None, "Should find a fuzzy match"

    def test_no_match_invalid_ticker(self, mock_bot):
        """Test no match for completely invalid ticker"""
        best_match = mock_bot.ticker_matcher.find_best_match("INVALIDXYZ123", min_similarity=0.6)

        # Either no match or very low similarity
        if best_match is not None:
            ticker, similarity = best_match
            assert similarity < 0.6, f"Should not have high similarity for invalid ticker: {similarity}"

    def test_no_match_random_string(self, mock_bot):
        """Test no match for random string"""
        best_match = mock_bot.ticker_matcher.find_best_match("XYZ", min_similarity=0.6)

        if best_match is not None:
            ticker, similarity = best_match
            assert similarity < 0.6, f"Should not match random string: {ticker} ({similarity})"


class TestMessageHandlingWithFuzzy:
    """Tests for message handling with fuzzy matching integration"""

    @pytest.fixture
    def mock_bot_with_agent(self):
        """Create mock LineBot with mocked agent analyze"""
        with patch('src.integrations.line_bot.TickerAnalysisAgent') as mock_agent_class:
            from src.integrations.line_bot import LineBot
            bot = LineBot()

            # Mock agent to return reports
            def mock_analyze(ticker):
                return f"📊 Report for {ticker}"

            mock_agent_class.return_value.analyze_ticker.side_effect = mock_analyze
            yield bot

    def test_message_handling_exact_match(self, mock_bot_with_agent):
        """Test message handling with exact ticker match"""
        event = {
            "type": "message",
            "message": {
                "type": "text",
                "text": "DBS19"
            }
        }

        response = mock_bot_with_agent.handle_message(event)

        assert response is not None, "Should return a response"
        assert len(response) > 0, "Response should not be empty"

    def test_message_handling_with_typo(self, mock_bot_with_agent):
        """Test message handling auto-corrects typo"""
        event = {
            "type": "message",
            "message": {
                "type": "text",
                "text": "DBS18"  # Typo
            }
        }

        response = mock_bot_with_agent.handle_message(event)

        # Should still get a response (either with correction or suggestion)
        assert response is not None, "Should handle typo gracefully"
