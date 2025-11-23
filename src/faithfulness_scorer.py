# -*- coding: utf-8 -*-
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

    Evaluates factual accuracy: "Are stated facts supported by retrieved info?"

    Checks:
    1. Numeric accuracy - All numbers match source data (with tolerance)
    2. Percentile accuracy - Percentile claims match calculations
    3. News citation accuracy - References match actual news
    4. Factual correctness - Company/sector/business context matches data
    5. Claim support - All statements backed by provided data (no external knowledge)

    Note: Logical consistency (interpretations matching data) is handled by ConsistencyScorer
    """

    def __init__(self):
        """Initialize faithfulness scorer"""
        pass

    def score_narrative(
        self,
        narrative: str,
        ground_truth: Dict,
        indicators: Dict,
        percentiles: Dict,
        news_data: List[Dict],
        ticker_data: Optional[Dict] = None
    ) -> FaithfulnessScore:
        """
        Score narrative faithfulness against ground truth

        Args:
            narrative: Generated Thai narrative text
            ground_truth: Ground truth data (market conditions, etc.)
            indicators: Technical indicators
            percentiles: Percentile data for historical context
            news_data: List of news items with [idx], title, sentiment
            ticker_data: Optional company data for factual correctness validation

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

        # 4. Check factual correctness (company/sector/business context)
        factual_score, factual_violations, factual_verified = self._check_factual_correctness(
            narrative, ticker_data
        )
        violations.extend(factual_violations)
        verified_claims.extend(factual_verified)

        # 5. Check claim support (all statements backed by data)
        claim_score, claim_violations, claim_verified = self._check_claim_support(
            narrative, news_data
        )
        violations.extend(claim_violations)
        verified_claims.extend(claim_verified)

        # Calculate overall score (weighted average)
        # Weights: Numeric 35%, Percentile 25%, News 20%, Factual 15%, Claim Support 5%
        overall_score = (
            numeric_score * 0.35 +
            percentile_score * 0.25 +
            news_score * 0.20 +
            factual_score * 0.15 +
            claim_score * 0.05
        )

        metric_scores = {
            'numeric_accuracy': numeric_score,
            'percentile_accuracy': percentile_score,
            'news_citation_accuracy': news_score,
            'factual_correctness': factual_score,
            'claim_support': claim_score
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


    def _check_factual_correctness(
        self,
        narrative: str,
        ticker_data: Optional[Dict]
    ) -> Tuple[float, List[str], List[str]]:
        """
        Check if company/sector/business context matches ticker_data.

        Validates semantic/factual correctness - ensures no external knowledge
        or incorrect business context is introduced.
        """
        violations = []
        verified = []

        if not ticker_data:
            # No ticker_data to validate against - score as neutral
            return 100.0, violations, verified

        # Check company name if present in narrative
        company_name = ticker_data.get('name', '')
        if company_name and company_name in narrative:
            verified.append(f"✓ Company name '{company_name}' correctly mentioned")
        elif company_name:
            # Check for potential wrong company name (difficult to detect, heuristic only)
            # Look for patterns like "บริษัท [name]" that don't match
            import re
            company_patterns = re.findall(r'บริษัท\s+([^\s]+(?:\s+[^\s]+){0,3})', narrative)
            for pattern in company_patterns:
                if company_name not in pattern and pattern not in company_name:
                    violations.append(f"❌ Mentioned company '{pattern}' but ticker data shows '{company_name}'")

        # Check sector/industry if present
        sector = ticker_data.get('sector', '')
        industry = ticker_data.get('industry', '')

        # Simple check: if narrative mentions sector/industry keywords, verify they're consistent
        # This is a basic heuristic - can be enhanced
        if sector:
            if sector.lower() in narrative.lower():
                verified.append(f"✓ Sector '{sector}' mentioned")

        if industry:
            if industry.lower() in narrative.lower():
                verified.append(f"✓ Industry '{industry}' mentioned")

        # Calculate score
        # If we have ticker_data and found violations, penalize
        if ticker_data and violations:
            score = max(0, 100 - len(violations) * 30)
        else:
            # No violations found, or no ticker_data to check
            score = 100.0

        return score, violations, verified

    def _check_claim_support(
        self,
        narrative: str,
        news_data: List[Dict]
    ) -> Tuple[float, List[str], List[str]]:
        """
        Check if all claims are backed by provided data (no external knowledge).

        Looks for unsupported claims like:
        - "Management announced..." without news backing it
        - "Company will expand to X countries" without data
        - External events not in news (e.g., "Following Fed rate cut")
        """
        violations = []
        verified = []

        # Keywords indicating potentially unsupported claims
        unsupported_keywords = [
            ('ประกาศ', 'announcement'),
            ('เปิดตัว', 'launch'),
            ('ควบรวม', 'merger'),
            ('เข้าซื้อ', 'acquisition'),
            ('ขยายไป', 'expansion'),
            ('เปิดสาขา', 'new branch'),
            ('Fed', 'Federal Reserve'),
            ('ธนาคารกลาง', 'central bank policy')
        ]

        # Check if narrative contains these keywords
        for thai_kw, eng_desc in unsupported_keywords:
            if thai_kw.lower() in narrative.lower():
                # Check if news_data supports this claim
                if news_data:
                    # Look for related keywords in news titles
                    supported = any(thai_kw.lower() in news.get('title', '').lower() for news in news_data)
                    if not supported:
                        violations.append(f"❌ Claim about '{eng_desc}' ('{thai_kw}') not backed by news data")
                    else:
                        verified.append(f"✓ Claim about '{eng_desc}' supported by news")
                else:
                    violations.append(f"❌ Claim about '{eng_desc}' ('{thai_kw}') but no news data provided")

        # Calculate score
        # High weight on violations - external knowledge is serious
        if violations:
            score = max(0, 100 - len(violations) * 40)
        else:
            score = 100.0

        return score, violations, verified

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
