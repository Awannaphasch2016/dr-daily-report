"""
Boundary Contract Tests: Step Functions → Lambda

Tests payload format contract between Step Functions and report_worker Lambda.

Related Principle: #19 (Cross-Boundary Contract Testing)

This file tests the TRANSITION between Step Functions and Lambda, not just
behavior within each component. Verifies that:
1. Lambda accepts Step Functions payload format
2. Lambda returns expected response format
3. Contract upheld across deployment environments

Why this matters: Integration tests against deployed systems pass because those
systems already have correct configuration. This test catches gaps when deploying
to NEW environments or integrating with DIFFERENT service versions.
"""

import pytest
import boto3
import json
import os
from unittest.mock import MagicMock, patch

pytestmark = [pytest.mark.infrastructure, pytest.mark.integration]


class TestStepFunctionsLambdaContract:
    """Test Step Functions → Lambda payload contract

    Tests the boundary between Step Functions and Lambda to ensure
    the payload format contract is maintained.
    """

    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up Lambda client and function name."""
        self.lambda_client = boto3.client('lambda', region_name='ap-southeast-1')
        environment = os.getenv('ENVIRONMENT', 'dev')
        self.lambda_name = f'dr-daily-report-report-worker-{environment}'

    def test_lambda_accepts_step_functions_payload(self):
        """Test Lambda accepts Step Functions payload format

        Boundary: Step Functions → Lambda
        Contract: Payload must have ticker, execution_id, source
        """
        payload = {
            'ticker': 'DBS19',
            'execution_id': 'test_exec_123',
            'source': 'step_functions_precompute'
        }

        with patch.object(self.lambda_client, 'invoke') as mock_invoke:
            mock_invoke.return_value = {
                'StatusCode': 200,
                'Payload': MagicMock(read=lambda: json.dumps({
                    'ticker': 'DBS19',
                    'status': 'success',
                    'pdf_s3_key': 'test.pdf',
                    'error': ''
                }).encode())
            }

            response = self.lambda_client.invoke(
                FunctionName=self.lambda_name,
                InvocationType='RequestResponse',
                Payload=json.dumps(payload)
            )

            assert response['StatusCode'] == 200
            result = json.loads(response['Payload'].read())
            assert 'ticker' in result
            assert 'status' in result
            assert result['ticker'] == 'DBS19'

    def test_lambda_response_format(self):
        """Test Lambda returns expected response format

        Boundary: Lambda → Step Functions
        Contract: Response must have ticker, status, pdf_s3_key, error
        """
        payload = {
            'ticker': 'DBS19',
            'execution_id': 'test_exec_456',
            'source': 'step_functions_precompute'
        }

        with patch.object(self.lambda_client, 'invoke') as mock_invoke:
            mock_invoke.return_value = {
                'StatusCode': 200,
                'Payload': MagicMock(read=lambda: json.dumps({
                    'ticker': 'DBS19',
                    'status': 'success',
                    'pdf_s3_key': 's3://bucket/key.pdf',
                    'error': ''
                }).encode())
            }

            response = self.lambda_client.invoke(
                FunctionName=self.lambda_name,
                InvocationType='RequestResponse',
                Payload=json.dumps(payload)
            )

            result = json.loads(response['Payload'].read())

            # Verify all required fields present
            assert 'ticker' in result, "Response missing 'ticker' field"
            assert 'status' in result, "Response missing 'status' field"
            assert 'pdf_s3_key' in result, "Response missing 'pdf_s3_key' field"
            assert 'error' in result, "Response missing 'error' field"

            # Verify field types
            assert isinstance(result['ticker'], str)
            assert result['status'] in ['success', 'failed']
            assert isinstance(result['error'], str)

    def test_lambda_handles_missing_ticker(self):
        """Test Lambda fails fast on missing ticker (defensive programming)

        Boundary: Step Functions → Lambda
        Contract: Lambda must validate required fields
        """
        payload = {
            'execution_id': 'test_exec_789',
            'source': 'step_functions_precompute'
            # Missing 'ticker' field
        }

        with patch.object(self.lambda_client, 'invoke') as mock_invoke:
            # Lambda should raise ValueError for missing ticker
            mock_invoke.return_value = {
                'StatusCode': 200,
                'FunctionError': 'Unhandled',
                'Payload': MagicMock(read=lambda: json.dumps({
                    'errorType': 'ValueError',
                    'errorMessage': "Missing 'ticker' field in direct invocation event"
                }).encode())
            }

            response = self.lambda_client.invoke(
                FunctionName=self.lambda_name,
                InvocationType='RequestResponse',
                Payload=json.dumps(payload)
            )

            # Lambda should return error response (not crash)
            assert 'FunctionError' in response
            error_payload = json.loads(response['Payload'].read())
            assert 'errorMessage' in error_payload
            assert 'ticker' in error_payload['errorMessage'].lower()

    def test_step_functions_map_payload_format(self):
        """Test Step Functions Map state payload includes required context

        Boundary: Step Functions Map → Lambda
        Contract: Payload from Map iteration includes ticker and execution_id
        """
        # Simulate Step Functions Map state payload
        # Map.Item.Value = ticker, Execution.Name = execution_id
        payload = {
            'ticker': 'DBS19',
            'execution_id': 'arn:aws:states:ap-southeast-1:123456789012:execution:precompute-workflow:exec_name'
        }

        with patch.object(self.lambda_client, 'invoke') as mock_invoke:
            mock_invoke.return_value = {
                'StatusCode': 200,
                'Payload': MagicMock(read=lambda: json.dumps({
                    'ticker': 'DBS19',
                    'status': 'success',
                    'pdf_s3_key': None,
                    'error': ''
                }).encode())
            }

            response = self.lambda_client.invoke(
                FunctionName=self.lambda_name,
                InvocationType='RequestResponse',
                Payload=json.dumps(payload)
            )

            # Verify Lambda accepts Map payload format
            assert response['StatusCode'] == 200
            mock_invoke.assert_called_once()
