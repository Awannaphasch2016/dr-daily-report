# -*- coding: utf-8 -*-
"""
E2E Test: Validate Generation Data via API

Since the TEST CloudFront is serving Twinbar (not DR Daily Report),
we validate the API directly to ensure generation information is correct.

This test validates:
1. API is accessible
2. Report generation works
3. Generated reports contain fundamental data, chart patterns, etc.

Run with:
    pytest tests/e2e/test_validate_api_generation.py -v -m e2e
"""

import os
import time
import pytest
import requests

# Dev API URL - use dev environment
API_URL = os.environ.get(
    "TELEGRAM_API_URL",
    "https://ou0ivives1.execute-api.ap-southeast-1.amazonaws.com/api/v1"
)

# Override if E2E_BASE_URL is set (for consistency with Playwright tests)
if "E2E_BASE_URL" in os.environ:
    # Extract API URL from frontend if needed, otherwise use default
    pass  # Keep using API_URL above

pytestmark = pytest.mark.e2e


class TestAPIGenerationData:
    """Validate generation data via API"""

    def test_api_health_check(self):
        """Validate API is accessible"""
        response = requests.get(f"{API_URL}/health", timeout=10)
        assert response.status_code == 200, f"API health check failed: {response.status_code}"
        data = response.json()
        assert data.get("status") == "ok", f"API status not ok: {data}"

    def test_search_endpoint_works(self):
        """Validate search endpoint returns results"""
        response = requests.get(f"{API_URL}/search", params={"q": "NVDA"}, timeout=10)
        assert response.status_code == 200, f"Search failed: {response.status_code}"
        data = response.json()
        assert "results" in data, f"Search response missing 'results': {data}"
        assert len(data["results"]) > 0, "Search should return at least one result"

    @pytest.mark.slow
    def test_report_generation_contains_fundamental_data(self):
        """Validate generated report contains fundamental data indicators"""
        # Submit report generation job
        ticker = "DBS19"
        response = requests.post(f"{API_URL}/report/{ticker}", timeout=10)
        assert response.status_code == 200, f"Report submission failed: {response.status_code}"
        
        job_data = response.json()
        assert "job_id" in job_data, f"Response missing job_id: {job_data}"
        job_id = job_data["job_id"]

        # Poll for completion (up to 120 seconds)
        max_wait = 120
        start_time = time.time()
        while time.time() - start_time < max_wait:
            status_response = requests.get(f"{API_URL}/report/status/{job_id}", timeout=10)
            assert status_response.status_code == 200, f"Status check failed: {status_response.status_code}"
            
            status_data = status_response.json()
            status = status_data.get("status")
            
            if status == "completed":
                # Get the full report (allow longer timeout for large reports)
                report_response = requests.get(f"{API_URL}/report/{ticker}", timeout=30)
                assert report_response.status_code == 200, f"Report fetch failed: {report_response.status_code}"
                
                report_data = report_response.json()
                report_text = report_data.get("report", "")
                
                # Validate fundamental data indicators
                fundamental_indicators = [
                    "มูลค่าตลาด",  # Market cap
                    "P/E",  # Price-to-earnings
                    "ROE",  # Return on equity
                    "กำไร",  # Profit
                    "รายได้",  # Revenue
                ]
                
                found_fundamental = any(indicator in report_text for indicator in fundamental_indicators)
                assert found_fundamental, f"Report should contain fundamental data. Report preview: {report_text[:500]}"
                
                return  # Success
            
            elif status == "failed":
                error_msg = status_data.get("error", "Unknown error")
                pytest.fail(f"Report generation failed: {error_msg}")
            
            # Still processing, wait and retry
            time.sleep(5)
        
        pytest.fail(f"Report generation timed out after {max_wait} seconds")

    @pytest.mark.slow
    def test_report_generation_contains_chart_patterns(self):
        """Validate generated report contains chart pattern analysis"""
        ticker = "NVDA19"
        response = requests.post(f"{API_URL}/report/{ticker}", timeout=10)
        assert response.status_code == 200
        
        job_id = response.json()["job_id"]
        
        # Poll for completion
        max_wait = 120
        start_time = time.time()
        while time.time() - start_time < max_wait:
            status_response = requests.get(f"{API_URL}/report/status/{job_id}", timeout=10)
            status_data = status_response.json()
            status = status_data.get("status")
            
            if status == "completed":
                report_response = requests.get(f"{API_URL}/report/{ticker}", timeout=30)
                report_data = report_response.json()
                report_text = report_data.get("report", "")
                
                # Validate chart pattern indicators
                chart_pattern_indicators = [
                    "รูปแบบ",  # Pattern
                    "กราฟ",  # Chart
                    "เทรนด์",  # Trend
                    "แนวโน้ม",  # Trend/Tendency
                    "การเคลื่อนไหว",  # Movement
                    "ราคา",  # Price
                ]
                
                found_chart_pattern = any(indicator in report_text for indicator in chart_pattern_indicators)
                assert found_chart_pattern, f"Report should contain chart pattern analysis. Report preview: {report_text[:500]}"
                
                return
            
            elif status == "failed":
                error_msg = status_data.get("error", "Unknown error")
                pytest.fail(f"Report generation failed: {error_msg}")
            
            time.sleep(5)
        
        pytest.fail(f"Report generation timed out after {max_wait} seconds")
