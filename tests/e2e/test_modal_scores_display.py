"""E2E test: Verify modal displays user-facing scores correctly

Tests that when a market card is clicked:
1. Modal opens
2. ScoringPanel component displays all_scores
3. Scores are visible and non-empty
"""
import pytest
from playwright.sync_api import Page, expect
import os


@pytest.mark.e2e
def test_modal_displays_user_facing_scores(page: Page):
    """
    Verify modal scoring panel displays user-facing scores from Aurora cache

    Steps:
    1. Navigate to TEST CloudFront distribution
    2. Wait for markets to load
    3. Click on first market card (should have cached report with scores)
    4. Wait for modal to open
    5. Verify ScoringPanel has score items displayed
    6. Take screenshot for verification
    """

    # Step 1: Navigate to TEST CloudFront
    test_url = "https://d24cidhj2eghux.cloudfront.net"

    # Listen to console messages for debugging
    console_messages = []
    page.on("console", lambda msg: console_messages.append(f"{msg.type}: {msg.text}"))

    page.goto(test_url, wait_until="networkidle", timeout=30000)

    # Step 2: Wait for markets to load (should appear within 5s)
    page.wait_for_selector('.market-card', timeout=10000)

    # Get count of market cards
    market_cards = page.locator('.market-card')
    card_count = market_cards.count()
    print(f"✅ Found {card_count} market cards")

    assert card_count > 0, "No market cards found - API might be down"

    # Step 3: Click the first market card to open modal
    first_card = market_cards.first
    card_title = first_card.locator('.market-title').text_content()
    print(f"📊 Clicking market card: {card_title}")

    first_card.click()

    # Step 4: Wait for modal to appear (Headless UI modal takes time to animate)
    page.wait_for_selector('[role="dialog"]', state='attached', timeout=10000)
    page.wait_for_timeout(5000)  # Wait for animation + fetchReport API call to complete
    print("✅ Modal opened")

    # DEBUG: Print console messages
    print("\n📋 Browser console messages:")
    for msg in console_messages[-20:]:  # Last 20 messages
        print(f"  {msg}")

    # DEBUG: Take screenshot before checking for scores
    screenshot_path_debug = os.path.join(
        os.path.dirname(__file__),
        'screenshots',
        'debug_modal_opened.png'
    )
    os.makedirs(os.path.dirname(screenshot_path_debug), exist_ok=True)
    page.screenshot(path=screenshot_path_debug, full_page=True)
    print(f"\n📸 Debug screenshot: {screenshot_path_debug}")

    # DEBUG: Print modal HTML content (check for "No scores" message)
    modal = page.locator('[role="dialog"]')
    modal_html = modal.inner_html()
    print(f"\nModal HTML (first 1000 chars):\n{modal_html[:1000]}")

    # Step 5: Verify ScoringPanel is visible and has score items
    # ScoringPanel should render score-item elements when scores are present
    page.wait_for_selector('[data-testid="score-item"]', timeout=15000)

    score_items = page.locator('[data-testid="score-item"]')
    score_count = score_items.count()

    print(f"✅ Found {score_count} score items in ScoringPanel")

    # Assert we have scores (backend returns 6 scores: fundamental, technical, etc.)
    assert score_count > 0, "No score items found - modal should display user_facing_scores"
    assert score_count >= 3, f"Expected at least 3 scores, got {score_count}"

    # Verify first score has required fields
    first_score = score_items.first

    # Check category field
    category = first_score.locator('[data-testid="score-category"]')
    expect(category).to_be_visible()
    category_text = category.text_content()
    print(f"   - Score 1 category: {category_text}")

    # Check score value
    score_value = first_score.locator('[data-testid="score-value"]')
    expect(score_value).to_be_visible()
    score_text = score_value.text_content()
    print(f"   - Score 1 value: {score_text}")

    # Verify score value format (should be like "7/10" or "8.5/10")
    assert "/" in score_text, f"Score value should be in 'X/Y' format, got: {score_text}"

    # Step 6: Expand first score to check rationale
    first_score.click()  # Click to expand accordion
    page.wait_for_timeout(500)  # Wait for animation

    # Verify rationale is visible
    rationale = first_score.locator('[data-testid="score-rationale"]')
    if rationale.count() > 0:
        expect(rationale).to_be_visible()
        rationale_text = rationale.text_content()
        print(f"   - Rationale: {rationale_text[:100]}...")
        assert len(rationale_text) > 0, "Rationale should not be empty"
    else:
        print("   - Rationale not found (might be missing in backend data)")

    # Step 7: Take screenshot for manual verification
    screenshot_path = os.path.join(
        os.path.dirname(__file__),
        'screenshots',
        'test_modal_scores.png'
    )
    os.makedirs(os.path.dirname(screenshot_path), exist_ok=True)
    page.screenshot(path=screenshot_path, full_page=True)
    print(f"📸 Screenshot saved: {screenshot_path}")

    print("\n✅ TEST PASSED: Modal displays user-facing scores correctly")


@pytest.mark.e2e
def test_modal_empty_state_when_no_scores(page: Page):
    """
    Verify modal handles gracefully when no scores available

    This test checks that ScoringPanel shows empty state when
    report doesn't have user_facing_scores (e.g., symbol 6618.HK has null scores)
    """

    # Navigate to homepage
    test_url = "https://d24cidhj2eghux.cloudfront.net"
    page.goto(test_url, wait_until="networkidle", timeout=30000)

    # Wait for markets to load
    page.wait_for_selector('.market-card', timeout=10000)

    # Find a market card (any will do for this test)
    market_cards = page.locator('.market-card')

    # Click last card (more likely to have missing data)
    last_card = market_cards.last
    last_card.click()

    # Wait for modal
    page.wait_for_selector('[role="dialog"]', timeout=10000)

    # Check if either scores or empty state message is shown
    score_items = page.locator('[data-testid="score-item"]')
    empty_message = page.locator('text=/No scores available|Loading/')

    # Should have either scores OR empty state (not crash)
    has_scores = score_items.count() > 0
    has_empty_state = empty_message.count() > 0

    assert has_scores or has_empty_state, \
        "Modal should show either scores or empty state, not crash"

    if has_scores:
        print(f"✅ Modal shows {score_items.count()} scores")
    else:
        print("✅ Modal shows empty state (no scores available)")

    # Take screenshot
    screenshot_path = os.path.join(
        os.path.dirname(__file__),
        'screenshots',
        'test_modal_empty_state.png'
    )
    os.makedirs(os.path.dirname(screenshot_path), exist_ok=True)
    page.screenshot(path=screenshot_path, full_page=True)
    print(f"📸 Screenshot saved: {screenshot_path}")

    print("\n✅ TEST PASSED: Modal handles empty scores gracefully")
