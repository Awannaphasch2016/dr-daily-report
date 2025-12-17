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
        percentiles: Dict,
        ticker_data: Dict,
        comparative_insights: Dict
    ) -> str:
        """
        Replace placeholders with exact ground truth values to ensure 100% faithfulness.

        This implements the Damodaran "narrative + number" approach where:
        - Numbers are deterministic (exact values from ground truth)
        - Narrative is LLM-generated (natural storytelling)

        Design: All parameters are required. Pass empty dict {} if data unavailable.
        The string.replace() method is selective - only replaces placeholders that
        exist in the narrative, so it's safe to build the full replacement dict
        regardless of what placeholders are actually used.

        Args:
            narrative: LLM-generated text with {{PLACEHOLDERS}}
            ground_truth: Calculated market conditions (pass {} if unavailable)
            indicators: Technical indicators (pass {} if unavailable)
            percentiles: Percentile data for historical context (pass {} if unavailable)
            ticker_data: Fundamental data - P/E, EPS, market cap, etc. (pass {} if unavailable)
            comparative_insights: Peer comparison metrics (pass {} if unavailable)

        Returns:
            Narrative with all placeholders replaced by exact values
        """
        # Helper functions for formatting
        def format_large_number(value):
            """Format large numbers with K/M/B/T suffixes"""
            if value is None or value == 'N/A':
                return 'N/A'
            try:
                val = float(value)
                if val >= 1e12:
                    return f"{val/1e12:.2f}T"
                elif val >= 1e9:
                    return f"{val/1e9:.2f}B"
                elif val >= 1e6:
                    return f"{val/1e6:.2f}M"
                else:
                    return f"{val:,.0f}"
            except (ValueError, TypeError):
                return str(value)

        def format_percentage(value):
            """Format percentage values (handles both 0.05 and 5.0 formats)"""
            if value is None or value == 'N/A':
                return 'N/A'
            try:
                val = float(value)
                return f"{val*100:.2f}" if val < 1 else f"{val:.2f}"
            except (ValueError, TypeError):
                return str(value)

        # Build COMPLETE replacement dictionary
        # Note: It's safe to always build all placeholders because string.replace()
        # only replaces what exists in the narrative
        replacements = {
            # TECHNICAL INDICATORS
            '{{UNCERTAINTY}}': f"{ground_truth.get('uncertainty_score', 0):.1f}",
            '{{ATR_PCT}}': f"{ground_truth.get('atr_pct', 0):.2f}",
            '{{VWAP_PCT}}': f"{abs(ground_truth.get('vwap_pct', 0)):.2f}",
            '{{VOLUME_RATIO}}': f"{ground_truth.get('volume_ratio', 0):.2f}",
            '{{RSI}}': f"{indicators.get('rsi', 0):.2f}",
            '{{MACD}}': f"{indicators.get('macd', 0):.4f}",
            '{{MACD_SIGNAL}}': f"{indicators.get('macd_signal', 0):.4f}",
            '{{CURRENT_PRICE}}': f"{indicators.get('current_price', 0):.2f}",
            '{{SMA_20}}': f"{indicators.get('sma_20', 0):.2f}",
            '{{SMA_50}}': f"{indicators.get('sma_50', 0):.2f}",
            '{{SMA_200}}': f"{indicators.get('sma_200', 0):.2f}",
            '{{EMA_12}}': f"{indicators.get('ema_12', 0):.2f}",
            '{{EMA_26}}': f"{indicators.get('ema_26', 0):.2f}",
            '{{BOLLINGER_UPPER}}': f"{indicators.get('bollinger_upper', 0):.2f}",
            '{{BOLLINGER_LOWER}}': f"{indicators.get('bollinger_lower', 0):.2f}",
            '{{BOLLINGER_MIDDLE}}': f"{indicators.get('bollinger_middle', 0):.2f}",
            '{{ATR}}': f"{indicators.get('atr', 0):.2f}",
            '{{VWAP}}': f"{indicators.get('vwap', 0):.2f}",

            # FUNDAMENTAL DATA (safe even if ticker_data = {})
            '{{PE_RATIO}}': f"{ticker_data.get('pe_ratio', 'N/A')}",
            '{{EPS}}': f"{ticker_data.get('eps', 'N/A')}",
            '{{MARKET_CAP}}': format_large_number(ticker_data.get('market_cap')),
            '{{DIVIDEND_YIELD}}': format_percentage(ticker_data.get('dividend_yield')),
            '{{PROFIT_MARGIN}}': format_percentage(ticker_data.get('profit_margin')),
            '{{REVENUE_GROWTH}}': format_percentage(ticker_data.get('revenue_growth')),
            '{{OPERATING_MARGIN}}': format_percentage(ticker_data.get('operating_margin')),
            '{{ROE}}': format_percentage(ticker_data.get('return_on_equity')),
            '{{ROA}}': format_percentage(ticker_data.get('return_on_assets')),
            '{{DEBT_TO_EQUITY}}': f"{ticker_data.get('debt_to_equity', 'N/A')}",
            '{{CURRENT_RATIO}}': f"{ticker_data.get('current_ratio', 'N/A')}",
            '{{BOOK_VALUE}}': f"{ticker_data.get('book_value', 'N/A')}",
            '{{52_WEEK_HIGH}}': f"{ticker_data.get('fifty_two_week_high', 'N/A')}",
            '{{52_WEEK_LOW}}': f"{ticker_data.get('fifty_two_week_low', 'N/A')}",
            '{{TARGET_PRICE}}': f"{ticker_data.get('target_mean_price', 'N/A')}",
            '{{BETA}}': f"{ticker_data.get('beta', 'N/A')}",

            # COMPARATIVE DATA (safe even if comparative_insights = {})
            '{{PERFORMANCE_ADVANTAGE}}': f"{comparative_insights.get('performance_advantage', 'N/A')}",
            '{{VOLATILITY_ADVANTAGE}}': f"{comparative_insights.get('volatility_advantage', 'N/A')}",
            '{{COMPARATIVE_RETURN}}': f"{comparative_insights.get('comparative_return', 'N/A')}",
            '{{PEER_COUNT}}': f"{comparative_insights.get('peer_count', 'N/A')}",
        }

        # Add percentile replacements (dynamic based on available percentiles)
        for key, value in percentiles.items():
            percentile_val = value.get('percentile', 0) if isinstance(value, dict) else value
            placeholder = f"{{{{{key.upper()}_PERCENTILE}}}}"
            replacements[placeholder] = f"{percentile_val:.1f}"

        # Check if LLM produced any placeholders at all
        all_placeholders = re.findall(r'\{\{[^}]+\}\}', narrative)
        if not all_placeholders:
            print("━" * 70)
            print("⚠️  WARNING: LLM did not produce any {{PLACEHOLDERS}}")
            print("━" * 70)
            print("   Expected: LLM writes placeholders like {{UNCERTAINTY}}, {{ATR_PCT}}, {{PE_RATIO}}")
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

        # Perform replacements and track successes
        result = narrative
        successful_injections = []

        for placeholder, value in replacements.items():
            if placeholder in narrative:
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

        # Validation: Check if any placeholders remain (comprehensive regex)
        # Catches: {{UPPERCASE}}, {{Mixed Case}}, {{with spaces}}, {{with-dashes}}
        remaining = re.findall(r'\{\{[^}]+\}\}', result)
        if remaining:
            # Filter out expected placeholders that might not be in replacement dict
            unexpected = [p for p in remaining if not any(
                skip in p for skip in ['USER_FACING', 'CITE:', 'DATA:']
            )]
            if unexpected:
                print(f"⚠️  Warning: Unused placeholders found: {unexpected}")
                print(f"   These placeholders are not defined in NumberInjector")
                print(f"   LLM may have invented them or they need to be added to the replacement dict")

        return result
