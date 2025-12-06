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
