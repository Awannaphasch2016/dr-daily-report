"""
Simplified Report Generator - No Sink Nodes

Generates reports directly from raw data (from Aurora) without LangGraph workflow.
This bypasses parallel execution and sink nodes since all data is already available.

Purpose:
- Fast iteration on report quality (no API calls)
- Generate multiple strategies on same data
- Cost-efficient (no repeated data fetching)
"""

import logging
import time
from typing import Dict, Any
from langchain_openai import ChatOpenAI
import os

from src.report import PromptBuilder, ContextBuilder, NumberInjector
from src.analysis import MarketAnalyzer
from src.formatters import DataFormatter
from src.analysis.technical_analysis import TechnicalAnalyzer
from src.report.mini_report_generator import MiniReportGenerator
from src.report.transparency_footer import TransparencyFooter

logger = logging.getLogger(__name__)


class SimpleReportGenerator:
    """
    Generate reports from pre-fetched data without workflow orchestration.

    This is used when data is already in Aurora and we just need to regenerate
    the report (e.g., testing new prompts, comparing strategies).
    """

    def __init__(self, llm=None):
        """Initialize report generator with dependencies."""
        self.llm = llm or ChatOpenAI(
            model="openai/gpt-4o",
            temperature=0.8,
            base_url="https://openrouter.ai/api/v1",
            api_key=os.getenv("OPENROUTER_API_KEY")
        )

        self.market_analyzer = MarketAnalyzer()
        self.data_formatter = DataFormatter()
        self.technical_analyzer = TechnicalAnalyzer()
        self.context_builder = ContextBuilder(
            self.market_analyzer,
            self.data_formatter,
            self.technical_analyzer
        )
        self.prompt_builder = PromptBuilder()
        self.number_injector = NumberInjector()
        self.mini_report_generator = MiniReportGenerator(self.llm)
        self.transparency_footer = TransparencyFooter()

    def generate_report(
        self,
        ticker: str,
        raw_data: Dict[str, Any],
        strategy: str = 'single-stage',
        language: str = 'th'
    ) -> Dict[str, Any]:
        """
        Generate report from raw data (no API calls, no sink nodes).

        Args:
            ticker: Ticker symbol (e.g., "DBS19")
            raw_data: Dictionary containing all raw data fields:
                - ticker_data: Price history and fundamentals
                - indicators: Technical indicators
                - percentiles: Statistical percentiles
                - news: News articles list
                - news_summary: News sentiment summary
                - comparative_data: Peer comparison data
                - comparative_insights: Peer analysis
                - chart_patterns: Chart patterns (optional)
                - pattern_statistics: Pattern stats (optional)
                - strategy_performance: Strategy backtest (optional)
                - sec_filing_data: SEC filings (optional)
                - financial_markets_data: MCP data (optional)
                - portfolio_insights: Portfolio context (optional)
                - alpaca_data: Real-time quotes (optional)
            strategy: 'single-stage' or 'multi-stage'
            language: 'th' or 'en'

        Returns:
            Dictionary with:
                - report: Generated report text
                - generation_time_ms: Time taken
                - api_costs: Token usage
                - mini_reports: Mini-reports (if multi-stage)
        """
        start_time = time.perf_counter()
        logger.info(f"Generating {strategy} report for {ticker} from cached data")

        # Extract data from raw_data
        ticker_data = raw_data.get('ticker_data', {})
        indicators = raw_data.get('indicators', {})
        percentiles = raw_data.get('percentiles', {})
        news = raw_data.get('news', [])
        news_summary = raw_data.get('news_summary', {})
        comparative_data = raw_data.get('comparative_data', {})
        comparative_insights = raw_data.get('comparative_insights', {})

        # Optional MCP data
        chart_patterns = raw_data.get('chart_patterns', [])
        pattern_statistics = raw_data.get('pattern_statistics', {})
        strategy_performance = raw_data.get('strategy_performance', {})
        sec_filing_data = raw_data.get('sec_filing_data', {})
        financial_markets_data = raw_data.get('financial_markets_data', {})
        portfolio_insights = raw_data.get('portfolio_insights', {})
        alpaca_data = raw_data.get('alpaca_data', {})

        # Generate report based on strategy
        if strategy == 'multi-stage':
            report, mini_reports, api_costs = self._generate_multistage(
                ticker=ticker,
                ticker_data=ticker_data,
                indicators=indicators,
                percentiles=percentiles,
                news=news,
                news_summary=news_summary,
                comparative_insights=comparative_insights,
                chart_patterns=chart_patterns,
                pattern_statistics=pattern_statistics,
                strategy_performance=strategy_performance,
                sec_filing_data=sec_filing_data,
                financial_markets_data=financial_markets_data,
                portfolio_insights=portfolio_insights,
                alpaca_data=alpaca_data,
                language=language
            )
        else:  # single-stage
            report, api_costs = self._generate_singlestage(
                ticker=ticker,
                ticker_data=ticker_data,
                indicators=indicators,
                percentiles=percentiles,
                news=news,
                news_summary=news_summary,
                comparative_insights=comparative_insights,
                chart_patterns=chart_patterns,
                pattern_statistics=pattern_statistics,
                strategy_performance=strategy_performance,
                sec_filing_data=sec_filing_data,
                financial_markets_data=financial_markets_data,
                portfolio_insights=portfolio_insights,
                alpaca_data=alpaca_data,
                language=language
            )
            mini_reports = {}

        generation_time_ms = int((time.perf_counter() - start_time) * 1000)

        return {
            'report': report,
            'generation_time_ms': generation_time_ms,
            'api_costs': api_costs,
            'mini_reports': mini_reports,
            'strategy': strategy
        }

    def _generate_multistage(self, **kwargs) -> tuple:
        """Generate report using multi-stage approach (6 mini-reports → synthesis)."""
        language = kwargs.get('language', 'th')

        # Generate 6 mini-reports
        mini_reports = {
            'technical': self.mini_report_generator.generate_technical_mini_report(
                indicators=kwargs['indicators'],
                percentiles=kwargs['percentiles'],
                chart_patterns=kwargs.get('chart_patterns'),
                pattern_statistics=kwargs.get('pattern_statistics'),
                financial_markets_data=kwargs.get('financial_markets_data')
            ),
            'fundamental': self.mini_report_generator.generate_fundamental_mini_report(
                ticker_data=kwargs['ticker_data'],
                sec_filing_data=kwargs.get('sec_filing_data')
            ),
            'market_conditions': self.mini_report_generator.generate_market_conditions_mini_report(
                indicators=kwargs['indicators'],
                percentiles=kwargs['percentiles'],
                alpaca_data=kwargs.get('alpaca_data')
            ),
            'news': self.mini_report_generator.generate_news_mini_report(
                news=kwargs['news'],
                news_summary=kwargs['news_summary']
            ),
            'comparative': self.mini_report_generator.generate_comparative_mini_report(
                comparative_insights=kwargs['comparative_insights']
            ),
            'strategy': self.mini_report_generator.generate_strategy_mini_report(
                strategy_performance=kwargs.get('strategy_performance', {}),
                portfolio_insights=kwargs.get('portfolio_insights')
            )
        }

        # Synthesis LLM call
        synthesis_prompt = self._build_synthesis_prompt(mini_reports, kwargs['ticker'], language)
        response = self.llm.invoke(synthesis_prompt)
        report = response.content if hasattr(response, 'content') else str(response)

        # Post-processing: Number injection, news references, transparency footer
        # (Same as single-stage to ensure consistency)
        report = self._post_process_report(
            report=report,
            indicators=kwargs['indicators'],
            percentiles=kwargs['percentiles'],
            news=kwargs['news'],
            language=language,
            strategy='multi-stage',
            ticker_data=kwargs['ticker_data'],
            comparative_insights=kwargs.get('comparative_insights', {}),
            strategy_performance=kwargs.get('strategy_performance', {})
        )

        # Estimate API costs (7 LLM calls: 6 mini + 1 synthesis)
        api_costs = {
            'llm_calls': 7,
            'estimated_input_tokens': 3500,  # Rough estimate
            'estimated_output_tokens': len(report) // 4  # 4 chars per token
        }

        return report, mini_reports, api_costs

    def _generate_singlestage(self, **kwargs) -> tuple:
        """Generate report using single-stage approach (one LLM call)."""
        language = kwargs.get('language', 'th')
        indicators = kwargs['indicators']
        strategy_performance = kwargs.get('strategy_performance', {})

        # Build context
        context = self.context_builder.prepare_context(
            ticker=kwargs['ticker'],
            ticker_data=kwargs['ticker_data'],
            indicators=indicators,
            percentiles=kwargs['percentiles'],
            news=kwargs['news'],
            news_summary=kwargs['news_summary'],
            strategy_performance=strategy_performance,
            comparative_insights=kwargs.get('comparative_insights', {}),
            sec_filing_data=kwargs.get('sec_filing_data', {}),
            financial_markets_data=kwargs.get('financial_markets_data', {}),
            portfolio_insights=kwargs.get('portfolio_insights', {}),
            alpaca_data=kwargs.get('alpaca_data', {})
        )

        # Extract uncertainty score from indicators
        uncertainty_score = indicators.get('uncertainty_score', 0)

        # Build prompt with correct language
        prompt_builder = PromptBuilder(language=language)
        prompt = prompt_builder.build_prompt(context, uncertainty_score, strategy_performance=strategy_performance)

        # LLM call
        response = self.llm.invoke(prompt)
        report = response.content if hasattr(response, 'content') else str(response)

        # Post-processing: Number injection, news references, transparency footer
        report = self._post_process_report(
            report=report,
            indicators=indicators,
            percentiles=kwargs['percentiles'],
            news=kwargs['news'],
            language=language,
            strategy='single-stage',
            ticker_data=kwargs['ticker_data'],
            comparative_insights=kwargs.get('comparative_insights', {}),
            strategy_performance=strategy_performance
        )

        # Calculate API costs
        api_costs = {
            'llm_calls': 1,
            'estimated_input_tokens': len(prompt) // 4,
            'estimated_output_tokens': len(report) // 4
        }

        return report, api_costs

    def _post_process_report(
        self,
        report: str,
        indicators: dict,
        percentiles: dict,
        news: list,
        language: str,
        strategy: str = 'single-stage',
        ticker_data: dict = None,
        comparative_insights: dict = None,
        strategy_performance: dict = None
    ) -> str:
        """
        Post-process report: inject numbers, add news references, add transparency footer.

        Args:
            report: Raw LLM-generated report text
            indicators: Technical indicators dict
            percentiles: Statistical percentiles dict
            news: News articles list
            language: Report language ('th' or 'en')
            strategy: Generation strategy ('single-stage' or 'multi-stage')
            ticker_data: Price history and fundamentals (for transparency footer)
            comparative_insights: Peer comparison insights (for transparency footer)
            strategy_performance: Backtest performance (for transparency footer)

        Returns:
            Post-processed report with number injection, news citations, and transparency footer
        """
        # Calculate market conditions for ground truth
        conditions = self.market_analyzer.calculate_market_conditions(indicators)

        # Build ground truth dict for placeholder replacement
        ground_truth = {
            'uncertainty_score': indicators.get('uncertainty_score', 0),
            'atr_pct': (indicators.get('atr', 0) / indicators.get('current_price', 1)) * 100 if indicators.get('current_price', 0) > 0 else 0,
            'vwap_pct': conditions.get('price_vs_vwap_pct', 0),
            'volume_ratio': conditions.get('volume_ratio', 0),
        }

        # Replace {{PLACEHOLDERS}} with exact values
        report = self.number_injector.inject_deterministic_numbers(
            report,
            ground_truth,
            indicators,
            percentiles,
            ticker_data or {},  # Pass empty dict if None
            comparative_insights or {}  # Pass empty dict if None
        )

        # Add news references
        if news:
            from src.data.news_fetcher import NewsFetcher
            news_fetcher = NewsFetcher()
            news_references = news_fetcher.get_news_references(news)
            report += f"\n\n{news_references}"

        # Add transparency footer (shows data sources used)
        state_for_footer = {
            'indicators': indicators,
            'percentiles': percentiles,
            'news': news,
            'ticker_data': ticker_data or {},
            'comparative_insights': comparative_insights or {},
            'strategy_performance': strategy_performance or {}
        }
        transparency_footer = self.transparency_footer.generate_data_usage_footnote(
            state_for_footer, strategy
        )
        report += f"\n\n{transparency_footer}"

        return report

    def _build_synthesis_prompt(self, mini_reports: Dict[str, str], ticker: str, language: str) -> str:
        """Build synthesis prompt from mini-reports."""
        # Format mini-reports
        formatted = "\n\n".join([
            f"=== {category.upper()} ===\n{content}"
            for category, content in mini_reports.items()
        ])

        prompt = f"""You are a Thai financial analyst synthesizing multiple analytical perspectives into a cohesive narrative.

You have been given 6 specialized mini-reports analyzing {ticker}:
{formatted}

Synthesize these into a single flowing Thai narrative following this structure:
📖 เรื่องราวของหุ้นตัวนี้ (2-3 sentences overview)
💡 สิ่งที่คุณต้องรู้ (3-4 flowing paragraphs, naturally weaving insights from all 6 perspectives)
🎯 ควรทำอะไรตอนนี้? (2-3 sentences, actionable recommendation)
⚠️ ระวังอะไร? (1-2 key risks)

Requirements:
- Write in Thai language, narrative style (no bullet points)
- Weave insights naturally across paragraphs (don't separate by category)
- Support claims with specific numbers from mini-reports
- Keep under 15 lines total
- Natural flowing prose, not structured sections"""

        return prompt
