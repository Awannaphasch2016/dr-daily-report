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
    
    Checks:
    1. Clarity - Are explanations clear and easy to understand?
    2. Coverage - Does reasoning cover all relevant aspects?
    3. Specificity - Are explanations specific rather than generic?
    4. Alignment - Do explanations align with data/claims?
    5. Minimality - Is reasoning concise without being incomplete?
    6. Consistency - Are explanations internally consistent?
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
        
        # 3. Specificity (20%)
        specificity_score, specificity_issues, specificity_strengths = self._check_specificity(
            narrative
        )
        issues.extend(specificity_issues)
        strengths.extend(specificity_strengths)
        
        # 4. Alignment (15%)
        alignment_score, alignment_issues, alignment_strengths = self._check_alignment(
            narrative, indicators, percentiles
        )
        issues.extend(alignment_issues)
        strengths.extend(alignment_strengths)
        
        # 5. Minimality (15%)
        minimality_score, minimality_issues, minimality_strengths = self._check_minimality(
            narrative
        )
        issues.extend(minimality_issues)
        strengths.extend(minimality_strengths)
        
        # 6. Consistency (10%)
        consistency_score, consistency_issues, consistency_strengths = self._check_consistency(
            narrative
        )
        issues.extend(consistency_issues)
        strengths.extend(consistency_strengths)
        
        # Calculate overall score (weighted average)
        overall_score = (
            clarity_score * 0.20 +
            coverage_score * 0.20 +
            specificity_score * 0.20 +
            alignment_score * 0.15 +
            minimality_score * 0.15 +
            consistency_score * 0.10
        )
        
        dimension_scores = {
            'clarity': clarity_score,
            'coverage': coverage_score,
            'specificity': specificity_score,
            'alignment': alignment_score,
            'minimality': minimality_score,
            'consistency': consistency_score
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
    
    def _check_alignment(self, narrative: str, indicators: Dict, percentiles: Dict) -> Tuple[float, List[str], List[str]]:
        """Check if explanations align with data/claims"""
        issues = []
        strengths = []
        
        narrative_lower = narrative.lower()
        
        # Check if percentile claims align with percentile data
        percentile_mentions = re.findall(r'เปอร์เซ็นไทล์\s*(\d+\.?\d*)%', narrative)
        percentile_aligned = 0
        percentile_total = 0
        
        if percentile_mentions:
            for claimed_pct in percentile_mentions:
                percentile_total += 1
                claimed_value = float(claimed_pct)
                # Check if it matches any actual percentile (within 5%)
                aligned = False
                for metric, metric_data in percentiles.items():
                    if isinstance(metric_data, dict):
                        actual_pct = metric_data.get('percentile', 0)
                    else:
                        actual_pct = metric_data
                    
                    if abs(claimed_value - actual_pct) <= 5:
                        aligned = True
                        break
                
                if aligned:
                    percentile_aligned += 1
        
        # Check if uncertainty interpretations align with thresholds
        uncertainty_score = indicators.get('uncertainty_score', 0)
        uncertainty_aligned = False
        
        if uncertainty_score < 25:
            expected_terms = ['เสถียร', 'stable', 'มั่นคง']
        elif uncertainty_score < 50:
            expected_terms = ['ปานกลาง', 'moderate', 'ค่อนข้าง']
        elif uncertainty_score < 75:
            expected_terms = ['สูง', 'high', 'ผันผวน']
        else:
            expected_terms = ['รุนแรง', 'extreme', 'สูงมาก']
        
        if any(term in narrative_lower for term in expected_terms):
            uncertainty_aligned = True
        
        # Check if VWAP interpretations align
        # Calculate VWAP percentage from indicators
        current_price = indicators.get('current_price', 0)
        vwap = indicators.get('vwap', 0)
        vwap_pct = ((current_price - vwap) / vwap * 100) if vwap and vwap > 0 else 0
        
        vwap_aligned = False
        
        if vwap_pct >= 15:
            expected_terms = ['แรงซื้อแรงมาก', 'strong buying']
        elif vwap_pct >= 5:
            expected_terms = ['แรงซื้อ', 'buying pressure']
        elif vwap_pct <= -15:
            expected_terms = ['แรงขายแรงมาก', 'strong selling']
        elif vwap_pct <= -5:
            expected_terms = ['แรงขาย', 'selling pressure']
        else:
            expected_terms = ['สมดุล', 'balanced', 'neutral']
        
        if any(term in narrative_lower for term in expected_terms):
            vwap_aligned = True
        
        # Scoring
        score = 100.0
        
        # Percentile alignment
        if percentile_total > 0:
            alignment_ratio = percentile_aligned / percentile_total
            if alignment_ratio >= 0.8:
                strengths.append(f"✅ {percentile_aligned}/{percentile_total} percentile claims aligned")
            else:
                score -= 30 * (1 - alignment_ratio)
                issues.append(f"❌ Only {percentile_aligned}/{percentile_total} percentile claims aligned")
        
        # Uncertainty alignment
        if uncertainty_aligned:
            strengths.append("✅ Uncertainty interpretation aligns with data")
        else:
            score -= 25
            issues.append("❌ Uncertainty interpretation doesn't align with score")
        
        # VWAP alignment
        if vwap_aligned:
            strengths.append("✅ VWAP interpretation aligns with data")
        else:
            score -= 25
            issues.append("❌ VWAP interpretation doesn't align with data")
        
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
    
    def _check_consistency(self, narrative: str) -> Tuple[float, List[str], List[str]]:
        """Check if explanations are internally consistent"""
        issues = []
        strengths = []
        
        narrative_lower = narrative.lower()
        
        # Check for contradictory statements
        contradictions = []
        
        # Check for conflicting recommendations
        has_buy = any(term in narrative_lower for term in ['buy', 'ซื้อ', 'แนะนำซื้อ'])
        has_sell = any(term in narrative_lower for term in ['sell', 'ขาย', 'แนะนำขาย'])
        has_hold = any(term in narrative_lower for term in ['hold', 'ถือ', 'แนะนำถือ'])
        
        # Count distinct recommendations
        recommendations = sum([has_buy, has_sell, has_hold])
        if recommendations > 1:
            contradictions.append("Multiple conflicting recommendations (BUY/SELL/HOLD)")
        
        # Check for conflicting risk assessments
        risk_terms_high = ['high risk', 'high risk', 'risky', 'dangerous', 'ความเสี่ยงสูง', 'เสี่ยงมาก']
        risk_terms_low = ['low risk', 'safe', 'stable', 'ความเสี่ยงต่ำ', 'ปลอดภัย']
        
        has_high_risk = any(term in narrative_lower for term in risk_terms_high)
        has_low_risk = any(term in narrative_lower for term in risk_terms_low)
        
        if has_high_risk and has_low_risk:
            # Check context - if they're in different sections, it's OK
            risk_sections = narrative.split('⚠️')
            if len(risk_sections) > 1:
                # OK - risk section can mention both
                pass
            else:
                contradictions.append("Conflicting risk assessments (high and low)")
        
        # Check for number consistency
        # Extract all numbers and check if same metric has different values
        numbers = re.findall(r'\d+\.?\d*', narrative)
        # This is a simple check - more sophisticated would require semantic understanding
        
        # Check for consistent terminology
        # Check if same concept is referred to differently (e.g., "uncertainty" vs "ความไม่แน่นอน")
        # This is OK - actually good for bilingual content
        
        # Scoring
        score = 100.0
        
        if contradictions:
            score -= len(contradictions) * 30
            for contradiction in contradictions:
                issues.append(f"❌ {contradiction}")
        else:
            strengths.append("✅ No internal contradictions found")
        
        # Check for consistent recommendation
        if recommendations == 1:
            strengths.append("✅ Single clear recommendation (no conflicts)")
        elif recommendations == 0:
            score -= 20
            issues.append("❌ No clear recommendation")
        else:
            score -= 25
            issues.append("⚠️ Multiple or conflicting recommendations")
        
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
