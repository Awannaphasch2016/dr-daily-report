#!/usr/bin/env python3
"""
Playwright UI Test for Telegram Mini App
Tests the frontend at https://demjoigiw6myp.cloudfront.net
"""

import asyncio
from playwright.async_api import async_playwright
import json

FRONTEND_URL = "https://demjoigiw6myp.cloudfront.net"

async def test_ui():
    results = {
        "tests": [],
        "passed": 0,
        "failed": 0,
        "screenshots": []
    }

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1280, "height": 720}
        )
        page = await context.new_page()

        # Collect console errors
        console_errors = []
        page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)

        print("=" * 60)
        print("PLAYWRIGHT UI TEST")
        print(f"URL: {FRONTEND_URL}")
        print("=" * 60)
        print()

        # Test 1: Page loads successfully
        print("TEST 1: Page Load")
        try:
            response = await page.goto(FRONTEND_URL, wait_until="networkidle")
            status = response.status if response else 0

            if status == 200:
                print(f"  [PASS] Page loaded with status {status}")
                results["passed"] += 1
                results["tests"].append({"name": "Page Load", "status": "PASS"})
            else:
                print(f"  [FAIL] Page returned status {status}")
                results["failed"] += 1
                results["tests"].append({"name": "Page Load", "status": "FAIL", "error": f"Status {status}"})
        except Exception as e:
            print(f"  [FAIL] Error: {e}")
            results["failed"] += 1
            results["tests"].append({"name": "Page Load", "status": "FAIL", "error": str(e)})

        # Take screenshot of initial page
        await page.screenshot(path="/tmp/ui_test_01_initial.png")
        results["screenshots"].append("/tmp/ui_test_01_initial.png")
        print("  Screenshot: /tmp/ui_test_01_initial.png")
        print()

        # Test 2: Check page title
        print("TEST 2: Page Title")
        title = await page.title()
        if "DR Daily Report" in title:
            print(f"  [PASS] Title: {title}")
            results["passed"] += 1
            results["tests"].append({"name": "Page Title", "status": "PASS", "value": title})
        else:
            print(f"  [FAIL] Unexpected title: {title}")
            results["failed"] += 1
            results["tests"].append({"name": "Page Title", "status": "FAIL", "value": title})
        print()

        # Test 3: Search box exists
        print("TEST 3: Search Box Present")
        search_box = await page.query_selector('input[type="text"], input[type="search"], #search, .search-input')
        if search_box:
            print("  [PASS] Search box found")
            results["passed"] += 1
            results["tests"].append({"name": "Search Box Present", "status": "PASS"})
        else:
            # Try alternative selectors
            search_box = await page.query_selector('input')
            if search_box:
                print("  [PASS] Input element found (possible search box)")
                results["passed"] += 1
                results["tests"].append({"name": "Search Box Present", "status": "PASS"})
            else:
                print("  [FAIL] No search box found")
                results["failed"] += 1
                results["tests"].append({"name": "Search Box Present", "status": "FAIL"})
        print()

        # Test 4: Type in search and check autocomplete
        print("TEST 4: Search Autocomplete")
        try:
            # Find any input field
            input_field = await page.query_selector('input')
            if input_field:
                await input_field.click()
                await input_field.fill("NVDA")
                await page.wait_for_timeout(1500)  # Wait for autocomplete

                # Take screenshot after typing
                await page.screenshot(path="/tmp/ui_test_02_search.png")
                results["screenshots"].append("/tmp/ui_test_02_search.png")
                print("  Screenshot: /tmp/ui_test_02_search.png")

                # Check for autocomplete results
                autocomplete = await page.query_selector('.autocomplete, .search-results, .dropdown, [role="listbox"]')
                if autocomplete:
                    visible = await autocomplete.is_visible()
                    if visible:
                        print("  [PASS] Autocomplete dropdown appeared")
                        results["passed"] += 1
                        results["tests"].append({"name": "Search Autocomplete", "status": "PASS"})
                    else:
                        print("  [WARN] Autocomplete element exists but not visible")
                        results["tests"].append({"name": "Search Autocomplete", "status": "WARN"})
                else:
                    # Check if results appeared anywhere
                    page_content = await page.content()
                    if "NVDA" in page_content and ("NVIDIA" in page_content or "nvda" in page_content.lower()):
                        print("  [PASS] Search results contain NVDA/NVIDIA")
                        results["passed"] += 1
                        results["tests"].append({"name": "Search Autocomplete", "status": "PASS"})
                    else:
                        print("  [FAIL] No autocomplete results found")
                        results["failed"] += 1
                        results["tests"].append({"name": "Search Autocomplete", "status": "FAIL"})
            else:
                print("  [SKIP] No input field to test")
                results["tests"].append({"name": "Search Autocomplete", "status": "SKIP"})
        except Exception as e:
            print(f"  [FAIL] Error: {e}")
            results["failed"] += 1
            results["tests"].append({"name": "Search Autocomplete", "status": "FAIL", "error": str(e)})
        print()

        # Test 5: Check for navigation/tabs
        print("TEST 5: Navigation Elements")
        nav_elements = await page.query_selector_all('nav, .nav, .tabs, [role="tablist"], .navigation')
        buttons = await page.query_selector_all('button')
        links = await page.query_selector_all('a')

        print(f"  Found: {len(nav_elements)} nav elements, {len(buttons)} buttons, {len(links)} links")
        if len(buttons) > 0 or len(nav_elements) > 0:
            print("  [PASS] Navigation elements present")
            results["passed"] += 1
            results["tests"].append({"name": "Navigation Elements", "status": "PASS", "buttons": len(buttons), "links": len(links)})
        else:
            print("  [WARN] Limited navigation elements")
            results["tests"].append({"name": "Navigation Elements", "status": "WARN"})
        print()

        # Test 6: Console Errors
        print("TEST 6: Console Errors")
        if len(console_errors) == 0:
            print("  [PASS] No console errors")
            results["passed"] += 1
            results["tests"].append({"name": "Console Errors", "status": "PASS"})
        else:
            print(f"  [FAIL] {len(console_errors)} console errors:")
            for err in console_errors[:5]:  # Show first 5
                print(f"    - {err[:100]}")
            results["failed"] += 1
            results["tests"].append({"name": "Console Errors", "status": "FAIL", "errors": console_errors[:10]})
        print()

        # Test 7: Check CSS loaded (page has styling)
        print("TEST 7: CSS Styling")
        body_bg = await page.evaluate("() => getComputedStyle(document.body).backgroundColor")
        body_font = await page.evaluate("() => getComputedStyle(document.body).fontFamily")

        if body_bg and body_font and body_bg != "rgba(0, 0, 0, 0)":
            print(f"  [PASS] CSS loaded - background: {body_bg}, font: {body_font[:30]}...")
            results["passed"] += 1
            results["tests"].append({"name": "CSS Styling", "status": "PASS"})
        else:
            print("  [WARN] CSS may not be fully loaded")
            results["tests"].append({"name": "CSS Styling", "status": "WARN"})
        print()

        # Test 8: Check API URL is configured
        print("TEST 8: API URL Configuration")
        api_url = await page.evaluate("() => window.TELEGRAM_API_URL || 'not set'")
        if api_url and "execute-api" in api_url:
            print(f"  [PASS] API URL configured: {api_url}")
            results["passed"] += 1
            results["tests"].append({"name": "API URL Configuration", "status": "PASS", "url": api_url})
        else:
            print(f"  [FAIL] API URL not properly configured: {api_url}")
            results["failed"] += 1
            results["tests"].append({"name": "API URL Configuration", "status": "FAIL", "url": api_url})
        print()

        # Final screenshot
        await page.screenshot(path="/tmp/ui_test_03_final.png", full_page=True)
        results["screenshots"].append("/tmp/ui_test_03_final.png")
        print("  Full page screenshot: /tmp/ui_test_03_final.png")

        await browser.close()

    # Summary
    print()
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"  Passed: {results['passed']}")
    print(f"  Failed: {results['failed']}")
    print(f"  Screenshots saved to /tmp/ui_test_*.png")
    print()

    # Save results to JSON
    with open("/tmp/ui_test_results.json", "w") as f:
        json.dump(results, f, indent=2)
    print("  Results saved to /tmp/ui_test_results.json")

    return results

if __name__ == "__main__":
    asyncio.run(test_ui())
