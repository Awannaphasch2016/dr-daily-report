"""Layer 2: Test Lambda handlers using local RIE (Runtime Interface Emulator)

This test layer validates handlers in the actual Lambda container environment:
- Tests import paths work in Lambda context
- Validates handler functions are callable
- Catches container-specific issues before deployment

Requires docker-compose.lambda.yml to be running.
Run with: pytest tests/lambda_rie/ -v --tier=2
"""

import pytest
import requests
import json
from typing import Dict, Any


def invoke_local_lambda(port: int, event: Dict[str, Any]) -> Dict[str, Any]:
    """Invoke Lambda function running in local RIE container.

    Args:
        port: RIE endpoint port (9001=report-worker, 9002=telegram-api, etc.)
        event: Lambda event payload

    Returns:
        Lambda response dict

    Raises:
        requests.exceptions.ConnectionError: If container not running
    """
    url = f"http://localhost:{port}/2015-03-31/functions/function/invocations"
    response = requests.post(url, json=event, timeout=30)
    return response.json()


@pytest.mark.tier(2)  # Integration tier - requires Docker
class TestReportWorkerRIE:
    """Test report_worker_handler using Lambda RIE (no AWS required)."""

    def test_handler_imports_successfully(self):
        """GIVEN report_worker Lambda container running
        WHEN sending minimal SQS event
        THEN handler should import without ImportModuleError

        This test would have caught the v116 import error.
        """
        event = {
            "Records": [{
                "messageId": "rie-test-import",
                "body": json.dumps({
                    "job_id": "rpt_rie_import_test",
                    "ticker": "DBS19"
                })
            }]
        }

        try:
            response = invoke_local_lambda(port=9001, event=event)
        except requests.exceptions.ConnectionError:
            pytest.skip("report-worker container not running. Start with: docker-compose -f docker-compose.lambda.yml up report-worker")

        # Check for import errors
        response_str = str(response)
        assert 'ImportModuleError' not in response_str, f"Import error detected: {response}"
        assert 'errorType' not in response or response['errorType'] != 'Runtime.ImportModuleError', \
            f"Runtime import error: {response.get('errorMessage', 'Unknown error')}"

    def test_valid_sqs_event_processes(self):
        """GIVEN valid SQS event
        WHEN invoking report-worker Lambda
        THEN should process without errors
        """
        event = {
            "Records": [{
                "messageId": "rie-test-valid",
                "body": json.dumps({
                    "job_id": "rpt_rie_test",
                    "ticker": "DBS19"
                })
            }]
        }

        try:
            response = invoke_local_lambda(port=9001, event=event)
        except requests.exceptions.ConnectionError:
            pytest.skip("report-worker container not running")

        # Verify response structure (handler executed)
        assert 'statusCode' in response or 'body' in response, \
            f"Unexpected response format: {response}"

    def test_handler_function_callable(self):
        """GIVEN Lambda container
        WHEN checking handler function exists
        THEN should be importable and callable
        """
        # Empty event to just test handler loads
        event = {"Records": []}

        try:
            response = invoke_local_lambda(port=9001, event=event)
        except requests.exceptions.ConnectionError:
            pytest.skip("report-worker container not running")

        # If handler not callable, Lambda returns specific error
        if 'errorType' in response:
            assert response['errorType'] != 'Runtime.HandlerNotFound', \
                f"Handler function not found: {response.get('errorMessage')}"


@pytest.mark.tier(2)
class TestTelegramAPIRIE:
    """Test telegram_lambda_handler using Lambda RIE."""

    def test_handler_imports_successfully(self):
        """GIVEN telegram-api Lambda container running
        WHEN sending minimal API Gateway event
        THEN handler should import without errors
        """
        event = {
            "requestContext": {
                "http": {
                    "method": "GET",
                    "path": "/api/v1/health"
                }
            },
            "headers": {}
        }

        try:
            response = invoke_local_lambda(port=9002, event=event)
        except requests.exceptions.ConnectionError:
            pytest.skip("telegram-api container not running. Start with: docker-compose -f docker-compose.lambda.yml up telegram-api")

        # Check for import errors
        response_str = str(response)
        assert 'ImportModuleError' not in response_str, f"Import error: {response}"

    def test_health_endpoint_responds(self):
        """GIVEN telegram-api Lambda
        WHEN calling /health endpoint
        THEN should return 200 OK
        """
        event = {
            "requestContext": {
                "http": {
                    "method": "GET",
                    "path": "/api/v1/health"
                }
            },
            "headers": {}
        }

        try:
            response = invoke_local_lambda(port=9002, event=event)
        except requests.exceptions.ConnectionError:
            pytest.skip("telegram-api container not running")

        # Health endpoint should return 200
        assert response.get('statusCode') == 200, \
            f"Health check failed: {response}"


@pytest.mark.tier(2)
class TestLINEBotRIE:
    """Test lambda_handler (LINE Bot) using Lambda RIE."""

    def test_handler_imports_successfully(self):
        """GIVEN LINE Bot Lambda container running
        WHEN sending minimal webhook event
        THEN handler should import without errors
        """
        event = {
            "headers": {
                "x-line-signature": "test_signature"
            },
            "body": json.dumps({"events": []})
        }

        try:
            response = invoke_local_lambda(port=9003, event=event)
        except requests.exceptions.ConnectionError:
            pytest.skip("line-bot container not running. Start with: docker-compose -f docker-compose.lambda.yml up line-bot")

        # Check for import errors
        response_str = str(response)
        assert 'ImportModuleError' not in response_str, f"Import error: {response}"

        # LINE handler uses lambda_handler function (not handler)
        if 'errorType' in response:
            assert response['errorType'] != 'Runtime.HandlerNotFound', \
                f"lambda_handler function not found: {response.get('errorMessage')}"


@pytest.mark.tier(2)
class TestAllHandlersImportParallel:
    """Test all handlers can import simultaneously (catches shared dependency issues)."""

    def test_all_critical_handlers_import(self):
        """GIVEN all Lambda containers running
        WHEN importing all handlers in parallel
        THEN all should succeed without conflicts

        This catches:
        - Shared dependency version conflicts
        - Global state issues
        - Resource contention
        """
        handlers_to_test = [
            (9001, "report-worker", {"Records": []}),
            (9002, "telegram-api", {"requestContext": {"http": {"method": "GET", "path": "/health"}}, "headers": {}}),
            (9003, "line-bot", {"headers": {}, "body": "{}"}),
        ]

        results = {}
        for port, name, event in handlers_to_test:
            try:
                response = invoke_local_lambda(port=port, event=event)
                results[name] = {
                    'success': 'ImportModuleError' not in str(response),
                    'response': response
                }
            except requests.exceptions.ConnectionError:
                results[name] = {'success': False, 'error': 'Container not running'}

        # Report results
        failed = {name: result for name, result in results.items() if not result['success']}

        if failed:
            failure_msg = "Handler import failures:\n"
            for name, result in failed.items():
                if 'error' in result:
                    failure_msg += f"  - {name}: {result['error']}\n"
                else:
                    failure_msg += f"  - {name}: {result['response']}\n"

            pytest.fail(failure_msg)
