# -*- coding: utf-8 -*-
from typing import TypedDict, Annotated, Sequence
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage
from langsmith import traceable
import operator
from datetime import datetime
import re
import pandas as pd
import time
import os
import logging

# Debug logging for package versions
logger = logging.getLogger(__name__)
try:
    import langchain_openai as _lc_openai
    import openai as _openai
    logger.info(f"📦 Package versions: langchain_openai={_lc_openai.__version__}, openai={_openai.__version__}")
except Exception as e:
    logger.warning(f"⚠️ Could not get package versions: {e}")
from src.types import AgentState
from src.data.data_fetcher import DataFetcher
from src.analysis.technical_analysis import TechnicalAnalyzer
from src.data.news_fetcher import NewsFetcher
from src.formatters.chart_generator import ChartGenerator
from src.formatters.pdf_generator import PDFReportGenerator
from src.scoring.faithfulness_scorer import FaithfulnessScorer
from src.utils.ticker_utils import is_us_ticker, has_mcp_server
from src.scoring.completeness_scorer import CompletenessScorer
from src.scoring.reasoning_quality_scorer import ReasoningQualityScorer
from src.scoring.compliance_scorer import ComplianceScorer
from src.scoring.qos_scorer import QoSScorer
from src.scoring.cost_scorer import CostScorer
from src.utils.strategy import SMAStrategyBacktester
from src.analysis.comparative_analysis import ComparativeAnalyzer
from src.scoring.scoring_service import ScoringService, ScoringContext
from src.formatters import DataFormatter
from src.analysis import MarketAnalyzer, StrategyAnalyzer
from src.report import PromptBuilder, ContextBuilder, NumberInjector
from src.workflow import WorkflowNodes
from src.types import AgentState
import json

class TickerAnalysisAgent:
    def __init__(self):
        api_key = os.getenv("OPENROUTER_API_KEY")
        # Debug logging for API key
        if api_key:
            logger.info(f"🔑 API key loaded: {api_key[:20]}... (length={len(api_key)})")
        else:
            logger.error("❌ OPENROUTER_API_KEY is None or empty!")

        self.llm = ChatOpenAI(
            model="openai/gpt-4o",
            temperature=0.8,
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key
        )
        self.data_fetcher = DataFetcher()
        self.technical_analyzer = TechnicalAnalyzer()
        self.news_fetcher = NewsFetcher()
        self.chart_generator = ChartGenerator()
        self.pdf_generator = PDFReportGenerator(use_thai_font=True)
        self.faithfulness_scorer = FaithfulnessScorer()
        self.completeness_scorer = CompletenessScorer()
        self.reasoning_quality_scorer = ReasoningQualityScorer()
        self.compliance_scorer = ComplianceScorer()
        self.qos_scorer = QoSScorer()
        self.cost_scorer = CostScorer()
        self.scoring_service = ScoringService()
        self.data_formatter = DataFormatter()
        self.strategy_backtester = SMAStrategyBacktester(fast_period=20, slow_period=50)
        self.comparative_analyzer = ComparativeAnalyzer()
        self.market_analyzer = MarketAnalyzer()
        self.strategy_analyzer = StrategyAnalyzer(self.strategy_backtester)
        self.prompt_builder = PromptBuilder()
        self.context_builder = ContextBuilder(self.market_analyzer, self.data_formatter, self.technical_analyzer)
        self.number_injector = NumberInjector()
        self.ticker_map = self.data_fetcher.load_tickers()
        
        # Track database query count for QoS (using list for shared mutable reference)
        self._db_query_count = [0]
        
        # Initialize workflow nodes
        self.workflow_nodes = WorkflowNodes(
            data_fetcher=self.data_fetcher,
            technical_analyzer=self.technical_analyzer,
            news_fetcher=self.news_fetcher,
            chart_generator=self.chart_generator,
            strategy_backtester=self.strategy_backtester,
            strategy_analyzer=self.strategy_analyzer,
            comparative_analyzer=self.comparative_analyzer,
            llm=self.llm,
            context_builder=self.context_builder,
            prompt_builder=self.prompt_builder,
            market_analyzer=self.market_analyzer,
            number_injector=self.number_injector,
            cost_scorer=self.cost_scorer,
            scoring_service=self.scoring_service,
            qos_scorer=self.qos_scorer,
            faithfulness_scorer=self.faithfulness_scorer,
            completeness_scorer=self.completeness_scorer,
            reasoning_quality_scorer=self.reasoning_quality_scorer,
            compliance_scorer=self.compliance_scorer,
            ticker_map=self.ticker_map,
            db_query_count_ref=self._db_query_count
        )
        
        self.graph = self.build_graph()

    def _route_after_fetch_data(self, state: AgentState) -> str:
        """
        PHASE 2: Conditional Routing - Route to appropriate next node based on ticker type.

        Skips Alpaca MCP for non-US tickers (saves ~1s latency).

        Args:
            state: Current workflow state

        Returns:
            Name of next node to execute
        """
        ticker = state.get("ticker", "")
        yahoo_ticker = self.ticker_map.get(ticker.upper())

        # Skip Alpaca for non-US tickers
        if yahoo_ticker and is_us_ticker(yahoo_ticker):
            return "fetch_alpaca_data"
        else:
            # Skip directly to news for non-US tickers
            return "fetch_news"

    def _route_after_financial_markets(self, state: AgentState) -> str:
        """
        Conditional routing after financial_markets - skip SEC filing for non-US tickers.

        Args:
            state: Current workflow state

        Returns:
            Name of next node to execute
        """
        ticker = state.get("ticker", "")
        yahoo_ticker = self.ticker_map.get(ticker.upper())

        # Only fetch SEC filings for US tickers
        if yahoo_ticker and is_us_ticker(yahoo_ticker):
            return "fetch_sec_filing"
        else:
            # Skip SEC filing for non-US, go straight to portfolio insights
            return "fetch_portfolio_insights"

    def build_graph(self):
        """
        Build LangGraph workflow with 3 parallel pipelines and sink nodes.

        Graph Structure:
        - fetch_data (entry)
          ├─→ Technical Pipeline: analyze_technical → merge_fund_tech_data
          ├─→ Chart Pipeline: generate_chart → merge_all_pipelines
          └─→ Fundamental Pipeline: [6 parallel fetches] → merge_fundamental_data → merge_fund_tech_data
                                     → [score + insights in parallel] → merge_all_pipelines
                                     → generate_report

        Returns:
            Compiled LangGraph workflow ready for execution
        """
        workflow = StateGraph(AgentState)

        # Add all nodes
        workflow.add_node("fetch_data", self.workflow_nodes.fetch_data)

        # Fundamental fetch nodes (6 parallel)
        workflow.add_node("fetch_news", self.workflow_nodes.fetch_news)
        workflow.add_node("fetch_alpaca_data", self.workflow_nodes.fetch_alpaca_data)
        workflow.add_node("fetch_financial_markets_data", self.workflow_nodes.fetch_financial_markets_data)
        workflow.add_node("fetch_sec_filing", self.workflow_nodes.fetch_sec_filing)
        workflow.add_node("fetch_portfolio_insights", self.workflow_nodes.fetch_portfolio_insights)
        workflow.add_node("fetch_comparative_data", self.workflow_nodes.fetch_comparative_data)

        # Technical pipeline node
        workflow.add_node("analyze_technical", self.workflow_nodes.analyze_technical)

        # Chart pipeline node
        workflow.add_node("generate_chart", self.workflow_nodes.generate_chart)

        # Sink nodes
        workflow.add_node("merge_fundamental_data", self.workflow_nodes.merge_fundamental_data)
        workflow.add_node("merge_fund_tech_data", self.workflow_nodes.merge_fund_tech_data)
        workflow.add_node("merge_all_pipelines", self.workflow_nodes.merge_all_pipelines)

        # Analysis nodes (parallel wave 2)
        workflow.add_node("score_user_facing", self.workflow_nodes.score_user_facing)
        workflow.add_node("analyze_comparative_insights", self.workflow_nodes.analyze_comparative_insights)

        # Final report node
        workflow.add_node("generate_report", self.workflow_nodes.generate_report)

        # ========== GRAPH STRUCTURE ==========
        # Entry point
        workflow.set_entry_point("fetch_data")

        # PIPELINE 1: Technical (fetch_data → analyze_technical → merge_fund_tech_data)
        workflow.add_edge("fetch_data", "analyze_technical")

        # PIPELINE 2: Fundamental - Fan out to 6 parallel fetches
        workflow.add_edge("fetch_data", "fetch_news")
        workflow.add_edge("fetch_data", "fetch_alpaca_data")
        workflow.add_edge("fetch_data", "fetch_financial_markets_data")
        workflow.add_edge("fetch_data", "fetch_sec_filing")
        workflow.add_edge("fetch_data", "fetch_portfolio_insights")
        workflow.add_edge("fetch_data", "fetch_comparative_data")

        # SINK 1: Merge 6 fundamental fetches
        workflow.add_edge("fetch_news", "merge_fundamental_data")
        workflow.add_edge("fetch_alpaca_data", "merge_fundamental_data")
        workflow.add_edge("fetch_financial_markets_data", "merge_fundamental_data")
        workflow.add_edge("fetch_sec_filing", "merge_fundamental_data")
        workflow.add_edge("fetch_portfolio_insights", "merge_fundamental_data")
        workflow.add_edge("fetch_comparative_data", "merge_fundamental_data")

        # SINK 2: Merge fundamental + technical
        workflow.add_edge("merge_fundamental_data", "merge_fund_tech_data")
        workflow.add_edge("analyze_technical", "merge_fund_tech_data")

        # PARALLEL WAVE 2: score_user_facing AND analyze_comparative_insights AND generate_chart
        # (all run after merge_fund_tech_data completes)
        workflow.add_edge("merge_fund_tech_data", "score_user_facing")
        workflow.add_edge("merge_fund_tech_data", "analyze_comparative_insights")
        workflow.add_edge("merge_fund_tech_data", "generate_chart")

        # SINK 3: Merge all pipelines (scores + insights + chart)
        workflow.add_edge("score_user_facing", "merge_all_pipelines")
        workflow.add_edge("analyze_comparative_insights", "merge_all_pipelines")
        workflow.add_edge("generate_chart", "merge_all_pipelines")

        # Final report generation
        workflow.add_edge("merge_all_pipelines", "generate_report")
        workflow.add_edge("generate_report", END)

        return workflow.compile()

    @traceable(name="analyze_ticker", tags=["agent", "workflow"])
    def analyze_ticker(self, ticker: str, strategy: str = "single-stage", language: str = 'th') -> AgentState:
        """
        Main entry point to analyze ticker

        Args:
            ticker: Ticker symbol to analyze
            strategy: Report generation strategy - 'single-stage' or 'multi-stage' (default: 'single-stage')
            language: Report language - 'th' for Thai or 'en' for English (default: 'th')

        Returns:
            Final workflow state dict (AgentState) containing:
            - report: Generated report text (str)
            - ticker_data: Historical price and company data (dict)
            - indicators: Technical indicators (dict)
            - percentiles: Statistical percentiles (dict)
            - news: News articles (list)
            - comparative_data: Peer comparison data (dict)
            - chart_base64: Base64-encoded chart (str)
            - scores: Quality scores (dict)
            - error: Error message if workflow failed (str)
            - Other workflow state fields

        Note:
            To extract just the report text, use: `result.get("report", "")`
        """
        initial_state = {
            "messages": [],
            "ticker": ticker,
            "ticker_data": {},
            "indicators": {},
            "percentiles": {},
            "chart_patterns": [],
            "pattern_statistics": {},
            "strategy_performance": {},
            "news": [],
            "news_summary": {},
            "comparative_data": {},
            "comparative_insights": {},
            "chart_base64": "",
            "report": "",
            "faithfulness_score": {},
            "completeness_score": {},
            "reasoning_quality_score": {},
            "compliance_score": {},
            "qos_score": {},
            "cost_score": {},
            "timing_metrics": {},
            "api_costs": {},
            "database_metrics": {},
            "sec_filing_data": {},  # SEC EDGAR filing data (MCP-enhanced, disabled)
            "financial_markets_data": {},  # Financial Markets MCP data
            "portfolio_insights": {},  # Portfolio Manager MCP data
            "alpaca_data": {},  # Alpaca MCP data
            "error": "",
            "strategy": strategy,  # Add strategy to state
            "language": language  # Add language to state
        }

        # Run the graph
        final_state = self.graph.invoke(initial_state)

        # Return full state dict for downstream processing (precompute service needs full state)
        # Error handling moved to callers who expect string vs dict
        return final_state

    def generate_pdf_report(self, ticker: str, output_path: str = None) -> bytes:
        """
        Generate PDF report for ticker analysis

        Args:
            ticker: Ticker symbol
            output_path: Optional path to save PDF file (if None, returns bytes)

        Returns:
            PDF bytes if output_path is None, otherwise saves to file and returns bytes
        """
        # Run analysis
        initial_state = {
            "messages": [],
            "ticker": ticker,
            "ticker_data": {},
            "indicators": {},
            "percentiles": {},
            "chart_patterns": [],
            "pattern_statistics": {},
            "strategy_performance": {},
            "news": [],
            "news_summary": {},
            "comparative_data": {},
            "comparative_insights": {},
            "chart_base64": "",
            "report": "",
            "faithfulness_score": {},
            "completeness_score": {},
            "reasoning_quality_score": {},
            "compliance_score": {},
            "qos_score": {},
            "cost_score": {},
            "timing_metrics": {},
            "api_costs": {},
            "database_metrics": {},
            "sec_filing_data": {},  # SEC EDGAR filing data (MCP-enhanced, disabled)
            "financial_markets_data": {},  # Financial Markets MCP data
            "portfolio_insights": {},  # Portfolio Manager MCP data
            "alpaca_data": {},  # Alpaca MCP data
            "error": ""
        }

        # Run the graph
        final_state = self.graph.invoke(initial_state)

        # Check for errors
        if final_state.get("error"):
            raise ValueError(f"Analysis failed: {final_state['error']}")

        # Generate PDF
        pdf_bytes = self.pdf_generator.generate_report(
            ticker=ticker,
            ticker_data=final_state.get("ticker_data", {}),
            indicators=final_state.get("indicators", {}),
            percentiles=final_state.get("percentiles", {}),
            news=final_state.get("news", []),
            news_summary=final_state.get("news_summary", {}),
            chart_base64=final_state.get("chart_base64", ""),
            report=final_state.get("report", ""),
            output_path=output_path
        )

        return pdf_bytes

