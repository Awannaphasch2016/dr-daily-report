# E2E Testing with Playwright

End-to-end browser testing for Telegram Mini App using Playwright.

---

## Overview

E2E tests verify the **complete user journey** from frontend → API → database → backend:
- Frontend renders correctly
- API returns expected data structure
- Charts display with real data
- User interactions work (search, watchlist, etc.)

**Technology:** Playwright (Python) for browser automation

---

## Running E2E Tests

### Quick Start

```bash
# Run all E2E tests against TEST CloudFront
E2E_BASE_URL="https://d24cidhj2eghux.cloudfront.net" pytest tests/e2e/ -m e2e

# Run specific test
E2E_BASE_URL="https://..." pytest tests/e2e/test_twinbar_enhanced.py::test_chart_renders -v

# Run with detailed output
E2E_BASE_URL="https://..." pytest tests/e2e/ -v --tb=short

# Run headful (see browser)
E2E_BASE_URL="https://..." pytest tests/e2e/ --headed
```

###Environment Variables

```bash
# Required
E2E_BASE_URL="https://..."  # CloudFront TEST distribution URL

# Optional
E2E_HEADLESS=false          # Show browser during test
E2E_SLOW_MO=1000            # Slow down actions (ms)
```

---

## Test Structure

### Test Organization

```
tests/e2e/
├── conftest.py                      # Playwright fixtures
├── test_twinbar_enhanced.py         # Main UI tests
├── test_empty_state_components.py   # Empty state handling
└── test_api_integration.py          # API contract tests
```

### Fixture Pattern

```python
# tests/e2e/conftest.py
import pytest
from playwright.sync_api import sync_playwright

@pytest.fixture(scope="session")
def browser():
    """Launch browser once per test session"""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        yield browser
        browser.close()

@pytest.fixture
def page(browser):
    """Create new page for each test"""
    context = browser.new_context(
        viewport={"width": 390, "height": 844},  # iPhone 12 Pro
        user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X)"
    )
    page = context.new_page()
    page.set_default_timeout(30000)  # 30s timeout
    yield page
    context.close()
```

---

## Writing E2E Tests

### Basic Test Pattern

```python
import pytest
from playwright.sync_api import Page, expect

@pytest.mark.e2e
def test_market_card_renders(page: Page):
    """Test that market cards display correctly"""
    # 1. Navigate to app
    page.goto(f"{BASE_URL}")

    # 2. Wait for data to load
    page.wait_for_selector("[data-testid='market-card']", timeout=10000)

    # 3. Verify elements exist
    card = page.locator("[data-testid='market-card']").first
    expect(card).to_be_visible()

    # 4. Verify data populated
    ticker = card.locator("[data-testid='ticker-symbol']")
    expect(ticker).not_to_be_empty()
```

### Testing User Interactions

```python
@pytest.mark.e2e
def test_search_ticker(page: Page):
    """Test ticker search functionality"""
    page.goto(f"{BASE_URL}")

    # Type in search box
    search_input = page.locator("[data-testid='search-input']")
    search_input.fill("NVDA")

    # Wait for results
    results = page.locator("[data-testid='search-result']")
    expect(results).to_have_count(1)

    # Click result
    results.first.click()

    # Verify navigation to detail page
    expect(page).to_have_url(f"{BASE_URL}/ticker/NVDA19")
```

### Testing Charts

```python
@pytest.mark.e2e
def test_chart_renders_with_data(page: Page):
    """Test that charts render with actual price data"""
    page.goto(f"{BASE_URL}")

    # Wait for chart component
    chart = page.locator("[data-testid='mini-chart']").first
    chart.wait_for(state="visible", timeout=10000)

    # Verify SVG exists (Recharts renders <svg>)
    svg = chart.locator("svg")
    expect(svg).to_be_visible()

    # Verify has data (check for path elements)
    paths = svg.locator("path")
    expect(paths).to_have_count_greater_than(0)
```

### Testing Empty States

```python
@pytest.mark.e2e
def test_empty_state_when_no_data(page: Page):
    """Component should show empty state, not disappear"""
    page.goto(f"{BASE_URL}/ticker/INVALID")

    # Chart component should still exist
    chart = page.locator("[data-testid='mini-chart']")
    expect(chart).to_be_visible()

    # Should show empty state message
    empty_state = chart.locator(".empty-state")
    expect(empty_state).to_be_visible()
    expect(empty_state).to_contain_text("No chart data available")
```

---

## Common Patterns

### Wait for Network Idle

```python
# Wait for API calls to complete
page.goto(f"{BASE_URL}", wait_until="networkidle")
```

### Wait for Specific Element

```python
# Wait for element before interacting
button = page.locator("[data-testid='submit-button']")
button.wait_for(state="visible", timeout=5000)
button.click()
```

### Check API Response

```python
# Intercept API calls
with page.expect_response(lambda r: "/api/v1/rankings" in r.url) as response_info:
    page.goto(f"{BASE_URL}")

response = response_info.value
assert response.status == 200
data = response.json()
assert len(data) > 0
```

### Screenshots on Failure

```python
@pytest.fixture(autouse=True)
def screenshot_on_failure(page: Page, request):
    """Take screenshot if test fails"""
    yield
    if request.node.rep_call.failed:
        page.screenshot(path=f"screenshots/{request.node.name}.png")
```

---

## Test Data Management

### Using Fixtures for Test Data

```python
# tests/e2e/conftest.py
@pytest.fixture
def sample_tickers():
    """Known tickers with cached data"""
    return ["NVDA19", "DBS19", "MWG19"]

# Usage in test
def test_tickers_load(page: Page, sample_tickers):
    for ticker in sample_tickers:
        page.goto(f"{BASE_URL}/ticker/{ticker}")
        expect(page.locator("[data-testid='ticker-symbol']")).to_contain_text(ticker)
```

### Pre-populating Cache

```bash
# Before running E2E tests, populate Aurora cache
aws lambda invoke \
  --function-name dr-daily-report-ticker-scheduler-dev \
  --payload '{"action":"parallel_precompute","include_report":true}' \
  /tmp/result.json

# Wait for completion (~5 minutes)
# Then run E2E tests
```

---

## Common Issues

### Timeout Waiting for Selector

**Problem:** `TimeoutError: Timeout 30000ms exceeded`

**Solutions:**
```python
# Increase timeout
page.set_default_timeout(60000)  # 60s

# Or per-selector
page.wait_for_selector("[data-testid='chart']", timeout=60000)

# Wait for network idle first
page.goto(url, wait_until="networkidle")
```

### Element Not Found

**Problem:** `Error: strict mode violation: locator resolved to X elements`

**Solutions:**
```python
# Be more specific
page.locator("[data-testid='market-card']").first

# Or use nth()
page.locator("[data-testid='market-card']").nth(0)

# Filter by text
page.locator("[data-testid='market-card']:has-text('NVDA')")
```

### Flaky Tests

**Problem:** Test passes locally, fails in CI

**Solutions:**
```python
# 1. Add explicit waits
page.wait_for_load_state("networkidle")

# 2. Wait for element state
button.wait_for(state="visible")
button.wait_for(state="enabled")

# 3. Use expect with retries (built-in)
expect(element).to_be_visible()  # Retries for 5s by default
```

### CI/CD Integration

```yaml
# .github/workflows/deploy.yml
jobs:
  e2e-tests:
    runs-on: ubuntu-latest
    steps:
      - name: Install Playwright
        run: |
          pip install playwright pytest-playwright
          playwright install chromium

      - name: Run E2E tests against TEST CloudFront
        env:
          E2E_BASE_URL: ${{ secrets.CLOUDFRONT_TEST_DOMAIN }}
        run: |
          pytest tests/e2e/ -m e2e --tb=short

      - name: Upload screenshots on failure
        if: failure()
        uses: actions/upload-artifact@v3
        with:
          name: e2e-screenshots
          path: screenshots/
```

---

## Best Practices

### 1. Use data-testid Attributes

```tsx
// frontend/twinbar/src/components/MiniChart.tsx
<div data-testid="mini-chart" className="...">
  {/* ... */}
</div>
```

**Why:** Decouples tests from CSS classes (which change frequently)

### 2. Test User Behavior, Not Implementation

```python
# GOOD: Test what user sees
def test_user_can_add_to_watchlist(page):
    page.click("[data-testid='add-to-watchlist']")
    expect(page.locator("[data-testid='watchlist-count']")).to_contain_text("1")

# BAD: Test internal state
def test_watchlist_api_called(page):
    # Don't test if API was called - test the RESULT the user sees
    pass
```

### 3. Independent Tests

```python
# GOOD: Each test is self-contained
def test_search():
    page.goto(BASE_URL)
    # ... test search

def test_filter():
    page.goto(BASE_URL)
    # ... test filter (doesn't depend on previous test)

# BAD: Tests depend on each other
def test_login():
    # ...
def test_dashboard():
    # Assumes login() ran first ❌
```

### 4. Clean State Between Tests

```python
@pytest.fixture(autouse=True)
def cleanup(page):
    """Clear state before each test"""
    yield
    # Clear localStorage
    page.evaluate("localStorage.clear()")
    # Clear cookies
    page.context.clear_cookies()
```

---

## Debugging Tests

### Run Headful Mode

```bash
# See browser during test
E2E_BASE_URL="..." pytest tests/e2e/ --headed --slowmo=1000
```

### Playwright Inspector

```bash
# Opens interactive debugger
PWDEBUG=1 pytest tests/e2e/test_twinbar_enhanced.py::test_chart_renders
```

### Add Debug Prints

```python
def test_debug_chart(page: Page):
    page.goto(BASE_URL)

    # Print page HTML
    print(page.content())

    # Print element count
    charts = page.locator("[data-testid='mini-chart']")
    print(f"Found {charts.count()} charts")

    # Take screenshot
    page.screenshot(path="debug.png")
```

### Check Console Logs

```python
def test_with_console_logs(page: Page):
    page.on("console", lambda msg: print(f"Browser log: {msg.text}"))
    page.goto(BASE_URL)
    # Console.log() from frontend will print here
```

---

## Test Coverage Goals

### Critical Paths (Must Test)
- ✅ Market cards render with correct data
- ✅ Charts display price history
- ✅ Ticker search returns results
- ✅ Report generation completes
- ✅ Empty states show meaningful messages

### Nice to Have
- Watchlist add/remove
- Filter by category (top gainers, etc.)
- Sort by column
- Mobile responsive layout
- Dark mode toggle (if implemented)

---

## Performance Testing

### Measure Page Load Time

```python
import time

def test_page_load_performance(page: Page):
    start = time.time()
    page.goto(BASE_URL)
    page.wait_for_load_state("networkidle")
    load_time = time.time() - start

    # Assert loads within acceptable time
    assert load_time < 5.0, f"Page took {load_time:.2f}s to load (max 5s)"
```

### Check API Response Times

```python
def test_api_response_time(page: Page):
    with page.expect_response(lambda r: "/api/v1/rankings" in r.url) as response_info:
        page.goto(BASE_URL)

    response = response_info.value
    timing = response.request.timing

    # Check server response time
    assert timing["responseEnd"] - timing["requestStart"] < 3000  # < 3s
```

---

## References

- [Playwright Python Docs](https://playwright.dev/python/)
- [Pytest-Playwright Plugin](https://github.com/microsoft/playwright-pytest)
- [CLAUDE.md Testing Guidelines](.claude/CLAUDE.md#testing-guidelines)
- [Empty State Testing Patterns](../e2e/test_empty_state_components.py)
