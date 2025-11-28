#!/usr/bin/env python3
"""
Improved Playwright Full Flow Test for Telegram Mini App
Uses correct selectors based on frontend code analysis
"""

import asyncio
from playwright.async_api import async_playwright
from datetime import datetime

FRONTEND_URL = "https://demjoigiw6myp.cloudfront.net"

async def test_full_flow():
    print("=" * 70)
    print("IMPROVED FLOW TEST: Search → Click → Modal → Report")
    print(f"URL: {FRONTEND_URL}")
    print(f"Started: {datetime.now().isoformat()}")
    print("=" * 70)
    print()

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1280, "height": 900})
        page = await context.new_page()

        # Collect errors
        console_errors = []
        console_logs = []
        network_requests = []

        page.on("console", lambda msg: (
            console_errors.append(msg.text) if msg.type == "error"
            else console_logs.append(f"[{msg.type}] {msg.text}")
        ))
        page.on("request", lambda req: network_requests.append(f"{req.method} {req.url}"))
        page.on("requestfailed", lambda req: console_errors.append(f"Network: {req.method} {req.url}"))

        try:
            # Step 1: Load page
            print("STEP 1: Loading page...")
            await page.goto(FRONTEND_URL, wait_until="networkidle")
            await page.screenshot(path="/tmp/improved_01_initial.png")
            print("  ✓ Page loaded")
            print()

            # Step 2: Verify search input exists
            print("STEP 2: Finding search input (#search-input)...")
            search_input = await page.wait_for_selector('#search-input', timeout=5000)
            if not search_input:
                print("  ✗ Search input not found!")
                return False
            print("  ✓ Search input found")
            print()

            # Step 3: Type search query
            print("STEP 3: Typing 'NVDA' in search...")
            await search_input.click()
            await page.keyboard.type("NVDA", delay=100)
            print("  ✓ Typed 'NVDA'")
            print()

            # Step 4: Wait for search results dropdown
            print("STEP 4: Waiting for search results (#search-results)...")
            await page.wait_for_timeout(2000)  # Wait for debounce + API

            # Check if search results are visible
            search_results = await page.query_selector('#search-results')
            if search_results:
                is_hidden = await search_results.evaluate("el => el.classList.contains('hidden')")
                if not is_hidden:
                    print("  ✓ Search results dropdown visible")
                else:
                    print("  ⚠ Search results exist but has 'hidden' class")
            else:
                print("  ✗ Search results container not found")

            await page.screenshot(path="/tmp/improved_02_search.png")
            print("  Screenshot: /tmp/improved_02_search.png")
            print()

            # Step 5: Look for search result items
            print("STEP 5: Looking for .search-result-item elements...")
            result_items = await page.query_selector_all('.search-result-item')
            print(f"  Found {len(result_items)} search result items")

            if len(result_items) > 0:
                # Get text of first result
                first_item = result_items[0]
                text = await first_item.text_content()
                ticker = await first_item.get_attribute('data-ticker')
                print(f"  First result: '{text.strip()}' (ticker: {ticker})")
                print()

                # Step 6: Click on first result
                print("STEP 6: Clicking on first search result...")
                await first_item.click()
                print("  ✓ Clicked")
                await page.wait_for_timeout(1000)
                await page.screenshot(path="/tmp/improved_03_clicked.png")
                print("  Screenshot: /tmp/improved_03_clicked.png")
                print()
            else:
                print("  ⚠ No search results found, trying Enter key...")
                await page.keyboard.press("Enter")
                await page.wait_for_timeout(1000)
                await page.screenshot(path="/tmp/improved_03_enter.png")
                print()

            # Step 7: Check if modal appeared
            print("STEP 7: Checking for modal (#report-modal)...")
            modal = await page.query_selector('#report-modal')
            if modal:
                is_hidden = await modal.evaluate("el => el.classList.contains('hidden')")
                is_visible = await modal.evaluate("el => el.classList.contains('visible')")
                print(f"  Modal hidden class: {is_hidden}")
                print(f"  Modal visible class: {is_visible}")

                if not is_hidden and is_visible:
                    print("  ✓ Modal is showing!")
                else:
                    print("  ✗ Modal exists but not visible")
            else:
                print("  ✗ Modal element not found")

            await page.screenshot(path="/tmp/improved_04_modal.png")
            print("  Screenshot: /tmp/improved_04_modal.png")
            print()

            # Step 8: Wait for report content
            print("STEP 8: Waiting for report content (up to 60s)...")
            report_body = await page.query_selector('#report-body')

            for i in range(12):  # 12 * 5 = 60 seconds
                await page.wait_for_timeout(5000)

                if report_body:
                    content = await report_body.inner_html()

                    # Check for loading indicator
                    if 'loading-indicator' in content:
                        print(f"  [{(i+1)*5}s] Still loading...")
                        continue

                    # Check for report content
                    if 'report-stance' in content or 'report-section' in content:
                        print(f"  ✓ Report content appeared after {(i+1)*5}s!")
                        break

                    # Check for error
                    if 'empty-state' in content and '❌' in content:
                        error_text = await report_body.text_content()
                        print(f"  ✗ Error in report: {error_text.strip()[:100]}")
                        break

            await page.screenshot(path="/tmp/improved_05_report.png", full_page=True)
            print("  Screenshot: /tmp/improved_05_report.png")
            print()

            # Step 9: Analyze final state
            print("STEP 9: Analyzing final state...")

            # Check modal content
            modal_ticker = await page.query_selector('#report-ticker')
            if modal_ticker:
                ticker_text = await modal_ticker.text_content()
                print(f"  Report ticker header: '{ticker_text}'")

            # Get report body content
            if report_body:
                body_text = await report_body.text_content()
                print(f"  Report body length: {len(body_text)} chars")

                # Check for key elements
                checks = {
                    'Has stance': any(x in body_text.lower() for x in ['bullish', 'bearish', 'neutral']),
                    'Has company name': 'NVIDIA' in body_text or 'nvidia' in body_text.lower(),
                    'Has technical': 'technical' in body_text.lower() or 'RSI' in body_text or 'MACD' in body_text,
                    'Has loading error': 'failed' in body_text.lower(),
                }

                for check, passed in checks.items():
                    status = "✓" if passed else "✗"
                    print(f"  {status} {check}")
            print()

            # Summary
            print("=" * 70)
            print("SUMMARY")
            print("=" * 70)

            if console_errors:
                print(f"  Console Errors: {len(console_errors)}")
                for err in console_errors[:5]:
                    print(f"    - {err[:100]}")
            else:
                print("  Console Errors: None")

            # Check for API calls
            api_calls = [r for r in network_requests if 'api' in r.lower()]
            print(f"  API Calls Made: {len(api_calls)}")
            for call in api_calls[:5]:
                print(f"    - {call}")

            print()
            print("Screenshots saved to /tmp/improved_*.png")

            # Determine pass/fail
            modal_visible = modal and not is_hidden and is_visible if modal else False
            return modal_visible

        except Exception as e:
            print(f"ERROR: {e}")
            import traceback
            traceback.print_exc()
            await page.screenshot(path="/tmp/improved_error.png")
            return False
        finally:
            await browser.close()

if __name__ == "__main__":
    result = asyncio.run(test_full_flow())
    print()
    print("=" * 70)
    if result:
        print("TEST RESULT: PASS - Modal appeared")
    else:
        print("TEST RESULT: FAIL - Modal did not appear")
    print("=" * 70)
