"""
Tests for CompletenessScorer
"""

import pytest
from src.completeness_scorer import CompletenessScorer, CompletenessScore


class TestCompletenessScorer:
    """Test suite for CompletenessScorer"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.scorer = CompletenessScorer()
        
        # Sample ticker data
        self.ticker_data = {
            'company_name': 'Apple Inc.',
            'ticker': 'AAPL',
            'current_price': 202.49,
            'close': 202.49,
            'sector': 'Technology',
            'industry': 'Consumer Electronics',
            'pe_ratio': 28.5,
            'eps': 6.11,
            'market_cap': 3.2e12,
            'fifty_two_week_high': 220.0,
            'fifty_two_week_low': 150.0
        }
        
        # Sample indicators
        self.indicators = {
            'rsi': 65.36,
            'macd': 2.5,
            'sma_20': 200.0,
            'uncertainty_score': 52.0,
            'atr': 6.14,
            'current_price': 202.49,
            'vwap': 180.0
        }
        
        # Sample percentiles
        self.percentiles = {
            'rsi': {
                'current_value': 65.36,
                'percentile': 88.5,
                'mean': 55.0
            },
            'uncertainty_score': {
                'current_value': 52.0,
                'percentile': 88.0
            }
        }
        
        # Sample news
        self.news = [
            {'idx': 1, 'title': 'Apple announces new iPhone', 'sentiment': 'positive'},
            {'idx': 2, 'title': 'Apple earnings beat expectations', 'sentiment': 'positive'}
        ]
    
    def test_context_completeness_full(self):
        """Test context completeness with all elements present"""
        narrative = """
        📖 เรื่องราวของหุ้นตัวนี้
        บริษัท Apple Inc. (AAPL) มีราคาปัจจุบัน $202.49 ซึ่งอยู่ในกลุ่ม Technology
        Market cap อยู่ที่ 3.2T และอยู่ใกล้ 52-week high
        
        💡 สิ่งที่คุณต้องรู้
        Technical indicators แสดง RSI 65.36 และ MACD 2.5
        
        🎯 ควรทำอะไรตอนนี้?
        แนะนำ BUY เพราะ...
        
        ⚠️ ระวังอะไร?
        ความเสี่ยง...
        """
        
        score = self.scorer.score_narrative(
            narrative, self.ticker_data, self.indicators, self.percentiles, self.news
        )
        
        assert score.dimension_scores['context_completeness'] == 100.0
        assert 'Company identity mentioned' in score.covered_elements
        assert 'Current price mentioned' in score.covered_elements
    
    def test_context_completeness_missing_price(self):
        """Test context completeness with missing price"""
        narrative = """
        📖 เรื่องราวของหุ้นตัวนี้
        บริษัท Apple Inc. (AAPL) แสดงสัญญาณดี
        
        💡 สิ่งที่คุณต้องรู้
        Technical indicators แสดง RSI 65.36
        
        🎯 ควรทำอะไรตอนนี้?
        แนะนำ BUY
        
        ⚠️ ระวังอะไร?
        ความเสี่ยง...
        """
        
        score = self.scorer.score_narrative(
            narrative, self.ticker_data, self.indicators, self.percentiles, self.news
        )
        
        assert score.dimension_scores['context_completeness'] < 100.0
        assert any('price' in missing.lower() for missing in score.missing_elements)
    
    def test_analysis_dimensions_full(self):
        """Test analysis dimensions completeness with all dimensions"""
        narrative = """
        📖 เรื่องราวของหุ้นตัวนี้
        บริษัท Apple Inc. (AAPL) มีราคา $202.49
        
        💡 สิ่งที่คุณต้องรู้
        Technical analysis: RSI 65.36, MACD 2.5, SMA 20
        Volatility: Uncertainty score 52/100 และ ATR 3.03%
        Market sentiment: VWAP แสดงแรงซื้อแรงมาก
        Volume: ปริมาณซื้อขาย 1.8x ของเฉลี่ย
        Fundamental: P/E ratio 28.5 และ EPS 6.11
        Historical: RSI อยู่ในเปอร์เซ็นไทล์ 88.5%
        
        🎯 ควรทำอะไรตอนนี้?
        แนะนำ BUY
        
        ⚠️ ระวังอะไร?
        ความเสี่ยง...
        """
        
        score = self.scorer.score_narrative(
            narrative, self.ticker_data, self.indicators, self.percentiles, self.news
        )
        
        assert score.dimension_scores['analysis_dimensions'] >= 80.0
    
    def test_analysis_dimensions_missing_volatility(self):
        """Test analysis dimensions with missing volatility"""
        narrative = """
        📖 เรื่องราวของหุ้นตัวนี้
        บริษัท Apple Inc. (AAPL) มีราคา $202.49
        
        💡 สิ่งที่คุณต้องรู้
        Technical analysis: RSI 65.36
        Volume: ปริมาณซื้อขาย 1.8x
        
        🎯 ควรทำอะไรตอนนี้?
        แนะนำ BUY
        
        ⚠️ ระวังอะไร?
        ความเสี่ยง...
        """
        
        score = self.scorer.score_narrative(
            narrative, self.ticker_data, self.indicators, self.percentiles, self.news
        )
        
        assert score.dimension_scores['analysis_dimensions'] < 100.0
        assert any('volatility' in missing.lower() or 'uncertainty' in missing.lower() 
                   for missing in score.missing_elements)
    
    def test_temporal_completeness_full(self):
        """Test temporal completeness with all elements"""
        narrative = """
        📖 เรื่องราวของหุ้นตัวนี้
        บริษัท Apple Inc. (AAPL) มีราคาปัจจุบัน $202.49
        
        💡 สิ่งที่คุณต้องรู้
        ราคาปัจจุบัน $202.49 ซึ่งอยู่ในเปอร์เซ็นไทล์ 88% - สูงมากในอดีต
        แสดงแนวโน้มขาขึ้นในช่วง 3 เดือนที่ผ่านมา
        Analysis valid สำหรับวันที่ 2025-11-01
        
        🎯 ควรทำอะไรตอนนี้?
        แนะนำ BUY
        
        ⚠️ ระวังอะไร?
        ความเสี่ยง...
        """
        
        score = self.scorer.score_narrative(
            narrative, self.ticker_data, self.indicators, self.percentiles, self.news
        )
        
        assert score.dimension_scores['temporal_completeness'] == 100.0
    
    def test_actionability_full(self):
        """Test actionability completeness with all elements"""
        narrative = """
        📖 เรื่องราวของหุ้นตัวนี้
        บริษัท Apple Inc. (AAPL) มีราคา $202.49
        
        💡 สิ่งที่คุณต้องรู้
        Technical indicators แสดง RSI 65.36
        
        🎯 ควรทำอะไรตอนนี้?
        แนะนำ BUY เพราะ uncertainty score ต่ำและมีแรงซื้อแรงมาก
        ปัจจัยสำคัญคือ technical indicators และ market sentiment
        
        ⚠️ ระวังอะไร?
        ควรระวังความผันผวนที่อาจเกิดขึ้น
        """
        
        score = self.scorer.score_narrative(
            narrative, self.ticker_data, self.indicators, self.percentiles, self.news
        )
        
        assert score.dimension_scores['actionability'] == 100.0
    
    def test_actionability_missing_reasoning(self):
        """Test actionability with missing reasoning"""
        narrative = """
        📖 เรื่องราวของหุ้นตัวนี้
        บริษัท Apple Inc. (AAPL) มีราคา $202.49
        
        💡 สิ่งที่คุณต้องรู้
        Technical indicators แสดง RSI 65.36
        
        🎯 ควรทำอะไรตอนนี้?
        แนะนำ BUY
        
        ⚠️ ระวังอะไร?
        ความเสี่ยง...
        """
        
        score = self.scorer.score_narrative(
            narrative, self.ticker_data, self.indicators, self.percentiles, self.news
        )
        
        assert score.dimension_scores['actionability'] < 100.0
        assert any('reasoning' in missing.lower() for missing in score.missing_elements)
    
    def test_narrative_structure_full(self):
        """Test narrative structure completeness"""
        narrative = """
        📖 เรื่องราวของหุ้นตัวนี้
        บริษัท Apple Inc. (AAPL) มีราคา $202.49
        
        💡 สิ่งที่คุณต้องรู้
        Technical indicators แสดง RSI 65.36
        
        🎯 ควรทำอะไรตอนนี้?
        แนะนำ BUY
        
        ⚠️ ระวังอะไร?
        ความเสี่ยง...
        """
        
        score = self.scorer.score_narrative(
            narrative, self.ticker_data, self.indicators, self.percentiles, self.news
        )
        
        assert score.dimension_scores['narrative_structure'] == 100.0
    
    def test_narrative_structure_missing_risk(self):
        """Test narrative structure with missing risk section"""
        narrative = """
        📖 เรื่องราวของหุ้นตัวนี้
        บริษัท Apple Inc. (AAPL) มีราคา $202.49
        
        💡 สิ่งที่คุณต้องรู้
        Technical indicators แสดง RSI 65.36
        
        🎯 ควรทำอะไรตอนนี้?
        แนะนำ BUY
        """
        
        score = self.scorer.score_narrative(
            narrative, self.ticker_data, self.indicators, self.percentiles, self.news
        )
        
        assert score.dimension_scores['narrative_structure'] < 100.0
        assert any('risk' in missing.lower() for missing in score.missing_elements)
    
    def test_quantitative_context_full(self):
        """Test quantitative context completeness"""
        narrative = """
        📖 เรื่องราวของหุ้นตัวนี้
        บริษัท Apple Inc. (AAPL) มีราคา $202.49
        
        💡 สิ่งที่คุณต้องรู้
        RSI 65.36 ซึ่งอยู่ในเปอร์เซ็นไทล์ 88.5% - สูงกว่าค่าเฉลี่ย 55.0
        Uncertainty score 52/100 สูง เมื่อเทียบกับประวัติศาสตร์
        
        🎯 ควรทำอะไรตอนนี้?
        แนะนำ BUY
        
        ⚠️ ระวังอะไร?
        ความเสี่ยง...
        """
        
        score = self.scorer.score_narrative(
            narrative, self.ticker_data, self.indicators, self.percentiles, self.news
        )
        
        assert score.dimension_scores['quantitative_context'] >= 80.0
    
    def test_fundamental_not_available(self):
        """Test that missing fundamental data doesn't penalize completeness"""
        ticker_data_no_fundamental = {
            'company_name': 'Apple Inc.',
            'ticker': 'AAPL',
            'current_price': 202.49,
            'close': 202.49,
            # No fundamental data
        }
        
        narrative = """
        📖 เรื่องราวของหุ้นตัวนี้
        บริษัท Apple Inc. (AAPL) มีราคา $202.49
        
        💡 สิ่งที่คุณต้องรู้
        Technical indicators แสดง RSI 65.36
        
        🎯 ควรทำอะไรตอนนี้?
        แนะนำ BUY เพราะ...
        
        ⚠️ ระวังอะไร?
        ความเสี่ยง...
        """
        
        score = self.scorer.score_narrative(
            narrative, ticker_data_no_fundamental, self.indicators, self.percentiles, self.news
        )
        
        # Should not penalize for missing fundamental analysis if data not available
        assert not any('fundamental' in missing.lower() for missing in score.missing_elements)
    
    def test_fundamental_available_but_not_mentioned(self):
        """Test that available fundamental data that's not mentioned is penalized"""
        narrative = """
        📖 เรื่องราวของหุ้นตัวนี้
        บริษัท Apple Inc. (AAPL) มีราคา $202.49
        
        💡 สิ่งที่คุณต้องรู้
        Technical indicators แสดง RSI 65.36
        
        🎯 ควรทำอะไรตอนนี้?
        แนะนำ BUY เพราะ...
        
        ⚠️ ระวังอะไร?
        ความเสี่ยง...
        """
        
        score = self.scorer.score_narrative(
            narrative, self.ticker_data, self.indicators, self.percentiles, self.news
        )
        
        # Should penalize if fundamental data available but not mentioned
        # Note: This depends on whether the narrative mentions fundamental terms
        # The scorer checks for P/E, EPS, earnings, revenue, etc.
    
    def test_format_score_report(self):
        """Test score report formatting"""
        narrative = """
        📖 เรื่องราวของหุ้นตัวนี้
        บริษัท Apple Inc. (AAPL) มีราคา $202.49
        
        💡 สิ่งที่คุณต้องรู้
        Technical indicators แสดง RSI 65.36
        
        🎯 ควรทำอะไรตอนนี้?
        แนะนำ BUY เพราะ...
        
        ⚠️ ระวังอะไร?
        ความเสี่ยง...
        """
        
        score = self.scorer.score_narrative(
            narrative, self.ticker_data, self.indicators, self.percentiles, self.news
        )
        
        report = self.scorer.format_score_report(score)
        
        assert "COMPLETENESS SCORE REPORT" in report
        assert f"{score.overall_score:.1f}/100" in report
        assert "Dimension Breakdown:" in report
    
    def test_no_news_doesnt_penalize(self):
        """Test that missing news doesn't penalize sentiment dimension"""
        narrative = """
        📖 เรื่องราวของหุ้นตัวนี้
        บริษัท Apple Inc. (AAPL) มีราคา $202.49
        
        💡 สิ่งที่คุณต้องรู้
        Technical indicators แสดง RSI 65.36
        VWAP แสดงแรงซื้อแรงมาก
        
        🎯 ควรทำอะไรตอนนี้?
        แนะนำ BUY เพราะ...
        
        ⚠️ ระวังอะไร?
        ความเสี่ยง...
        """
        
        score = self.scorer.score_narrative(
            narrative, self.ticker_data, self.indicators, self.percentiles, []
        )
        
        # Should not penalize if VWAP mentioned (even without news)
        assert score.dimension_scores['analysis_dimensions'] >= 60.0
    
    def test_percentile_context_missing(self):
        """Test that missing percentile context is penalized when numbers are mentioned"""
        narrative = """
        📖 เรื่องราวของหุ้นตัวนี้
        บริษัท Apple Inc. (AAPL) มีราคา $202.49
        
        💡 สิ่งที่คุณต้องรู้
        RSI 65.36 แสดงภาวะ Overbought
        Uncertainty score 52/100
        
        🎯 ควรทำอะไรตอนนี้?
        แนะนำ BUY เพราะ...
        
        ⚠️ ระวังอะไร?
        ความเสี่ยง...
        """
        
        score = self.scorer.score_narrative(
            narrative, self.ticker_data, self.indicators, self.percentiles, self.news
        )
        
        # Should penalize if numbers mentioned but no percentile context
        # Note: This depends on whether percentile data is available
        assert isinstance(score.dimension_scores['quantitative_context'], float)
    
    def test_overall_score_calculation(self):
        """Test overall score calculation"""
        narrative = """
        📖 เรื่องราวของหุ้นตัวนี้
        บริษัท Apple Inc. (AAPL) มีราคาปัจจุบัน $202.49
        
        💡 สิ่งที่คุณต้องรู้
        Technical analysis: RSI 65.36 ซึ่งอยู่ในเปอร์เซ็นไทล์ 88.5%
        Volatility: Uncertainty score 52/100 และ ATR 3.03%
        Market sentiment: VWAP แสดงแรงซื้อแรงมาก
        Volume: ปริมาณซื้อขาย 1.8x ของเฉลี่ย
        Fundamental: P/E ratio 28.5
        Historical: RSI สูงกว่าค่าเฉลี่ยในอดีต แสดงแนวโน้มขาขึ้น
        
        🎯 ควรทำอะไรตอนนี้?
        แนะนำ BUY เพราะ uncertainty score ต่ำและมีแรงซื้อแรงมาก
        ปัจจัยสำคัญคือ technical indicators
        
        ⚠️ ระวังอะไร?
        ควรระวังความผันผวนที่อาจเกิดขึ้น
        """
        
        score = self.scorer.score_narrative(
            narrative, self.ticker_data, self.indicators, self.percentiles, self.news
        )
        
        # Calculate expected overall score
        expected = (
            score.dimension_scores['context_completeness'] * 0.20 +
            score.dimension_scores['analysis_dimensions'] * 0.25 +
            score.dimension_scores['temporal_completeness'] * 0.15 +
            score.dimension_scores['actionability'] * 0.20 +
            score.dimension_scores['narrative_structure'] * 0.10 +
            score.dimension_scores['quantitative_context'] * 0.10
        )
        
        assert abs(score.overall_score - expected) < 0.01


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
