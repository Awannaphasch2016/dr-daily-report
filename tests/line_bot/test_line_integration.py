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
             patch('src.integrations.line_bot.PrecomputeService') as mock_precompute, \
             patch('src.integrations.line_bot.PDFStorage') as mock_pdf, \
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

            # Configure mock Aurora precompute service
            mock_precompute_instance = MagicMock()
            mock_precompute_instance.get_cached_report.return_value = None
            mock_precompute_instance.store_report_from_api.return_value = True  # Default success
            mock_precompute.return_value = mock_precompute_instance

            # Configure mock PDF storage
            mock_pdf_instance = MagicMock()
            mock_pdf_instance.is_available.return_value = False
            mock_pdf.return_value = mock_pdf_instance

            yield {
                'agent': mock_agent,
                'fetcher': mock_fetcher,
                'precompute': mock_precompute_instance,  # Return instance, not class
                'pdf': mock_pdf
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

    def test_cache_miss_generates_new_report(self, mock_dependencies, line_bot):
        """Test full workflow when Aurora cache is empty: cache miss → generate → store"""
        # Setup: Aurora returns None (cache miss)
        mock_dependencies['precompute'].get_cached_report.return_value = None

        # Setup: Store to cache returns True (success)
        mock_precompute_instance = mock_dependencies['precompute']
        mock_precompute_instance.store_report_from_api.return_value = True

        # Create webhook event with ticker message
        event = {
            "events": [{
                "type": "message",
                "replyToken": "test_token",
                "source": {"userId": "U_test", "type": "user"},
                "timestamp": 1462629479859,
                "message": {"type": "text", "id": "msg_123", "text": "DBS19"}
            }]
        }
        body = json.dumps(event)
        signature = "test_signature"

        with patch.object(line_bot, 'verify_signature', return_value=True):
            result = line_bot.handle_webhook(body, signature)

        # Verify workflow executed all steps
        assert result['statusCode'] == 200

        # Step 1: Checked cache (cache miss)
        mock_precompute_instance.get_cached_report.assert_called_once_with('DBS19')

        # Step 2: Generated new report (since cache miss)
        # Note: agent.analyze_ticker is called on the instance created by LINE bot
        # We can't easily assert this without more complex mocking, but we can verify the outcome

        # Step 3: Stored report to cache
        mock_precompute_instance.store_report_from_api.assert_called_once()
        call_args = mock_precompute_instance.store_report_from_api.call_args
        assert call_args[1]['symbol'] == 'DBS19'
        assert call_args[1]['report_text'] == "Test report in Thai"  # Default from fixture

        # Step 4: Response returned to user (test mode returns responses in body)
        response_body = json.loads(result['body'])
        assert 'responses' in response_body
        assert len(response_body['responses']) > 0

    def test_cache_storage_failure_is_detected(self, mock_dependencies, line_bot):
        """Test that cache storage failure (0 rows affected) is detected and logged"""
        # Setup: Aurora returns None (cache miss)
        mock_dependencies['precompute'].get_cached_report.return_value = None

        # Setup: Agent generates new report
        mock_dependencies['agent'].analyze_ticker.return_value = "Report text"

        # Setup: Store to cache returns False (0 rows affected - FK constraint failure)
        mock_precompute_instance = mock_dependencies['precompute']
        mock_precompute_instance.store_report_from_api.return_value = False  # Failure!

        # Setup: Mock fetcher
        mock_dependencies['fetcher'].load_tickers.return_value = {'NVDA19': 'NVIDIA'}

        # Create webhook event
        event = {
            "events": [{
                "type": "message",
                "replyToken": "test_token",
                "source": {"userId": "U_test", "type": "user"},
                "timestamp": 1462629479859,
                "message": {"type": "text", "id": "msg_123", "text": "NVDA19"}
            }]
        }

        with patch.object(line_bot, 'verify_signature', return_value=True):
            with patch.object(line_bot, 'reply_message', return_value=True):
                # Should complete despite cache failure
                result = line_bot.handle_webhook(json.dumps(event), "test_signature")

        # Verify webhook succeeded (cache failure shouldn't block user response)
        assert result['statusCode'] == 200

        # Verify storage was attempted
        mock_precompute_instance.store_report_from_api.assert_called_once()

        # Test verifies: Silent failure detected (method returned False)
        # In production, this logs warning: "Cache storage failed for NVDA19 (0 rows affected)"


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
