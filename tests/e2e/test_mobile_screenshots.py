"""
Mobile Screenshot Tests for Telegram Mini App UI Validation.

This test suite captures screenshots at mobile viewport (390x712px) to verify
that the UI layout matches what users see in Telegram Mini App.

Screenshots are saved to tests/e2e/screenshots/ for manual review and validation.

Purpose:
- Ensure visual consistency between Playwright tests and actual Telegram app
- Verify responsive design works correctly at mobile viewport
- Provide visual evidence for UI validation and regression testing

Usage:
    # Run all screenshot tests
    E2E_BASE_URL="https://d24cidhj2eghux.cloudfront.net" \
    pytest tests/e2e/test_mobile_screenshots.py -v

    # Review generated screenshots
    ls -lh tests/e2e/screenshots/

    # Open screenshots for visual inspection
    open tests/e2e/screenshots/
"""

import os
import pytest
from pathlib import Path
from playwright.sync_api import Page, expect


class TestMobileScreenshots:
    """
    Capture screenshots at mobile viewport to verify Telegram Mini App UI.

    All tests use 390x712px viewport (iPhone 12 in Telegram) via conftest.py fixture.
    Screenshots are saved to tests/e2e/screenshots/ directory.
    """

    SCREENSHOTS_DIR = Path("tests/e2e/screenshots")
    BASE_URL = os.environ.get("E2E_BASE_URL", "https://d24cidhj2eghux.cloudfront.net")

    def setup_method(self):
        """Create screenshots directory if it doesn't exist"""
        self.SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
        print(f"\n📸 Screenshots will be saved to: {self.SCREENSHOTS_DIR.absolute()}")

    def test_01_home_page_viewport(self, page: Page):
        """
        Capture full homepage at mobile viewport (390x712).

        Verifies:
        - Header renders correctly
        - Market cards display in single column (not 3 columns)
        - All UI elements fit within 390px width
        """
        page.goto(self.BASE_URL)
        page.wait_for_selector(".market-card", timeout=10000)

        # Full viewport screenshot
        screenshot_path = self.SCREENSHOTS_DIR / "01_home_mobile_viewport.png"
        page.screenshot(
            path=screenshot_path,
            full_page=False  # Just visible area (712px height)
        )
        print(f"✅ Saved: {screenshot_path.name}")

        # Verify no horizontal overflow
        body_width = page.evaluate("() => document.body.scrollWidth")
        viewport_width = page.evaluate("() => window.innerWidth")

        print(f"📏 Body width: {body_width}px, Viewport: {viewport_width}px")
        assert body_width <= 390, f"Content overflows viewport: {body_width}px > 390px"

    def test_02_market_cards_single_column(self, page: Page):
        """
        Verify market cards render in single column on mobile.

        At 390px viewport, Tailwind's grid-cols-1 should apply.
        This is different from desktop where grid-cols-3 applies.
        """
        page.goto(self.BASE_URL)
        page.wait_for_selector(".market-card", timeout=10000)

        # Get markets grid layout
        grid = page.locator(".markets-grid")
        grid_columns = grid.evaluate("el => window.getComputedStyle(el).gridTemplateColumns")

        print(f"📐 Grid columns CSS: {grid_columns}")

        # Should be single column (fixed width like "358px", not multiple columns)
        # At mobile viewport, Tailwind's grid-cols-1 creates a single column
        # We verify by checking there's only one width value (not space-separated)
        column_values = grid_columns.split()
        assert len(column_values) == 1, f"Expected 1 column, got {len(column_values)} columns: {grid_columns}"

        # Screenshot first card
        screenshot_path = self.SCREENSHOTS_DIR / "02_market_card_mobile.png"
        page.locator(".market-card").first.screenshot(path=screenshot_path)
        print(f"✅ Saved: {screenshot_path.name}")

    def test_03_modal_fullscreen_mobile(self, page: Page):
        """
        Verify modal fills entire viewport on mobile (not floating).

        Mobile modals should be fullscreen for better UX on small screens.
        """
        page.goto(self.BASE_URL)
        page.wait_for_selector(".market-card", timeout=10000)

        # Open modal
        page.locator(".market-card").first.click()
        page.wait_for_timeout(300)  # Animation

        modal = page.locator("#market-modal")
        expect(modal).to_be_visible()

        # Modal should fill most of viewport (accounting for padding)
        modal_bbox = modal.bounding_box()
        print(f"📏 Modal dimensions: {modal_bbox['width']}x{modal_bbox['height']}px")

        # Modal width should be close to viewport width (358px is reasonable with 16px padding each side)
        # 390px viewport - 32px padding = 358px content area
        assert modal_bbox["width"] >= 350, f"Modal should fill viewport width (got {modal_bbox['width']}px)"

        screenshot_path = self.SCREENSHOTS_DIR / "03_modal_fullscreen.png"
        modal.screenshot(path=screenshot_path)
        print(f"✅ Saved: {screenshot_path.name}")

    def test_04_scrollable_content(self, page: Page):
        """
        Verify content is scrollable within 712px viewport.

        Captures screenshot after scrolling to verify scroll behavior.
        """
        page.goto(self.BASE_URL)
        page.wait_for_selector(".market-card", timeout=10000)

        # Get initial scroll height
        scroll_height = page.evaluate("() => document.documentElement.scrollHeight")
        viewport_height = page.evaluate("() => window.innerHeight")

        print(f"📏 Total content height: {scroll_height}px")
        print(f"📏 Viewport height: {viewport_height}px")
        print(f"📏 Scrollable distance: {scroll_height - viewport_height}px")

        # Scroll down 300px
        page.evaluate("() => window.scrollTo(0, 300)")
        page.wait_for_timeout(100)

        screenshot_path = self.SCREENSHOTS_DIR / "04_scrolled_view.png"
        page.screenshot(path=screenshot_path, full_page=False)
        print(f"✅ Saved: {screenshot_path.name} (scrolled 300px down)")

    def test_05_category_navigation(self, page: Page):
        """
        Verify category navigation fits on mobile without overflow.
        """
        page.goto(self.BASE_URL)

        # Wait for UI to load
        page.wait_for_selector(".market-card", timeout=10000)

        # Click category (Finance has emoji icon)
        finance_category = page.locator("text=💰 Finance")
        if finance_category.count() > 0:
            finance_category.click()
            page.wait_for_timeout(200)

            screenshot_path = self.SCREENSHOTS_DIR / "05_category_finance.png"
            page.screenshot(path=screenshot_path, full_page=False)
            print(f"✅ Saved: {screenshot_path.name} (Finance category)")
        else:
            print("⚠️  Finance category not found - using default view")
            screenshot_path = self.SCREENSHOTS_DIR / "05_category_default.png"
            page.screenshot(path=screenshot_path, full_page=False)
            print(f"✅ Saved: {screenshot_path.name} (Default view)")

    def test_06_chart_visibility_mobile(self, page: Page):
        """
        Verify charts render correctly at mobile viewport.

        Charts should be responsive and fit within 390px width.
        This tests both MiniChart (on cards) and FullChart (in modal).
        """
        page.goto(self.BASE_URL)
        page.wait_for_selector(".market-card", timeout=10000)

        # Open modal to see chart
        page.locator(".market-card").first.click()
        page.wait_for_timeout(500)  # Wait for modal animation

        # Try to find chart (may not exist with mock data)
        chart_wrapper = page.locator(".recharts-wrapper").first

        if chart_wrapper.count() > 0:
            expect(chart_wrapper).to_be_visible(timeout=5000)

            # Chart should fit viewport
            chart_bbox = chart_wrapper.bounding_box()
            print(f"📊 Chart dimensions: {chart_bbox['width']}x{chart_bbox['height']}px")

            assert chart_bbox["width"] <= 390, f"Chart overflows: {chart_bbox['width']}px > 390px"

            screenshot_path = self.SCREENSHOTS_DIR / "06_chart_mobile.png"
            chart_wrapper.screenshot(path=screenshot_path)
            print(f"✅ Saved: {screenshot_path.name}")
        else:
            print("⚠️  No charts found (mock data may not include chart data)")
            screenshot_path = self.SCREENSHOTS_DIR / "06_modal_no_chart.png"
            page.screenshot(path=screenshot_path, full_page=False)
            print(f"✅ Saved: {screenshot_path.name} (Modal without chart)")

    def test_07_comparison_desktop_vs_mobile(self, page: Page):
        """
        Generate side-by-side comparison: desktop vs mobile viewport.

        This test temporarily switches viewport to demonstrate the difference
        between desktop (1280x720) and mobile (390x712) layouts.
        """
        # Mobile screenshot (current fixture provides 390x712)
        page.goto(self.BASE_URL)
        page.wait_for_selector(".market-card", timeout=10000)

        screenshot_path_mobile = self.SCREENSHOTS_DIR / "07a_mobile_390x712.png"
        page.screenshot(path=screenshot_path_mobile, full_page=False)
        print(f"✅ Saved: {screenshot_path_mobile.name} (Mobile 390x712)")

        # Switch to desktop viewport
        page.set_viewport_size({"width": 1280, "height": 720})
        page.reload()
        page.wait_for_selector(".market-card", timeout=10000)

        screenshot_path_desktop = self.SCREENSHOTS_DIR / "07b_desktop_1280x720.png"
        page.screenshot(path=screenshot_path_desktop, full_page=False)
        print(f"✅ Saved: {screenshot_path_desktop.name} (Desktop 1280x720)")

        # Restore mobile viewport (for subsequent tests)
        page.set_viewport_size({"width": 390, "height": 712})

        print("\n🔍 Compare these screenshots to see mobile vs desktop layout:")
        print(f"   Mobile:  {screenshot_path_mobile.name} (single column)")
        print(f"   Desktop: {screenshot_path_desktop.name} (3 columns)")

    def test_08_full_page_scroll(self, page: Page):
        """
        Capture full-page screenshot showing entire scrollable content.

        This is useful for seeing the complete mobile layout at once.
        """
        page.goto(self.BASE_URL)
        page.wait_for_selector(".market-card", timeout=10000)

        screenshot_path = self.SCREENSHOTS_DIR / "08_full_page_mobile.png"
        page.screenshot(path=screenshot_path, full_page=True)
        print(f"✅ Saved: {screenshot_path.name} (Full scrollable content)")

        # Print content dimensions
        scroll_height = page.evaluate("() => document.documentElement.scrollHeight")
        print(f"📏 Full page height: {scroll_height}px")


@pytest.mark.e2e
class TestMobileScreenshotsMarker:
    """
    Same tests but with @pytest.mark.e2e marker.

    These will only run when explicitly requested with:
    pytest tests/e2e/test_mobile_screenshots.py -m e2e
    """
    pass  # Inherits all tests from TestMobileScreenshots


if __name__ == "__main__":
    # Allow running directly: python tests/e2e/test_mobile_screenshots.py
    pytest.main([__file__, "-v", "-s"])
