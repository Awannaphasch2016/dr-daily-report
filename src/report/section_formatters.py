# -*- coding: utf-8 -*-
"""
Section formatters using Strategy + Null Object patterns.

This module provides a unified way to handle optional sections in prompts and contexts.
Each section type has its own formatter strategy, and empty sections use the Null Object pattern.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


class SectionFormatter(ABC):
    """Strategy interface for formatting sections"""
    
    @abstractmethod
    def format(self, data: Any) -> str:
        """Format section data into string
        
        Args:
            data: Section data (can be None, dict, list, etc.)
            
        Returns:
            Formatted string (empty string if no data)
        """
        pass
    
    @abstractmethod
    def has_data(self, data: Any) -> bool:
        """Check if section has data
        
        Args:
            data: Section data to check
            
        Returns:
            True if section has data, False otherwise
        """
        pass
    
    @abstractmethod
    def get_section_name(self) -> str:
        """Get section identifier
        
        Returns:
            Section name/identifier
        """
        pass


class EmptySectionFormatter(SectionFormatter):
    """Null Object pattern: Empty section formatter"""
    
    def format(self, data: Any) -> str:
        return ""
    
    def has_data(self, data: Any) -> bool:
        return False
    
    def get_section_name(self) -> str:
        return "empty"


class StrategySectionFormatter(SectionFormatter):
    """Formatter for strategy performance section"""
    
    def __init__(self, data_formatter=None):
        self.data_formatter = data_formatter
    
    def format(self, data: Any) -> str:
        """Format strategy performance data into context
        
        Strategy data is now included in context like other sections,
        using placeholders for numbers to ensure accuracy.
        """
        if not self.has_data(data):
            return ""
        
        return self._format_strategy_section(data)
    
    def _format_strategy_section(self, strategy_performance: dict) -> str:
        """Format supporting strategy data for LLM context.

        Expects the filtered 'supporting' dict shape from filter_supporting_strategies():
            {
                'supporting_strategies': {name: {buy_only: {...}, sell_only: {...}}, ...},
                'best_supporting': {'name': str, 'buy_only': {...}, 'sell_only': {...}},
                'support_count': int,
                'total_count': int,
            }
        """
        support_count = strategy_performance.get('support_count', 0)
        total_count = strategy_performance.get('total_count', 0)
        supporting_strategies = strategy_performance.get('supporting_strategies', {})
        best_supporting = strategy_performance.get('best_supporting', {})

        section = f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🎯 SUPPORTING STRATEGY PERFORMANCE ({support_count}/{total_count} strategies support recommendation)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

USE PLACEHOLDERS FOR ALL NUMBERS - DO NOT WRITE ACTUAL VALUES IN YOUR NARRATIVE

"""
        # Supporting strategies breakdown
        if supporting_strategies:
            section += "Supporting Strategies:\n"
            section += "  Strategy             | Buy Return | Sell Return\n"
            section += "  " + "-" * 55 + "\n"
            for name, dirs in supporting_strategies.items():
                buy_ret = dirs.get('buy_only', {}).get('total_return_pct', 0)
                sell_ret = dirs.get('sell_only', {}).get('total_return_pct', 0)
                section += f"  {name:<22}| {buy_ret:>9.2f}% | {sell_ret:>10.2f}%\n"

        # Best supporting strategy details
        if best_supporting:
            best_name = best_supporting.get('name', 'N/A')
            buy_only = best_supporting.get('buy_only', {})
            sell_only = best_supporting.get('sell_only', {})

            section += f"\nBest Supporting Strategy: {best_name}\n"

            section += "\n  Buy-Only Performance:\n"
            if buy_only:
                section += f"""  - Total Return: Use {{{{STRATEGY_BUY_RETURN}}}}% placeholder (current: {buy_only.get('total_return_pct', 0):.2f}%)
  - Sharpe Ratio: Use {{{{STRATEGY_BUY_SHARPE}}}} placeholder (current: {buy_only.get('sharpe_ratio', 0):.2f})
  - Win Rate: Use {{{{STRATEGY_BUY_WIN_RATE}}}}% placeholder (current: {buy_only.get('win_rate', 0):.1f}%)
  - Max Drawdown: Use {{{{STRATEGY_BUY_DRAWDOWN}}}}% placeholder (current: {buy_only.get('max_drawdown_pct', 0):.2f}%)
"""

            section += "\n  Sell-Only Performance:\n"
            if sell_only:
                section += f"""  - Total Return: Use {{{{STRATEGY_SELL_RETURN}}}}% placeholder (current: {sell_only.get('total_return_pct', 0):.2f}%)
  - Sharpe Ratio: Use {{{{STRATEGY_SELL_SHARPE}}}} placeholder (current: {sell_only.get('sharpe_ratio', 0):.2f})
  - Win Rate: Use {{{{STRATEGY_SELL_WIN_RATE}}}}% placeholder (current: {sell_only.get('win_rate', 0):.1f}%)
  - Max Drawdown: Use {{{{STRATEGY_SELL_DRAWDOWN}}}}% placeholder (current: {sell_only.get('max_drawdown_pct', 0):.2f}%)
"""

        section += "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        section += "\nREMEMBER: Use placeholders like {{{{STRATEGY_BUY_RETURN}}}}% NOT actual numbers like \"15.2%\"\n"

        return section
    
    def has_data(self, data: Any) -> bool:
        """Check if strategy performance data exists"""
        return bool(data and isinstance(data, dict) and len(data) > 0)
    
    def get_section_name(self) -> str:
        return "strategy"


class ComparativeSectionFormatter(SectionFormatter):
    """Formatter for comparative insights section"""
    
    def __init__(self, data_formatter):
        self.data_formatter = data_formatter
    
    def format(self, data: Any) -> str:
        """Format comparative insights"""
        if not self.has_data(data):
            return ""
        
        # Use existing formatter
        return self.data_formatter.format_comparative_insights(
            ticker="",  # Ticker not needed for formatting
            insights=data
        )
    
    def has_data(self, data: Any) -> bool:
        """Check if comparative insights exist"""
        if not data or not isinstance(data, dict):
            return False
        # Check if any meaningful data exists
        return bool(
            data.get('similar_tickers') or
            data.get('cluster_id') or
            data.get('volatility_vs_peers') or
            data.get('return_vs_peers') or
            data.get('volatility_rank')
        )
    
    def get_section_name(self) -> str:
        return "comparative"


class SECFilingSectionFormatter(SectionFormatter):
    """Formatter for SEC filing section"""
    
    def format(self, data: Any) -> str:
        """Format SEC filing data"""
        if not self.has_data(data):
            return ""
        
        return self._format_sec_filing_section(data)
    
    def _format_sec_filing_section(self, sec_filing_data: dict) -> str:
        """Format SEC filing data for LLM context"""
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
    
    def has_data(self, data: Any) -> bool:
        """Check if SEC filing data exists"""
        return bool(data and isinstance(data, dict) and len(data) > 0)
    
    def get_section_name(self) -> str:
        return "sec_filing"


class FinancialMarketsSectionFormatter(SectionFormatter):
    """Formatter for Financial Markets MCP section"""
    
    def format(self, data: Any) -> str:
        """Format Financial Markets MCP data"""
        if not self.has_data(data):
            return ""
        
        return self._format_financial_markets_section(data)
    
    def _format_financial_markets_section(self, financial_markets_data: dict) -> str:
        """Format Financial Markets MCP data for LLM context"""
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
    
    def has_data(self, data: Any) -> bool:
        """Check if Financial Markets data exists"""
        return bool(data and isinstance(data, dict) and len(data) > 0)
    
    def get_section_name(self) -> str:
        return "financial_markets"


class PortfolioInsightsSectionFormatter(SectionFormatter):
    """Formatter for Portfolio Manager MCP section"""
    
    def format(self, data: Any) -> str:
        """Format Portfolio Manager MCP data"""
        if not self.has_data(data):
            return ""
        
        return self._format_portfolio_insights_section(data)
    
    def _format_portfolio_insights_section(self, portfolio_insights: dict) -> str:
        """Format Portfolio Manager MCP data for LLM context"""
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
    
    def has_data(self, data: Any) -> bool:
        """Check if Portfolio insights exist"""
        return bool(data and isinstance(data, dict) and len(data) > 0)
    
    def get_section_name(self) -> str:
        return "portfolio_insights"


class AlpacaSectionFormatter(SectionFormatter):
    """Formatter for Alpaca MCP section"""
    
    def format(self, data: Any) -> str:
        """Format Alpaca MCP data"""
        if not self.has_data(data):
            return ""
        
        return self._format_alpaca_data_section(data)
    
    def _format_alpaca_data_section(self, alpaca_data: dict) -> str:
        """Format Alpaca MCP data for LLM context"""
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
    
    def has_data(self, data: Any) -> bool:
        """Check if Alpaca data exists"""
        return bool(data and isinstance(data, dict) and len(data) > 0)
    
    def get_section_name(self) -> str:
        return "alpaca"


class NewsSectionFormatter(SectionFormatter):
    """Formatter for news section"""
    
    def __init__(self, data_formatter):
        self.data_formatter = data_formatter
    
    def format(self, data: Any) -> str:
        """Format news data"""
        if not self.has_data(data):
            return ""
        
        news, news_summary = data
        return self.data_formatter.format_news_section(news, news_summary)
    
    def has_data(self, data: Any) -> bool:
        """Check if news data exists"""
        if not data or not isinstance(data, tuple) or len(data) != 2:
            return False
        news, news_summary = data
        return bool(news and len(news) > 0)
    
    def get_section_name(self) -> str:
        return "news"


class SectionRegistry:
    """Registry for section formatters"""
    
    def __init__(self, data_formatter):
        """Initialize registry with all formatters"""
        self.formatters: Dict[str, SectionFormatter] = {
            'strategy': StrategySectionFormatter(data_formatter),
            'comparative': ComparativeSectionFormatter(data_formatter),
            'sec_filing': SECFilingSectionFormatter(),
            'financial_markets': FinancialMarketsSectionFormatter(),
            'portfolio_insights': PortfolioInsightsSectionFormatter(),
            'alpaca': AlpacaSectionFormatter(),
            'news': NewsSectionFormatter(data_formatter),
        }
    
    def get_formatter(self, section_name: str) -> SectionFormatter:
        """Get formatter for a section"""
        return self.formatters.get(section_name, EmptySectionFormatter())
    
    def get_all_formatters(self) -> Dict[str, SectionFormatter]:
        """Get all registered formatters"""
        return self.formatters.copy()
