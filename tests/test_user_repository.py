"""Tests for UserRepository.

Validates SQL generation and interceptor integration with mocked Aurora client.
"""

import logging
import pytest
from unittest.mock import MagicMock, patch

from src.data.aurora.user_repository import UserRepository
import src.request_interceptor as interceptor_module
from src.request_interceptor import handler


@pytest.fixture
def mock_client():
    client = MagicMock()
    client.execute.return_value = 1
    client.fetch_one.return_value = {"id": 7}
    return client


@pytest.fixture
def repo(mock_client):
    with patch("src.data.aurora.user_repository.get_aurora_client", return_value=mock_client):
        return UserRepository()


class TestUpsertUser:
    def test_inserts_new_user(self, repo, mock_client):
        uid = repo.upsert_user("line", "U123abc")

        assert uid == 7
        call_args = mock_client.execute.call_args
        assert "INSERT INTO users" in call_args[0][0]
        assert "ON DUPLICATE KEY UPDATE" in call_args[0][0]
        assert call_args[0][1] == ("line", "U123abc")

    def test_fetches_user_id_after_upsert(self, repo, mock_client):
        uid = repo.upsert_user("telegram", "99999")

        assert uid == 7
        fetch_args = mock_client.fetch_one.call_args
        assert "SELECT id FROM users" in fetch_args[0][0]
        assert fetch_args[0][1] == ("telegram", "99999")

    def test_increments_request_count(self, repo, mock_client):
        repo.upsert_user("line", "U123abc")

        sql = mock_client.execute.call_args[0][0]
        assert "request_count = request_count + 1" in sql


class TestRecordRequest:
    def test_inserts_request(self, repo, mock_client):
        repo.record_request(7, "DBS19", "line", "cache_hit", 45.3, "req-abc")

        call_args = mock_client.execute.call_args
        assert "INSERT INTO user_requests" in call_args[0][0]
        assert "response_body" in call_args[0][0]
        assert call_args[0][1] == (7, "DBS19", "line", "cache_hit", 45, "req-abc", None)

    def test_handles_none_duration(self, repo, mock_client):
        repo.record_request(7, "DBS19", "line", "cache_miss", None, None)

        call_args = mock_client.execute.call_args
        assert call_args[0][1] == (7, "DBS19", "line", "cache_miss", None, None, None)

    def test_stores_response_body(self, repo, mock_client):
        repo.record_request(7, "DBS19", "line", "cache_hit", 100, "req-1",
                            response_body="Report text here")

        call_args = mock_client.execute.call_args
        assert call_args[0][1] == (7, "DBS19", "line", "cache_hit", 100, "req-1",
                                   "Report text here")

    def test_truncates_response_body_over_10kb(self, repo, mock_client):
        long_body = "x" * 15000
        repo.record_request(7, "DBS19", "line", "cache_hit", 50, "req-2",
                            response_body=long_body)

        call_args = mock_client.execute.call_args
        stored_body = call_args[0][1][6]
        assert len(stored_body) == 10000


class TestInterceptorAuroraIntegration:
    @pytest.fixture(autouse=True)
    def reset_interceptor(self, monkeypatch):
        interceptor_module._is_cold_start = True
        interceptor_module._original_handler = None
        monkeypatch.delenv("ORIGINAL_HANDLER", raising=False)
        monkeypatch.delenv("INTERCEPTOR_DISABLED", raising=False)

    def test_aurora_write_failure_does_not_break_response(self, monkeypatch):
        """If Aurora is down, interceptor still returns the response."""
        mock_handler = MagicMock(return_value={"statusCode": 200, "body": "ok"})
        interceptor_module._original_handler = mock_handler
        monkeypatch.setenv("ORIGINAL_HANDLER", "lambda_handler.lambda_handler")

        # Mock _record_to_aurora to raise
        with patch.object(interceptor_module, "_record_to_aurora",
                          side_effect=Exception("Aurora connection refused")):
            ctx = MagicMock()
            ctx.aws_request_id = "test-123"
            event = {
                "body": '{"events":[{"type":"message","source":{"userId":"U999"},'
                        '"message":{"type":"text","text":"DBS19"},"replyToken":"t"}]}',
                "headers": {"x-line-signature": "sig"},
            }
            response = handler(event, ctx)

        assert response["statusCode"] == 200
        mock_handler.assert_called_once()
