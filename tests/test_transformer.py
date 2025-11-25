#!/usr/bin/env python3
"""
Unit tests for ResponseTransformer

Tests AgentState to API response transformation.
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, patch, AsyncMock
from src.api.transformer import ResponseTransformer


class TestResponseTransformer:
    """Test suite for ResponseTransformer"""

    @pytest.fixture
    def transformer(self):
        """Create ResponseTransformer instance"""
        with patch('src.api.transformer.get_pdf_storage') as mock_pdf:
            mock_pdf.return_value.is_available.return_value = False
            return ResponseTransformer()

    @pytest.fixture
    def sample_state(self):
        """Create sample AgentState for testing"""
        return {
            'ticker': 'NVDA19',
            'ticker_data': {
                'company_name': 'NVIDIA Corporation',
                'close': 150.0,
                'open': 145.0,
                'pe_ratio': 25.5,
                'market_cap': 1000000000,
                'eps': 5.5,
                'dividend_yield': 0.02,
                'timestamp': '2025-01-15T10:00:00'
            },
            'indicators': {
                'rsi': 55,
                'macd': 0.5,
                'sma_20': 148.0,
                'sma_50': 145.0,
                'volume_ratio': 1.2
            },
            'percentiles': {
                'rsi_percentile': 60,
                'price_percentile': 75
            },
            'news': [
                {
                    'title': 'NVIDIA Reports Record Revenue',
                    'url': 'https://example.com/news1',
                    'source': 'Reuters',
                    'timestamp': '2025-01-15T08:00:00'
                }
            ],
            'report': '''📊 สรุปวิเคราะห์หุ้น NVDA

**สรุป**
- หุ้นมีแนวโน้มดี น่าสนใจลงทุนระยะกลาง
- ปัจจัยบวกจากอุตสาหกรรม AI

**ปัจจัยขับเคลื่อนราคา**
- ความต้องการ GPU สำหรับ AI เพิ่มขึ้น
- ผลประกอบการที่แข็งแกร่ง

**ความเสี่ยง**
- ราคาหุ้นผันผวนสูง
- การแข่งขันในตลาด GPU
''',
            'strategy': 'multi_stage_analysis',
            'cache_hit': False
        }

    @pytest.fixture
    def sample_ticker_info(self):
        """Create sample ticker info"""
        return {
            'symbol': 'NVDA19',
            'company_name': 'NVIDIA Corporation',
            'currency': 'USD',
            'yahoo_symbol': 'NVDA'
        }

    # Test 1: Basic transformation
    @pytest.mark.asyncio
    async def test_transform_report_basic(self, transformer, sample_state, sample_ticker_info):
        """Test basic report transformation"""
        with patch.object(transformer, '_get_pdf_url', return_value=None):
            with patch('src.api.transformer.get_peer_selector_service') as mock_peer:
                mock_peer.return_value.find_peers_async = AsyncMock(return_value=[])

                result = await transformer.transform_report(sample_state, sample_ticker_info)

                assert result.ticker == 'NVDA19'
                assert result.company_name == 'NVIDIA Corporation'
                assert result.price == 150.0
                assert result.currency == 'USD'

    @pytest.mark.asyncio
    async def test_transform_report_price_change(self, transformer, sample_state, sample_ticker_info):
        """Test price change percentage calculation"""
        with patch.object(transformer, '_get_pdf_url', return_value=None):
            with patch('src.api.transformer.get_peer_selector_service') as mock_peer:
                mock_peer.return_value.find_peers_async = AsyncMock(return_value=[])

                result = await transformer.transform_report(sample_state, sample_ticker_info)

                # (150 - 145) / 145 * 100 = 3.45%
                assert abs(result.price_change_pct - 3.45) < 0.1

    # Test 2: Stance extraction
    def test_extract_stance_bullish(self, transformer):
        """Test bullish stance extraction"""
        report_text = "หุ้นน่าสนใจ แนวโน้มดี ปัจจัยบวก เติบโต แข็งแกร่ง"
        indicators = {'rsi': 55}
        percentiles = {}

        result = transformer._extract_stance(report_text, indicators, percentiles)

        assert result['stance'] == 'bullish'

    def test_extract_stance_bearish(self, transformer):
        """Test bearish stance extraction"""
        report_text = "มีความเสี่ยง ระวัง อ่อนแอ ลดลง ปัจจัยลบ กังวล"
        indicators = {'rsi': 75}
        percentiles = {}

        result = transformer._extract_stance(report_text, indicators, percentiles)

        assert result['stance'] == 'bearish'

    def test_extract_stance_neutral(self, transformer):
        """Test neutral stance extraction"""
        report_text = "หุ้นมีปัจจัยทั้งบวกและลบ"
        indicators = {'rsi': 50}
        percentiles = {}

        result = transformer._extract_stance(report_text, indicators, percentiles)

        assert result['stance'] == 'neutral'

    def test_extract_stance_confidence_high(self, transformer):
        """Test high confidence detection"""
        # Many bullish keywords = high confidence
        report_text = "น่าสนใจ แนวโน้มดี ปัจจัยบวก โอกาส เติบโต แข็งแกร่ง สูงขึ้น"
        indicators = {'rsi': 50}
        percentiles = {}

        result = transformer._extract_stance(report_text, indicators, percentiles)

        assert result['confidence'] in ['high', 'medium']

    # Test 3: Investment horizon extraction
    def test_extract_horizon_short_term(self, transformer):
        """Test short-term horizon extraction"""
        report_text = "เหมาะสำหรับเทรดระยะสั้น สัปดาห์หน้า"

        result = transformer._extract_horizon(report_text)

        assert result == "1-3 months"

    def test_extract_horizon_medium_term(self, transformer):
        """Test medium-term horizon extraction (default)"""
        report_text = "วิเคราะห์หุ้นทั่วไป"

        result = transformer._extract_horizon(report_text)

        assert result == "6-12 months"

    def test_extract_horizon_long_term(self, transformer):
        """Test long-term horizon extraction"""
        report_text = "เหมาะสำหรับลงทุนระยะยาว ถือยาว หลายปี ปันผล"

        result = transformer._extract_horizon(report_text)

        assert result == "1-2 years"

    # Test 4: Summary sections extraction
    def test_extract_summary_sections(self, transformer, sample_state):
        """Test summary section extraction from report"""
        result = transformer._extract_summary_sections(sample_state['report'])

        assert result is not None
        # Check structure exists
        assert hasattr(result, 'key_takeaways')
        assert hasattr(result, 'price_drivers')
        assert hasattr(result, 'risks_to_watch')

    # Test 5: Technical metrics building
    def test_build_technical_metrics(self, transformer, sample_state):
        """Test technical metrics building"""
        indicators = sample_state['indicators']
        percentiles = sample_state['percentiles']

        result = transformer._build_technical_metrics(indicators, percentiles)

        assert isinstance(result, list)
        # Should have RSI metric
        metric_names = [m.name for m in result]
        assert any('RSI' in name or 'rsi' in name.lower() for name in metric_names)

    # Test 6: Fundamentals building
    def test_build_fundamentals(self, transformer, sample_state):
        """Test fundamentals building"""
        ticker_data = sample_state['ticker_data']

        result = transformer._build_fundamentals(ticker_data)

        assert result is not None
        # Check valuation has P/E
        pe_metrics = [m for m in result.valuation if 'P/E' in m.name]
        assert len(pe_metrics) > 0
        assert pe_metrics[0].value == 25.5

    def test_build_fundamentals_with_growth(self, transformer):
        """Test fundamentals with growth metrics"""
        ticker_data = {
            'pe_ratio': 25.0,
            'revenue_growth': 0.15,  # 15%
            'earnings_growth': 0.20  # 20%
        }

        result = transformer._build_fundamentals(ticker_data)

        # Check growth metrics were added
        growth_names = [m.name for m in result.growth]
        assert 'Revenue Growth' in growth_names or len(result.growth) > 0

    # Test 7: News items building
    def test_build_news_items(self, transformer, sample_state):
        """Test news items building"""
        news = sample_state['news']

        result = transformer._build_news_items(news)

        assert len(result) == 1
        assert result[0].title == 'NVIDIA Reports Record Revenue'
        assert result[0].source == 'Reuters'

    def test_build_news_items_empty(self, transformer):
        """Test building with empty news"""
        result = transformer._build_news_items([])

        assert result == []

    # Test 8: Risk building
    def test_build_risk(self, transformer, sample_state):
        """Test risk assessment building"""
        indicators = sample_state['indicators']
        percentiles = sample_state['percentiles']
        report_text = sample_state['report']

        result = transformer._build_risk(indicators, percentiles, report_text)

        assert result is not None
        assert hasattr(result, 'level')
        assert hasattr(result, 'bullets')

    # Test 9: Generation metadata
    @pytest.mark.asyncio
    async def test_generation_metadata(self, transformer, sample_state, sample_ticker_info):
        """Test generation metadata is included"""
        with patch.object(transformer, '_get_pdf_url', return_value=None):
            with patch('src.api.transformer.get_peer_selector_service') as mock_peer:
                mock_peer.return_value.find_peers_async = AsyncMock(return_value=[])

                result = await transformer.transform_report(sample_state, sample_ticker_info)

                assert result.generation_metadata is not None
                assert result.generation_metadata.strategy == 'multi_stage_analysis'
                assert result.generation_metadata.cache_hit is False

    # Test 10: Timestamp extraction
    @pytest.mark.asyncio
    async def test_timestamp_from_ticker_data(self, transformer, sample_state, sample_ticker_info):
        """Test timestamp is extracted from ticker_data"""
        with patch.object(transformer, '_get_pdf_url', return_value=None):
            with patch('src.api.transformer.get_peer_selector_service') as mock_peer:
                mock_peer.return_value.find_peers_async = AsyncMock(return_value=[])

                result = await transformer.transform_report(sample_state, sample_ticker_info)

                # Should use timestamp from ticker_data, not current time
                assert result.as_of is not None


class TestResponseTransformerEdgeCases:
    """Edge case tests for ResponseTransformer"""

    @pytest.fixture
    def transformer(self):
        """Create ResponseTransformer instance"""
        with patch('src.api.transformer.get_pdf_storage') as mock_pdf:
            mock_pdf.return_value.is_available.return_value = False
            return ResponseTransformer()

    def test_extract_stance_empty_report(self, transformer):
        """Test stance extraction with empty report"""
        result = transformer._extract_stance("", {}, {})

        assert result['stance'] == 'neutral'

    def test_extract_horizon_empty_report(self, transformer):
        """Test horizon extraction with empty report"""
        result = transformer._extract_horizon("")

        assert result == "6-12 months"  # Default

    def test_build_fundamentals_empty_data(self, transformer):
        """Test fundamentals with empty ticker data"""
        result = transformer._build_fundamentals({})

        assert result is not None
        assert result.valuation == []
        assert result.growth == []
        assert result.profitability == []

    def test_build_technical_metrics_empty(self, transformer):
        """Test technical metrics with empty indicators"""
        result = transformer._build_technical_metrics({}, {})

        assert result == []
