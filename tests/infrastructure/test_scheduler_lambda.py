# -*- coding: utf-8 -*-
"""
Infrastructure tests for Scheduler Lambda

Tests that verify the scheduler Lambda can be invoked and the precompute
functionality works correctly. These tests drive the requirement that
the deployed Lambda must have the src/scheduler module.

TDD Tests:
1. Lambda can be invoked without import errors
2. Lambda can connect to Aurora
3. Precompute action returns valid response

Markers:
    @pytest.mark.integration - Requires real AWS access
    @pytest.mark.infrastructure - Infrastructure verification tests
"""

import json
import pytest
import boto3
from botocore.exceptions import ClientError


@pytest.mark.integration
class TestSchedulerLambdaHealth:
    """Test suite for scheduler Lambda health and functionality"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up AWS clients"""
        self.lambda_client = boto3.client('lambda', region_name='ap-southeast-1')
        self.function_name = 'dr-daily-report-ticker-scheduler-dev'

    def test_lambda_can_be_invoked_without_import_error(self):
        """Test that Lambda can be invoked without module import errors

        This test verifies that the deployed Docker image contains
        the src/scheduler module. If this fails, the image needs to
        be rebuilt and redeployed.
        """
        # Invoke with a simple health check action
        response = self.lambda_client.invoke(
            FunctionName=self.function_name,
            InvocationType='RequestResponse',
            Payload=json.dumps({'action': 'health'})
        )

        # Read response
        payload = json.loads(response['Payload'].read().decode('utf-8'))

        # Check for import errors
        if 'errorType' in payload:
            if payload.get('errorType') == 'Runtime.ImportModuleError':
                pytest.fail(
                    f"Lambda has import error: {payload.get('errorMessage')}. "
                    "The Docker image is stale and needs to be rebuilt with "
                    "the src/scheduler module included."
                )
            # Other errors might be acceptable for health check

        # Function should not have FunctionError
        assert 'FunctionError' not in response, (
            f"Lambda invocation failed: {payload}"
        )

    def test_lambda_precompute_action_responds(self):
        """Test that precompute action can be invoked

        This test verifies the scheduler can handle precompute requests.
        It doesn't validate the full precomputation, just that the
        handler recognizes the action.
        """
        response = self.lambda_client.invoke(
            FunctionName=self.function_name,
            InvocationType='RequestResponse',
            Payload=json.dumps({
                'action': 'precompute',
                'symbol': 'TEST_TICKER',  # Non-existent ticker for quick failure
                'include_report': False
            })
        )

        payload = json.loads(response['Payload'].read().decode('utf-8'))

        # Should not have import errors
        if 'errorType' in payload:
            if 'ImportModuleError' in payload.get('errorType', ''):
                pytest.fail(
                    f"Lambda module import failed: {payload.get('errorMessage')}"
                )

        # Response should have statusCode (even if precompute failed for test ticker)
        # The key is that the handler was reached, not that precompute succeeded
        assert 'FunctionError' not in response or 'statusCode' in payload, (
            f"Precompute action not recognized: {payload}"
        )


@pytest.mark.integration
class TestSchedulerAuroraConnectivity:
    """Test suite for scheduler Lambda Aurora connectivity"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up AWS clients"""
        self.lambda_client = boto3.client('lambda', region_name='ap-southeast-1')
        self.function_name = 'dr-daily-report-ticker-scheduler-dev'

    def test_lambda_can_connect_to_aurora(self):
        """Test that Lambda can establish Aurora connection

        This test verifies VPC configuration, security groups, and
        Aurora credentials are correctly configured.
        """
        # Use aurora_setup action which tests connection
        response = self.lambda_client.invoke(
            FunctionName=self.function_name,
            InvocationType='RequestResponse',
            Payload=json.dumps({
                'action': 'aurora_setup',
                'create_tables_only': True  # Just test connection, don't modify
            })
        )

        payload = json.loads(response['Payload'].read().decode('utf-8'))

        # Check for import errors first
        if 'errorType' in payload:
            if 'ImportModuleError' in payload.get('errorType', ''):
                pytest.skip(
                    f"Skipping Aurora test - Lambda has import error: "
                    f"{payload.get('errorMessage')}"
                )

        # Check response indicates successful connection
        if 'FunctionError' in response:
            # Parse the error to see if it's connection-related
            error_msg = payload.get('errorMessage', '')
            if 'Connection' in error_msg or 'timeout' in error_msg.lower():
                pytest.fail(
                    f"Lambda cannot connect to Aurora: {error_msg}. "
                    "Check VPC configuration, security groups, and Aurora endpoint."
                )

        # Should have statusCode indicating handler executed
        assert 'statusCode' in payload or 'body' in payload, (
            f"Aurora setup action did not return expected response: {payload}"
        )


@pytest.mark.integration
class TestSchedulerPrecomputeSuccess:
    """Test suite for verifying precompute actually succeeds

    TDD Tests that catch schema mismatches and silent failures.
    Previous gap: tests verified Lambda CAN invoke but not that
    database writes SUCCEED.
    """

    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up AWS clients"""
        self.lambda_client = boto3.client('lambda', region_name='ap-southeast-1')
        self.function_name = 'dr-daily-report-ticker-scheduler-dev'

    def test_precompute_succeeds_without_schema_errors(self):
        """Test that precompute doesn't fail with schema errors

        Regression Test: Catches database schema mismatches like:
        - "Unknown column 'date' in 'field list'"
        - FK constraint failures (silent, rowcount=0)
        - ENUM value mismatches (silent, rowcount=0)

        This test verifies the database schema matches what precompute
        service expects. Previous gap: tests verified Lambda CAN invoke
        but not that precompute SUCCEEDS.
        """
        # Invoke precompute with a real ticker
        response = self.lambda_client.invoke(
            FunctionName=self.function_name,
            InvocationType='RequestResponse',
            Payload=json.dumps({
                'action': 'precompute',
                'symbol': 'NVDA',  # Real ticker (should succeed)
                'include_report': False  # Faster, no LLM call
            })
        )

        payload = json.loads(response['Payload'].read().decode('utf-8'))

        # Should not have FunctionError
        assert 'FunctionError' not in response, (
            f"Precompute failed with exception: {payload}"
        )

        # Response should have body with success indicator
        assert 'body' in payload, f"No body in response: {payload}"
        body = payload['body']

        # Check for schema errors in response
        if isinstance(body, dict):
            # Check details for schema-related errors
            details = body.get('details', [])
            if details and len(details) > 0:
                first_detail = details[0]
                error_msg = first_detail.get('error', '')

                # Fail if schema mismatch detected
                if 'Unknown column' in error_msg:
                    pytest.fail(
                        f"Database schema mismatch detected: {error_msg}. "
                        f"The code references a column that doesn't exist in Aurora. "
                        f"Check precompute_service.py SQL queries."
                    )

                # Fail if FK constraint detected (indicates schema mismatch)
                if 'foreign key constraint' in error_msg.lower():
                    pytest.fail(
                        f"Foreign key constraint failure: {error_msg}. "
                        f"This may indicate ticker_id doesn't exist in ticker_master."
                    )

            # Verify at least one success
            success_count = body.get('success', 0)
            total_count = body.get('total', 0)

            assert success_count > 0 or total_count == 0, (
                f"Precompute processed {total_count} tickers but 0 succeeded. "
                f"This indicates all database writes failed (likely schema mismatch). "
                f"Details: {details}"
            )
