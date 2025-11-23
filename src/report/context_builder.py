# -*- coding: utf-8 -*-
"""Context building utilities for LLM report generation"""

import logging
from typing import Dict, List, Optional
from src.analysis import MarketAnalyzer
from src.formatters import DataFormatter
from src.analysis.technical_analysis import TechnicalAnalyzer

# Setup logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class ContextBuilder:
    """Builds context for LLM report generation"""
    
    def __init__(self, market_analyzer: MarketAnalyzer, data_formatter: DataFormatter, technical_analyzer: TechnicalAnalyzer):
        """Initialize with required dependencies"""
        self.market_analyzer = market_analyzer
        self.data_formatter = data_formatter
        self.technical_analyzer = technical_analyzer
    
    def prepare_context(self, ticker: str, ticker_data: dict, indicators: dict, percentiles: dict, news: list, news_summary: dict, strategy_performance: dict = None, comparative_insights: dict = None) -> str:
        """Prepare context for LLM with uncertainty components and percentile information"""
        logger.info("📝 [ContextBuilder] Building context for LLM")
        logger.info(f"   📊 Input parameters:")
        logger.info(f"      - Ticker: {ticker}")
        logger.info(f"      - Ticker data keys: {list(ticker_data.keys()) if ticker_data else 'None'}")
        logger.info(f"      - Indicators keys: {list(indicators.keys()) if indicators else 'None'}")
        logger.info(f"      - Percentiles keys: {list(percentiles.keys()) if percentiles else 'None'}")
        logger.info(f"      - News items: {len(news) if news else 0}")
        logger.info(f"      - News summary keys: {list(news_summary.keys()) if news_summary else 'None'}")
        logger.info(f"      - Strategy performance included: {strategy_performance is not None}")
        logger.info(f"      - Comparative insights included: {comparative_insights is not None}")
        
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

        # Log section sizes
        logger.info(f"   📋 Context sections:")
        logger.info(f"      - Fundamental section: {len(fundamental_section)} chars")
        logger.info(f"      - Technical section: {len(technical_section)} chars")
        logger.info(f"      - News section: {len(news_section)} chars")
        logger.info(f"      - Percentile context: {len(percentile_context)} chars")
        logger.info(f"      - Comparative section: {len(comparative_section)} chars {'(included)' if comparative_section else '(excluded)'}")

        # Calculate ground truth for placeholder reference
        ground_truth = {
            'uncertainty_score': conditions['uncertainty_score'],
            'atr_pct': (indicators.get('atr', 0) / current_price * 100) if current_price > 0 else 0,
            'vwap_pct': conditions['price_vs_vwap_pct'],
            'volume_ratio': conditions['volume_ratio'],
        }

        logger.info(f"   🔢 Ground truth values:")
        logger.info(f"      - Uncertainty: {ground_truth['uncertainty_score']:.2f}/100")
        logger.info(f"      - ATR %: {ground_truth['atr_pct']:.2f}%")
        logger.info(f"      - VWAP %: {ground_truth['vwap_pct']:.2f}%")
        logger.info(f"      - Volume ratio: {ground_truth['volume_ratio']:.2f}x")
        logger.info(f"      - Current price: ${current_price:.2f}")

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
        
        # Log final context summary
        logger.info(f"   ✅ Final context built:")
        logger.info(f"      - Total length: {len(context)} characters (~{len(context) // 4} tokens estimated)")
        logger.info(f"      - First 200 chars: {context[:200]}...")
        logger.info(f"      - Last 200 chars: ...{context[-200:]}")
        
        # Log full context content (split into chunks if too long for single log line)
        logger.info("   📄 Full context content:")
        # Split into chunks of ~8000 chars to avoid CloudWatch log line limits
        chunk_size = 8000
        for i in range(0, len(context), chunk_size):
            chunk = context[i:i + chunk_size]
            chunk_num = (i // chunk_size) + 1
            total_chunks = (len(context) + chunk_size - 1) // chunk_size
            if total_chunks > 1:
                logger.info(f"      [Chunk {chunk_num}/{total_chunks}]:\n{chunk}")
            else:
                logger.info(f"      {chunk}")
        
        return context
