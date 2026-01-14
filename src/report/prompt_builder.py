# -*- coding: utf-8 -*-
"""Prompt building utilities for LLM report generation"""

import logging
from pathlib import Path
from typing import Dict, Optional, Tuple, Any

from src.report.number_injector import NumberInjector
from src.integrations.prompt_service import get_prompt_service, PromptResult

# Setup logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class PromptBuilder:
    """Builds prompts for LLM report generation"""

    def __init__(self, context_builder=None):
        """Initialize PromptBuilder

        Args:
            context_builder: Optional ContextBuilder instance for section presence detection
        """
        self._prompt_service = get_prompt_service()
        self._prompt_result: Optional[PromptResult] = None
        self.main_prompt_template = self._load_main_prompt_template()
        self.context_builder = context_builder

    def _load_main_prompt_template(self) -> str:
        """
        Load the main prompt template from Langfuse or disk.

        Returns:
            Main prompt template string

        Raises:
            FileNotFoundError: If template file doesn't exist
        """
        # Use PromptService for Langfuse integration with file fallback
        self._prompt_result = self._prompt_service.get_prompt("report-generation")
        logger.info(f"📝 Prompt loaded: source={self._prompt_result.source}, version={self._prompt_result.version}")
        return self._prompt_result.content

    def get_prompt_metadata(self) -> Dict[str, Any]:
        """Get prompt metadata for Langfuse trace tracking.

        Returns:
            Dict with prompt_name, prompt_version, prompt_source for trace metadata

        Note:
            Call this after build_prompt() to attach metadata to Langfuse traces.
            This enables performance comparison between prompt versions.
        """
        if self._prompt_result:
            return {
                "prompt_name": self._prompt_result.name,
                "prompt_version": self._prompt_result.version,
                "prompt_source": self._prompt_result.source,
            }
        return {
            "prompt_name": "report-generation",
            "prompt_version": "unknown",
            "prompt_source": "unknown",
        }

    def _build_placeholder_list(self, placeholders, ground_truth=None, indicators=None,
                                percentiles=None, ticker_data=None,
                                comparative_insights=None, strategy_performance=None,
                                line_length=80):
        """Format placeholder list for template injection, filtering out unavailable data

        Args:
            placeholders: List of (name, suffix) tuples from NumberInjector
            ground_truth: Ground truth data for filtering (optional)
            indicators: Technical indicators for filtering (optional)
            percentiles: Percentile data for filtering (optional)
            ticker_data: Fundamental data for filtering (optional)
            comparative_insights: Comparative data for filtering (optional)
            strategy_performance: Strategy data for filtering (optional)
            line_length: Max characters per line before wrapping

        Returns:
            Formatted string with only available placeholders, or empty string if none available

        Example:
            Input: [('UNCERTAINTY', '/100'), ('ATR_PCT', '%')], with data available
            Output: "{UNCERTAINTY}/100, {ATR_PCT}%"

        Note:
            Uses single braces because this string is injected as a VALUE into
            the template, not as template code. Python .format() doesn't process
            escape sequences in injected values.
        """
        # Filter to only placeholders with actual data
        available_placeholders = []
        for name, suffix in placeholders:
            if self._has_value(
                name,
                ground_truth or {},
                indicators or {},
                percentiles or {},
                ticker_data or {},
                comparative_insights or {},
                strategy_performance or {}
            ):
                available_placeholders.append((name, suffix))

        # If no data available for this category, return empty string
        if not available_placeholders:
            return ""

        # Format available placeholders
        formatted = []
        for name, suffix in available_placeholders:
            # Single braces - this is injected as a value, not template code
            formatted.append(f"{{{name}}}{suffix}")

        # Join with comma-space, wrapping at line_length
        result = ", ".join(formatted)

        # Optional: Add line breaks for readability (every ~80 chars)
        if len(result) > line_length:
            # Split into chunks at comma boundaries
            lines = []
            current_line = ""
            for item in formatted:
                if len(current_line) + len(item) + 2 > line_length and current_line:
                    lines.append(current_line.rstrip(", "))
                    current_line = item + ", "
                else:
                    current_line += item + ", "
            if current_line:
                lines.append(current_line.rstrip(", "))
            result = "\n".join(lines)

        return result

    def _has_value(self, placeholder_name: str, ground_truth: dict, indicators: dict,
                   percentiles: dict, ticker_data: dict, comparative_insights: dict,
                   strategy_performance: dict) -> bool:
        """Check if placeholder has actual non-empty data

        Args:
            placeholder_name: Name of placeholder to check (e.g., 'UNCERTAINTY', 'RSI')
            ground_truth: Ground truth data (uncertainty, atr_pct, vwap_pct, volume_ratio)
            indicators: Technical indicators (rsi, macd, sma_20, etc.)
            percentiles: Percentile data
            ticker_data: Fundamental data (pe_ratio, eps, market_cap, etc.)
            comparative_insights: Comparative analysis data
            strategy_performance: Strategy performance data

        Returns:
            True if value exists and is meaningful (not None, not 0 for prices, not empty string)
        """
        # Risk metrics (from ground_truth)
        if placeholder_name in ['UNCERTAINTY', 'ATR_PCT', 'VWAP_PCT', 'VOLUME_RATIO']:
            key_map = {
                'UNCERTAINTY': 'uncertainty_score',
                'ATR_PCT': 'atr_pct',
                'VWAP_PCT': 'vwap_pct',
                'VOLUME_RATIO': 'volume_ratio'
            }
            value = ground_truth.get(key_map[placeholder_name])
            return value is not None and value != 0

        # Current price (from indicators)
        if placeholder_name == 'CURRENT_PRICE':
            value = indicators.get('current_price')
            return value is not None and value > 0

        # Momentum indicators (from indicators)
        if placeholder_name in ['RSI', 'MACD', 'MACD_SIGNAL']:
            key_map = {
                'RSI': 'rsi',
                'MACD': 'macd',
                'MACD_SIGNAL': 'macd_signal'
            }
            value = indicators.get(key_map[placeholder_name])
            return value is not None

        # Trend indicators (from indicators)
        if placeholder_name in ['SMA_20', 'SMA_50', 'SMA_200', 'EMA_12', 'EMA_26']:
            key = placeholder_name.lower()
            value = indicators.get(key)
            return value is not None and value > 0

        # Volatility indicators (from indicators)
        if placeholder_name in ['ATR', 'BOLLINGER_UPPER', 'BOLLINGER_LOWER', 'BOLLINGER_MIDDLE']:
            key = placeholder_name.lower()
            value = indicators.get(key)
            return value is not None and value > 0

        # Volume indicators (from indicators)
        if placeholder_name == 'VWAP':
            value = indicators.get('vwap')
            return value is not None and value > 0

        # Fundamentals (from ticker_data)
        if placeholder_name in ['PE_RATIO', 'EPS', 'MARKET_CAP', 'REVENUE_GROWTH',
                                'PROFIT_MARGIN', 'DIVIDEND_YIELD', 'ROE', 'DEBT_TO_EQUITY',
                                'CURRENT_RATIO', 'BOOK_VALUE', '52_WEEK_HIGH', '52_WEEK_LOW',
                                'TARGET_PRICE', 'BETA']:
            key_map = {
                'PE_RATIO': 'pe_ratio',
                'EPS': 'eps',
                'MARKET_CAP': 'market_cap',
                'REVENUE_GROWTH': 'revenue_growth',
                'PROFIT_MARGIN': 'profit_margin',
                'DIVIDEND_YIELD': 'dividend_yield',
                'ROE': 'return_on_equity',
                'DEBT_TO_EQUITY': 'debt_to_equity',
                'CURRENT_RATIO': 'current_ratio',
                'BOOK_VALUE': 'book_value',
                '52_WEEK_HIGH': 'fifty_two_week_high',
                '52_WEEK_LOW': 'fifty_two_week_low',
                'TARGET_PRICE': 'target_mean_price',
                'BETA': 'beta',
            }
            value = ticker_data.get(key_map.get(placeholder_name, ''))
            return value is not None and value != 'N/A' and value != ''

        # Comparative (from comparative_insights)
        if placeholder_name in ['PERFORMANCE_ADVANTAGE', 'VOLATILITY_ADVANTAGE',
                                'COMPARATIVE_RETURN', 'PEER_COUNT']:
            key = placeholder_name.lower()
            value = comparative_insights.get(key) if comparative_insights else None
            return value is not None and value != 'N/A'

        # Strategy (from strategy_performance)
        if placeholder_name.startswith('STRATEGY_'):
            if not strategy_performance:
                return False

            # Map placeholder to strategy data path
            if 'BUY' in placeholder_name:
                data = strategy_performance.get('buy_only', {})
            elif 'SELL' in placeholder_name:
                data = strategy_performance.get('sell_only', {})
            elif 'LAST_BUY' in placeholder_name:
                data = strategy_performance.get('last_buy_signal', {})
            elif 'LAST_SELL' in placeholder_name:
                data = strategy_performance.get('last_sell_signal', {})
            else:
                return False

            return bool(data)  # True if dict is non-empty

        # Percentiles (from percentiles)
        if placeholder_name.endswith('_PERCENTILE'):
            # Remove _PERCENTILE suffix and map to percentile key
            base_name = placeholder_name.replace('_PERCENTILE', '').lower()

            # Handle name standardization (reverse mapping)
            key_map = {
                'uncertainty': 'uncertainty_score',
                'atr_pct': 'atr_percent',
            }
            key = key_map.get(base_name, base_name)

            value = percentiles.get(key) if percentiles else None
            if isinstance(value, dict):
                percentile_val = value.get('percentile')
                return percentile_val is not None
            return value is not None

        # Default: assume not available
        return False

    def _load_section_template(self, template_name: str) -> str:
        """Load a section template from disk

        Args:
            template_name: Name of the template file (without .txt extension)

        Returns:
            Template content as string

        Raises:
            FileNotFoundError: If template file doesn't exist
        """
        templates_dir = Path(__file__).parent / "prompt_templates" / "th" / "single-stage"
        filepath = templates_dir / f"{template_name}.txt"

        if not filepath.exists():
            raise FileNotFoundError(f"Section template not found: {filepath}")

        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()

    def build_prompt(self, ticker: str, context: str,
                    ground_truth: dict = None,
                    indicators: dict = None,
                    percentiles: dict = None,
                    ticker_data: dict = None,
                    strategy_performance: dict = None,
                    comparative_insights: dict = None,
                    sec_filing_data: dict = None,
                    financial_markets_data: dict = None,
                    portfolio_insights: dict = None,
                    alpaca_data: dict = None) -> str:
        """Build LLM prompt with dynamic placeholder filtering

        Args:
            ticker: Stock ticker symbol
            context: Context string from ContextBuilder
            ground_truth: Ground truth data (uncertainty, atr_pct, vwap_pct, volume_ratio) for filtering
            indicators: Technical indicators (rsi, macd, sma_20, etc.) for filtering
            percentiles: Percentile data for filtering
            ticker_data: Fundamental data (pe_ratio, eps, market_cap, etc.) for filtering
            strategy_performance: Strategy performance data (for section presence detection)
            comparative_insights: Comparative insights data (for section presence detection)
            sec_filing_data: SEC filing data (for section presence detection)
            financial_markets_data: Financial Markets MCP data (for section presence detection)
            portfolio_insights: Portfolio Manager MCP data (for section presence detection)
            alpaca_data: Alpaca MCP data (for section presence detection)
        """
        logger.info("🔨 [PromptBuilder] Building prompt from template with dynamic filtering")
        logger.info(f"   📊 Input parameters:")
        logger.info(f"      - Context length: {len(context)} characters")

        # Default to empty dicts if not provided
        ground_truth = ground_truth or {}
        indicators = indicators or {}
        percentiles = percentiles or {}
        ticker_data = ticker_data or {}
        comparative_insights = comparative_insights or {}
        strategy_performance = strategy_performance or {}

        # Get section presence from context builder if available, otherwise use direct checks
        if self.context_builder:
            section_presence = self.context_builder.get_section_presence(
                strategy_performance=strategy_performance,
                comparative_insights=comparative_insights,
                sec_filing_data=sec_filing_data,
                financial_markets_data=financial_markets_data,
                portfolio_insights=portfolio_insights,
                alpaca_data=alpaca_data
            )
            has_strategy = section_presence.get('strategy', False)
        else:
            # Fallback: use direct check (backward compatibility)
            has_strategy = bool(strategy_performance)
            section_presence = {'strategy': has_strategy}

        logger.info(f"      - Strategy performance included: {has_strategy}")

        # Get placeholder definitions from NumberInjector (single source of truth)
        placeholder_defs = NumberInjector.get_placeholder_definitions()

        # Build filtered placeholder lists (only include available data)
        risk_vars = self._build_placeholder_list(
            placeholder_defs['risk_metrics'],
            ground_truth=ground_truth,
            indicators=indicators
        )

        momentum_vars = self._build_placeholder_list(
            placeholder_defs['momentum_indicators'],
            indicators=indicators
        )

        trend_vars = self._build_placeholder_list(
            placeholder_defs['trend_indicators'],
            indicators=indicators
        )

        volatility_vars = self._build_placeholder_list(
            placeholder_defs['volatility_indicators'],
            indicators=indicators
        )

        volume_vars = self._build_placeholder_list(
            placeholder_defs['volume_indicators'],
            indicators=indicators
        )

        fundamental_vars = self._build_placeholder_list(
            placeholder_defs['fundamentals'],
            ticker_data=ticker_data
        )

        comparative_vars = self._build_placeholder_list(
            placeholder_defs['comparative'],
            comparative_insights=comparative_insights
        )

        strategy_vars = self._build_placeholder_list(
            placeholder_defs['strategy'],
            strategy_performance=strategy_performance
        )

        percentiles_vars = self._build_placeholder_list(
            placeholder_defs['percentiles'],
            percentiles=percentiles
        )

        # Log what's available
        logger.info("   📊 Available placeholder categories:")
        logger.info(f"      - Risk metrics: {len(risk_vars.split(',')) if risk_vars else 0} variables")
        logger.info(f"      - Momentum: {len(momentum_vars.split(',')) if momentum_vars else 0} variables")
        logger.info(f"      - Trend: {len(trend_vars.split(',')) if trend_vars else 0} variables")
        logger.info(f"      - Volatility: {len(volatility_vars.split(',')) if volatility_vars else 0} variables")
        logger.info(f"      - Volume: {len(volume_vars.split(',')) if volume_vars else 0} variables")
        logger.info(f"      - Fundamentals: {len(fundamental_vars.split(',')) if fundamental_vars else 0} variables")
        logger.info(f"      - Comparative: {len(comparative_vars.split(',')) if comparative_vars else 0} variables")
        logger.info(f"      - Strategy: {len(strategy_vars.split(',')) if strategy_vars else 0} variables")
        logger.info(f"      - Percentiles: {len(percentiles_vars.split(',')) if percentiles_vars else 0} variables")

        # Log template variables for v4 minimal (single template approach)
        logger.info("━" * 70)
        logger.info("📝 TEMPLATE VARIABLE VALUES (v4 dynamic placeholders):")
        logger.info("━" * 70)
        logger.info("")
        logger.info(f"   {{TICKER}} = {ticker}")
        logger.info("")
        logger.info("   {CONTEXT} =")
        logger.info(f"{context[:500]}...")  # Show first 500 chars
        logger.info("")
        logger.info(f"   {{RISK_METRICS}} = {risk_vars[:100] if risk_vars else '(no data)'}...")
        logger.info(f"   {{FUNDAMENTAL_VARIABLES}} = {fundamental_vars[:100] if fundamental_vars else '(no data)'}...")
        logger.info(f"   {{PERCENTILES_VARIABLES}} = {percentiles_vars[:100] if percentiles_vars else '(no data)'}...")
        logger.info("")
        logger.info("━" * 70)

        # Format template with variables (empty categories show fallback message)
        final_prompt = self.main_prompt_template.format(
            TICKER=ticker,
            CONTEXT=context,
            RISK_METRICS=risk_vars or "(no data available)",
            MOMENTUM_INDICATORS=momentum_vars or "(no data available)",
            TREND_INDICATORS=trend_vars or "(no data available)",
            VOLATILITY_INDICATORS=volatility_vars or "(no data available)",
            VOLUME_INDICATORS=volume_vars or "(no data available)",
            FUNDAMENTAL_VARIABLES=fundamental_vars or "(no data available)",
            COMPARATIVE_VARIABLES=comparative_vars or "(optional - not available)",
            STRATEGY_VARIABLES=strategy_vars or "(optional - not available)",
            PERCENTILES_VARIABLES=percentiles_vars or "(optional - not available)"
        )
        
        # Log final prompt summary
        logger.info(f"   ✅ Final prompt built:")
        logger.info(f"      - Total length: {len(final_prompt)} characters (~{len(final_prompt) // 4} tokens estimated)")
        logger.info(f"      - First 200 chars: {final_prompt[:200]}...")
        logger.info(f"      - Last 200 chars: ...{final_prompt[-200:]}")
        
        # Log full prompt content (split into chunks if too long for single log line)
        logger.info("   📄 Full prompt content:")
        # Split into chunks of ~8000 chars to avoid CloudWatch log line limits
        chunk_size = 8000
        for i in range(0, len(final_prompt), chunk_size):
            chunk = final_prompt[i:i + chunk_size]
            chunk_num = (i // chunk_size) + 1
            total_chunks = (len(final_prompt) + chunk_size - 1) // chunk_size
            if total_chunks > 1:
                logger.info(f"      [Chunk {chunk_num}/{total_chunks}]:\n{chunk}")
            else:
                logger.info(f"      {chunk}")
        
        return final_prompt
    
    def _build_base_prompt_section(self) -> str:
        """Build narrative elements section from template"""
        return self._load_section_template("narrative_elements")


    def _build_strategy_section(self) -> str:
        """Build strategy performance section from template"""
        return self._load_section_template("strategy_section")

    def _build_comparative_section(self) -> str:
        """Build comparative analysis section from template"""
        return self._load_section_template("comparative_section")

    def build_prompt_structure(self, has_strategy: bool) -> str:
        """Build the report structure section from template"""
        template = self._load_section_template("prompt_structure")
        
        # Handle dynamic parts (strategy integration)
        strategy_integration = "\n- If strategy performance data is provided, weave it naturally into this section to support your analysis" if has_strategy else ""
        strategy_recommendation = "\n- If strategy performance data is provided and aligns with your recommendation, include it here to strengthen your argument (e.g., 'หากคุณติดตามกลยุทธ์ของเรา การซื้อครั้งล่าสุดอยู่ที่ $X และสถิติแสดงว่า...')" if has_strategy else ""
        
        return template.format(
            STRATEGY_INTEGRATION=strategy_integration,
            STRATEGY_RECOMMENDATION=strategy_recommendation
        )

    def _calculate_market_conditions(self, indicators: dict) -> dict:
        """Calculate market condition metrics"""
        current_price = indicators.get('current_price', 0)
        current_volume = indicators.get('volume', 0)
        volume_sma = indicators.get('volume_sma', 0)
        uncertainty_score = indicators.get('uncertainty_score', 0)
        atr = indicators.get('atr', 0)
        vwap = indicators.get('vwap', 0)
        
        # Calculate buy/sell pressure indicators
        price_vs_vwap_pct = ((current_price - vwap) / vwap) * 100 if vwap and vwap > 0 else 0
        volume_ratio = current_volume / volume_sma if volume_sma and volume_sma > 0 else 1.0
        
        return {
            'current_price': current_price,
            'uncertainty_score': uncertainty_score,
            'atr': atr,
            'vwap': vwap,
            'price_vs_vwap_pct': price_vs_vwap_pct,
            'volume_ratio': volume_ratio
        }
    
    def _interpret_uncertainty_level(self, uncertainty_score: float) -> str:
        """Interpret uncertainty score into Thai description"""
        if uncertainty_score < 25:
            return "ตลาดเสถียรมาก - แรงซื้อขายสมดุล เหมาะสำหรับการวางแผนระยะยาว"
        elif uncertainty_score < 50:
            return "ตลาดค่อนข้างเสถียร - มีความเคลื่อนไหวปกติ เหมาะสำหรับการลงทุนทั่วไป"
        elif uncertainty_score < 75:
            return "ตลาดผันผวนสูง - แรงซื้อขายไม่สมดุล ต้องระวังการเปลี่ยนทิศทางอย่างกะทันหัน"
        else:
            return "ตลาดผันผวนรุนแรง - แรงซื้อขายชนกันหนัก เหมาะสำหรับมืออาชีพเท่านั้น"
    
    def _interpret_volatility(self, atr: float, current_price: float) -> str:
        """Interpret ATR volatility into Thai description"""
        if atr and current_price > 0:
            atr_percent = (atr / current_price) * 100
            if atr_percent < 1:
                return f"ความผันผวนต่ำมาก (ATR {atr_percent:.2f}%) - ราคาเคลื่อนไหวช้า มั่นคง"
            elif atr_percent < 2:
                return f"ความผันผวนปานกลาง (ATR {atr_percent:.2f}%) - ราคาเคลื่อนไหวปกติ"
            elif atr_percent < 4:
                return f"ความผันผวนสูง (ATR {atr_percent:.2f}%) - ราคาแกว่งตัวรุนแรง อาจขึ้นลง 3-5% ได้ง่าย"
            else:
                return f"ความผันผวนสูงมาก (ATR {atr_percent:.2f}%) - ราคาแกว่งตัวมาก อาจขึ้นลง 5-10% ภายในวัน"
        return "ไม่สามารถวัดความผันผวนได้"
    
    def _interpret_vwap_pressure(self, price_vs_vwap_pct: float, vwap: float) -> str:
        """Interpret VWAP pressure into Thai description"""
        if price_vs_vwap_pct > 3:
            return f"แรงซื้อแรงมาก - ราคา {price_vs_vwap_pct:.1f}% เหนือ VWAP ({vwap:.2f}) คนซื้อยอมจ่ายแพงกว่าราคาเฉลี่ย แสดงความต้องการสูง"
        elif price_vs_vwap_pct > 1:
            return f"แรงซื้อดี - ราคา {price_vs_vwap_pct:.1f}% เหนือ VWAP ({vwap:.2f}) มีความต้องการซื้อเหนือกว่า"
        elif price_vs_vwap_pct > -1:
            return f"แรงซื้อขายสมดุล - ราคาใกล้เคียง VWAP ({vwap:.2f}) ตลาดยังไม่มีทิศทางชัด"
        elif price_vs_vwap_pct > -3:
            return f"แรงขายเริ่มมี - ราคา {abs(price_vs_vwap_pct):.1f}% ต่ำกว่า VWAP ({vwap:.2f}) มีแรงกดดันขาย"
        else:
            return f"แรงขายหนัก - ราคา {abs(price_vs_vwap_pct):.1f}% ต่ำกว่า VWAP ({vwap:.2f}) คนขายยอมขายถูกกว่าเฉลี่ย แสดงความตื่นตระหนก"
    
    def _interpret_volume(self, volume_ratio: float) -> str:
        """Interpret volume ratio into Thai description"""
        if volume_ratio > 2.0:
            return f"ปริมาณซื้อขายระเบิด {volume_ratio:.1f}x ของค่าเฉลี่ย - มีเหตุการณ์สำคัญ นักลงทุนใหญ่กำลังเคลื่อนไหว"
        elif volume_ratio > 1.5:
            return f"ปริมาณซื้อขายสูง {volume_ratio:.1f}x ของค่าเฉลี่ย - ความสนใจเพิ่มขึ้นมาก"
        elif volume_ratio > 0.7:
            return f"ปริมาณซื้อขายปกติ ({volume_ratio:.1f}x ของค่าเฉลี่ย)"
        else:
            return f"ปริมาณซื้อขายเงียบ {volume_ratio:.1f}x ของค่าเฉลี่ย - นักลงทุนไม่ค่อยสนใจ อาจรอข่าวใหม่"
    
