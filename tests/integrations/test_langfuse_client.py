# -*- coding: utf-8 -*-
"""Tests for langfuse_client utility functions."""

from unittest.mock import patch, MagicMock

from src.integrations.langfuse_client import get_current_trace_id


class TestGetCurrentTraceId:
    @patch("src.integrations.langfuse_client.get_langfuse_client")
    def test_returns_trace_id(self, mock_get_client):
        mock_client = MagicMock()
        mock_client.get_current_trace_id.return_value = "abc-123-def-456"
        mock_get_client.return_value = mock_client

        result = get_current_trace_id()

        assert result == "abc-123-def-456"
        mock_client.get_current_trace_id.assert_called_once()

    @patch("src.integrations.langfuse_client.get_langfuse_client")
    def test_returns_none_when_client_not_configured(self, mock_get_client):
        mock_get_client.return_value = None

        result = get_current_trace_id()

        assert result is None

    @patch("src.integrations.langfuse_client.get_langfuse_client")
    def test_returns_none_on_exception(self, mock_get_client):
        mock_client = MagicMock()
        mock_client.get_current_trace_id.side_effect = Exception("No active trace")
        mock_get_client.return_value = mock_client

        result = get_current_trace_id()

        assert result is None
