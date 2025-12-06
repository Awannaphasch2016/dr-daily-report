"""
Pytest configuration for E2E tests with mobile viewport emulation.

This conftest overrides pytest-playwright's default `page` fixture to use
mobile viewport dimensions matching Telegram Mini App on iPhone.

Impact: ALL E2E tests automatically use mobile viewport (390x712px) instead
of desktop (1280x720px), ensuring tests verify the actual user experience.
"""

import pytest
from playwright.sync_api import Browser, BrowserContext, Page

# Telegram Mini App viewport presets for different devices
TELEGRAM_DEVICES = {
    "iPhone 12": {
        "viewport": {"width": 390, "height": 712},  # Telegram Mini App viewport
        "device_scale_factor": 3.0,  # Retina display
        "is_mobile": True,
        "has_touch": True,
        "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148"
    },
    "iPhone 14": {
        "viewport": {"width": 390, "height": 712},  # Same as iPhone 12
        "device_scale_factor": 3.0,
        "is_mobile": True,
        "has_touch": True,
        "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148"
    },
    "Android": {
        "viewport": {"width": 412, "height": 690},  # Typical Android phone
        "device_scale_factor": 2.75,
        "is_mobile": True,
        "has_touch": True,
        "user_agent": "Mozilla/5.0 (Linux; Android 12) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.45 Mobile Safari/537.36"
    }
}


@pytest.fixture(scope="function")
def page(playwright) -> Page:
    """
    Mobile-emulated page fixture for Telegram Mini App testing.

    Overrides pytest-playwright's default fixture to use iPhone 12 viewport
    dimensions (390x712px) that match what users see in Telegram Mini App.

    Viewport breakdown:
    - iPhone 12 physical: 390x844px
    - Telegram header: ~88px
    - Bottom safe area: ~44px
    - Available for Mini App: 390x712px

    This ensures:
    - Tests verify actual mobile layout (single column grid)
    - Screenshots match what users see in Telegram
    - Touch targets and overflow are properly tested
    - Responsive CSS breakpoints are correctly exercised

    Returns:
        Page: Playwright page object with mobile configuration
    """
    device_config = TELEGRAM_DEVICES["iPhone 12"]

    browser: Browser = playwright.chromium.launch()
    context: BrowserContext = browser.new_context(**device_config)
    page = context.new_page()

    yield page

    context.close()
    browser.close()
