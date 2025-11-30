# -*- coding: utf-8 -*-
"""
Integration Tests for Report Worker

Tests that verify the async report generation pipeline works end-to-end:
1. Submit report job via API
2. Poll for completion
3. Verify report is generated correctly

This catches issues like missing dependencies (e.g., sklearn) that only
manifest when the worker Lambda actually processes the SQS message.

Usage:
    # Against deployed environment
    API_URL=https://xxx.execute-api.ap-southeast-1.amazonaws.com pytest tests/integration/test_report_worker.py -v

    # CI/CD (uses TELEGRAM_API_URL secret)
    pytest tests/integration/test_report_worker.py -v -m integration
"""

import os
import time
import pytest
import requests
from typing import Optional


# Mark all tests as integration tests (require deployed infrastructure)
pytestmark = [pytest.mark.integration, pytest.mark.slow]


# Get API URL from environment
API_URL = os.environ.get(
    "API_URL",
    os.environ.get("TELEGRAM_API_URL", "http://localhost:8001")
)

# Timeout settings
JOB_POLL_INTERVAL = 5  # seconds between status checks
JOB_TIMEOUT = 120  # max seconds to wait for job completion


def get_api_url() -> str:
    """Get the API base URL"""
    return API_URL.rstrip("/")


class TestReportWorkerIntegration:
    """Integration tests for the async report generation pipeline"""

    @pytest.mark.integration
    def test_report_job_completes_successfully(self):
        """
        End-to-end test: Submit report job and wait for completion.

        This test verifies:
        1. API can receive report requests
        2. Job is queued to SQS
        3. Worker Lambda processes the job
        4. All dependencies (including sklearn) are available
        5. Report is generated and stored
        """
        base_url = get_api_url()
        ticker = "DBS19"  # Use a known valid ticker

        # Step 1: Submit report job
        submit_url = f"{base_url}/api/v1/report/{ticker}"
        submit_response = requests.post(submit_url, timeout=30)

        assert submit_response.status_code == 200, \
            f"Failed to submit report job: {submit_response.status_code} - {submit_response.text}"

        job_data = submit_response.json()
        assert "job_id" in job_data, f"Response missing job_id: {job_data}"
        job_id = job_data["job_id"]

        print(f"\n  Job submitted: {job_id}")

        # Step 2: Poll for completion
        status_url = f"{base_url}/api/v1/report/status/{job_id}"
        start_time = time.time()
        final_status = None

        while time.time() - start_time < JOB_TIMEOUT:
            status_response = requests.get(status_url, timeout=30)
            assert status_response.status_code == 200, \
                f"Failed to get job status: {status_response.status_code}"

            status_data = status_response.json()
            status = status_data.get("status")

            print(f"  Status: {status} (elapsed: {int(time.time() - start_time)}s)")

            if status == "completed":
                final_status = status_data
                break
            elif status == "failed":
                error = status_data.get("error", "Unknown error")
                pytest.fail(f"Report job failed: {error}")
            elif status in ["pending", "processing"]:
                time.sleep(JOB_POLL_INTERVAL)
            else:
                pytest.fail(f"Unknown job status: {status}")

        # Step 3: Verify completion
        assert final_status is not None, \
            f"Job did not complete within {JOB_TIMEOUT}s timeout"
        assert final_status["status"] == "completed", \
            f"Job ended with status: {final_status['status']}"

        # Step 4: Verify result contains expected fields
        result = final_status.get("result")
        assert result is not None, "Completed job has no result"

        # Check for key report fields
        assert "ticker" in result or "report" in result, \
            f"Result missing expected fields: {list(result.keys()) if isinstance(result, dict) else type(result)}"

        print(f"  Report generated successfully!")

    @pytest.mark.integration
    def test_report_job_handles_invalid_ticker(self):
        """Test that invalid tickers are rejected gracefully"""
        base_url = get_api_url()
        ticker = "INVALID_TICKER_12345"

        submit_url = f"{base_url}/api/v1/report/{ticker}"
        response = requests.post(submit_url, timeout=30)

        # Should return 400 or 404, not 500
        assert response.status_code in [400, 404, 422], \
            f"Invalid ticker should be rejected: {response.status_code} - {response.text}"

    @pytest.mark.integration
    def test_worker_can_import_all_dependencies(self):
        """
        Verify all required modules can be imported.

        This catches missing dependency errors like 'No module named sklearn'
        before deployment.
        """
        # These imports should succeed if requirements.txt is complete
        try:
            # Core dependencies
            import numpy
            import pandas
            import scipy
            import sklearn  # This was missing!
            import matplotlib
            import networkx

            # LLM/Agent
            import langchain
            import langgraph
            import langsmith

            # Web framework
            import fastapi
            import mangum
            import boto3

            # Financial
            import yfinance
            import ta

            # The actual handler imports
            from src.report_worker_handler import handler
            from src.telegram_lambda_handler import handler as api_handler

        except ImportError as e:
            pytest.fail(f"Missing dependency: {e}")

    @pytest.mark.integration
    def test_comparative_analysis_imports(self):
        """
        Verify comparative_analysis module can be imported.

        This module uses sklearn and was the source of the import error.
        """
        try:
            from src.analysis.comparative_analysis import ComparativeAnalyzer
        except ImportError as e:
            pytest.fail(f"ComparativeAnalyzer import failed: {e}")
