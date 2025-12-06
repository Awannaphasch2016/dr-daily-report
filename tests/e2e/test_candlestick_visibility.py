"""
Check if candlesticks are VISIBLE or hidden by CSS.
"""
import pytest
from playwright.sync_api import Page

BASE_URL = "https://d24cidhj2eghux.cloudfront.net"

pytestmark = pytest.mark.e2e


class TestCandlestickVisibility:
    """Check if candlesticks have visibility/opacity issues."""

    def test_candlesticks_are_actually_visible(self, page: Page):
        """Check computed styles of candlesticks."""
        page.goto(BASE_URL)
        page.wait_for_selector(".market-card", state="visible", timeout=10000)

        # Find Apple Vision Pro card
        cards = page.locator(".market-card")
        for i in range(cards.count()):
            card = cards.nth(i)
            title_text = card.locator(".market-title").inner_text()
            if "Apple Vision Pro" in title_text or "WWDC" in title_text:
                card.click()
                break

        # Wait for modal
        page.wait_for_selector("#market-modal", state="visible", timeout=5000)

        # Get first candlestick
        chart_section = page.locator("[data-testid='full-chart-section']")
        first_candlestick = chart_section.locator("svg rect.candlestick").first

        # Check if visible
        is_visible = first_candlestick.is_visible()
        print(f"Candlestick is_visible: {is_visible}")

        # Get bounding box (returns None if not visible)
        bbox = first_candlestick.bounding_box()
        print(f"Candlestick bounding_box: {bbox}")

        # Get computed styles
        opacity = first_candlestick.evaluate("el => window.getComputedStyle(el).opacity")
        visibility = first_candlestick.evaluate("el => window.getComputedStyle(el).visibility")
        display = first_candlestick.evaluate("el => window.getComputedStyle(el).display")
        fill = first_candlestick.evaluate("el => window.getComputedStyle(el).fill")
        stroke = first_candlestick.evaluate("el => window.getComputedStyle(el).stroke")
        width = first_candlestick.evaluate("el => el.getAttribute('width')")
        height = first_candlestick.evaluate("el => el.getAttribute('height')")

        print(f"Computed styles:")
        print(f"  opacity: {opacity}")
        print(f"  visibility: {visibility}")
        print(f"  display: {display}")
        print(f"  fill: {fill}")
        print(f"  stroke: {stroke}")
        print(f"  width: {width}")
        print(f"  height: {height}")

        # Diagnose issue
        if not is_visible or bbox is None:
            print("❌ ISSUE FOUND: Candlesticks are in DOM but NOT VISIBLE")
            print(f"   Likely cause: opacity={opacity}, visibility={visibility}, or height={height}")
        elif height == "0" or (bbox and bbox['height'] == 0):
            print("❌ ISSUE FOUND: Candlesticks have height=0 (collapsed)")
        elif opacity == "0":
            print("❌ ISSUE FOUND: Candlesticks have opacity=0 (invisible)")
        else:
            print(f"✓ Candlesticks are visible with dimensions: {bbox}")

        # Always show result
        assert is_visible, f"Candlesticks not visible! opacity={opacity}, visibility={visibility}, height={height}"
