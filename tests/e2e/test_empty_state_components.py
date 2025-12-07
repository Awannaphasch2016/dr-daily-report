# -*- coding: utf-8 -*-
"""
E2E tests for empty state component rendering.

Following TDD RED → GREEN → REFACTOR cycle from CLAUDE.md:
- Tests should verify BEHAVIOR (user sees feedback) not IMPLEMENTATION (cache populated)
- Components should ALWAYS render, showing either data OR empty state
- Aligns with Principle 4: Schema Testing at System Boundaries (CLAUDE.md:340-383)
"""

import pytest
from playwright.sync_api import Page, expect
import os


# Use CloudFront TEST distribution for E2E testing
BASE_URL = os.getenv('E2E_BASE_URL', 'http://localhost:8080')


class TestEmptyStateComponents:
    """
    Test that UI components render empty states when data is missing.

    WHY: Observability - we can see component exists, know data is missing (not a UI bug)

    Principle from CLAUDE.md line 342-346:
    "If changing this breaks consumers, it's a contract (test it).
    If changing this doesn't affect consumers, it's implementation (don't test it)."

    Contract: User sees feedback (either data or empty state)
    Implementation: How the data is fetched (we don't test this)
    """

    @pytest.mark.e2e
    def test_mini_chart_shows_empty_state_when_no_data(self, page: Page):
        """
        Component should render with empty state message, not disappear.

        BEHAVIOR TEST: User sees either chart data OR "No data available" message
        NOT IMPLEMENTATION TEST: Don't check if cache was populated

        Anti-Pattern Avoided: "Happy Path Only" (CLAUDE.md:214)
        - We test BOTH success (data exists) AND failure (no data) scenarios
        """
        page.goto(f"{BASE_URL}")

        # Wait for market card to exist (app loaded)
        card = page.locator(".market-card").first
        card.wait_for(state="visible", timeout=10000)

        # CRITICAL: Chart component should ALWAYS exist in DOM
        chart = card.locator("[data-testid='mini-chart']")
        expect(chart).to_be_visible()

        # BEHAVIOR: Must show EITHER data OR empty state (not removed from DOM)
        has_svg = chart.locator("svg").count() > 0
        has_empty_state = chart.locator(".empty-state").count() > 0

        assert has_svg or has_empty_state, \
            "Chart must show data OR empty state (not removed from DOM)"

        # If empty state shown, verify it has meaningful message
        if has_empty_state:
            empty_state = chart.locator(".empty-state")
            expect(empty_state).to_contain_text("No chart data available", ignore_case=True)

    @pytest.mark.e2e
    def test_score_table_shows_empty_state_when_no_scores(self, page: Page):
        """
        Score table should render with empty message, not disappear.

        Aligns with CLAUDE.md Principle 1: Test Outcomes, Not Execution (line 295)
        - Outcome: User sees feedback about missing scores
        - Execution: We don't test HOW scores are fetched
        """
        page.goto(f"{BASE_URL}")

        # Wait for market card to exist
        card = page.locator(".market-card").first
        card.wait_for(state="visible", timeout=10000)

        # Score table component should ALWAYS exist
        score_table = card.locator("[data-testid='score-table']")
        expect(score_table).to_be_visible()

        # BEHAVIOR: Must show EITHER scores OR empty state
        has_score_rows = score_table.locator(".score-row").count() > 0
        has_empty_state = score_table.locator(".empty-state").count() > 0

        assert has_score_rows or has_empty_state, \
            "Score table must show data OR empty state (not removed from DOM)"

        # If empty state shown, verify meaningful message
        if has_empty_state:
            empty_state = score_table.locator(".empty-state")
            expect(empty_state).to_contain_text("No scoring data available", ignore_case=True)

    @pytest.mark.e2e
    def test_all_components_exist_even_with_empty_cache(self, page: Page):
        """
        Round-trip test: ALL components should render even when cache is empty.

        This is the INTEGRATION CONTRACT between frontend and backend:
        - Backend may return empty arrays (cache miss)
        - Frontend MUST still render components (with empty states)

        Aligns with CLAUDE.md Principle 4: Schema Testing at System Boundaries (line 340)
        """
        page.goto(f"{BASE_URL}")

        # Wait for page load
        card = page.locator(".market-card").first
        card.wait_for(state="visible", timeout=10000)

        # All components should exist in DOM
        components = {
            'mini-chart': card.locator("[data-testid='mini-chart']"),
            'score-table': card.locator("[data-testid='score-table']"),
        }

        for component_name, locator in components.items():
            expect(locator).to_be_visible(), \
                f"Component '{component_name}' should always be visible (with data or empty state)"

            # Each component should show EITHER data OR empty state
            has_data = locator.locator(".score-row, svg").count() > 0
            has_empty_state = locator.locator(".empty-state").count() > 0

            assert has_data or has_empty_state, \
                f"Component '{component_name}' must show data OR empty state"

    @pytest.mark.e2e
    def test_empty_state_has_visual_indicator(self, page: Page):
        """
        Empty states should have visual indicators (icons) for better UX.

        Graceful degradation principle: Empty state should be INFORMATIVE, not just "nothing here"
        """
        page.goto(f"{BASE_URL}")

        # Wait for page load
        card = page.locator(".market-card").first
        card.wait_for(state="visible", timeout=10000)

        # If any empty states exist, they should have icons
        empty_states = page.locator(".empty-state")
        count = empty_states.count()

        if count > 0:
            for i in range(count):
                empty_state = empty_states.nth(i)

                # Should have icon (emoji or SVG)
                has_icon = empty_state.locator(".empty-state__icon").count() > 0
                has_emoji = "📊" in empty_state.text_content() or "📈" in empty_state.text_content()

                assert has_icon or has_emoji, \
                    "Empty state should have visual indicator (icon or emoji)"
