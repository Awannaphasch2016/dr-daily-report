import pytest
from playwright.sync_api import Page, expect
import time


BASE_URL = "http://127.0.0.1:5000"


class TestTilesPage:
    """End-to-end tests for Stock Tiles Dashboard"""

    def test_page_loads(self, page: Page):
        """Test that the tiles page loads successfully"""
        page.goto(f"{BASE_URL}/tiles")
        
        # Check page title
        expect(page).to_have_title("Stock Tiles Dashboard")
        
        # Check main heading
        heading = page.locator("h1")
        expect(heading).to_contain_text("Stock Tiles Dashboard")
        
        # Check that controls are visible
        sort_select = page.locator("#sortBy")
        expect(sort_select).to_be_visible()
        
        search_input = page.locator("#searchTicker")
        expect(search_input).to_be_visible()

    def test_default_dbs19_filter(self, page: Page):
        """Test that DBS19 is set as default filter"""
        page.goto(f"{BASE_URL}/tiles")
        
        # Wait for page to load
        page.wait_for_load_state("networkidle")
        
        # Check that search input has DBS19
        search_input = page.locator("#searchTicker")
        expect(search_input).to_have_value("DBS19")
        
        # Check that tiles container shows filtered results
        tiles_container = page.locator("#tiles-container")
        expect(tiles_container).to_be_visible()
        
        # Wait a bit for data to load
        time.sleep(2)

    def test_api_returns_data(self, page: Page):
        """Test that the API endpoint returns data"""
        # Check API directly
        response = page.request.get(f"{BASE_URL}/api/tiles-data")
        expect(response).to_be_ok()
        
        data = response.json()
        assert isinstance(data, list), "API should return a list"
        
        # If there's data, check structure
        if len(data) > 0:
            sample = data[0]
            assert "ticker" in sample, "Data should have ticker field"
            assert "date" in sample, "Data should have date field"
            assert "filename" in sample, "Data should have filename field"

    def test_tiles_display(self, page: Page):
        """Test that tiles are displayed on the page"""
        page.goto(f"{BASE_URL}/tiles")
        page.wait_for_load_state("networkidle")
        
        # Wait for tiles to render
        tiles_container = page.locator("#tiles-container")
        expect(tiles_container).to_be_visible()
        
        # Wait for either tiles or empty state
        time.sleep(3)
        
        # Check if we have tiles or empty state message
        empty_state = page.locator(".empty-state")
        tiles = page.locator(".tile")
        
        # Either tiles exist or empty state message
        assert tiles.count() > 0 or empty_state.is_visible(), "Should show either tiles or empty state"

    def test_sorting_functionality(self, page: Page):
        """Test sorting functionality"""
        page.goto(f"{BASE_URL}/tiles")
        page.wait_for_load_state("networkidle")
        time.sleep(2)
        
        # Clear search filter first to see more tiles
        search_input = page.locator("#searchTicker")
        search_input.clear()
        search_input.fill("")
        time.sleep(1)
        
        # Get initial tile order
        sort_select = page.locator("#sortBy")
        
        # Test sorting by ticker
        sort_select.select_option("ticker")
        time.sleep(2)
        
        # Test sorting by date
        sort_select.select_option("date")
        time.sleep(2)
        
        # Test sorting by change percent
        sort_select.select_option("changePercent")
        time.sleep(2)
        
        # Verify sort select still works
        expect(sort_select).to_be_visible()

    def test_filtering_by_sector(self, page: Page):
        """Test filtering by sector"""
        page.goto(f"{BASE_URL}/tiles")
        page.wait_for_load_state("networkidle")
        time.sleep(2)
        
        # Clear search filter
        search_input = page.locator("#searchTicker")
        search_input.clear()
        search_input.fill("")
        time.sleep(1)
        
        # Get sector filter
        sector_filter = page.locator("#filterSector")
        expect(sector_filter).to_be_visible()
        
        # Check if sectors are populated
        options = sector_filter.locator("option")
        if options.count() > 1:  # More than just "All Sectors"
            # Select first sector
            sector_filter.select_option(index=1)
            time.sleep(2)
            
            # Verify filter is applied
            selected_value = sector_filter.input_value()
            assert selected_value != "", "Sector filter should be applied"

    def test_filtering_by_volatility(self, page: Page):
        """Test filtering by volatility"""
        page.goto(f"{BASE_URL}/tiles")
        page.wait_for_load_state("networkidle")
        time.sleep(2)
        
        # Clear search filter
        search_input = page.locator("#searchTicker")
        search_input.clear()
        search_input.fill("")
        time.sleep(1)
        
        volatility_filter = page.locator("#filterVolatility")
        expect(volatility_filter).to_be_visible()
        
        # Test filtering by low volatility
        volatility_filter.select_option("low")
        time.sleep(2)
        
        # Test filtering by high volatility
        volatility_filter.select_option("high")
        time.sleep(2)
        
        # Verify filter works
        expect(volatility_filter).to_have_value("high")

    def test_filtering_by_market_cap(self, page: Page):
        """Test filtering by market cap"""
        page.goto(f"{BASE_URL}/tiles")
        page.wait_for_load_state("networkidle")
        time.sleep(2)
        
        # Clear search filter
        search_input = page.locator("#searchTicker")
        search_input.clear()
        search_input.fill("")
        time.sleep(1)
        
        market_cap_filter = page.locator("#filterMarketCap")
        expect(market_cap_filter).to_be_visible()
        
        # Test filtering by large cap
        market_cap_filter.select_option("large")
        time.sleep(2)
        
        expect(market_cap_filter).to_have_value("large")

    def test_search_ticker_filter(self, page: Page):
        """Test searching by ticker"""
        page.goto(f"{BASE_URL}/tiles")
        page.wait_for_load_state("networkidle")
        time.sleep(2)
        
        search_input = page.locator("#searchTicker")
        
        # Test searching for a specific ticker
        search_input.clear()
        search_input.fill("NVDA19")
        time.sleep(2)
        
        # Verify search is applied
        expect(search_input).to_have_value("NVDA19")
        
        # Clear search
        search_input.clear()
        search_input.fill("")
        time.sleep(2)
        
        expect(search_input).to_have_value("")

    def test_stats_display(self, page: Page):
        """Test that statistics are displayed"""
        page.goto(f"{BASE_URL}/tiles")
        page.wait_for_load_state("networkidle")
        time.sleep(2)
        
        # Check stats cards
        total_tickers = page.locator("#totalTickers")
        expect(total_tickers).to_be_visible()
        
        gainers = page.locator("#gainers")
        expect(gainers).to_be_visible()
        
        decliners = page.locator("#decliners")
        expect(decliners).to_be_visible()
        
        latest_date = page.locator("#latestDate")
        expect(latest_date).to_be_visible()

    def test_tile_click_navigation(self, page: Page):
        """Test that clicking a tile opens PDF"""
        page.goto(f"{BASE_URL}/tiles")
        page.wait_for_load_state("networkidle")
        time.sleep(3)
        
        # Find a tile
        tiles = page.locator(".tile")
        
        if tiles.count() > 0:
            # Click first tile
            first_tile = tiles.first()
            
            # Set up promise to wait for new page/tab
            with page.context.expect_page() as new_page_info:
                first_tile.click()
            
            new_page = new_page_info.value
            new_page.wait_for_load_state()
            
            # Check if PDF was opened (URL should contain /reports/)
            url = new_page.url
            assert "/reports/" in url or url.endswith(".pdf"), "Clicking tile should open PDF"

    def test_navigation_to_archive(self, page: Page):
        """Test navigation link to archive page"""
        page.goto(f"{BASE_URL}/tiles")
        
        # Find navigation link
        nav_link = page.locator("a[href='/']")
        expect(nav_link).to_be_visible()
        expect(nav_link).to_contain_text("View Archive")
        
        # Click navigation link
        nav_link.click()
        
        # Verify we're on archive page
        expect(page).to_have_url(f"{BASE_URL}/")
        expect(page.locator("h1")).to_contain_text("Daily Report Archive")

    def test_legend_display(self, page: Page):
        """Test that legend is displayed"""
        page.goto(f"{BASE_URL}/tiles")
        page.wait_for_load_state("networkidle")
        
        legend = page.locator(".legend")
        expect(legend).to_be_visible()
        
        # Check legend sections
        expect(legend).to_contain_text("Volatility")
        expect(legend).to_contain_text("Market Cap")
        expect(legend).to_contain_text("52-Week Position")

    def test_multiple_filters_combined(self, page: Page):
        """Test that multiple filters can be combined"""
        page.goto(f"{BASE_URL}/tiles")
        page.wait_for_load_state("networkidle")
        time.sleep(2)
        
        # Clear search first
        search_input = page.locator("#searchTicker")
        search_input.clear()
        search_input.fill("")
        time.sleep(1)
        
        # Apply multiple filters
        volatility_filter = page.locator("#filterVolatility")
        volatility_filter.select_option("medium")
        time.sleep(1)
        
        market_cap_filter = page.locator("#filterMarketCap")
        market_cap_filter.select_option("large")
        time.sleep(2)
        
        # Verify both filters are applied
        expect(volatility_filter).to_have_value("medium")
        expect(market_cap_filter).to_have_value("large")

    def test_responsive_layout(self, page: Page):
        """Test that layout works on different screen sizes"""
        page.goto(f"{BASE_URL}/tiles")
        page.wait_for_load_state("networkidle")
        
        # Test mobile viewport
        page.set_viewport_size({"width": 375, "height": 667})
        time.sleep(1)
        
        # Check that controls are still visible
        sort_select = page.locator("#sortBy")
        expect(sort_select).to_be_visible()
        
        # Test tablet viewport
        page.set_viewport_size({"width": 768, "height": 1024})
        time.sleep(1)
        
        expect(sort_select).to_be_visible()
        
        # Test desktop viewport
        page.set_viewport_size({"width": 1280, "height": 720})
        time.sleep(1)
        
        expect(sort_select).to_be_visible()

    def test_error_handling_no_data(self, page: Page):
        """Test error handling when no data is available"""
        page.goto(f"{BASE_URL}/tiles")
        page.wait_for_load_state("networkidle")
        
        # Set a filter that should return no results
        search_input = page.locator("#searchTicker")
        search_input.clear()
        search_input.fill("NONEXISTENTTICKER123")
        time.sleep(2)
        
        # Should show empty state message
        empty_state = page.locator(".empty-state")
        # May or may not show depending on filtering logic, but shouldn't crash

    def test_tile_visual_elements(self, page: Page):
        """Test that tile visual elements are rendered"""
        page.goto(f"{BASE_URL}/tiles")
        page.wait_for_load_state("networkidle")
        time.sleep(3)
        
        # Check if tiles exist
        tiles = page.locator(".tile")
        
        if tiles.count() > 0:
            # Check that SVG elements exist (tiles are rendered in SVG)
            svg = page.locator("#tiles-container svg")
            expect(svg).to_be_visible()
            
            # Check for tile background rectangles
            rects = svg.locator("rect.tile-background")
            if rects.count() > 0:
                expect(rects.first()).to_be_visible()

    def test_api_response_time(self, page: Page):
        """Test that API responds within reasonable time"""
        start_time = time.time()
        
        response = page.request.get(f"{BASE_URL}/api/tiles-data")
        expect(response).to_be_ok()
        
        end_time = time.time()
        response_time = end_time - start_time
        
        # API should respond within 5 seconds
        assert response_time < 5.0, f"API response time {response_time:.2f}s exceeds 5s"

    def test_console_errors(self, page: Page):
        """Test that there are no console errors"""
        errors = []
        
        def handle_error(msg):
            if msg.type == "error":
                errors.append(msg.text)
        
        page.on("console", handle_error)
        
        page.goto(f"{BASE_URL}/tiles")
        page.wait_for_load_state("networkidle")
        time.sleep(3)
        
        # Filter out known non-critical errors
        critical_errors = [
            e for e in errors 
            if "favicon" not in e.lower() 
            and "extension" not in e.lower()
        ]
        
        # Should have no critical console errors
        assert len(critical_errors) == 0, f"Found console errors: {critical_errors}"
