# -*- coding: utf-8 -*-
"""
Integration tests for scheduler -> precompute trigger flow.

These tests verify the end-to-end integration between:
1. Scheduler (ticker_fetcher_handler)
2. Precompute trigger (async Lambda invocation)
3. Step Functions state machine

Tier: 2 (integration tests)
Runtime: ~30-60 seconds per test
Requires: AWS credentials, deployed Lambda functions
"""

import pytest
import json
import time
import boto3
from datetime import datetime
from typing import Dict, Any


@pytest.mark.integration
class TestPrecomputeTriggerIntegration:
    """Integration tests for precompute trigger flow."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up AWS clients and resources."""
        self.lambda_client = boto3.client('lambda')
        self.sfn_client = boto3.client('stepfunctions')
        self.sqs_client = boto3.client('sqs')

        # Get resource ARNs from environment
        import os
        self.scheduler_function = os.environ.get('SCHEDULER_FUNCTION_NAME')
        self.precompute_controller_arn = os.environ.get('PRECOMPUTE_CONTROLLER_ARN')
        self.state_machine_arn = os.environ.get('PRECOMPUTE_STATE_MACHINE_ARN')

        if not all([self.scheduler_function, self.precompute_controller_arn]):
            pytest.skip("Integration test requires deployed Lambda functions")

    def test_scheduler_triggers_precompute_on_successful_fetch(self):
        """
        GIVEN successful ticker fetch
        WHEN scheduler completes
        THEN it should trigger precompute Lambda asynchronously
        """
        # Invoke scheduler with specific tickers (faster than all tickers)
        event = {'tickers': ['NVDA', 'DBS19']}

        response = self.lambda_client.invoke(
            FunctionName=self.scheduler_function,
            InvocationType='RequestResponse',  # Wait for response
            Payload=json.dumps(event)
        )

        # Verify scheduler completed successfully
        assert response['StatusCode'] == 200, "Scheduler invocation failed"

        # Parse response
        payload = json.loads(response['Payload'].read())
        assert payload['statusCode'] == 200, f"Scheduler returned error: {payload}"

        body = payload['body']

        # Verify precompute was triggered
        assert body['precompute_triggered'] is True, "Precompute trigger flag is False"
        assert body['success_count'] > 0, "No successful fetches"

        # Note: We can't easily verify the async Lambda was invoked
        # (no direct way to check without CloudWatch Logs)
        # But we verified the scheduler returned precompute_triggered=True

    def test_scheduler_skips_precompute_when_all_fetches_fail(self):
        """
        GIVEN ticker fetch with all failures
        WHEN scheduler completes
        THEN it should NOT trigger precompute
        """
        # Invoke with invalid ticker (will fail)
        event = {'tickers': ['INVALID_TICKER_9999']}

        response = self.lambda_client.invoke(
            FunctionName=self.scheduler_function,
            InvocationType='RequestResponse',
            Payload=json.dumps(event)
        )

        # Verify scheduler completed successfully (even though fetches failed)
        assert response['StatusCode'] == 200

        payload = json.loads(response['Payload'].read())
        body = payload['body']

        # Verify precompute was NOT triggered
        assert body['success_count'] == 0, "Expected no successful fetches"
        assert body['precompute_triggered'] is False, "Precompute should not be triggered when all fetches fail"

    @pytest.mark.skipif(
        not pytest.config.getoption("--run-e2e", default=False),
        reason="E2E test requires full deployment and takes several minutes"
    )
    def test_end_to_end_scheduler_to_step_functions(self):
        """
        GIVEN full scheduler + precompute pipeline
        WHEN scheduler is invoked
        THEN Step Functions execution should start and complete

        This is a full E2E test that:
        1. Invokes scheduler
        2. Waits for precompute trigger
        3. Polls Step Functions for execution
        4. Verifies execution completes successfully

        Runtime: ~5-10 minutes (waits for Step Functions)
        """
        if not self.state_machine_arn:
            pytest.skip("PRECOMPUTE_STATE_MACHINE_ARN not set")

        # Record start time
        test_start = datetime.utcnow()

        # Invoke scheduler with 2 tickers (fast test)
        event = {'tickers': ['NVDA', 'DBS19']}

        scheduler_response = self.lambda_client.invoke(
            FunctionName=self.scheduler_function,
            InvocationType='RequestResponse',
            Payload=json.dumps(event)
        )

        assert scheduler_response['StatusCode'] == 200

        payload = json.loads(scheduler_response['Payload'].read())
        assert payload['body']['precompute_triggered'] is True

        # Wait a few seconds for async Lambda to start Step Functions
        time.sleep(5)

        # Poll Step Functions for recent execution
        max_wait = 600  # 10 minutes
        poll_interval = 10  # seconds
        elapsed = 0

        execution_found = False
        execution_arn = None

        while elapsed < max_wait:
            # List recent executions
            executions = self.sfn_client.list_executions(
                stateMachineArn=self.state_machine_arn,
                statusFilter='RUNNING',
                maxResults=10
            )

            # Find execution started after our test
            for execution in executions['executions']:
                exec_start = execution['startDate'].replace(tzinfo=None)
                if exec_start >= test_start:
                    execution_found = True
                    execution_arn = execution['executionArn']
                    break

            if execution_found:
                break

            time.sleep(poll_interval)
            elapsed += poll_interval

        assert execution_found, f"No Step Functions execution found within {max_wait}s"

        # Wait for execution to complete
        while elapsed < max_wait:
            status = self.sfn_client.describe_execution(executionArn=execution_arn)

            if status['status'] in ['SUCCEEDED', 'FAILED', 'TIMED_OUT', 'ABORTED']:
                break

            time.sleep(poll_interval)
            elapsed += poll_interval

        # Verify execution succeeded
        final_status = self.sfn_client.describe_execution(executionArn=execution_arn)
        assert final_status['status'] == 'SUCCEEDED', \
            f"Step Functions execution failed: {final_status['status']}"

        # Verify output
        output = json.loads(final_status.get('output', '{}'))
        assert output.get('status') == 'completed', "Execution did not complete successfully"


@pytest.mark.integration
class TestStepFunctionsContract:
    """Test Step Functions input/output contracts."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up test environment."""
        import os
        self.get_ticker_function = os.environ.get('GET_TICKER_LIST_FUNCTION_NAME')
        if not self.get_ticker_function:
            pytest.skip("GET_TICKER_LIST_FUNCTION_NAME not set")

        self.lambda_client = boto3.client('lambda')

    def test_get_ticker_list_output_matches_step_functions_contract(self):
        """
        GIVEN get_ticker_list Lambda
        WHEN invoked by Step Functions
        THEN output must match $.ticker_list.tickers JSONPath
        """
        # Invoke get_ticker_list
        response = self.lambda_client.invoke(
            FunctionName=self.get_ticker_function,
            InvocationType='RequestResponse',
            Payload=json.dumps({})
        )

        assert response['StatusCode'] == 200

        # Parse output
        output = json.loads(response['Payload'].read())

        # Verify Step Functions contract
        assert 'tickers' in output, "Missing 'tickers' field (required by $.ticker_list.tickers)"
        assert 'count' in output, "Missing 'count' field"

        # Verify types
        assert isinstance(output['tickers'], list), "tickers must be a list"
        assert isinstance(output['count'], int), "count must be an integer"
        assert len(output['tickers']) == output['count'], "count must match tickers length"

        # Verify all tickers are strings (Map state requirement)
        assert all(isinstance(t, str) for t in output['tickers']), \
            "All tickers must be strings for Step Functions Map state"

        # Verify non-empty tickers
        assert all(len(t) > 0 for t in output['tickers']), \
            "Ticker symbols must not be empty"

    def test_ticker_list_is_json_serializable(self):
        """
        GIVEN get_ticker_list output
        WHEN Step Functions processes it
        THEN it must be JSON serializable (no NumPy types, datetime objects, etc.)
        """
        response = self.lambda_client.invoke(
            FunctionName=self.get_ticker_function,
            InvocationType='RequestResponse',
            Payload=json.dumps({})
        )

        output = json.loads(response['Payload'].read())

        # Attempt round-trip serialization
        json_str = json.dumps(output)
        parsed = json.loads(json_str)

        # Verify round-trip produces same result
        assert parsed == output, "Output must be JSON serializable for Step Functions"
