# -*- coding: utf-8 -*-
"""
Tests for Multi-Stage Report Generation

Tests the MiniReportGenerator, SynthesisGenerator, and multi-stage workflow.
"""

import pytest
from unittest.mock import Mock, MagicMock
from src.report.mini_report_generator import MiniReportGenerator
from src.report.synthesis_generator import SynthesisGenerator


class MockLLMResponse:
    """Mock LLM response object"""
    def __init__(self, content):
        self.content = content


class TestMiniReportGenerator:
    """Test suite for MiniReportGenerator"""

    @pytest.fixture
    def mock_llm(self):
        """Create a mock LLM"""
        llm = Mock()
        llm.invoke = Mock(return_value=MockLLMResponse("Test mini-report content in Thai"))
        return llm

    @pytest.fixture
    def generator(self, mock_llm):
        """Create MiniReportGenerator with mock LLM"""
        return MiniReportGenerator(mock_llm)

    def test_load_prompt_templates(self, generator):
        """Test that all 6 prompt templates are loaded"""
        assert 'technical' in generator.prompts
        assert 'fundamental' in generator.prompts
        assert 'market_conditions' in generator.prompts
        assert 'news' in generator.prompts
        assert 'comparative' in generator.prompts
        assert 'strategy' in generator.prompts

    def test_generate_technical_mini_report(self, generator, mock_llm):
        """Test technical mini-report generation"""
        indicators = {
            'rsi': 55.71,
            'macd': 0.4579,
            'sma_20': 53.5,
            'current_price': 53.67
        }
        percentiles = {
            'rsi': {'current_value': 55.71, 'percentile': 35.2}
        }

        result = generator.generate_technical_mini_report(indicators, percentiles)

        assert isinstance(result, str)
        assert len(result) > 0
        mock_llm.invoke.assert_called_once()

    def test_generate_fundamental_mini_report(self, generator, mock_llm):
        """Test fundamental mini-report generation"""
        ticker_data = {
            'pe_ratio': 13.73,
            'eps': 3.91,
            'market_cap': 152309366784,
            'sector': 'Financial Services'
        }

        result = generator.generate_fundamental_mini_report(ticker_data)

        assert isinstance(result, str)
        assert len(result) > 0
        mock_llm.invoke.assert_called_once()

    def test_generate_market_conditions_mini_report(self, generator, mock_llm):
        """Test market conditions mini-report generation"""
        indicators = {
            'uncertainty_score': 51.4,
            'atr_percentage': 1.28,
            'vwap_percentage': 20.37,
            'volume_ratio': 1.5
        }
        percentiles = {
            'uncertainty_score': {'percentile': 45.0},
            'atr_percentage': {'percentile': 30.0}
        }

        result = generator.generate_market_conditions_mini_report(indicators, percentiles)

        assert isinstance(result, str)
        assert len(result) > 0
        mock_llm.invoke.assert_called_once()

    def test_generate_news_mini_report(self, generator, mock_llm):
        """Test news & events mini-report generation"""
        news = [
            {'title': 'DBS reports earnings', 'impact_score': 75},
            {'title': 'Banking sector update', 'impact_score': 60}
        ]
        news_summary = {
            'sentiment': 'positive',
            'confidence': 0.85
        }

        result = generator.generate_news_mini_report(news, news_summary)

        assert isinstance(result, str)
        assert len(result) > 0
        mock_llm.invoke.assert_called_once()

    def test_generate_comparative_mini_report(self, generator, mock_llm):
        """Test comparative analysis mini-report generation"""
        comparative_insights = {
            'similar_tickers': [('STEG19', 0.85), ('DBS19', 0.75)],
            'avg_correlation': 0.80,
            'volatility_rank': 3
        }

        result = generator.generate_comparative_mini_report(comparative_insights)

        assert isinstance(result, str)
        assert len(result) > 0
        mock_llm.invoke.assert_called_once()

    def test_generate_strategy_mini_report(self, generator, mock_llm):
        """Test strategy performance mini-report generation"""
        strategy_performance = {
            'total_return': 15.2,
            'sharpe_ratio': 1.2,
            'win_rate': 62.0,
            'max_drawdown': -12.5
        }

        result = generator.generate_strategy_mini_report(strategy_performance)

        assert isinstance(result, str)
        assert len(result) > 0
        mock_llm.invoke.assert_called_once()


class TestSynthesisGenerator:
    """Test suite for SynthesisGenerator"""

    @pytest.fixture
    def mock_llm(self):
        """Create a mock LLM"""
        llm = Mock()
        llm.invoke = Mock(return_value=MockLLMResponse(
            "📖 **เรื่องราวของหุ้นตัวนี้**\n"
            "หุ้นนี้แสดงความแข็งแกร่งทั้งจากมุมมองทางเทคนิคและพื้นฐาน\n\n"
            "💡 **สิ่งที่คุณต้องรู้**\n"
            "การวิเคราะห์ทางเทคนิคแสดงแนวโน้มขาขึ้น...\n\n"
            "🎯 **ควรทำอะไรตอนนี้?**\n"
            "แนะนำ HOLD เนื่องจาก...\n\n"
            "⚠️ **ระวังอะไร?**\n"
            "ความเสี่ยงจากความไม่แน่นอนของตลาด"
        ))
        return llm

    @pytest.fixture
    def generator(self, mock_llm):
        """Create SynthesisGenerator with mock LLM"""
        return SynthesisGenerator(mock_llm)

    def test_load_synthesis_prompt(self, generator):
        """Test that synthesis prompt is loaded"""
        assert generator.synthesis_prompt is not None
        assert len(generator.synthesis_prompt) > 0
        assert '{mini_reports}' in generator.synthesis_prompt

    def test_format_mini_reports(self, generator):
        """Test mini-reports formatting"""
        mini_reports = {
            'technical': 'Technical analysis shows uptrend...',
            'fundamental': 'P/E ratio is attractive...',
            'market_conditions': 'Market is uncertain...',
            'news': 'Recent earnings beat expectations...',
            'comparative': 'Outperforming peers...',
            'strategy': 'Strategy shows positive backtest...'
        }

        formatted = generator._format_mini_reports(mini_reports)

        assert '📈 **Technical Analysis Mini-Report**' in formatted
        assert '💼 **Fundamental Analysis Mini-Report**' in formatted
        assert '🌐 **Market Conditions Mini-Report**' in formatted
        assert '📰 **News & Events Mini-Report**' in formatted
        assert '📊 **Comparative Analysis Mini-Report**' in formatted
        assert '🎯 **Strategy Performance Mini-Report**' in formatted
        assert 'Technical analysis shows uptrend' in formatted

    def test_format_mini_reports_with_missing_data(self, generator):
        """Test mini-reports formatting when some data is missing"""
        mini_reports = {
            'technical': 'Technical analysis content',
            'fundamental': 'Fundamental analysis content',
            # Missing: market_conditions, news, comparative, strategy
        }

        formatted = generator._format_mini_reports(mini_reports)

        assert 'Technical analysis content' in formatted
        assert 'Fundamental analysis content' in formatted
        assert '[ไม่มีข้อมูล / Data not available]' in formatted

    def test_generate_synthesis(self, generator, mock_llm):
        """Test synthesis generation"""
        mini_reports = {
            'technical': 'แนวโน้มขาขึ้นชัดเจน RSI 55.71',
            'fundamental': 'P/E 13.73 ต่ำกว่าค่าเฉลี่ย',
            'market_conditions': 'ความไม่แน่นอน 51.4/100',
            'news': 'ข่าวเชิงบวกจากผลประกอบการ',
            'comparative': 'ดีกว่าค่าเฉลี่ยของกลุ่ม',
            'strategy': 'Sharpe ratio 1.2 ดี'
        }

        result = generator.generate_synthesis(mini_reports)

        assert isinstance(result, str)
        assert len(result) > 0
        assert '📖' in result or '💡' in result or '🎯' in result or '⚠️' in result
        mock_llm.invoke.assert_called_once()

    def test_synthesis_prompt_contains_all_mini_reports(self, generator, mock_llm):
        """Test that synthesis prompt includes all mini-reports"""
        mini_reports = {
            'technical': 'Tech content',
            'fundamental': 'Fund content',
            'market_conditions': 'Market content',
            'news': 'News content',
            'comparative': 'Comp content',
            'strategy': 'Strat content'
        }

        generator.generate_synthesis(mini_reports)

        # Check that the invoke was called with prompt containing all mini-reports
        call_args = mock_llm.invoke.call_args[0][0]
        assert 'Tech content' in call_args
        assert 'Fund content' in call_args
        assert 'Market content' in call_args
        assert 'News content' in call_args
        assert 'Comp content' in call_args
        assert 'Strat content' in call_args


class TestMultiStageIntegration:
    """Integration tests for multi-stage workflow"""

    def test_end_to_end_multistage_flow(self):
        """Test complete multi-stage flow (mock)"""
        # This is a high-level integration test
        # In a real scenario, this would test the full workflow_nodes integration

        # Create mock LLM
        llm = Mock()
        llm.invoke = Mock(return_value=MockLLMResponse("Mock report content"))

        # Create generators
        mini_gen = MiniReportGenerator(llm)
        synth_gen = SynthesisGenerator(llm)

        # Simulate generating mini-reports
        mini_reports = {
            'technical': mini_gen.generate_technical_mini_report({'rsi': 55}, {}),
            'fundamental': mini_gen.generate_fundamental_mini_report({'pe_ratio': 13.73}),
            'market_conditions': mini_gen.generate_market_conditions_mini_report({'uncertainty_score': 51.4}, {}),
            'news': mini_gen.generate_news_mini_report([], {}),
            'comparative': mini_gen.generate_comparative_mini_report({}),
            'strategy': mini_gen.generate_strategy_mini_report({})
        }

        # Simulate synthesis
        final_report = synth_gen.generate_synthesis(mini_reports)

        # Verify
        assert final_report is not None
        assert len(final_report) > 0
        # 6 mini-reports + 1 synthesis = 7 LLM calls
        assert llm.invoke.call_count == 7
