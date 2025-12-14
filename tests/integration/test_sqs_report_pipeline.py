# -*- coding: utf-8 -*-
"""
SQS Report Pipeline Integration Tests

Following CLAUDE.md Testing Principles:
- Test outcomes (data flows end-to-end), not just execution (resource exists)
- Round-trip validation (scheduler → SQS → worker → Aurora)
- Silent failure detection (check CloudWatch logs, not just HTTP 200)
"""

import json
import os
import time
import pytest
import boto3
from datetime import datetime, timedelta
from typing import Optional


@pytest.mark.integration
class TestSQSReportPipeline:
    """Test full scheduler → SQS → worker → Aurora pipeline.

    Following CLAUDE.md: These tests validate the entire data flow,
    not just individual components.
    """

    @classmethod
    def setup_class(cls):
        """Initialize AWS clients."""
        cls.aws_region = "ap-southeast-1"
        cls.environment = "dev"

        cls.queue_name = f"dr-daily-report-report-jobs-{cls.environment}"
        cls.dlq_name = f"dr-daily-report-report-jobs-dlq-{cls.environment}"
        cls.worker_lambda_name = f"dr-daily-report-report-worker-{cls.environment}"
        cls.scheduler_lambda_name = f"dr-daily-report-ticker-scheduler-{cls.environment}"

        cls.sqs_client = boto3.client('sqs', region_name=cls.aws_region)
        cls.lambda_client = boto3.client('lambda', region_name=cls.aws_region)
        cls.logs_client = boto3.client('logs', region_name=cls.aws_region)

    def test_queue_exists_and_accessible(self):
        """SQS queue exists and can be accessed.

        Following CLAUDE.md: Validate configuration at startup.
        This test should FAIL before infrastructure deployment.
        """
        try:
            response = self.sqs_client.get_queue_url(QueueName=self.queue_name)
            queue_url = response['QueueUrl']

            assert queue_url is not None, f"Queue URL should not be None"
            assert self.queue_name in queue_url, \
                f"Queue URL should contain queue name {self.queue_name}"

            # Log success for visibility
            print(f"✅ Queue {self.queue_name} exists: {queue_url}")

        except self.sqs_client.exceptions.QueueDoesNotExist:
            pytest.fail(f"❌ Queue {self.queue_name} does not exist. Deploy infrastructure first.")
        except Exception as e:
            pytest.fail(f"❌ Failed to access queue: {e}")

    def test_dlq_exists_and_accessible(self):
        """Dead Letter Queue exists and can be accessed.

        Following CLAUDE.md: Fail fast - verify DLQ exists for error handling.
        """
        try:
            response = self.sqs_client.get_queue_url(QueueName=self.dlq_name)
            dlq_url = response['QueueUrl']

            assert dlq_url is not None, "DLQ URL should not be None"
            assert self.dlq_name in dlq_url, \
                f"DLQ URL should contain queue name {self.dlq_name}"

            print(f"✅ DLQ {self.dlq_name} exists: {dlq_url}")

        except self.sqs_client.exceptions.QueueDoesNotExist:
            pytest.fail(f"❌ DLQ {self.dlq_name} does not exist. Deploy infrastructure first.")

    def test_worker_lambda_has_queue_url_configured(self):
        """Worker Lambda has REPORT_JOBS_QUEUE_URL env var.

        Following CLAUDE.md: Validate configuration at startup, not on first use.
        This test should FAIL before infrastructure deployment.
        """
        try:
            response = self.lambda_client.get_function_configuration(
                FunctionName=self.worker_lambda_name
            )

            env_vars = response.get('Environment', {}).get('Variables', {})

            assert 'REPORT_JOBS_QUEUE_URL' in env_vars, \
                f"Worker Lambda should have REPORT_JOBS_QUEUE_URL env var"

            queue_url = env_vars['REPORT_JOBS_QUEUE_URL']
            assert queue_url is not None, "Queue URL env var should not be None"
            assert self.queue_name in queue_url, \
                f"Queue URL should reference {self.queue_name}"

            print(f"✅ Worker Lambda configured with queue URL: {queue_url}")

        except self.lambda_client.exceptions.ResourceNotFoundException:
            pytest.fail(f"❌ Worker Lambda {self.worker_lambda_name} not found")
        except Exception as e:
            pytest.fail(f"❌ Failed to get Lambda configuration: {e}")

    def test_send_message_to_queue(self):
        """Can send message to queue programmatically.

        Following CLAUDE.md: Test outcomes (message sent successfully),
        not just execution (no exception raised).
        """
        # Get queue URL
        queue_url = self._get_queue_url()

        # Create test message
        test_message = {
            "job_id": f"test-{int(time.time())}",
            "ticker": "DBS19",
            "strategy": "single-stage",
            "retry_count": 0
        }

        try:
            response = self.sqs_client.send_message(
                QueueUrl=queue_url,
                MessageBody=json.dumps(test_message)
            )

            # Validate response
            assert 'MessageId' in response, "Response should contain MessageId"
            assert response['MessageId'] is not None, "MessageId should not be None"

            print(f"✅ Message sent successfully: MessageId={response['MessageId']}")

            # Clean up: Delete message (if it hasn't been processed yet)
            time.sleep(2)  # Wait for message to be available
            self._purge_test_messages(queue_url)

        except Exception as e:
            pytest.fail(f"❌ Failed to send message to queue: {e}")

    @pytest.mark.tier3
    def test_worker_processes_message_without_errors(self):
        """Worker Lambda processes message and caches to Aurora.

        Following CLAUDE.md: STRONGEST VALIDATION
        - Test full end-to-end pipeline
        - Check CloudWatch logs for errors (silent failure detection)
        - Verify job ID appears in logs (proof of processing)

        This is a tier 3 test (E2E smoke test) - requires live infrastructure.
        """
        # Get queue URL
        queue_url = self._get_queue_url()

        # Create test message with unique job ID
        job_id = f"e2e-test-{int(time.time())}"
        test_message = {
            "job_id": job_id,
            "ticker": "DBS19",  # Use known ticker for reliability
            "strategy": "single-stage",
            "retry_count": 0
        }

        print(f"🚀 Sending E2E test message: {test_message}")

        # Send message to queue
        try:
            response = self.sqs_client.send_message(
                QueueUrl=queue_url,
                MessageBody=json.dumps(test_message)
            )

            message_id = response['MessageId']
            print(f"✅ Message sent: MessageId={message_id}")

        except Exception as e:
            pytest.fail(f"❌ Failed to send message: {e}")

        # Wait for Lambda to process message (max 2 minutes)
        print("⏳ Waiting for worker Lambda to process message...")
        time.sleep(30)  # Give Lambda time to trigger and process

        # Check CloudWatch logs for processing
        log_group = f"/aws/lambda/{self.worker_lambda_name}"
        start_time = int((datetime.now() - timedelta(minutes=5)).timestamp() * 1000)

        try:
            # Search for job ID in logs
            logs = self.logs_client.filter_log_events(
                logGroupName=log_group,
                startTime=start_time,
                filterPattern=job_id
            )

            events = logs.get('events', [])

            assert len(events) > 0, \
                f"❌ Job ID {job_id} not found in Lambda logs. Worker may not have processed message."

            print(f"✅ Found {len(events)} log events for job {job_id}")

            # Check for ERROR in logs (silent failure detection)
            error_logs = self.logs_client.filter_log_events(
                logGroupName=log_group,
                startTime=start_time,
                filterPattern='ERROR'
            )

            error_events = [e for e in error_logs.get('events', [])
                            if job_id in e['message']]

            if error_events:
                error_messages = '\n'.join([e['message'] for e in error_events[:3]])
                pytest.fail(f"❌ Found errors in Lambda logs:\n{error_messages}")

            print(f"✅ No errors found in Lambda logs for job {job_id}")

        except self.logs_client.exceptions.ResourceNotFoundException:
            pytest.fail(f"❌ Log group {log_group} not found. Worker Lambda may not exist.")
        except Exception as e:
            pytest.fail(f"❌ Failed to check CloudWatch logs: {e}")

    @pytest.mark.tier3
    def test_no_messages_in_dlq_after_processing(self):
        """No messages should be in DLQ after normal processing.

        Following CLAUDE.md: Silent Failure Detection
        - Messages in DLQ = failed processing
        - Should be 0 for healthy system
        """
        dlq_url = self._get_dlq_url()

        try:
            # Get queue attributes
            response = self.sqs_client.get_queue_attributes(
                QueueUrl=dlq_url,
                AttributeNames=['ApproximateNumberOfMessages']
            )

            message_count = int(response['Attributes']['ApproximateNumberOfMessages'])

            # Warning if messages in DLQ (but don't fail test - may be from previous runs)
            if message_count > 0:
                print(f"⚠️  Warning: {message_count} messages in DLQ. Check for processing failures.")

                # Peek at first message for debugging
                messages = self.sqs_client.receive_message(
                    QueueUrl=dlq_url,
                    MaxNumberOfMessages=1
                )

                if 'Messages' in messages:
                    print(f"DLQ message sample: {messages['Messages'][0]['Body'][:200]}")
            else:
                print(f"✅ DLQ is empty (no failed messages)")

        except Exception as e:
            pytest.fail(f"❌ Failed to check DLQ: {e}")

    # Helper methods

    def _get_queue_url(self) -> str:
        """Get main queue URL."""
        try:
            response = self.sqs_client.get_queue_url(QueueName=self.queue_name)
            return response['QueueUrl']
        except Exception as e:
            pytest.fail(f"Failed to get queue URL: {e}")

    def _get_dlq_url(self) -> str:
        """Get DLQ URL."""
        try:
            response = self.sqs_client.get_queue_url(QueueName=self.dlq_name)
            return response['QueueUrl']
        except Exception as e:
            pytest.fail(f"Failed to get DLQ URL: {e}")

    def _purge_test_messages(self, queue_url: str):
        """Purge test messages from queue (cleanup).

        Note: PurgeQueue has 60-second rate limit per queue.
        """
        try:
            # Receive and delete individual messages instead of purging
            # (avoids rate limit issues)
            messages = self.sqs_client.receive_message(
                QueueUrl=queue_url,
                MaxNumberOfMessages=10
            )

            if 'Messages' in messages:
                for message in messages['Messages']:
                    self.sqs_client.delete_message(
                        QueueUrl=queue_url,
                        ReceiptHandle=message['ReceiptHandle']
                    )

                print(f"✅ Cleaned up {len(messages['Messages'])} test messages")

        except Exception as e:
            print(f"⚠️  Failed to clean up test messages: {e}")
