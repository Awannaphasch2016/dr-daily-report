# -*- coding: utf-8 -*-
"""Context building utilities for LLM report generation

This implements Layer 2 output of the three-layer architecture:
  Layer 1 (Code): Numeric calculations, ground truth
  Layer 2 (Code): Semantic state classification + Context building ← THIS MODULE
  Layer 3 (LLM): Narrative synthesis constrained by states

Research basis: https://www.getdbt.com/blog/semantic-layer-as-the-data-interface-for-llms
"""

import logging
from typing import Dict, List, Optional
from src.analysis import MarketAnalyzer
from src.formatters import DataFormatter
from src.analysis.technical_analysis import TechnicalAnalyzer
from src.analysis.semantic_state_generator import SemanticStateGenerator
from src.report.section_formatters import SectionRegistry
from src.report.metric_registry import MetricRegistry, get_metric_registry

# Setup logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


# Label translations for context building (Thai only)
CONTEXT_LABELS = {
    'symbol': 'สัญลักษณ์',
    'company': 'บริษัท',
    'sector': 'ภาคธุรกิจ',
    'industry': 'อุตสาหกรรม',
    'market_cap': 'มูลค่าตลาด',
    'pe_ratio': 'P/E',
    'dividend_yield': 'ผลตอบแทนเงินปันผล',
    'current_price': 'ราคาปัจจุบัน',
    'week_high': 'สูงสุด 52 สัปดาห์',
    'week_low': 'ต่ำสุด 52 สัปดาห์',
    'volume': 'ปริมาณซื้อขาย',
    'avg_volume': 'ปริมาณเฉลี่ย',
    'beta': 'เบต้า',
    # Technical indicators
    'sma': 'SMA',
    'rsi': 'RSI',
    'macd': 'MACD',
    'atr': 'ATR',
    'bollinger': 'Bollinger Bands',
    'vwap': 'VWAP',
    # Market conditions
    'uncertainty': 'ความไม่แน่นอน',
    'volatility': 'ความผันผวน',
    'momentum': 'โมเมนตัม',
    'trend': 'แนวโน้ม',
}


class ContextBuilder:
    """Builds context for LLM report generation (Layer 2 output)

    CRITICAL: This module builds semantic context (Layer 2), NOT narrative (Layer 3).
    It converts numeric data to semantic states WITHOUT number leakage.

    Research: Semantic layers improve LLM accuracy by 300%
    https://www.getdbt.com/blog/semantic-layer-as-the-data-interface-for-llms
    """

    def __init__(self, market_analyzer: MarketAnalyzer, data_formatter: DataFormatter,
                 technical_analyzer: TechnicalAnalyzer, registry: Optional[MetricRegistry] = None):
        """Initialize with required dependencies

        Args:
            market_analyzer: Market analysis service (for condition calculation)
            data_formatter: Data formatting service
            technical_analyzer: Technical analysis service
            registry: Optional MetricRegistry instance (falls back to singleton)
        """
        self.market_analyzer = market_analyzer
        self.data_formatter = data_formatter
        self.technical_analyzer = technical_analyzer
        self.registry = registry
        self.semantic_generator = SemanticStateGenerator()  # NEW: Semantic state generator
        self.labels = CONTEXT_LABELS

        # Initialize section registry for unified section handling
        self.section_registry = SectionRegistry(data_formatter)

    @property
    def _registry(self) -> MetricRegistry:
        if self.registry is not None:
            return self.registry
        return get_metric_registry()

    def prepare_context(self, ticker: str, ticker_data: dict, indicators: dict, percentiles: dict, news: list, news_summary: dict, ground_truth: dict = None, strategy_performance: dict = None, comparative_insights: dict = None, sec_filing_data: dict = None, financial_markets_data: dict = None, portfolio_insights: dict = None, alpaca_data: dict = None) -> str:
        """Prepare semantic context for LLM (Layer 2 output)

        Design principle: Separate values from semantics
        - Layer 1 (numeric) → Layer 2 (semantic states) → Layer 3 (LLM narrative)

        Args:
            ticker: Ticker symbol
            ticker_data: Fundamental data
            indicators: Technical indicators
            percentiles: Percentile data
            news: News items
            news_summary: News summary
            ground_truth: Calculated market conditions (NEW - required for semantic states)
            strategy_performance: Optional strategy data
            comparative_insights: Optional peer comparison
            sec_filing_data: Optional SEC filing data
            financial_markets_data: Optional market data
            portfolio_insights: Optional portfolio data
            alpaca_data: Optional broker data

        Returns:
            str: Semantic context string with NO number leakage
        """
        logger.info("📝 [ContextBuilder] Building semantic context (Layer 2) for LLM")
        logger.info(f"   📊 Input parameters:")
        logger.info(f"      - Ticker: {ticker}")
        logger.info(f"      - Ticker data keys: {list(ticker_data.keys()) if ticker_data else 'None'}")
        logger.info(f"      - Indicators keys: {list(indicators.keys()) if indicators else 'None'}")
        logger.info(f"      - Percentiles keys: {list(percentiles.keys()) if percentiles else 'None'}")
        logger.info(f"      - News items: {len(news) if news else 0}")
        logger.info(f"      - News summary keys: {list(news_summary.keys()) if news_summary else 'None'}")
        logger.info(f"      - Strategy performance included: {strategy_performance is not None}")
        logger.info(f"      - Comparative insights included: {comparative_insights is not None}")
        logger.info(f"      - SEC filing data included: {sec_filing_data is not None and len(sec_filing_data) > 0}")
        
        # Calculate market conditions (Layer 1 → ground truth)
        conditions = self.market_analyzer.calculate_market_conditions(indicators)
        current_price = conditions['current_price']

        # Build ground_truth if not provided (backwards compatibility)
        if ground_truth is None:
            ground_truth = {
                'uncertainty_score': conditions.get('uncertainty_score', 0),
                'atr_pct': (conditions.get('atr', 0) / current_price * 100) if current_price > 0 else 0,
                'vwap_pct': conditions.get('price_vs_vwap_pct', 0),
                'volume_ratio': conditions.get('volume_ratio', 0),
            }

        # Generate semantic states (Layer 1 → Layer 2)
        semantic_states = self.semantic_generator.generate_all_states(ground_truth, indicators)

        # ❌ REMOVED: interpret_uncertainty_level() - caused number leakage
        # ❌ REMOVED: interpret_volatility() - caused number leakage
        # ❌ REMOVED: interpret_vwap_pressure() - caused number leakage
        # ❌ REMOVED: interpret_volume() - caused number leakage

        # Format sections (factual data only, NO interpretation)
        percentile_context = self.data_formatter.format_percentile_context(percentiles)
        fundamental_section = self.data_formatter.format_fundamental_section(ticker_data)
        technical_section = self.data_formatter.format_technical_section(indicators, current_price, self.technical_analyzer)
        
        # Use unified section formatters for optional sections
        comparative_insights = comparative_insights or {}
        comparative_formatter = self.section_registry.get_formatter('comparative')
        comparative_section = comparative_formatter.format(comparative_insights)
        
        # Format optional sections using unified pattern
        sec_filing_formatter = self.section_registry.get_formatter('sec_filing')
        sec_filing_section = sec_filing_formatter.format(sec_filing_data)
        if sec_filing_formatter.has_data(sec_filing_data):
            logger.info(f"      - SEC filing data available: {sec_filing_data.get('form_type', 'N/A')} filed {sec_filing_data.get('filing_date', 'N/A')}")
        
        financial_markets_formatter = self.section_registry.get_formatter('financial_markets')
        financial_markets_section = financial_markets_formatter.format(financial_markets_data)
        if financial_markets_formatter.has_data(financial_markets_data):
            logger.info(f"      - Financial Markets MCP data available: {list(financial_markets_data.keys())}")
        
        portfolio_formatter = self.section_registry.get_formatter('portfolio_insights')
        portfolio_insights_section = portfolio_formatter.format(portfolio_insights)
        if portfolio_formatter.has_data(portfolio_insights):
            logger.info(f"      - Portfolio Manager MCP data available: {list(portfolio_insights.keys())}")
        
        alpaca_formatter = self.section_registry.get_formatter('alpaca')
        alpaca_section = alpaca_formatter.format(alpaca_data)
        if alpaca_formatter.has_data(alpaca_data):
            logger.info(f"      - Alpaca MCP data available: {list(alpaca_data.keys())}")
        
        news_formatter = self.section_registry.get_formatter('news')
        news_section = news_formatter.format((news, news_summary))
        
        # Format strategy performance data (now included in context like other sections)
        strategy_formatter = self.section_registry.get_formatter('strategy')
        strategy_section = strategy_formatter.format(strategy_performance)
        if strategy_formatter.has_data(strategy_performance):
            logger.info(f"      - Strategy performance data available: {list(strategy_performance.keys())}")

        # Log section sizes
        logger.info(f"   📋 Context sections:")
        logger.info(f"      - Fundamental section: {len(fundamental_section)} chars")
        logger.info(f"      - Technical section: {len(technical_section)} chars")
        logger.info(f"      - News section: {len(news_section)} chars")
        logger.info(f"      - Percentile context: {len(percentile_context)} chars")
        logger.info(f"      - Comparative section: {len(comparative_section)} chars {'(included)' if comparative_section else '(excluded)'}")
        logger.info(f"      - SEC filing section: {len(sec_filing_section)} chars {'(included)' if sec_filing_section else '(excluded)'}")
        logger.info(f"      - Financial Markets section: {len(financial_markets_section)} chars {'(included)' if financial_markets_section else '(excluded)'}")
        logger.info(f"      - Portfolio insights section: {len(portfolio_insights_section)} chars {'(included)' if portfolio_insights_section else '(excluded)'}")
        logger.info(f"      - Alpaca section: {len(alpaca_section)} chars {'(included)' if alpaca_section else '(excluded)'}")
        logger.info(f"      - Strategy section: {len(strategy_section)} chars {'(included)' if strategy_section else '(excluded)'}")

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

        # Build context with Thai labels
        no_comparative_data_msg = "- ไม่มีข้อมูลเปรียบเทียบ (ใช้ข้อมูลเดียวกับหุ้นตัวนี้เท่านั้น)"

        # Build market conditions block dynamically from registry
        market_condition_lines = "Market Conditions (interpret context, use placeholders):"
        for category in ['risk_metrics', 'momentum_indicators']:
            for metric in self._registry.get_ready_metrics(category=category):
                # Use quadruple braces because this goes through .format() later
                market_condition_lines += f"\n  {{{{{{{{{metric.placeholder}}}}}}}}}{metric.suffix} - {metric.description}"

        # Build risk state lines with conditional uncertainty_state
        risk_state_lines = f"""Risk Regime:"""
        if self._registry.is_ready('uncertainty'):
            risk_state_lines += f"\n  - Market State: {semantic_states.risk.uncertainty_state}"
        risk_state_lines += f"""
  - Volatility: {semantic_states.risk.volatility_regime}
  - Pressure: {semantic_states.risk.pressure_direction}
  - Volume Confidence: {semantic_states.risk.volume_confidence}"""

        context = f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 MARKET DATA FOR {ticker} (use placeholders below - NO raw numbers)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{market_condition_lines}

Percentiles (historical context - optional to use):"""

        # Add percentile placeholders without values
        for key, value in percentiles.items():
            context += f"\n  {{{{{key.upper()}_PERCENTILE}}}}% - How current {key} compares to 1-year history"

        context += f"""

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{self.labels['symbol']}: {ticker}
{self.labels['company']}: {ticker_data.get('company_name', ticker)}
{self.labels['current_price']}: Use {{{{CURRENT_PRICE}}}} placeholder
Date: {ticker_data.get('date')}

{fundamental_section}
{technical_section}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SEMANTIC STATES (Interpret these, use placeholders for numbers):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Market Regime: {semantic_states.market_regime.regime}
  - bull: Sustained uptrend with supporting momentum
  - bear: Sustained downtrend with confirming momentum
  - sideways: Mixed signals, range-bound market

{risk_state_lines}

Momentum State:
  - RSI Zone: {semantic_states.momentum.rsi_zone}
  - MACD Signal: {semantic_states.momentum.macd_signal}
  - Direction: {semantic_states.momentum.momentum_direction}

Trend State:
  - SMA Alignment: {semantic_states.trend.sma_alignment}
  - Price Position: {semantic_states.trend.price_vs_sma}

Divergence Signal: {semantic_states.divergence.signal}
  - bullish_divergence: Price down but RSI rising (hidden strength)
  - bearish_divergence: Price up but RSI falling (hidden weakness)
  - no_divergence: Price and RSI moving together

Constraint Satisfaction Rules:
1. NARRATIVE MUST honor semantic states above (e.g., if risk=stable, don't write "risky")
2. USE placeholders for ALL numeric references: {{{{UNCERTAINTY}}}}/100, {{{{ATR_PCT}}}}%
3. COMBINE states logically (e.g., oversold + uptrend = "pullback in uptrend")
4. DIRECTIONAL language from states: "strengthening" not "increasing"
5. NEVER copy raw numbers from data sections below

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{percentile_context}
Relative Analysis:
- Analyst Recommendation: {(ticker_data.get('recommendation') or 'N/A').upper() if ticker_data.get('recommendation') else 'N/A'}
- Target Price (Avg): {ticker_data.get('target_mean_price', 'N/A')}
- Analyst Count: {ticker_data.get('analyst_count', 'N/A')}
- {self.labels['week_high']}: {ticker_data.get('fifty_two_week_high', 'N/A')}
- {self.labels['week_low']}: {ticker_data.get('fifty_two_week_low', 'N/A')}

Comparative Analysis:
{comparative_section if comparative_section else no_comparative_data_msg}
{sec_filing_section if sec_filing_section else ""}
{financial_markets_section if financial_markets_section else ""}
{portfolio_insights_section if portfolio_insights_section else ""}
{alpaca_section if alpaca_section else ""}
{news_section}
{strategy_section if strategy_section else ""}"""
        
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
    
    def get_section_presence(self, strategy_performance: dict = None, 
                            comparative_insights: dict = None,
                            sec_filing_data: dict = None,
                            financial_markets_data: dict = None,
                            portfolio_insights: dict = None,
                            alpaca_data: dict = None) -> Dict[str, bool]:
        """Get which sections have data (for instruction building)
        
        Args:
            strategy_performance: Strategy performance data
            comparative_insights: Comparative insights data
            sec_filing_data: SEC filing data
            financial_markets_data: Financial Markets MCP data
            portfolio_insights: Portfolio Manager MCP data
            alpaca_data: Alpaca MCP data
            
        Returns:
            Dictionary mapping section names to boolean presence indicators
        """
        return {
            'strategy': self.section_registry.get_formatter('strategy').has_data(strategy_performance),
            'comparative': self.section_registry.get_formatter('comparative').has_data(comparative_insights or {}),
            'sec_filing': self.section_registry.get_formatter('sec_filing').has_data(sec_filing_data),
            'financial_markets': self.section_registry.get_formatter('financial_markets').has_data(financial_markets_data),
            'portfolio_insights': self.section_registry.get_formatter('portfolio_insights').has_data(portfolio_insights),
            'alpaca': self.section_registry.get_formatter('alpaca').has_data(alpaca_data),
        }
    
    def _format_sec_filing_section(self, sec_filing_data: dict) -> str:
        """
        Format SEC filing data for LLM context.
        
        Args:
            sec_filing_data: SEC filing data from MCP server
            
        Returns:
            Formatted SEC filing section text
        """
        if not sec_filing_data:
            return ""
        
        filing_date = sec_filing_data.get('filing_date', 'N/A')
        form_type = sec_filing_data.get('form_type', 'N/A')
        xbrl = sec_filing_data.get('xbrl', {})
        text_sections = sec_filing_data.get('text_sections', {})
        
        section = f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📄 SEC FILING DATA (จาก SEC EDGAR)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Form Type: {form_type}
Filing Date: {filing_date}
"""
        
        # Add XBRL financial metrics if available
        if xbrl:
            revenue = xbrl.get('RevenueFromContractWithCustomerExcludingAssessedTax')
            operating_income = xbrl.get('OperatingIncomeLoss')
            net_income = xbrl.get('NetIncomeLoss')
            total_assets = xbrl.get('Assets')
            
            if revenue or operating_income or net_income:
                section += "\nFinancial Metrics (XBRL):\n"
                if revenue:
                    section += f"  - Revenue: ${revenue:,.0f}\n"
                if operating_income:
                    section += f"  - Operating Income: ${operating_income:,.0f}\n"
                if net_income:
                    section += f"  - Net Income: ${net_income:,.0f}\n"
                if total_assets:
                    section += f"  - Total Assets: ${total_assets:,.0f}\n"
                
                # Calculate margins if available
                if revenue and operating_income:
                    op_margin = (operating_income / revenue) * 100
                    section += f"  - Operating Margin: {op_margin:.2f}%\n"
                if revenue and net_income:
                    net_margin = (net_income / revenue) * 100
                    section += f"  - Net Margin: {net_margin:.2f}%\n"
        
        # Add risk factors if available
        if text_sections.get('risk_factors'):
            risk_factors = text_sections['risk_factors']
            # Truncate if too long (keep first 1000 chars)
            if len(risk_factors) > 1000:
                risk_factors = risk_factors[:1000] + "... (truncated)"
            section += f"\nRisk Factors:\n{risk_factors}\n"
        
        section += "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        
        return section
    
    def format_financial_markets_section(self, financial_markets_data: dict) -> str:
        """
        Format Financial Markets MCP data for LLM context.
        
        Args:
            financial_markets_data: Financial Markets data from MCP server
            
        Returns:
            Formatted Financial Markets section text
        """
        if not financial_markets_data:
            return ""
        
        section = """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📈 ADVANCED TECHNICAL ANALYSIS (Financial Markets MCP)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
        
        # Chart patterns
        if financial_markets_data.get('chart_patterns'):
            chart_patterns = financial_markets_data['chart_patterns']
            section += "\nChart Patterns:\n"
            if isinstance(chart_patterns, list):
                for pattern in chart_patterns[:5]:  # Limit to top 5
                    section += f"  - {pattern}\n"
            elif isinstance(chart_patterns, dict):
                for pattern_name, details in list(chart_patterns.items())[:5]:
                    section += f"  - {pattern_name}: {details}\n"
        
        # Candlestick patterns
        if financial_markets_data.get('candlestick_patterns'):
            candlestick_patterns = financial_markets_data['candlestick_patterns']
            section += "\nCandlestick Patterns:\n"
            if isinstance(candlestick_patterns, list):
                for pattern in candlestick_patterns[:5]:
                    section += f"  - {pattern}\n"
            elif isinstance(candlestick_patterns, dict):
                for pattern_name, details in list(candlestick_patterns.items())[:5]:
                    section += f"  - {pattern_name}: {details}\n"
        
        # Support/Resistance levels
        if financial_markets_data.get('support_resistance'):
            support_resistance = financial_markets_data['support_resistance']
            section += "\nSupport/Resistance Levels:\n"
            if isinstance(support_resistance, dict):
                support = support_resistance.get('support', [])
                resistance = support_resistance.get('resistance', [])
                if support:
                    section += f"  Support Levels: {', '.join(map(str, support[:3]))}\n"
                if resistance:
                    section += f"  Resistance Levels: {', '.join(map(str, resistance[:3]))}\n"
        
        # Advanced technical indicators
        if financial_markets_data.get('technical_indicators'):
            technical_indicators = financial_markets_data['technical_indicators']
            section += "\nAdvanced Technical Indicators:\n"
            if isinstance(technical_indicators, dict):
                for indicator_name, value in list(technical_indicators.items())[:10]:
                    section += f"  - {indicator_name}: {value}\n"
        
        section += "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        
        return section
    
    def format_portfolio_insights_section(self, portfolio_insights: dict) -> str:
        """
        Format Portfolio Manager MCP data for LLM context.
        
        Args:
            portfolio_insights: Portfolio insights from MCP server
            
        Returns:
            Formatted Portfolio insights section text
        """
        if not portfolio_insights:
            return ""
        
        section = """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💼 PORTFOLIO INSIGHTS (Portfolio Manager MCP)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
        
        # Portfolio allocation
        if portfolio_insights.get('allocation'):
            allocation = portfolio_insights['allocation']
            section += "\nPortfolio Allocation:\n"
            if isinstance(allocation, dict):
                for asset, percentage in allocation.items():
                    section += f"  - {asset}: {percentage}%\n"
        
        # Diversification metrics
        if portfolio_insights.get('diversification'):
            diversification = portfolio_insights['diversification']
            section += "\nDiversification Metrics:\n"
            if isinstance(diversification, dict):
                for metric, value in diversification.items():
                    section += f"  - {metric}: {value}\n"
        
        # Risk assessment
        if portfolio_insights.get('risk'):
            risk = portfolio_insights['risk']
            section += "\nRisk Assessment:\n"
            if isinstance(risk, dict):
                for risk_type, value in risk.items():
                    section += f"  - {risk_type}: {value}\n"
        
        section += "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        
        return section
    
    def format_alpaca_data_section(self, alpaca_data: dict) -> str:
        """
        Format Alpaca MCP data for LLM context.
        
        Args:
            alpaca_data: Alpaca data from MCP server
            
        Returns:
            Formatted Alpaca data section text
        """
        if not alpaca_data:
            return ""
        
        section = """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 REAL-TIME MARKET DATA (Alpaca MCP)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
        
        # Real-time quote
        if alpaca_data.get('quote'):
            quote = alpaca_data['quote']
            section += "\nReal-Time Quote:\n"
            if isinstance(quote, dict):
                for key, value in quote.items():
                    section += f"  - {key}: {value}\n"
        
        # Options chain (for volatility analysis)
        if alpaca_data.get('options_chain'):
            options_chain = alpaca_data['options_chain']
            section += "\nOptions Chain (Volatility Analysis):\n"
            if isinstance(options_chain, dict):
                implied_vol = options_chain.get('implied_volatility')
                greeks = options_chain.get('greeks', {})
                if implied_vol:
                    section += f"  - Implied Volatility: {implied_vol}%\n"
                if greeks:
                    section += "  - Greeks:\n"
                    for greek, value in list(greeks.items())[:5]:
                        section += f"    - {greek}: {value}\n"
        
        # Market data
        if alpaca_data.get('market_data'):
            market_data = alpaca_data['market_data']
            section += "\nMarket Data:\n"
            if isinstance(market_data, dict):
                for key, value in list(market_data.items())[:10]:
                    section += f"  - {key}: {value}\n"
        
        section += "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        
        return section
