"""
Check if SMA values and candlestick values are on different scales.
"""
import pytest
from playwright.sync_api import Page

BASE_URL = "https://d24cidhj2eghux.cloudfront.net"

pytestmark = pytest.mark.e2e


class TestChartDataMismatch:
    """Validate SMA vs candlestick price scale mismatch."""

    def test_sma_vs_candlestick_price_ranges(self, page: Page):
        """Check if SMA and candlestick data are on wildly different scales."""
        page.goto(BASE_URL)
        page.wait_for_selector(".market-card", state="visible", timeout=10000)

        # Find Apple Vision Pro card
        cards = page.locator(".market-card")
        for i in range(cards.count()):
            card = cards.nth(i)
            title_text = card.locator(".market-title").inner_text()
            if "Apple Vision Pro" in title_text or "WWDC" in title_text:
                print(f"✓ Found card: {title_text}")
                card.click()
                break

        # Wait for modal
        page.wait_for_selector("#market-modal", state="visible", timeout=5000)

        # Get chart SVG
        chart_section = page.locator("[data-testid='full-chart-section']")
        svg = chart_section.locator("svg").first

        # Get candlestick Y positions (Y coordinate in SVG)
        candlesticks = chart_section.locator("svg rect.candlestick")
        candlestick_y_values = []
        for i in range(min(5, candlesticks.count())):  # Sample first 5
            cs = candlesticks.nth(i)
            y = cs.get_attribute("y")
            height = cs.get_attribute("height")
            candlestick_y_values.append({"y": float(y), "height": float(height)})

        print(f"\nCandlestick positions (SVG coordinates):")
        for i, cs in enumerate(candlestick_y_values):
            print(f"  Candlestick {i}: y={cs['y']:.2f}, height={cs['height']:.2f}")

        # Get SMA path positions
        sma_paths = chart_section.locator("svg path")
        sma_path_data = []
        for i in range(sma_paths.count()):
            path = sma_paths.nth(i)
            d = path.get_attribute("d")
            stroke = path.get_attribute("stroke")
            if d:
                sma_path_data.append({"d": d[:100], "stroke": stroke})  # First 100 chars

        print(f"\nSMA path data:")
        for i, sma in enumerate(sma_path_data):
            print(f"  Path {i}: d={sma['d']}... stroke={sma['stroke']}")

        # Extract Y values from path data (format: "M x y L x y ...")
        # Parse first path to get Y range
        if sma_path_data:
            d = sma_path_data[0]['d']
            # Extract numbers from path
            import re
            numbers = re.findall(r'-?\d+\.?\d*', d)
            # Y values are at odd indices (x, y, x, y, ...)
            y_values = [float(numbers[i]) for i in range(1, min(10, len(numbers)), 2)]
            print(f"\nSMA Y values (SVG coordinates): {y_values[:5]}")

            # Compare ranges
            candlestick_y_range = [cs['y'] for cs in candlestick_y_values]
            avg_candlestick_y = sum(candlestick_y_range) / len(candlestick_y_range)
            avg_sma_y = sum(y_values[:5]) / min(5, len(y_values))

            print(f"\nComparison:")
            print(f"  Avg Candlestick Y: {avg_candlestick_y:.2f}")
            print(f"  Avg SMA Y: {avg_sma_y:.2f}")
            print(f"  Difference: {abs(avg_candlestick_y - avg_sma_y):.2f}px")

            if abs(avg_candlestick_y - avg_sma_y) > 100:
                print(f"\n❌ ISSUE CONFIRMED: SMA and Candlesticks on different scales!")
                print(f"   They're {abs(avg_candlestick_y - avg_sma_y):.0f}px apart in SVG space")
            else:
                print(f"\n✓ SMA and Candlesticks appear to be on same scale")

        # Now check the actual DATA values being rendered
        # Get the React component's data prop
        market_data = page.evaluate("""() => {
            // Try to access the chart data from the DOM
            const chartSection = document.querySelector('[data-testid="full-chart-section"]');
            if (!chartSection) return null;

            // Check if we can find the data in React fiber
            const fiberKey = Object.keys(chartSection).find(key => key.startsWith('__reactFiber'));
            if (!fiberKey) return null;

            const fiber = chartSection[fiberKey];
            // Walk up to find FullChart component
            let current = fiber;
            while (current) {
                if (current.memoizedProps && current.memoizedProps.data) {
                    return current.memoizedProps.data.slice(0, 5); // First 5 data points
                }
                current = current.return;
            }
            return null;
        }""")

        if market_data:
            print(f"\n📊 Actual data being passed to chart:")
            for i, point in enumerate(market_data):
                print(f"  Point {i}: {point}")

            # Check price ranges
            closes = [p.get('close', 0) for p in market_data if 'close' in p]
            if closes:
                print(f"\n  Close prices: min={min(closes):.2f}, max={max(closes):.2f}")
                if max(closes) < 50:
                    print(f"  ❌ ISSUE: Candlestick data in ${closes[0]:.0f}s range (too low!)")
                elif min(closes) > 400:
                    print(f"  ⚠️  Data in ${closes[0]:.0f}s range (very high)")
        else:
            print("\n⚠️  Could not extract chart data from React component")
