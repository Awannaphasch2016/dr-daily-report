# -*- coding: utf-8 -*-
"""Workflow nodes for LangGraph ticker analysis agent"""

import logging
from typing import TypedDict
import time
import json
from datetime import datetime, date
import pandas as pd
import numpy as np
from langchain_core.messages import HumanMessage
from concurrent.futures import ThreadPoolExecutor, as_completed

from src.types import AgentState
from src.data.aurora.precompute_service import PrecomputeService
from src.evaluation import observe, get_langchain_handler, set_observation_level
import os

# Setup logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class WorkflowNodes:
    """Encapsulates all LangGraph workflow node methods"""

    def __init__(
        self,
        data_fetcher,
        technical_analyzer,
        news_fetcher,
        chart_generator,
        strategy_backtester,
        strategy_analyzer,
        comparative_analyzer,
        llm,
        context_builder,
        prompt_builder,
        market_analyzer,
        number_injector,
        cost_scorer,
        scoring_service,
        qos_scorer,
        faithfulness_scorer,
        completeness_scorer,
        reasoning_quality_scorer,
        compliance_scorer,
        ticker_map,
        db_query_count_ref
    ):
        """
        Initialize WorkflowNodes with all required dependencies

        Args:
            db_query_count_ref: Reference to _db_query_count from agent (for shared state)
        """
        self.data_fetcher = data_fetcher
        self.technical_analyzer = technical_analyzer
        self.news_fetcher = news_fetcher
        self.chart_generator = chart_generator
        self.strategy_backtester = strategy_backtester
        self.strategy_analyzer = strategy_analyzer
        self.comparative_analyzer = comparative_analyzer
        self.llm = llm
        self.context_builder = context_builder
        self.prompt_builder = prompt_builder
        self.market_analyzer = market_analyzer
        self.number_injector = number_injector
        self.cost_scorer = cost_scorer
        self.scoring_service = scoring_service
        self.qos_scorer = qos_scorer
        self.faithfulness_scorer = faithfulness_scorer
        self.completeness_scorer = completeness_scorer
        self.reasoning_quality_scorer = reasoning_quality_scorer
        self.compliance_scorer = compliance_scorer
        self.ticker_map = ticker_map
        self._db_query_count_ref = db_query_count_ref
        # Track node execution for summary
        self._node_execution_log = []

    def _log_node_start(self, node_name: str, state: AgentState):
        """Log node execution start"""
        ticker = state.get("ticker", "UNKNOWN")
        logger.info(f"🟢 [{node_name}] START - Ticker: {ticker}")
        self._node_execution_log.append({
            'node': node_name,
            'ticker': ticker,
            'status': 'started',
            'timestamp': datetime.now().isoformat()
        })

    def _log_node_success(self, node_name: str, state: AgentState, details: dict = None):
        """Log node execution success"""
        ticker = state.get("ticker", "UNKNOWN")
        details_str = f" - {details}" if details else ""
        logger.info(f"✅ [{node_name}] SUCCESS - Ticker: {ticker}{details_str}")
        self._node_execution_log.append({
            'node': node_name,
            'ticker': ticker,
            'status': 'success',
            'timestamp': datetime.now().isoformat(),
            'details': details or {}
        })

    def _log_node_error(self, node_name: str, state: AgentState, error_msg: str):
        """Log node execution error"""
        ticker = state.get("ticker", "UNKNOWN")
        logger.error(f"❌ [{node_name}] ERROR - Ticker: {ticker} - {error_msg}")
        self._node_execution_log.append({
            'node': node_name,
            'ticker': ticker,
            'status': 'error',
            'timestamp': datetime.now().isoformat(),
            'error': error_msg
        })

    def _log_node_skip(self, node_name: str, state: AgentState, reason: str):
        """Log node execution skip"""
        ticker = state.get("ticker", "UNKNOWN")
        logger.warning(f"⏭️  [{node_name}] SKIPPED - Ticker: {ticker} - Reason: {reason}")
        self._node_execution_log.append({
            'node': node_name,
            'ticker': ticker,
            'status': 'skipped',
            'timestamp': datetime.now().isoformat(),
            'reason': reason
        })

    def _validate_state_field(self, state: AgentState, field_name: str, node_name: str) -> bool:
        """Validate that a state field is not None"""
        value = state.get(field_name)
        if value is None:
            logger.warning(f"⚠️  [{node_name}] VALIDATION WARNING - Field '{field_name}' is None")
            return False
        return True

    def _validate_state_fields(self, state: AgentState, required_fields: list, node_name: str) -> dict:
        """Validate multiple state fields and return validation results"""
        results = {}
        for field in required_fields:
            results[field] = self._validate_state_field(state, field, node_name)
        return results

    def _reconstruct_data_from_aurora(self, ticker_data: dict, ticker: str, yahoo_ticker: str) -> dict:
        """Reconstruct ticker data dict from Aurora storage.

        Args:
            ticker_data: Result from PrecomputeService.get_ticker_data()
            ticker: Original ticker symbol (e.g., 'DBS19')
            yahoo_ticker: Resolved Yahoo symbol (e.g., 'D05.SI')

        Returns:
            Dict in same format as expected by workflow (with 'history' DataFrame)
        """
        # Parse JSON fields from Aurora
        price_history = ticker_data.get('price_history', [])
        company_info = ticker_data.get('company_info', {})

        # Reconstruct DataFrame from cached price_history
        if isinstance(price_history, list) and len(price_history) > 0:
            hist = pd.DataFrame(price_history)
        else:
            logger.warning(f"Empty price_history in Aurora cache for {ticker}")
            hist = pd.DataFrame()

        # Extract latest price data (same as DataFetcher.fetch_ticker_data)
        if not hist.empty:
            latest = hist.iloc[-1]
            latest_date = latest.get('Date', date.today())
        else:
            latest = {}
            latest_date = date.today()

        # Reconstruct data dict (same structure as Yahoo Finance fetch)
        data = {
            'date': latest_date,
            'open': latest.get('Open') if not hist.empty else None,
            'high': latest.get('High') if not hist.empty else None,
            'low': latest.get('Low') if not hist.empty else None,
            'close': latest.get('Close') if not hist.empty else None,
            'volume': latest.get('Volume') if not hist.empty else None,
            'market_cap': company_info.get('market_cap'),
            'pe_ratio': company_info.get('pe_ratio'),
            'eps': company_info.get('eps'),
            'dividend_yield': company_info.get('dividend_yield'),
            'sector': company_info.get('sector'),
            'industry': company_info.get('industry'),
            'company_name': company_info.get('company_name', yahoo_ticker),
            'history': hist
        }

        logger.info(f"   📦 Reconstructed data from Aurora: {len(hist)} rows, company={data['company_name']}")
        return data

    def get_workflow_summary(self) -> dict:
        """Get summary of workflow node execution"""
        summary = {
            'total_nodes': len(self._node_execution_log),
            'nodes': self._node_execution_log,
            'success_count': sum(1 for n in self._node_execution_log if n['status'] == 'success'),
            'error_count': sum(1 for n in self._node_execution_log if n['status'] == 'error'),
            'skipped_count': sum(1 for n in self._node_execution_log if n['status'] == 'skipped')
        }
        return summary

    def log_workflow_summary(self, state: AgentState):
        """Log comprehensive workflow execution summary"""
        summary = self.get_workflow_summary()
        ticker = state.get("ticker", "UNKNOWN")

        logger.info("=" * 80)
        logger.info(f"📊 WORKFLOW EXECUTION SUMMARY - Ticker: {ticker}")
        logger.info("=" * 80)

        for node_log in summary['nodes']:
            status_emoji = {
                'started': '🟢',
                'success': '✅',
                'error': '❌',
                'skipped': '⏭️'
            }.get(node_log['status'], '❓')

            logger.info(f"{status_emoji} [{node_log['node']}] {node_log['status'].upper()}")
            if node_log.get('error'):
                logger.info(f"   Error: {node_log['error']}")
            if node_log.get('reason'):
                logger.info(f"   Reason: {node_log['reason']}")
            if node_log.get('details'):
                logger.info(f"   Details: {node_log['details']}")

        logger.info("-" * 80)
        logger.info(f"Total Nodes: {summary['total_nodes']}")
        logger.info(f"✅ Success: {summary['success_count']}")
        logger.info(f"❌ Errors: {summary['error_count']}")
        logger.info(f"⏭️  Skipped: {summary['skipped_count']}")
        logger.info("=" * 80)

        # Validate critical state fields
        critical_fields = {
            'fetch_data': ['ticker_data'],
            'fetch_news': ['news', 'news_summary'],
            'analyze_technical': ['indicators', 'percentiles'],
            'generate_chart': ['chart_base64'],
            'generate_report': ['report']
        }

        logger.info("🔍 STATE FIELD VALIDATION:")
        for node_name, fields in critical_fields.items():
            node_logs = [n for n in summary['nodes'] if n['node'] == node_name]
            if node_logs and node_logs[-1]['status'] == 'success':
                validation = self._validate_state_fields(state, fields, node_name)
                for field, is_valid in validation.items():
                    status = "✅" if is_valid else "❌"
                    logger.info(f"   {status} {node_name}.{field}: {'OK' if is_valid else 'MISSING/NONE'}")

        logger.info("=" * 80)

    @observe(name="fetch_data")
    def fetch_data(self, state: AgentState) -> AgentState:
        """Fetch ticker data from Aurora (ground truth)

        Aurora is the primary data store - data is pre-populated nightly by scheduler.
        If data is missing, pipeline fails explicitly (no fallback to external APIs).

        Flow:
        1. Query Aurora ticker_data for ticker data
        2. If found -> use data (Aurora is ground truth)
        3. If missing -> FAIL (data not ready, run scheduler to populate Aurora)
        """
        self._log_node_start("fetch_data", state)
        start_time = time.perf_counter()
        ticker = state["ticker"]

        # Reset query count at start of new run
        self._db_query_count_ref[0] = 0

        # Get Yahoo ticker from symbol
        yahoo_ticker = self.ticker_map.get(ticker.upper())

        if not yahoo_ticker:
            error_msg = f"ไม่พบข้อมูล ticker สำหรับ {ticker}"
            state["error"] = error_msg
            set_observation_level("ERROR")
            self._log_node_error("fetch_data", state, error_msg)
            return state

        logger.info(f"   📊 Fetching data for {ticker} -> {yahoo_ticker}")

        # Query Aurora for ticker data (ground truth)
        precompute_service = PrecomputeService()
        # Use Bangkok timezone for business dates (CLAUDE.md Principle #14: Timezone Discipline)
        from datetime import datetime
        from zoneinfo import ZoneInfo
        bangkok_tz = ZoneInfo("Asia/Bangkok")
        ticker_data = precompute_service.get_ticker_data(symbol=ticker, data_date=datetime.now(bangkok_tz).date())

        if not ticker_data:
            # Data not available - FAIL FAST (no fallback)
            error_msg = (
                f"Data not available in Aurora for {ticker}. "
                f"Run scheduler to populate ticker data before generating reports."
            )
            state["error"] = error_msg
            set_observation_level("ERROR")
            logger.error(f"   ❌ {error_msg}")
            self._log_node_error("fetch_data", state, error_msg)
            return state

        # Data found - Use Aurora as ground truth
        logger.info(f"   ✅ Data found in Aurora for {ticker}")
        data = self._reconstruct_data_from_aurora(ticker_data, ticker, yahoo_ticker)

        # Record timing
        elapsed = time.perf_counter() - start_time
        timing_metrics = state.get("timing_metrics", {})
        timing_metrics["data_fetch"] = elapsed
        state["timing_metrics"] = timing_metrics

        state["ticker_data"] = data

        # Validate output
        if not self._validate_state_field(state, "ticker_data", "fetch_data"):
            self._log_node_error("fetch_data", state, "ticker_data is None after reconstruction")
        else:
            details = {
                'yahoo_ticker': yahoo_ticker,
                'source': 'aurora',
                'has_history': 'history' in data and data['history'] is not None,
                'duration_ms': f"{elapsed*1000:.2f}"
            }
            self._log_node_success("fetch_data", state, details)

        return state

    def fetch_news(self, state: AgentState) -> dict:
        """
        Fetch high-impact news for the ticker.

        Returns partial state with only modified fields (for parallel execution).
        """
        self._log_node_start("fetch_news", state)

        if state.get("error"):
            self._log_node_skip("fetch_news", state, "Previous error in workflow")
            return {}  # Return empty dict, don't propagate error

        start_time = time.perf_counter()
        yahoo_ticker = self.ticker_map.get(state["ticker"].upper())
        if not yahoo_ticker:
            self._log_node_skip("fetch_news", state, "No yahoo_ticker found")
            return {
                "news": [],
                "news_summary": {}
            }

        logger.info(f"   📰 Fetching news for {yahoo_ticker}")

        # Fetch high-impact news (min score 40, max 5 items)
        high_impact_news = self.news_fetcher.filter_high_impact_news(
            yahoo_ticker,
            min_score=40.0,
            max_news=5
        )

        # Get news summary statistics
        news_summary = self.news_fetcher.get_news_summary(high_impact_news)

        # Log success with timing
        elapsed = time.perf_counter() - start_time
        details = {
            'news_count': len(high_impact_news),
            'positive': news_summary.get('positive_count', 0),
            'negative': news_summary.get('negative_count', 0),
            'neutral': news_summary.get('neutral_count', 0),
            'duration_ms': f"{elapsed*1000:.2f}"
        }
        self._log_node_success("fetch_news", state, details)

        # Return only modified fields (partial state)
        return {
            "news": high_impact_news,
            "news_summary": news_summary
        }

    @observe(name="analyze_technical")
    def analyze_technical(self, state: AgentState) -> dict:
        """
        Analyze technical indicators with percentile analysis.

        Returns partial state with only modified fields (for parallel execution).
        """
        self._log_node_start("analyze_technical", state)

        if state.get("error"):
            self._log_node_skip("analyze_technical", state, "Previous error in workflow")
            return {}  # Return empty dict, don't propagate error

        # VALIDATION GATE - check prerequisite data exists and is non-empty
        ticker_data = state.get("ticker_data")
        if not ticker_data or len(ticker_data) == 0:
            error_msg = f"Cannot analyze technical: ticker_data is empty or missing for {state.get('ticker')}"
            logger.error(error_msg)
            self._log_node_error("analyze_technical", state, error_msg)
            return {"error": error_msg}

        start_time = time.perf_counter()
        hist_data = ticker_data.get('history')

        if hist_data is None or hist_data.empty:
            error_msg = "ไม่มีข้อมูลประวัติสำหรับการวิเคราะห์"
            self._log_node_error("analyze_technical", state, error_msg)
            return {"error": error_msg}

        logger.info(f"   📈 Analyzing technical indicators (data points: {len(hist_data)})")

        # Calculate indicators with percentiles
        result = self.technical_analyzer.calculate_all_indicators_with_percentiles(hist_data)

        if not result or not result.get('indicators'):
            error_msg = "ไม่สามารถคำนวณ indicators ได้"
            self._log_node_error("analyze_technical", state, error_msg)
            return {"error": error_msg}

        indicators = result['indicators']
        percentiles = result.get('percentiles', {})
        chart_patterns = result.get('chart_patterns', [])
        pattern_statistics = result.get('pattern_statistics', {})

        # Calculate strategy performance
        strategy_performance = {}
        if self.strategy_backtester:
            try:
                buy_results = self.strategy_backtester.backtest_buy_only(hist_data)
                sell_results = self.strategy_backtester.backtest_sell_only(hist_data)

                if buy_results and sell_results:
                    strategy_performance = {
                        'buy_only': buy_results,
                        'sell_only': sell_results,
                        'last_buy_signal': self.strategy_analyzer.get_last_buy_signal(hist_data),
                        'last_sell_signal': self.strategy_analyzer.get_last_sell_signal(hist_data)
                    }
            except Exception as e:
                logger.warning(f"   ⚠️  Error calculating strategy performance: {str(e)}")
                strategy_performance = {}

        # Validate output
        elapsed = time.perf_counter() - start_time
        details = {
            'indicators_count': len(indicators),
            'percentiles_count': len(percentiles),
            'patterns_count': len(chart_patterns),
            'has_strategy': bool(strategy_performance),
            'duration_ms': f"{elapsed*1000:.2f}"
        }
        self._log_node_success("analyze_technical", state, details)

        # Return only modified fields (partial state)
        return {
            "indicators": indicators,
            "percentiles": percentiles,
            "chart_patterns": chart_patterns,
            "pattern_statistics": pattern_statistics,
            "strategy_performance": strategy_performance
        }

    def fetch_sec_filing(self, state: AgentState) -> dict:
        """
        Fetch SEC filing - DISABLED for Thai market focus.

        This node is disabled by default. Set ENABLE_SEC_EDGAR=true to enable.

        Returns partial state with only modified fields (for parallel execution).
        """
        self._log_node_start("fetch_sec_filing", state)

        # Always skip - SEC EDGAR disabled for Thai market focus
        self._log_node_skip("fetch_sec_filing", state, "SEC EDGAR disabled (Thai market focus)")

        # Return only modified fields (partial state)
        return {"sec_filing_data": {}}

    def score_user_facing(self, state: AgentState) -> dict:
        """
        Calculate user-facing investment scores (0-10 scale).

        Returns partial state with only modified fields (for parallel execution).
        """
        self._log_node_start("score_user_facing", state)

        if state.get("error"):
            self._log_node_skip("score_user_facing", state, "Previous error in workflow")
            return {}  # Return empty dict, don't propagate error

        start_time = time.perf_counter()
        scores = {}

        try:
            from src.scoring.user_facing_scorer import UserFacingScorer
            scorer = UserFacingScorer()

            logger.info("   🎯 Calculating user-facing scores")

            scores = scorer.calculate_all_scores(
                ticker_data=state.get("ticker_data", {}),
                indicators=state.get("indicators", {}),
                percentiles=state.get("percentiles", {})
            )

            # Validate output
            if scores and len(scores) >= 5:
                elapsed = time.perf_counter() - start_time
                details = {
                    'scores_count': len(scores),
                    'categories': list(scores.keys()),
                    'duration_ms': f"{elapsed*1000:.2f}"
                }
                self._log_node_success("score_user_facing", state, details)
            else:
                self._log_node_error("score_user_facing", state, f"Insufficient scores: {len(scores) if scores else 0}")

        except Exception as e:
            error_msg = f"Failed to calculate scores: {e}"
            self._log_node_error("score_user_facing", state, error_msg)
            return {"error": error_msg}

        # Return only modified fields (partial state)
        return {"user_facing_scores": scores}

    @observe(name="generate_chart")
    def generate_chart(self, state: AgentState) -> dict:
        """
        Generate technical analysis chart.

        Returns partial state with only modified fields (for parallel execution).
        """
        self._log_node_start("generate_chart", state)

        if state.get("error"):
            self._log_node_skip("generate_chart", state, "Previous error in workflow")
            return {}  # Return empty dict, don't propagate error

        start_time = time.perf_counter()
        chart_base64 = ""

        try:
            ticker = state["ticker"]
            ticker_data = state["ticker_data"]
            indicators = state.get("indicators", {})

            # Skip if no indicators (might happen in parallel execution)
            if not indicators:
                logger.warning(f"   ⚠️  No indicators available for {ticker}, skipping chart")
                self._log_node_skip("generate_chart", state, "No indicators available")
                return {"chart_base64": ""}

            logger.info(f"   📊 Generating chart for {ticker}")

            # Generate chart (90 days by default)
            chart_base64 = self.chart_generator.generate_chart(
                ticker_data=ticker_data,
                indicators=indicators,
                ticker_symbol=ticker,
                days=90
            )

            # Validate output
            if chart_base64:
                elapsed = time.perf_counter() - start_time
                details = {
                    'chart_size_bytes': len(chart_base64),
                    'duration_ms': f"{elapsed*1000:.2f}"
                }
                self._log_node_success("generate_chart", state, details)
            else:
                self._log_node_error("generate_chart", state, "chart_base64 is empty")

        except Exception as e:
            logger.error(f"   ⚠️  Chart generation failed: {str(e)}")
            # Don't set error - chart is optional, continue without it
            chart_base64 = ""
            set_observation_level("WARNING")  # Degraded but not fatal
            self._log_node_error("generate_chart", state, f"Exception: {str(e)}")

        # Return only modified fields (partial state)
        return {"chart_base64": chart_base64}

    @observe(name="generate_report")
    def generate_report(self, state: AgentState) -> AgentState:
        """Generate Thai language report using LLM with Semantic Layer Architecture"""
        self._log_node_start("generate_report", state)

        if state.get("error"):
            self._log_node_skip("generate_report", state, "Previous error in workflow")
            return state

        # VALIDATION GATE - check prerequisite data exists and is non-empty
        ticker_data = state.get("ticker_data")
        indicators = state.get("indicators")

        if not ticker_data or len(ticker_data) == 0:
            error_msg = f"Cannot generate report: ticker_data is empty or missing for {state.get('ticker')}"
            logger.error(error_msg)
            state["error"] = error_msg
            set_observation_level("ERROR")
            self._log_node_error("generate_report", state, error_msg)
            return state

        if not indicators or len(indicators) == 0:
            error_msg = f"Cannot generate report: indicators is empty or missing for {state.get('ticker')}"
            logger.error(error_msg)
            state["error"] = error_msg
            set_observation_level("ERROR")
            self._log_node_error("generate_report", state, error_msg)
            return state

        # Generate report using Semantic Layer Architecture (single-stage only)
        return self._generate_report_singlestage(state)

    def _post_process_report_workflow(
        self,
        report: str,
        state: AgentState,
        indicators: dict
    ) -> str:
        """
        Apply all post-processing steps to generated report (Thai only).

        Steps:
        1. Calculate ground truth from indicators
        2. Inject deterministic numbers (replace {{PLACEHOLDERS}})
        3. Add news references
        4. Add transparency footer

        Note: Percentile analysis removed (Thai reports don't show it)
        Uses Semantic Layer Architecture (three-layer pattern)

        Args:
            report: Raw LLM-generated report
            state: Complete workflow state
            indicators: Technical indicators

        Returns:
            Post-processed report with all enhancements
        """
        # Step 1: Calculate ground truth for number injection
        conditions = self.market_analyzer.calculate_market_conditions(indicators)
        ground_truth = {
            'uncertainty_score': indicators.get('uncertainty_score', 0),
            'atr_pct': (indicators.get('atr', 0) / indicators.get('current_price', 1)) * 100
                       if indicators.get('current_price', 0) > 0 else 0,
            'vwap_pct': conditions.get('price_vs_vwap_pct', 0),
            'volume_ratio': conditions.get('volume_ratio', 0),
        }

        # Step 2: Replace {{PLACEHOLDERS}} with exact values
        percentiles = state.get('percentiles', {})
        strategy_performance = state.get('strategy_performance', {})
        report = self.number_injector.inject_deterministic_numbers(
            report,
            ground_truth,
            indicators,
            percentiles,
            state.get('ticker_data') or {},
            state.get('comparative_insights') or {},
            strategy_performance=strategy_performance  # Pass strategy data for placeholder replacement
        )

        # Step 3: Add news references
        news = state.get('news', [])
        if news:
            news_references = self.news_fetcher.get_news_references(news)
            report += f"\n\n{news_references}"

        # Step 4: Add transparency footer (Thai only, no percentile section)
        from src.report import TransparencyFooter
        transparency = TransparencyFooter()
        footnote = transparency.generate_data_usage_footnote(state)
        report += footnote

        return report

    def _generate_report_singlestage(self, state: AgentState) -> AgentState:
        """
        Generate report using Semantic Layer Architecture (three-layer pattern).

        Layer 1: Raw numeric calculations → Ground truth values
        Layer 2: Semantic state classification → Categorical labels
        Layer 3: LLM narrative synthesis → Natural language constrained by states
        """

        llm_start_time = time.perf_counter()
        logger.info(f"   📝 Generating report with LLM")
        ticker = state["ticker"]
        ticker_data = state["ticker_data"]
        indicators = state["indicators"]
        percentiles = state.get("percentiles", {})
        chart_patterns = state.get("chart_patterns", [])
        pattern_statistics = state.get("pattern_statistics", {})
        strategy_performance = state.get("strategy_performance", {})
        news = state.get("news", [])
        news_summary = state.get("news_summary", {})

        # Initialize API costs tracking
        api_costs = state.get("api_costs", {})
        total_input_tokens = 0
        total_output_tokens = 0
        llm_calls = 0

        # Calculate ground truth for semantic state generation
        from src.analysis.market_analyzer import MarketAnalyzer
        market_analyzer = MarketAnalyzer()
        conditions = market_analyzer.calculate_market_conditions(indicators)

        ground_truth = {
            'uncertainty_score': indicators.get('uncertainty_score', 0),
            'atr_pct': (indicators.get('atr', 0) / indicators.get('current_price', 1)) * 100
                       if indicators.get('current_price', 0) > 0 else 0,
            'vwap_pct': conditions.get('price_vs_vwap_pct', 0),
            'volume_ratio': conditions.get('volume_ratio', 0),
        }

        # First pass: Generate report without strategy data to determine recommendation
        comparative_insights = state.get("comparative_insights", {})
        sec_filing_data = state.get("sec_filing_data", {})
        financial_markets_data = state.get("financial_markets_data", {})
        portfolio_insights = state.get("portfolio_insights", {})
        alpaca_data = state.get("alpaca_data", {})
        context = self.context_builder.prepare_context(
            ticker, ticker_data, indicators, percentiles, news, news_summary,
            ground_truth=ground_truth,
            strategy_performance=None,
            comparative_insights=comparative_insights,
            sec_filing_data=sec_filing_data,
            financial_markets_data=financial_markets_data,
            portfolio_insights=portfolio_insights,
            alpaca_data=alpaca_data
        )
        prompt = self.prompt_builder.build_prompt(
            ticker,
            context,
            ground_truth=ground_truth,
            indicators=indicators,
            percentiles=percentiles,
            ticker_data=ticker_data,
            strategy_performance=None,
            comparative_insights=comparative_insights,
            sec_filing_data=sec_filing_data,
            financial_markets_data=financial_markets_data,
            portfolio_insights=portfolio_insights,
            alpaca_data=alpaca_data
        )
        # Get Langfuse callback handler for token tracking
        langfuse_handler = get_langchain_handler()
        invoke_config = {"callbacks": [langfuse_handler]} if langfuse_handler else {}

        response = self.llm.invoke([HumanMessage(content=prompt)], config=invoke_config)
        initial_report = response.content
        llm_calls += 1

        # Extract token usage from response
        response_metadata = getattr(response, 'response_metadata', {})
        usage = response_metadata.get('token_usage', {})
        if usage:
            total_input_tokens += usage.get('prompt_tokens', 0)
            total_output_tokens += usage.get('completion_tokens', 0)
        else:
            # Fallback: estimate tokens (rough approximation: 4 chars per token)
            total_input_tokens += len(prompt) // 4
            total_output_tokens += len(initial_report) // 4

        # Extract recommendation from initial report
        recommendation = self.strategy_analyzer.extract_recommendation(initial_report)

        # Check if strategy performance aligns with recommendation
        include_strategy = self.strategy_analyzer.check_strategy_alignment(recommendation, strategy_performance)

        # Second pass: If aligned, regenerate with strategy data
        if include_strategy and strategy_performance:
            context_with_strategy = self.context_builder.prepare_context(
                ticker, ticker_data, indicators, percentiles, news, news_summary,
                ground_truth=ground_truth,
                strategy_performance=strategy_performance,
                comparative_insights=comparative_insights,
                sec_filing_data=sec_filing_data,
                financial_markets_data=financial_markets_data,
                portfolio_insights=portfolio_insights,
                alpaca_data=alpaca_data
            )
            prompt_with_strategy = self.prompt_builder.build_prompt(
                ticker,
                context_with_strategy,
                ground_truth=ground_truth,
                indicators=indicators,
                percentiles=percentiles,
                ticker_data=ticker_data,
                strategy_performance=strategy_performance,
                comparative_insights=comparative_insights,
                sec_filing_data=sec_filing_data,
                financial_markets_data=financial_markets_data,
                portfolio_insights=portfolio_insights,
                alpaca_data=alpaca_data
            )
            response = self.llm.invoke([HumanMessage(content=prompt_with_strategy)], config=invoke_config)
            report = response.content
            llm_calls += 1

            # Extract token usage from second response
            response_metadata = getattr(response, 'response_metadata', {})
            usage = response_metadata.get('token_usage', {})
            if usage:
                total_input_tokens += usage.get('prompt_tokens', 0)
                total_output_tokens += usage.get('completion_tokens', 0)
            else:
                total_input_tokens += len(prompt_with_strategy) // 4
                total_output_tokens += len(report) // 4
        else:
            report = initial_report

        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # INJECT DETERMINISTIC NUMBERS (Damodaran "narrative + number" approach)
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # Apply post-processing pipeline (number injection, news references, transparency footer)
        report = self._post_process_report_workflow(report, state, indicators)
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

        # Record LLM timing
        llm_elapsed = time.perf_counter() - llm_start_time
        timing_metrics = state.get("timing_metrics", {})
        timing_metrics["llm_generation"] = llm_elapsed
        state["timing_metrics"] = timing_metrics

        # Calculate API costs
        api_costs = self.cost_scorer.calculate_api_cost(
            total_input_tokens, total_output_tokens, actual_cost_usd=None
        )
        state["api_costs"] = api_costs

        # Validate report output
        if not report or len(report.strip()) == 0:
            error_msg = "Generated report is empty"
            state["error"] = error_msg
            self._log_node_error("generate_report", state, error_msg)
            return state

        state["report"] = report

        # Log success with details
        llm_elapsed = time.perf_counter() - llm_start_time
        details = {
            'report_length': len(report),
            'llm_calls': llm_calls,
            'input_tokens': total_input_tokens,
            'output_tokens': total_output_tokens,
            'duration_ms': f"{llm_elapsed*1000:.2f}"
        }
        self._log_node_success("generate_report", state, details)

        # Build scoring context for storage and scoring
        # Convert datetime/DataFrame objects to JSON-serializable format
        from src.utils.serialization import make_json_serializable

        market_conditions = self.market_analyzer.calculate_market_conditions(indicators)
        from src.scoring.scoring_service import ScoringContext
        scoring_context = ScoringContext(
            indicators=make_json_serializable(indicators),
            percentiles=make_json_serializable(percentiles),
            news=make_json_serializable(news),
            ticker_data=make_json_serializable(ticker_data),
            market_conditions={
                'uncertainty_score': indicators.get('uncertainty_score', 0),
                'atr_pct': (indicators.get('atr', 0) / indicators.get('current_price', 1)) * 100 if indicators.get('current_price', 0) > 0 else 0,
                'price_vs_vwap_pct': market_conditions.get('price_vs_vwap_pct', 0),
                'volume_ratio': market_conditions.get('volume_ratio', 0),
            },
            comparative_insights=make_json_serializable(state.get('comparative_insights', {}))
        )

        # Get yahoo ticker for background evaluation
        yahoo_ticker = self.ticker_map.get(ticker.upper()) or ticker

        state["report"] = report

        # ============================================
        # TIMING METRICS
        # ============================================
        # Calculate total latency up to this point
        total_latency = sum(timing_metrics.values())
        timing_metrics["total"] = total_latency
        state["timing_metrics"] = timing_metrics

        # ============================================
        # QUALITY SCORING + LANGFUSE INTEGRATION
        # ============================================
        # Compute quality scores and push to Langfuse trace
        try:
            from src.evaluation import score_trace_batch

            # Compute quality scores (rule-based scorers - fast)
            quality_scores = self.scoring_service.compute_all_quality_scores(
                report_text=report,
                context=scoring_context
            )

            # Build scores dict for Langfuse
            langfuse_scores = {}

            # Extract overall scores from each rule-based scorer result
            for score_name, score_result in quality_scores.items():
                if hasattr(score_result, 'overall_score'):
                    overall = score_result.overall_score
                    # Build comment from sub-scores if available
                    comment = None
                    if hasattr(score_result, 'sub_scores') and score_result.sub_scores:
                        sub_details = [f"{k}={v:.1f}" for k, v in score_result.sub_scores.items()]
                        comment = ", ".join(sub_details)
                    langfuse_scores[score_name] = (overall, comment)

            # Store scores in state for downstream use
            state["quality_scores"] = {
                name: result.overall_score if hasattr(result, 'overall_score') else 0
                for name, result in quality_scores.items()
            }

            # Log score summary
            score_summary = ", ".join([
                f"{name}={result.overall_score:.1f}"
                for name, result in quality_scores.items()
                if hasattr(result, 'overall_score')
            ])
            logger.info(f"📈 Rule-based scores: {score_summary}")

            # ============================================
            # LLM-AS-JUDGE SCORING (Two-Tier Framework)
            # ============================================
            # Optional: Compute LLM-based scores if enabled
            enable_llm_scoring = os.environ.get('ENABLE_LLM_SCORING', 'false').lower() == 'true'

            if enable_llm_scoring:
                try:
                    # Build LLM scoring context
                    llm_context = self.scoring_service.build_llm_scoring_context(
                        report_text=report,
                        ticker=ticker,
                        context=scoring_context,
                    )

                    # Compute LLM scores (async via sync wrapper)
                    llm_scores = self.scoring_service.compute_llm_scores(llm_context)

                    # Convert to Langfuse format and merge
                    llm_langfuse_scores = self.scoring_service.llm_scores_to_langfuse_format(llm_scores)
                    langfuse_scores.update(llm_langfuse_scores)

                    # Store LLM scores in state
                    state["llm_scores"] = {
                        name: result.value
                        for name, result in llm_scores.items()
                    }

                    # Log LLM score summary
                    llm_summary = ", ".join([
                        f"{name}={result.value:.2f}"
                        for name, result in llm_scores.items()
                    ])
                    logger.info(f"🤖 LLM-as-judge scores: {llm_summary}")

                except Exception as e:
                    logger.warning(f"⚠️ LLM scoring failed (non-blocking): {e}")
                    state["llm_scores"] = {}
            else:
                state["llm_scores"] = {}

            # Push all scores to Langfuse trace
            scores_pushed = score_trace_batch(langfuse_scores)
            if scores_pushed > 0:
                logger.info(f"📊 Pushed {scores_pushed} scores to Langfuse")

        except Exception as e:
            logger.warning(f"⚠️ Quality scoring failed (non-blocking): {e}")
            state["quality_scores"] = {}
            state["llm_scores"] = {}

        # Reset query count for next run
        self._db_query_count_ref[0] = 0

        # Log workflow summary
        self.log_workflow_summary(state)

        return state

    @observe(name="fetch_comparative_data")
    def fetch_comparative_data(self, state: AgentState) -> dict:
        """
        Fetch historical data for comparative analysis with similar tickers.

        Returns partial state with only modified fields (for parallel execution).
        """
        self._log_node_start("fetch_comparative_data", state)

        if state.get("error"):
            self._log_node_skip("fetch_comparative_data", state, "Previous error in workflow")
            return {}  # Return empty dict, don't propagate error

        start_time = time.perf_counter()
        ticker = state["ticker"]
        yahoo_ticker = self.ticker_map.get(ticker.upper())

        if not yahoo_ticker:
            self._log_node_skip("fetch_comparative_data", state, "No yahoo_ticker found")
            return {"comparative_data": {}}

        comparative_data = {}

        try:
            logger.info(f"   🔄 Fetching comparative data for {ticker}")

            # Get similar tickers from the same sector or nearby tickers in our list
            # For now, fetch 3-5 other tickers from our ticker list for comparison
            all_tickers = list(self.ticker_map.keys())
            similar_tickers = []

            # Find tickers in same sector if available
            ticker_data = state.get("ticker_data", {})
            sector = ticker_data.get("sector")

            # Get 3-5 other tickers (excluding current ticker)
            for t in all_tickers:
                if t != ticker.upper() and len(similar_tickers) < 5:
                    similar_tickers.append(t)

            # Fetch historical data for comparative analysis
            for t in similar_tickers[:5]:  # Limit to 5 to avoid too many API calls
                yt = self.ticker_map.get(t)
                if yt:
                    try:
                        hist_data = self.data_fetcher.fetch_historical_data(yt, days=90)
                        if hist_data is not None and not hist_data.empty:
                            comparative_data[t] = hist_data
                    except Exception as e:
                        logger.warning(f"   ⚠️  Failed to fetch comparative data for {t}: {str(e)}")
                        continue

            # Validate output
            elapsed = time.perf_counter() - start_time
            details = {
                'tickers_fetched': len(comparative_data),
                'duration_ms': f"{elapsed*1000:.2f}"
            }
            self._log_node_success("fetch_comparative_data", state, details)

        except Exception as e:
            logger.error(f"   ⚠️  Comparative data fetch failed: {str(e)}")
            set_observation_level("WARNING")  # Optional data, continue without it
            self._log_node_error("fetch_comparative_data", state, f"Exception: {str(e)}")
            comparative_data = {}

        # Return only modified fields (partial state)
        return {"comparative_data": comparative_data}

    def merge_fundamental_data(self, state: AgentState) -> dict:
        """
        SINK 1: Aggregate 6 fundamental parallel fetch results.

        This checkpoint validates all fundamental data fetches completed
        and provides debug logging for transparency.

        Returns empty dict (no new state modifications, just validation).
        """
        logger.info("=" * 70)
        logger.info("📦 SINK 1: FUNDAMENTAL DATA MERGE CHECKPOINT")
        logger.info("=" * 70)

        # Validate all 6 fundamental fetches
        news = state.get("news", [])
        alpaca = state.get("alpaca_data", {})
        markets = state.get("financial_markets_data", {})
        sec = state.get("sec_filing_data", {})
        portfolio = state.get("portfolio_insights", {})
        comparative = state.get("comparative_data", {})

        logger.info(f"  ✓ News: {len(news)} articles")
        logger.info(f"  ✓ Alpaca: {'data present' if alpaca else 'empty'}")
        logger.info(f"  ✓ Markets: {'data present' if markets else 'empty'}")
        logger.info(f"  ✓ SEC: {'data present' if sec else 'empty'}")
        logger.info(f"  ✓ Portfolio: {'data present' if portfolio else 'empty'}")
        logger.info(f"  ✓ Comparative: {len(comparative)} tickers")

        # Check for errors from parallel branches
        if state.get("error"):
            logger.error(f"  ❌ Error in fundamental fetch: {state['error']}")

        logger.info("=" * 70)

        # Return empty dict (sink doesn't modify state)
        return {}

    def merge_fund_tech_data(self, state: AgentState) -> dict:
        """
        SINK 2: Merge fundamental + technical pipelines.

        Prerequisite for score_user_facing and analyze_comparative_insights.

        Returns empty dict (no new state modifications, just validation).
        """
        logger.info("=" * 70)
        logger.info("📦 SINK 2: FUNDAMENTAL + TECHNICAL MERGE CHECKPOINT")
        logger.info("=" * 70)

        # Validate fundamental data present
        fundamental_count = sum([
            1 if state.get("news") else 0,
            1 if state.get("alpaca_data") else 0,
            1 if state.get("financial_markets_data") else 0,
            1 if state.get("sec_filing_data") else 0,
            1 if state.get("portfolio_insights") else 0,
            1 if state.get("comparative_data") else 0
        ])

        # Validate technical data present
        indicators = state.get("indicators", {})
        percentiles = state.get("percentiles", {})

        logger.info(f"  ✓ Fundamental: {fundamental_count}/6 data sources populated")
        logger.info(f"  ✓ Technical: Indicators={len(indicators)} fields, Percentiles={len(percentiles)} fields")

        # Check for errors
        if state.get("error"):
            logger.error(f"  ❌ Error in pipeline: {state['error']}")

        logger.info("=" * 70)

        # Return empty dict (sink doesn't modify state)
        return {}

    def merge_all_pipelines(self, state: AgentState) -> dict:
        """
        SINK 3: Merge all pipelines before final report.

        Combines scores, comparative insights, and chart for report generation.

        Returns empty dict (no new state modifications, just validation).
        """
        logger.info("=" * 70)
        logger.info("📦 SINK 3: FINAL MERGE CHECKPOINT (ALL PIPELINES)")
        logger.info("=" * 70)

        # Validate all required data present
        # Note: These field names may need adjustment based on actual state schema
        # Check what score_user_facing actually outputs
        has_scores = any(key.endswith('_score') for key in state.keys())
        insights = state.get("comparative_insights", {})
        chart = state.get("chart_base64", "")

        logger.info(f"  ✓ Scores: {'present' if has_scores else 'missing'}")
        logger.info(f"  ✓ Comparative insights: {'present' if insights else 'empty'}")
        logger.info(f"  ✓ Chart: {'generated' if chart else 'missing'}")

        # Check for errors
        if state.get("error"):
            logger.error(f"  ❌ Error in pipeline: {state['error']}")

        logger.info("=" * 70)

        # Return empty dict (sink doesn't modify state)
        return {}

    @observe(name="analyze_comparative_insights")
    def analyze_comparative_insights(self, state: AgentState) -> dict:
        """
        Perform comparative analysis and extract narrative-ready insights.

        Returns partial state with only modified fields (for parallel execution).
        """
        self._log_node_start("analyze_comparative_insights", state)

        if state.get("error"):
            self._log_node_skip("analyze_comparative_insights", state, "Previous error in workflow")
            return {}

        start_time = time.perf_counter()
        ticker = state["ticker"]
        ticker_data = state.get("ticker_data", {})
        indicators = state.get("indicators", {})
        comparative_data = state.get("comparative_data", {})

        if not comparative_data:
            self._log_node_skip("analyze_comparative_insights", state, "No comparative data available")
            return {"comparative_insights": {}}

        try:
            logger.info(f"   🔍 Analyzing comparative insights for {ticker}")

            # Add current ticker's data to comparative dataset
            yahoo_ticker = self.ticker_map.get(ticker.upper())
            if yahoo_ticker and ticker_data.get("history") is not None:
                hist_data = ticker_data.get("history")
                if hist_data is not None and not hist_data.empty:
                    comparative_data[ticker.upper()] = hist_data

            # Perform comprehensive comparative analysis
            if len(comparative_data) >= 2:
                analysis_results = self.comparative_analyzer.comprehensive_analysis(comparative_data)

                # Extract narrative-ready insights
                insights = self._extract_narrative_insights(ticker, indicators, analysis_results, comparative_data)

                # Validate output
                elapsed = time.perf_counter() - start_time
                details = {
                    'insights_count': len(insights),
                    'comparative_tickers': len(comparative_data),
                    'duration_ms': f"{elapsed*1000:.2f}"
                }
                self._log_node_success("analyze_comparative_insights", state, details)

                # Return only modified fields (partial state)
                return {"comparative_insights": insights}
            else:
                self._log_node_skip("analyze_comparative_insights", state, "Insufficient comparative data")
                return {"comparative_insights": {}}

        except Exception as e:
            logger.error(f"   ⚠️  Comparative analysis failed: {str(e)}")
            set_observation_level("WARNING")  # Optional analysis, continue without it
            self._log_node_error("analyze_comparative_insights", state, f"Exception: {str(e)}")
            return {"comparative_insights": {}}

    def _extract_narrative_insights(self, target_ticker: str, indicators: dict, analysis_results: dict, comparative_data: dict) -> dict:
        """Extract insights that can be woven into narrative in Damodaran style"""
        insights = {}

        if 'error' in analysis_results:
            return insights

        # Get correlation insights
        if 'correlation_matrix' in analysis_results:
            corr_dict = analysis_results['correlation_matrix']
            if isinstance(corr_dict, dict):
                corr_matrix = pd.DataFrame(corr_dict)
            else:
                corr_matrix = corr_dict

            if not corr_matrix.empty and target_ticker.upper() in corr_matrix.index:
                # Find most similar tickers
                similar = self.comparative_analyzer.find_similar_tickers(
                    corr_matrix, target_ticker.upper(), top_n=3
                )
                insights['similar_tickers'] = similar

                # Average correlation
                target_corrs = corr_matrix.loc[target_ticker.upper()].drop(target_ticker.upper())
                insights['avg_correlation'] = float(target_corrs.mean()) if len(target_corrs) > 0 else None

        # Get clustering insights
        if 'clustering' in analysis_results:
            clustering = analysis_results['clustering']
            clusters = self.comparative_analyzer.get_ticker_clusters(clustering)

            # Find which cluster target ticker is in
            for cluster_id, tickers in clusters.items():
                if target_ticker.upper() in tickers:
                    insights['cluster_id'] = cluster_id
                    insights['cluster_members'] = [t for t in tickers if t != target_ticker.upper()][:3]
                    break

        # Get feature comparison insights
        if 'features' in analysis_results:
            features_df = analysis_results['features']
            if not features_df.empty and 'ticker' in features_df.columns:
                # Set ticker as index for easier access
                features_df_indexed = features_df.set_index('ticker')

                if target_ticker.upper() in features_df_indexed.index:
                    target_features = features_df_indexed.loc[target_ticker.upper()]

                    # Compare volatility, returns, sharpe ratio
                    insights['volatility_vs_peers'] = {
                        'current': float(target_features.get('volatility', 0)),
                        'peer_avg': float(features_df_indexed['volatility'].mean()) if 'volatility' in features_df_indexed.columns else None
                    }

                    insights['return_vs_peers'] = {
                        'current': float(target_features.get('mean_return', 0)),
                        'peer_avg': float(features_df_indexed['mean_return'].mean()) if 'mean_return' in features_df_indexed.columns else None
                    }

                    insights['sharpe_vs_peers'] = {
                        'current': float(target_features.get('sharpe_ratio', 0)),
                        'peer_avg': float(features_df_indexed['sharpe_ratio'].mean()) if 'sharpe_ratio' in features_df_indexed.columns else None
                    }

                    # Rank position
                    if 'volatility' in features_df_indexed.columns:
                        vol_rank = (features_df_indexed['volatility'] < target_features['volatility']).sum() + 1
                        insights['volatility_rank'] = {
                            'position': int(vol_rank),
                            'total': len(features_df_indexed)
                        }

        return insights

    def fetch_all_data_parallel(self, state: AgentState) -> AgentState:
        """
        Fetch all data in parallel (data, news, comparative).

        This combines fetch_data, fetch_news, and fetch_comparative_data
        into a single parallelized operation for ~3x speedup.
        """
        self._log_node_start("fetch_all_data_parallel", state)
        start_time = time.perf_counter()

        ticker = state["ticker"]
        yahoo_ticker = self.ticker_map.get(ticker.upper())

        if not yahoo_ticker:
            error_msg = f"ไม่พบข้อมูล ticker สำหรับ {ticker}"
            state["error"] = error_msg
            self._log_node_error("fetch_all_data_parallel", state, error_msg)
            return state

        # Reset query count at start of new run
        self._db_query_count_ref[0] = 0

        logger.info(f"   🚀 Fetching all data in parallel for {ticker} -> {yahoo_ticker}")

        # Define fetch functions
        def fetch_main_data():
            """Fetch main ticker data"""
            try:
                data = self.data_fetcher.fetch_ticker_data(yahoo_ticker)
                if not data:
                    return None
                info = self.data_fetcher.get_ticker_info(yahoo_ticker)
                data.update(info)
                return data
            except Exception as e:
                logger.error(f"Error fetching main data: {e}")
                return None

        def fetch_news_data():
            """Fetch news (optimized - reduced to 3 items)"""
            try:
                high_impact_news = self.news_fetcher.filter_high_impact_news(
                    yahoo_ticker, min_score=40.0, max_news=3
                )
                news_summary = self.news_fetcher.get_news_summary(high_impact_news)
                return (high_impact_news, news_summary)
            except Exception as e:
                logger.error(f"Error fetching news: {e}")
                return ([], {})

        def fetch_comparative():
            """Fetch comparative data"""
            try:
                all_tickers = list(self.ticker_map.keys())
                similar_tickers = []

                # Get 3-5 other tickers (excluding current ticker)
                for t in all_tickers:
                    if t != ticker.upper() and len(similar_tickers) < 5:
                        similar_tickers.append(t)

                # Fetch historical data for comparative analysis
                comparative_data = {}
                for t in similar_tickers[:5]:
                    yt = self.ticker_map.get(t)
                    if yt:
                        try:
                            hist_data = self.data_fetcher.fetch_historical_data(yt, days=90)
                            if hist_data is not None and not hist_data.empty:
                                comparative_data[t] = hist_data
                        except Exception as e:
                            logger.warning(f"Failed to fetch comparative data for {t}: {e}")
                            continue

                return comparative_data
            except Exception as e:
                logger.error(f"Error fetching comparative data: {e}")
                return {}

        # Run all fetches in parallel
        results = {'data': None, 'news': ([], {}), 'comparative': {}}

        with ThreadPoolExecutor(max_workers=3) as executor:
            future_data = executor.submit(fetch_main_data)
            future_news = executor.submit(fetch_news_data)
            future_comparative = executor.submit(fetch_comparative)

            # Collect results
            try:
                results['data'] = future_data.result(timeout=30)
            except Exception as e:
                logger.error(f"Main data fetch failed: {e}")

            try:
                results['news'] = future_news.result(timeout=30)
            except Exception as e:
                logger.error(f"News fetch failed: {e}")

            try:
                results['comparative'] = future_comparative.result(timeout=30)
            except Exception as e:
                logger.error(f"Comparative fetch failed: {e}")

        # Process results
        data = results['data']
        if not data:
            error_msg = f"ไม่สามารถดึงข้อมูลสำหรับ {ticker} ({yahoo_ticker}) ได้"
            state["error"] = error_msg
            self._log_node_error("fetch_all_data_parallel", state, error_msg)
            return state

        # Update state
        state["ticker_data"] = data
        state["news"], state["news_summary"] = results['news']
        state["comparative_data"] = results['comparative']

        # Record timing
        elapsed = time.perf_counter() - start_time
        timing_metrics = state.get("timing_metrics", {})
        timing_metrics["parallel_fetch_all"] = elapsed
        state["timing_metrics"] = timing_metrics

        # Log success
        details = {
            'yahoo_ticker': yahoo_ticker,
            'news_count': len(state["news"]),
            'comparative_tickers': len(state["comparative_data"]),
            'duration_ms': f"{elapsed*1000:.2f}",
            'speedup': f"~{(1.36+0.29+0.56)/elapsed:.1f}x"
        }
        self._log_node_success("fetch_all_data_parallel", state, details)

        return state

    def fetch_financial_markets_data(self, state: AgentState) -> dict:
        """
        Fetch advanced technical data from Financial Markets MCP.

        Returns partial state with only modified fields (for parallel execution).
        """
        self._log_node_start("fetch_financial_markets_data", state)

        if state.get("error"):
            self._log_node_skip("fetch_financial_markets_data", state, "Previous error in workflow")
            return {}  # Return empty dict, don't propagate error

        start_time = time.perf_counter()
        ticker = state["ticker"]
        yahoo_ticker = self.ticker_map.get(ticker.upper())

        if not yahoo_ticker:
            self._log_node_skip("fetch_financial_markets_data", state, "No yahoo_ticker found")
            return {"financial_markets_data": {}}

        financial_markets_data = {}

        try:
            from src.integrations.mcp_client import get_mcp_client, MCPServerError

            mcp_client = get_mcp_client()

            # Check if Financial Markets MCP server is available
            if not mcp_client.is_server_available('financial_markets'):
                logger.info("Financial Markets MCP server not configured, skipping")
                self._log_node_skip("fetch_financial_markets_data", state, "MCP server not configured")
                return {"financial_markets_data": {}}

            logger.info(f"   📈 Fetching Financial Markets data for {ticker} ({yahoo_ticker}) via MCP")

            # Call MCP tools in sequence (with graceful degradation)
            # Note: MCP client now parses content array automatically, returns parsed JSON dict
            try:
                # Get chart patterns
                chart_patterns = mcp_client.call_tool(
                    server='financial_markets',
                    tool_name='get_chart_patterns',
                    arguments={'ticker': yahoo_ticker}
                )
                # Check for valid data (not empty dict and no error key)
                if chart_patterns and isinstance(chart_patterns, dict) and 'error' not in chart_patterns:
                    financial_markets_data['chart_patterns'] = chart_patterns
            except Exception as e:
                logger.warning(f"Failed to fetch chart patterns: {e}")

            try:
                # Get candlestick patterns
                candlestick_patterns = mcp_client.call_tool(
                    server='financial_markets',
                    tool_name='get_candlestick_patterns',
                    arguments={'ticker': yahoo_ticker}
                )
                if candlestick_patterns and isinstance(candlestick_patterns, dict) and 'error' not in candlestick_patterns:
                    financial_markets_data['candlestick_patterns'] = candlestick_patterns
            except Exception as e:
                logger.warning(f"Failed to fetch candlestick patterns: {e}")

            try:
                # Get support/resistance levels
                support_resistance = mcp_client.call_tool(
                    server='financial_markets',
                    tool_name='get_support_resistance',
                    arguments={'ticker': yahoo_ticker}
                )
                if support_resistance and isinstance(support_resistance, dict) and 'error' not in support_resistance:
                    financial_markets_data['support_resistance'] = support_resistance
            except Exception as e:
                logger.warning(f"Failed to fetch support/resistance: {e}")

            try:
                # Get advanced technical indicators
                technical_indicators = mcp_client.call_tool(
                    server='financial_markets',
                    tool_name='get_technical_indicators',
                    arguments={'ticker': yahoo_ticker}
                )
                if technical_indicators and isinstance(technical_indicators, dict) and 'error' not in technical_indicators:
                    financial_markets_data['technical_indicators'] = technical_indicators
            except Exception as e:
                logger.warning(f"Failed to fetch technical indicators: {e}")

            elapsed = time.perf_counter() - start_time
            details = {
                'ticker': yahoo_ticker,
                'data_keys': list(financial_markets_data.keys()),
                'duration_ms': f"{elapsed*1000:.2f}"
            }
            self._log_node_success("fetch_financial_markets_data", state, details)

        except MCPServerError as e:
            logger.warning(f"Financial Markets MCP failed: {e}, skipping")
            self._log_node_skip("fetch_financial_markets_data", state, f"MCP error: {str(e)}")
            financial_markets_data = {}
        except Exception as e:
            logger.error(f"Unexpected error fetching Financial Markets data: {e}")
            self._log_node_error("fetch_financial_markets_data", state, f"Exception: {str(e)}")
            financial_markets_data = {}

        # Return only modified fields (partial state)
        return {"financial_markets_data": financial_markets_data}

    def fetch_portfolio_insights(self, state: AgentState) -> dict:
        """
        Fetch portfolio-level insights from Portfolio Manager MCP (optional).

        Returns partial state with only modified fields (for parallel execution).
        """
        self._log_node_start("fetch_portfolio_insights", state)

        if state.get("error"):
            self._log_node_skip("fetch_portfolio_insights", state, "Previous error in workflow")
            return {}  # Return empty dict, don't propagate error

        try:
            from src.integrations.mcp_client import get_mcp_client, MCPServerError

            mcp_client = get_mcp_client()

            # Check if Portfolio Manager MCP server is available
            if not mcp_client.is_server_available('portfolio_manager'):
                logger.info("Portfolio Manager MCP server not configured, skipping")
                self._log_node_skip("fetch_portfolio_insights", state, "MCP server not configured")
                return {"portfolio_insights": {}}

            # Note: Portfolio Manager requires portfolio context (user's holdings)
            # For now, skip if no portfolio context is available
            # In future, this could be passed via state or API request
            logger.info("   💼 Portfolio Manager MCP requires portfolio context - skipping for now")
            self._log_node_skip("fetch_portfolio_insights", state, "No portfolio context available")

        except Exception as e:
            logger.warning(f"Error checking Portfolio Manager MCP: {e}")
            self._log_node_skip("fetch_portfolio_insights", state, f"Exception: {str(e)}")

        # Return only modified fields (partial state)
        return {"portfolio_insights": {}}

    def fetch_alpaca_data(self, state: AgentState) -> dict:
        """
        Fetch real-time market data and options from Alpaca MCP.

        Returns partial state with only modified fields (for parallel execution).
        """
        self._log_node_start("fetch_alpaca_data", state)

        if state.get("error"):
            self._log_node_skip("fetch_alpaca_data", state, "Previous error in workflow")
            return {}  # Return empty dict, don't propagate error

        start_time = time.perf_counter()
        ticker = state["ticker"]
        yahoo_ticker = self.ticker_map.get(ticker.upper())

        if not yahoo_ticker:
            self._log_node_skip("fetch_alpaca_data", state, "No yahoo_ticker found")
            return {"alpaca_data": {}}

        # Alpaca primarily supports US markets
        # Check if ticker is US-listed
        is_us_ticker = (
            yahoo_ticker.endswith('.US') or
            not any(yahoo_ticker.endswith(ext) for ext in ['.SI', '.HK', '.T', '.TW'])
        )

        if not is_us_ticker:
            logger.info(f"Skipping Alpaca data for non-US ticker: {ticker} ({yahoo_ticker})")
            self._log_node_skip("fetch_alpaca_data", state, f"Non-US ticker: {yahoo_ticker}")
            return {"alpaca_data": {}}

        alpaca_data = {}

        try:
            from src.integrations.mcp_client import get_mcp_client, MCPServerError

            mcp_client = get_mcp_client()

            # Check if Alpaca MCP server is available
            if not mcp_client.is_server_available('alpaca'):
                logger.info("Alpaca MCP server not configured, skipping")
                self._log_node_skip("fetch_alpaca_data", state, "MCP server not configured")
                return {"alpaca_data": {}}

            logger.info(f"   📊 Fetching Alpaca data for {ticker} ({yahoo_ticker}) via MCP")

            # Extract US ticker symbol (remove .US suffix if present)
            us_ticker = yahoo_ticker.replace('.US', '').upper()

            # Call MCP tools with graceful degradation
            try:
                # Get real-time quote
                quote = mcp_client.call_tool(
                    server='alpaca',
                    tool_name='get_realtime_quote',
                    arguments={'ticker': us_ticker}
                )
                if quote:
                    alpaca_data['quote'] = quote
            except Exception as e:
                logger.warning(f"Failed to fetch real-time quote: {e}")

            try:
                # Get options chain (for volatility analysis)
                options_chain = mcp_client.call_tool(
                    server='alpaca',
                    tool_name='get_options_chain',
                    arguments={'ticker': us_ticker}
                )
                if options_chain:
                    alpaca_data['options_chain'] = options_chain
            except Exception as e:
                logger.warning(f"Failed to fetch options chain: {e}")

            try:
                # Get market data
                market_data = mcp_client.call_tool(
                    server='alpaca',
                    tool_name='get_market_data',
                    arguments={'ticker': us_ticker}
                )
                if market_data:
                    alpaca_data['market_data'] = market_data
            except Exception as e:
                logger.warning(f"Failed to fetch market data: {e}")

            elapsed = time.perf_counter() - start_time
            details = {
                'ticker': us_ticker,
                'data_keys': list(alpaca_data.keys()),
                'duration_ms': f"{elapsed*1000:.2f}"
            }
            self._log_node_success("fetch_alpaca_data", state, details)

        except MCPServerError as e:
            logger.warning(f"Alpaca MCP failed: {e}, skipping")
            self._log_node_skip("fetch_alpaca_data", state, f"MCP error: {str(e)}")
            alpaca_data = {}
        except Exception as e:
            logger.error(f"Unexpected error fetching Alpaca data: {e}")
            self._log_node_error("fetch_alpaca_data", state, f"Exception: {str(e)}")
            alpaca_data = {}

        # Return only modified fields (partial state)
        return {"alpaca_data": alpaca_data}
