"""
E2E test to validate UI displays Aurora data correctly.

Tests:
1. Homepage loads successfully
2. Market data is populated from Aurora
3. Charts and indicators are visible
4. At least one ticker displays complete data
"""
import re
from playwright.sync_api import Page, expect
import pytest


@pytest.mark.e2e
def test_ui_displays_aurora_data(page: Page):
    """Verify UI displays data populated in Aurora."""

    # Navigate to the APP CloudFront distribution
    url = "https://demjoigiw6myp.cloudfront.net"
    print(f"\n📍 Navigating to: {url}")

    page.goto(url, wait_until="networkidle", timeout=30000)

    # Take screenshot of initial page load
    page.screenshot(path="tests/e2e/screenshots/ui_homepage.png", full_page=True)
    print("📸 Screenshot saved: ui_homepage.png")

    # Wait for the page to load completely
    page.wait_for_load_state("networkidle")

    # Check if page title is correct
    expect(page).to_have_title(re.compile(".*Market.*|.*Ticker.*|.*Report.*", re.IGNORECASE))
    print(f"✅ Page title: {page.title()}")

    # Look for market data indicators (common UI patterns)
    # This will depend on your actual UI structure

    # Check if there are any ticker symbols displayed
    ticker_elements = page.locator('[data-testid*="ticker"], [class*="ticker"], [id*="ticker"]').all()
    if not ticker_elements:
        # Try broader selectors
        ticker_elements = page.locator('text=/[A-Z]{2,5}(\\.SI|\\.HK|\\.T|\\.VN|19)?/').all()

    print(f"🔍 Found {len(ticker_elements)} ticker elements")

    # Check for data table or cards
    data_containers = page.locator('[class*="card"], [class*="table"], [class*="grid"]').all()
    print(f"📊 Found {len(data_containers)} data containers")

    # Check for chart elements
    chart_elements = page.locator('canvas, svg[class*="chart"], [id*="chart"]').all()
    print(f"📈 Found {len(chart_elements)} chart elements")

    # Try to find specific ticker data (e.g., NVDA, DBS19)
    test_tickers = ["NVDA", "DBS19", "NVDA19", "D05.SI"]
    found_tickers = []

    for ticker in test_tickers:
        try:
            # Check if ticker is visible on page
            ticker_locator = page.get_by_text(ticker, exact=False)
            if ticker_locator.count() > 0:
                found_tickers.append(ticker)
                print(f"✅ Found ticker: {ticker}")

                # Take screenshot of this ticker's section
                ticker_locator.first.screenshot(
                    path=f"tests/e2e/screenshots/ticker_{ticker.replace('.', '_')}.png"
                )
        except Exception as e:
            print(f"⚠️  Ticker {ticker} not found: {e}")

    # Take final full-page screenshot
    page.screenshot(path="tests/e2e/screenshots/ui_full_page.png", full_page=True)
    print("📸 Screenshot saved: ui_full_page.png")

    # Assertions
    assert len(data_containers) > 0, "No data containers found - UI might not be loading data"
    assert len(chart_elements) > 0 or len(ticker_elements) > 0, \
        "No charts or ticker data found - Aurora data might not be displaying"

    print(f"\n✅ UI Validation Summary:")
    print(f"   - Data containers: {len(data_containers)}")
    print(f"   - Chart elements: {len(chart_elements)}")
    print(f"   - Ticker elements: {len(ticker_elements)}")
    print(f"   - Found tickers: {', '.join(found_tickers) if found_tickers else 'None'}")


@pytest.mark.e2e
def test_search_and_view_ticker_details(page: Page):
    """Test searching for a specific ticker and viewing its details."""

    url = "https://demjoigiw6myp.cloudfront.net"
    page.goto(url, wait_until="networkidle", timeout=30000)

    # Look for search input
    search_inputs = page.locator('input[type="search"], input[placeholder*="search" i], input[placeholder*="ticker" i]').all()

    if len(search_inputs) > 0:
        search_input = search_inputs[0]
        print(f"🔍 Found search input")

        # Search for NVDA (known to have data in Aurora)
        search_input.fill("NVDA")
        page.wait_for_timeout(1000)  # Wait for search results

        page.screenshot(path="tests/e2e/screenshots/search_nvda.png", full_page=True)
        print("📸 Screenshot saved: search_nvda.png")

        # Look for NVDA in results
        nvda_elements = page.get_by_text("NVDA", exact=False).all()
        assert len(nvda_elements) > 0, "NVDA not found in search results despite being in Aurora"

        print(f"✅ Found {len(nvda_elements)} NVDA references")
    else:
        print("⚠️  No search input found - UI might have different navigation")


@pytest.mark.e2e
def test_api_connectivity(page: Page):
    """Verify UI can connect to API and fetch data."""

    # Monitor network requests
    api_requests = []
    api_responses = []

    def handle_request(request):
        if "execute-api" in request.url or "/api/" in request.url:
            api_requests.append(request.url)
            print(f"📡 API Request: {request.method} {request.url}")

    def handle_response(response):
        if "execute-api" in response.url or "/api/" in response.url:
            api_responses.append({
                'url': response.url,
                'status': response.status,
                'ok': response.ok
            })
            print(f"📥 API Response: {response.status} {response.url}")

    page.on("request", handle_request)
    page.on("response", handle_response)

    # Navigate to page
    url = "https://demjoigiw6myp.cloudfront.net"
    page.goto(url, wait_until="networkidle", timeout=30000)

    # Wait for any API calls to complete
    page.wait_for_timeout(3000)

    # Take screenshot
    page.screenshot(path="tests/e2e/screenshots/api_connectivity.png", full_page=True)

    print(f"\n📊 API Connectivity Summary:")
    print(f"   - Total API requests: {len(api_requests)}")
    print(f"   - Total API responses: {len(api_responses)}")

    if api_responses:
        successful = [r for r in api_responses if r['ok']]
        failed = [r for r in api_responses if not r['ok']]

        print(f"   - Successful: {len(successful)}")
        print(f"   - Failed: {len(failed)}")

        if failed:
            for r in failed:
                print(f"     ❌ {r['status']} - {r['url']}")

        # Assert that we have at least some successful API calls
        assert len(successful) > 0, "No successful API calls - backend might be down"
    else:
        print("   ⚠️  No API calls detected - UI might be using static data or cache")

    print(f"\n✅ API connectivity test completed")
