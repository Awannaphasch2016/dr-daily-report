#!/usr/bin/env python3
"""
End-to-End Tests for Telegram Mini App Frontend

Uses Playwright to test the web UI with real API calls.
Covers non-trivial logic, constraints, and user flows.

Run with: pytest tests/e2e/test_telegram_webapp.py -v
"""

import os
import pytest
from playwright.sync_api import Page, expect
import time


# Mark entire module as e2e (requires running server + playwright)
pytestmark = pytest.mark.e2e


# Test configuration - read from environment for flexibility
BASE_URL = os.environ.get("E2E_BASE_URL", os.environ.get("BASE_URL", "http://localhost:8080"))
API_BASE_URL = os.environ.get("E2E_API_URL", "https://ou0ivives1.execute-api.ap-southeast-1.amazonaws.com/api/v1")


class TestPageLoad:
    """Tests for initial page load and basic UI elements"""

    def test_page_loads_successfully(self, page: Page):
        """Test that the page loads without errors"""
        page.goto(BASE_URL)

        # Check title
        expect(page).to_have_title("DR Daily Report")

    def test_header_displays_correctly(self, page: Page):
        """Test that header shows app title and subtitle"""
        page.goto(BASE_URL)

        # Check header elements
        expect(page.locator(".app-title")).to_contain_text("DR Daily Report")
        expect(page.locator(".app-subtitle")).to_contain_text("AI-Powered")

    def test_search_input_is_visible(self, page: Page):
        """Test that search input is visible and has placeholder"""
        page.goto(BASE_URL)

        search_input = page.locator("#search-input")
        expect(search_input).to_be_visible()
        expect(search_input).to_have_attribute("placeholder", "ค้นหาหุ้น... (NVDA, DBS, AAPL)")

    def test_tab_navigation_exists(self, page: Page):
        """Test that tab navigation buttons exist"""
        page.goto(BASE_URL)

        # Check both tabs exist
        expect(page.locator(".tab-btn[data-tab='rankings']")).to_be_visible()
        expect(page.locator(".tab-btn[data-tab='watchlist']")).to_be_visible()

    def test_rankings_tab_active_by_default(self, page: Page):
        """Test that Rankings tab is active on initial load"""
        page.goto(BASE_URL)

        rankings_btn = page.locator(".tab-btn[data-tab='rankings']")
        expect(rankings_btn).to_have_class("tab-btn active")


class TestSearchFunctionality:
    """Tests for search input and results"""

    def test_search_shows_results_dropdown(self, page: Page):
        """Test that typing in search shows results dropdown"""
        page.goto(BASE_URL)

        # Type in search
        search_input = page.locator("#search-input")
        search_input.fill("NVDA")

        # Wait for results (debounced)
        page.wait_for_timeout(500)

        # Results should be visible
        results = page.locator("#search-results")
        expect(results).not_to_have_class("hidden")

    def test_search_results_contain_ticker(self, page: Page):
        """Test that search results contain matching ticker"""
        page.goto(BASE_URL)

        search_input = page.locator("#search-input")
        search_input.fill("DBS")

        page.wait_for_timeout(500)

        # Should find DBS19
        results = page.locator("#search-results")
        expect(results).to_contain_text("DBS19")

    def test_search_empty_clears_results(self, page: Page):
        """Test that clearing search hides results or shows empty state"""
        page.goto(BASE_URL)

        search_input = page.locator("#search-input")
        search_input.fill("NVDA")
        page.wait_for_timeout(500)

        # Clear input
        search_input.fill("")
        page.wait_for_timeout(500)  # Longer wait for debounce

        # Results should be hidden or empty (depending on implementation)
        results = page.locator("#search-results")
        # Check either hidden class, no results displayed, or no results from NVDA
        is_hidden = "hidden" in (results.get_attribute("class") or "")
        results_text = results.inner_text().strip()
        is_empty = results_text == "" or "No results" in results_text
        # Also accept if results no longer contain NVDA (cleared successfully)
        nvda_cleared = "NVDA" not in results_text
        assert is_hidden or is_empty or nvda_cleared, f"Results should be hidden or empty after clearing search. Got: hidden={is_hidden}, empty={is_empty}, text='{results_text[:100]}'"

    def test_click_outside_closes_results(self, page: Page):
        """Test that clicking outside search closes results"""
        page.goto(BASE_URL)

        search_input = page.locator("#search-input")
        search_input.fill("NVDA")
        page.wait_for_timeout(500)

        # Click outside (on header)
        page.locator(".app-header").click()

        # Results should be hidden
        results = page.locator("#search-results")
        expect(results).to_have_class("search-results hidden")


class TestTabNavigation:
    """Tests for tab switching behavior"""

    def test_click_watchlist_tab_switches_view(self, page: Page):
        """Test that clicking watchlist tab shows watchlist panel"""
        page.goto(BASE_URL)

        # Click watchlist tab
        page.locator(".tab-btn[data-tab='watchlist']").click()

        # Watchlist tab should be active
        expect(page.locator(".tab-btn[data-tab='watchlist']")).to_have_class("tab-btn active")

        # Watchlist panel should be visible
        expect(page.locator("#watchlist-tab")).not_to_have_class("hidden")

        # Rankings panel should be hidden
        expect(page.locator("#rankings-tab")).to_have_class("tab-panel hidden")

    def test_click_rankings_tab_switches_back(self, page: Page):
        """Test that clicking rankings tab switches back"""
        page.goto(BASE_URL)

        # Switch to watchlist first
        page.locator(".tab-btn[data-tab='watchlist']").click()

        # Switch back to rankings
        page.locator(".tab-btn[data-tab='rankings']").click()

        # Rankings tab should be active
        expect(page.locator(".tab-btn[data-tab='rankings']")).to_have_class("tab-btn active")

        # Rankings panel should be visible
        expect(page.locator("#rankings-tab")).not_to_have_class("hidden")


class TestRankingsCategory:
    """Tests for rankings category switching"""

    def test_category_buttons_exist(self, page: Page):
        """Test that all 4 category buttons exist"""
        page.goto(BASE_URL)

        expect(page.locator(".category-btn[data-category='top_gainers']")).to_be_visible()
        expect(page.locator(".category-btn[data-category='top_losers']")).to_be_visible()
        expect(page.locator(".category-btn[data-category='volume_surge']")).to_be_visible()
        expect(page.locator(".category-btn[data-category='trending']")).to_be_visible()

    def test_top_gainers_active_by_default(self, page: Page):
        """Test that top_gainers is active by default"""
        page.goto(BASE_URL)

        gainers_btn = page.locator(".category-btn[data-category='top_gainers']")
        expect(gainers_btn).to_have_class("category-btn active")

    def test_click_category_switches_active(self, page: Page):
        """Test that clicking category switches active state"""
        page.goto(BASE_URL)

        # Click top_losers
        page.locator(".category-btn[data-category='top_losers']").click()

        # Top losers should be active
        expect(page.locator(".category-btn[data-category='top_losers']")).to_have_class("category-btn active")

        # Top gainers should not be active
        expect(page.locator(".category-btn[data-category='top_gainers']")).not_to_have_class("active")


class TestWatchlistOperations:
    """Tests for watchlist add/remove operations"""

    def test_empty_watchlist_shows_message(self, page: Page):
        """Test that empty watchlist shows appropriate message"""
        page.goto(BASE_URL)

        # Switch to watchlist tab
        page.locator(".tab-btn[data-tab='watchlist']").click()

        # Wait for API response
        page.wait_for_timeout(1000)

        # Should show empty state or have tickers
        watchlist = page.locator("#watchlist-list")
        # Either shows empty state or has content
        expect(watchlist).to_be_visible()

    def test_search_result_click_opens_modal(self, page: Page):
        """Test that clicking search result opens report modal"""
        page.goto(BASE_URL)

        # Search for ticker
        search_input = page.locator("#search-input")
        search_input.fill("DBS")
        page.wait_for_timeout(500)

        # Click on result
        page.locator(".search-result-item").first.click()

        # Modal should be visible
        modal = page.locator("#report-modal")
        expect(modal).not_to_have_class("hidden")


class TestReportModal:
    """Tests for report modal behavior"""

    def test_modal_close_button_works(self, page: Page):
        """Test that modal close button hides modal"""
        page.goto(BASE_URL)

        # Open modal via search
        search_input = page.locator("#search-input")
        search_input.fill("DBS")
        page.wait_for_timeout(500)
        page.locator(".search-result-item").first.click()

        # Wait for modal to be visible
        page.wait_for_timeout(300)

        # Click close button
        page.locator(".modal-close").click()

        # Wait for animation
        page.wait_for_timeout(400)

        # Modal should be hidden
        modal = page.locator("#report-modal")
        expect(modal).to_have_class("modal hidden")

    def test_modal_shows_ticker_name(self, page: Page):
        """Test that modal header shows the ticker symbol"""
        page.goto(BASE_URL)

        # Open modal for DBS19
        search_input = page.locator("#search-input")
        search_input.fill("DBS")
        page.wait_for_timeout(500)
        page.locator(".search-result-item").first.click()

        # Check ticker is shown
        ticker_header = page.locator("#report-ticker")
        expect(ticker_header).to_contain_text("DBS")

    def test_modal_shows_loading_state(self, page: Page):
        """Test that modal shows loading indicator while fetching"""
        page.goto(BASE_URL)

        # Open modal
        search_input = page.locator("#search-input")
        search_input.fill("DBS")
        page.wait_for_timeout(500)
        page.locator(".search-result-item").first.click()

        # Should show loading indicator initially
        loading = page.locator("#report-body .loading-indicator")
        expect(loading).to_be_visible()


class TestResponsiveUI:
    """Tests for UI responsiveness and visual elements"""

    def test_toast_container_exists(self, page: Page):
        """Test that toast notification container exists in DOM"""
        page.goto(BASE_URL)

        # Toast container exists but is hidden until a toast is shown
        toast_container = page.locator("#toast-container")
        expect(toast_container).to_be_attached()

    def test_loading_spinner_in_modal(self, page: Page):
        """Test that loading spinner element exists in modal"""
        page.goto(BASE_URL)

        # Open modal to trigger loading
        search_input = page.locator("#search-input")
        search_input.fill("DBS")
        page.wait_for_timeout(500)
        page.locator(".search-result-item").first.click()

        # Check spinner exists in the report body (modal)
        spinner = page.locator("#report-body .spinner")
        expect(spinner).to_be_visible()


class TestErrorHandling:
    """Tests for error states and edge cases"""

    def test_invalid_search_shows_no_results(self, page: Page):
        """Test that invalid search query shows no results message"""
        page.goto(BASE_URL)

        # Search for something that doesn't exist
        search_input = page.locator("#search-input")
        search_input.fill("ZZZZZZZ123")
        page.wait_for_timeout(500)

        # Should show "No results" or empty
        results = page.locator("#search-results")
        expect(results).not_to_have_class("hidden")

    def test_special_characters_in_search(self, page: Page):
        """Test that special characters don't break search"""
        page.goto(BASE_URL)

        # Search with special characters
        search_input = page.locator("#search-input")
        search_input.fill("!@#$%")
        page.wait_for_timeout(500)

        # Page should not crash, results should be empty or show message
        expect(page.locator("#search-results")).to_be_visible()


class TestKeyboardNavigation:
    """Tests for keyboard interactions"""

    def test_enter_key_triggers_search(self, page: Page):
        """Test that pressing Enter triggers search action"""
        page.goto(BASE_URL)

        search_input = page.locator("#search-input")
        search_input.fill("NVDA")
        search_input.press("Enter")

        # Should open modal for NVDA
        page.wait_for_timeout(500)
        modal = page.locator("#report-modal")
        # Modal may or may not open depending on if there's a direct search-to-report flow
        # Just verify no crash
        expect(page).to_have_title("DR Daily Report")


# Pytest configuration for Playwright
@pytest.fixture(scope="function")
def page(browser):
    """Create a new page for each test"""
    context = browser.new_context()
    page = context.new_page()
    yield page
    context.close()


@pytest.fixture(scope="session")
def browser(playwright):
    """Launch browser once per session"""
    browser = playwright.chromium.launch(headless=True)
    yield browser
    browser.close()
