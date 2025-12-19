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

    def __init__(self, language: str = 'th', context_builder=None):
        """Initialize PromptBuilder

        Args:
            language: Report language ('en' or 'th'), defaults to 'th'
            context_builder: Optional ContextBuilder instance for section presence detection
        """
        self.main_prompt_template = self._load_main_prompt_template(language)
        self.context_builder = context_builder

    def _load_main_prompt_template(self, language: str = 'th') -> str:
        """
        Load the main prompt template from disk.

        Args:
            language: Report language ('en' or 'th'), defaults to 'th'

        Returns:
            Main prompt template string

        Raises:
            FileNotFoundError: If template file doesn't exist
        """
        templates_dir = Path(__file__).parent / "prompt_templates" / language
        filepath = templates_dir / "main_prompt.txt"

        if not filepath.exists():
            raise FileNotFoundError(f"Main prompt template not found: {filepath}")

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
        """Route to language-specific implementation for complete separation

        This ensures editing Thai prompts has ZERO effect on English prompts.
        """
        return self._build_base_prompt_section_th()

    def _build_base_prompt_section_th(self) -> str:
        """Thai prompts with DEEMPHASIZED percentiles (as of 2025-12-15)

        Percentiles are presented as optional context, not mandatory requirements.
        """
        return """1. **Price Uncertainty** (use {{{{UNCERTAINTY}}}}/100 placeholder): Sets the overall market mood
   - Low (0-25): "ตลาดเสถียรมาก" - Stable, good for positioning
   - Moderate (25-50): "ตลาดค่อนข้างเสถียร" - Normal movement
   - High (50-75): "ตลาดผันผวนสูง" - High risk, be cautious
   - Extreme (75-100): "ตลาดผันผวนรุนแรง" - Extreme risk, warn strongly
   - Percentile information is optionally available if you find it relevant (e.g., "Uncertainty {{{{UNCERTAINTY}}}}/100 ซึ่งอยู่ในเปอร์เซ็นไทล์ {{{{UNCERTAINTY_SCORE_PERCENTILE}}}}%")

2. **Volatility (ATR %)**: The speed of price movement
   - Include the ATR% number and explain what it means
   - Example: "ATR 1.2% แสดงราคาเคลื่อนไหวช้ามั่นคง นักลงทุนเห็นตรงกัน"
   - Example: "ATR 3.8% แสดงตลาดลังเล ราคากระโดดขึ้นลง 3-5% ได้ง่าย"
   - Percentile context available if needed (e.g., "ATR 1.99% อยู่ในเปอร์เซ็นไทล์ 61%")

3. **Buy/Sell Pressure (Price vs VWAP %)**: Who's winning - buyers or sellers?
   - Include the % above/below VWAP and explain the implication
   - Example: "ราคา 22.4% เหนือ VWAP แสดงแรงซื้อแรงมาก คนซื้อวันนี้ยอมจ่ายแพงกว่าเฉลี่ย"
   - Example: "ราคา -2.8% ต่ำกว่า VWAP แสดงแรงขายหนัก คนขายรีบขายถูกกว่าเฉลี่ย"
   - Percentile available to show rarity if relevant (e.g., "ราคา 5% เหนือ VWAP ซึ่งอยู่ในเปอร์เซ็นไทล์ 90%")

4. **Volume (Volume Ratio)**: Is smart money interested?
   - Include the volume ratio (e.g., 0.8x, 1.5x, 2.0x) and explain what it means
   - Example: "ปริมาณซื้อขาย 1.8x ของเฉลี่ย แสดงนักลงทุนใหญ่กำลังเคลื่อนไหว"
   - Example: "ปริมาณซื้อขาย 0.7x ของเฉลี่ย แสดงนักลงทุนเฉยๆ รอดูก่อน"
   - Percentile frequency available (e.g., "ปริมาณ 1.03x อยู่ในเปอร์เซ็นไทล์ 71%")

5. **Statistical Context (Percentiles)**: Optional historical perspective on current values
   - Percentile information is available in the data if you want to add historical context
   - Use percentiles ONLY if they meaningfully enhance your narrative
   - This can tell the reader: "Is this value unusual compared to history?"
   - Examples (optional):
     * "RSI {{{{RSI}}}} ซึ่งอยู่ในเปอร์เซ็นไทล์ {{{{RSI_PERCENTILE}}}}%"
     * "MACD {{{{MACD}}}} อยู่ในเปอร์เซ็นไทล์ {{{{MACD_PERCENTILE}}}}%"
     * "Uncertainty {{{{UNCERTAINTY}}}}/100 อยู่ในเปอร์เซ็นไทล์ {{{{UNCERTAINTY_SCORE_PERCENTILE}}}}%"

6. **Fundamental Analysis (P/E, EPS, Market Cap, Growth)**: CRITICAL - You MUST incorporate fundamental metrics into your narrative
   - P/E Ratio: Compare to industry average (e.g., "P/E 44.58 สูงกว่าค่าเฉลี่ยของกลุ่มเทคโนโลยี - แสดงว่านักลงทุนยินดีจ่ายแพงสำหรับการเติบโตในอนาคต")
   - EPS: Discuss growth trajectory (e.g., "EPS 4.04 และการเติบโตของกำไรที่เกิน 60% แสดงถึงความแข็งแกร่งของบริษัท")
   - Market Cap: Provide context (e.g., "Market Cap $4384.6B ทำให้เป็นบริษัทขนาดใหญ่ - มีเสถียรภาพแต่การเติบโตอาจช้าลง")
   - Revenue Growth: Mention when significant (e.g., "Revenue Growth 60%+ แสดงว่าบริษัทกำลังขยายตัวเร็ว")
   - Profit Margin: Discuss efficiency (e.g., "Profit Margin สูงแสดงว่าบริษัทจัดการต้นทุนได้ดี")
   - Format: Weave fundamental metrics naturally into paragraphs - don't list them separately
   - Use fundamental data to support your BUY/SELL/HOLD recommendation
   - Example: "ในด้านพื้นฐาน P/E Ratio 44.58 สูงกว่าค่าเฉลี่ยของกลุ่ม แต่เมื่อพิจารณาการเติบโตของรายได้ที่ 60%+ และ Profit Margin ที่สูง แสดงว่าบริษัทมีศักยภาพที่จะเติบโตต่อไป"

7. **Chart Patterns & Advanced Technical Analysis (Financial Markets MCP)**: When chart pattern data is provided, USE IT to enhance technical analysis
   - Chart Patterns: Mention detected patterns (e.g., "พบรูปแบบ Head & Shoulders ซึ่งอาจบ่งชี้ถึงการเปลี่ยนทิศทางขาลง")
   - Candlestick Patterns: Discuss implications (e.g., "รูปแบบ Doji แสดงความลังเลของตลาด - นักลงทุนไม่แน่ใจทิศทาง")
   - Support/Resistance: Reference key levels (e.g., "ราคาตอนนี้อยู่ใกล้ระดับ Resistance ที่ $185 - หากทะลุได้อาจขึ้นต่อ")
   - Advanced Indicators: Mention when relevant (e.g., "Fibonacci Retracement แสดงว่าราคาอยู่ที่ 61.8% ซึ่งเป็นจุดสำคัญ")
   - Format: Integrate chart patterns into technical analysis narrative - don't create separate section
   - Use chart patterns to support your technical analysis and risk assessment
   - Example: "เมื่อดูจากรูปแบบกราฟ พบ Head & Shoulders pattern ซึ่งบ่งชี้ถึงการเปลี่ยนทิศทางขาลง ขณะที่ราคายังอยู่เหนือ Support ที่ $175 - หากราคาตกต่ำกว่าระดับนี้ อาจเป็นสัญญาณขาย"

These 7 elements (4 market conditions + statistical context + fundamental analysis + chart patterns) ARE the foundation of your narrative. Include specific numbers, and use percentiles ONLY if they add meaningful context."""


    def _build_strategy_section(self) -> str:
        """Build strategy performance section"""
        return """

8. **Strategy Performance (Historical Backtesting)**: When strategy performance data is provided, USE IT to support your recommendation
   - CRITICAL: Only include strategy performance when it ALIGNS with your BUY/SELL recommendation
   - Weave strategy performance naturally into your narrative with "narrative + number" style
   - DO NOT mention what strategy was used - just present the performance as evidence
   - Examples of how to incorporate:
     * For BUY recommendation: "หากคุณติดตามกลยุทธ์ของเรา การซื้อครั้งล่าสุดอยู่ที่ $175 และเมื่อดูจากสถิติการซื้อเท่านั้น (buy-only strategy) ในอดีต การเข้าตำแหน่งแบบนี้ให้ผลตอบแทนเฉลี่ย +15.2% โดยมี Sharpe ratio 1.2 และอัตราชนะ 62% - แสดงว่าจุดเข้าแบบนี้มีความเสี่ยงต่ำและให้ผลตอบแทนดี"
     * For SELL recommendation: "หากคุณติดตามกลยุทธ์ของเรา การขายครั้งล่าสุดอยู่ที่ $180 และเมื่อดูจากสถิติการขายเท่านั้น (sell-only strategy) ในอดีต การเข้าตำแหน่งแบบนี้ให้ผลตอบแทนเฉลี่ย +8.5% โดยมี Sharpe ratio 0.9 และอัตราชนะ 58% - แสดงว่าจุดเข้าแบบนี้มีความเสี่ยงปานกลางและให้ผลตอบแทนดี"
   - Include risk/reward metrics: "Max Drawdown -12.5% แสดงว่าในอดีต ตำแหน่งแบบนี้เสี่ยงสูงสุดที่จะขาดทุน 12.5% ก่อนจะกลับขึ้นมา"
   - Format: "หากคุณติดตามกลยุทธ์ของเรา, การซื้อ/ขายครั้งล่าสุดอยู่ที่ [price] และเมื่อดูจากสถิติการซื้อ/ขายเท่านั้น (buy-only/sell-only strategy) ในอดีต, การเข้าตำแหน่งแบบนี้ให้ผลตอบแทนเฉลี่ย [return]% โดยมี Sharpe ratio [sharpe] และอัตราชนะ [win_rate]% - แสดงว่า[interpretation]"
   - NEVER mention the strategy name (SMA crossing) - just say "กลยุทธ์ของเรา" or "strategies"
   - Use strategy data to strengthen your argument, not as standalone facts"""

    def _build_comparative_section(self) -> str:
        """Build comparative analysis section"""
        return """

9. **Comparative Analysis (Relative Performance)**: When comparative insights are provided, USE THEM to add relative context
   - CRITICAL: Weave comparative insights naturally into your narrative - don't create a separate section
   - Use comparative data to show how this ticker performs RELATIVE to peers
   - Examples of how to incorporate:
     * Similar tickers: "หุ้นนี้เคลื่อนไหวคล้ายกับ XYZ (correlation 0.85) และ ABC (correlation 0.78) - แสดงว่าอยู่ในกลุ่มเดียวกัน"
     * Volatility comparison: "ความผันผวนสูงกว่าค่าเฉลี่ยของหุ้นในกลุ่ม 25% - แสดงว่าหุ้นนี้มีความเสี่ยงสูงกว่าเพื่อนบ้าน"
     * Return comparison: "ผลตอบแทนต่ำกว่าค่าเฉลี่ยของกลุ่ม 15% - แสดงว่า underperform เมื่อเทียบกับเพื่อนร่วมกลุ่ม"
     * Cluster context: "อยู่ในกลุ่มเดียวกับ DEF, GHI - หุ้นในกลุ่มนี้มักจะ..."
   - Use comparative insights to strengthen your argument about whether the ticker is outperforming or underperforming its peers
   - Format examples:
     * "เมื่อเทียบกับหุ้นที่คล้ายกัน เช่น [ticker] (correlation [value]), หุ้นนี้มีความผันผวน[สูงกว่า/ต่ำกว่า]และให้ผลตอบแทน[ดีกว่า/แย่กว่า]"
     * "หุ้นนี้อยู่ในอันดับที่ [rank] จาก [total] ด้านความผันผวน - แสดงว่า[interpretation]"
   - NEVER create a separate "การวิเคราะห์เปรียบเทียบ" section - integrate naturally into the main narrative
   - Use comparative data as supporting evidence, not as standalone facts"""

    def build_prompt_structure(self, has_strategy: bool) -> str:
        """Build the report structure section"""
        strategy_integration = "\n- If strategy performance data is provided, weave it naturally into this section to support your analysis" if has_strategy else ""
        strategy_recommendation = "\n- If strategy performance data is provided and aligns with your recommendation, include it here to strengthen your argument (e.g., 'หากคุณติดตามกลยุทธ์ของเรา การซื้อครั้งล่าสุดอยู่ที่ $X และสถิติแสดงว่า...')" if has_strategy else ""
        
        return f"""

IMPORTANT: When high-impact news [1], [2] exists in the data, reference it naturally in your story when relevant. Don't force it - only use if it meaningfully affects the narrative.

Structure (in Thai):

📖 **เรื่องราวของหุ้นตัวนี้**
Write 2-3 sentences telling the STORY. MUST include: uncertainty score context + ATR% + VWAP% + volume ratio with their meanings. Include news naturally if relevant.

💡 **สิ่งที่คุณต้องรู้**
Write 3-4 flowing paragraphs (NOT numbered lists) that explain WHY this matters to an investor. MUST continuously reference:
- The 4 market condition elements (uncertainty, ATR, VWAP, volume) with numbers throughout
- Fundamental metrics (P/E ratio, EPS, Market Cap, Revenue Growth, Profit Margin) - CRITICAL: Mention at least 2-3 fundamental metrics
- Chart patterns from Financial Markets MCP (if available) - CRITICAL: Mention detected patterns and their implications
- Technical indicators (RSI, MACD, SMA trends)
- Comparative analysis (relative performance vs peers)
- News (when relevant)
Mix all elements seamlessly - don't section them.{strategy_integration}

🎯 **ควรทำอะไรตอนนี้?**
Give ONE clear action: BUY MORE / SELL / HOLD. Explain WHY in 2-3 sentences using uncertainty score + market conditions (ATR/VWAP/volume). Reference news if it changes the decision.{strategy_recommendation}

⚠️ **ระวังอะไร?**
Warn about 1-2 key risks using the 4 market condition metrics. What volatility/pressure/volume signals should trigger concern? Keep it practical.

Rules for narrative flow:
- Tell STORIES, don't list bullet points - write like you're texting a friend investor
- CRITICAL: ALWAYS include all 4 market condition metrics (uncertainty, ATR%, VWAP%, volume ratio) with specific numbers AND percentile context throughout
- Use numbers IN sentences as evidence, not as standalone facts
- Explain WHY things matter (implication), not just WHAT they are (description)
- Mix technical + fundamental + relative + news + statistical context + comparative analysis + chart patterns seamlessly - don't section them
- CRITICAL: MUST mention fundamental metrics (P/E, EPS, Market Cap, Growth) in "สิ่งที่คุณต้องรู้" section
- CRITICAL: MUST mention chart patterns from Financial Markets MCP (if available) in technical analysis discussion
- Reference news [1], [2] ONLY when it genuinely affects the story
- CRITICAL: When percentile data is available, USE IT to add historical context to numbers (e.g., "RSI 75 ซึ่งอยู่ในเปอร์เซ็นไทล์ 85%")
- Write under 12-15 lines total
- NO tables, NO numbered lists in the insight section, just flowing narrative

Write entirely in Thai, naturally flowing like Damodaran's style - narrative supported by numbers, not numbers with explanation."""

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
    
    def _format_percentile_context_th(self, percentiles: dict) -> str:
        """Thai percentile context - empty

        Following CLAUDE.md principle: complete separation instead of scattered conditionals.
        """
        return ""

    def _format_percentile_context(self, percentiles: dict) -> str:
        """Format percentile context based on language

        Router method that delegates to language-specific implementations.
        Following CLAUDE.md principle: language decision in ONE place.

        Uses self.language attribute to determine which implementation to call.
        """
        return self._format_percentile_context_th(percentiles)
