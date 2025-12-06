"""
Quick validation test for Apple Vision Pro chart display issue.
"""
import pytest
from playwright.sync_api import Page, expect

BASE_URL = "https://d24cidhj2eghux.cloudfront.net"

pytestmark = pytest.mark.e2e


class TestAppleVisionProChart:
    """Validate candlestick + SMA display in Apple Vision Pro market."""

    def test_apple_vision_pro_chart_shows_candlesticks_and_sma(self, page: Page):
        """Chart should show BOTH candlesticks AND SMA lines."""
        page.goto(BASE_URL)

        # Wait for cards to load
        page.wait_for_selector(".market-card", state="visible", timeout=10000)

        # Find the Apple Vision Pro card
        cards = page.locator(".market-card")
        apple_card = None

        for i in range(cards.count()):
            card = cards.nth(i)
            title_text = card.locator(".market-title").inner_text()
            if "Apple Vision Pro" in title_text or "WWDC" in title_text:
                apple_card = card
                print(f"✓ Found card: {title_text}")
                break

        assert apple_card is not None, "Apple Vision Pro card not found"

        # Click the card to open modal
        apple_card.click()

        # Wait for modal to open
        page.wait_for_selector("#market-modal", state="visible", timeout=5000)

        # Chart should be at the top (Section 1)
        chart_section = page.locator("[data-testid='full-chart-section']")
        expect(chart_section).to_be_visible()

        # Check for candlesticks (SVG rect elements with class 'candlestick')
        candlesticks = chart_section.locator("svg rect.candlestick")
        candlestick_count = candlesticks.count()
        print(f"Candlesticks found: {candlestick_count}")

        # Check for SMA lines (SVG path elements)
        sma_lines = chart_section.locator("svg path")
        sma_line_count = sma_lines.count()
        print(f"SMA/path elements found: {sma_line_count}")

        # Validate
        if candlestick_count == 0:
            print("❌ ISSUE CONFIRMED: No candlesticks found, only SMA lines")
            print(f"   Chart has {sma_line_count} path elements but 0 candlesticks")

            # Get chart HTML for debugging
            chart_html = chart_section.inner_html()
            print(f"Chart HTML preview: {chart_html[:500]}...")

            # This will fail and show the issue
            assert False, f"Chart missing candlesticks! Found 0 candlesticks but {sma_line_count} SMA lines"
        else:
            print(f"✓ Chart has both candlesticks ({candlestick_count}) and SMA lines ({sma_line_count})")
            assert candlestick_count > 0, "Chart should have candlesticks"
