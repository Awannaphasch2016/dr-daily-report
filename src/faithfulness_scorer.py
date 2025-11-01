"""
Faithfulness Scorer for Narrative Reports

Measures how accurately the LLM-generated narrative reflects the actual data.
Prevents hallucinations and ensures all claims are grounded in facts.
"""

import re
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass


@dataclass
class FaithfulnessScore:
    """Container for faithfulness scoring results"""
    overall_score: float  # 0-100
    metric_scores: Dict[str, float]  # Individual metric scores
    violations: List[str]  # List of faithfulness violations
    verified_claims: List[str]  # List of verified factual claims


class FaithfulnessScorer:
    """
    Score narrative faithfulness to ground truth data

    Checks:
    1. Numeric accuracy - All numbers match source data
    2. Percentile accuracy - Percentile claims match calculations
    3. News citation accuracy - References match actual news
    4. Interpretation accuracy - Qualitative claims match quantitative thresholds
    
    Note: Completeness (coverage) is now handled by CompletenessScorer
    """

    # Interpretation thresholds (from prompt)
    UNCERTAINTY_THRESHOLDS = {
        'stable': (0, 25),
        'moderate': (25, 50),
        'high': (50, 75),
        'extreme': (75, 100)
    }

    ATR_THRESHOLDS = {
        'low': (0, 2.0),  # Stable movement
        'moderate': (2.0, 3.5),  # Normal volatility
        'high': (3.5, 100)  # High volatility
    }

    VWAP_THRESHOLDS = {
        'strong_buy': 15.0,  # Strong buying pressure
        'buy': 5.0,  # Buying pressure
        'neutral': (-5.0, 5.0),  # Balanced
        'sell': -5.0,  # Selling pressure
        'strong_sell': -15.0  # Strong selling pressure
    }

    VOLUME_THRESHOLDS = {
        'low': (0, 0.8),  # Low interest
        'normal': (0.8, 1.2),  # Normal interest
        'high': (1.2, 100)  # High interest
    }

    def __init__(self):
        """Initialize faithfulness scorer"""
        pass

    def score_narrative(
        self,
        narrative: str,
        ground_truth: Dict,
        indicators: Dict,
        percentiles: Dict,
        news_data: List[Dict]
    ) -> FaithfulnessScore:
        """
        Score narrative faithfulness against ground truth

        Args:
            narrative: Generated Thai narrative text
            ground_truth: Ground truth data (market conditions, etc.)
            indicators: Technical indicators
            percentiles: Percentile data for historical context
            news_data: List of news items with [idx], title, sentiment

        Returns:
            FaithfulnessScore object with detailed scoring
        """
        violations = []
        verified_claims = []

        # 1. Check numeric accuracy
        numeric_score, numeric_violations, numeric_verified = self._check_numeric_accuracy(
            narrative, ground_truth, indicators, percentiles
        )
        violations.extend(numeric_violations)
        verified_claims.extend(numeric_verified)

        # 2. Check percentile claims
        percentile_score, percentile_violations, percentile_verified = self._check_percentile_accuracy(
            narrative, percentiles
        )
        violations.extend(percentile_violations)
        verified_claims.extend(percentile_verified)

        # 3. Check news citations
        news_score, news_violations, news_verified = self._check_news_citations(
            narrative, news_data
        )
        violations.extend(news_violations)
        verified_claims.extend(news_verified)

        # 4. Check interpretation accuracy
        interpretation_score, interp_violations, interp_verified = self._check_interpretation_accuracy(
            narrative, ground_truth
        )
        violations.extend(interp_violations)
        verified_claims.extend(interp_verified)

        # Calculate overall score (weighted average)
        # Updated weights: Numeric 30%, Percentile 25%, News 20%, Interpretation 25%
        overall_score = (
            numeric_score * 0.30 +
            percentile_score * 0.25 +
            news_score * 0.20 +
            interpretation_score * 0.25
        )

        metric_scores = {
            'numeric_accuracy': numeric_score,
            'percentile_accuracy': percentile_score,
            'news_citation_accuracy': news_score,
            'interpretation_accuracy': interpretation_score
        }

        return FaithfulnessScore(
            overall_score=overall_score,
            metric_scores=metric_scores,
            violations=violations,
            verified_claims=verified_claims
        )

    def _check_numeric_accuracy(
        self,
        narrative: str,
        ground_truth: Dict,
        indicators: Dict,
        percentiles: Dict
    ) -> Tuple[float, List[str], List[str]]:
        """Check if numbers in narrative match ground truth"""
        violations = []
        verified = []

        # Extract key metrics from ground truth
        expected_values = {
            'uncertainty': ground_truth.get('uncertainty_score', 0),
            'atr_pct': ground_truth.get('atr_pct', 0),
            'vwap_pct': ground_truth.get('vwap_pct', 0),
            'volume_ratio': ground_truth.get('volume_ratio', 0),
            'rsi': indicators.get('rsi', 0),
            'current_price': indicators.get('current_price', 0)
        }

        # Check each metric
        for metric, expected_value in expected_values.items():
            if expected_value == 0:
                continue

            # Search for this metric's value in narrative
            found = self._find_numeric_claim(narrative, metric, expected_value)

            if found:
                is_accurate, claimed_value = found
                if is_accurate:
                    verified.append(f"{metric}: {claimed_value:.2f} matches {expected_value:.2f}")
                else:
                    violations.append(
                        f"❌ {metric} mismatch: narrative claims {claimed_value:.2f}, actual is {expected_value:.2f}"
                    )

        # Calculate score
        total_checks = len(expected_values)
        accurate_count = len(verified)
        score = (accurate_count / total_checks * 100) if total_checks > 0 else 100

        return score, violations, verified

    def _find_numeric_claim(
        self,
        narrative: str,
        metric: str,
        expected_value: float
    ) -> Optional[Tuple[bool, float]]:
        """
        Find and verify a numeric claim in the narrative

        Returns:
            (is_accurate, claimed_value) or None if not found
        """
        # Define patterns for each metric type
        patterns = {
            'uncertainty': [
                r'ความไม่แน่นอน[^0-9]*?(\d+\.?\d*)',
                r'uncertainty[^0-9]*?(\d+\.?\d*)',
                r'(\d+\.?\d*)/100'
            ],
            'atr_pct': [
                r'ATR[^0-9]*?(\d+\.?\d*)%',
                r'ความผันผวน[^0-9]*?(\d+\.?\d*)%'
            ],
            'vwap_pct': [
                r'(\d+\.?\d*)%[^V]*?(?:เหนือ|ต่ำกว่า|above|below)[^V]*?VWAP',
                r'VWAP[^0-9]*?(\d+\.?\d*)%'
            ],
            'volume_ratio': [
                r'ปริมาณ[^0-9]*?(\d+\.?\d*)x',
                r'(\d+\.?\d*)x[^0-9]*?ของเฉลี่ย'
            ],
            'rsi': [
                r'RSI[^0-9]*?(\d+\.?\d*)',
            ],
            'current_price': [
                r'\$(\d+\.?\d*)',
                r'ราคา[^0-9]*?(\d+\.?\d*)',
            ]
        }

        if metric not in patterns:
            return None

        # Try each pattern
        for pattern in patterns[metric]:
            matches = re.findall(pattern, narrative)
            if matches:
                # Get first match
                claimed_value = float(matches[0])

                # Check if within tolerance (2% for most metrics, 0.5% for prices)
                tolerance = 0.005 if metric == 'current_price' else 0.02
                is_accurate = abs(claimed_value - expected_value) <= (expected_value * tolerance)

                return (is_accurate, claimed_value)

        return None

    def _check_percentile_accuracy(
        self,
        narrative: str,
        percentiles: Dict
    ) -> Tuple[float, List[str], List[str]]:
        """Check if percentile claims match calculations"""
        violations = []
        verified = []

        # Extract percentile mentions from narrative
        percentile_pattern = r'เปอร์เซ็นไทล์[^0-9]*?(\d+\.?\d*)%'
        percentile_mentions = re.findall(percentile_pattern, narrative)

        if not percentile_mentions:
            # No percentile claims to verify
            return 100.0, violations, ["No percentile claims made"]

        # Check each percentile mention
        for claimed_percentile in percentile_mentions:
            claimed_pct = float(claimed_percentile)

            # Try to match with actual percentiles
            matched = False
            for metric, metric_data in percentiles.items():
                # Handle both dict and float formats
                if isinstance(metric_data, dict):
                    actual_pct = metric_data.get('percentile', 0)
                else:
                    actual_pct = metric_data

                if abs(claimed_pct - actual_pct) <= 5:  # Within 5% tolerance
                    verified.append(f"Percentile {claimed_pct}% matches {metric} ({actual_pct:.1f}%)")
                    matched = True
                    break

            if not matched:
                violations.append(f"❌ Percentile {claimed_pct}% does not match any actual percentile")

        # Calculate score
        total = len(percentile_mentions)
        accurate = len(verified)
        score = (accurate / total * 100) if total > 0 else 100

        return score, violations, verified

    def _check_news_citations(
        self,
        narrative: str,
        news_data: List[Dict]
    ) -> Tuple[float, List[str], List[str]]:
        """Check if news citations [1], [2], [3] are valid"""
        violations = []
        verified = []

        # Extract news citations from narrative
        citation_pattern = r'\[(\d+)\]'
        citations = re.findall(citation_pattern, narrative)

        if not citations:
            # No citations made - this is fine
            return 100.0, violations, ["No news citations made"]

        # Check each citation
        valid_indices = set(range(1, len(news_data) + 1))

        for citation in citations:
            idx = int(citation)
            if idx in valid_indices:
                verified.append(f"News citation [{idx}] is valid")
            else:
                violations.append(f"❌ News citation [{idx}] references non-existent news item")

        # Calculate score
        total = len(citations)
        valid = len(verified)
        score = (valid / total * 100) if total > 0 else 100

        return score, violations, verified


    def _check_interpretation_accuracy(
        self,
        narrative: str,
        ground_truth: Dict
    ) -> Tuple[float, List[str], List[str]]:
        """Check if qualitative interpretations match quantitative thresholds"""
        violations = []
        verified = []

        # Check uncertainty interpretation
        uncertainty = ground_truth.get('uncertainty_score', 0)
        uncertainty_interp = self._get_uncertainty_interpretation(uncertainty)

        thai_uncertainty_keywords = {
            'stable': ['เสถียร', 'มั่นคง'],
            'moderate': ['ปานกลาง', 'ค่อนข้าง'],
            'high': ['สูง', 'ผันผวน'],
            'extreme': ['รุนแรง', 'สูงมาก']
        }

        keywords = thai_uncertainty_keywords.get(uncertainty_interp, [])
        if any(kw in narrative for kw in keywords):
            verified.append(f"Uncertainty interpretation '{uncertainty_interp}' matches {uncertainty:.1f}")
        else:
            # Check if wrong interpretation used
            for interp, kws in thai_uncertainty_keywords.items():
                if interp != uncertainty_interp and any(kw in narrative for kw in kws):
                    violations.append(
                        f"❌ Uncertainty {uncertainty:.1f} interpreted as '{interp}' but should be '{uncertainty_interp}'"
                    )
                    break

        # Check VWAP interpretation
        vwap_pct = ground_truth.get('vwap_pct', 0)
        vwap_interp = self._get_vwap_interpretation(vwap_pct)

        thai_vwap_keywords = {
            'strong_buy': ['แรงซื้อแรงมาก', 'แรงซื้อสูงมาก'],
            'buy': ['แรงซื้อ'],
            'neutral': ['สมดุล', 'ปกติ'],
            'sell': ['แรงขาย'],
            'strong_sell': ['แรงขายแรงมาก', 'แรงขายสูงมาก']
        }

        keywords = thai_vwap_keywords.get(vwap_interp, [])
        if any(kw in narrative for kw in keywords):
            verified.append(f"VWAP interpretation '{vwap_interp}' matches {vwap_pct:.1f}%")

        # Calculate score
        total_checks = 2  # uncertainty + vwap
        accurate = len(verified)
        score = (accurate / total_checks * 100) if total_checks > 0 else 100

        return score, violations, verified

    def _get_uncertainty_interpretation(self, uncertainty: float) -> str:
        """Get interpretation category for uncertainty score"""
        for category, (low, high) in self.UNCERTAINTY_THRESHOLDS.items():
            if low <= uncertainty < high:
                return category
        return 'extreme'

    def _get_vwap_interpretation(self, vwap_pct: float) -> str:
        """Get interpretation category for VWAP percentage"""
        if vwap_pct >= self.VWAP_THRESHOLDS['strong_buy']:
            return 'strong_buy'
        elif vwap_pct >= self.VWAP_THRESHOLDS['buy']:
            return 'buy'
        elif vwap_pct <= self.VWAP_THRESHOLDS['strong_sell']:
            return 'strong_sell'
        elif vwap_pct <= self.VWAP_THRESHOLDS['sell']:
            return 'sell'
        else:
            return 'neutral'

    def format_score_report(self, score: FaithfulnessScore) -> str:
        """Format faithfulness score as human-readable report"""
        report_lines = [
            "=" * 80,
            "FAITHFULNESS SCORE REPORT",
            "=" * 80,
            "",
            f"📊 Overall Faithfulness Score: {score.overall_score:.1f}/100",
            "",
            "Metric Breakdown:",
        ]

        for metric, value in score.metric_scores.items():
            emoji = "✅" if value >= 80 else ("⚠️" if value >= 60 else "❌")
            report_lines.append(f"  {emoji} {metric}: {value:.1f}/100")

        if score.violations:
            report_lines.extend([
                "",
                "⚠️ Faithfulness Violations:",
            ])
            for violation in score.violations:
                report_lines.append(f"  {violation}")

        report_lines.extend([
            "",
            f"✅ Verified Claims: {len(score.verified_claims)}",
            "",
            "=" * 80
        ])

        return "\n".join(report_lines)
