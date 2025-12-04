"""
E2E Tests for Twinbar Prediction Market WebApp

TDD: Write tests first, then implement UI to pass them.
"""
import os
import re
import pytest
from playwright.sync_api import Page, expect

# Get base URL from environment or use default
BASE_URL = os.environ.get("E2E_BASE_URL", "http://localhost:8000")

pytestmark = pytest.mark.e2e


class TestTwinbarBranding:
    """Verify Twinbar branding elements are present."""

    def test_page_title_is_twinbar(self, page: Page):
        """Page title should be 'Twinbar'."""
        page.goto(BASE_URL)
        expect(page).to_have_title("Twinbar")

    def test_logo_mark_displays_twin_bars(self, page: Page):
        """Logo should show '||' twin bars mark."""
        page.goto(BASE_URL)
        logo_mark = page.locator(".logo-mark")
        expect(logo_mark).to_be_visible()
        expect(logo_mark).to_have_text("||")

    def test_logo_text_displays_twinbar(self, page: Page):
        """Logo text should say 'Twinbar'."""
        page.goto(BASE_URL)
        logo_text = page.locator(".logo-text")
        expect(logo_text).to_be_visible()
        expect(logo_text).to_have_text("Twinbar")

    def test_subtitle_displays_tagline(self, page: Page):
        """Subtitle should show the value proposition."""
        page.goto(BASE_URL)
        subtitle = page.locator(".app-subtitle")
        expect(subtitle).to_be_visible()
        expect(subtitle).to_contain_text("Predictive Markets")


class TestCategoryNavigation:
    """Verify category filter chips work correctly."""

    def test_category_chips_exist(self, page: Page):
        """Should have category filter chips."""
        page.goto(BASE_URL)
        category_nav = page.locator(".category-nav")
        expect(category_nav).to_be_visible()

        # Check for key categories
        expect(page.locator("[data-category='all']")).to_be_visible()
        expect(page.locator("[data-category='trending']")).to_be_visible()
        expect(page.locator("[data-category='finance']")).to_be_visible()

    def test_all_category_active_by_default(self, page: Page):
        """'All' category should be active by default."""
        page.goto(BASE_URL)
        all_chip = page.locator("[data-category='all']")
        expect(all_chip).to_have_class(re.compile(r"active"))

    def test_clicking_category_switches_active(self, page: Page):
        """Clicking a category chip should make it active."""
        page.goto(BASE_URL)

        finance_chip = page.locator("[data-category='finance']")
        finance_chip.click()

        expect(finance_chip).to_have_class(re.compile(r"active"))
        expect(page.locator("[data-category='all']")).not_to_have_class(re.compile(r"active"))


class TestSortOptions:
    """Verify sort functionality."""

    def test_sort_bar_exists(self, page: Page):
        """Sort bar with options should exist."""
        page.goto(BASE_URL)
        sort_bar = page.locator(".sort-bar")
        expect(sort_bar).to_be_visible()

    def test_sort_options_available(self, page: Page):
        """Should have Newest, Volume, Ending Soon sort options."""
        page.goto(BASE_URL)

        expect(page.locator("[data-sort='newest']")).to_be_visible()
        expect(page.locator("[data-sort='volume']")).to_be_visible()
        expect(page.locator("[data-sort='ending']")).to_be_visible()

    def test_newest_sort_active_by_default(self, page: Page):
        """'Newest' sort should be active by default."""
        page.goto(BASE_URL)
        newest_btn = page.locator("[data-sort='newest']")
        expect(newest_btn).to_have_class(re.compile(r"active"))


class TestMarketsGrid:
    """Verify markets grid displays correctly."""

    def test_markets_grid_exists(self, page: Page):
        """Markets grid container should exist."""
        page.goto(BASE_URL)
        grid = page.locator("#markets-grid")
        expect(grid).to_be_visible()

    def test_market_cards_display(self, page: Page):
        """Should display market cards (or loading state)."""
        page.goto(BASE_URL)

        # Wait for either cards or loading indicator
        page.wait_for_selector(".market-card, .loading-indicator", timeout=5000)

        # Check that grid has content
        grid = page.locator("#markets-grid")
        expect(grid).not_to_be_empty()


class TestMarketCard:
    """Verify individual market card structure."""

    def _wait_for_cards(self, page: Page):
        """Helper to wait for market cards to load."""
        page.goto(BASE_URL)
        page.wait_for_selector(".market-card", timeout=10000)

    def test_market_card_has_title(self, page: Page):
        """Each market card should have a title/question."""
        self._wait_for_cards(page)
        first_card = page.locator(".market-card").first
        title = first_card.locator(".market-title")
        expect(title).to_be_visible()

    def test_market_card_has_outcome_buttons(self, page: Page):
        """Each market card should have Yes/No outcome buttons."""
        self._wait_for_cards(page)
        first_card = page.locator(".market-card").first

        # Should have buy buttons for outcomes
        yes_btn = first_card.locator(".outcome-btn.yes, [data-outcome='yes']")
        no_btn = first_card.locator(".outcome-btn.no, [data-outcome='no']")

        expect(yes_btn).to_be_visible()
        expect(no_btn).to_be_visible()

    def test_market_card_shows_odds(self, page: Page):
        """Market card should display current odds/probability."""
        self._wait_for_cards(page)
        first_card = page.locator(".market-card").first

        # Should show percentage odds
        odds = first_card.locator(".market-odds, .outcome-odds")
        expect(odds.first).to_be_visible()

    def test_market_card_shows_volume(self, page: Page):
        """Market card should display trading volume."""
        self._wait_for_cards(page)
        first_card = page.locator(".market-card").first

        volume = first_card.locator(".market-volume")
        expect(volume).to_be_visible()

    def test_clicking_card_opens_detail_modal(self, page: Page):
        """Clicking a market card should open detail modal."""
        self._wait_for_cards(page)

        # Click on card (not on a button)
        first_card = page.locator(".market-card").first
        first_card.locator(".market-title").click()

        # Modal should appear (Headless UI renders it when open)
        modal = page.locator("#market-modal")
        expect(modal).to_be_visible()


class TestBuyInterface:
    """Verify buy/trade interface works."""

    def _wait_for_cards(self, page: Page):
        """Helper to wait for market cards to load."""
        page.goto(BASE_URL)
        page.wait_for_selector(".market-card", timeout=10000)

    def test_yes_button_has_buy_action(self, page: Page):
        """Yes button should trigger buy action."""
        self._wait_for_cards(page)
        first_card = page.locator(".market-card").first

        yes_btn = first_card.locator(".outcome-btn.yes, [data-outcome='yes']")
        expect(yes_btn).to_contain_text(re.compile(r"Yes|Buy"))

    def test_no_button_has_buy_action(self, page: Page):
        """No button should trigger buy action."""
        self._wait_for_cards(page)
        first_card = page.locator(".market-card").first

        no_btn = first_card.locator(".outcome-btn.no, [data-outcome='no']")
        expect(no_btn).to_contain_text(re.compile(r"No|Buy"))


class TestMarketModal:
    """Verify market detail modal functionality."""

    def test_modal_hidden_initially(self, page: Page):
        """Modal should not be visible initially."""
        page.goto(BASE_URL)
        page.wait_for_selector(".market-card", timeout=10000)
        # Headless UI Dialog conditionally renders, so modal won't exist initially
        modal = page.locator("#market-modal")
        expect(modal).to_have_count(0)

    def test_modal_opens_on_card_click(self, page: Page):
        """Clicking a card should open the modal."""
        page.goto(BASE_URL)
        page.wait_for_selector(".market-card", timeout=10000)

        # Click on card title to open modal
        page.locator(".market-card").first.locator(".market-title").click()
        page.wait_for_timeout(300)

        # Modal should now be visible
        modal = page.locator("#market-modal")
        expect(modal).to_be_visible()

    def test_modal_close_button_works(self, page: Page):
        """Modal close button should hide the modal."""
        page.goto(BASE_URL)
        page.wait_for_selector(".market-card", timeout=10000)

        # Open modal
        page.locator(".market-card").first.locator(".market-title").click()
        page.wait_for_timeout(300)

        # Close modal
        page.locator(".modal-close").click()
        page.wait_for_timeout(300)

        # Modal should be gone (Headless UI unmounts it)
        modal = page.locator("#market-modal")
        expect(modal).to_have_count(0)


class TestSearchFunctionality:
    """Verify search works for finding markets."""

    def test_search_input_exists(self, page: Page):
        """Search input should be visible."""
        page.goto(BASE_URL)
        search_input = page.locator("#search-input")
        expect(search_input).to_be_visible()

    def test_search_placeholder_text(self, page: Page):
        """Search should have appropriate placeholder."""
        page.goto(BASE_URL)
        search_input = page.locator("#search-input")
        expect(search_input).to_have_attribute("placeholder", re.compile(r"[Ss]earch.*market"))


class TestResponsiveDesign:
    """Verify UI is responsive for mobile (Telegram WebApp)."""

    def test_app_container_full_height(self, page: Page):
        """App should fill viewport height."""
        page.goto(BASE_URL)
        app = page.locator("#app")
        expect(app).to_be_visible()

    def test_markets_grid_responsive(self, page: Page):
        """Markets grid should adapt to screen width."""
        page.goto(BASE_URL)
        grid = page.locator(".markets-grid")
        expect(grid).to_be_visible()
        # Grid should have CSS grid or flexbox for responsive layout
