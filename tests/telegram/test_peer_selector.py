#!/usr/bin/env python3
"""
Unit tests for PeerSelectorService

Following TDD methodology - these tests are written BEFORE implementation.
"""

import pytest
import pandas as pd
from unittest.mock import Mock, patch, MagicMock
from src.api.peer_selector import PeerSelectorService, PeerInfo


class TestPeerSelectorService:
    """Test suite for PeerSelectorService"""

    @pytest.fixture
    def service(self):
        """Create PeerSelectorService instance for testing"""
        return PeerSelectorService()

    @pytest.fixture
    def mock_ticker_data(self):
        """Mock historical price data for multiple tickers"""
        # Create simple price data
        dates = pd.date_range('2024-01-01', periods=100, freq='D')

        return {
            'NVDA19': pd.DataFrame({
                'Close': [100 + i * 0.5 for i in range(100)],
                'Volume': [1000000] * 100
            }, index=dates),
            'JPMUS19': pd.DataFrame({
                'Close': [150 + i * 0.3 for i in range(100)],  # Similar trend to NVDA
                'Volume': [2000000] * 100
            }, index=dates),
            'DBS19': pd.DataFrame({
                'Close': [50 - i * 0.2 for i in range(100)],  # Opposite trend
                'Volume': [500000] * 100
            }, index=dates),
        }

    @pytest.fixture
    def mock_correlation_matrix(self):
        """Mock correlation matrix"""
        return pd.DataFrame({
            'NVDA19': [1.0, 0.95, -0.3],
            'JPMUS19': [0.95, 1.0, -0.25],
            'DBS19': [-0.3, -0.25, 1.0]
        }, index=['NVDA19', 'JPMUS19', 'DBS19'])

    # Test 1: Service initialization
    def test_service_initialization(self, service):
        """Test that service initializes correctly"""
        assert service is not None
        assert hasattr(service, '_analyzer')
        assert hasattr(service, '_ticker_map')

    # Test 2: Find peers with correlation matrix
    def test_find_peers_with_matrix(self, service, mock_correlation_matrix):
        """Test finding peers given a correlation matrix"""
        with patch.object(service._analyzer, 'find_similar_tickers') as mock_find:
            mock_find.return_value = [('JPMUS19', 0.95), ('DBS19', -0.3)]

            peers = service.find_peers(
                target_ticker='NVDA19',
                correlation_matrix=mock_correlation_matrix,
                limit=2
            )

            assert len(peers) == 2
            assert peers[0].ticker == 'JPMUS19'
            assert peers[0].correlation == 0.95
            mock_find.assert_called_once()

    # Test 3: Find peers fetches historical data if no matrix provided
    @pytest.mark.asyncio
    async def test_find_peers_fetches_data(self, service, mock_ticker_data):
        """Test that service fetches historical data when no matrix provided"""
        with patch.object(service, '_fetch_historical_data') as mock_fetch:
            mock_fetch.return_value = mock_ticker_data

            with patch.object(service._analyzer, 'calculate_correlation_matrix') as mock_corr:
                mock_corr.return_value = pd.DataFrame()

                with patch.object(service._analyzer, 'find_similar_tickers') as mock_find:
                    mock_find.return_value = []

                    await service.find_peers_async('NVDA19', limit=3)

                    mock_fetch.assert_called_once()
                    mock_corr.assert_called_once()

    # Test 4: Limit parameter enforcement
    def test_limit_parameter(self, service, mock_correlation_matrix):
        """Test that limit parameter restricts number of peers"""
        with patch.object(service._analyzer, 'find_similar_tickers') as mock_find:
            mock_find.return_value = [
                ('JPMUS19', 0.95),
                ('DBS19', -0.3),
                ('SIA19', 0.8)
            ]

            peers = service.find_peers('NVDA19', mock_correlation_matrix, limit=2)

            assert len(peers) <= 2

    # Test 5: PeerInfo model validation
    def test_peer_info_model(self):
        """Test PeerInfo pydantic model"""
        peer = PeerInfo(
            ticker='JPMUS19',
            company_name='JPMorgan Chase',
            correlation=0.95,
            price_change_pct=2.5,
            estimated_upside_pct=5.0,
            stance='bullish',
            valuation_label='fair'
        )

        assert peer.ticker == 'JPMUS19'
        assert peer.correlation == 0.95
        assert peer.price_change_pct == 2.5
        assert peer.stance == 'bullish'

    # Test 6: Handle target ticker not in matrix
    def test_target_ticker_not_found(self, service, mock_correlation_matrix):
        """Test handling when target ticker not in correlation matrix"""
        with patch.object(service._analyzer, 'find_similar_tickers') as mock_find:
            mock_find.return_value = []

            peers = service.find_peers('INVALID', mock_correlation_matrix)

            assert peers == []

    # Test 7: Handle empty correlation matrix
    def test_empty_correlation_matrix(self, service):
        """Test handling of empty correlation matrix"""
        empty_matrix = pd.DataFrame()

        peers = service.find_peers('NVDA19', empty_matrix)

        assert peers == []

    # Test 8: Convert to API Peer model
    def test_convert_to_api_peer(self, service):
        """Test converting PeerInfo to API Peer model"""
        from src.api.models import Peer

        peer_info = PeerInfo(
            ticker='JPMUS19',
            company_name='JPMorgan Chase',
            correlation=0.95,
            price_change_pct=2.5,
            estimated_upside_pct=5.0,
            stance='bullish',
            valuation_label='fair'
        )

        api_peer = service.to_api_peer(peer_info)

        assert isinstance(api_peer, Peer)
        assert api_peer.ticker == 'JPMUS19'
        assert api_peer.company_name == 'JPMorgan Chase'
        assert api_peer.stance == 'bullish'
        assert api_peer.valuation_label == 'fair'

    # Test 9: Fetch historical data for tickers
    @pytest.mark.asyncio
    async def test_fetch_historical_data(self, service):
        """Test fetching historical price data"""
        tickers = ['NVDA19', 'JPMUS19']

        with patch('yfinance.download') as mock_download:
            mock_df = pd.DataFrame({
                'NVDA19': [100, 101, 102],
                'JPMUS19': [150, 151, 152]
            })
            mock_download.return_value = mock_df

            result = await service._fetch_historical_data(tickers, period='3mo')

            assert result is not None
            mock_download.assert_called_once()

    # Test 10: Handle data fetch errors
    @pytest.mark.asyncio
    async def test_fetch_data_error_handling(self, service):
        """Test handling of errors during data fetch"""
        with patch('yfinance.download') as mock_download:
            mock_download.side_effect = Exception("Network error")

            result = await service._fetch_historical_data(['NVDA19'])

            assert result == {}

    # Test 11: Filter out low correlations
    def test_filter_low_correlations(self, service, mock_correlation_matrix):
        """Test filtering peers with very low correlations"""
        with patch.object(service._analyzer, 'find_similar_tickers') as mock_find:
            mock_find.return_value = [
                ('JPMUS19', 0.95),   # High correlation
                ('DBS19', 0.1),      # Low correlation
                ('SIA19', -0.05)     # Very low correlation
            ]

            peers = service.find_peers(
                'NVDA19',
                mock_correlation_matrix,
                limit=5,
                min_correlation=0.3  # Filter threshold
            )

            # Should only include JPMUS19
            assert len(peers) == 1
            assert peers[0].ticker == 'JPMUS19'

    # Test 12: Get company names from ticker service
    def test_get_company_names(self, service):
        """Test retrieving company names for peer tickers"""
        # Just test that it returns a string (actual value depends on ticker_service data)
        company_name = service._get_company_name('JPMUS19')

        assert isinstance(company_name, str)
        assert len(company_name) > 0

    # Test 13: Get current prices for peers
    @pytest.mark.asyncio
    async def test_get_peer_prices(self, service):
        """Test fetching current prices for peer tickers"""
        async def mock_fetch_single(symbol):
            return {
                'price_change_pct': 2.5
            }

        with patch.object(service, '_fetch_single_ticker_data', side_effect=mock_fetch_single):
            result = await service._get_peer_current_data(['JPMUS19'])

            assert 'JPMUS19' in result
            assert result['JPMUS19']['price_change_pct'] == 2.5

    # Test 14: Calculate estimated upside from analyst targets
    def test_calculate_upside_with_target(self, service):
        """Test calculating estimated upside when target price available"""
        mock_info = {
            'regularMarketPrice': 100.0,
            'targetMeanPrice': 120.0  # 20% upside
        }

        upside = service._calculate_upside(mock_info)

        assert upside is not None
        assert upside == 20.0  # (120 - 100) / 100 * 100 = 20%

    def test_calculate_upside_no_target(self, service):
        """Test upside calculation when no target price available"""
        mock_info = {
            'regularMarketPrice': 100.0,
            # No targetMeanPrice
        }

        upside = service._calculate_upside(mock_info)

        assert upside is None

    def test_calculate_upside_downside(self, service):
        """Test negative upside (downside) calculation"""
        mock_info = {
            'regularMarketPrice': 150.0,
            'targetMeanPrice': 120.0  # 20% downside
        }

        upside = service._calculate_upside(mock_info)

        assert upside is not None
        assert upside == -20.0

    # Test 15: Get valuation label from P/E ratio
    def test_valuation_label_cheap(self, service):
        """Test valuation label for cheap stock (low P/E)"""
        mock_info = {
            'trailingPE': 10.0,
            'forwardPE': 8.0
        }

        label = service._get_valuation_label(mock_info)

        assert label == "cheap"

    def test_valuation_label_expensive(self, service):
        """Test valuation label for expensive stock (high P/E)"""
        mock_info = {
            'trailingPE': 50.0,
            'forwardPE': 45.0
        }

        label = service._get_valuation_label(mock_info)

        assert label == "expensive"

    def test_valuation_label_fair(self, service):
        """Test valuation label for fair-valued stock (moderate P/E)"""
        mock_info = {
            'trailingPE': 20.0,  # Around market average
            'forwardPE': 18.0
        }

        label = service._get_valuation_label(mock_info)

        assert label == "fair"

    def test_valuation_label_no_pe(self, service):
        """Test valuation label when P/E not available defaults to fair"""
        mock_info = {
            # No PE ratios
        }

        label = service._get_valuation_label(mock_info)

        assert label == "fair"

    # Test 16: Full peer data fetch includes upside and valuation
    @pytest.mark.asyncio
    async def test_fetch_single_ticker_includes_upside_valuation(self, service):
        """Test that single ticker fetch includes upside and valuation"""
        mock_info = {
            'regularMarketPrice': 100.0,
            'regularMarketPreviousClose': 98.0,
            'targetMeanPrice': 115.0,
            'trailingPE': 15.0,
            'forwardPE': 12.0
        }

        with patch('yfinance.Ticker') as mock_yf:
            mock_ticker = MagicMock()
            mock_ticker.info = mock_info
            mock_yf.return_value = mock_ticker

            result = await service._fetch_single_ticker_data('NVDA19')

            assert result is not None
            assert 'price_change_pct' in result
            assert 'estimated_upside_pct' in result
            assert 'valuation_label' in result
            assert result['estimated_upside_pct'] == 15.0
            assert result['valuation_label'] == "cheap"


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--asyncio-mode=auto'])
