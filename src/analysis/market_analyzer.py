"""Market analysis utilities for calculating market conditions and interpretations"""

from typing import Dict


class MarketAnalyzer:
    """Analyzes market conditions and provides interpretations"""
    
    def calculate_market_conditions(self, indicators: Dict) -> Dict:
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
    
    def interpret_uncertainty_level(self, uncertainty_score: float) -> str:
        """Interpret uncertainty score into Thai description"""
        if uncertainty_score < 25:
            return "ตลาดเสถียรมาก - แรงซื้อขายสมดุล เหมาะสำหรับการวางแผนระยะยาว"
        elif uncertainty_score < 50:
            return "ตลาดค่อนข้างเสถียร - มีความเคลื่อนไหวปกติ เหมาะสำหรับการลงทุนทั่วไป"
        elif uncertainty_score < 75:
            return "ตลาดผันผวนสูง - แรงซื้อขายไม่สมดุล ต้องระวังการเปลี่ยนทิศทางอย่างกะทันหัน"
        else:
            return "ตลาดผันผวนรุนแรง - แรงซื้อขายชนกันหนัก เหมาะสำหรับมืออาชีพเท่านั้น"
    
    def interpret_volatility(self, atr: float, current_price: float) -> str:
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
    
    def interpret_vwap_pressure(self, price_vs_vwap_pct: float, vwap: float) -> str:
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
    
    def interpret_volume(self, volume_ratio: float) -> str:
        """Interpret volume ratio into Thai description"""
        if volume_ratio > 2.0:
            return f"ปริมาณซื้อขายระเบิด {volume_ratio:.1f}x ของค่าเฉลี่ย - มีเหตุการณ์สำคัญ นักลงทุนใหญ่กำลังเคลื่อนไหว"
        elif volume_ratio > 1.5:
            return f"ปริมาณซื้อขายสูง {volume_ratio:.1f}x ของค่าเฉลี่ย - ความสนใจเพิ่มขึ้นมาก"
        elif volume_ratio > 0.7:
            return f"ปริมาณซื้อขายปกติ ({volume_ratio:.1f}x ของค่าเฉลี่ย)"
        else:
            return f"ปริมาณซื้อขายเงียบ {volume_ratio:.1f}x ของค่าเฉลี่ย - นักลงทุนไม่ค่อยสนใจ อาจรอข่าวใหม่"
