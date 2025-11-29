# -*- coding: utf-8 -*-
"""
Tests for Chart Generation

Tests the ChartGenerator component with real data.
Marked as integration tests since they require external API calls.
"""

import os
import base64
import pytest
from unittest.mock import Mock, patch
import pandas as pd
import numpy as np


class TestChartGeneration:
    """Tests for chart generation functionality"""

    @pytest.fixture
    def chart_generator(self):
        """Create ChartGenerator instance"""
        from src.formatters.chart_generator import ChartGenerator
        return ChartGenerator()

    @pytest.fixture
    def mock_ticker_data(self):
        """Create mock ticker data for testing"""
        dates = pd.date_range(start='2024-01-01', periods=100, freq='D')
        prices = 100 + np.cumsum(np.random.randn(100) * 2)

        history = pd.DataFrame({
            'Open': prices * 0.99,
            'High': prices * 1.02,
            'Low': prices * 0.98,
            'Close': prices,
            'Volume': np.random.randint(1000000, 10000000, 100)
        }, index=dates)

        return {
            'history': history,
            'company_name': 'Test Company',
            'close': float(prices[-1]),
            'symbol': 'TEST'
        }

    @pytest.fixture
    def mock_indicators(self):
        """Create mock technical indicators"""
        return {
            'rsi': 55.0,
            'macd': 2.5,
            'macd_signal': 2.0,
            'sma_20': 150.0,
            'sma_50': 145.0,
            'ema_12': 152.0,
            'ema_26': 148.0,
            'bb_upper': 160.0,
            'bb_middle': 150.0,
            'bb_lower': 140.0
        }

    def test_generate_chart_returns_base64(self, chart_generator, mock_ticker_data, mock_indicators):
        """Test that generate_chart returns valid base64 string"""
        chart_base64 = chart_generator.generate_chart(
            ticker_data=mock_ticker_data,
            indicators=mock_indicators,
            ticker_symbol='TEST',
            days=90
        )

        assert isinstance(chart_base64, str), f"Expected str, got {type(chart_base64)}"
        assert len(chart_base64) > 0, "Chart base64 is empty"

    def test_generate_chart_is_valid_png(self, chart_generator, mock_ticker_data, mock_indicators):
        """Test that generated chart is valid PNG format"""
        chart_base64 = chart_generator.generate_chart(
            ticker_data=mock_ticker_data,
            indicators=mock_indicators,
            ticker_symbol='TEST',
            days=90
        )

        # Decode base64
        decoded = base64.b64decode(chart_base64)
        assert len(decoded) > 0, "Decoded chart is empty"

        # Check PNG magic bytes
        png_header = b'\x89PNG\r\n\x1a\n'
        assert decoded[:8] == png_header, "Chart is not valid PNG format"

    def test_save_chart_creates_file(self, chart_generator, mock_ticker_data, mock_indicators, tmp_path):
        """Test that save_chart creates a file"""
        output_path = tmp_path / "test_chart.png"

        chart_generator.save_chart(
            ticker_data=mock_ticker_data,
            indicators=mock_indicators,
            ticker_symbol='TEST',
            filepath=str(output_path),
            days=90
        )

        assert output_path.exists(), f"Chart file not created at {output_path}"
        assert output_path.stat().st_size > 0, "Chart file is empty"

    def test_save_chart_is_valid_png(self, chart_generator, mock_ticker_data, mock_indicators, tmp_path):
        """Test that saved chart is valid PNG"""
        output_path = tmp_path / "test_chart.png"

        chart_generator.save_chart(
            ticker_data=mock_ticker_data,
            indicators=mock_indicators,
            ticker_symbol='TEST',
            filepath=str(output_path),
            days=90
        )

        with open(output_path, 'rb') as f:
            content = f.read()

        png_header = b'\x89PNG\r\n\x1a\n'
        assert content[:8] == png_header, "Saved chart is not valid PNG"

    def test_generate_chart_with_minimal_data(self, chart_generator, mock_indicators):
        """Test chart generation with minimal required data"""
        dates = pd.date_range(start='2024-01-01', periods=30, freq='D')
        prices = 100 + np.cumsum(np.random.randn(30) * 2)

        minimal_data = {
            'history': pd.DataFrame({
                'Open': prices * 0.99,
                'High': prices * 1.02,
                'Low': prices * 0.98,
                'Close': prices,
                'Volume': np.random.randint(1000000, 10000000, 30)
            }, index=dates),
            'company_name': 'Minimal Test',
            'close': float(prices[-1]),
            'symbol': 'MIN'
        }

        chart_base64 = chart_generator.generate_chart(
            ticker_data=minimal_data,
            indicators=mock_indicators,
            ticker_symbol='MIN',
            days=30
        )

        assert isinstance(chart_base64, str)
        assert len(chart_base64) > 100  # Reasonable minimum for base64 PNG


@pytest.mark.integration
@pytest.mark.slow
class TestChartGenerationIntegration:
    """Integration tests with real data fetching - require external APIs"""

    @pytest.fixture
    def real_components(self):
        """Initialize real components for integration tests"""
        from src.formatters.chart_generator import ChartGenerator
        from src.data.data_fetcher import DataFetcher
        from src.analysis.technical_analysis import TechnicalAnalyzer

        return {
            'chart_gen': ChartGenerator(),
            'fetcher': DataFetcher(),
            'analyzer': TechnicalAnalyzer()
        }

    def test_full_chart_generation_pipeline(self, real_components):
        """Test complete chart generation with real data"""
        ticker = "AAPL"

        # Fetch real data
        ticker_data = real_components['fetcher'].fetch_ticker_data(ticker)
        assert ticker_data is not None, f"Failed to fetch data for {ticker}"

        info = real_components['fetcher'].get_ticker_info(ticker)
        ticker_data.update(info)

        # Calculate indicators
        hist_data = ticker_data.get('history')
        indicators = real_components['analyzer'].calculate_all_indicators(hist_data)
        assert indicators is not None, "Failed to calculate indicators"

        # Generate chart
        chart_base64 = real_components['chart_gen'].generate_chart(
            ticker_data=ticker_data,
            indicators=indicators,
            ticker_symbol=ticker,
            days=90
        )

        # Validate output
        assert isinstance(chart_base64, str), f"Expected str, got {type(chart_base64)}"
        assert len(chart_base64) > 1000, "Chart seems too small"

        decoded = base64.b64decode(chart_base64)
        assert decoded[:8] == b'\x89PNG\r\n\x1a\n', "Not valid PNG"
