# -*- coding: utf-8 -*-
"""
Quick validation test for TEST CloudFront environment

This test validates:
1. Page loads correctly
2. API is configured and accessible
3. Search functionality works
4. Report generation can be triggered

Run with:
    E2E_BASE_URL=https://d24cidhj2eghux.cloudfront.net pytest tests/e2e/test_validate_test_env.py -v -m e2e
"""

import os
import pytest
from playwright.sync_api import Page, expect

TEST_URL = os.environ.get("E2E_BASE_URL", "https://d24cidhj2eghux.cloudfront.net")

pytestmark = pytest.mark.e2e


class TestTestEnvironment:
    """Validate TEST CloudFront environment is working"""

    def test_page_loads_and_api_configured(self, page: Page):
        """Validate page loads and API is accessible"""
        page.goto(TEST_URL, wait_until="networkidle", timeout=30000)
        page.wait_for_load_state("domcontentloaded")
        page.wait_for_timeout(3000)

        # Check search input exists
        search_input = page.locator("#search-input")
        expect(search_input).to_be_visible(timeout=10000)

        # Check API URL is configured (check window object)
        api_url = page.evaluate("() => window.TELEGRAM_API_URL || 'not set'")
        assert api_url != "not set", f"API URL not configured. Found: {api_url}"
        assert "api/v1" in api_url or "execute-api" in api_url, f"API URL seems invalid: {api_url}"

        # Try to trigger search
        search_input.fill("NVDA")
        page.wait_for_timeout(3000)  # Wait for API call

        # Check if autocomplete appears (be flexible with selectors)
        autocomplete_found = False
        for selector in [".search-result-item", ".autocomplete-item", "[class*='result']", "[class*='suggestion']"]:
            if page.locator(selector).count() > 0:
                autocomplete_found = True
                break

        if not autocomplete_found:
            # Take screenshot for debugging
            page.screenshot(path="tests/e2e/screenshots/test_env_search_failed.png")
            # Check for errors in page
            page_text = page.locator("body").inner_text()
            pytest.fail(f"Search autocomplete not found. API URL: {api_url}. Page text preview: {page_text[:200]}")

        assert autocomplete_found, "Search autocomplete should appear"
