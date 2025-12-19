# -*- coding: utf-8 -*-
"""Prompt building utilities for LLM report generation"""

import logging
from pathlib import Path
from typing import Dict, Optional

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
        self.main_prompt_template = self._load_main_prompt_template()
        self.context_builder = context_builder

    def _load_main_prompt_template(self) -> str:
        """
        Load the main prompt template from disk.

        Returns:
            Main prompt template string

        Raises:
            FileNotFoundError: If template file doesn't exist
        """
        templates_dir = Path(__file__).parent / "prompt_templates" / "th"
        filepath = templates_dir / "main_prompt.txt"

        if not filepath.exists():
            raise FileNotFoundError(f"Main prompt template not found: {filepath}")

        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()

    def _load_section_template(self, template_name: str) -> str:
        """Load a section template from disk

        Args:
            template_name: Name of the template file (without .txt extension)

        Returns:
            Template content as string

        Raises:
            FileNotFoundError: If template file doesn't exist
        """
        templates_dir = Path(__file__).parent / "prompt_templates" / "th"
        filepath = templates_dir / f"{template_name}.txt"

        if not filepath.exists():
            raise FileNotFoundError(f"Section template not found: {filepath}")

        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()

    def build_prompt(self, context: str, strategy_performance: dict = None,
                    comparative_insights: dict = None,
                    sec_filing_data: dict = None,
                    financial_markets_data: dict = None,
                    portfolio_insights: dict = None,
                    alpaca_data: dict = None) -> str:
        """Build LLM prompt using template file
        
        Args:
            context: Context string from ContextBuilder
            strategy_performance: Strategy performance data (for section presence detection)
            comparative_insights: Comparative insights data (for section presence detection)
            sec_filing_data: SEC filing data (for section presence detection)
            financial_markets_data: Financial Markets MCP data (for section presence detection)
            portfolio_insights: Portfolio Manager MCP data (for section presence detection)
            alpaca_data: Alpaca MCP data (for section presence detection)
        """
        logger.info("🔨 [PromptBuilder] Building prompt from template")
        logger.info(f"   📊 Input parameters:")
        logger.info(f"      - Context length: {len(context)} characters")
        
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

        # Build all sections using unified pattern
        narrative_elements = self._build_base_prompt_section()
        strategy_section = self._build_strategy_section() if has_strategy else ""
        comparative_section = self._build_comparative_section()
        structure = self.build_prompt_structure(has_strategy)

        # Log section details
        logger.info(f"   📋 Prompt sections:")
        logger.info(f"      - Template loaded: {len(self.main_prompt_template)} chars")
        logger.info(f"      - Narrative elements: {len(narrative_elements)} chars")
        logger.info(f"      - Strategy section: {len(strategy_section)} chars {'(included)' if strategy_section else '(excluded)'}")
        logger.info(f"      - Comparative section: {len(comparative_section)} chars")
        logger.info(f"      - Structure: {len(structure)} chars")

        # Log each template variable content for debugging
        logger.info("━" * 70)
        logger.info("📝 TEMPLATE VARIABLE VALUES (what gets injected into main_prompt.txt):")
        logger.info("━" * 70)
        logger.info("")
        logger.info("   {CONTEXT} =")
        logger.info(f"{context}")
        logger.info("")
        logger.info("   {NARRATIVE_ELEMENTS} =")
        logger.info(f"{narrative_elements}")
        logger.info("")
        if strategy_section:
            logger.info("   {STRATEGY_SECTION} =")
            logger.info(f"{strategy_section}")
            logger.info("")
        logger.info("   {COMPARATIVE_SECTION} =")
        logger.info(f"{comparative_section}")
        logger.info("")
        logger.info("   {PROMPT_STRUCTURE} =")
        logger.info(f"{structure}")
        logger.info("")
        logger.info("━" * 70)

        # Format template with variables (replaces hardcoded concatenation)
        final_prompt = self.main_prompt_template.format(
            CONTEXT=context,
            NARRATIVE_ELEMENTS=narrative_elements,
            STRATEGY_SECTION=strategy_section,
            COMPARATIVE_SECTION=comparative_section,
            PROMPT_STRUCTURE=structure
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
    
