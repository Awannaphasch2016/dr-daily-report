# -*- coding: utf-8 -*-
"""
Completeness Scorer for Narrative Reports

Measures how comprehensively the LLM-generated narrative covers all necessary
analytical dimensions. Focuses on conceptual coverage rather than exact wording.
"""

import re
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass


@dataclass
class CompletenessScore:
    """Container for completeness scoring results"""
    overall_score: float  # 0-100
    dimension_scores: Dict[str, float]  # Individual dimension scores
    missing_elements: List[str]  # Missing analytical elements
    covered_elements: List[str]  # Successfully covered elements


class CompletenessScorer:
    """
    Score narrative completeness across analytical dimensions
    
    Checks:
    1. Context Completeness - Company identity, current state, market context
    2. Analysis Dimension Completeness - Technical, volatility, sentiment, volume, fundamental, historical
    3. Temporal Completeness - Current state, historical comparison, trend, timeframe
    4. Actionability Completeness - Clear recommendation, reasoning, risk warnings
    5. Narrative Structure Completeness - Proper sections (story, analysis, recommendation, risk)
    6. Quantitative Context Completeness - Percentile context, threshold interpretation, comparative context
    """
    
    def __init__(self):
        """Initialize completeness scorer"""
        pass
    
    def score_narrative(
        self,
        narrative: str,
        ticker_data: Dict,
        indicators: Dict,
        percentiles: Dict,
        news_data: List[Dict]
    ) -> CompletenessScore:
        """
        Score narrative completeness
        
        Args:
            narrative: Generated Thai narrative text
            ticker_data: Ticker data including company name, price, sector, etc.
            indicators: Technical indicators
            percentiles: Percentile data for historical context
            news_data: List of news items
        
        Returns:
            CompletenessScore object with detailed scoring
        """
        missing_elements = []
        covered_elements = []
        
        # 1. Context Completeness (20%)
        context_score, context_missing, context_covered = self._check_context_completeness(
            narrative, ticker_data
        )
        missing_elements.extend(context_missing)
        covered_elements.extend(context_covered)
        
        # 2. Analysis Dimension Completeness (25%)
        analysis_score, analysis_missing, analysis_covered = self._check_analysis_dimensions(
            narrative, indicators, percentiles, ticker_data, news_data
        )
        missing_elements.extend(analysis_missing)
        covered_elements.extend(analysis_covered)
        
        # 3. Temporal Completeness (15%)
        temporal_score, temporal_missing, temporal_covered = self._check_temporal_completeness(
            narrative, indicators, percentiles, ticker_data
        )
        missing_elements.extend(temporal_missing)
        covered_elements.extend(temporal_covered)
        
        # 4. Actionability Completeness (20%)
        action_score, action_missing, action_covered = self._check_actionability(
            narrative
        )
        missing_elements.extend(action_missing)
        covered_elements.extend(action_covered)
        
        # 5. Narrative Structure Completeness (10%)
        structure_score, structure_missing, structure_covered = self._check_narrative_structure(
            narrative
        )
        missing_elements.extend(structure_missing)
        covered_elements.extend(structure_covered)
        
        # 6. Quantitative Context Completeness (10%)
        quant_score, quant_missing, quant_covered = self._check_quantitative_context(
            narrative, indicators, percentiles
        )
        missing_elements.extend(quant_missing)
        covered_elements.extend(quant_covered)
        
        # Calculate overall score (weighted average)
        overall_score = (
            context_score * 0.20 +
            analysis_score * 0.25 +
            temporal_score * 0.15 +
            action_score * 0.20 +
            structure_score * 0.10 +
            quant_score * 0.10
        )
        
        dimension_scores = {
            'context_completeness': context_score,
            'analysis_dimensions': analysis_score,
            'temporal_completeness': temporal_score,
            'actionability': action_score,
            'narrative_structure': structure_score,
            'quantitative_context': quant_score
        }
        
        return CompletenessScore(
            overall_score=overall_score,
            dimension_scores=dimension_scores,
            missing_elements=missing_elements,
            covered_elements=covered_elements
        )
    
    def _check_context_completeness(
        self,
        narrative: str,
        ticker_data: Dict
    ) -> Tuple[float, List[str], List[str]]:
        """Check if report provides sufficient context about the ticker"""
        missing = []
        covered = []
        
        narrative_lower = narrative.lower()
        
        # Check company identity
        company_name = ticker_data.get('company_name', '')
        ticker_symbol = ticker_data.get('ticker', '')
        
        has_company_identity = (
            company_name.lower() in narrative_lower or
            ticker_symbol.lower() in narrative_lower or
            any(keyword in narrative_lower for keyword in ['บริษัท', 'company', 'หุ้น', 'stock'])
        )
        
        if has_company_identity:
            covered.append("Company identity mentioned")
        else:
            missing.append("❌ Company identity (name/ticker) not mentioned")
        
        # Check current price
        current_price = ticker_data.get('current_price') or ticker_data.get('close')
        has_price = (
            bool(re.search(r'\$\d+\.?\d*', narrative)) or
            bool(re.search(r'ราคา[^0-9]*?\d+\.?\d*', narrative)) or
            bool(re.search(r'\d+\.?\d*[^%]*บาท', narrative))
        )
        
        if has_price:
            covered.append("Current price mentioned")
        else:
            missing.append("❌ Current price not mentioned")
        
        # Check market context (sector/industry) - optional, don't penalize if not available
        sector = ticker_data.get('sector')
        industry = ticker_data.get('industry')
        
        if sector or industry:
            has_context = (
                bool(sector and sector.lower() in narrative_lower) or
                bool(industry and industry.lower() in narrative_lower) or
                any(keyword in narrative_lower for keyword in ['sector', 'industry', 'อุตสาหกรรม', 'กลุ่ม'])
            )
            
            if has_context:
                covered.append("Market context (sector/industry) mentioned")
            # Don't penalize if not mentioned - this is optional
        
        # Check market positioning (52-week high/low, market cap) - optional
        has_market_positioning = (
            bool(re.search(r'52[^0-9]*week', narrative_lower)) or
            bool(re.search(r'high|low', narrative_lower)) or
            bool(re.search(r'market[^0-9]*cap', narrative_lower)) or
            bool(re.search(r'มูลค่าตลาด', narrative_lower))
        )
        
        if has_market_positioning:
            covered.append("Market positioning (52-week high/low or market cap) mentioned")
        
        # Calculate score
        total_checks = 2  # Required: company identity, current price
        covered_count = sum([has_company_identity, has_price])
        score = (covered_count / total_checks * 100) if total_checks > 0 else 100
        
        return score, missing, covered
    
    def _check_analysis_dimensions(
        self,
        narrative: str,
        indicators: Dict,
        percentiles: Dict,
        ticker_data: Dict,
        news_data: List[Dict]
    ) -> Tuple[float, List[str], List[str]]:
        """Check if report covers all relevant analytical dimensions"""
        missing = []
        covered = []
        
        narrative_lower = narrative.lower()
        
        # 1. Technical Analysis
        has_technical = any(keyword in narrative_lower for keyword in [
            'rsi', 'macd', 'sma', 'bollinger', 'technical', 'ทางเทคนิค',
            'technical indicator', 'ตัวชี้วัด', 'indicators'
        ])
        
        if has_technical:
            covered.append("Technical analysis mentioned")
        else:
            missing.append("❌ Technical analysis (RSI, MACD, SMA, Bollinger Bands) not mentioned")
        
        # 2. Volatility/Risk Assessment
        has_volatility = (
            any(keyword in narrative_lower for keyword in [
                'uncertainty', 'ความไม่แน่นอน', 'uncertainty score',
                'volatility', 'ความผันผวน', 'atr', 'volatile'
            ]) or
            bool(re.search(r'atr[^0-9]*?\d+\.?\d*', narrative_lower))
        )
        
        if has_volatility:
            covered.append("Volatility/risk assessment mentioned")
        else:
            missing.append("❌ Volatility/risk assessment (uncertainty score or ATR) not mentioned")
        
        # 3. Market Sentiment
        has_sentiment = (
            any(keyword in narrative_lower for keyword in [
                'vwap', 'buying pressure', 'selling pressure', 'แรงซื้อ', 'แรงขาย',
                'sentiment', 'sentiment', 'news sentiment', 'market sentiment'
            ]) or
            bool(re.search(r'vwap', narrative_lower)) or
            (len(news_data) > 0 and ('[1]' in narrative or '[2]' in narrative or '[3]' in narrative))
        )
        
        if has_sentiment:
            covered.append("Market sentiment (VWAP or news sentiment) mentioned")
        else:
            missing.append("❌ Market sentiment (buying/selling pressure or news sentiment) not mentioned")
        
        # 4. Volume Analysis
        has_volume = any(keyword in narrative_lower for keyword in [
            'volume', 'ปริมาณ', 'volume ratio', 'trading activity',
            'ปริมาณซื้อขาย', 'trading volume'
        ])
        
        if has_volume:
            covered.append("Volume analysis mentioned")
        else:
            missing.append("❌ Volume analysis not mentioned")
        
        # 5. Fundamental Context (if available)
        has_fundamental = False
        fundamental_available = any([
            ticker_data.get('pe_ratio'),
            ticker_data.get('eps'),
            ticker_data.get('revenue_growth'),
            ticker_data.get('earnings_growth')
        ])
        
        if fundamental_available:
            has_fundamental = any(keyword in narrative_lower for keyword in [
                'p/e', 'pe ratio', 'eps', 'earnings', 'revenue', 'fundamental',
                'มูลค่าพื้นฐาน', 'อัตราส่วน', 'ผลกำไร'
            ])
            
            if has_fundamental:
                covered.append("Fundamental analysis mentioned")
            else:
                missing.append("❌ Fundamental analysis not mentioned (data available but not used)")
        # Don't penalize if fundamental data not available
        
        # 6. Historical Context
        has_historical = (
            any(keyword in narrative_lower for keyword in [
                'percentile', 'เปอร์เซ็นไทล์', 'historical', 'historical comparison',
                'ประวัติศาสตร์', 'เปรียบเทียบ', 'ในอดีต'
            ]) or
            bool(re.search(r'เปอร์เซ็นไทล์[^0-9]*?\d+\.?\d*%', narrative)) or
            bool(re.search(r'percentile[^0-9]*?\d+\.?\d*%', narrative_lower))
        )
        
        if has_historical:
            covered.append("Historical context (percentile analysis) mentioned")
        else:
            missing.append("❌ Historical context (percentile analysis) not mentioned")
        
        # Calculate score
        # Count dimensions that are either covered or not required (fundamental without data)
        total_dimensions = 6 if fundamental_available else 5
        covered_dimensions = sum([
            has_technical,
            has_volatility,
            has_sentiment,
            has_volume,
            has_historical,
            has_fundamental if fundamental_available else True  # Don't count if not available
        ])
        
        score = (covered_dimensions / total_dimensions * 100) if total_dimensions > 0 else 100
        
        return score, missing, covered
    
    def _check_temporal_completeness(
        self,
        narrative: str,
        indicators: Dict,
        percentiles: Dict,
        ticker_data: Dict
    ) -> Tuple[float, List[str], List[str]]:
        """Check if report provides temporal context"""
        missing = []
        covered = []
        
        narrative_lower = narrative.lower()
        
        # 1. Current State
        has_current_state = (
            bool(re.search(r'current|ปัจจุบัน|ตอนนี้|now', narrative_lower)) or
            bool(re.search(r'ราคา[^0-9]*?\d+\.?\d*', narrative)) or
            bool(re.search(r'\$\d+\.?\d*', narrative))
        )
        
        if has_current_state:
            covered.append("Current state mentioned")
        else:
            missing.append("❌ Current state not clearly mentioned")
        
        # 2. Historical Comparison
        has_historical = (
            any(keyword in narrative_lower for keyword in [
                'percentile', 'เปอร์เซ็นไทล์', 'historical', 'compared to',
                'เทียบกับ', 'ในอดีต', 'ประวัติศาสตร์'
            ]) or
            bool(re.search(r'เปอร์เซ็นไทล์[^0-9]*?\d+\.?\d*%', narrative))
        )
        
        if has_historical:
            covered.append("Historical comparison mentioned")
        else:
            missing.append("❌ Historical comparison (percentile or historical values) not mentioned")
        
        # 3. Trend Direction
        has_trend = any(keyword in narrative_lower for keyword in [
            'trend', 'trending', 'momentum', 'upward', 'downward', 'flat',
            'แนวโน้ม', 'ขึ้น', 'ลง', 'เพิ่มขึ้น', 'ลดลง', 'โมเมนตัม'
        ])
        
        if has_trend:
            covered.append("Trend direction mentioned")
        else:
            missing.append("❌ Trend direction not mentioned")
        
        # 4. Timeframe Awareness
        has_timeframe = (
            bool(re.search(r'\d{4}[-/]\d{1,2}[-/]\d{1,2}', narrative)) or  # Date format
            bool(re.search(r'(today|yesterday|this week|this month)', narrative_lower)) or
            bool(re.search(r'(วันนี้|เมื่อวาน|สัปดาห์นี้|เดือนนี้)', narrative_lower)) or
            bool(re.search(r'(recent|ล่าสุด|เมื่อเร็วๆนี้)', narrative_lower))
        )
        
        if has_timeframe:
            covered.append("Timeframe awareness (date or time context) mentioned")
        else:
            missing.append("❌ Timeframe awareness not mentioned")
        
        # Calculate score
        total_checks = 4
        covered_count = sum([has_current_state, has_historical, has_trend, has_timeframe])
        score = (covered_count / total_checks * 100) if total_checks > 0 else 100
        
        return score, missing, covered
    
    def _check_actionability(
        self,
        narrative: str
    ) -> Tuple[float, List[str], List[str]]:
        """Check if report provides actionable insights"""
        missing = []
        covered = []
        
        narrative_upper = narrative.upper()
        narrative_lower = narrative.lower()
        
        # 1. Clear Recommendation
        has_recommendation = (
            'BUY' in narrative_upper or
            'SELL' in narrative_upper or
            'HOLD' in narrative_upper or
            'ซื้อ' in narrative or
            'ขาย' in narrative or
            'ถือ' in narrative or
            'แนะนำ' in narrative
        )
        
        if has_recommendation:
            covered.append("Clear recommendation (BUY/SELL/HOLD) provided")
        else:
            missing.append("❌ Clear recommendation (BUY/SELL/HOLD) not provided")
        
        # 2. Reasoning Provided
        has_reasoning = any(keyword in narrative_lower for keyword in [
            'because', 'because of', 'due to', 'เนื่องจาก', 'เพราะว่า',
            'reason', 'rationale', 'เหตุผล', 'why', 'เพราะ',
            'based on', 'จาก', 'ด้วยเหตุผล'
        ])
        
        if has_reasoning:
            covered.append("Reasoning for recommendation provided")
        else:
            missing.append("❌ Reasoning for recommendation not provided")
        
        # 3. Risk Warnings
        has_risks = any(keyword in narrative_lower for keyword in [
            'risk', 'risky', 'warning', 'caution', 'concern',
            'ความเสี่ยง', 'ระวัง', 'ควรระวัง', 'ข้อควรระวัง',
            '⚠️', 'warn', 'warns'
        ])
        
        if has_risks:
            covered.append("Risk warnings mentioned")
        else:
            missing.append("❌ Risk warnings not mentioned")
        
        # 4. Key Decision Factors
        has_factors = any(keyword in narrative_lower for keyword in [
            'factor', 'factors', 'key', 'important', 'main',
            'ปัจจัย', 'สำคัญ', 'หลัก', 'สำคัญที่สุด'
        ])
        
        if has_factors:
            covered.append("Key decision factors identified")
        else:
            missing.append("❌ Key decision factors not clearly identified")
        
        # Calculate score
        total_checks = 4
        covered_count = sum([has_recommendation, has_reasoning, has_risks, has_factors])
        score = (covered_count / total_checks * 100) if total_checks > 0 else 100
        
        return score, missing, covered
    
    def _check_narrative_structure(
        self,
        narrative: str
    ) -> Tuple[float, List[str], List[str]]:
        """Check if report has proper narrative structure"""
        missing = []
        covered = []
        
        narrative_lower = narrative.lower()
        
        # Check for story/context section (📖)
        has_story = (
            '📖' in narrative or
            'story' in narrative_lower or
            'context' in narrative_lower or
            'เรื่องราว' in narrative or
            'บริบท' in narrative
        )
        
        if has_story:
            covered.append("Story/context section (📖) present")
        else:
            missing.append("❌ Story/context section (📖) missing")
        
        # Check for analysis/insights section (💡)
        has_analysis = (
            '💡' in narrative or
            'insight' in narrative_lower or
            'analysis' in narrative_lower or
            'สิ่งที่คุณต้องรู้' in narrative or
            'วิเคราะห์' in narrative
        )
        
        if has_analysis:
            covered.append("Analysis/insights section (💡) present")
        else:
            missing.append("❌ Analysis/insights section (💡) missing")
        
        # Check for recommendation section (🎯)
        has_recommendation = (
            '🎯' in narrative or
            'recommendation' in narrative_lower or
            'action' in narrative_lower or
            'ควรทำอะไร' in narrative or
            'แนะนำ' in narrative
        )
        
        if has_recommendation:
            covered.append("Recommendation section (🎯) present")
        else:
            missing.append("❌ Recommendation section (🎯) missing")
        
        # Check for risk section (⚠️)
        has_risk = (
            '⚠️' in narrative or
            '⚠' in narrative or
            'risk' in narrative_lower or
            'warning' in narrative_lower or
            'ระวัง' in narrative or
            'ข้อควรระวัง' in narrative
        )
        
        if has_risk:
            covered.append("Risk section (⚠️) present")
        else:
            missing.append("❌ Risk section (⚠️) missing")
        
        # Calculate score
        total_checks = 4
        covered_count = sum([has_story, has_analysis, has_recommendation, has_risk])
        score = (covered_count / total_checks * 100) if total_checks > 0 else 100
        
        return score, missing, covered
    
    def _check_quantitative_context(
        self,
        narrative: str,
        indicators: Dict,
        percentiles: Dict
    ) -> Tuple[float, List[str], List[str]]:
        """Check if numbers are properly contextualized"""
        missing = []
        covered = []
        
        narrative_lower = narrative.lower()
        
        # Check if percentiles are used when numbers are mentioned
        # Look for number patterns followed by percentile context
        has_percentile_context = (
            bool(re.search(r'เปอร์เซ็นไทล์[^0-9]*?\d+\.?\d*%', narrative)) or
            bool(re.search(r'percentile[^0-9]*?\d+\.?\d*%', narrative_lower)) or
            any(keyword in narrative_lower for keyword in [
                'percentile', 'เปอร์เซ็นไทล์', 'เทียบกับประวัติศาสตร์'
            ])
        )
        
        # Check if numbers are mentioned
        has_numbers = bool(re.search(r'\d+\.?\d*', narrative))
        
        if has_numbers:
            if has_percentile_context:
                covered.append("Numbers include percentile context")
            else:
                missing.append("❌ Numbers mentioned but percentile context missing")
        else:
            # No numbers mentioned, can't check percentile context
            covered.append("No numbers to contextualize")
        
        # Check threshold interpretation
        # Look for qualitative terms that should match quantitative thresholds
        has_interpretation = any(keyword in narrative_lower for keyword in [
            'high', 'low', 'moderate', 'extreme', 'stable',
            'สูง', 'ต่ำ', 'ปานกลาง', 'รุนแรง', 'เสถียร'
        ])
        
        if has_interpretation:
            covered.append("Qualitative interpretation provided")
        else:
            missing.append("❌ Qualitative interpretation missing")
        
        # Check comparative context
        has_comparative = any(keyword in narrative_lower for keyword in [
            'compared to', 'versus', 'vs', 'compared with',
            'เทียบกับ', 'เมื่อเทียบ', 'สูงกว่า', 'ต่ำกว่า',
            'above', 'below', 'higher', 'lower', 'average', 'เฉลี่ย'
        ])
        
        if has_comparative:
            covered.append("Comparative context provided")
        else:
            missing.append("❌ Comparative context missing")
        
        # Calculate score
        total_checks = 3
        covered_count = sum([
            has_percentile_context if has_numbers else True,  # Don't penalize if no numbers
            has_interpretation,
            has_comparative
        ])
        score = (covered_count / total_checks * 100) if total_checks > 0 else 100
        
        return score, missing, covered
    
    def format_score_report(self, score: CompletenessScore) -> str:
        """Format completeness score as human-readable report"""
        report_lines = [
            "=" * 80,
            "COMPLETENESS SCORE REPORT",
            "=" * 80,
            "",
            f"📊 Overall Completeness Score: {score.overall_score:.1f}/100",
            "",
            "Dimension Breakdown:",
        ]
        
        for dimension, value in score.dimension_scores.items():
            emoji = "✅" if value >= 80 else ("⚠️" if value >= 60 else "❌")
            report_lines.append(f"  {emoji} {dimension}: {value:.1f}/100")
        
        if score.missing_elements:
            report_lines.extend([
                "",
                "❌ Missing Elements:",
            ])
            for missing in score.missing_elements:
                report_lines.append(f"  {missing}")
        
        report_lines.extend([
            "",
            f"✅ Covered Elements: {len(score.covered_elements)}",
            "",
            "=" * 80
        ])
        
        return "\n".join(report_lines)
