# -*- coding: utf-8 -*-
"""Workflow nodes for LangGraph ticker analysis agent"""

import logging
from typing import TypedDict
import time
import json
from datetime import datetime
import pandas as pd
import numpy as np
from langchain_core.messages import HumanMessage
from langsmith import traceable
from langsmith.run_helpers import get_current_run_tree
from concurrent.futures import ThreadPoolExecutor, as_completed

from src.types import AgentState
from src.langsmith_integration import async_evaluate_and_log
import os

# Setup logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def _filter_state_for_langsmith(state: dict) -> dict:
    """
    Filter AgentState for LangSmith tracing.

    Removes non-serializable objects like pandas DataFrames to avoid serialization
    errors when LangSmith traces workflow execution. This function is used by
    @traceable decorators via process_inputs and process_outputs parameters.

    LangSmith's tracer cannot handle pandas DataFrames with Timestamp indices,
    causing errors: "keys must be str, int, float, bool or None, not Timestamp"

    Args:
        state: Workflow state dictionary (AgentState)

    Returns:
        Cleaned state dictionary safe for JSON serialization

    Example:
        @traceable(
            name="analyze_technical",
            process_inputs=_filter_state_for_langsmith,
            process_outputs=_filter_state_for_langsmith
        )
        def analyze_technical(self, state: AgentState) -> AgentState:
            return state  # Filtering happens automatically
    """
    if not isinstance(state, dict):
        return state

    cleaned = state.copy()

    # Remove DataFrame from ticker_data but keep other fields
    if "ticker_data" in cleaned and isinstance(cleaned.get("ticker_data"), dict):
        ticker_data_clean = {
            k: v for k, v in cleaned["ticker_data"].items()
            if k != "history"  # Remove DataFrame with Timestamp index
        }
        cleaned["ticker_data"] = ticker_data_clean

    # Remove comparative_data DataFrames
    # Keep the keys but replace DataFrame values with placeholders
    if "comparative_data" in cleaned and isinstance(cleaned.get("comparative_data"), dict):
        cleaned["comparative_data"] = {
            k: f"<DataFrame with {len(v)} rows>" if isinstance(v, pd.DataFrame) else v
            for k, v in cleaned.get("comparative_data", {}).items()
        }

    return cleaned


class WorkflowNodes:
    """Encapsulates all LangGraph workflow node methods"""

    def __init__(
        self,
        data_fetcher,
        technical_analyzer,
        news_fetcher,
        chart_generator,
        db,
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
        self.db = db
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

    def _prepare_state_for_tracing(self, state: AgentState) -> AgentState:
        """
        DEPRECATED: Use module-level _filter_state_for_langsmith() instead.

        This method is kept for backward compatibility but delegates to the
        module-level function. The @traceable decorator now handles filtering
        automatically via process_inputs and process_outputs parameters.

        Args:
            state: Original workflow state

        Returns:
            Cleaned state copy safe for JSON serialization
        """
        return _filter_state_for_langsmith(state)

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

    def fetch_data(self, state: AgentState) -> AgentState:
        """Fetch ticker data from Yahoo Finance"""
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
            self._log_node_error("fetch_data", state, error_msg)
            return state

        logger.info(f"   📊 Fetching data for {ticker} -> {yahoo_ticker}")

        # Fetch data
        data = self.data_fetcher.fetch_ticker_data(yahoo_ticker)

        if not data:
            error_msg = f"ไม่สามารถดึงข้อมูลสำหรับ {ticker} ({yahoo_ticker}) ได้"
            state["error"] = error_msg
            self._log_node_error("fetch_data", state, error_msg)
            return state

        # Get additional info
        info = self.data_fetcher.get_ticker_info(yahoo_ticker)
        data.update(info)

        # Save to database
        self.db.insert_ticker_data(
            ticker, yahoo_ticker, data['date'],
            {
                'open': data['open'],
                'high': data['high'],
                'low': data['low'],
                'close': data['close'],
                'volume': data['volume'],
                'market_cap': data.get('market_cap'),
                'pe_ratio': data.get('pe_ratio'),
                'eps': data.get('eps'),
                'dividend_yield': data.get('dividend_yield')
            }
        )
        self._db_query_count_ref[0] += 1

        # Record timing
        elapsed = time.perf_counter() - start_time
        timing_metrics = state.get("timing_metrics", {})
        timing_metrics["data_fetch"] = elapsed
        state["timing_metrics"] = timing_metrics

        state["ticker_data"] = data

        # Validate output
        if not self._validate_state_field(state, "ticker_data", "fetch_data"):
            self._log_node_error("fetch_data", state, "ticker_data is None after fetch")
        else:
            details = {
                'yahoo_ticker': yahoo_ticker,
                'has_history': 'history' in data and data['history'] is not None,
                'duration_ms': f"{elapsed*1000:.2f}"
            }
            self._log_node_success("fetch_data", state, details)

        return state

    def fetch_news(self, state: AgentState) -> AgentState:
        """Fetch high-impact news for the ticker"""
        self._log_node_start("fetch_news", state)

        if state.get("error"):
            self._log_node_skip("fetch_news", state, "Previous error in workflow")
            return state

        start_time = time.perf_counter()
        yahoo_ticker = self.ticker_map.get(state["ticker"].upper())
        if not yahoo_ticker:
            state["news"] = []
            state["news_summary"] = {}
            self._log_node_skip("fetch_news", state, "No yahoo_ticker found")
            return state

        logger.info(f"   📰 Fetching news for {yahoo_ticker}")

        # Fetch high-impact news (min score 40, max 5 items)
        high_impact_news = self.news_fetcher.filter_high_impact_news(
            yahoo_ticker,
            min_score=40.0,
            max_news=5
        )

        # Get news summary statistics
        news_summary = self.news_fetcher.get_news_summary(high_impact_news)

        # Record timing
        elapsed = time.perf_counter() - start_time
        timing_metrics = state.get("timing_metrics", {})
        timing_metrics["news_fetch"] = elapsed
        state["timing_metrics"] = timing_metrics

        state["news"] = high_impact_news
        state["news_summary"] = news_summary

        # Validate output
        validation = self._validate_state_fields(state, ["news", "news_summary"], "fetch_news")
        if all(validation.values()):
            details = {
                'news_count': len(high_impact_news),
                'positive': news_summary.get('positive_count', 0),
                'negative': news_summary.get('negative_count', 0),
                'neutral': news_summary.get('neutral_count', 0),
                'duration_ms': f"{elapsed*1000:.2f}"
            }
            self._log_node_success("fetch_news", state, details)
        else:
            self._log_node_error("fetch_news", state, f"Validation failed: {validation}")

        return state

    @traceable(
        name="analyze_technical",
        tags=["workflow", "analysis"],
        process_inputs=_filter_state_for_langsmith,
        process_outputs=_filter_state_for_langsmith
    )
    def analyze_technical(self, state: AgentState) -> AgentState:
        """Analyze technical indicators with percentile analysis"""
        self._log_node_start("analyze_technical", state)

        if state.get("error"):
            self._log_node_skip("analyze_technical", state, "Previous error in workflow")
            return state

        start_time = time.perf_counter()
        ticker_data = state["ticker_data"]
        hist_data = ticker_data.get('history')

        if hist_data is None or hist_data.empty:
            error_msg = "ไม่มีข้อมูลประวัติสำหรับการวิเคราะห์"
            state["error"] = error_msg
            self._log_node_error("analyze_technical", state, error_msg)
            return state

        logger.info(f"   📈 Analyzing technical indicators (data points: {len(hist_data)})")

        # Calculate indicators with percentiles
        result = self.technical_analyzer.calculate_all_indicators_with_percentiles(hist_data)

        if not result or not result.get('indicators'):
            error_msg = "ไม่สามารถคำนวณ indicators ได้"
            state["error"] = error_msg
            self._log_node_error("analyze_technical", state, error_msg)
            return state

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

        # Save indicators to database
        yahoo_ticker = self.ticker_map.get(state["ticker"].upper())
        if yahoo_ticker:  # Only save if ticker is in the map
            self.db.insert_technical_indicators(
                yahoo_ticker, ticker_data['date'], indicators
            )
            self._db_query_count_ref[0] += 1

        # Record timing
        elapsed = time.perf_counter() - start_time
        timing_metrics = state.get("timing_metrics", {})
        timing_metrics["technical_analysis"] = elapsed
        state["timing_metrics"] = timing_metrics

        state["indicators"] = indicators
        state["percentiles"] = percentiles
        state["chart_patterns"] = chart_patterns
        state["pattern_statistics"] = pattern_statistics
        state["strategy_performance"] = strategy_performance

        # Validate output
        validation = self._validate_state_fields(state, ["indicators", "percentiles"], "analyze_technical")
        if all(validation.values()):
            details = {
                'indicators_count': len(indicators),
                'percentiles_count': len(percentiles),
                'patterns_count': len(chart_patterns),
                'has_strategy': bool(strategy_performance),
                'duration_ms': f"{elapsed*1000:.2f}"
            }
            self._log_node_success("analyze_technical", state, details)
        else:
            self._log_node_error("analyze_technical", state, f"Validation failed: {validation}")

        return state

    @traceable(
        name="generate_chart",
        tags=["workflow", "visualization"],
        process_inputs=_filter_state_for_langsmith,
        process_outputs=_filter_state_for_langsmith
    )
    def generate_chart(self, state: AgentState) -> AgentState:
        """Generate technical analysis chart"""
        self._log_node_start("generate_chart", state)

        if state.get("error"):
            self._log_node_skip("generate_chart", state, "Previous error in workflow")
            return state

        start_time = time.perf_counter()
        try:
            ticker = state["ticker"]
            ticker_data = state["ticker_data"]
            indicators = state["indicators"]

            logger.info(f"   📊 Generating chart for {ticker}")

            # Generate chart (90 days by default)
            chart_base64 = self.chart_generator.generate_chart(
                ticker_data=ticker_data,
                indicators=indicators,
                ticker_symbol=ticker,
                days=90
            )

            state["chart_base64"] = chart_base64

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
            state["chart_base64"] = ""
            self._log_node_error("generate_chart", state, f"Exception: {str(e)}")

        # Record timing (even if failed)
        elapsed = time.perf_counter() - start_time
        timing_metrics = state.get("timing_metrics", {})
        timing_metrics["chart_generation"] = elapsed
        state["timing_metrics"] = timing_metrics

        return state

    @traceable(
        name="generate_report",
        tags=["workflow", "llm", "report"],
        process_inputs=_filter_state_for_langsmith,
        process_outputs=_filter_state_for_langsmith
    )
    def generate_report(self, state: AgentState) -> AgentState:
        """Generate Thai language report using LLM"""
        self._log_node_start("generate_report", state)

        if state.get("error"):
            self._log_node_skip("generate_report", state, "Previous error in workflow")
            return state

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

        # First pass: Generate report without strategy data to determine recommendation
        comparative_insights = state.get("comparative_insights", {})
        context = self.context_builder.prepare_context(ticker, ticker_data, indicators, percentiles, news, news_summary, strategy_performance=None, comparative_insights=comparative_insights)
        uncertainty_score = indicators.get('uncertainty_score', 0)

        prompt = self.prompt_builder.build_prompt(context, uncertainty_score, strategy_performance=None)
        response = self.llm.invoke([HumanMessage(content=prompt)])
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
                ticker, ticker_data, indicators, percentiles, news, news_summary, strategy_performance=strategy_performance, comparative_insights=comparative_insights
            )
            prompt_with_strategy = self.prompt_builder.build_prompt(context_with_strategy, uncertainty_score, strategy_performance=strategy_performance)
            response = self.llm.invoke([HumanMessage(content=prompt_with_strategy)])
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
        # Calculate ground truth for injection
        conditions = self.market_analyzer.calculate_market_conditions(indicators)
        ground_truth = {
            'uncertainty_score': indicators.get('uncertainty_score', 0),
            'atr_pct': (indicators.get('atr', 0) / indicators.get('current_price', 1)) * 100 if indicators.get('current_price', 0) > 0 else 0,
            'vwap_pct': conditions.get('price_vs_vwap_pct', 0),
            'volume_ratio': conditions.get('volume_ratio', 0),
        }

        # Replace all {{PLACEHOLDERS}} with exact ground truth values
        report = self.number_injector.inject_deterministic_numbers(
            report, ground_truth, indicators, percentiles
        )
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

        # Add news references at the end if news exists
        if news:
            news_references = self.news_fetcher.get_news_references(news)
            report += f"\n\n{news_references}"

        # Add percentile analysis at the end
        if percentiles:
            percentile_analysis = self.technical_analyzer.format_percentile_analysis(percentiles)
            report += f"\n\n{percentile_analysis}"

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
        def make_json_serializable(obj):
            """Recursively convert datetime/date/DataFrame/numpy objects to JSON-serializable format"""
            from datetime import date
            if isinstance(obj, (datetime, date)):
                return obj.isoformat()
            elif isinstance(obj, pd.Timestamp):
                return obj.isoformat()
            elif isinstance(obj, pd.DataFrame):
                # Convert DataFrame to list of records (handles timestamp indexes)
                df_copy = obj.reset_index(drop=False)
                return make_json_serializable(df_copy.to_dict('records'))
            elif isinstance(obj, np.integer):
                # Convert numpy integers (int64, int32, etc.) to Python int
                return int(obj)
            elif isinstance(obj, np.floating):
                # Convert numpy floats (float64, float32, etc.) to Python float
                return float(obj)
            elif isinstance(obj, np.ndarray):
                # Convert numpy arrays to lists
                return make_json_serializable(obj.tolist())
            elif isinstance(obj, dict):
                # Convert dict keys and values
                return {str(k) if isinstance(k, (pd.Timestamp, datetime, date)) else k: make_json_serializable(v)
                        for k, v in obj.items()}
            elif isinstance(obj, list):
                return [make_json_serializable(item) for item in obj]
            return obj

        market_conditions = self.market_analyzer.calculate_market_conditions(indicators)
        from src.scoring_service import ScoringContext
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

        # Save report with context to database
        yahoo_ticker = self.ticker_map.get(ticker.upper()) or ticker
        self.db.save_report(
            yahoo_ticker,
            ticker_data['date'],
            {
                'report_text': report,
                'context_json': json.dumps(make_json_serializable(scoring_context.to_json())),
                'technical_summary': self.technical_analyzer.analyze_trend(indicators, indicators.get('current_price')),
                'fundamental_summary': f"P/E: {ticker_data.get('pe_ratio', 'N/A')}",
                'sector_analysis': ticker_data.get('sector', 'N/A')
            }
        )
        self._db_query_count_ref[0] += 1

        state["report"] = report

        # ============================================
        # ASYNC BACKGROUND EVALUATION
        # ============================================
        # Report is complete - now score asynchronously to avoid blocking LINE bot response
        # Scoring happens in background thread and logs to both SQLite DB and LangSmith

        # Calculate total latency up to this point (before scoring)
        total_latency = sum(timing_metrics.values())
        timing_metrics["total"] = total_latency
        state["timing_metrics"] = timing_metrics

        # Check if LangSmith tracing is enabled and capture run ID
        langsmith_enabled = os.environ.get('LANGSMITH_TRACING_V2', 'false').lower() == 'true'
        langsmith_run_id = None

        if langsmith_enabled:
            try:
                # Get the current LangSmith run tree to extract ROOT trace ID
                run_tree = get_current_run_tree()
                if run_tree and hasattr(run_tree, 'trace_id'):
                    # Use trace_id to get the ROOT trace, not the current node's ID
                    langsmith_run_id = str(run_tree.trace_id)
                    logger.info(f"Captured LangSmith ROOT trace ID: {langsmith_run_id}")
                else:
                    logger.warning("LangSmith tracing enabled but no run tree available")
            except Exception as e:
                logger.warning(f"Failed to capture LangSmith run ID: {e}")

        # Spawn background thread for evaluation (does not block return)
        if yahoo_ticker:
            logger.info(f"Starting async background evaluation for {yahoo_ticker}")

            executor = ThreadPoolExecutor(max_workers=1)
            executor.submit(
                async_evaluate_and_log,
                # Pass all dependencies needed for scoring
                self.scoring_service,
                self.qos_scorer,
                self.cost_scorer,
                self.db,
                # Pass data for scoring
                report,
                scoring_context,
                yahoo_ticker,
                ticker_data['date'],
                timing_metrics.copy(),  # Copy to avoid mutation
                langsmith_run_id if langsmith_enabled else None
            )

            logger.info(f"Background evaluation thread spawned for {yahoo_ticker}, returning immediately")
        else:
            logger.warning("No yahoo_ticker available, skipping background evaluation")

        # Reset query count for next run
        self._db_query_count_ref[0] = 0

        # Log workflow summary
        self.log_workflow_summary(state)

        return state

    def fetch_comparative_data(self, state: AgentState) -> AgentState:
        """Fetch historical data for comparative analysis with similar tickers"""
        self._log_node_start("fetch_comparative_data", state)

        if state.get("error"):
            self._log_node_skip("fetch_comparative_data", state, "Previous error in workflow")
            return state

        start_time = time.perf_counter()
        ticker = state["ticker"]
        yahoo_ticker = self.ticker_map.get(ticker.upper())

        if not yahoo_ticker:
            state["comparative_data"] = {}
            self._log_node_skip("fetch_comparative_data", state, "No yahoo_ticker found")
            return state

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
            comparative_data = {}
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

            state["comparative_data"] = comparative_data

            # Validate output
            elapsed = time.perf_counter() - start_time
            details = {
                'tickers_fetched': len(comparative_data),
                'duration_ms': f"{elapsed*1000:.2f}"
            }
            self._log_node_success("fetch_comparative_data", state, details)

        except Exception as e:
            logger.error(f"   ⚠️  Comparative data fetch failed: {str(e)}")
            state["comparative_data"] = {}
            self._log_node_error("fetch_comparative_data", state, f"Exception: {str(e)}")

        # Record timing
        elapsed = time.perf_counter() - start_time
        timing_metrics = state.get("timing_metrics", {})
        timing_metrics["comparative_data_fetch"] = elapsed
        state["timing_metrics"] = timing_metrics

        return state

    @traceable(
        name="analyze_comparative_insights",
        tags=["workflow", "analysis", "comparative"],
        process_inputs=_filter_state_for_langsmith,
        process_outputs=_filter_state_for_langsmith
    )
    def analyze_comparative_insights(self, state: AgentState) -> AgentState:
        """Perform comparative analysis and extract narrative-ready insights"""
        self._log_node_start("analyze_comparative_insights", state)

        if state.get("error"):
            self._log_node_skip("analyze_comparative_insights", state, "Previous error in workflow")
            return state

        start_time = time.perf_counter()
        ticker = state["ticker"]
        ticker_data = state.get("ticker_data", {})
        indicators = state.get("indicators", {})
        comparative_data = state.get("comparative_data", {})

        if not comparative_data:
            state["comparative_insights"] = {}
            self._log_node_skip("analyze_comparative_insights", state, "No comparative data available")
            return state

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
                state["comparative_insights"] = insights

                # Validate output
                elapsed = time.perf_counter() - start_time
                details = {
                    'insights_count': len(insights),
                    'comparative_tickers': len(comparative_data),
                    'duration_ms': f"{elapsed*1000:.2f}"
                }
                self._log_node_success("analyze_comparative_insights", state, details)
            else:
                state["comparative_insights"] = {}
                self._log_node_skip("analyze_comparative_insights", state, "Insufficient comparative data")

        except Exception as e:
            logger.error(f"   ⚠️  Comparative analysis failed: {str(e)}")
            state["comparative_insights"] = {}
            self._log_node_error("analyze_comparative_insights", state, f"Exception: {str(e)}")

        # Record timing
        elapsed = time.perf_counter() - start_time
        timing_metrics = state.get("timing_metrics", {})
        timing_metrics["comparative_analysis"] = elapsed
        state["timing_metrics"] = timing_metrics

        return state

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

    @traceable(
        name="fetch_all_data_parallel",
        tags=["workflow", "data", "parallel"],
        process_inputs=_filter_state_for_langsmith,
        process_outputs=_filter_state_for_langsmith
    )
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

        # Save to database
        self.db.insert_ticker_data(
            ticker, yahoo_ticker, data['date'],
            {
                'open': data['open'],
                'high': data['high'],
                'low': data['low'],
                'close': data['close'],
                'volume': data['volume'],
                'market_cap': data.get('market_cap'),
                'pe_ratio': data.get('pe_ratio'),
                'eps': data.get('eps'),
                'dividend_yield': data.get('dividend_yield')
            }
        )
        self._db_query_count_ref[0] += 1

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
