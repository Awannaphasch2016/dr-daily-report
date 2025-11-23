# -*- coding: utf-8 -*-
"""
Reasoning Quality Scorer for Narrative Reports

Measures the quality of explanations and reasoning in LLM-generated narratives.
Evaluates clarity, coverage, specificity, alignment, minimality, and consistency.
"""

import re
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass


@dataclass
class ReasoningQualityScore:
    """Container for reasoning quality scoring results"""
    overall_score: float  # 0-100
    dimension_scores: Dict[str, float]  # Individual dimension scores
    issues: List[str]  # List of reasoning quality issues
    strengths: List[str]  # List of reasoning quality strengths


class ReasoningQualityScorer:
    """
    Score reasoning quality of narrative explanations

    Evaluates HOW explanations are structured, not IF they're correct/consistent.

    Checks:
    1. Clarity (25%) - Are explanations clear and easy to understand?
    2. Coverage (25%) - Does reasoning cover all relevant aspects?
    3. Specificity (25%) - Are explanations specific rather than generic?
    4. Minimality (25%) - Is reasoning concise without being incomplete?

    Note: Logical consistency (interpretations matching data) is handled by ConsistencyScorer
    """
    
    def __init__(self):
        """Initialize reasoning quality scorer"""
        pass
    
    def score_narrative(
        self,
        narrative: str,
        indicators: Dict,
        percentiles: Dict,
        ticker_data: Dict
    ) -> ReasoningQualityScore:
        """
        Score reasoning quality of narrative
        
        Args:
            narrative: Generated Thai narrative text
            indicators: Technical indicators
            percentiles: Percentile data for historical context
            ticker_data: Ticker data including company info
        
        Returns:
            ReasoningQualityScore object with detailed scoring
        """
        issues = []
        strengths = []
        
        # 1. Clarity (20%)
        clarity_score, clarity_issues, clarity_strengths = self._check_clarity(
            narrative
        )
        issues.extend(clarity_issues)
        strengths.extend(clarity_strengths)
        
        # 2. Coverage (20%)
        coverage_score, coverage_issues, coverage_strengths = self._check_coverage(
            narrative, indicators, percentiles, ticker_data
        )
        issues.extend(coverage_issues)
        strengths.extend(coverage_strengths)
        
        # 3. Specificity (25%)
        specificity_score, specificity_issues, specificity_strengths = self._check_specificity(
            narrative
        )
        issues.extend(specificity_issues)
        strengths.extend(specificity_strengths)

        # 4. Minimality (25%)
        minimality_score, minimality_issues, minimality_strengths = self._check_minimality(
            narrative
        )
        issues.extend(minimality_issues)
        strengths.extend(minimality_strengths)

        # Calculate overall score (weighted average)
        # Weights: Clarity 25%, Coverage 25%, Specificity 25%, Minimality 25%
        overall_score = (
            clarity_score * 0.25 +
            coverage_score * 0.25 +
            specificity_score * 0.25 +
            minimality_score * 0.25
        )

        dimension_scores = {
            'clarity': clarity_score,
            'coverage': coverage_score,
            'specificity': specificity_score,
            'minimality': minimality_score
        }
        
        return ReasoningQualityScore(
            overall_score=overall_score,
            dimension_scores=dimension_scores,
            issues=issues,
            strengths=strengths
        )
    
    def _check_clarity(self, narrative: str) -> Tuple[float, List[str], List[str]]:
        """Check if explanations are clear and easy to understand"""
        issues = []
        strengths = []
        
        narrative_lower = narrative.lower()
        
        # Check for vague terms that reduce clarity
        vague_terms = [
            'maybe', 'perhaps', 'might', 'could', 'possibly', 'might be',
            'อาจจะ', 'อาจ', 'บางที', 'น่าจะ', 'เป็นไปได้'
        ]
        
        vague_count = sum(1 for term in vague_terms if term in narrative_lower)
        
        # Check for clear cause-effect relationships
        cause_effect_markers = [
            'because', 'เนื่องจาก', 'เพราะว่า', 'ด้วยเหตุผล', 'เพราะ',
            'therefore', 'ดังนั้น', 'จึง', 'ทำให้', 'ส่งผลให้',
            'due to', 'จาก', 'เป็นผลมาจาก'
        ]
        
        has_cause_effect = any(marker in narrative_lower for marker in cause_effect_markers)
        
        # Check for clear structure (sections, formatting)
        has_structure = any(marker in narrative for marker in ['📖', '💡', '🎯', '⚠️', '**'])
        
        # Check for explanations (not just statements)
        explanation_markers = [
            'หมายความว่า', 'หมายถึง', 'แสดงว่า', 'บ่งบอกว่า',
            'means', 'indicates', 'shows', 'suggests', 'implies'
        ]
        
        has_explanations = any(marker in narrative_lower for marker in explanation_markers)
        
        # Check sentence length (very long sentences reduce clarity)
        sentences = re.split(r'[.!?。]', narrative)
        avg_sentence_length = sum(len(s.split()) for s in sentences if s.strip()) / max(len([s for s in sentences if s.strip()]), 1)
        
        # Scoring
        score = 100.0
        
        # Penalize excessive vague terms
        if vague_count > 5:
            score -= 20
            issues.append("❌ Too many vague terms reduce clarity")
        elif vague_count == 0:
            strengths.append("✅ No vague terms - explanations are confident")
        
        # Reward cause-effect relationships
        if has_cause_effect:
            strengths.append("✅ Clear cause-effect relationships present")
        else:
            score -= 15
            issues.append("❌ Missing clear cause-effect relationships")
        
        # Reward structured format
        if has_structure:
            strengths.append("✅ Well-structured narrative format")
        else:
            score -= 10
            issues.append("❌ Narrative lacks clear structure")
        
        # Reward explanations
        if has_explanations:
            strengths.append("✅ Explanations provided (not just statements)")
        else:
            score -= 15
            issues.append("❌ Missing explanations (only statements)")
        
        # Penalize overly long sentences
        if avg_sentence_length > 30:
            score -= 10
            issues.append("❌ Sentences too long (reduce clarity)")
        elif avg_sentence_length < 10:
            score -= 5
            issues.append("⚠️ Sentences too short (may lack detail)")
        
        return max(0, min(100, score)), issues, strengths
    
    def _check_coverage(self, narrative: str, indicators: Dict, percentiles: Dict, ticker_data: Dict) -> Tuple[float, List[str], List[str]]:
        """Check if reasoning covers all relevant aspects"""
        issues = []
        strengths = []
        
        narrative_lower = narrative.lower()
        
        # Check if multiple analytical dimensions are explained
        explained_dimensions = []
        
        # Technical indicators
        if any(keyword in narrative_lower for keyword in ['rsi', 'macd', 'sma', 'technical', 'ทางเทคนิค']):
            explained_dimensions.append('technical')
        
        # Volatility/risk
        if any(keyword in narrative_lower for keyword in ['uncertainty', 'ความไม่แน่นอน', 'atr', 'volatility', 'ความผันผวน']):
            explained_dimensions.append('volatility')
        
        # Market sentiment
        if any(keyword in narrative_lower for keyword in ['vwap', 'buying pressure', 'selling pressure', 'แรงซื้อ', 'แรงขาย', 'sentiment']):
            explained_dimensions.append('sentiment')
        
        # Volume
        if any(keyword in narrative_lower for keyword in ['volume', 'ปริมาณ', 'trading activity']):
            explained_dimensions.append('volume')
        
        # Historical context
        if any(keyword in narrative_lower for keyword in ['percentile', 'เปอร์เซ็นไทล์', 'historical', 'ประวัติศาสตร์', 'ในอดีต']):
            explained_dimensions.append('historical')
        
        # Fundamental (if available)
        if ticker_data.get('pe_ratio') or ticker_data.get('eps'):
            if any(keyword in narrative_lower for keyword in ['p/e', 'pe ratio', 'eps', 'fundamental', 'มูลค่าพื้นฐาน']):
                explained_dimensions.append('fundamental')
        
        # Scoring based on how many dimensions are explained
        total_dimensions = 5 if not (ticker_data.get('pe_ratio') or ticker_data.get('eps')) else 6
        coverage_ratio = len(explained_dimensions) / total_dimensions
        
        score = coverage_ratio * 100
        
        if coverage_ratio >= 0.8:
            strengths.append(f"✅ Covers {len(explained_dimensions)}/{total_dimensions} analytical dimensions")
        elif coverage_ratio >= 0.6:
            issues.append(f"⚠️ Only covers {len(explained_dimensions)}/{total_dimensions} analytical dimensions")
        else:
            issues.append(f"❌ Covers only {len(explained_dimensions)}/{total_dimensions} analytical dimensions")
        
        # Check if reasoning explains WHY, not just WHAT
        why_markers = [
            'เพราะ', 'เนื่องจาก', 'เพราะว่า', 'ด้วยเหตุผล', 'ทำไม',
            'why', 'because', 'reason', 'rationale', 'cause'
        ]
        
        has_why = any(marker in narrative_lower for marker in why_markers)
        
        if has_why:
            strengths.append("✅ Explains WHY (not just WHAT)")
        else:
            score -= 20
            issues.append("❌ Missing WHY explanations (only describes WHAT)")
        
        return max(0, min(100, score)), issues, strengths
    
    def _check_specificity(self, narrative: str) -> Tuple[float, List[str], List[str]]:
        """Check if explanations are specific rather than generic"""
        issues = []
        strengths = []
        
        narrative_lower = narrative.lower()
        
        # Check for generic phrases
        generic_phrases = [
            'generally', 'usually', 'typically', 'often', 'in general',
            'โดยทั่วไป', 'มักจะ', 'ปกติ', 'ทั่วไป', 'ส่วนใหญ่'
        ]
        
        generic_count = sum(1 for phrase in generic_phrases if phrase in narrative_lower)
        
        # Check for specific numbers/data references
        number_patterns = [
            r'\d+\.?\d*%',  # Percentages
            r'\$\d+\.?\d*',  # Dollar amounts
            r'\d+\.?\d*x',  # Multipliers
            r'\d+/\d+',  # Ratios like 51/100
            r'เปอร์เซ็นไทล์\s*\d+\.?\d*%',  # Percentile mentions
        ]
        
        specific_numbers = sum(len(re.findall(pattern, narrative)) for pattern in number_patterns)
        
        # Check for specific comparisons
        comparison_markers = [
            'compared to', 'เทียบกับ', 'เมื่อเทียบ', 'versus', 'vs',
            'higher than', 'lower than', 'สูงกว่า', 'ต่ำกว่า',
            'above', 'below', 'เหนือ', 'ต่ำกว่า'
        ]
        
        has_comparisons = any(marker in narrative_lower for marker in comparison_markers)
        
        # Check for named entities or specific references
        has_specific_refs = bool(re.search(r'DBS\d+|AAPL\d+|NVDA\d+', narrative)) or \
                           bool(re.search(r'บริษัท\s+\w+', narrative))
        
        # Scoring
        score = 100.0
        
        # Penalize excessive generic language
        if generic_count > 3:
            score -= 25
            issues.append("❌ Too many generic phrases (reduce specificity)")
        elif generic_count == 0:
            strengths.append("✅ No generic phrases - explanations are specific")
        
        # Reward specific numbers
        if specific_numbers >= 5:
            strengths.append(f"✅ Includes {specific_numbers} specific numbers/data points")
        elif specific_numbers >= 3:
            score -= 10
            issues.append("⚠️ Could include more specific numbers")
        else:
            score -= 30
            issues.append("❌ Lacks specific numbers/data points")
        
        # Reward comparisons
        if has_comparisons:
            strengths.append("✅ Includes specific comparisons")
        else:
            score -= 15
            issues.append("❌ Missing specific comparisons")
        
        # Reward specific references
        if has_specific_refs:
            strengths.append("✅ References specific entities/tickers")
        
        return max(0, min(100, score)), issues, strengths
    
    def _check_minimality(self, narrative: str) -> Tuple[float, List[str], List[str]]:
        """Check if reasoning is concise without being incomplete"""
        issues = []
        strengths = []
        
        narrative_lower = narrative.lower()
        
        # Calculate basic metrics
        word_count = len(narrative.split())
        char_count = len(narrative)
        
        # Check for repetition
        sentences = re.split(r'[.!?。]', narrative)
        unique_sentences = len(set(s.strip().lower() for s in sentences if s.strip()))
        repetition_ratio = unique_sentences / max(len([s for s in sentences if s.strip()]), 1)
        
        # Check for redundant phrases
        redundant_phrases = [
            'in other words', 'กล่าวอีกนัยหนึ่ง', 'อีกนัยหนึ่ง',
            'to put it simply', 'กล่าวง่ายๆ', 'ง่ายๆ',
            'as mentioned before', 'ดังที่กล่าวมาแล้ว', 'ที่กล่าวมาแล้ว'
        ]
        
        redundant_count = sum(1 for phrase in redundant_phrases if phrase.lower() in narrative.lower())
        
        # Check for filler words
        filler_words = [
            'actually', 'basically', 'essentially', 'literally',
            'จริงๆ', 'โดยพื้นฐาน', 'โดยแท้จริง', 'จริงๆแล้ว'
        ]
        
        filler_count = sum(1 for word in filler_words if word.lower() in narrative_lower)
        
        # Scoring
        score = 100.0
        
        # Optimal length: 200-800 words
        if 200 <= word_count <= 800:
            strengths.append(f"✅ Optimal length ({word_count} words)")
        elif word_count < 200:
            score -= 20
            issues.append(f"⚠️ Too short ({word_count} words) - may lack detail")
        elif word_count > 1200:
            score -= 30
            issues.append(f"❌ Too long ({word_count} words) - needs conciseness")
        elif word_count > 800:
            score -= 15
            issues.append(f"⚠️ Slightly long ({word_count} words)")
        
        # Repetition penalty
        if repetition_ratio < 0.7:
            score -= 20
            issues.append("❌ Too much repetition reduces conciseness")
        elif repetition_ratio >= 0.9:
            strengths.append("✅ No significant repetition")
        
        # Redundant phrases penalty
        if redundant_count > 2:
            score -= 15
            issues.append(f"❌ {redundant_count} redundant phrases found")
        elif redundant_count == 0:
            strengths.append("✅ No redundant phrases")
        
        # Filler words penalty
        if filler_count > 3:
            score -= 10
            issues.append(f"⚠️ {filler_count} filler words found")
        
        return max(0, min(100, score)), issues, strengths

    def format_score_report(self, score: ReasoningQualityScore) -> str:
        """Format reasoning quality score as human-readable report"""
        report_lines = [
            "=" * 80,
            "REASONING QUALITY SCORE REPORT",
            "=" * 80,
            "",
            f"📊 Overall Reasoning Quality Score: {score.overall_score:.1f}/100",
            "",
            "Dimension Breakdown:",
        ]
        
        for dimension, value in score.dimension_scores.items():
            emoji = "✅" if value >= 80 else ("⚠️" if value >= 60 else "❌")
            report_lines.append(f"  {emoji} {dimension}: {value:.1f}/100")
        
        if score.issues:
            report_lines.extend([
                "",
                "❌ Reasoning Quality Issues:",
            ])
            for issue in score.issues:
                report_lines.append(f"  {issue}")
        
        if score.strengths:
            report_lines.extend([
                "",
                "✅ Reasoning Quality Strengths:",
            ])
            for strength in score.strengths:
                report_lines.append(f"  {strength}")
        
        report_lines.extend([
            "",
            "=" * 80
        ])
        
        return "\n".join(report_lines)
