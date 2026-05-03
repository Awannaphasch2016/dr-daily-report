"""Unit tests for the precompute_consumer Lambda handler.

This handler is the consumer side of the Throttled Pipeline (second instance,
the first being fund_data_sync). It reads SQS messages enqueued by the
precompute Step Functions Map state and delegates each ticker to the existing
report-worker logic via `_handle_step_functions_mode`.

These tests mock at the `_handle_step_functions_mode` boundary so no AWS
calls (Aurora, Yahoo, Langfuse) happen. We test:

- the SQS-event contract (batchItemFailures shape)
- partial-batch failure isolation (one bad message doesn't poison the rest)
- error-classification fan-out (malformed JSON, missing ticker, downstream
  exception, downstream-returned status='failed' all become a single
  itemIdentifier in batchItemFailures)
- empty-batch tolerance
"""

import json
from unittest.mock import patch, AsyncMock, Mock

import pytest


def _sqs_record(message_id: str, body_obj: dict | str) -> dict:
    """Build one SQS record. Pass dict to be JSON-encoded, or str for raw body."""
    body = body_obj if isinstance(body_obj, str) else json.dumps(body_obj)
    return {
        "messageId": message_id,
        "receiptHandle": f"handle-{message_id}",
        "body": body,
        "attributes": {"ApproximateReceiveCount": "1"},
    }


@pytest.fixture
def lambda_context():
    ctx = Mock()
    ctx.aws_request_id = "test-request-id"
    ctx.function_name = "dr-daily-report-precompute-consumer-dev"
    return ctx


class TestPrecomputeConsumerHandler:

    # ------------------------------------------------------------------
    # Happy path
    # ------------------------------------------------------------------

    def test_all_records_succeed_returns_no_failures(self, lambda_context):
        from src.lambda_handlers import precompute_consumer_handler as mod

        event = {
            "Records": [
                _sqs_record("m1", {"ticker": "AAPL", "execution_id": "exec-1", "source": "step_functions_precompute"}),
                _sqs_record("m2", {"ticker": "TSLA", "execution_id": "exec-1", "source": "step_functions_precompute"}),
                _sqs_record("m3", {"ticker": "GOOG", "execution_id": "exec-1", "source": "step_functions_precompute"}),
            ]
        }

        async def fake_step_functions_mode(sf_event):
            return {"ticker": sf_event["ticker"], "status": "success", "error": ""}

        with patch.object(mod, "_handle_step_functions_mode", side_effect=fake_step_functions_mode):
            response = mod.lambda_handler(event, lambda_context)

        assert response == {"batchItemFailures": []}

    def test_event_payload_is_passed_through_to_step_functions_mode(self, lambda_context):
        """The shape we send to _handle_step_functions_mode matches what
        report_worker.handler() builds when called from SFN directly — same
        ticker / execution_id / source keys, so the worker logic doesn't
        notice it's now coming from SQS instead of a direct invoke."""
        from src.lambda_handlers import precompute_consumer_handler as mod

        captured: list[dict] = []

        async def capture(sf_event):
            captured.append(sf_event)
            return {"ticker": sf_event["ticker"], "status": "success", "error": ""}

        event = {
            "Records": [
                _sqs_record("m1", {
                    "ticker": "MSFT",
                    "execution_id": "exec-42",
                    "source": "step_functions_precompute",
                }),
            ]
        }

        with patch.object(mod, "_handle_step_functions_mode", side_effect=capture):
            mod.lambda_handler(event, lambda_context)

        assert len(captured) == 1
        assert captured[0]["ticker"] == "MSFT"
        assert captured[0]["execution_id"] == "exec-42"
        assert captured[0]["source"] == "step_functions_precompute"

    # ------------------------------------------------------------------
    # Partial-batch failure (the contract that lets SQS redrive correctly)
    # ------------------------------------------------------------------

    def test_one_failure_in_batch_is_isolated_to_that_message_id(self, lambda_context):
        from src.lambda_handlers import precompute_consumer_handler as mod

        async def fake_step_functions_mode(sf_event):
            if sf_event["ticker"] == "BAD":
                return {"ticker": "BAD", "status": "failed", "error": "yahoo 429"}
            return {"ticker": sf_event["ticker"], "status": "success", "error": ""}

        event = {
            "Records": [
                _sqs_record("m1", {"ticker": "AAPL", "execution_id": "x", "source": "s"}),
                _sqs_record("m2", {"ticker": "BAD", "execution_id": "x", "source": "s"}),
                _sqs_record("m3", {"ticker": "GOOG", "execution_id": "x", "source": "s"}),
            ]
        }

        with patch.object(mod, "_handle_step_functions_mode", side_effect=fake_step_functions_mode):
            response = mod.lambda_handler(event, lambda_context)

        assert response == {"batchItemFailures": [{"itemIdentifier": "m2"}]}

    def test_downstream_exception_becomes_batch_item_failure(self, lambda_context):
        from src.lambda_handlers import precompute_consumer_handler as mod

        async def raise_for_ticker(sf_event):
            if sf_event["ticker"] == "BOOM":
                raise RuntimeError("simulated downstream failure")
            return {"ticker": sf_event["ticker"], "status": "success", "error": ""}

        event = {
            "Records": [
                _sqs_record("m1", {"ticker": "OK", "execution_id": "x", "source": "s"}),
                _sqs_record("m2", {"ticker": "BOOM", "execution_id": "x", "source": "s"}),
            ]
        }

        with patch.object(mod, "_handle_step_functions_mode", side_effect=raise_for_ticker):
            response = mod.lambda_handler(event, lambda_context)

        assert response == {"batchItemFailures": [{"itemIdentifier": "m2"}]}

    # ------------------------------------------------------------------
    # Malformed input (poison messages)
    # ------------------------------------------------------------------

    def test_malformed_json_body_redrives_only_that_message(self, lambda_context):
        from src.lambda_handlers import precompute_consumer_handler as mod

        async def fake(_):
            return {"status": "success", "error": ""}

        event = {
            "Records": [
                _sqs_record("m1", "this-is-not-json{{"),
                _sqs_record("m2", {"ticker": "AAPL", "execution_id": "x", "source": "s"}),
            ]
        }

        with patch.object(mod, "_handle_step_functions_mode", side_effect=fake):
            response = mod.lambda_handler(event, lambda_context)

        assert response == {"batchItemFailures": [{"itemIdentifier": "m1"}]}

    def test_missing_ticker_field_redrives_only_that_message(self, lambda_context):
        from src.lambda_handlers import precompute_consumer_handler as mod

        async def fake(sf_event):
            return {"ticker": sf_event["ticker"], "status": "success", "error": ""}

        event = {
            "Records": [
                _sqs_record("m1", {"execution_id": "x", "source": "s"}),  # no ticker
                _sqs_record("m2", {"ticker": "TSLA", "execution_id": "x", "source": "s"}),
            ]
        }

        with patch.object(mod, "_handle_step_functions_mode", side_effect=fake):
            response = mod.lambda_handler(event, lambda_context)

        assert response == {"batchItemFailures": [{"itemIdentifier": "m1"}]}

    # ------------------------------------------------------------------
    # Edge cases
    # ------------------------------------------------------------------

    def test_empty_records_list_returns_empty_failures(self, lambda_context):
        from src.lambda_handlers import precompute_consumer_handler as mod
        response = mod.lambda_handler({"Records": []}, lambda_context)
        assert response == {"batchItemFailures": []}

    def test_no_records_key_returns_empty_failures(self, lambda_context):
        from src.lambda_handlers import precompute_consumer_handler as mod
        response = mod.lambda_handler({}, lambda_context)
        assert response == {"batchItemFailures": []}
