#!/usr/bin/env python3
"""
Unit tests for RankingsService

Following TDD methodology - these tests are written BEFORE implementation.
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock
from src.api.rankings_service import RankingsService, RankingItem


class TestRankingsService:
    """Test suite for RankingsService"""

    @pytest.fixture
    def service(self):
        """Create RankingsService instance for testing"""
        return RankingsService(cache_ttl_seconds=300)

    @pytest.fixture
    def mock_ticker_data(self):
        """Mock ticker data from yfinance"""
        return {
            'NVDA19': {
                'regularMarketPrice': 150.0,
                'regularMarketPreviousClose': 145.0,
                'regularMarketVolume': 5000000,
                'averageVolume': 3000000,
                'shortName': 'NVIDIA Corp',
                'currency': 'USD',
                'regularMarketChangePercent': 3.45,
            },
            'DBS19': {
                'regularMarketPrice': 35.0,
                'regularMarketPreviousClose': 36.0,
                'regularMarketVolume': 2000000,
                'averageVolume': 1500000,
                'shortName': 'DBS Group Holdings',
                'currency': 'SGD',
                'regularMarketChangePercent': -2.78,
            },
            'JPMUS19': {
                'regularMarketPrice': 180.0,
                'regularMarketPreviousClose': 178.0,
                'regularMarketVolume': 8000000,
                'averageVolume': 2000000,
                'shortName': 'JPMorgan Chase',
                'currency': 'USD',
                'regularMarketChangePercent': 1.12,
            },
        }

    # Test 1: Service initialization
    def test_service_initialization(self, service):
        """Test that service initializes with correct defaults"""
        assert isinstance(service, RankingsService), f"Expected RankingsService, got {type(service)}"
        assert service.cache_ttl_seconds == 300
        assert service._cache == {}
        assert service._cache_timestamp is None

    # Test 2: Fetch single ticker data
    @pytest.mark.asyncio
    async def test_fetch_single_ticker(self, service, mock_ticker_data):
        """Test fetching data for a single ticker"""
        with patch('yfinance.Ticker') as mock_yf:
            mock_ticker = Mock()
            mock_ticker.info = mock_ticker_data['NVDA19']
            mock_yf.return_value = mock_ticker

            result = await service._fetch_ticker_data('NVDA19')

            assert result is not None
            assert result['ticker'] == 'NVDA19'
            assert result['price'] == 150.0
            assert result['price_change_pct'] == 3.45
            assert result['currency'] == 'USD'
            assert result['volume_ratio'] == pytest.approx(1.67, rel=0.01)

    # Test 3: Fetch multiple tickers in parallel
    @pytest.mark.asyncio
    async def test_fetch_all_tickers_parallel(self, service, mock_ticker_data):
        """Test parallel fetching of all tickers"""
        with patch.object(service, '_fetch_ticker_data') as mock_fetch:
            # Simulate successful fetches
            mock_fetch.side_effect = [
                {'ticker': 'NVDA19', 'price_change_pct': 3.45, 'currency': 'USD', 'volume_ratio': 1.67},
                {'ticker': 'DBS19', 'price_change_pct': -2.78, 'currency': 'SGD', 'volume_ratio': 1.33},
                {'ticker': 'JPMUS19', 'price_change_pct': 1.12, 'currency': 'USD', 'volume_ratio': 4.0},
            ]

            tickers = ['NVDA19', 'DBS19', 'JPMUS19']
            results = await service._fetch_all_tickers(tickers)

            assert len(results) == 3
            assert mock_fetch.call_count == 3

    # Test 4: Calculate top gainers
    def test_calculate_top_gainers(self, service):
        """Test ranking by highest price change percentage"""
        ticker_data = [
            {'ticker': 'NVDA19', 'company_name': 'NVIDIA', 'price': 150.0,
             'price_change_pct': 5.5, 'currency': 'USD', 'volume_ratio': 1.2},
            {'ticker': 'DBS19', 'company_name': 'DBS', 'price': 35.0,
             'price_change_pct': 2.3, 'currency': 'SGD', 'volume_ratio': 1.0},
            {'ticker': 'JPMUS19', 'company_name': 'JPMorgan', 'price': 180.0,
             'price_change_pct': -1.2, 'currency': 'USD', 'volume_ratio': 0.8},
        ]

        gainers = service._calculate_top_gainers(ticker_data, limit=2)

        assert len(gainers) == 2
        assert gainers[0].ticker == 'NVDA19'
        assert gainers[0].price_change_pct == 5.5
        assert gainers[1].ticker == 'DBS19'
        assert gainers[1].price_change_pct == 2.3

    # Test 5: Calculate top losers
    def test_calculate_top_losers(self, service):
        """Test ranking by lowest price change percentage"""
        ticker_data = [
            {'ticker': 'NVDA19', 'company_name': 'NVIDIA', 'price': 150.0,
             'price_change_pct': 2.5, 'currency': 'USD', 'volume_ratio': 1.2},
            {'ticker': 'DBS19', 'company_name': 'DBS', 'price': 35.0,
             'price_change_pct': -3.8, 'currency': 'SGD', 'volume_ratio': 1.0},
            {'ticker': 'JPMUS19', 'company_name': 'JPMorgan', 'price': 180.0,
             'price_change_pct': -5.2, 'currency': 'USD', 'volume_ratio': 0.8},
        ]

        losers = service._calculate_top_losers(ticker_data, limit=2)

        assert len(losers) == 2
        assert losers[0].ticker == 'JPMUS19'
        assert losers[0].price_change_pct == -5.2
        assert losers[1].ticker == 'DBS19'
        assert losers[1].price_change_pct == -3.8

    # Test 6: Calculate volume surge
    def test_calculate_volume_surge(self, service):
        """Test ranking by highest volume ratio"""
        ticker_data = [
            {'ticker': 'NVDA19', 'company_name': 'NVIDIA', 'price': 150.0,
             'price_change_pct': 2.5, 'currency': 'USD', 'volume_ratio': 1.5},
            {'ticker': 'DBS19', 'company_name': 'DBS', 'price': 35.0,
             'price_change_pct': -1.2, 'currency': 'SGD', 'volume_ratio': 3.8},
            {'ticker': 'JPMUS19', 'company_name': 'JPMorgan', 'price': 180.0,
             'price_change_pct': 0.5, 'currency': 'USD', 'volume_ratio': 2.2},
        ]

        volume_surge = service._calculate_volume_surge(ticker_data, limit=2)

        assert len(volume_surge) == 2
        assert volume_surge[0].ticker == 'DBS19'
        assert volume_surge[0].volume_ratio == 3.8
        assert volume_surge[1].ticker == 'JPMUS19'

    # Test 7: Calculate trending (momentum score)
    def test_calculate_trending(self, service):
        """Test ranking by combined momentum score"""
        ticker_data = [
            {'ticker': 'NVDA19', 'company_name': 'NVIDIA', 'price': 150.0,
             'price_change_pct': 5.0, 'currency': 'USD', 'volume_ratio': 2.0},  # Score: 5.0 + 2.0 = 7.0
            {'ticker': 'DBS19', 'company_name': 'DBS', 'price': 35.0,
             'price_change_pct': 3.0, 'currency': 'SGD', 'volume_ratio': 1.5},  # Score: 3.0 + 1.5 = 4.5
            {'ticker': 'JPMUS19', 'company_name': 'JPMorgan', 'price': 180.0,
             'price_change_pct': 2.0, 'currency': 'USD', 'volume_ratio': 4.0},  # Score: 2.0 + 4.0 = 6.0
        ]

        trending = service._calculate_trending(ticker_data, limit=2)

        assert len(trending) == 2
        assert trending[0].ticker == 'NVDA19'  # Highest momentum
        assert trending[1].ticker == 'JPMUS19'

    # Test 8: Cache behavior - fresh data
    @pytest.mark.asyncio
    async def test_cache_fresh_data(self, service):
        """Test that cache returns fresh data without refetching"""
        # Populate cache
        service._cache = {
            'top_gainers': [
                RankingItem(ticker='NVDA19', company_name='NVIDIA', price=150.0,
                           price_change_pct=5.0, currency='USD', volume_ratio=2.0)
            ]
        }
        service._cache_timestamp = datetime.now()

        with patch.object(service, '_fetch_all_tickers') as mock_fetch:
            result = await service.get_rankings('top_gainers')

            # Should not fetch, use cache
            mock_fetch.assert_not_called()
            assert len(result) == 1
            assert result[0].ticker == 'NVDA19'

    # Test 9: Cache behavior - stale data
    @pytest.mark.asyncio
    async def test_cache_stale_data(self, service):
        """Test that stale cache triggers refetch"""
        # Populate cache with old timestamp
        service._cache = {
            'top_gainers': [
                RankingItem(ticker='OLD', company_name='Old Data', price=100.0,
                           price_change_pct=1.0, currency='USD', volume_ratio=1.0)
            ]
        }
        service._cache_timestamp = datetime.now() - timedelta(seconds=400)  # Stale

        with patch.object(service, '_fetch_all_tickers') as mock_fetch:
            mock_fetch.return_value = [
                {'ticker': 'NVDA19', 'company_name': 'NVIDIA', 'price': 150.0,
                 'price_change_pct': 5.0, 'currency': 'USD', 'volume_ratio': 2.0}
            ]

            result = await service.get_rankings('top_gainers')

            # Should fetch new data
            mock_fetch.assert_called_once()

    # Test 10: Error handling - network failure
    @pytest.mark.asyncio
    async def test_network_failure_handling(self, service):
        """Test graceful handling of network failures"""
        with patch('yfinance.Ticker') as mock_yf:
            mock_yf.side_effect = Exception("Network error")

            result = await service._fetch_ticker_data('NVDA19')

            # Should return None on error
            assert result is None

    # Test 11: Error handling - invalid ticker
    @pytest.mark.asyncio
    async def test_invalid_ticker_handling(self, service):
        """Test handling of invalid ticker symbols"""
        with patch('yfinance.Ticker') as mock_yf:
            mock_ticker = Mock()
            mock_ticker.info = {}  # Empty info
            mock_yf.return_value = mock_ticker

            result = await service._fetch_ticker_data('INVALID')

            assert result is None

    # Test 12: Error handling - missing data fields
    @pytest.mark.asyncio
    async def test_missing_data_fields(self, service):
        """Test handling of incomplete ticker data"""
        with patch('yfinance.Ticker') as mock_yf:
            mock_ticker = Mock()
            mock_ticker.info = {
                'regularMarketPrice': 150.0,
                # Missing regularMarketPreviousClose and volume data
            }
            mock_yf.return_value = mock_ticker

            result = await service._fetch_ticker_data('NVDA19')

            # Should handle missing fields gracefully
            assert result is None or result.get('price_change_pct') is not None

    # Test 13: Get rankings with different categories
    @pytest.mark.asyncio
    async def test_get_rankings_all_categories(self, service):
        """Test fetching rankings for all category types"""
        categories = ['top_gainers', 'top_losers', 'volume_surge', 'trending']

        with patch.object(service, '_fetch_all_tickers') as mock_fetch:
            mock_fetch.return_value = [
                {'ticker': 'NVDA19', 'company_name': 'NVIDIA', 'price': 150.0,
                 'price_change_pct': 5.0, 'currency': 'USD', 'volume_ratio': 2.0},
                {'ticker': 'DBS19', 'company_name': 'DBS', 'price': 35.0,
                 'price_change_pct': -3.0, 'currency': 'SGD', 'volume_ratio': 1.5},
            ]

            for category in categories:
                result = await service.get_rankings(category)
                assert isinstance(result, list)
                assert len(result) > 0
                assert isinstance(result[0], RankingItem)

    # Test 14: Limit parameter enforcement
    @pytest.mark.asyncio
    async def test_limit_parameter(self, service):
        """Test that limit parameter correctly restricts results"""
        # Create mix of positive and negative price changes
        ticker_data = [
            {'ticker': f'TICK{i}', 'company_name': f'Company {i}', 'price': 100.0,
             'price_change_pct': float(i - 10), 'currency': 'USD', 'volume_ratio': 1.0}  # -10 to +9
            for i in range(20)
        ]

        with patch.object(service, '_fetch_all_tickers', return_value=ticker_data):
            result = await service.get_rankings('top_gainers', limit=5)
            assert len(result) == 5

            result = await service.get_rankings('top_losers', limit=10)
            assert len(result) == 10

    # Test 15: RankingItem model validation
    def test_ranking_item_model(self):
        """Test RankingItem pydantic model validation"""
        # Valid item
        item = RankingItem(
            ticker='NVDA19',
            company_name='NVIDIA Corp',
            price=150.50,
            price_change_pct=3.45,
            currency='USD',
            volume_ratio=1.67
        )
        assert item.ticker == 'NVDA19'
        assert item.price == 150.50
        assert item.currency == 'USD'

        # Invalid item - missing required fields
        with pytest.raises(Exception):  # Pydantic ValidationError
            RankingItem(ticker='NVDA19')

    # Test 16: Concurrent requests handling
    @pytest.mark.asyncio
    async def test_concurrent_requests(self, service):
        """Test that service handles concurrent requests properly"""
        with patch.object(service, '_fetch_all_tickers') as mock_fetch:
            # Provide data that satisfies all categories
            mock_fetch.return_value = [
                {'ticker': 'NVDA19', 'company_name': 'NVIDIA', 'price': 150.0,
                 'price_change_pct': 5.0, 'currency': 'USD', 'volume_ratio': 2.0},  # Gainer + volume surge
                {'ticker': 'DBS19', 'company_name': 'DBS', 'price': 35.0,
                 'price_change_pct': -3.0, 'currency': 'SGD', 'volume_ratio': 1.8},  # Loser + volume surge
                {'ticker': 'JPMUS19', 'company_name': 'JPMorgan', 'price': 180.0,
                 'price_change_pct': 2.0, 'currency': 'USD', 'volume_ratio': 1.6},  # Gainer + volume surge
            ]

            # Make 3 concurrent requests
            tasks = [
                service.get_rankings('top_gainers'),
                service.get_rankings('top_losers'),
                service.get_rankings('volume_surge'),
            ]

            results = await asyncio.gather(*tasks)

            # All should succeed
            assert len(results) == 3
            for result in results:
                assert len(result) > 0

    # Test 17: Empty ticker list handling
    @pytest.mark.asyncio
    async def test_empty_ticker_list(self, service):
        """Test handling of empty ticker list"""
        with patch.object(service, '_fetch_all_tickers', return_value=[]):
            result = await service.get_rankings('top_gainers')
            assert result == []

    # Test 18: Performance - parallel fetch timing
    @pytest.mark.asyncio
    async def test_parallel_fetch_performance(self, service):
        """Test that parallel fetching is faster than sequential"""
        import time

        async def mock_slow_fetch(ticker):
            await asyncio.sleep(0.1)  # Simulate slow network
            return {'ticker': ticker, 'company_name': 'Test', 'price': 100.0,
                   'price_change_pct': 1.0, 'currency': 'USD', 'volume_ratio': 1.0}

        with patch.object(service, '_fetch_ticker_data', side_effect=mock_slow_fetch):
            start = time.time()
            tickers = [f'TICK{i}' for i in range(5)]
            await service._fetch_all_tickers(tickers)
            duration = time.time() - start

            # 5 tickers @ 0.1s each = 0.5s sequential, but ~0.1s parallel
            assert duration < 0.3  # Should be much faster than 0.5s


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--asyncio-mode=auto'])
