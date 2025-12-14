"""E2E test: Verify price chart displays in modal

Tests that when a market card is clicked:
1. Modal opens
2. Price chart section is visible
3. Chart canvas/SVG element renders
"""
import pytest
from playwright.sync_api import Page, expect
import os


@pytest.mark.e2e
def test_modal_displays_price_chart(page: Page):
    """
    Verify modal displays price chart with historical data

    Steps:
    1. Navigate to TEST CloudFront distribution
    2. Wait for markets to load
    3. Click on first market card
    4. Wait for modal to open
    5. Verify FullChart section exists
    6. Verify chart SVG/canvas element is rendered
    7. Take screenshot for visual verification
    """

    # Step 1: Navigate to TEST CloudFront
    test_url = "https://d24cidhj2eghux.cloudfront.net"

    # Listen to console errors
    console_messages = []
    page.on("console", lambda msg: console_messages.append(f"{msg.type}: {msg.text}"))

    page.goto(test_url, wait_until="networkidle", timeout=30000)

    # Step 2: Wait for markets to load
    page.wait_for_selector('.market-card', timeout=10000)

    market_cards = page.locator('.market-card')
    card_count = market_cards.count()
    print(f"✅ Found {card_count} market cards")

    # Step 3: Click the first market card
    first_card = market_cards.first
    card_title = first_card.locator('.market-title').text_content()
    print(f"📊 Clicking market card: {card_title}")

    first_card.click()

    # Step 4: Wait for modal to appear
    page.wait_for_selector('[role="dialog"]', state='attached', timeout=10000)
    page.wait_for_timeout(5000)  # Wait for fetchReport to complete
    print("✅ Modal opened")

    # Step 5: Check for FullChart section
    chart_section = page.locator('[data-testid="full-chart-section"]')
    chart_section_count = chart_section.count()
    print(f"\n📊 FullChart section count: {chart_section_count}")

    if chart_section_count > 0:
        print("✅ FullChart section found")

        # Check if section is visible
        is_visible = chart_section.is_visible()
        print(f"   - Is visible: {is_visible}")

        # Get section HTML
        section_html = chart_section.inner_html()
        print(f"   - Section HTML (first 500 chars): {section_html[:500]}")
    else:
        print("❌ FullChart section NOT FOUND")

    # Step 6: Check for chart rendering elements
    # Recharts typically renders SVG elements
    svg_elements = page.locator('[data-testid="full-chart-section"] svg')
    svg_count = svg_elements.count()
    print(f"\n📊 SVG elements in chart section: {svg_count}")

    # Check for canvas (alternative chart renderer)
    canvas_elements = page.locator('[data-testid="full-chart-section"] canvas')
    canvas_count = canvas_elements.count()
    print(f"📊 Canvas elements in chart section: {canvas_count}")

    # Check for any chart-related elements
    recharts_wrapper = page.locator('.recharts-wrapper')
    recharts_count = recharts_wrapper.count()
    print(f"📊 Recharts wrapper elements: {recharts_count}")

    # Step 7: Print relevant console messages
    print("\n📋 Console messages (errors/warnings):")
    error_messages = [msg for msg in console_messages if 'error' in msg.lower() or 'width' in msg.lower()]
    for msg in error_messages[-10:]:
        print(f"  {msg}")

    # Step 8: Take screenshot for visual verification
    screenshot_path = os.path.join(
        os.path.dirname(__file__),
        'screenshots',
        'test_modal_chart_display.png'
    )
    os.makedirs(os.path.dirname(screenshot_path), exist_ok=True)
    page.screenshot(path=screenshot_path, full_page=True)
    print(f"\n📸 Screenshot saved: {screenshot_path}")

    # Step 9: Validate chart is actually rendering
    if chart_section_count == 0:
        print("\n❌ VALIDATION FAILED: FullChart section not found in modal")
        assert False, "FullChart section missing from modal"

    if svg_count == 0 and canvas_count == 0:
        print("\n❌ VALIDATION FAILED: No SVG or Canvas elements found in chart section")
        print("   This suggests the chart is not rendering properly")
        assert False, "Chart not rendering - no SVG or Canvas elements found"

    if recharts_count == 0:
        print("\n⚠️ WARNING: No recharts-wrapper found - chart may not be rendering")

    # Check if chart has actual data
    modal = page.locator('[role="dialog"]')
    modal_text = modal.inner_text()

    # Look for empty state messages
    if "No data available" in modal_text or "Loading" in modal_text:
        print(f"\n⚠️ WARNING: Chart may be showing empty state")
        lines = modal_text.split('\n')
        relevant_lines = [s for s in lines if 'No data' in s or 'Loading' in s]
        print(f"   Modal text contains: {relevant_lines}")

    print("\n✅ TEST PASSED: Chart section exists (see screenshot for visual confirmation)")


@pytest.mark.e2e
def test_compare_card_vs_modal_chart(page: Page):
    """
    Compare chart display in card (MiniChart) vs modal (FullChart)

    This test checks if both charts are rendering to isolate the issue
    """

    test_url = "https://d24cidhj2eghux.cloudfront.net"
    page.goto(test_url, wait_until="networkidle", timeout=30000)

    # Wait for markets to load
    page.wait_for_selector('.market-card', timeout=10000)

    # Step 1: Check if MiniChart displays in cards
    mini_chart = page.locator('[data-testid="mini-chart"]').first
    mini_chart_count = page.locator('[data-testid="mini-chart"]').count()
    print(f"📊 MiniChart elements on page: {mini_chart_count}")

    if mini_chart_count > 0:
        # Check if MiniChart has SVG
        mini_svg = page.locator('[data-testid="mini-chart"] svg').count()
        print(f"   - MiniChart SVG elements: {mini_svg}")
        print("✅ MiniChart renders in cards")
    else:
        print("❌ MiniChart NOT found in cards")

    # Step 2: Open modal and check FullChart
    first_card = page.locator('.market-card').first
    first_card.click()

    page.wait_for_selector('[role="dialog"]', state='attached', timeout=10000)
    page.wait_for_timeout(5000)

    full_chart_section = page.locator('[data-testid="full-chart-section"]')
    full_chart_count = full_chart_section.count()
    print(f"\n📊 FullChart section in modal: {full_chart_count}")

    if full_chart_count > 0:
        full_svg = page.locator('[data-testid="full-chart-section"] svg').count()
        print(f"   - FullChart SVG elements: {full_svg}")

        if full_svg > 0:
            print("✅ FullChart renders in modal")
        else:
            print("❌ FullChart section exists but NO SVG elements (chart not rendering!)")
    else:
        print("❌ FullChart section NOT found in modal")

    # Take comparison screenshot
    screenshot_path = os.path.join(
        os.path.dirname(__file__),
        'screenshots',
        'test_chart_comparison.png'
    )
    os.makedirs(os.path.dirname(screenshot_path), exist_ok=True)
    page.screenshot(path=screenshot_path, full_page=True)
    print(f"\n📸 Comparison screenshot: {screenshot_path}")

    # Summary
    print(f"\n📊 SUMMARY:")
    print(f"   - MiniChart (cards): {mini_chart_count} found, {mini_svg if mini_chart_count > 0 else 0} SVG")
    print(f"   - FullChart (modal): {full_chart_count} found, {full_svg if full_chart_count > 0 else 0} SVG")

    if mini_chart_count > 0 and mini_svg > 0 and (full_chart_count == 0 or full_svg == 0):
        print("\n❌ USER'S CLAIM VALIDATED: MiniChart works but FullChart does NOT render in modal")
        assert False, "Chart displays in cards but not in modal - regression confirmed"
    elif full_chart_count > 0 and full_svg > 0:
        print("\n✅ Chart displays correctly in both card and modal")
    else:
        print("\n⚠️ Charts not rendering in either location - different issue")
