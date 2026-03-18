"""Number injection utilities for deterministic value replacement"""

import logging
from typing import Dict, Optional
import re

from src.report.metric_registry import MetricRegistry, get_metric_registry

logger = logging.getLogger(__name__)


class NumberInjector:
    """Injects deterministic numbers into narrative placeholders.

    Delegates metric definitions and replacement dict building to MetricRegistry.
    Keeps post-processing (malformed placeholder cleanup, validation) here.
    """

    def __init__(self, registry: Optional[MetricRegistry] = None):
        self._registry = registry

    @property
    def registry(self) -> MetricRegistry:
        if self._registry is not None:
            return self._registry
        return get_metric_registry()

    @staticmethod
    def get_placeholder_definitions(registry: Optional[MetricRegistry] = None):
        """Return available placeholders grouped by category with display syntax.

        Delegates to MetricRegistry. Only READY metrics are included.

        Returns:
            Dict with categories containing (placeholder_name, suffix) tuples
        """
        reg = registry or get_metric_registry()
        return reg.get_placeholder_definitions()

    def inject_deterministic_numbers(
        self,
        narrative: str,
        ground_truth: Dict,
        indicators: Dict,
        percentiles: Dict,
        ticker_data: Dict,
        comparative_insights: Dict,
        strategy_performance: Dict = None
    ) -> str:
        """
        Replace placeholders with exact ground truth values to ensure 100% faithfulness.

        This implements the Damodaran "narrative + number" approach where:
        - Numbers are deterministic (exact values from ground truth)
        - Narrative is LLM-generated (natural storytelling)

        Delegates replacement dict building to MetricRegistry (only READY metrics).
        Keeps post-processing (malformed placeholder cleanup, validation) here.

        Args:
            narrative: LLM-generated text with {{PLACEHOLDERS}}
            ground_truth: Calculated market conditions (pass {} if unavailable)
            indicators: Technical indicators (pass {} if unavailable)
            percentiles: Percentile data for historical context (pass {} if unavailable)
            ticker_data: Fundamental data - P/E, EPS, market cap, etc. (pass {} if unavailable)
            comparative_insights: Peer comparison metrics (pass {} if unavailable)
            strategy_performance: Strategy backtest data (pass {} or None if unavailable)

        Returns:
            Narrative with all placeholders replaced by exact values
        """
        # Build replacement dict from registry (only READY metrics)
        replacements = self.registry.build_replacement_dict(
            ground_truth=ground_truth,
            indicators=indicators,
            percentiles=percentiles,
            ticker_data=ticker_data,
            comparative_insights=comparative_insights,
            strategy_performance=strategy_performance,
        )

        # Check if LLM produced any placeholders at all (v4 uses single braces)
        all_placeholders = re.findall(r'\{[A-Z_0-9]+\}', narrative)
        if not all_placeholders:
            print("━" * 70)
            print("⚠️  WARNING: LLM did not produce any {PLACEHOLDERS}")
            print("━" * 70)
            print("   Expected: LLM writes placeholders like {UNCERTAINTY}, {ATR_PCT}, {PE_RATIO}")
            print("   Actual:   LLM wrote actual numbers directly in the narrative")
            print("")
            print("   This breaks the Damodaran 'narrative + number' approach:")
            print("   - Numbers should come from ground truth (deterministic)")
            print("   - LLM-generated numbers may be inaccurate or hallucinated")
            print("")
            print("   Possible causes:")
            print("   1. Prompt instructions not strong enough")
            print("   2. LLM model ignoring format instructions")
            print("   3. Context data too visible (LLM copies numbers directly)")
            print("")
            print("   Solutions:")
            print("   - Try different LLM model (Claude, Gemini)")
            print("   - Implement placeholder normalization (Option 2)")
            print("   - Hide numbers from context (show only structure)")
            print("━" * 70)

        # Normalize placeholder variants before replacement.
        # LLM may write {{VAR}}, {{{VAR}}}, or bare VAR instead of {VAR}.
        # Normalize all to {VAR} so the replacement loop catches them.
        known_names = sorted(
            {m.placeholder for m in self.registry.get_ready_metrics()},
            key=len, reverse=True  # longest first: ATR_PCT_PERCENTILE before ATR_PCT before ATR
        )
        normalized_count = 0
        result = narrative
        for name in known_names:
            # Negative lookahead (?![A-Z_]) prevents matching {ATR inside {ATR_PCT}.
            # \b alone is insufficient because {ATR_PCT} has no word boundary after ATR.
            lookahead = r'(?![A-Z_0-9])'
            if '_' in name:
                pattern = re.compile(r'\{*\b' + re.escape(name) + lookahead + r'\b\}*')
            else:
                pattern = re.compile(r'\{+' + re.escape(name) + lookahead + r'\}*|\{*' + re.escape(name) + lookahead + r'\}+')
            normalized_form = '{' + name + '}'
            for match in pattern.finditer(result):
                if match.group() != normalized_form:
                    normalized_count += 1
            result = pattern.sub(normalized_form, result)

        if normalized_count > 0:
            logger.info(f"🔧 Normalized {normalized_count} placeholder variant(s) to single-brace form")

        # Pre-injection diagnostic: compare what LLM used vs what we can replace
        llm_used = set(re.findall(r'\{[A-Z_0-9]+\}', result))
        dict_has = set(replacements.keys())
        gap = llm_used - dict_has
        if gap:
            logger.warning(f"⚠️ PRE-INJECTION GAP: LLM wrote {len(gap)} placeholder(s) "
                           f"not in replacement dict: {sorted(gap)}")

        # Perform replacements and track successes
        self.last_replacements = dict(replacements)  # Save for scorer (placeholder → formatted value)
        successful_injections = []

        for placeholder, value in sorted(replacements.items(), key=lambda x: len(x[0]), reverse=True):
            if placeholder in result:
                result = result.replace(placeholder, str(value))
                successful_injections.append(f"{placeholder} → {value}")
            else:
                # Placeholder not found in narrative (not used by LLM)
                continue

        # Log successful injections
        if successful_injections:
            print("━" * 70)
            print(f"✅ Successfully injected {len(successful_injections)} placeholder(s):")
            print("━" * 70)
            for injection in successful_injections:
                print(f"   {injection}")
            print("━" * 70)

        # POST-PROCESSING FIX: Remove braces from malformed placeholders
        # LLM sometimes writes {51.3} instead of {UNCERTAINTY} - this cleans it up
        # Pattern: {number} where number can be: 51.3, 0.79, 14.033248, 155.71B, etc.
        malformed_pattern = r'\{([\d.]+[A-Z]?)\}'  # Matches {51.3}, {155.71B}, etc.
        malformed = re.findall(malformed_pattern, result)

        if malformed:
            print("━" * 70)
            print(f"🔧 POST-PROCESSING FIX: Cleaning {len(malformed)} malformed placeholder(s)")
            print("━" * 70)
            print("   LLM wrote numbers inside braces instead of placeholder names")
            print("   Converting: {51.3}/100 → 51.3/100")
            print("")
            for match in set(malformed):  # Use set to avoid duplicates in log
                print(f"   Fixing: {{{match}}} → {match}")
            print("━" * 70)

            # Remove braces around numbers
            result = re.sub(malformed_pattern, r'\1', result)

        # Validation: Check if any placeholders remain (v4 uses single braces)
        # Catches: {UPPERCASE}, {Mixed Case}, {with spaces}, {with-dashes}
        remaining = re.findall(r'\{[A-Z_0-9]+\}', result)
        if remaining:
            # Filter out expected placeholders that might not be in replacement dict
            unexpected = [p for p in remaining if not any(
                skip in p for skip in ['USER_FACING', 'CITE:', 'DATA:']
            )]
            if unexpected:
                print(f"⚠️  Warning: Unused placeholders found: {unexpected}")
                print(f"   These placeholders are not defined in NumberInjector")
                print(f"   LLM may have invented them or they need to be added to the replacement dict")

        # Store metrics for observability (Langfuse placeholder_compliance score)
        self.last_metrics = {
            'normalized_count': normalized_count,
            'injected_count': len(successful_injections),
            'unresolved_count': len(remaining),
            'orphan_suffix_count': len(re.findall(r'[\d.-]+_[A-Z_]+\}+', result)),
        }

        return result
