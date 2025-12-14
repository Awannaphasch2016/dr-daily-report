# -*- coding: utf-8 -*-
"""
E2E Test: Validate Generation Data Display at TEST CloudFront

This test validates that all generation information (fundamental data,
chart patterns, MCP integration) is displayed correctly in the UI.

Run with:
    E2E_BASE_URL=https://d24cidhj2eghux.cloudfront.net pytest tests/e2e/test_validate_generation_data.py -v --headed
"""

import os
import pytest
from playwright.sync_api import Page, expect

# TEST CloudFront URL for dev environment
TEST_URL = os.environ.get("E2E_BASE_URL", "https://d24cidhj2eghux.cloudfront.net")

pytestmark = pytest.mark.e2e


class TestGenerationDataDisplay:
    """Validate that all generation information is displayed correctly"""

    @pytest.mark.slow
    def test_report_generation_displays_all_sections(self, page: Page):
        """Validate that generated report contains all expected sections"""
        page.goto(TEST_URL, wait_until="networkidle", timeout=30000)
        page.wait_for_load_state("domcontentloaded")
        page.wait_for_timeout(3000)  # Wait for React to render

        # Search for a ticker
        search_input = page.locator("#search-input")
        expect(search_input).to_be_visible(timeout=10000)
        search_input.fill("DBS19")
        
        # Wait longer for API call and autocomplete to appear
        page.wait_for_timeout(2000)  # Give API time to respond
        
        # Check if autocomplete appears (try multiple selectors)
        autocomplete_visible = False
        selectors = [".search-result-item", ".autocomplete-item", "[data-testid='search-result']"]
        for selector in selectors:
            if page.locator(selector).count() > 0:
                autocomplete_visible = True
                page.locator(selector).first.click()
                break
        
        if not autocomplete_visible:
            # Take screenshot for debugging
            page.screenshot(path="tests/e2e/screenshots/search_failed.png")
            # Check console for errors
            console_logs = []
            for log in page.evaluate("() => { return window.console.logs || []; }"):
                console_logs.append(log)
            pytest.fail(f"Autocomplete not found. Selectors tried: {selectors}. Console logs: {console_logs}")

        # Wait for modal to open
        expect(page.locator(".modal")).to_be_visible(timeout=3000)
        expect(page.locator("#report-body")).to_be_visible()

        # Wait for report to complete (up to 120 seconds)
        # The report-stance class appears when report is rendered
        expect(page.locator(".report-stance")).to_be_visible(timeout=120000)

        # Validate report body contains content
        report_body = page.locator("#report-body")
        expect(report_body).to_be_visible()
        
        # Get full report text for validation
        report_text = report_body.inner_text()
        
        # Validate key sections are present
        # These sections should be present based on the enhanced prompt
        assert len(report_text) > 100, "Report should have substantial content"
        
        # Check for fundamental data indicators (Thai text patterns)
        fundamental_indicators = [
            "มูลค่าตลาด",  # Market cap
            "P/E",  # Price-to-earnings
            "ROE",  # Return on equity
            "กำไร",  # Profit
            "รายได้",  # Revenue
        ]
        
        found_fundamental = any(indicator in report_text for indicator in fundamental_indicators)
        assert found_fundamental, f"Report should contain fundamental data indicators. Found text: {report_text[:500]}"

    @pytest.mark.slow
    def test_report_contains_chart_pattern_analysis(self, page: Page):
        """Validate that chart pattern analysis is included"""
        page.goto(TEST_URL)

        # Search and generate report
        page.locator("#search-input").fill("NVDA19")
        expect(page.locator(".search-result-item")).to_be_visible(timeout=5000)
        page.locator(".search-result-item").first.click()

        # Wait for report completion
        expect(page.locator(".report-stance")).to_be_visible(timeout=120000)

        report_body = page.locator("#report-body")
        report_text = report_body.inner_text()

        # Check for chart pattern indicators (Thai text patterns)
        chart_pattern_indicators = [
            "รูปแบบ",  # Pattern
            "กราฟ",  # Chart
            "เทรนด์",  # Trend
            "แนวโน้ม",  # Trend/Tendency
            "การเคลื่อนไหว",  # Movement
            "ราคา",  # Price
        ]
        
        found_chart_pattern = any(indicator in report_text for indicator in chart_pattern_indicators)
        assert found_chart_pattern, f"Report should contain chart pattern analysis. Found text: {report_text[:500]}"

    @pytest.mark.slow
    def test_report_has_stance_indicator(self, page: Page):
        """Validate that report stance (bullish/bearish/neutral) is displayed"""
        page.goto(TEST_URL)

        # Generate report
        page.locator("#search-input").fill("DBS19")
        expect(page.locator(".search-result-item")).to_be_visible(timeout=5000)
        page.locator(".search-result-item").first.click()

        # Wait for report completion
        expect(page.locator(".report-stance")).to_be_visible(timeout=120000)

        # Check stance indicator is visible and has content
        stance_element = page.locator(".report-stance")
        expect(stance_element).to_be_visible()
        
        stance_text = stance_element.inner_text()
        assert len(stance_text) > 0, "Stance indicator should have text"
        
        # Stance should be one of: bullish, bearish, neutral (in Thai or English)
        stance_keywords = ["Bullish", "Bearish", "Neutral", "บวก", "ลบ", "กลาง"]
        found_stance = any(keyword.lower() in stance_text.lower() for keyword in stance_keywords)
        assert found_stance, f"Report should have stance indicator. Found: {stance_text}"

    @pytest.mark.slow
    def test_report_has_key_takeaways(self, page: Page):
        """Validate that Key Takeaways section is present"""
        page.goto(TEST_URL)

        # Generate report
        page.locator("#search-input").fill("NVDA19")
        expect(page.locator(".search-result-item")).to_be_visible(timeout=5000)
        page.locator(".search-result-item").first.click()

        # Wait for report completion
        expect(page.locator(".report-stance")).to_be_visible(timeout=120000)

        report_body = page.locator("#report-body")
        report_text = report_body.inner_text()

        # Check for Key Takeaways section
        takeaways_indicators = [
            "Key Takeaways",
            "ประเด็นสำคัญ",
            "สรุป",
            "สรุปผล",
        ]
        
        found_takeaways = any(indicator in report_text for indicator in takeaways_indicators)
        assert found_takeaways, f"Report should contain Key Takeaways section. Found text: {report_text[:500]}"

    @pytest.mark.slow
    def test_report_has_technical_analysis(self, page: Page):
        """Validate that technical analysis section is present"""
        page.goto(TEST_URL)

        # Generate report
        page.locator("#search-input").fill("DBS19")
        expect(page.locator(".search-result-item")).to_be_visible(timeout=5000)
        page.locator(".search-result-item").first.click()

        # Wait for report completion
        expect(page.locator(".report-stance")).to_be_visible(timeout=120000)

        report_body = page.locator("#report-body")
        report_text = report_body.inner_text()

        # Check for technical analysis indicators
        technical_indicators = [
            "RSI",
            "MACD",
            "Moving Average",
            "MA",
            "เทคนิค",
            "ตัวชี้วัด",
            "RSI",
            "MACD",
        ]
        
        found_technical = any(indicator in report_text for indicator in technical_indicators)
        assert found_technical, f"Report should contain technical analysis. Found text: {report_text[:500]}"

    def test_page_loads_correctly(self, page: Page):
        """Validate that the page loads without errors"""
        page.goto(TEST_URL, wait_until="networkidle", timeout=30000)

        # Wait for page to load
        page.wait_for_load_state("domcontentloaded")
        page.wait_for_timeout(3000)  # Wait for React to render

        # Take screenshot for debugging
        page.screenshot(path="tests/e2e/screenshots/test_page_load.png")

        # Check that page has content (more flexible check)
        page_title = page.title()
        page_body = page.locator("body")
        expect(page_body).to_be_visible(timeout=10000)
        
        # Check for search input (key element)
        search_input = page.locator("#search-input")
        if search_input.count() == 0:
            # Try alternative selectors
            search_input = page.locator("input[type='text']")
            if search_input.count() == 0:
                search_input = page.locator("input[placeholder*='search' i]")
        
        assert search_input.count() > 0, f"Search input not found. Page title: {page_title}, URL: {page.url}"
        expect(search_input.first).to_be_visible(timeout=5000)
        
        # Check that API is configured (should not show errors)
        page.wait_for_timeout(2000)
        
        # Check for common error indicators
        error_indicators = page.locator("text=/error|Error|ERROR/")
        error_count = error_indicators.count()
        assert error_count == 0, f"Page should not show errors. Found {error_count} error indicators. Page title: {page_title}"
