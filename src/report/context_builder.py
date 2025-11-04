"""Context building utilities for LLM report generation"""

from typing import Dict, List, Optional
from src.analysis import MarketAnalyzer
from src.formatters import DataFormatter
from src.technical_analysis import TechnicalAnalyzer


class ContextBuilder:
    """Builds context for LLM report generation"""
    
    def __init__(self, market_analyzer: MarketAnalyzer, data_formatter: DataFormatter, technical_analyzer: TechnicalAnalyzer):
        """Initialize with required dependencies"""
        self.market_analyzer = market_analyzer
        self.data_formatter = data_formatter
        self.technical_analyzer = technical_analyzer
    
    def prepare_context(self, ticker: str, ticker_data: dict, indicators: dict, percentiles: dict, news: list, news_summary: dict, strategy_performance: dict = None, comparative_insights: dict = None) -> str:
        """Prepare context for LLM with uncertainty components and percentile information"""
        conditions = self.market_analyzer.calculate_market_conditions(indicators)
        current_price = conditions['current_price']
        
        uncertainty_level = self.market_analyzer.interpret_uncertainty_level(conditions['uncertainty_score'])
        volatility_desc = self.market_analyzer.interpret_volatility(conditions['atr'], current_price)
        vwap_desc = self.market_analyzer.interpret_vwap_pressure(conditions['price_vs_vwap_pct'], conditions['vwap'])
        volume_desc = self.market_analyzer.interpret_volume(conditions['volume_ratio'])
        percentile_context = self.data_formatter.format_percentile_context(percentiles)
        fundamental_section = self.data_formatter.format_fundamental_section(ticker_data)
        technical_section = self.data_formatter.format_technical_section(indicators, current_price, self.technical_analyzer)
        news_section = self.data_formatter.format_news_section(news, news_summary)
        
        # Add comparative insights
        comparative_insights = comparative_insights or {}
        comparative_section = self.data_formatter.format_comparative_insights(ticker, comparative_insights)

        # Calculate ground truth for placeholder reference
        ground_truth = {
            'uncertainty_score': conditions['uncertainty_score'],
            'atr_pct': (indicators.get('atr', 0) / current_price * 100) if current_price > 0 else 0,
            'vwap_pct': conditions['price_vs_vwap_pct'],
            'volume_ratio': conditions['volume_ratio'],
        }

        context = f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔢 GROUND TRUTH VALUES - USE THESE PLACEHOLDERS IN YOUR NARRATIVE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Market Conditions (use placeholders, current values shown for reference):
  {{{{UNCERTAINTY}}}} = {ground_truth['uncertainty_score']:.1f}
  {{{{ATR_PCT}}}} = {ground_truth['atr_pct']:.2f}
  {{{{VWAP_PCT}}}} = {abs(ground_truth['vwap_pct']):.2f}
  {{{{VOLUME_RATIO}}}} = {ground_truth['volume_ratio']:.2f}
  {{{{RSI}}}} = {indicators.get('rsi', 0):.2f}
  {{{{MACD}}}} = {indicators.get('macd', 0):.4f}
  {{{{CURRENT_PRICE}}}} = {current_price:.2f}

Percentiles (use placeholders, current values shown for reference):"""

        # Add percentile placeholders
        for key, value in percentiles.items():
            percentile_val = value.get('percentile', 0) if isinstance(value, dict) else value
            context += f"\n  {{{{{key.upper()}_PERCENTILE}}}} = {percentile_val:.1f}"

        context += f"""

REMEMBER: Write "{{{{UNCERTAINTY}}}}/100" NOT "{ground_truth['uncertainty_score']:.1f}/100"
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

สัญลักษณ์: {ticker}
บริษัท: {ticker_data.get('company_name', ticker)}
ราคาปัจจุบัน: Use {{{{CURRENT_PRICE}}}} placeholder (current: {current_price:.2f})
วันที่: {ticker_data.get('date')}

{fundamental_section}
{technical_section}
สภาวะตลาด (Market Condition - USE PLACEHOLDERS FOR THESE VALUES):
สถานะ: {uncertainty_level}

1. ความผันผวน (Volatility): {volatility_desc}

2. แรงซื้อ-ขาย (Buy/Sell Pressure): {vwap_desc}

3. ปริมาณการซื้อขาย (Volume): {volume_desc}
{percentile_context}
การวิเคราะห์เทียบเคียง (Relative Analysis):
- คำแนะนำนักวิเคราะห์: {ticker_data.get('recommendation', 'N/A').upper()}
- ราคาเป้าหมายเฉลี่ย: {ticker_data.get('target_mean_price', 'N/A')}
- จำนวนนักวิเคราะห์: {ticker_data.get('analyst_count', 'N/A')}
- ราคาสูงสุด 52 สัปดาห์: {ticker_data.get('fifty_two_week_high', 'N/A')}
- ราคาต่ำสุด 52 สัปดาห์: {ticker_data.get('fifty_two_week_low', 'N/A')}

การวิเคราะห์เปรียบเทียบกับหุ้นอื่น (Comparative Analysis):
{comparative_section if comparative_section else "- ไม่มีข้อมูลเปรียบเทียบ (ใช้ข้อมูลเดียวกับหุ้นตัวนี้เท่านั้น)"}
{news_section}"""
        
        return context
