"""
Lambda handler for Fund Data Sync triggered by SQS events.

Receives SQS messages containing S3 ObjectCreated events and orchestrates
the ETL pipeline: S3 → CSV Parse → Aurora Batch Upsert.

Architecture:
    S3 ObjectCreated Event → SQS Queue → Lambda (this handler) → Aurora

Handler Behavior:
- Processes SQS message batches (up to 10 messages per invocation)
- Returns batchItemFailures for failed messages (SQS will retry)
- Continues processing remaining messages even if one fails
- Logs detailed processing information for observability

Example SQS Event:
    {
        "Records": [
            {
                "messageId": "059f36b4-87a3-44ab-83d2-661975830a7d",
                "receiptHandle": "AQEBwJnKyrHigUMZj6rYigCgxlaS3SLy0a...",
                "body": "{\"Records\":[{\"s3\":{\"bucket\":{\"name\":\"bucket\"},\"object\":{\"key\":\"file.csv\"}}}]}"
            }
        ]
    }

Returns:
    {
        "statusCode": 200,
        "body": {
            "batchItemFailures": [{"itemIdentifier": "message-id-1"}],
            "successCount": 5,
            "failureCount": 1
        }
    }

Deployment:
- Runtime: Python 3.11+
- Timeout: 120 seconds (2 minutes for ETL processing)
- Memory: 512 MB (CSV parsing + batch upsert)
- VPC: Required (Aurora in private subnets)
- IAM: S3 read, SQS receive/delete, Aurora write
"""

import json
import logging
import sys
from pathlib import Path
from typing import Dict, Any, List

# Add /var/task to Python path for Lambda runtime
# This ensures imports work correctly when handler is at root level
if '/var/task' not in sys.path:
    sys.path.insert(0, '/var/task')

# Import directly from module to avoid triggering src.data.__init__.py
# which imports modules requiring yfinance (not in fund-data-sync requirements)
from src.data.etl.fund_data_sync import get_fund_data_sync_service

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Lambda handler for SQS-triggered Fund Data Sync.

    Args:
        event: SQS event with Records list containing S3 event messages
        context: Lambda context object (function_name, request_id, etc.)

    Returns:
        Lambda response with batchItemFailures for SQS partial batch response:
        {
            "statusCode": 200,
            "body": {
                "batchItemFailures": [{"itemIdentifier": "msg-id"}],
                "successCount": 5,
                "failureCount": 1
            }
        }

    SQS Partial Batch Response:
        - Messages NOT in batchItemFailures are deleted from queue (success)
        - Messages in batchItemFailures are retried by SQS
        - After maxReceiveCount retries, messages move to DLQ

    Error Handling:
        - Individual message failures do NOT stop batch processing
        - Failed messages are logged and added to batchItemFailures
        - Lambda always returns 200 (SQS sees partial success, not Lambda error)
    """
    logger.info('Starting Fund Data Sync Lambda handler')
    logger.info(f'Request ID: {context.aws_request_id}')
    logger.info(f'Function: {context.function_name}')

    # Get ETL service singleton
    service = get_fund_data_sync_service()

    # Extract SQS records
    records = event.get('Records', [])
    logger.info(f'Processing {len(records)} SQS messages')

    if not records:
        logger.warning('Received empty SQS batch (no Records)')
        return _build_response(
            batch_item_failures=[],
            success_count=0,
            failure_count=0
        )

    # Process each SQS message
    batch_item_failures = []
    success_count = 0
    failure_count = 0

    for record in records:
        message_id = record.get('messageId')
        receipt_handle = record.get('receiptHandle')
        body = record.get('body')

        logger.info(f'Processing message {message_id}')

        try:
            # Parse SQS message body (contains S3 event JSON)
            result = service.process_sqs_message(body)

            if result.get('success'):
                # Success: message will be deleted from queue
                success_count += 1
                logger.info(
                    f'Successfully processed message {message_id}: '
                    f'{result.get("records_processed", 0)} records, '
                    f'{result.get("rows_affected", 0)} rows affected, '
                    f'source: {result.get("s3_source")}'
                )
            else:
                # Processing failed: add to batchItemFailures for retry
                failure_count += 1
                error = result.get('error', 'Unknown error')
                logger.error(
                    f'Failed to process message {message_id}: {error}. '
                    f'Message will be retried by SQS.'
                )
                batch_item_failures.append({
                    'itemIdentifier': message_id
                })

        except json.JSONDecodeError as e:
            # Malformed JSON in SQS message body
            failure_count += 1
            logger.error(
                f'Failed to parse JSON in message {message_id}: {e}. '
                f'Message will be retried by SQS.'
            )
            batch_item_failures.append({
                'itemIdentifier': message_id
            })

        except Exception as e:
            # Unexpected exception during processing
            failure_count += 1
            logger.error(
                f'Unexpected error processing message {message_id}: {e}',
                exc_info=True
            )
            batch_item_failures.append({
                'itemIdentifier': message_id
            })

    # Log summary
    logger.info(
        f'Batch processing complete: '
        f'{success_count} succeeded, {failure_count} failed, '
        f'{len(batch_item_failures)} messages to retry'
    )

    # Return Lambda response with batchItemFailures
    return _build_response(
        batch_item_failures=batch_item_failures,
        success_count=success_count,
        failure_count=failure_count
    )


def _build_response(
    batch_item_failures: List[Dict[str, str]],
    success_count: int,
    failure_count: int
) -> Dict[str, Any]:
    """Build Lambda response with SQS partial batch response.

    Args:
        batch_item_failures: List of failed message IDs for SQS retry
        success_count: Number of successfully processed messages
        failure_count: Number of failed messages

    Returns:
        Lambda response dictionary:
        {
            "statusCode": 200,
            "body": JSON string with batchItemFailures
        }

    Notes:
        - Lambda always returns 200 (not 500) for partial batch response
        - SQS uses batchItemFailures to determine which messages to retry
        - Empty batchItemFailures = all messages succeeded (deleted from queue)
    """
    response_body = {
        'batchItemFailures': batch_item_failures,
        'successCount': success_count,
        'failureCount': failure_count
    }

    return {
        'statusCode': 200,
        'body': json.dumps(response_body)
    }
