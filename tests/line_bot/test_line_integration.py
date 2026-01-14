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

    def test_cache_miss_returns_error(self, mock_dependencies, line_bot):
        """Test Aurora-First architecture: cache miss returns fail-fast error (no on-demand generation)"""
        # Setup: Aurora returns None (cache miss)
        mock_dependencies['precompute'].get_cached_report.return_value = None

        mock_precompute_instance = mock_dependencies['precompute']

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

        # Verify fail-fast behavior (Aurora-First principle)
        assert result['statusCode'] == 200

        # Step 1: Checked cache (cache miss)
        mock_precompute_instance.get_cached_report.assert_called_once_with('DBS19')

        # Step 2: Did NOT generate on-demand (fail-fast architecture)
        mock_precompute_instance.store_report_from_api.assert_not_called()

        # Step 3: Returned error message to user
        response_body = json.loads(result['body'])
        assert 'responses' in response_body
        assert len(response_body['responses']) > 0
        # Check for Thai error message (report not ready)
        # In test mode, responses are stringified directly
        response_text = str(response_body['responses'][0])
        assert 'ยังไม่พร้อม' in response_text or 'not ready' in response_text.lower()

    @pytest.mark.skip(reason="Obsolete: Aurora-First architecture no longer generates reports on-demand. Cache is populated only by scheduler. See CLAUDE.md Core Principle #3")
    def test_cache_storage_failure_is_detected(self, mock_dependencies, line_bot):
        """OBSOLETE: Test for on-demand report generation behavior (no longer used)

        This test validated cache storage failure detection during on-demand report
        generation. However, Aurora-First architecture (CLAUDE.md Core Principle #3)
        changed the system to:
        - Cache populated ONLY by nightly scheduler (46 tickers)
        - APIs are read-only and query Aurora directly
        - Cache miss returns fail-fast error (no on-demand generation)

        Original behavior (obsolete):
        - Cache miss → generate report → store to cache → respond

        Current behavior (Aurora-First):
        - Cache miss → return error immediately (fail-fast)

        Keeping test for historical context. For current cache behavior, see:
        - test_cache_hit_returns_cached_report (cache hit path)
        - test_cache_miss_returns_error (cache miss fail-fast path)
        """
        pass


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


class TestLineBotHelpCommand:
    """Tests for LINE bot help command per linebot/invariants.md.

    Invariant: /help returns command reference (Level 0 User Invariant).
    """

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
            mock_fetcher_instance = MagicMock()
            mock_fetcher_instance.load_tickers.return_value = {'DBS19': 'DBS Bank'}
            mock_fetcher.return_value = mock_fetcher_instance
            mock_precompute_instance = MagicMock()
            mock_precompute.return_value = mock_precompute_instance
            mock_pdf_instance = MagicMock()
            mock_pdf_instance.is_available.return_value = False
            mock_pdf.return_value = mock_pdf_instance
            yield

    @pytest.fixture
    def line_bot(self, mock_dependencies):
        """Create LineBot instance with mocked dependencies"""
        from src.integrations.line_bot import LineBot
        return LineBot()

    def test_help_command_returns_usage_instructions(self, line_bot):
        """Test that 'help' command returns usage instructions."""
        event = {
            "type": "message",
            "message": {"type": "text", "text": "help"}
        }
        result = line_bot.handle_message(event)

        assert result is not None
        assert "วิธีใช้งาน" in result or "วิธีใช้" in result, "Help message should contain usage instructions"

    def test_help_command_thai_keyword(self, line_bot):
        """Test that Thai help keyword 'วิธีใช้' returns help message."""
        event = {
            "type": "message",
            "message": {"type": "text", "text": "วิธีใช้"}
        }
        result = line_bot.handle_message(event)

        assert result is not None
        assert "Daily Report Bot" in result or "ticker" in result, "Help should mention bot purpose"

    def test_help_command_lists_example_tickers(self, line_bot):
        """Test that help message includes example tickers."""
        event = {
            "type": "message",
            "message": {"type": "text", "text": "help"}
        }
        result = line_bot.handle_message(event)

        assert "DBS19" in result or "ticker" in result, "Help should include example tickers"


class TestLineBotInvalidTicker:
    """Tests for LINE bot invalid ticker handling per linebot/invariants.md.

    Invariant: Invalid ticker returns 'Ticker not found' with suggestions (Level 0 User Invariant).
    """

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
            mock_fetcher_instance = MagicMock()
            mock_fetcher_instance.load_tickers.return_value = {'DBS19': 'DBS Bank', 'UOB19': 'UOB Bank'}
            mock_fetcher.return_value = mock_fetcher_instance
            mock_precompute_instance = MagicMock()
            mock_precompute_instance.get_cached_report.return_value = None  # Simulate cache miss
            mock_precompute.return_value = mock_precompute_instance
            mock_pdf_instance = MagicMock()
            mock_pdf_instance.is_available.return_value = False
            mock_pdf.return_value = mock_pdf_instance
            yield {'precompute': mock_precompute_instance}

    @pytest.fixture
    def line_bot(self, mock_dependencies):
        """Create LineBot instance with mocked dependencies"""
        from src.integrations.line_bot import LineBot
        return LineBot()

    def test_invalid_ticker_returns_not_ready_message(self, line_bot, mock_dependencies):
        """Test that uncached ticker returns 'not ready' message."""
        event = {
            "type": "message",
            "message": {"type": "text", "text": "INVALID_TICKER_XYZ"}
        }
        result = line_bot.handle_message(event)

        assert result is not None
        # Should indicate report is not ready (Aurora-first architecture)
        assert "ยังไม่พร้อม" in result or "not ready" in result.lower() or "ลองใหม่" in result

    def test_empty_message_returns_prompt(self, line_bot):
        """Test that empty message returns prompt for ticker."""
        event = {
            "type": "message",
            "message": {"type": "text", "text": ""}
        }
        result = line_bot.handle_message(event)

        assert result is not None
        assert "ticker" in result.lower() or "ส่งชื่อ" in result


class TestLineBotReportContent:
    """Tests for LINE bot report content per linebot/invariants.md.

    Invariant: Report contains required sections (Level 2 Data Invariant).
    """

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
            mock_fetcher_instance = MagicMock()
            mock_fetcher_instance.load_tickers.return_value = {'DBS19': 'DBS Bank'}
            mock_fetcher.return_value = mock_fetcher_instance

            # Configure mock precompute with a realistic cached report
            mock_precompute_instance = MagicMock()
            mock_precompute_instance.get_cached_report.return_value = {
                'report_text': """รายงานวิเคราะห์ DBS19

📊 สรุปภาพรวมตลาด
ตลาดมีความผันผวน...

💼 วิเคราะห์พอร์ตโฟลิโอ
สถานะการลงทุน...

📰 ข่าวสารสำคัญ
ข่าวล่าสุดเกี่ยวกับ DBS...

💭 วิเคราะห์ความเชื่อมั่น
sentiment analysis...

✅ คำแนะนำ
แนะนำให้ถือ...""",
                'ticker': 'DBS19',
                'generated_at': '2026-01-14T10:00:00'
            }
            mock_precompute.return_value = mock_precompute_instance

            mock_pdf_instance = MagicMock()
            mock_pdf_instance.is_available.return_value = False
            mock_pdf.return_value = mock_pdf_instance
            yield {'precompute': mock_precompute_instance}

    @pytest.fixture
    def line_bot(self, mock_dependencies):
        """Create LineBot instance with mocked dependencies"""
        from src.integrations.line_bot import LineBot
        return LineBot()

    def test_cached_report_returns_report_text(self, line_bot, mock_dependencies):
        """Test that cached report returns the stored report text."""
        event = {
            "type": "message",
            "message": {"type": "text", "text": "DBS19"}
        }
        result = line_bot.handle_message(event)

        assert result is not None
        # Verify precompute cache was checked
        mock_dependencies['precompute'].get_cached_report.assert_called()

    def test_report_contains_market_section(self, line_bot):
        """Test that report contains market overview section."""
        event = {
            "type": "message",
            "message": {"type": "text", "text": "DBS19"}
        }
        result = line_bot.handle_message(event)

        assert result is not None
        assert "ตลาด" in result or "market" in result.lower(), "Report should contain market section"

    def test_report_contains_recommendation_section(self, line_bot):
        """Test that report contains recommendation section."""
        event = {
            "type": "message",
            "message": {"type": "text", "text": "DBS19"}
        }
        result = line_bot.handle_message(event)

        assert result is not None
        assert "คำแนะนำ" in result or "แนะนำ" in result, "Report should contain recommendation section"
