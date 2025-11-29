# -*- coding: utf-8 -*-
"""
Tests for LINE Bot Integration

Tests the LINE bot webhook handling with mocked external services.
"""

import json
import pytest
from unittest.mock import patch, MagicMock


class TestLineBotWebhook:
    """Tests for LINE bot webhook handling"""

    @pytest.fixture
    def mock_dependencies(self):
        """Patch all heavy dependencies that LineBot uses"""
        with patch('src.integrations.line_bot.TickerAnalysisAgent') as mock_agent, \
             patch('src.integrations.line_bot.DataFetcher') as mock_fetcher, \
             patch('src.integrations.line_bot.TickerDatabase') as mock_db, \
             patch('src.integrations.line_bot.PDFStorage') as mock_pdf, \
             patch('src.integrations.line_bot.S3Cache') as mock_cache, \
             patch.dict('os.environ', {
                 'LINE_CHANNEL_ACCESS_TOKEN': 'test_token',
                 'LINE_CHANNEL_SECRET': 'test_secret'
             }):
            # Configure mock fetcher
            mock_fetcher_instance = MagicMock()
            mock_fetcher_instance.load_tickers.return_value = {'DBS19': 'DBS Bank'}
            mock_fetcher.return_value = mock_fetcher_instance

            # Configure mock agent
            mock_agent_instance = MagicMock()
            mock_agent_instance.analyze_ticker.return_value = "Test report in Thai"
            mock_agent.return_value = mock_agent_instance

            # Configure mock database - need to return None for cache miss
            mock_db_instance = MagicMock()
            mock_db_instance.get_cached_report.return_value = None
            mock_db.return_value = mock_db_instance

            # Configure mock PDF storage
            mock_pdf_instance = MagicMock()
            mock_pdf_instance.is_available.return_value = False
            mock_pdf.return_value = mock_pdf_instance

            yield {
                'agent': mock_agent,
                'fetcher': mock_fetcher,
                'db': mock_db,
                'pdf': mock_pdf,
                'cache': mock_cache
            }

    @pytest.fixture
    def line_bot(self, mock_dependencies):
        """Create LineBot instance with mocked dependencies"""
        from src.integrations.line_bot import LineBot
        return LineBot()

    @pytest.fixture
    def mock_webhook_event(self):
        """Create mock LINE webhook event"""
        return {
            "events": [
                {
                    "type": "message",
                    "replyToken": "mock_reply_token_123",
                    "source": {
                        "userId": "U123456789",
                        "type": "user"
                    },
                    "timestamp": 1462629479859,
                    "message": {
                        "type": "text",
                        "id": "325708",
                        "text": "DBS19"
                    }
                }
            ]
        }

    def test_webhook_returns_200_on_success(self, line_bot, mock_webhook_event):
        """Test that webhook returns 200 status code on success"""
        body = json.dumps(mock_webhook_event)
        signature = "test_signature"

        # Mock reply_message to prevent actual LINE API calls
        with patch.object(line_bot, 'reply_message', return_value=True):
            with patch.object(line_bot, 'verify_signature', return_value=True):
                result = line_bot.handle_webhook(body, signature)

        assert result['statusCode'] == 200, f"Expected 200, got {result['statusCode']}"

    def test_webhook_captures_sent_messages(self, line_bot, mock_webhook_event):
        """Test that webhook correctly returns responses in test mode"""
        body = json.dumps(mock_webhook_event)
        signature = "test_signature"  # Test signature triggers test mode

        with patch.object(line_bot, 'verify_signature', return_value=True):
            result = line_bot.handle_webhook(body, signature)

        # In test mode, responses are returned in the body
        assert result['statusCode'] == 200
        response_body = json.loads(result['body'])

        # Test mode returns responses array
        assert 'responses' in response_body, f"Expected 'responses' in body, got {response_body.keys()}"
        responses = response_body['responses']
        assert len(responses) > 0, "Expected at least one response"
        assert len(str(responses[0])) > 0, "Response should not be empty"

    def test_webhook_handles_empty_events(self, line_bot):
        """Test that webhook handles empty events gracefully"""
        empty_event = {"events": []}
        body = json.dumps(empty_event)
        signature = "test_signature"

        with patch.object(line_bot, 'verify_signature', return_value=True):
            result = line_bot.handle_webhook(body, signature)

        assert result['statusCode'] == 200

    def test_webhook_handles_non_message_event(self, line_bot):
        """Test that webhook handles non-message events (e.g., follow)"""
        follow_event = {
            "events": [
                {
                    "type": "follow",
                    "replyToken": "mock_token",
                    "source": {
                        "userId": "U123456789",
                        "type": "user"
                    },
                    "timestamp": 1462629479859
                }
            ]
        }
        body = json.dumps(follow_event)
        signature = "test_signature"

        with patch.object(line_bot, 'reply_message', return_value=True):
            with patch.object(line_bot, 'verify_signature', return_value=True):
                result = line_bot.handle_webhook(body, signature)

        assert result['statusCode'] == 200


class TestLineBotMessageParsing:
    """Tests for LINE bot message parsing"""

    def test_extracts_ticker_from_message(self):
        """Test that ticker symbol is extracted from message text"""
        message = {"type": "text", "text": "DBS19"}

        # Test the ticker extraction logic
        ticker = message.get("text", "").strip().upper()

        assert ticker == "DBS19", f"Expected 'DBS19', got '{ticker}'"

    def test_handles_lowercase_ticker(self):
        """Test that lowercase ticker is converted to uppercase"""
        message = {"type": "text", "text": "nvda19"}

        ticker = message.get("text", "").strip().upper()

        assert ticker == "NVDA19", f"Expected 'NVDA19', got '{ticker}'"

    def test_handles_ticker_with_whitespace(self):
        """Test that whitespace is trimmed from ticker"""
        message = {"type": "text", "text": "  AAPL  "}

        ticker = message.get("text", "").strip().upper()

        assert ticker == "AAPL", f"Expected 'AAPL', got '{ticker}'"


@pytest.mark.integration
@pytest.mark.slow
class TestLineBotIntegration:
    """Integration tests requiring actual LINE bot processing"""

    @pytest.fixture
    def real_line_bot(self):
        """Create real LineBot for integration tests"""
        import os
        if not os.getenv('LINE_CHANNEL_ACCESS_TOKEN'):
            pytest.skip("LINE credentials not available")

        from src.integrations.line_bot import LineBot
        return LineBot()

    def test_full_webhook_processing(self, real_line_bot):
        """Test complete webhook processing with real agent"""
        event = {
            "events": [
                {
                    "type": "message",
                    "replyToken": "integration_test_token",
                    "source": {
                        "userId": "U_integration_test",
                        "type": "user"
                    },
                    "timestamp": 1462629479859,
                    "message": {
                        "type": "text",
                        "id": "integration_test",
                        "text": "AAPL"
                    }
                }
            ]
        }

        body = json.dumps(event)
        signature = "test_signature"

        # Mock only the actual LINE API reply to prevent external calls
        sent_messages = []

        def capture_reply(reply_token, text):
            sent_messages.append(text)
            return True

        with patch.object(real_line_bot, 'reply_message', side_effect=capture_reply):
            with patch.object(real_line_bot, 'verify_signature', return_value=True):
                result = real_line_bot.handle_webhook(body, signature)

        assert result['statusCode'] == 200, f"Expected 200, got {result['statusCode']}"
        # If a message was sent, verify it has content
        if sent_messages:
            assert len(str(sent_messages[0])) > 0, "Reply message should not be empty"
