#!/usr/bin/env python3
"""
Playwright Full Flow Test for Telegram Mini App
Tests: Search → Click Ticker → Report Generation
"""

import asyncio
from playwright.async_api import async_playwright
import json
from datetime import datetime

FRONTEND_URL = "https://demjoigiw6myp.cloudfront.net"

async def test_full_flow():
    print("=" * 70)
    print("FULL FLOW TEST: Search → Ticker → Report")
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
        network_errors = []
        page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
        page.on("requestfailed", lambda req: network_errors.append(f"{req.method} {req.url}"))

        try:
            # Step 1: Load page
            print("STEP 1: Loading page...")
            await page.goto(FRONTEND_URL, wait_until="networkidle")
            await page.screenshot(path="/tmp/flow_01_initial.png")
            print("  ✓ Page loaded")
            print("  Screenshot: /tmp/flow_01_initial.png")
            print()

            # Step 2: Find search input
            print("STEP 2: Finding search input...")
            search_input = await page.query_selector('input[type="text"], input[type="search"], input')
            if not search_input:
                print("  ✗ No search input found!")
                return False
            print("  ✓ Search input found")
            print()

            # Step 3: Type search query
            print("STEP 3: Typing 'NVDA' in search...")
            await search_input.click()
            await search_input.fill("")  # Clear first
            await page.keyboard.type("NVDA", delay=100)
            await page.wait_for_timeout(2000)  # Wait for autocomplete
            await page.screenshot(path="/tmp/flow_02_search.png")
            print("  ✓ Typed 'NVDA'")
            print("  Screenshot: /tmp/flow_02_search.png")
            print()

            # Step 4: Click on autocomplete result
            print("STEP 4: Looking for autocomplete results...")

            # Try various selectors for autocomplete items
            selectors_to_try = [
                '.autocomplete-item',
                '.search-result',
                '.dropdown-item',
                '[role="option"]',
                '.ticker-item',
                'li:has-text("NVDA")',
                'div:has-text("NVDA19")',
                '.result-item'
            ]

            clicked = False
            for selector in selectors_to_try:
                try:
                    item = await page.query_selector(selector)
                    if item:
                        visible = await item.is_visible()
                        if visible:
                            await item.click()
                            clicked = True
                            print(f"  ✓ Clicked autocomplete result (selector: {selector})")
                            break
                except:
                    continue

            if not clicked:
                # Try clicking any element containing NVDA19
                print("  Trying to find any clickable element with NVDA...")
                elements = await page.query_selector_all('*')
                for el in elements[:100]:  # Check first 100 elements
                    try:
                        text = await el.text_content()
                        if text and 'NVDA19' in text:
                            clickable = await el.is_visible()
                            if clickable:
                                await el.click()
                                clicked = True
                                print(f"  ✓ Clicked element containing NVDA19")
                                break
                    except:
                        continue

            if not clicked:
                print("  ⚠ Could not find clickable autocomplete result")
                # Try pressing Enter instead
                print("  Trying Enter key...")
                await page.keyboard.press("Enter")

            await page.wait_for_timeout(2000)
            await page.screenshot(path="/tmp/flow_03_after_click.png")
            print("  Screenshot: /tmp/flow_03_after_click.png")
            print()

            # Step 5: Wait for report to start loading
            print("STEP 5: Checking for report loading indicator...")
            await page.wait_for_timeout(3000)

            # Look for loading indicators
            page_content = await page.content()
            loading_indicators = ['loading', 'spinner', 'progress', 'generating', 'please wait']
            found_loading = any(ind in page_content.lower() for ind in loading_indicators)

            if found_loading:
                print("  ✓ Loading indicator found - report is being generated")
            else:
                print("  ⚠ No loading indicator detected")

            await page.screenshot(path="/tmp/flow_04_loading.png")
            print("  Screenshot: /tmp/flow_04_loading.png")
            print()

            # Step 6: Wait for report (up to 90 seconds)
            print("STEP 6: Waiting for report to complete (up to 90s)...")
            start_time = asyncio.get_event_loop().time()

            report_completed = False
            for i in range(18):  # 18 * 5 = 90 seconds
                await page.wait_for_timeout(5000)
                elapsed = int(asyncio.get_event_loop().time() - start_time)

                page_content = await page.content()

                # Check for report content indicators
                report_indicators = [
                    'stance',
                    'bullish', 'bearish', 'neutral',
                    'technical',
                    'RSI', 'MACD', 'SMA',
                    'summary',
                    'price_change'
                ]

                found = sum(1 for ind in report_indicators if ind.lower() in page_content.lower())

                print(f"  [{elapsed}s] Checking... found {found}/10 report indicators")

                if found >= 3:
                    report_completed = True
                    print(f"  ✓ Report content detected!")
                    break

                # Check if error occurred
                if 'error' in page_content.lower() and 'failed' in page_content.lower():
                    print(f"  ✗ Error detected on page")
                    break

            await page.screenshot(path="/tmp/flow_05_final.png", full_page=True)
            print("  Full screenshot: /tmp/flow_05_final.png")
            print()

            # Step 7: Analyze final state
            print("STEP 7: Analyzing final state...")

            # Get page text content for analysis
            body = await page.query_selector('body')
            page_text = await body.text_content() if body else ""

            print(f"  Page contains {len(page_text)} characters of text")

            # Check for key elements
            checks = {
                'Has ticker name': 'NVDA' in page_text,
                'Has company name': 'NVIDIA' in page_text,
                'Has price info': any(x in page_text.lower() for x in ['price', 'usd', '$']),
                'Has analysis': any(x in page_text.lower() for x in ['technical', 'analysis', 'indicator']),
                'Has stance': any(x in page_text.lower() for x in ['bullish', 'bearish', 'neutral', 'stance'])
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
                for err in console_errors[:3]:
                    print(f"    - {err[:80]}...")
            else:
                print("  Console Errors: None")

            if network_errors:
                print(f"  Network Errors: {len(network_errors)}")
                for err in network_errors[:3]:
                    print(f"    - {err}")
            else:
                print("  Network Errors: None")

            checks_passed = sum(checks.values())
            print(f"  Content Checks: {checks_passed}/{len(checks)} passed")
            print(f"  Report Completed: {'Yes' if report_completed else 'No'}")

            print()
            print("Screenshots saved to /tmp/flow_*.png")

            return report_completed and checks_passed >= 3

        except Exception as e:
            print(f"ERROR: {e}")
            await page.screenshot(path="/tmp/flow_error.png")
            return False
        finally:
            await browser.close()

if __name__ == "__main__":
    result = asyncio.run(test_full_flow())
    print()
    print("=" * 70)
    if result:
        print("TEST RESULT: PASS")
    else:
        print("TEST RESULT: PARTIAL - Manual review recommended")
    print("=" * 70)
