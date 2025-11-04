"""Number injection utilities for deterministic value replacement"""

from typing import Dict
import re


class NumberInjector:
    """Injects deterministic numbers into narrative placeholders"""
    
    def inject_deterministic_numbers(
        self,
        narrative: str,
        ground_truth: Dict,
        indicators: Dict,
        percentiles: Dict
    ) -> str:
        """
        Replace placeholders with exact ground truth values to ensure 100% faithfulness.

        This implements the Damodaran "narrative + number" approach where:
        - Numbers are deterministic (exact values from ground truth)
        - Narrative is LLM-generated (natural storytelling)

        Args:
            narrative: LLM-generated text with {{PLACEHOLDERS}}
            ground_truth: Calculated market conditions
            indicators: Technical indicators
            percentiles: Percentile data for historical context

        Returns:
            Narrative with all placeholders replaced by exact values
        """
        # Build replacement dictionary
        replacements = {
            '{{UNCERTAINTY}}': f"{ground_truth['uncertainty_score']:.1f}",
            '{{ATR_PCT}}': f"{ground_truth['atr_pct']:.2f}",
            '{{VWAP_PCT}}': f"{abs(ground_truth['vwap_pct']):.2f}",  # abs() for Thai text formatting
            '{{VOLUME_RATIO}}': f"{ground_truth['volume_ratio']:.2f}",
            '{{RSI}}': f"{indicators.get('rsi', 0):.2f}",
            '{{MACD}}': f"{indicators.get('macd', 0):.4f}",
            '{{CURRENT_PRICE}}': f"{indicators.get('current_price', 0):.2f}",
            '{{SMA_20}}': f"{indicators.get('sma_20', 0):.2f}",
            '{{SMA_50}}': f"{indicators.get('sma_50', 0):.2f}",
        }

        # Add percentile replacements
        for key, value in percentiles.items():
            percentile_val = value.get('percentile', 0) if isinstance(value, dict) else value
            placeholder = f"{{{{{key.upper()}_PERCENTILE}}}}"
            replacements[placeholder] = f"{percentile_val:.1f}"

        # Perform replacements
        result = narrative
        for placeholder, value in replacements.items():
            result = result.replace(placeholder, value)

        # Validation: Check if any placeholders remain (LLM forgot to use them)
        remaining = re.findall(r'\{\{[A-Z_]+\}\}', result)
        if remaining:
            print(f"??  Warning: Unused placeholders found: {remaining}")
            print(f"   LLM may have forgotten to use these placeholders")

        return result
