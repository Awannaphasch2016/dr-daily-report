# -*- coding: utf-8 -*-
"""
End-to-End Frontend Tests using Playwright

Tests the full user journey through the Telegram Mini App frontend.
Requires: pytest-playwright

Run with:
    pytest tests/test_e2e_frontend.py -v --headed    # Watch browser
    pytest tests/test_e2e_frontend.py -v             # Headless (CI)
    pytest tests/test_e2e_frontend.py -v -k "search" # Specific test

Environment variables:
    FRONTEND_URL: Override default CloudFront URL (for local testing)
"""

import os
import re
import pytest
from playwright.sync_api import Page, expect

# Default to dev CloudFront URL, can override for local testing
FRONTEND_URL = os.environ.get(
    "FRONTEND_URL",
    "https://demjoigiw6myp.cloudfront.net"
)


@pytest.fixture(scope="module")
def browser_context_args(browser_context_args):
    """Configure browser context for all tests"""
    return {
        **browser_context_args,
        "viewport": {"width": 1280, "height": 900},
        "ignore_https_errors": True,
    }


class TestHomePage:
    """Tests for the homepage loading and basic elements"""

    @pytest.mark.e2e
    def test_homepage_loads(self, page: Page):
        """Homepage loads without errors"""
        page.goto(FRONTEND_URL)

        # Verify key elements are present
        expect(page.locator("h1")).to_contain_text("DR Daily Report")
        expect(page.locator("#search-input")).to_be_visible()

    @pytest.mark.e2e
    def test_tabs_visible(self, page: Page):
        """Rankings and Watchlist tabs are visible"""
        page.goto(FRONTEND_URL)

        # Use specific tab button selectors to avoid matching loading text
        expect(page.locator('.tab-btn[data-tab="rankings"]')).to_be_visible()
        expect(page.locator('.tab-btn[data-tab="watchlist"]')).to_be_visible()

    @pytest.mark.e2e
    def test_ranking_categories_visible(self, page: Page):
        """Ranking category buttons are visible"""
        page.goto(FRONTEND_URL)

        # Check ranking category buttons exist
        expect(page.get_by_text("Top Gainers")).to_be_visible()
        expect(page.get_by_text("Top Losers")).to_be_visible()
        expect(page.get_by_text("Volume Surge")).to_be_visible()
        expect(page.get_by_text("Trending")).to_be_visible()


class TestSearchFlow:
    """Tests for the search and autocomplete functionality"""

    @pytest.mark.e2e
    def test_search_input_accepts_text(self, page: Page):
        """User can type in search box"""
        page.goto(FRONTEND_URL)

        search = page.locator("#search-input")
        search.fill("NVDA")

        expect(search).to_have_value("NVDA")

    @pytest.mark.e2e
    def test_search_shows_autocomplete(self, page: Page):
        """Typing in search shows autocomplete results"""
        page.goto(FRONTEND_URL)

        search = page.locator("#search-input")
        search.fill("NVDA")

        # Wait for autocomplete dropdown
        expect(page.locator(".search-result-item")).to_be_visible(timeout=5000)

    @pytest.mark.e2e
    def test_autocomplete_shows_ticker_info(self, page: Page):
        """Autocomplete shows ticker symbol and company name"""
        page.goto(FRONTEND_URL)

        search = page.locator("#search-input")
        search.fill("NVDA")

        # Wait for results and check content
        result = page.locator(".search-result-item").first
        expect(result).to_be_visible(timeout=5000)

        # Should show NVDA19 (DR ticker format)
        expect(result).to_contain_text("NVDA")


class TestReportGeneration:
    """Tests for the report generation flow"""

    @pytest.mark.e2e
    @pytest.mark.slow
    def test_clicking_result_opens_modal(self, page: Page):
        """Clicking autocomplete result opens report modal"""
        page.goto(FRONTEND_URL)

        # Search and click result
        page.locator("#search-input").fill("NVDA")
        page.locator(".search-result-item").first.click()

        # Modal should open
        expect(page.locator(".modal")).to_be_visible(timeout=3000)
        expect(page.locator("#report-body")).to_be_visible()

    @pytest.mark.e2e
    @pytest.mark.slow
    def test_modal_shows_loading_state(self, page: Page):
        """Modal shows loading indicator after clicking ticker"""
        page.goto(FRONTEND_URL)

        # Search and click result
        page.locator("#search-input").fill("NVDA")
        page.locator(".search-result-item").first.click()

        # Should show loading message (async pattern)
        expect(page.locator("#report-body")).to_contain_text(
            "Report job submitted",
            timeout=5000
        )

    @pytest.mark.e2e
    @pytest.mark.slow
    def test_report_generation_completes(self, page: Page):
        """Full report generation completes successfully

        Note: This test takes 30-90 seconds due to LLM generation time.
        """
        page.goto(FRONTEND_URL)

        # Search and click result
        page.locator("#search-input").fill("NVDA")
        page.locator(".search-result-item").first.click()

        # Wait for report content (up to 120 seconds)
        # The report-stance class appears when report is rendered
        expect(page.locator(".report-stance")).to_be_visible(timeout=120000)

        # Verify report has key sections
        report_body = page.locator("#report-body")
        expect(report_body).to_contain_text("Key Takeaways")

    @pytest.mark.e2e
    def test_modal_can_be_closed(self, page: Page):
        """Modal close button works"""
        page.goto(FRONTEND_URL)

        # Open modal
        page.locator("#search-input").fill("NVDA")
        page.locator(".search-result-item").first.click()
        expect(page.locator(".modal")).to_be_visible(timeout=3000)

        # Close modal
        page.locator(".modal-close").click()

        # Modal should be hidden
        expect(page.locator(".modal")).to_be_hidden(timeout=2000)


class TestRankingsTab:
    """Tests for the rankings functionality"""

    @pytest.mark.e2e
    def test_switching_ranking_categories(self, page: Page):
        """User can switch between ranking categories"""
        page.goto(FRONTEND_URL)

        # Click through each category using specific button selectors
        categories = [".category-btn:has-text('Top Gainers')",
                      ".category-btn:has-text('Top Losers')",
                      ".category-btn:has-text('Volume Surge')",
                      ".category-btn:has-text('Trending')"]
        for selector in categories:
            page.locator(selector).click()
            # Small delay to allow UI update
            page.wait_for_timeout(500)

    @pytest.mark.e2e
    def test_rankings_show_data_or_empty_state(self, page: Page):
        """Rankings show either data or appropriate empty state"""
        page.goto(FRONTEND_URL)

        # Wait for rankings to load
        page.wait_for_timeout(3000)

        # rankings-list is an ID, not a class
        rankings_container = page.locator("#rankings-list")
        expect(rankings_container).to_be_visible(timeout=5000)


class TestWatchlistTab:
    """Tests for the watchlist functionality"""

    @pytest.mark.e2e
    def test_watchlist_tab_accessible(self, page: Page):
        """User can switch to watchlist tab"""
        page.goto(FRONTEND_URL)

        # Click watchlist tab using specific selector
        watchlist_tab = page.locator('.tab-btn[data-tab="watchlist"]')
        watchlist_tab.click()

        # Verify tab becomes active (class contains "active")
        expect(watchlist_tab).to_have_class(re.compile("active"))

        # Wait for content change (either watchlist items or empty state)
        page.wait_for_timeout(1000)


class TestResponsiveness:
    """Tests for mobile responsiveness"""

    @pytest.mark.e2e
    def test_mobile_viewport(self, page: Page):
        """App works on mobile viewport"""
        page.set_viewport_size({"width": 375, "height": 667})  # iPhone SE
        page.goto(FRONTEND_URL)

        # Key elements should still be visible (use specific selectors)
        expect(page.locator("#search-input")).to_be_visible()
        expect(page.locator('.tab-btn[data-tab="rankings"]')).to_be_visible()

    @pytest.mark.e2e
    def test_tablet_viewport(self, page: Page):
        """App works on tablet viewport"""
        page.set_viewport_size({"width": 768, "height": 1024})  # iPad
        page.goto(FRONTEND_URL)

        expect(page.locator("#search-input")).to_be_visible()
        expect(page.locator('.tab-btn[data-tab="rankings"]')).to_be_visible()
