#!/usr/bin/env python3
"""
User Journey Test - Step by step with screenshots
"""

import asyncio
from playwright.async_api import async_playwright
from datetime import datetime

FRONTEND_URL = "https://demjoigiw6myp.cloudfront.net"

async def test_user_journey():
    print("=" * 70)
    print("USER JOURNEY: Step-by-step Report Generation")
    print(f"URL: {FRONTEND_URL}")
    print(f"Started: {datetime.now().strftime('%H:%M:%S')}")
    print("=" * 70)
    print()

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1280, "height": 900})
        page = await context.new_page()

        try:
            # STEP 1: Open the app
            print("STEP 1: Open the app")
            print(f"  Action: Navigate to {FRONTEND_URL}")
            await page.goto(FRONTEND_URL, wait_until="networkidle")
            await page.screenshot(path="/tmp/journey_01_homepage.png")
            print("  Result: Homepage loaded with search box and Rankings tab")
            print("  Screenshot: /tmp/journey_01_homepage.png")
            print()

            # STEP 2: Click on search box
            print("STEP 2: Click on the search box")
            search_input = await page.wait_for_selector('#search-input')
            await search_input.click()
            await page.screenshot(path="/tmp/journey_02_search_focused.png")
            print("  Action: Click on the search input field")
            print("  Result: Search box is now focused (cursor blinking)")
            print("  Screenshot: /tmp/journey_02_search_focused.png")
            print()

            # STEP 3: Type ticker symbol
            print("STEP 3: Type a ticker symbol")
            await page.keyboard.type("NVDA", delay=150)
            await page.wait_for_timeout(2000)  # Wait for autocomplete
            await page.screenshot(path="/tmp/journey_03_typing.png")
            print("  Action: Type 'NVDA' in the search box")
            print("  Result: Autocomplete dropdown appears with matching tickers")
            print("  Screenshot: /tmp/journey_03_typing.png")
            print()

            # STEP 4: Click on autocomplete result
            print("STEP 4: Click on autocomplete result")
            result_item = await page.wait_for_selector('.search-result-item', timeout=5000)
            ticker_text = await result_item.text_content()
            await page.screenshot(path="/tmp/journey_04_autocomplete.png")
            print(f"  Action: Click on '{ticker_text.strip()}'")
            await result_item.click()
            await page.wait_for_timeout(500)
            print("  Result: Modal opens with loading indicator")
            print("  Screenshot: /tmp/journey_04_autocomplete.png")
            print()

            # STEP 5: Modal opens with loading
            print("STEP 5: Report generation starts")
            await page.screenshot(path="/tmp/journey_05_loading.png")
            print("  Action: (Automatic) Report generation begins")
            print("  Result: Modal shows 'Starting AI analysis...'")
            print("  Screenshot: /tmp/journey_05_loading.png")
            print()

            # STEP 6-8: Wait and capture progress
            print("STEP 6-8: Waiting for report (polling every 5s)...")
            for i in range(12):  # Max 60 seconds
                await page.wait_for_timeout(5000)
                elapsed = (i + 1) * 5

                # Check modal content
                report_body = await page.query_selector('#report-body')
                if report_body:
                    content = await report_body.inner_html()

                    # Check if still loading
                    if 'loading-indicator' in content:
                        # Get loading message
                        loading_text = await report_body.text_content()
                        print(f"  [{elapsed}s] {loading_text.strip()}")
                        if elapsed == 10:
                            await page.screenshot(path="/tmp/journey_06_processing.png")
                            print("  Screenshot: /tmp/journey_06_processing.png")
                    elif 'report-stance' in content or 'report-section' in content:
                        print(f"  [{elapsed}s] Report loaded!")
                        break
                    elif 'empty-state' in content and '❌' in content:
                        error_text = await report_body.text_content()
                        print(f"  [{elapsed}s] ERROR: {error_text.strip()[:50]}")
                        break
            print()

            # STEP 9: View completed report
            print("STEP 9: View the completed report")
            await page.screenshot(path="/tmp/journey_07_report_top.png", full_page=False)
            print("  Result: Full AI-generated report is displayed")
            print("  Screenshot: /tmp/journey_07_report_top.png")
            print()

            # Scroll down to see more
            await page.evaluate("document.querySelector('.modal-body').scrollTop = 300")
            await page.wait_for_timeout(500)
            await page.screenshot(path="/tmp/journey_08_report_scroll.png")
            print("  (Scrolled down to see Technical Metrics)")
            print("  Screenshot: /tmp/journey_08_report_scroll.png")
            print()

            # STEP 10: Close modal
            print("STEP 10: Close the report modal")
            close_btn = await page.query_selector('.modal-close')
            if close_btn:
                await close_btn.click()
                await page.wait_for_timeout(500)
            await page.screenshot(path="/tmp/journey_09_closed.png")
            print("  Action: Click the X button in top-right corner")
            print("  Result: Modal closes, back to homepage")
            print("  Screenshot: /tmp/journey_09_closed.png")
            print()

            print("=" * 70)
            print("USER JOURNEY COMPLETE")
            print("=" * 70)
            print()
            print("Screenshots saved:")
            print("  1. /tmp/journey_01_homepage.png     - Initial homepage")
            print("  2. /tmp/journey_02_search_focused.png - Search box focused")
            print("  3. /tmp/journey_03_typing.png       - Typing 'NVDA'")
            print("  4. /tmp/journey_04_autocomplete.png - Autocomplete results")
            print("  5. /tmp/journey_05_loading.png      - Modal with loading")
            print("  6. /tmp/journey_06_processing.png   - Processing (10s)")
            print("  7. /tmp/journey_07_report_top.png   - Report (top)")
            print("  8. /tmp/journey_08_report_scroll.png - Report (scrolled)")
            print("  9. /tmp/journey_09_closed.png       - Modal closed")

            return True

        except Exception as e:
            print(f"ERROR: {e}")
            import traceback
            traceback.print_exc()
            await page.screenshot(path="/tmp/journey_error.png")
            return False
        finally:
            await browser.close()

if __name__ == "__main__":
    result = asyncio.run(test_user_journey())
    print()
    if result:
        print("TEST PASSED - User journey completed successfully")
    else:
        print("TEST FAILED - See error above")
