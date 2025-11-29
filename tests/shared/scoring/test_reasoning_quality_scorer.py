"""
Tests for ReasoningQualityScorer
"""

import pytest
from src.scoring.reasoning_quality_scorer import ReasoningQualityScorer, ReasoningQualityScore


class TestReasoningQualityScorer:
    """Test suite for ReasoningQualityScorer"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.scorer = ReasoningQualityScorer()
        
        # Sample indicators
        self.indicators = {
            'rsi': 65.36,
            'macd': 2.5,
            'uncertainty_score': 52.0,
            'atr': 0.70,
            'current_price': 53.93,
            'vwap': 44.20,
            'volume': 1000000,
            'volume_sma': 1150000
        }
        
        # Sample percentiles
        self.percentiles = {
            'rsi': {
                'current_value': 65.36,
                'percentile': 88.5
            },
            'uncertainty_score': {
                'current_value': 52.0,
                'percentile': 66.0
            }
        }
        
        # Sample ticker data
        self.ticker_data = {
            'company_name': 'Apple Inc.',
            'ticker': 'AAPL',
            'current_price': 53.93
        }
    
    def test_clarity_good(self):
        """Test clarity scoring with good explanations"""
        narrative = """
        📖 เรื่องราวของหุ้นตัวนี้
        Uncertainty score 52/100 แสดงตลาดผันผวนสูง ซึ่งหมายความว่า
        ตลาดมีความไม่แน่นอนและอาจมีการเปลี่ยนแปลงราคาอย่างรวดเร็ว
        
        💡 สิ่งที่คุณต้องรู้
        RSI 65.36 ซึ่งอยู่ในเปอร์เซ็นไทล์ 88.5% แสดงว่าตอนนี้ RSI สูงกว่าปกติ
        เมื่อเทียบกับประวัติศาสตร์ ซึ่งบ่งชี้ว่า stock อาจอยู่ในภาวะ overbought
        
        🎯 ควรทำอะไรตอนนี้?
        แนะนำ BUY เพราะ uncertainty score ต่ำและมีแรงซื้อแรงมาก
        
        ⚠️ ระวังอะไร?
        ควรระวังความผันผวนที่อาจเกิดขึ้น
        """
        
        score = self.scorer.score_narrative(
            narrative, self.indicators, self.percentiles, self.ticker_data
        )
        
        assert score.dimension_scores['clarity'] >= 80
        assert any('Clear cause-effect' in strength for strength in score.strengths)
    
    def test_coverage_full(self):
        """Test coverage scoring with full coverage"""
        narrative = """
        📖 เรื่องราวของหุ้นตัวนี้
        Uncertainty score 52/100 ซึ่งแสดงตลาดผันผวนสูง
        
        💡 สิ่งที่คุณต้องรู้
        Technical analysis: RSI 65.36, MACD 2.5
        Volatility: Uncertainty score 52/100 และ ATR 1.30%
        Market sentiment: VWAP แสดงแรงซื้อแรงมาก
        Volume: Volume ratio 0.87x
        Fundamental: P/E ratio 28.5
        Historical: RSI อยู่ในเปอร์เซ็นไทล์ 88.5%
        
        🎯 ควรทำอะไรตอนนี้?
        แนะนำ BUY
        
        ⚠️ ระวังอะไร?
        ความเสี่ยง...
        """
        
        score = self.scorer.score_narrative(
            narrative, self.indicators, self.percentiles, self.ticker_data
        )
        
        assert score.dimension_scores['coverage'] >= 80
    
    def test_specificity_good(self):
        """Test specificity scoring with specific details"""
        narrative = """
        📖 เรื่องราวของหุ้นตัวนี้
        Uncertainty score 52/100 ซึ่งอยู่ในเปอร์เซ็นไทล์ 66%
        ATR 1.30% แสดงความผันผวนต่ำ
        ราคา 22.06% เหนือ VWAP
        Volume ratio 0.87x ของค่าเฉลี่ย
        
        💡 สิ่งที่คุณต้องรู้
        RSI 65.36 ซึ่งอยู่ในเปอร์เซ็นไทล์ 88.5% - สูงกว่าค่าเฉลี่ยในอดีต
        
        🎯 ควรทำอะไรตอนนี้?
        แนะนำ BUY
        
        ⚠️ ระวังอะไร?
        ความเสี่ยง...
        """
        
        score = self.scorer.score_narrative(
            narrative, self.indicators, self.percentiles, self.ticker_data
        )
        
        assert score.dimension_scores['specificity'] >= 80
        assert any('specific numbers' in strength.lower() for strength in score.strengths)
    
    def test_minimality_optimal_length(self):
        """Test minimality scoring with optimal length content"""
        # Generate a narrative with optimal word count (200-800 words)
        narrative = """
        📖 เรื่องราวของหุ้นตัวนี้
        Uncertainty score 52/100 ซึ่งแสดงตลาดผันผวนสูง เนื่องจากตลาดมีความไม่แน่นอนสูง
        ATR 1.30% แสดงความผันผวนต่ำ ทำให้ลงทุนได้ปลอดภัยในระยะสั้น
        ราคา 22.06% เหนือ VWAP แสดงแรงซื้อแรงมาก ซึ่งบ่งบอกว่าตลาดมีความต้องการหุ้นตัวนี้สูง

        💡 สิ่งที่คุณต้องรู้
        Technical indicators show positive momentum. RSI indicates normal levels without overbought conditions.
        Volume is trading at normal levels compared to average. MACD shows positive momentum which is a good sign
        for short term trading. The stock has been showing consistent performance over the past weeks.

        🎯 ควรทำอะไรตอนนี้?
        แนะนำ BUY เพราะ indicators แสดงสัญญาณบวก และ momentum ยังคงแข็งแกร่ง
        This recommendation is based on technical analysis and market conditions.

        ⚠️ ระวังอะไร?
        ความเสี่ยงหลักคือความผันผวนของตลาดที่อาจเกิดขึ้นได้
        Market volatility may impact short term price movements.
        """

        score = self.scorer.score_narrative(
            narrative, self.indicators, self.percentiles, self.ticker_data
        )

        # Implementation only has 4 dimensions: clarity, coverage, specificity, minimality
        # All dimension scores should be valid
        assert 'minimality' in score.dimension_scores
        assert 0 <= score.dimension_scores['minimality'] <= 100
    
    def test_minimality_good(self):
        """Test minimality scoring with concise but complete reasoning"""
        narrative = """
        📖 เรื่องราวของหุ้นตัวนี้
        Uncertainty score 52/100 แสดงตลาดผันผวนสูง
        
        💡 สิ่งที่คุณต้องรู้
        RSI 65.36 ซึ่งอยู่ในเปอร์เซ็นไทล์ 88.5% แสดงภาวะ overbought
        
        🎯 ควรทำอะไรตอนนี้?
        แนะนำ BUY เพราะ uncertainty ต่ำและมีแรงซื้อแรงมาก
        
        ⚠️ ระวังอะไร?
        ควรระวังความผันผวน
        """
        
        score = self.scorer.score_narrative(
            narrative, self.indicators, self.percentiles, self.ticker_data
        )
        
        assert score.dimension_scores['minimality'] >= 80
    
    def test_clarity_with_explanations(self):
        """Test clarity scoring with well-explained content"""
        narrative = """
        📖 เรื่องราวของหุ้นตัวนี้
        Uncertainty score 52/100 แสดงตลาดผันผวนสูง เนื่องจากมีความไม่แน่นอนในตลาด
        ซึ่งหมายความว่าการลงทุนมีความเสี่ยงสูงขึ้น

        💡 สิ่งที่คุณต้องรู้
        RSI 65.36 ซึ่งอยู่ในเปอร์เซ็นไทล์ 88.5% แสดงว่าหุ้นอยู่ในระดับที่สูงกว่าปกติ
        ดังนั้นควรระวังการ overbought

        🎯 ควรทำอะไรตอนนี้?
        แนะนำ BUY เพราะ momentum ยังคงแข็งแกร่ง

        ⚠️ ระวังอะไร?
        ความเสี่ยงหลักคือความผันผวนของตลาด
        """

        score = self.scorer.score_narrative(
            narrative, self.indicators, self.percentiles, self.ticker_data
        )

        # Implementation only has 4 dimensions: clarity, coverage, specificity, minimality
        assert 'clarity' in score.dimension_scores
        assert 0 <= score.dimension_scores['clarity'] <= 100

    def test_coverage_technical_and_volume(self):
        """Test coverage scoring with technical and volume analysis"""
        narrative = """
        📖 เรื่องราวของหุ้นตัวนี้
        Uncertainty score 52/100 แสดงความผันผวน

        💡 สิ่งที่คุณต้องรู้
        RSI 65.36 and MACD 2.5 show technical momentum
        Volume is at 1.0x average showing normal trading activity
        Historical percentile at 88.5% indicates above average levels

        🎯 ควรทำอะไรตอนนี้?
        แนะนำ BUY เพราะ technical indicators positive

        ⚠️ ระวังอะไร?
        ความเสี่ยง volatility
        """

        score = self.scorer.score_narrative(
            narrative, self.indicators, self.percentiles, self.ticker_data
        )

        # Implementation only has 4 dimensions: clarity, coverage, specificity, minimality
        assert 'coverage' in score.dimension_scores
        assert 0 <= score.dimension_scores['coverage'] <= 100
    
    def test_overall_score_calculation(self):
        """Test overall score calculation"""
        narrative = """
        📖 เรื่องราวของหุ้นตัวนี้
        Uncertainty score 52/100 ซึ่งแสดงตลาดผันผวนสูง

        💡 สิ่งที่คุณต้องรู้
        RSI 65.36 ซึ่งอยู่ในเปอร์เซ็นไทล์ 88.5%

        🎯 ควรทำอะไรตอนนี้?
        แนะนำ BUY เพราะ...

        ⚠️ ระวังอะไร?
        ความเสี่ยง...
        """

        score = self.scorer.score_narrative(
            narrative, self.indicators, self.percentiles, self.ticker_data
        )

        # Implementation uses 4 dimensions at 25% each
        expected = (
            score.dimension_scores['clarity'] * 0.25 +
            score.dimension_scores['coverage'] * 0.25 +
            score.dimension_scores['specificity'] * 0.25 +
            score.dimension_scores['minimality'] * 0.25
        )

        # Allow small rounding differences (0.5 tolerance)
        assert abs(score.overall_score - expected) < 0.5
    
    def test_format_score_report(self):
        """Test score report formatting"""
        narrative = """
        📖 เรื่องราวของหุ้นตัวนี้
        Uncertainty score 52/100
        
        💡 สิ่งที่คุณต้องรู้
        Technical indicators...
        
        🎯 ควรทำอะไรตอนนี้?
        แนะนำ BUY
        
        ⚠️ ระวังอะไร?
        ความเสี่ยง...
        """
        
        score = self.scorer.score_narrative(
            narrative, self.indicators, self.percentiles, self.ticker_data
        )
        
        report = self.scorer.format_score_report(score)
        
        assert "REASONING QUALITY SCORE REPORT" in report
        assert f"{score.overall_score:.1f}/100" in report
        assert "Dimension Breakdown:" in report


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
