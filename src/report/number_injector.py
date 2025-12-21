"""Number injection utilities for deterministic value replacement"""

from typing import Dict
import re


class NumberInjector:
    """Injects deterministic numbers into narrative placeholders"""

    @staticmethod
    def get_placeholder_definitions():
        """Return available placeholders grouped by category with display syntax

        This is the single source of truth for what placeholders exist.
        Used by PromptBuilder to dynamically generate the <placeholders> section.

        Returns:
            Dict with categories containing (placeholder_name, suffix) tuples

        Example:
            ('UNCERTAINTY', '/100') → renders as {UNCERTAINTY}/100
            ('ATR_PCT', '%') → renders as {ATR_PCT}%
        """
        return {
            'risk_metrics': [  # Renamed from 'market_conditions'
                ('UNCERTAINTY', '/100'),
                ('ATR_PCT', '%'),
                ('VWAP_PCT', '%'),
                ('VOLUME_RATIO', 'x'),
                ('CURRENT_PRICE', ''),
            ],
            'momentum_indicators': [  # Extracted from old 'market_conditions'
                ('RSI', ''),
                ('MACD', ''),
                ('MACD_SIGNAL', ''),
            ],
            'trend_indicators': [  # Split from 'technical_indicators'
                ('SMA_20', ''),
                ('SMA_50', ''),
                ('SMA_200', ''),
                ('EMA_12', ''),
                ('EMA_26', ''),
            ],
            'volatility_indicators': [  # New category
                ('ATR', ''),  # Raw form (different from ATR_PCT)
                ('BOLLINGER_UPPER', ''),
                ('BOLLINGER_LOWER', ''),
                ('BOLLINGER_MIDDLE', ''),
            ],
            'volume_indicators': [  # New category
                ('VWAP', ''),  # Raw form (different from VWAP_PCT)
            ],
            'fundamentals': [  # Unchanged
                ('PE_RATIO', ''),
                ('EPS', ''),
                ('MARKET_CAP', ''),
                ('REVENUE_GROWTH', '%'),
                ('PROFIT_MARGIN', '%'),
                ('DIVIDEND_YIELD', '%'),
                ('ROE', '%'),
                ('DEBT_TO_EQUITY', ''),
                ('CURRENT_RATIO', ''),
                ('BOOK_VALUE', ''),
                ('52_WEEK_HIGH', ''),
                ('52_WEEK_LOW', ''),
                ('TARGET_PRICE', ''),
                ('BETA', ''),
            ],
            'comparative': [  # Unchanged
                ('PERFORMANCE_ADVANTAGE', ''),
                ('VOLATILITY_ADVANTAGE', ''),
                ('COMPARATIVE_RETURN', ''),
                ('PEER_COUNT', ''),
            ],
            'strategy': [  # Unchanged
                ('STRATEGY_BUY_RETURN', ''),
                ('STRATEGY_BUY_SHARPE', ''),
                ('STRATEGY_BUY_WIN_RATE', ''),
                ('STRATEGY_BUY_DRAWDOWN', ''),
                ('STRATEGY_SELL_RETURN', ''),
                ('STRATEGY_SELL_SHARPE', ''),
                ('STRATEGY_SELL_WIN_RATE', ''),
                ('STRATEGY_SELL_DRAWDOWN', ''),
                ('STRATEGY_LAST_BUY_PRICE', ''),
                ('STRATEGY_LAST_SELL_PRICE', ''),
            ],
            'percentiles': [
                # Risk metrics percentiles (standardized names)
                ('UNCERTAINTY_PERCENTILE', '%'),      # Was: UNCERTAINTY_SCORE_PERCENTILE
                ('ATR_PCT_PERCENTILE', '%'),          # Was: ATR_PERCENT_PERCENTILE
                ('VWAP_PCT_PERCENTILE', '%'),         # NEW - added for completeness
                ('VOLUME_RATIO_PERCENTILE', '%'),     # Unchanged

                # Momentum indicators percentiles
                ('RSI_PERCENTILE', '%'),              # Unchanged
                ('MACD_PERCENTILE', '%'),             # NEW
                ('MACD_SIGNAL_PERCENTILE', '%'),      # NEW

                # Trend indicators percentiles
                ('SMA_20_PERCENTILE', '%'),           # NEW
                ('SMA_50_PERCENTILE', '%'),           # NEW
                ('SMA_200_PERCENTILE', '%'),          # NEW
                ('EMA_12_PERCENTILE', '%'),           # NEW
                ('EMA_26_PERCENTILE', '%'),           # NEW

                # Volatility indicators percentiles
                ('ATR_PERCENTILE', '%'),              # NEW (raw ATR, different from ATR_PCT)
                ('BOLLINGER_UPPER_PERCENTILE', '%'),  # NEW
                ('BOLLINGER_LOWER_PERCENTILE', '%'),  # NEW
                ('BOLLINGER_MIDDLE_PERCENTILE', '%'), # NEW

                # Volume indicators percentiles
                ('VWAP_PERCENTILE', '%'),             # NEW (raw VWAP, different from VWAP_PCT)
            ]
        }

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
            # TECHNICAL INDICATORS (v4 uses single braces)
            '{UNCERTAINTY}': f"{ground_truth.get('uncertainty_score', 0):.1f}",
            '{ATR_PCT}': f"{ground_truth.get('atr_pct', 0):.2f}",
            '{VWAP_PCT}': f"{abs(ground_truth.get('vwap_pct', 0)):.2f}",
            '{VOLUME_RATIO}': f"{ground_truth.get('volume_ratio', 0):.2f}",
            '{RSI}': f"{indicators.get('rsi', 0):.2f}",
            '{MACD}': f"{indicators.get('macd', 0):.4f}",
            '{MACD_SIGNAL}': f"{indicators.get('macd_signal', 0):.4f}",
            '{CURRENT_PRICE}': f"{indicators.get('current_price', 0):.2f}",
            '{SMA_20}': f"{indicators.get('sma_20', 0):.2f}",
            '{SMA_50}': f"{indicators.get('sma_50', 0):.2f}",
            '{SMA_200}': f"{indicators.get('sma_200', 0):.2f}",
            '{EMA_12}': f"{indicators.get('ema_12', 0):.2f}",
            '{EMA_26}': f"{indicators.get('ema_26', 0):.2f}",
            '{BOLLINGER_UPPER}': f"{indicators.get('bollinger_upper', 0):.2f}",
            '{BOLLINGER_LOWER}': f"{indicators.get('bollinger_lower', 0):.2f}",
            '{BOLLINGER_MIDDLE}': f"{indicators.get('bollinger_middle', 0):.2f}",
            '{ATR}': f"{indicators.get('atr', 0):.2f}",
            '{VWAP}': f"{indicators.get('vwap', 0):.2f}",

            # FUNDAMENTAL DATA (safe even if ticker_data = {})
            '{PE_RATIO}': f"{ticker_data.get('pe_ratio', 'N/A')}",
            '{EPS}': f"{ticker_data.get('eps', 'N/A')}",
            '{MARKET_CAP}': format_large_number(ticker_data.get('market_cap')),
            '{DIVIDEND_YIELD}': format_percentage(ticker_data.get('dividend_yield')),
            '{PROFIT_MARGIN}': format_percentage(ticker_data.get('profit_margin')),
            '{REVENUE_GROWTH}': format_percentage(ticker_data.get('revenue_growth')),
            '{OPERATING_MARGIN}': format_percentage(ticker_data.get('operating_margin')),
            '{ROE}': format_percentage(ticker_data.get('return_on_equity')),
            '{ROA}': format_percentage(ticker_data.get('return_on_assets')),
            '{DEBT_TO_EQUITY}': f"{ticker_data.get('debt_to_equity', 'N/A')}",
            '{CURRENT_RATIO}': f"{ticker_data.get('current_ratio', 'N/A')}",
            '{BOOK_VALUE}': f"{ticker_data.get('book_value', 'N/A')}",
            '{52_WEEK_HIGH}': f"{ticker_data.get('fifty_two_week_high', 'N/A')}",
            '{52_WEEK_LOW}': f"{ticker_data.get('fifty_two_week_low', 'N/A')}",
            '{TARGET_PRICE}': f"{ticker_data.get('target_mean_price', 'N/A')}",
            '{BETA}': f"{ticker_data.get('beta', 'N/A')}",

            # COMPARATIVE DATA (safe even if comparative_insights = {})
            '{PERFORMANCE_ADVANTAGE}': f"{comparative_insights.get('performance_advantage', 'N/A')}",
            '{VOLATILITY_ADVANTAGE}': f"{comparative_insights.get('volatility_advantage', 'N/A')}",
            '{COMPARATIVE_RETURN}': f"{comparative_insights.get('comparative_return', 'N/A')}",
            '{PEER_COUNT}': f"{comparative_insights.get('peer_count', 'N/A')}",
        }
        
        # Add strategy performance replacements if available
        if strategy_performance:
            buy_only = strategy_performance.get('buy_only', {})
            sell_only = strategy_performance.get('sell_only', {})
            last_buy_signal = strategy_performance.get('last_buy_signal', {})
            last_sell_signal = strategy_performance.get('last_sell_signal', {})
            
            # Buy-only strategy placeholders (v4 uses single braces)
            if buy_only:
                replacements['{STRATEGY_BUY_RETURN}'] = f"{buy_only.get('total_return_pct', 0):.2f}"
                replacements['{STRATEGY_BUY_SHARPE}'] = f"{buy_only.get('sharpe_ratio', 0):.2f}"
                replacements['{STRATEGY_BUY_WIN_RATE}'] = f"{buy_only.get('win_rate', 0):.1f}"
                replacements['{STRATEGY_BUY_DRAWDOWN}'] = f"{abs(buy_only.get('max_drawdown_pct', 0)):.2f}"

            # Sell-only strategy placeholders (v4 uses single braces)
            if sell_only:
                replacements['{STRATEGY_SELL_RETURN}'] = f"{sell_only.get('total_return_pct', 0):.2f}"
                replacements['{STRATEGY_SELL_SHARPE}'] = f"{sell_only.get('sharpe_ratio', 0):.2f}"
                replacements['{STRATEGY_SELL_WIN_RATE}'] = f"{sell_only.get('win_rate', 0):.1f}"
                replacements['{STRATEGY_SELL_DRAWDOWN}'] = f"{abs(sell_only.get('max_drawdown_pct', 0)):.2f}"

            # Last signal placeholders (v4 uses single braces)
            if last_buy_signal:
                buy_price = last_buy_signal.get('price', 0) if isinstance(last_buy_signal, dict) else last_buy_signal
                replacements['{STRATEGY_LAST_BUY_PRICE}'] = f"{buy_price:.2f}"

            if last_sell_signal:
                sell_price = last_sell_signal.get('price', 0) if isinstance(last_sell_signal, dict) else last_sell_signal
                replacements['{STRATEGY_LAST_SELL_PRICE}'] = f"{sell_price:.2f}"

        # Add percentile replacements with standardized naming (v4 uses single braces)
        for key, value in percentiles.items():
            percentile_val = value.get('percentile', 0) if isinstance(value, dict) else value

            # Standardize key names to match placeholder definitions
            standardized_key = key.upper()

            # Map old names to new standardized names
            name_mapping = {
                'UNCERTAINTY_SCORE': 'UNCERTAINTY',
                'ATR_PERCENT': 'ATR_PCT',
            }
            standardized_key = name_mapping.get(standardized_key, standardized_key)

            placeholder = f"{{{standardized_key}_PERCENTILE}}"
            replacements[placeholder] = f"{percentile_val:.1f}"

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

        return result
