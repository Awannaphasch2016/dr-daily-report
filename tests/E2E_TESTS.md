# Playwright End-to-End Tests

## Overview

This directory contains end-to-end tests for the Stock Tiles Dashboard using Playwright.

## Prerequisites

1. Install dependencies:
```bash
pip install -r requirements.txt
playwright install chromium
```

2. Start the Flask application:
```bash
cd webapp
python app.py
```

The app should be running at `http://127.0.0.1:5000`

## Running Tests

### Run all E2E tests:
```bash
pytest tests/test_tiles_e2e.py --browser chromium
```

### Run with UI (headed mode):
```bash
pytest tests/test_tiles_e2e.py --browser chromium --headed
```

### Run specific test:
```bash
pytest tests/test_tiles_e2e.py::TestTilesPage::test_page_loads --browser chromium
```

### Run using shell script:
```bash
./tests/run_e2e_tests.sh
```

## Test Coverage

The E2E tests cover:

1. **Page Loading**
   - Page loads successfully
   - All UI elements are visible
   - API endpoint returns data

2. **Default Behavior**
   - DBS19 filter is applied by default
   - Tiles are displayed correctly

3. **Filtering**
   - Filter by sector
   - Filter by volatility
   - Filter by market cap
   - Filter by recommendation
   - Search by ticker
   - Multiple filters combined

4. **Sorting**
   - Sort by ticker
   - Sort by date
   - Sort by change percent
   - Sort by price, volume, etc.

5. **Navigation**
   - Click tile opens PDF
   - Navigation to archive page

6. **Visual Elements**
   - Stats display correctly
   - Legend is visible
   - Tiles render correctly

7. **Responsive Design**
   - Layout works on mobile
   - Layout works on tablet
   - Layout works on desktop

8. **Error Handling**
   - No data scenarios
   - Console errors
   - API response time

## Test Structure

```
tests/
├── test_tiles_e2e.py      # Main E2E test file
├── conftest.py            # Pytest fixtures
└── run_e2e_tests.sh       # Test runner script
```

## Debugging

### View test execution:
```bash
pytest tests/test_tiles_e2e.py --browser chromium --headed --slowmo=1000
```

### Generate HTML report:
```bash
pytest tests/test_tiles_e2e.py --browser chromium --html=report.html
```

### Debug mode:
```bash
pytest tests/test_tiles_e2e.py --browser chromium --pdb
```

## CI/CD Integration

To run in CI/CD, use:
```bash
pytest tests/test_tiles_e2e.py --browser chromium --headless
```

## Troubleshooting

1. **Tests fail with connection error**: Make sure Flask app is running
2. **Browser not found**: Run `playwright install chromium`
3. **Timeout errors**: Increase timeout in pytest.ini or test file
4. **Flaky tests**: Add more wait conditions or increase sleep times
