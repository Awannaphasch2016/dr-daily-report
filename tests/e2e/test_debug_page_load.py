"""Debug test: See what actually loads on the page"""
import pytest
from playwright.sync_api import Page
import os


@pytest.mark.e2e
def test_debug_page_content(page: Page):
    """Take screenshot and print page content to debug"""

    # Navigate to TEST CloudFront
    test_url = "https://d24cidhj2eghux.cloudfront.net"
    page.goto(test_url, wait_until="networkidle", timeout=30000)

    # Wait a bit for any dynamic content
    page.wait_for_timeout(5000)

    # Take screenshot
    screenshot_path = os.path.join(
        os.path.dirname(__file__),
        'screenshots',
        'debug_page_load.png'
    )
    os.makedirs(os.path.dirname(screenshot_path), exist_ok=True)
    page.screenshot(path=screenshot_path, full_page=True)
    print(f"📸 Screenshot saved: {screenshot_path}")

    # Print page title
    title = page.title()
    print(f"Page title: {title}")

    # Print page HTML (first 2000 chars)
    html = page.content()
    print(f"Page HTML (first 2000 chars):\n{html[:2000]}")

    # Check if there are any elements with data-testid
    all_testids = page.locator('[data-testid]').all()
    print(f"\nFound {len(all_testids)} elements with data-testid:")
    for elem in all_testids[:10]:  # Print first 10
        testid = elem.get_attribute('data-testid')
        print(f"  - {testid}")

    # Check console errors
    page.on("console", lambda msg: print(f"Console {msg.type}: {msg.text}"))
