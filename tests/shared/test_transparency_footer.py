# -*- coding: utf-8 -*-
"""
Tests for TransparencyFooter

Tests the data usage footnote generation logic.
"""

import pytest
from src.report.transparency_footer import TransparencyFooter


class TestTransparencyFooter:
    """Test suite for TransparencyFooter"""

    def test_footnote_with_all_data_available(self):
        """Test when all data categories are available"""
        state = {
            'indicators': {
                'rsi': 55.71,
                'macd': 0.4579,
                'sma_20': 53.5,
                'uncertainty_score': 51.4,
                'atr': 0.68,
                'current_price': 53.67,
                'vwap': 44.72,
                'volume': 1234567
            },
            'ticker_data': {
                'pe_ratio': 13.73,
                'eps': 3.91,
                'market_cap': 152309366784,
                'sector': 'Financial Services'
            },
            'percentiles': {
                'rsi': {'current_value': 55.71, 'percentile': 35.2},
                'macd': {'current_value': 0.4579, 'percentile': 22.2}
            },
            'news': [
                {'title': 'DBS reports earnings', 'impact_score': 75},
                {'title': 'Banking sector update', 'impact_score': 60}
            ],
            'comparative_insights': {
                'similar_tickers': [('STEG19', 0.85)],
                'avg_correlation': 0.75
            },
            'strategy_performance': None
        }

        footer = TransparencyFooter()
        result = footer.generate_data_usage_footnote(state, 'single-stage')

        # Check structure
        assert '✅ **Used in Analysis:**' in result
        assert '⚠️ **Not Used' in result
        assert '🔄 **Generation Strategy:**' in result

        # Check data categories
        assert 'Technical Analysis' in result
        assert 'Fundamental Analysis' in result
        assert 'Market Conditions' in result
        assert 'Statistical Context' in result
        assert 'News & Events' in result
        assert 'Comparative Analysis' in result

        # Check strategy performance is marked as not used
        assert 'Strategy Performance' in result
        assert 'ระบบ backtesting ยังไม่เปิดใช้งาน' in result

        # Check strategy indicator
        assert 'Single Stage' in result
        assert 'direct generation' in result

    def test_footnote_with_missing_fundamental_data(self):
        """Test when fundamental data is unavailable"""
        state = {
            'indicators': {'rsi': 55, 'uncertainty_score': 50, 'current_price': 100, 'atr': 2},
            'ticker_data': {},  # No fundamental data
            'percentiles': {'rsi': {'current_value': 55, 'percentile': 50}},
            'news': [],
            'comparative_insights': {},
            'strategy_performance': None
        }

        footer = TransparencyFooter()
        result = footer.generate_data_usage_footnote(state, 'single-stage')

        # Should show fundamental as not used
        assert '⚠️ **Not Used' in result
        assert 'Fundamental Analysis' in result
        assert 'Yahoo Finance ไม่มีข้อมูล fundamental' in result

        # Should show news as not used
        assert 'News & Events' in result
        assert 'ไม่พบข่าวล่าสุด' in result

    def test_footnote_with_high_impact_news(self):
        """Test that high-impact news count is shown"""
        state = {
            'indicators': {'rsi': 55, 'uncertainty_score': 50, 'current_price': 100, 'atr': 2},
            'ticker_data': {'pe_ratio': 15},
            'percentiles': {},
            'news': [
                {'title': 'Major announcement', 'impact_score': 85},
                {'title': 'Earnings beat', 'impact_score': 75},
                {'title': 'Minor news', 'impact_score': 30}  # Below threshold
            ],
            'comparative_insights': {},
            'strategy_performance': None
        }

        footer = TransparencyFooter()
        result = footer.generate_data_usage_footnote(state, 'single-stage')

        # Should show only high-impact news count
        assert 'News & Events (2 ข่าวผลกระทบสูง)' in result

    def test_footnote_multi_stage_strategy(self):
        """Test multi-stage strategy indicator"""
        state = {
            'indicators': {'rsi': 55, 'uncertainty_score': 50, 'current_price': 100, 'atr': 2},
            'ticker_data': {},
            'percentiles': {},
            'news': [],
            'comparative_insights': {},
            'strategy_performance': None
        }

        footer = TransparencyFooter()
        result = footer.generate_data_usage_footnote(state, 'multi-stage')

        # Check multi-stage indicator (space-separated after title() conversion)
        assert 'Multi Stage' in result
        assert '6 mini-reports → synthesis' in result

    def test_footnote_with_strategy_performance(self):
        """Test when strategy performance data is available"""
        state = {
            'indicators': {'rsi': 55, 'uncertainty_score': 50, 'current_price': 100, 'atr': 2},
            'ticker_data': {},
            'percentiles': {},
            'news': [],
            'comparative_insights': {},
            'strategy_performance': {
                'buy_only': {'total_return_pct': 15.2, 'sharpe_ratio': 1.2},
                'sell_only': None
            }
        }

        footer = TransparencyFooter()
        result = footer.generate_data_usage_footnote(state, 'single-stage')

        # Should show strategy performance as used
        assert '✅ **Used in Analysis:**' in result
        assert 'Strategy Performance' in result
        assert 'backtesting results' in result

    def test_footnote_market_cap_formatting(self):
        """Test that market cap is formatted correctly"""
        state = {
            'indicators': {'rsi': 55, 'uncertainty_score': 50, 'current_price': 100, 'atr': 2},
            'ticker_data': {
                'pe_ratio': 28.5,
                'eps': 6.11,
                'market_cap': 3200000000000  # 3.2 trillion
            },
            'percentiles': {},
            'news': [],
            'comparative_insights': {},
            'strategy_performance': None
        }

        footer = TransparencyFooter()
        result = footer.generate_data_usage_footnote(state, 'single-stage')

        # Should show market cap in billions
        assert 'Market Cap $3200.0B' in result or 'Market Cap $3.2e+03B' in result
        assert 'P/E 28.5' in result
        assert 'EPS 6.11' in result


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
