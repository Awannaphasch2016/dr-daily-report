# -*- coding: utf-8 -*-
"""
Completeness Scorer for Narrative Reports - REFACTORED

Measures how comprehensively the LLM-generated narrative covers all necessary
analytical dimensions. Focuses on conceptual coverage rather than exact wording.

Refactored to reduce cyclomatic complexity by:
1. Extracting pattern checking logic into helper class
2. Using table-driven configuration
3. Simplifying conditional logic
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


class PatternChecker:
    """Helper class for checking keyword and regex patterns in text"""

    @staticmethod
    def check_keywords(text: str, keywords: List[str]) -> bool:
        """Check if any keyword exists in text (case-insensitive)"""
        text_lower = text.lower()
        return any(keyword.lower() in text_lower for keyword in keywords)

    @staticmethod
    def check_regex(text: str, pattern: str) -> bool:
        """Check if regex pattern matches in text"""
        return bool(re.search(pattern, text, re.IGNORECASE))

    @staticmethod
    def check_either(text: str, keywords: List[str] = None, regex: str = None) -> bool:
        """Check if either keywords or regex match"""
        keyword_match = PatternChecker.check_keywords(text, keywords) if keywords else False
        regex_match = PatternChecker.check_regex(text, regex) if regex else False
        return keyword_match or regex_match


# Table-driven configuration for analysis dimensions
ANALYSIS_DIMENSIONS = {
    'technical': {
        'keywords': ['rsi', 'macd', 'sma', 'bollinger', 'technical', 'ทางเทคนิค',
                    'technical indicator', 'ตัวชี้วัด', 'indicators'],
        'covered_msg': "Technical analysis mentioned",
        'missing_msg': "❌ Technical analysis (RSI, MACD, SMA, Bollinger Bands) not mentioned",
        'required': True
    },
    'volatility': {
        'keywords': ['volatility', 'ความผันผวน', 'atr', 'volatile'],
        'regex': r'atr[^0-9]*?\d+\.?\d*',
        'covered_msg': "Volatility/risk assessment mentioned",
        'missing_msg': "❌ Volatility/risk assessment (ATR or volatility) not mentioned",
        'required': True
    },
    'sentiment': {
        'keywords': ['vwap', 'buying pressure', 'selling pressure', 'แรงซื้อ', 'แรงขาย',
                    'sentiment', 'news sentiment', 'market sentiment'],
        'regex': r'vwap',
        'covered_msg': "Market sentiment (VWAP or news sentiment) mentioned",
        'missing_msg': "❌ Market sentiment (buying/selling pressure or news sentiment) not mentioned",
        'required': True,
        'special_check': 'news_citations'  # Check for [1], [2], [3]
    },
    'volume': {
        'keywords': ['volume', 'ปริมาณ', 'volume ratio', 'trading activity',
                    'ปริมาณซื้อขาย', 'trading volume'],
        'covered_msg': "Volume analysis mentioned",
        'missing_msg': "❌ Volume analysis not mentioned",
        'required': True
    },
    'fundamental': {
        'keywords': ['p/e', 'pe ratio', 'eps', 'earnings', 'revenue', 'fundamental',
                    'มูลค่าพื้นฐาน', 'อัตราส่วน', 'ผลกำไร'],
        'covered_msg': "Fundamental analysis mentioned",
        'missing_msg': "❌ Fundamental analysis not mentioned (data available but not used)",
        'required': False,  # Only required if data available
        'data_required_check': ['pe_ratio', 'eps', 'revenue_growth', 'earnings_growth']
    },
    'historical': {
        'keywords': ['percentile', 'เปอร์เซ็นไทล์', 'historical', 'historical comparison',
                    'ประวัติศาสตร์', 'เปรียบเทียบ', 'ในอดีต'],
        'regex': r'(เปอร์เซ็นไทล์|percentile)[^0-9]*?\d+\.?\d*%',
        'covered_msg': "Historical context (percentile analysis) mentioned",
        'missing_msg': "❌ Historical context (percentile analysis) not mentioned",
        'required': True
    }
}


class CompletenessScorer:
    """
    Score narrative completeness across analytical dimensions

    Refactored to use table-driven configuration and helper methods
    for reduced cyclomatic complexity.

    VERSION history:
        1.0 — Initial weights: context 20%, analysis 25%, temporal 15%, action 20%, structure 10%, quant 10%
    """
    VERSION = "1.0"

    def __init__(self):
        """Initialize completeness scorer"""
        self.checker = PatternChecker()

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

    def _check_single_item(
        self,
        narrative: str,
        keywords: List[str] = None,
        regex: str = None,
        covered_msg: str = "",
        missing_msg: str = ""
    ) -> Tuple[bool, str, str]:
        """
        Helper: Check a single item with keywords and/or regex

        Returns: (found, covered_msg, missing_msg)
        """
        found = self.checker.check_either(narrative, keywords=keywords, regex=regex)
        return (
            found,
            covered_msg if found else "",
            "" if found else missing_msg
        )

    def _check_context_completeness(
        self,
        narrative: str,
        ticker_data: Dict
    ) -> Tuple[float, List[str], List[str]]:
        """Check if report provides sufficient context about the ticker"""
        missing = []
        covered = []

        # Extract common data
        company_name = ticker_data.get('company_name', '')
        ticker_symbol = ticker_data.get('ticker', '')
        sector = ticker_data.get('sector')
        industry = ticker_data.get('industry')

        # 1. Company identity
        has_identity = self._check_company_identity(narrative, company_name, ticker_symbol)
        if has_identity:
            covered.append("Company identity mentioned")
        else:
            missing.append("❌ Company identity (name/ticker) not mentioned")

        # 2. Current price
        has_price = self._check_price_mention(narrative)
        if has_price:
            covered.append("Current price mentioned")
        else:
            missing.append("❌ Current price not mentioned")

        # 3. Market context (optional)
        if sector or industry:
            has_context = self._check_market_context(narrative, sector, industry)
            if has_context:
                covered.append("Market context (sector/industry) mentioned")

        # 4. Market positioning (optional)
        if self._check_market_positioning(narrative):
            covered.append("Market positioning (52-week high/low or market cap) mentioned")

        # Calculate score (only required items)
        score = self._calculate_score([has_identity, has_price])
        return score, missing, covered

    def _check_company_identity(self, narrative: str, company_name: str, ticker_symbol: str) -> bool:
        """Check if company identity is mentioned"""
        narrative_lower = narrative.lower()
        return (
            (company_name and company_name.lower() in narrative_lower) or
            (ticker_symbol and ticker_symbol.lower() in narrative_lower) or
            self.checker.check_keywords(narrative, ['บริษัท', 'company', 'หุ้น', 'stock'])
        )

    def _check_price_mention(self, narrative: str) -> bool:
        """Check if price is mentioned"""
        price_patterns = [
            r'\$\d+\.?\d*',
            r'ราคา[^0-9]*?\d+\.?\d*',
            r'\d+\.?\d*[^%]*บาท'
        ]
        return any(self.checker.check_regex(narrative, pattern) for pattern in price_patterns)

    def _check_market_context(self, narrative: str, sector: str, industry: str) -> bool:
        """Check if market context (sector/industry) is mentioned"""
        narrative_lower = narrative.lower()
        return (
            (sector and sector.lower() in narrative_lower) or
            (industry and industry.lower() in narrative_lower) or
            self.checker.check_keywords(narrative, ['sector', 'industry', 'อุตสาหกรรม', 'กลุ่ม'])
        )

    def _check_market_positioning(self, narrative: str) -> bool:
        """Check if market positioning is mentioned"""
        return self.checker.check_either(
            narrative,
            keywords=['market cap', 'มูลค่าตลาด'],
            regex=r'52[^0-9]*week|high|low'
        )

    def _check_analysis_dimensions(
        self,
        narrative: str,
        indicators: Dict,
        percentiles: Dict,
        ticker_data: Dict,
        news_data: List[Dict]
    ) -> Tuple[float, List[str], List[str]]:
        """
        Check if report covers all relevant analytical dimensions

        Refactored to use table-driven configuration
        """
        missing = []
        covered = []
        covered_count = 0
        total_count = 0

        # Check each dimension using configuration
        for dim_name, config in ANALYSIS_DIMENSIONS.items():
            # Check if dimension is required
            is_required = config.get('required', True)

            # Handle conditional requirements (e.g., fundamental data)
            if not is_required and 'data_required_check' in config:
                data_fields = config['data_required_check']
                data_available = any(ticker_data.get(field) for field in data_fields)
                if not data_available:
                    continue  # Skip this dimension if data not available
                is_required = True  # Now required since data is available

            total_count += 1

            # Check dimension
            dimension_found = self._check_dimension(
                narrative,
                config,
                news_data if dim_name == 'sentiment' else None
            )

            if dimension_found:
                covered_count += 1
                covered.append(config['covered_msg'])
            else:
                missing.append(config['missing_msg'])

        score = self._calculate_score_from_count(covered_count, total_count)
        return score, missing, covered

    def _check_dimension(
        self,
        narrative: str,
        config: Dict,
        news_data: Optional[List] = None
    ) -> bool:
        """Check a single analysis dimension using configuration"""
        # Standard check: keywords or regex
        found = self.checker.check_either(
            narrative,
            keywords=config.get('keywords'),
            regex=config.get('regex')
        )

        # Special check for news citations
        if config.get('special_check') == 'news_citations' and news_data:
            has_citations = any(f'[{i}]' in narrative for i in range(1, 4))
            found = found or (len(news_data) > 0 and has_citations)

        return found

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

        checks = [
            ('current_state', ['current', 'ปัจจุบัน', 'ตอนนี้', 'now'],
             r'(ราคา|current)[^0-9]*?\d+\.?\d*|\$\d+\.?\d*',
             "Current state mentioned", "❌ Current state not clearly mentioned"),

            ('historical', ['percentile', 'เปอร์เซ็นไทล์', 'historical', 'compared to',
                          'เทียบกับ', 'ในอดีต', 'ประวัติศาสตร์'],
             r'เปอร์เซ็นไทล์[^0-9]*?\d+\.?\d*%',
             "Historical comparison mentioned", "❌ Historical comparison not mentioned"),

            ('trend', ['trend', 'trending', 'momentum', 'upward', 'downward', 'flat',
                      'แนวโน้ม', 'ขึ้น', 'ลง', 'เพิ่มขึ้น', 'ลดลง', 'โมเมนตัม'],
             None,
             "Trend direction mentioned", "❌ Trend direction not mentioned"),

            ('timeframe', ['today', 'yesterday', 'this week', 'this month',
                          'วันนี้', 'เมื่อวาน', 'สัปดาห์นี้', 'เดือนนี้', 'recent', 'ล่าสุด'],
             r'\d{4}[-/]\d{1,2}[-/]\d{1,2}',
             "Timeframe awareness mentioned", "❌ Timeframe awareness not mentioned")
        ]

        results = []
        for _, keywords, regex, covered_msg, missing_msg in checks:
            found, cov, miss = self._check_single_item(
                narrative, keywords, regex, covered_msg, missing_msg
            )
            results.append(found)
            if cov:
                covered.append(cov)
            if miss:
                missing.append(miss)

        score = self._calculate_score(results)
        return score, missing, covered

    def _check_actionability(
        self,
        narrative: str
    ) -> Tuple[float, List[str], List[str]]:
        """Check if report provides actionable insights"""
        missing = []
        covered = []

        # 1. Recommendation
        has_recommendation = self._check_recommendation(narrative)
        if has_recommendation:
            covered.append("Clear recommendation (BUY/SELL/HOLD) provided")
        else:
            missing.append("❌ Clear recommendation (BUY/SELL/HOLD) not provided")

        # 2. Reasoning
        has_reasoning = self.checker.check_keywords(narrative, [
            'because', 'due to', 'เนื่องจาก', 'เพราะว่า', 'reason', 'rationale',
            'เหตุผล', 'why', 'เพราะ', 'based on', 'จาก', 'ด้วยเหตุผล'
        ])
        if has_reasoning:
            covered.append("Reasoning for recommendation provided")
        else:
            missing.append("❌ Reasoning for recommendation not provided")

        # 3. Risk warnings
        has_risks = self.checker.check_keywords(narrative, [
            'risk', 'risky', 'warning', 'caution', 'concern', 'ความเสี่ยง',
            'ระวัง', 'ควรระวัง', 'ข้อควรระวัง', '⚠️', 'warn'
        ])
        if has_risks:
            covered.append("Risk warnings mentioned")
        else:
            missing.append("❌ Risk warnings not mentioned")

        # 4. Key factors
        has_factors = self.checker.check_keywords(narrative, [
            'factor', 'factors', 'key', 'important', 'main',
            'ปัจจัย', 'สำคัญ', 'หลัก', 'สำคัญที่สุด'
        ])
        if has_factors:
            covered.append("Key decision factors identified")
        else:
            missing.append("❌ Key decision factors not clearly identified")

        score = self._calculate_score([has_recommendation, has_reasoning, has_risks, has_factors])
        return score, missing, covered

    def _check_recommendation(self, narrative: str) -> bool:
        """Check if clear recommendation is provided"""
        narrative_upper = narrative.upper()
        return (
            'BUY' in narrative_upper or 'SELL' in narrative_upper or 'HOLD' in narrative_upper or
            'ซื้อ' in narrative or 'ขาย' in narrative or 'ถือ' in narrative or 'แนะนำ' in narrative
        )

    def _check_narrative_structure(
        self,
        narrative: str
    ) -> Tuple[float, List[str], List[str]]:
        """
        Check if report has proper narrative structure

        Refactored to use structured checking
        """
        missing = []
        covered = []

        sections = [
            ('story', '📖', ['story', 'context', 'เรื่องราว', 'บริบท'],
             "Story/context section (📖) present", "❌ Story/context section (📖) missing"),

            ('analysis', '💡', ['insight', 'analysis', 'สิ่งที่คุณต้องรู้', 'วิเคราะห์'],
             "Analysis/insights section (💡) present", "❌ Analysis/insights section (💡) missing"),

            ('recommendation', '🎯', ['recommendation', 'action', 'ควรทำอะไร', 'แนะนำ'],
             "Recommendation section (🎯) present", "❌ Recommendation section (🎯) missing"),

            ('risk', '⚠️', ['risk', 'warning', 'ระวัง', 'ข้อควรระวัง'],
             "Risk section (⚠️) present", "❌ Risk section (⚠️) missing")
        ]

        results = []
        for _, emoji, keywords, covered_msg, missing_msg in sections:
            has_section = emoji in narrative or self.checker.check_keywords(narrative, keywords)
            results.append(has_section)

            if has_section:
                covered.append(covered_msg)
            else:
                missing.append(missing_msg)

        score = self._calculate_score(results)
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

        has_numbers = bool(re.search(r'\d+\.?\d*', narrative))

        # 1. Percentile context
        has_percentile = self.checker.check_either(
            narrative,
            keywords=['percentile', 'เปอร์เซ็นไทล์', 'เทียบกับประวัติศาสตร์'],
            regex=r'(เปอร์เซ็นไทล์|percentile)[^0-9]*?\d+\.?\d*%'
        )

        if has_numbers:
            if has_percentile:
                covered.append("Numbers include percentile context")
            else:
                missing.append("❌ Numbers mentioned but percentile context missing")
        else:
            covered.append("No numbers to contextualize")

        # 2. Qualitative interpretation
        has_interpretation = self.checker.check_keywords(narrative, [
            'high', 'low', 'moderate', 'extreme', 'stable',
            'สูง', 'ต่ำ', 'ปานกลาง', 'รุนแรง', 'เสถียร'
        ])

        if has_interpretation:
            covered.append("Qualitative interpretation provided")
        else:
            missing.append("❌ Qualitative interpretation missing")

        # 3. Comparative context
        has_comparative = self.checker.check_keywords(narrative, [
            'compared to', 'versus', 'vs', 'compared with', 'เทียบกับ', 'เมื่อเทียบ',
            'สูงกว่า', 'ต่ำกว่า', 'above', 'below', 'higher', 'lower', 'average', 'เฉลี่ย'
        ])

        if has_comparative:
            covered.append("Comparative context provided")
        else:
            missing.append("❌ Comparative context missing")

        # Calculate score
        percentile_check = has_percentile if has_numbers else True
        score = self._calculate_score([percentile_check, has_interpretation, has_comparative])

        return score, missing, covered

    def _calculate_score(self, checks: List[bool]) -> float:
        """Calculate score from list of boolean checks"""
        if not checks:
            return 100.0
        return (sum(checks) / len(checks)) * 100

    def _calculate_score_from_count(self, covered: int, total: int) -> float:
        """Calculate score from covered/total count"""
        if total == 0:
            return 100.0
        return (covered / total) * 100

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
