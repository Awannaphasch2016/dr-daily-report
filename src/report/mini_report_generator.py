"""
Mini-Report Generator for Multi-Stage Report Generation.

This module generates specialized mini-reports for each data category:
- Technical Analysis
- Fundamental Analysis
- Market Conditions
- News & Events
- Comparative Analysis
- Strategy Performance

Each mini-report is 150-200 words in Thai, focusing on one aspect of the analysis.
"""

import os
from pathlib import Path
from typing import Dict, Any, List
import json
import numpy as np
import pandas as pd
from datetime import datetime, date

from src.evaluation import observe


class MiniReportGenerator:
    """
    Generates specialized mini-reports for different data categories.

    Each generator focuses on one aspect and produces a 150-200 word
    narrative in Thai based on prompt templates.
    """

    def __init__(self, llm):
        """
        Initialize the MiniReportGenerator.

        Args:
            llm: Language model instance for generating narratives
        """
        self.llm = llm
        self.prompts = self._load_prompt_templates()

    def _make_json_serializable(self, obj):
        """Convert numpy/pandas/datetime objects to JSON-serializable types"""
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        elif isinstance(obj, pd.Timestamp):
            return obj.isoformat()
        elif isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return self._make_json_serializable(obj.tolist())
        elif isinstance(obj, dict):
            return {str(k) if isinstance(k, (pd.Timestamp, datetime, date)) else k: self._make_json_serializable(v)
                    for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._make_json_serializable(item) for item in obj]
        return obj

    def _load_prompt_templates(self) -> Dict[str, str]:
        """
        Load all prompt templates from the prompt_templates directory.

        Returns:
            Dictionary mapping template names to their content
        """
        templates_dir = Path(__file__).parent / "prompt_templates" / "th" / "multi-stage"

        template_files = {
            'technical': 'technical_mini_prompt.txt',
            'fundamental': 'fundamental_mini_prompt.txt',
            'market_conditions': 'market_conditions_mini_prompt.txt',
            'news': 'news_mini_prompt.txt',
            'comparative': 'comparative_mini_prompt.txt',
            'strategy': 'strategy_mini_prompt.txt',
        }

        prompts = {}
        for key, filename in template_files.items():
            filepath = templates_dir / filename
            if filepath.exists():
                with open(filepath, 'r', encoding='utf-8') as f:
                    prompts[key] = f.read()
            else:
                raise FileNotFoundError(f"Prompt template not found: {filepath}")

        return prompts

    def _format_technical_data(self, indicators: Dict[str, Any], percentiles: Dict[str, Any]) -> str:
        """Format technical analysis data for prompt substitution."""
        data = {
            'indicators': self._make_json_serializable(indicators),
            'percentiles': self._make_json_serializable(percentiles)
        }
        return json.dumps(data, indent=2, ensure_ascii=False)

    def _format_fundamental_data(self, ticker_data: Dict[str, Any]) -> str:
        """Format fundamental analysis data for prompt substitution."""
        # Extract key fundamental metrics
        fundamental_metrics = {
            'pe_ratio': ticker_data.get('pe_ratio'),
            'forward_pe': ticker_data.get('forward_pe'),  # NEW: From fund_data
            'eps': ticker_data.get('eps'),
            'market_cap': ticker_data.get('market_cap'),
            'dividend_yield': ticker_data.get('dividend_yield'),
            'profit_margin': ticker_data.get('profit_margin'),
            'roe': ticker_data.get('roe'),
            'price_to_book': ticker_data.get('price_to_book'),  # NEW: From fund_data
            'debt_to_equity': ticker_data.get('debt_to_equity'),
            'revenue_growth': ticker_data.get('revenue_growth'),
            'target_price': ticker_data.get('target_price'),  # NEW: From fund_data
            'sector': ticker_data.get('sector'),
            'industry': ticker_data.get('industry'),
        }

        # Filter out None values and make JSON serializable
        fundamental_metrics = {k: v for k, v in fundamental_metrics.items() if v is not None}
        fundamental_metrics = self._make_json_serializable(fundamental_metrics)

        return json.dumps(fundamental_metrics, indent=2, ensure_ascii=False)

    def _format_market_conditions_data(self, indicators: Dict[str, Any], percentiles: Dict[str, Any]) -> str:
        """Format market conditions data for prompt substitution."""
        market_data = {
            'uncertainty_score': indicators.get('uncertainty_score'),
            'atr_percentage': indicators.get('atr_percentage'),
            'vwap_percentage': indicators.get('vwap_percentage'),
            'volume_ratio': indicators.get('volume_ratio'),
            'percentiles': {
                'uncertainty_score': percentiles.get('uncertainty_score', {}).get('percentile'),
                'atr_percentage': percentiles.get('atr_percentage', {}).get('percentile'),
            }
        }
        market_data = self._make_json_serializable(market_data)
        return json.dumps(market_data, indent=2, ensure_ascii=False)

    def _format_news_data(self, news: List[Dict[str, Any]], news_summary: Dict[str, Any]) -> str:
        """Format news & events data for prompt substitution."""
        news_data = {
            'news_items': news[:5],  # Top 5 news items
            'summary': news_summary
        }
        news_data = self._make_json_serializable(news_data)
        return json.dumps(news_data, indent=2, ensure_ascii=False)

    def _format_comparative_data(self, comparative_insights: Dict[str, Any]) -> str:
        """Format comparative analysis data for prompt substitution."""
        comparative_insights = self._make_json_serializable(comparative_insights)
        return json.dumps(comparative_insights, indent=2, ensure_ascii=False)

    def _format_strategy_data(self, strategy_performance: Dict[str, Any]) -> str:
        """Format strategy performance data for prompt substitution."""
        strategy_performance = self._make_json_serializable(strategy_performance)
        return json.dumps(strategy_performance, indent=2, ensure_ascii=False)

    @observe(name="mini_report_technical")
    def generate_technical_mini_report(
        self,
        indicators: Dict[str, Any],
        percentiles: Dict[str, Any],
        chart_patterns: list = None,
        pattern_statistics: dict = None,
        financial_markets_data: dict = None
    ) -> str:
        """
        Generate a focused technical analysis mini-report.

        Args:
            indicators: Dictionary of technical indicators
            percentiles: Dictionary of percentile data
            chart_patterns: Optional list of chart patterns from MCP
            pattern_statistics: Optional pattern statistics from MCP
            financial_markets_data: Optional advanced technical data from Financial Markets MCP

        Returns:
            150-200 word Thai narrative focusing on technical analysis
        """
        technical_data = self._format_technical_data(indicators, percentiles)

        # Add MCP data if available
        mcp_data_parts = []
        if chart_patterns:
            mcp_data_parts.append(f"Chart Patterns: {', '.join(chart_patterns)}")
        if pattern_statistics and len(pattern_statistics) > 0:
            stats_str = ", ".join(f"{k}: {v}" for k, v in pattern_statistics.items())
            mcp_data_parts.append(f"Pattern Statistics: {stats_str}")
        if financial_markets_data and len(financial_markets_data) > 0:
            fm_keys = list(financial_markets_data.keys())
            mcp_data_parts.append(f"Advanced Technical Data: {', '.join(fm_keys)}")

        if mcp_data_parts:
            technical_data += "\n\n" + "\n".join(mcp_data_parts)

        prompt = self.prompts['technical'].replace('{technical_data}', technical_data)

        response = self.llm.invoke(prompt)
        return response.content if hasattr(response, 'content') else str(response)

    @observe(name="mini_report_fundamental")
    def generate_fundamental_mini_report(
        self,
        ticker_data: Dict[str, Any],
        sec_filing_data: dict = None
    ) -> str:
        """
        Generate a focused fundamental analysis mini-report.

        Args:
            ticker_data: Dictionary of fundamental data
            sec_filing_data: Optional SEC filing data from SEC EDGAR MCP

        Returns:
            150-200 word Thai narrative focusing on fundamental analysis
        """
        fundamental_data = self._format_fundamental_data(ticker_data)

        # Add SEC filing data if available
        if sec_filing_data and len(sec_filing_data) > 0:
            form_type = sec_filing_data.get('form_type', 'N/A')
            filing_date = sec_filing_data.get('filing_date', 'N/A')
            fundamental_data += f"\n\nSEC Filings: {form_type} filed on {filing_date}"

        prompt = self.prompts['fundamental'].replace('{fundamental_data}', fundamental_data)

        response = self.llm.invoke(prompt)
        return response.content if hasattr(response, 'content') else str(response)

    @observe(name="mini_report_market_conditions")
    def generate_market_conditions_mini_report(
        self,
        indicators: Dict[str, Any],
        percentiles: Dict[str, Any],
        alpaca_data: dict = None
    ) -> str:
        """
        Generate a focused market conditions mini-report.

        Args:
            indicators: Dictionary of market indicators
            percentiles: Dictionary of percentile data
            alpaca_data: Optional real-time market data from Alpaca MCP

        Returns:
            150-200 word Thai narrative focusing on market conditions
        """
        market_data = self._format_market_conditions_data(indicators, percentiles)

        # Add Alpaca real-time data if available
        if alpaca_data and len(alpaca_data) > 0:
            alpaca_keys = list(alpaca_data.keys())
            market_data += f"\n\nReal-time Market Data: {', '.join(alpaca_keys)}"

        prompt = self.prompts['market_conditions'].replace('{market_conditions_data}', market_data)

        response = self.llm.invoke(prompt)
        return response.content if hasattr(response, 'content') else str(response)

    @observe(name="mini_report_news")
    def generate_news_mini_report(self, news: List[Dict[str, Any]], news_summary: Dict[str, Any]) -> str:
        """
        Generate a focused news & events mini-report.

        Args:
            news: List of news items
            news_summary: Summary of news sentiment

        Returns:
            150-200 word Thai narrative focusing on news & events
        """
        news_data = self._format_news_data(news, news_summary)
        prompt = self.prompts['news'].replace('{news_data}', news_data)

        response = self.llm.invoke(prompt)
        return response.content if hasattr(response, 'content') else str(response)

    @observe(name="mini_report_comparative")
    def generate_comparative_mini_report(self, comparative_insights: Dict[str, Any]) -> str:
        """
        Generate a focused comparative analysis mini-report.

        Args:
            comparative_insights: Dictionary of comparative analysis data

        Returns:
            150-200 word Thai narrative focusing on comparative analysis
        """
        comparative_data = self._format_comparative_data(comparative_insights)
        prompt = self.prompts['comparative'].replace('{comparative_data}', comparative_data)

        response = self.llm.invoke(prompt)
        return response.content if hasattr(response, 'content') else str(response)

    @observe(name="mini_report_strategy")
    def generate_strategy_mini_report(
        self,
        strategy_performance: Dict[str, Any],
        portfolio_insights: dict = None
    ) -> str:
        """
        Generate a focused strategy performance mini-report.

        Args:
            strategy_performance: Dictionary of strategy backtest results
            portfolio_insights: Optional portfolio context from Portfolio Manager MCP

        Returns:
            150-200 word Thai narrative focusing on strategy performance
        """
        strategy_data = self._format_strategy_data(strategy_performance)

        # Add portfolio insights if available
        if portfolio_insights and len(portfolio_insights) > 0:
            portfolio_keys = list(portfolio_insights.keys())
            strategy_data += f"\n\nPortfolio Context: {', '.join(portfolio_keys)}"

        prompt = self.prompts['strategy'].replace('{strategy_data}', strategy_data)

        response = self.llm.invoke(prompt)
        return response.content if hasattr(response, 'content') else str(response)
