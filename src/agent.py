from typing import TypedDict, Annotated, Sequence
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage
import operator
from datetime import datetime
import re
import pandas as pd
import time
from src.data_fetcher import DataFetcher
from src.technical_analysis import TechnicalAnalyzer
from src.database import TickerDatabase
from src.news_fetcher import NewsFetcher
from src.chart_generator import ChartGenerator
from src.pdf_generator import PDFReportGenerator
from src.faithfulness_scorer import FaithfulnessScorer
from src.completeness_scorer import CompletenessScorer
from src.reasoning_quality_scorer import ReasoningQualityScorer
from src.compliance_scorer import ComplianceScorer
from src.qos_scorer import QoSScorer
from src.cost_scorer import CostScorer
from src.strategy import SMAStrategyBacktester
from src.comparative_analysis import ComparativeAnalyzer
from src.scoring_service import ScoringService, ScoringContext
from src.formatters import DataFormatter
from src.analysis import MarketAnalyzer, StrategyAnalyzer
from src.report import PromptBuilder, ContextBuilder, NumberInjector
from src.workflow import WorkflowNodes
from src.types import AgentState
import json

class TickerAnalysisAgent:
    def __init__(self):
        self.llm = ChatOpenAI(model="gpt-4o", temperature=0.8)
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
        self.db = TickerDatabase()
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
            db=self.db,
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

    def build_graph(self):
        """
        Build LangGraph workflow with all processing nodes.
        
        Returns:
            Compiled LangGraph workflow ready for execution
        """
        workflow = StateGraph(AgentState)

        # Add nodes
        workflow.add_node("fetch_data", self.workflow_nodes.fetch_data)
        workflow.add_node("fetch_news", self.workflow_nodes.fetch_news)
        workflow.add_node("analyze_technical", self.workflow_nodes.analyze_technical)
        workflow.add_node("fetch_comparative_data", self.workflow_nodes.fetch_comparative_data)
        workflow.add_node("analyze_comparative_insights", self.workflow_nodes.analyze_comparative_insights)
        workflow.add_node("generate_chart", self.workflow_nodes.generate_chart)
        workflow.add_node("generate_report", self.workflow_nodes.generate_report)
        
        # Add edges
        workflow.set_entry_point("fetch_data")
        workflow.add_edge("fetch_data", "fetch_news")
        workflow.add_edge("fetch_news", "analyze_technical")
        workflow.add_edge("analyze_technical", "fetch_comparative_data")
        workflow.add_edge("fetch_comparative_data", "analyze_comparative_insights")
        workflow.add_edge("analyze_comparative_insights", "generate_chart")
        workflow.add_edge("generate_chart", "generate_report")
        workflow.add_edge("generate_report", END)

        return workflow.compile()

    def analyze_ticker(self, ticker: str) -> str:
        """Main entry point to analyze ticker"""
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
            "error": ""
        }

        # Run the graph
        final_state = self.graph.invoke(initial_state)

        # Return error or report
        if final_state.get("error"):
            return f"❌ เกิดข้อผิดพลาด: {final_state['error']}"

        return final_state.get("report", "ไม่สามารถสร้างรายงานได้")

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

