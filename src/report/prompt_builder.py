"""Prompt building utilities for LLM report generation"""

from typing import Dict, Optional


class PromptBuilder:
    """Builds prompts for LLM report generation"""
    
    def build_prompt(self, context: str, uncertainty_score: float, strategy_performance: dict = None) -> str:
        """Build LLM prompt with optional strategy performance data"""
        base_intro = f"""You are a world-class financial analyst like Aswath Damodaran. Write in Thai, but think like him - tell stories with data, don't just list numbers.

Data:
{context}

Write a narrative-driven report that answers: "Should I BUY MORE?", "Should I SELL?", or "Should I HOLD?" and WHY?

Your job is to weave TECHNICAL + FUNDAMENTAL + RELATIVE + NEWS + STATISTICAL CONTEXT into a flowing narrative that tells the STORY of this stock right now.

🔢 CRITICAL: USE PLACEHOLDERS FOR ALL NUMBERS (Damodaran "narrative + number" approach)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
To ensure 100% accuracy, NEVER write actual numbers. ALWAYS use placeholders:

Market Conditions:
  - Uncertainty: {{{{UNCERTAINTY}}}}/100 (NOT "52/100")
  - ATR: {{{{ATR_PCT}}}}% (NOT "1.30%")
  - VWAP: {{{{VWAP_PCT}}}}% (NOT "22.06%")
  - Volume: {{{{VOLUME_RATIO}}}}x (NOT "0.87x")
  - RSI: {{{{RSI}}}} (NOT "65.36")
  - MACD: {{{{MACD}}}} (NOT "6.32")
  - Price: ${{{{CURRENT_PRICE}}}} (NOT "$53.93")

Percentiles:
  - RSI Percentile: {{{{RSI_PERCENTILE}}}}% (NOT "88.5%")
  - Uncertainty Percentile: {{{{UNCERTAINTY_SCORE_PERCENTILE}}}}% (NOT "66.0%")
  - ATR Percentile: {{{{ATR_PERCENT_PERCENTILE}}}}% (NOT "75.2%")
  - VWAP Percentile: {{{{PRICE_VWAP_PERCENT_PERCENTILE}}}}% (NOT "92.1%")
  - Volume Percentile: {{{{VOLUME_RATIO_PERCENTILE}}}}% (NOT "45.3%")

Examples:
  ❌ BAD: "ความไม่แน่นอน 52/100 ซึ่งอยู่ในเปอร์เซ็นไทล์ 66%"
  ✅ GOOD: "ความไม่แน่นอน {{{{UNCERTAINTY}}}}/100 ซึ่งอยู่ในเปอร์เซ็นไทล์ {{{{UNCERTAINTY_SCORE_PERCENTILE}}}}%"

  ❌ BAD: "ATR 1.30% อยู่ในเปอร์เซ็นไทล์ 75%"
  ✅ GOOD: "ATR {{{{ATR_PCT}}}}% อยู่ในเปอร์เซ็นไทล์ {{{{ATR_PERCENT_PERCENTILE}}}}%"

  ❌ BAD: "ราคา 22.06% เหนือ VWAP"
  ✅ GOOD: "ราคา {{{{VWAP_PCT}}}}% เหนือ VWAP"

Write naturally - just replace numbers with {{{{PLACEHOLDERS}}}}. The system will fill in exact values automatically.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

CRITICAL NARRATIVE ELEMENTS - You MUST weave these "narrative + number + historical context" components into your story:

"""

        narrative_elements = self._build_base_prompt_section(uncertainty_score)
        strategy_section = self._build_strategy_section() if strategy_performance else ""
        comparative_section = self._build_comparative_section()
        structure = self.build_prompt_structure(bool(strategy_performance))

        return base_intro + narrative_elements + strategy_section + comparative_section + structure
    
    def _build_base_prompt_section(self, uncertainty_score: float) -> str:
        """Build the base narrative elements section"""
        return f"""1. **Price Uncertainty** ({uncertainty_score:.0f}/100): Sets the overall market mood
   - Low (0-25): "ตลาดเสถียรมาก" - Stable, good for positioning
   - Moderate (25-50): "ตลาดค่อนข้างเสถียร" - Normal movement
   - High (50-75): "ตลาดผันผวนสูง" - High risk, be cautious
   - Extreme (75-100): "ตลาดผันผวนรุนแรง" - Extreme risk, warn strongly
   - **IMPORTANT**: Use percentile information to add historical context (e.g., "Uncertainty 52/100 ซึ่งอยู่ในเปอร์เซ็นไทล์ 88% - แสดงว่าความไม่แน่นอนนี้สูงกว่าปกติเมื่อเทียบกับประวัติศาสตร์")

2. **Volatility (ATR %)**: The speed of price movement
   - Include the ATR% number and explain what it means
   - Example: "ATR 1.2% แสดงราคาเคลื่อนไหวช้ามั่นคง นักลงทุนเห็นตรงกัน"
   - Example: "ATR 3.8% แสดงตลาดลังเล ราคากระโดดขึ้นลง 3-5% ได้ง่าย"
   - **IMPORTANT**: Use percentile context (e.g., "ATR 1.99% อยู่ในเปอร์เซ็นไทล์ 61% - สูงกว่าค่าเฉลี่ยปกติเล็กน้อย")

3. **Buy/Sell Pressure (Price vs VWAP %)**: Who's winning - buyers or sellers?
   - Include the % above/below VWAP and explain the implication
   - Example: "ราคา 22.4% เหนือ VWAP แสดงแรงซื้อแรงมาก คนซื้อวันนี้ยอมจ่ายแพงกว่าเฉลี่ย"
   - Example: "ราคา -2.8% ต่ำกว่า VWAP แสดงแรงขายหนัก คนขายรีบขายถูกกว่าเฉลี่ย"
   - **IMPORTANT**: Use percentile to show rarity (e.g., "ราคา 5% เหนือ VWAP ซึ่งอยู่ในเปอร์เซ็นไทล์ 90% - แสดงแรงซื้อที่ผิดปกติมากในอดีต")

4. **Volume (Volume Ratio)**: Is smart money interested?
   - Include the volume ratio (e.g., 0.8x, 1.5x, 2.0x) and explain what it means
   - Example: "ปริมาณซื้อขาย 1.8x ของเฉลี่ย แสดงนักลงทุนใหญ่กำลังเคลื่อนไหว"
   - Example: "ปริมาณซื้อขาย 0.7x ของเฉลี่ย แสดงนักลงทุนเฉยๆ รอดูก่อน"
   - **IMPORTANT**: Use percentile frequency (e.g., "ปริมาณ 1.03x อยู่ในเปอร์เซ็นไทล์ 71% - สูงกว่าปกติ แต่ไม่ใช่ระดับที่ผิดปกติ")

5. **Statistical Context (Percentiles)**: Historical perspective on current values
   - CRITICAL: You MUST incorporate percentile information naturally into your narrative
   - This tells the reader: "Is this value unusual compared to history?"
   - Examples:
     * "RSI 81.12 ซึ่งอยู่ในเปอร์เซ็นไทล์ 94% - สูงมากในอดีต ควรระวังภาวะ Overbought"
     * "MACD 6.32 อยู่ในเปอร์เซ็นไทล์ 77% - สูงกว่าปกติ แสดงแรงซื้อแรงมาก"
     * "Uncertainty 52/100 อยู่ในเปอร์เซ็นไทล์ 88% - ความไม่แน่นอนนี้สูงกว่าปกติในอดีต"
   - Frequency percentages help explain rarity:
     * "RSI นี้สูงกว่า 70% ได้แค่ 28% ของเวลาในอดีต - แสดงภาวะ Overbought ที่หายาก"
     * "Volume 1.03x แต่ในอดีตเคยสูงถึง 2x ได้แค่ 1.9% ของเวลา - ปริมาณปัจจุบันยังไม่ใช่ระดับผิดปกติ"

These 5 elements (4 market conditions + statistical context) ARE the foundation of your narrative. ALWAYS include specific numbers WITH historical context (percentiles) - this is the "narrative + number + history" Damodaran style."""

    def _build_strategy_section(self) -> str:
        """Build strategy performance section"""
        return """

6. **Strategy Performance (Historical Backtesting)**: When strategy performance data is provided, USE IT to support your recommendation
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

7. **Comparative Analysis (Relative Performance)**: When comparative insights are provided, USE THEM to add relative context
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
Write 3-4 flowing paragraphs (NOT numbered lists) that explain WHY this matters to an investor. MUST continuously reference the 4 market condition elements (uncertainty, ATR, VWAP, volume) with numbers throughout. Mix technical + fundamental + relative + news seamlessly.{strategy_integration}

🎯 **ควรทำอะไรตอนนี้?**
Give ONE clear action: BUY MORE / SELL / HOLD. Explain WHY in 2-3 sentences using uncertainty score + market conditions (ATR/VWAP/volume). Reference news if it changes the decision.{strategy_recommendation}

⚠️ **ระวังอะไร?**
Warn about 1-2 key risks using the 4 market condition metrics. What volatility/pressure/volume signals should trigger concern? Keep it practical.

Rules for narrative flow:
- Tell STORIES, don't list bullet points - write like you're texting a friend investor
- CRITICAL: ALWAYS include all 4 market condition metrics (uncertainty, ATR%, VWAP%, volume ratio) with specific numbers AND percentile context throughout
- Use numbers IN sentences as evidence, not as standalone facts
- Explain WHY things matter (implication), not just WHAT they are (description)
- Mix technical + fundamental + relative + news + statistical context + comparative analysis seamlessly - don't section them
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
    
    def _format_percentile_context(self, percentiles: dict) -> str:
        """Format percentile context for prompt"""
        if not percentiles:
            return ""
        
        context = "\n\nการวิเคราะห์เปอร์เซ็นไทล์ (Percentile Analysis - เปรียบเทียบกับประวัติศาสตร์):\n"
        
        if 'rsi' in percentiles:
            rsi_stats = percentiles['rsi']
            context += f"- RSI: {rsi_stats['current_value']:.2f} (เปอร์เซ็นไทล์: {rsi_stats['percentile']:.1f}% - สูงกว่าค่าเฉลี่ย {rsi_stats['mean']:.2f})\n"
            context += f"  ความถี่ที่ RSI > 70: {rsi_stats['frequency_above_70']:.1f}% | ความถี่ที่ RSI < 30: {rsi_stats['frequency_below_30']:.1f}%\n"
        
        if 'macd' in percentiles:
            macd_stats = percentiles['macd']
            context += f"- MACD: {macd_stats['current_value']:.4f} (เปอร์เซ็นไทล์: {macd_stats['percentile']:.1f}%)\n"
            context += f"  ความถี่ที่ MACD > 0: {macd_stats['frequency_positive']:.1f}%\n"
        
        if 'uncertainty_score' in percentiles:
            unc_stats = percentiles['uncertainty_score']
            context += f"- Uncertainty Score: {unc_stats['current_value']:.2f}/100 (เปอร์เซ็นไทล์: {unc_stats['percentile']:.1f}%)\n"
            context += f"  ความถี่ที่ต่ำ (<25): {unc_stats['frequency_low']:.1f}% | ความถี่ที่สูง (>75): {unc_stats['frequency_high']:.1f}%\n"
        
        if 'atr_percent' in percentiles:
            atr_stats = percentiles['atr_percent']
            context += f"- ATR %: {atr_stats['current_value']:.2f}% (เปอร์เซ็นไทล์: {atr_stats['percentile']:.1f}%)\n"
            context += f"  ความถี่ที่ความผันผวนต่ำ (<1%): {atr_stats['frequency_low_volatility']:.1f}% | ความถี่ที่ความผันผวนสูง (>4%): {atr_stats['frequency_high_volatility']:.1f}%\n"
        
        if 'price_vwap_percent' in percentiles:
            vwap_stats = percentiles['price_vwap_percent']
            context += f"- Price vs VWAP %: {vwap_stats['current_value']:.2f}% (เปอร์เซ็นไทล์: {vwap_stats['percentile']:.1f}%)\n"
            context += f"  ความถี่ที่ราคาเหนือ VWAP >3%: {vwap_stats['frequency_above_3pct']:.1f}% | ความถี่ที่ราคาต่ำกว่า VWAP <-3%: {vwap_stats['frequency_below_neg3pct']:.1f}%\n"
        
        if 'volume_ratio' in percentiles:
            vol_stats = percentiles['volume_ratio']
            context += f"- Volume Ratio: {vol_stats['current_value']:.2f}x (เปอร์เซ็นไทล์: {vol_stats['percentile']:.1f}%)\n"
            context += f"  ความถี่ที่ปริมาณสูง (>2x): {vol_stats['frequency_high_volume']:.1f}% | ความถี่ที่ปริมาณต่ำ (<0.7x): {vol_stats['frequency_low_volume']:.1f}%\n"
        
        context += "\n**IMPORTANT**: Use these percentile values naturally in your narrative to add historical context. Don't just list them - weave them into the story!"
        return context

