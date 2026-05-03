"""Lambda handler for SQS-triggered precompute report generation.

Second instance of the Throttled Pipeline pattern (first is fund_data_sync).
Step Functions enqueues one ticker per message; this Lambda's Event Source
Mapping reads the queue with bounded concurrency (the token bucket) and
delegates each ticker to the existing report-worker logic.

Architecture:
    Step Functions Map -> sqs:sendMessage -> SQS queue
    -> ESM (max_concurrency=5) -> this handler
    -> _handle_step_functions_mode -> Aurora precomputed_reports

Message body shape (sent by Step Functions):
    {"ticker": "AAPL", "execution_id": "...", "source": "step_functions_precompute"}

Returns:
    {"batchItemFailures": [{"itemIdentifier": "msg-id"}, ...]}
    SQS retries failed messages up to maxReceiveCount, then routes to DLQ.
"""

import asyncio
import json
import logging
from typing import Any

from src.report_worker_handler import _handle_step_functions_mode

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event: dict, context: Any) -> dict:
    """SQS-triggered handler. Processes one ticker per message.

    Each record's body is JSON `{"ticker": "...", ...}`. Failures are
    reported via `ReportBatchItemFailures` so SQS retries only the failed
    items, not the whole batch.
    """
    request_id = getattr(context, "aws_request_id", "unknown")
    records = event.get("Records", [])
    logger.info(f"precompute_consumer start: request_id={request_id} records={len(records)}")

    if not records:
        logger.warning("Empty SQS batch (no Records)")
        return {"batchItemFailures": []}

    batch_item_failures: list[dict[str, str]] = []
    success_count = 0
    failure_count = 0

    for record in records:
        message_id = record.get("messageId", "unknown")
        body_raw = record.get("body", "")

        try:
            body = json.loads(body_raw)
            ticker = body.get("ticker")
            if not ticker:
                raise ValueError(f"message body missing 'ticker' field: {body_raw[:200]}")

            sf_event = {
                "ticker": ticker,
                "execution_id": body.get("execution_id", ""),
                "source": body.get("source", "sqs_precompute"),
                "data_date": body.get("data_date", ""),
                "model": body.get("model", ""),
            }

            logger.info(f"processing message_id={message_id} ticker={ticker}")
            result = asyncio.run(_handle_step_functions_mode(sf_event))

            if result.get("status") == "success":
                success_count += 1
                logger.info(f"completed message_id={message_id} ticker={ticker}")
            else:
                failure_count += 1
                error = result.get("error", "unknown")
                logger.error(f"failed message_id={message_id} ticker={ticker} error={error}")
                batch_item_failures.append({"itemIdentifier": message_id})

        except json.JSONDecodeError as e:
            failure_count += 1
            logger.error(f"malformed JSON message_id={message_id}: {e}")
            batch_item_failures.append({"itemIdentifier": message_id})

        except Exception as e:
            failure_count += 1
            logger.error(f"unexpected error message_id={message_id}: {e}", exc_info=True)
            batch_item_failures.append({"itemIdentifier": message_id})

    logger.info(
        f"precompute_consumer done: success={success_count} failure={failure_count} "
        f"redrive={len(batch_item_failures)}"
    )
    return {"batchItemFailures": batch_item_failures}
