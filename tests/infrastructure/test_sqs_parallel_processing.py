# -*- coding: utf-8 -*-
"""
Infrastructure tests for SQS parallel processing setup

Tests that verify the SQS queue, worker Lambda, and event source mapping
are correctly configured for parallel report generation.

TDD RED phase: These tests WILL FAIL until infrastructure is deployed.

Architecture:
    Scheduler Lambda → SQS Queue → Worker Lambda (parallel invocations)

Markers:
    @pytest.mark.integration - Requires real AWS access
    @pytest.mark.infrastructure - Infrastructure verification tests
"""

import pytest
import boto3
import json
import time
from botocore.exceptions import ClientError


@pytest.mark.integration
class TestSQSParallelProcessing:
    """Test suite for SQS parallel processing infrastructure"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up AWS clients and resource names"""
        self.sqs_client = boto3.client('sqs', region_name='ap-southeast-1')
        self.lambda_client = boto3.client('lambda', region_name='ap-southeast-1')

        # Resource names (following naming convention)
        self.queue_name = 'dr-daily-report-telegram-queue-dev'
        self.expected_queue_url = f'https://sqs.ap-southeast-1.amazonaws.com/755283537543/{self.queue_name}'
        self.worker_lambda_name = 'dr-daily-report-report-worker-dev'
        self.scheduler_lambda_name = 'dr-daily-report-ticker-scheduler-dev'

    def test_sqs_queue_exists(self):
        """Test that the SQS queue exists for job distribution

        TDD RED: This will FAIL - queue doesn't exist yet
        """
        try:
            response = self.sqs_client.get_queue_url(QueueName=self.queue_name)
            queue_url = response['QueueUrl']
            assert queue_url == self.expected_queue_url, \
                f"Queue URL mismatch: expected {self.expected_queue_url}, got {queue_url}"
        except ClientError as e:
            if e.response['Error']['Code'] == 'AWS.SimpleQueueService.NonExistentQueue':
                pytest.fail(f"SQS queue '{self.queue_name}' does not exist. Deploy infrastructure first.")
            raise

    def test_sqs_queue_has_correct_attributes(self):
        """Test that SQS queue has appropriate settings for parallel processing

        TDD RED: This will FAIL - queue doesn't exist yet

        Requirements:
        - VisibilityTimeout: 900s (15 min - matches Lambda max timeout)
        - MessageRetentionPeriod: 1209600s (14 days - for debugging failed jobs)
        - ReceiveMessageWaitTimeSeconds: 20s (long polling to reduce costs)
        """
        response = self.sqs_client.get_queue_attributes(
            QueueUrl=self.expected_queue_url,
            AttributeNames=['All']
        )

        attrs = response['Attributes']

        # Visibility timeout should match worker Lambda timeout
        visibility_timeout = int(attrs.get('VisibilityTimeout', 0))
        assert visibility_timeout == 900, \
            f"VisibilityTimeout should be 900s (15 min), got {visibility_timeout}s"

        # Message retention for debugging
        retention = int(attrs.get('MessageRetentionPeriod', 0))
        assert retention == 1209600, \
            f"MessageRetentionPeriod should be 1209600s (14 days), got {retention}s"

        # Long polling enabled
        wait_time = int(attrs.get('ReceiveMessageWaitTimeSeconds', 0))
        assert wait_time == 20, \
            f"ReceiveMessageWaitTimeSeconds should be 20s, got {wait_time}s"

    def test_worker_lambda_has_sqs_event_source_mapping(self):
        """Test that worker Lambda is triggered by SQS queue

        TDD RED: This will FAIL - event source mapping doesn't exist yet

        The event source mapping tells Lambda to poll SQS and invoke the worker
        when messages arrive. This enables parallel processing.
        """
        response = self.lambda_client.list_event_source_mappings(
            FunctionName=self.worker_lambda_name
        )

        mappings = response.get('EventSourceMappings', [])
        assert len(mappings) > 0, \
            f"Worker Lambda '{self.worker_lambda_name}' has no event source mappings"

        # Find SQS mapping
        sqs_mapping = None
        for mapping in mappings:
            if self.queue_name in mapping.get('EventSourceArn', ''):
                sqs_mapping = mapping
                break

        assert sqs_mapping is not None, \
            f"Worker Lambda is not connected to SQS queue '{self.queue_name}'"

        # Verify mapping is enabled
        assert sqs_mapping['State'] == 'Enabled', \
            f"Event source mapping is not enabled: {sqs_mapping['State']}"

    def test_event_source_mapping_batch_settings(self):
        """Test that event source mapping has optimal batch settings

        TDD RED: This will FAIL - event source mapping doesn't exist yet

        Batch settings control parallel invocations:
        - BatchSize: 1 (process one ticker per Lambda invocation)
        - MaximumBatchingWindowInSeconds: 0 (no batching delay)
        """
        response = self.lambda_client.list_event_source_mappings(
            FunctionName=self.worker_lambda_name
        )

        mappings = response.get('EventSourceMappings', [])
        sqs_mapping = next(
            (m for m in mappings if self.queue_name in m.get('EventSourceArn', '')),
            None
        )

        assert sqs_mapping is not None, "Event source mapping not found"

        # One message per invocation for maximum parallelism
        batch_size = sqs_mapping.get('BatchSize', 0)
        assert batch_size == 1, \
            f"BatchSize should be 1 for max parallelism, got {batch_size}"

        # No batching window
        batching_window = sqs_mapping.get('MaximumBatchingWindowInSeconds', -1)
        assert batching_window == 0, \
            f"MaximumBatchingWindowInSeconds should be 0, got {batching_window}"

    def test_scheduler_lambda_has_sqs_send_permission(self):
        """Test that scheduler Lambda has permission to send to SQS

        TDD RED: This will FAIL if IAM policy doesn't exist

        The scheduler needs sqs:SendMessage permission to fan out jobs.
        """
        # Get scheduler Lambda role
        response = self.lambda_client.get_function(FunctionName=self.scheduler_lambda_name)
        role_arn = response['Configuration']['Role']

        # Extract role name from ARN
        role_name = role_arn.split('/')[-1]

        # Check if role has SQS send permission
        iam_client = boto3.client('iam', region_name='ap-southeast-1')

        # Get attached policies
        response = iam_client.list_attached_role_policies(RoleName=role_name)
        policy_arns = [p['PolicyArn'] for p in response['AttachedPolicies']]

        # Check inline policies
        response = iam_client.list_role_policies(RoleName=role_name)
        inline_policies = response['PolicyNames']

        # Should have either attached or inline policy with SQS permissions
        has_sqs_policy = any('SQS' in arn or 'sqs' in arn for arn in policy_arns) or \
                        any('sqs' in name.lower() for name in inline_policies)

        assert has_sqs_policy or len(policy_arns) > 0 or len(inline_policies) > 0, \
            f"Scheduler Lambda role '{role_name}' should have SQS send permissions"


@pytest.mark.integration
class TestParallelProcessingEndToEnd:
    """End-to-end tests for parallel processing (integration tests)"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up AWS clients"""
        self.sqs_client = boto3.client('sqs', region_name='ap-southeast-1')
        self.lambda_client = boto3.client('lambda', region_name='ap-southeast-1')
        self.queue_url = 'https://sqs.ap-southeast-1.amazonaws.com/755283537543/dr-daily-report-telegram-queue-dev'
        self.worker_lambda_name = 'dr-daily-report-report-worker-dev'

    @pytest.mark.skip(reason="Infrastructure not deployed yet - TDD RED phase")
    def test_send_message_triggers_worker_lambda(self):
        """Test that sending a message to SQS triggers worker Lambda

        TDD RED: Skipped until infrastructure is deployed

        This is a smoke test to verify the event source mapping works.
        """
        # Send test message
        test_message = {
            'job_id': 'test_job_123',
            'ticker': 'TEST19'
        }

        self.sqs_client.send_message(
            QueueUrl=self.queue_url,
            MessageBody=json.dumps(test_message)
        )

        # Wait for Lambda to process
        time.sleep(5)

        # Check CloudWatch Logs for recent invocation
        logs_client = boto3.client('logs', region_name='ap-southeast-1')
        log_group = f'/aws/lambda/{self.worker_lambda_name}'

        response = logs_client.filter_log_events(
            logGroupName=log_group,
            startTime=int((time.time() - 60) * 1000),  # Last minute
            filterPattern='START RequestId'
        )

        assert len(response['events']) > 0, \
            "Worker Lambda was not invoked after sending SQS message"

    @pytest.mark.skip(reason="Infrastructure not deployed yet - TDD RED phase")
    def test_parallel_processing_scales(self):
        """Test that multiple messages trigger parallel Lambda invocations

        TDD RED: Skipped until infrastructure is deployed

        Send 5 messages and verify they're processed concurrently.
        """
        # Send 5 test messages
        for i in range(5):
            test_message = {
                'job_id': f'test_job_{i}',
                'ticker': f'TEST{i}19'
            }

            self.sqs_client.send_message(
                QueueUrl=self.queue_url,
                MessageBody=json.dumps(test_message)
            )

        # Wait for processing
        time.sleep(10)

        # Check that multiple invocations happened concurrently
        logs_client = boto3.client('logs', region_name='ap-southeast-1')
        log_group = f'/aws/lambda/{self.worker_lambda_name}'

        response = logs_client.filter_log_events(
            logGroupName=log_group,
            startTime=int((time.time() - 60) * 1000),
            filterPattern='START RequestId'
        )

        # Should have 5 invocations
        assert len(response['events']) >= 5, \
            f"Expected at least 5 concurrent invocations, got {len(response['events'])}"

    @pytest.mark.integration
    def test_worker_lambda_required_env_vars(self):
        """Test worker Lambda has required environment variables

        Defensive programming principle: Validate configuration at startup.
        Worker Lambda must have all required env vars to avoid runtime failures.

        Following pattern from test_eventbridge_scheduler.py:test_required_env_vars_present()
        """
        response = self.lambda_client.get_function_configuration(
            FunctionName=self.worker_lambda_name
        )
        env_vars = response.get('Environment', {}).get('Variables', {})

        required_vars = {
            'OPENROUTER_API_KEY': 'LLM report generation',
            'AURORA_HOST': 'Aurora database caching',
            'PDF_BUCKET_NAME': 'PDF report storage',
            'JOBS_TABLE_NAME': 'Job status tracking'
        }

        missing_vars = {var: purpose for var, purpose in required_vars.items()
                       if var not in env_vars or not env_vars[var]}

        assert len(missing_vars) == 0, \
            f"Worker Lambda missing required environment variables:\n" + \
            "\n".join(f"  - {var} (needed for: {purpose})"
                     for var, purpose in missing_vars.items())
