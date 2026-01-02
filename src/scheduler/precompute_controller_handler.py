# -*- coding: utf-8 -*-
"""
Lambda handler for precompute workflow orchestration (Transform Controller).

Single Responsibility: Start Step Functions workflow for parallel report precomputation.

Architecture: This is a lightweight controller that delegates orchestration to Step Functions.
- Old pattern: Fire-and-forget SQS (no observability)
- New pattern: Step Functions orchestration (full visibility, retry, completion tracking)

Triggered by: Manual invocation OR EventBridge (optional daily schedule)

The Step Functions state machine handles:
1. GetAllTickers → Query ticker_resolver for 47 tickers
2. FanOut (Map) → Submit 47 SQS messages (one per ticker)
3. WaitForCompletion → Wait for workers to finish
4. CheckProgress → Query DynamoDB jobs table
5. Decision → All done? Retry? Timeout?
6. AggregateResults → Final status report
"""

import json
import logging
import os
from datetime import datetime
from typing import Any, Dict
import traceback
import boto3

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _validate_required_config() -> None:
    """Validate required environment variables at Lambda startup.

    Defensive programming principle (CLAUDE.md #1): Validate configuration
    at startup, not on first use. Fails fast if critical config is missing.

    Raises:
        RuntimeError: If any required environment variable is missing
    """
    required_vars = {
        'PRECOMPUTE_STATE_MACHINE_ARN': 'Step Functions state machine ARN',
        'TZ': 'Bangkok timezone for date handling'
    }

    missing = {var: purpose for var, purpose in required_vars.items()
               if not os.getenv(var)}

    if missing:
        error_msg = "Missing required environment variables:\n"
        for var, purpose in missing.items():
            error_msg += f"  - {var} (needed for: {purpose})\n"
        error_msg += "\nLambda cannot start precompute workflow without these variables."
        logger.error(error_msg)
        raise RuntimeError(error_msg)

    logger.info(f"✅ All {len(required_vars)} required env vars present")


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Start Step Functions workflow for parallel precomputation.

    Event format:
        {
            "limit": 5  # Optional: limit number of tickers (for testing)
        }

    Args:
        event: Lambda event (optional limit param)
        context: Lambda context

    Returns:
        Response dict with Step Functions execution ARN
    """
    # Validate configuration at startup - fail fast!
    _validate_required_config()

    start_time = datetime.now()
    logger.info(f"Precompute Controller invoked at {start_time.isoformat()}")
    logger.info(f"Event: {json.dumps(event)}")

    try:
        # Get Step Functions state machine ARN from environment
        state_machine_arn = os.environ['PRECOMPUTE_STATE_MACHINE_ARN']

        # Create Step Functions client
        sfn_client = boto3.client('stepfunctions')

        # Prepare input for state machine
        workflow_input = {
            'limit': event.get('limit'),  # Optional limit for testing
            'triggered_at': start_time.isoformat(),
            'triggered_by': 'manual' if not event.get('source') else event.get('source')
        }

        # Start state machine execution
        execution_name = f"precompute-{start_time.strftime('%Y%m%d-%H%M%S')}"

        logger.info(f"Starting Step Functions execution: {execution_name}")
        logger.info(f"State machine ARN: {state_machine_arn}")
        logger.info(f"Workflow input: {json.dumps(workflow_input)}")

        response = sfn_client.start_execution(
            stateMachineArn=state_machine_arn,
            name=execution_name,
            input=json.dumps(workflow_input)
        )

        execution_arn = response['executionArn']
        logger.info(f"Step Functions execution started: {execution_arn}")

        end_time = datetime.now()
        duration_seconds = (end_time - start_time).total_seconds()

        return {
            'statusCode': 200,
            'body': {
                'message': 'Precompute workflow started',
                'execution_arn': execution_arn,
                'execution_name': execution_name,
                'state_machine_arn': state_machine_arn,
                'workflow_input': workflow_input,
                'duration_seconds': duration_seconds,
                'console_url': f"https://console.aws.amazon.com/states/home?region={os.environ.get('AWS_REGION', 'ap-southeast-1')}#/executions/details/{execution_arn}"
            }
        }

    except Exception as e:
        logger.error(f"Failed to start precompute workflow: {e}")
        logger.error(traceback.format_exc())

        return {
            'statusCode': 500,
            'body': {
                'message': 'Failed to start precompute workflow',
                'error': str(e),
                'traceback': traceback.format_exc()
            }
        }


# For local testing
if __name__ == '__main__':
    # Test with limit
    test_event = {'limit': 5}
    result = lambda_handler(test_event, None)
    print(json.dumps(result, indent=2))
