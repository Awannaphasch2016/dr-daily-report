"""
E2E Test: Identify Empty Market Cards on Initial Load

User Report: "when page first finished reload, not all boxes are filled with data,
some box is has no data, but when i clicked on it, newest page reload."

Investigation Strategy:
1. Load page and wait for markets
2. Take screenshot of initial state
3. Identify cards with missing data (specifically SMFG19)
4. Click empty card and verify if it triggers reload/sort reset

User Clarifications:
- Empty cards are ALWAYS the same specific tickers (e.g., SMFG19)
- Happens every single page load (consistent, reproducible)
- Data-specific issue, not timing/race condition
"""

import pytest
import re
from playwright.sync_api import Page, expect
from pathlib import Path


@pytest.mark.e2e
def test_identify_empty_market_cards(page: Page):
    """
    Identify which market cards appear empty on initial page load

    This diagnostic test will:
    1. Load the page and wait for markets
    2. Screenshot initial state
    3. Iterate through all cards and identify empty ones
    4. Report which cards have missing data
    """

    # Navigate to production site
    page.goto("https://d24cidhj2eghux.cloudfront.net/")

    # Wait for markets to load
    page.wait_for_selector('[data-market-id]', timeout=15000)

    # Wait a bit longer to ensure all data loads
    page.wait_for_timeout(3000)

    # Take screenshot of initial state
    screenshots_dir = Path("tests/e2e/screenshots")
    screenshots_dir.mkdir(exist_ok=True)
    page.screenshot(path=str(screenshots_dir / "empty_cards_investigation.png"))

    # Get all market cards
    cards = page.locator('[data-market-id]').all()

    print(f"\n{'='*80}")
    print(f"Found {len(cards)} total market cards")
    print(f"{'='*80}\n")

    empty_cards = []

    for i, card in enumerate(cards):
        # Get the market ID
        market_id = card.get_attribute('data-market-id')

        # Try to find title element (card might have different structures)
        # Look for common class patterns for market card titles
        title_selectors = [
            '.market-title',
            '.card-title',
            'h3',
            'h4',
            '[class*="title"]'
        ]

        title_text = None
        for selector in title_selectors:
            try:
                title_elem = card.locator(selector).first
                if title_elem.is_visible(timeout=500):
                    title_text = title_elem.text_content()
                    if title_text and title_text.strip():
                        break
            except:
                continue

        # Try to find price/value elements
        price_selectors = [
            '.market-price',
            '.price',
            '[class*="price"]',
            '[class*="value"]'
        ]

        price_text = None
        for selector in price_selectors:
            try:
                price_elem = card.locator(selector).first
                if price_elem.is_visible(timeout=500):
                    price_text = price_elem.text_content()
                    if price_text and price_text.strip():
                        break
            except:
                continue

        # Get all text content as fallback
        all_text = card.text_content()

        # Check if card appears empty or has missing data
        is_empty = False
        missing_fields = []

        if not title_text or not title_text.strip():
            is_empty = True
            missing_fields.append('title')

        if not price_text or not price_text.strip():
            is_empty = True
            missing_fields.append('price')

        # Check if card has very little text (< 10 chars indicates likely empty)
        if all_text and len(all_text.strip()) < 10:
            is_empty = True
            missing_fields.append('content')

        if is_empty:
            empty_cards.append({
                'index': i,
                'market_id': market_id,
                'title': title_text,
                'price': price_text,
                'all_text': all_text[:100] if all_text else None,
                'missing': missing_fields
            })

            print(f"🔍 EMPTY CARD #{i}:")
            print(f"   Market ID: {market_id}")
            print(f"   Title: {title_text or '(missing)'}")
            print(f"   Price: {price_text or '(missing)'}")
            print(f"   Missing: {', '.join(missing_fields)}")
            print(f"   All text: {all_text[:100] if all_text else '(none)'}...")

            # Check if this is SMFG19 specifically (user mentioned this ticker)
            if market_id and 'SMFG19' in market_id.upper():
                print(f"   ⚠️  THIS IS SMFG19 - the ticker user reported!")
            print()

    print(f"\n{'='*80}")
    print(f"Summary: Found {len(empty_cards)} empty/incomplete cards out of {len(cards)} total")
    print(f"{'='*80}\n")

    # This is a diagnostic test - we don't fail, just report
    # But we do want to know if we found the problematic cards
    if len(empty_cards) > 0:
        print(f"✅ Successfully identified {len(empty_cards)} cards with missing data")
        print(f"   Screenshots saved to: {screenshots_dir / 'empty_cards_investigation.png'}")
    else:
        print(f"ℹ️  No empty cards found - may need to adjust detection logic")


@pytest.mark.e2e
def test_clicking_empty_card_causes_sort_reset(page: Page):
    """
    Verify that clicking an empty card (if found) triggers sort reset

    This test validates the user's claim that clicking empty cards
    causes the page to reload/reset to "Newest" sort.
    """

    # Navigate to production site
    page.goto("https://d24cidhj2eghux.cloudfront.net/")

    # Wait for markets to load
    page.wait_for_selector('[data-market-id]', timeout=15000)
    page.wait_for_timeout(3000)

    # Try to find SMFG19 card specifically (user's example)
    smfg_card = None
    try:
        # Try multiple approaches to find SMFG19
        all_cards = page.locator('[data-market-id]').all()

        for card in all_cards:
            market_id = card.get_attribute('data-market-id')
            card_text = card.text_content()

            # Check if this card contains SMFG19 or Sumitomo Mitsui
            if (market_id and 'SMFG19' in market_id.upper()) or \
               (card_text and ('SMFG19' in card_text.upper() or 'SUMITOMO MITSUI' in card_text.upper())):
                smfg_card = card
                print(f"\n✅ Found SMFG19 card!")
                print(f"   Market ID: {market_id}")
                print(f"   Text: {card_text[:100]}...")
                break

        if not smfg_card:
            print(f"\n⚠️  SMFG19 card not found on page")
            print(f"   Total cards: {len(all_cards)}")
            pytest.skip("SMFG19 card not found - cannot test clicking empty card")
            return

    except Exception as e:
        print(f"\n❌ Error finding SMFG19 card: {e}")
        pytest.skip(f"Error locating SMFG19: {e}")
        return

    # Change sort to "Volume" first to detect reload
    print(f"\n📊 Changing sort to 'Volume' to enable reload detection...")
    volume_btn = page.locator('button[data-sort="volume"]')
    volume_btn.click()
    page.wait_for_timeout(1000)

    # Verify sort changed
    expect(volume_btn).to_have_class(re.compile("active"))
    print(f"✅ Sort changed to 'Volume'")

    # Click the SMFG19 card
    print(f"\n🖱️  Clicking SMFG19 card...")
    smfg_card.click()

    # Wait for any modal or state changes
    page.wait_for_timeout(2000)

    # Check if sort reset to "Newest"
    newest_btn = page.locator('button[data-sort="newest"]')

    # Take screenshot of state after clicking
    screenshots_dir = Path("tests/e2e/screenshots")
    screenshots_dir.mkdir(exist_ok=True)
    page.screenshot(path=str(screenshots_dir / "after_clicking_smfg19.png"))

    # Check current sort state
    is_newest_active = "active" in newest_btn.get_attribute("class")
    is_volume_active = "active" in volume_btn.get_attribute("class")

    print(f"\n📊 Sort state after clicking SMFG19:")
    print(f"   Newest active: {is_newest_active}")
    print(f"   Volume active: {is_volume_active}")

    if is_newest_active:
        print(f"\n❌ BUG CONFIRMED: Clicking SMFG19 reset sort to 'Newest'")
        print(f"   Expected: Volume sort preserved")
        print(f"   Actual: Sort reset to Newest")

        # This confirms the bug
        assert False, "Clicking empty card (SMFG19) caused sort to reset to 'Newest'"
    else:
        print(f"\n✅ Sort preserved as 'Volume' - no reload detected")


@pytest.mark.e2e
def test_smfg19_card_data_content(page: Page):
    """
    Examine the actual HTML structure and data of SMFG19 card

    This diagnostic test inspects what data is actually present
    in the SMFG19 card to understand why it might appear empty.
    """

    # Navigate to production site
    page.goto("https://d24cidhj2eghux.cloudfront.net/")

    # Wait for markets to load
    page.wait_for_selector('[data-market-id]', timeout=15000)
    page.wait_for_timeout(3000)

    # Find SMFG19 card
    all_cards = page.locator('[data-market-id]').all()

    smfg_card = None
    for card in all_cards:
        market_id = card.get_attribute('data-market-id')
        card_text = card.text_content() or ""

        if (market_id and 'SMFG19' in market_id.upper()) or \
           ('SMFG19' in card_text.upper() or 'SUMITOMO MITSUI' in card_text.upper()):
            smfg_card = card

            print(f"\n{'='*80}")
            print(f"SMFG19 Card Data Analysis")
            print(f"{'='*80}\n")

            print(f"Market ID attribute: {market_id}")
            print(f"\nFull text content:\n{card_text}\n")

            # Get HTML structure
            inner_html = card.inner_html()
            print(f"HTML structure (first 500 chars):\n{inner_html[:500]}\n")

            # Try to find specific data elements
            print(f"Data element search:")

            # Company name
            try:
                company_elem = card.locator('[class*="company"], [class*="title"], h3, h4').first
                company_text = company_elem.text_content() if company_elem else None
                print(f"  Company name: {company_text}")
            except:
                print(f"  Company name: (not found)")

            # Price/value
            try:
                price_elem = card.locator('[class*="price"], [class*="value"]').first
                price_text = price_elem.text_content() if price_elem else None
                print(f"  Price: {price_text}")
            except:
                print(f"  Price: (not found)")

            # Volume
            try:
                volume_elem = card.locator('[class*="volume"]').first
                volume_text = volume_elem.text_content() if volume_elem else None
                print(f"  Volume: {volume_text}")
            except:
                print(f"  Volume: (not found)")

            break

    if not smfg_card:
        pytest.skip("SMFG19 card not found for data inspection")
