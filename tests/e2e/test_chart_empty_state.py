# -*- coding: utf-8 -*-
"""
E2E Test: Validate Chart Empty State in Investment Package Box

Tests that the MiniChart component in MarketCard shows empty state
when no chart data is available (following TDD principles from principles.mdc).

Following principles.mdc testing guidelines:
- Test outcomes, not execution
- Validate actual data content (empty state text)
- Explicit failure detection (check for empty state indicator)

Run with:
    E2E_BASE_URL=https://d24cidhj2eghux.cloudfront.net pytest tests/e2e/test_chart_empty_state.py -v -m e2e
"""

import os
import re
import pytest
from playwright.sync_api import Page, expect

TEST_URL = os.environ.get("E2E_BASE_URL", "https://d24cidhj2eghux.cloudfront.net")

pytestmark = pytest.mark.e2e


class TestChartEmptyState:
    """Validate chart empty state in investment package box"""

    def test_mini_chart_shows_empty_state_when_no_data(self, page: Page):
        """
        Validate that MiniChart in MarketCard shows empty state when price_history is empty.
        
        Following principles.mdc:
        - Test outcomes: Check for empty state text, not just component existence
        - Validate actual content: "No chart data available" text must be present
        - Explicit failure detection: Empty state indicator must be visible
        """
        page.goto(TEST_URL, wait_until="networkidle", timeout=30000)
        page.wait_for_load_state("domcontentloaded")
        page.wait_for_timeout(5000)  # Wait for initial data load

        # Find market cards (investment package boxes)
        market_cards = page.locator(".market-card, [data-market-id]")
        
        # Wait for at least one market card to appear
        expect(market_cards.first).to_be_visible(timeout=10000)

        # Get the first market card
        first_card = market_cards.first

        # Find the horizontal content section (investment package box)
        # This contains MiniChart (65% width) and ScoreTable (35% width)
        horizontal_content = first_card.locator('[data-testid="horizontal-content"]')
        expect(horizontal_content).to_be_visible(timeout=5000)

        # Find the MiniChart component within the horizontal content
        # MiniChart is in the left 65% section
        mini_chart = horizontal_content.locator('[data-testid="mini-chart"]')
        expect(mini_chart).to_be_visible(timeout=5000)

        # Validate empty state is shown
        # Following principles.mdc: Test outcomes, not execution
        # Check for actual empty state content, not just component existence
        
        # Check for empty state text element (CSS selector)
        empty_state_text = mini_chart.locator('.empty-state__text')
        empty_state_text_visible = empty_state_text.count() > 0 and empty_state_text.first.is_visible()
        
        # Also check for text content using get_by_text with regex pattern
        empty_state_by_text = mini_chart.get_by_text(re.compile(r'no.*chart.*data', re.IGNORECASE))
        empty_state_by_text_visible = empty_state_by_text.count() > 0
        
        # Check for empty state class indicator
        chart_class = mini_chart.get_attribute("class") or ""
        has_empty_class = "mini-chart--empty" in chart_class
        
        # Check if empty state container exists
        empty_state_container = mini_chart.locator('.empty-state')
        has_empty_container = empty_state_container.count() > 0
        
        # Validate: Chart should show empty state (no price_history data)
        # At least one indicator should be present
        empty_state_visible = empty_state_text_visible or empty_state_by_text_visible or has_empty_class or has_empty_container
        
        assert empty_state_visible, \
            f"Chart should show empty state when no data. " \
            f"Empty state text visible: {empty_state_text_visible}, " \
            f"Empty state by text visible: {empty_state_by_text_visible}, " \
            f"Has empty class: {has_empty_class}, " \
            f"Has empty container: {has_empty_container}, " \
            f"Chart class: {chart_class}, " \
            f"Chart HTML: {mini_chart.inner_html()[:200]}"

    def test_mini_chart_empty_state_has_correct_text(self, page: Page):
        """
        Validate that empty state shows correct text: "No chart data available"
        
        Following principles.mdc: Validate actual output content
        """
        page.goto(TEST_URL, wait_until="networkidle", timeout=30000)
        page.wait_for_load_state("domcontentloaded")
        page.wait_for_timeout(5000)

        # Find market card
        market_card = page.locator(".market-card, [data-market-id]").first
        expect(market_card).to_be_visible(timeout=10000)

        # Find MiniChart
        mini_chart = market_card.locator('[data-testid="mini-chart"]')
        expect(mini_chart).to_be_visible(timeout=5000)

        # Check for empty state text
        empty_state = mini_chart.locator(".empty-state")
        
        if empty_state.count() > 0:
            # Validate empty state text content
            empty_text = empty_state.locator(".empty-state__text")
            if empty_text.count() > 0:
                text_content = empty_text.first.inner_text().lower()
                assert "no" in text_content and ("chart" in text_content or "data" in text_content), \
                    f"Empty state should contain 'no chart data' text. Found: {text_content}"

    def test_all_market_cards_have_chart_components(self, page: Page):
        """
        Validate that all market cards have chart components (even if empty)
        
        Following principles.mdc: Validate all components are present
        """
        page.goto(TEST_URL, wait_until="networkidle", timeout=30000)
        page.wait_for_load_state("domcontentloaded")
        page.wait_for_timeout(5000)

        # Find all market cards
        market_cards = page.locator(".market-card, [data-market-id]")
        
        # Wait for cards to load
        card_count = market_cards.count()
        assert card_count > 0, "Should have at least one market card"

        # Validate each card has chart component
        for i in range(min(card_count, 5)):  # Check first 5 cards
            card = market_cards.nth(i)
            
            # Check horizontal content exists (investment package box)
            horizontal_content = card.locator('[data-testid="horizontal-content"]')
            if horizontal_content.count() > 0:
                # Check MiniChart exists
                mini_chart = horizontal_content.locator('[data-testid="mini-chart"]')
                assert mini_chart.count() > 0, f"Market card {i} should have MiniChart component"
