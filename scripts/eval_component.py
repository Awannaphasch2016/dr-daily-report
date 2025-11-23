#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Component-Level Evaluation Runner

Runs isolated LLM component evaluation using LangSmith's evaluate() function.
Compares component output against ground truth using all 7 evaluators.

Currently supported components:
- report-generation: Isolated report generation LLM call
"""

import logging
from typing import Dict, Any
from langsmith import Client
from langsmith.evaluation import evaluate

from src.langsmith_evaluator_adapters import get_all_evaluators

logger = logging.getLogger(__name__)


def target_report_generation(inputs: Dict[str, Any]) -> Dict[str, Any]:
    """
    Target function for report-generation component evaluation.

    This runs only the report generation LLM call, bypassing data fetching
    and using pre-fetched data from inputs.

    Args:
        inputs: Dict containing:
            - ticker: Stock ticker symbol
            - date: Date for analysis
            - indicators: Pre-fetched technical indicators
            - percentiles: Pre-fetched percentile data
            - news: Pre-fetched news data
            - ticker_data: Pre-fetched ticker data
            - market_conditions: Pre-calculated market conditions
            - comparative_insights: Pre-fetched comparative analysis (optional)

    Returns:
        Dict containing:
            - narrative: Generated report text
    """
    from src.workflow.workflow_nodes import WorkflowNodes
    from src.database import TickerDatabase
    from src.data_fetcher import DataFetcher
    from src.technical_analysis import TechnicalAnalyzer
    from src.news_fetcher import NewsFetcher
    from src.chart_generator import ChartGenerator
    from src.strategy import SMAStrategyBacktester
    from src.analysis import StrategyAnalyzer
    from src.comparative_analysis import ComparativeAnalyzer
    from src.report import PromptBuilder, ContextBuilder, NumberInjector
    from src.analysis import MarketAnalyzer
    from src.cost_scorer import CostScorer
    from langchain_openai import ChatOpenAI
    from src.scoring_service import ScoringService
    from src.qos_scorer import QoSScorer
    from src.faithfulness_scorer import FaithfulnessScorer
    from src.completeness_scorer import CompletenessScorer
    from src.reasoning_quality_scorer import ReasoningQualityScorer
    from src.compliance_scorer import ComplianceScorer
    ticker = inputs.get("ticker")
    logger.info(f"Running report-generation component for {ticker}")

    # Initialize all required dependencies
    # (This is necessary because WorkflowNodes needs them all)
    db = TickerDatabase()
    data_fetcher = DataFetcher()
    technical_analyzer = TechnicalAnalyzer()
    news_fetcher = NewsFetcher()
    chart_generator = ChartGenerator()
    strategy_backtester = SMAStrategyBacktester()
    strategy_analyzer = StrategyAnalyzer(strategy_backtester)
    comparative_analyzer = ComparativeAnalyzer()
    llm = ChatOpenAI(model="gpt-4o", temperature=0.8)
    from src.formatters import DataFormatter
    data_formatter = DataFormatter()
    market_analyzer = MarketAnalyzer()
    context_builder = ContextBuilder(market_analyzer, data_formatter, technical_analyzer)
    prompt_builder = PromptBuilder()
    number_injector = NumberInjector()
    cost_scorer = CostScorer()
    scoring_service = ScoringService()
    qos_scorer = QoSScorer()
    ticker_map = data_fetcher.load_tickers()

    # Create WorkflowNodes instance
    nodes = WorkflowNodes(
        data_fetcher=data_fetcher,
        technical_analyzer=technical_analyzer,
        news_fetcher=news_fetcher,
        chart_generator=chart_generator,
        db=db,
        strategy_backtester=strategy_backtester,
        strategy_analyzer=strategy_analyzer,
        comparative_analyzer=comparative_analyzer,
        llm=llm,
        context_builder=context_builder,
        prompt_builder=prompt_builder,
        market_analyzer=market_analyzer,
        number_injector=number_injector,
        cost_scorer=cost_scorer,
        scoring_service=scoring_service,
        qos_scorer=qos_scorer,
        faithfulness_scorer=FaithfulnessScorer(),
        completeness_scorer=CompletenessScorer(),
        reasoning_quality_scorer=ReasoningQualityScorer(),
        compliance_scorer=ComplianceScorer(),
        ticker_map=ticker_map,
        db_query_count_ref=[0]
    )

    # Build minimal state from inputs (component-level: all data pre-fetched)
    state = {
        "ticker": inputs.get("ticker"),
        "ticker_data": inputs.get("ticker_data", {}),
        "indicators": inputs.get("indicators", {}),
        "percentiles": inputs.get("percentiles", {}),
        "news": inputs.get("news", []),
        "news_summary": inputs.get("news_summary", {}),
        "chart_patterns": inputs.get("chart_patterns", []),
        "pattern_statistics": inputs.get("pattern_statistics", {}),
        "strategy_performance": inputs.get("strategy_performance", {}),
        "comparative_insights": inputs.get("comparative_insights", {}),
        "timing_metrics": {},
        "api_costs": {}
    }

    try:
        # Call generate_report method
        result_state = nodes.generate_report(state)

        # Extract report from result
        report = result_state.get("report", "")

        return {
            "narrative": report
        }

    except Exception as e:
        logger.error(f"Component evaluation error for {ticker}: {e}")
        # Return empty report on error
        return {
            "narrative": f"Error generating report: {str(e)}"
        }


# Component target function mapping
COMPONENT_TARGETS = {
    "report-generation": target_report_generation
}


def run_component_evaluation(
    component_name: str,
    dataset_name: str,
    experiment_prefix: str = None
) -> Any:
    """
    Run component-level evaluation against a LangSmith dataset.

    Args:
        component_name: Name of component to evaluate (e.g., "report-generation")
        dataset_name: Name of LangSmith dataset to evaluate against
        experiment_prefix: Optional experiment name prefix

    Returns:
        Evaluation results from LangSmith
    """
    logger.info(f"Starting component evaluation: {component_name} with dataset: {dataset_name}")

    # Validate component name
    if component_name not in COMPONENT_TARGETS:
        raise ValueError(
            f"Unknown component: {component_name}. "
            f"Valid components: {', '.join(COMPONENT_TARGETS.keys())}"
        )

    # Get target function
    target_func = COMPONENT_TARGETS[component_name]

    # Get LangSmith client
    client = Client()

    # Default experiment name
    if not experiment_prefix:
        from datetime import datetime
        experiment_prefix = f"dr-component-{component_name}-{dataset_name}-{datetime.now().strftime('%Y%m%d-%H%M%S')}"

    # Get all 7 evaluators
    evaluators = get_all_evaluators()

    logger.info(f"Using {len(evaluators)} evaluators:")
    for evaluator in evaluators:
        logger.info(f"  - {evaluator.__name__}")

    # Run evaluation
    logger.info(f"Running evaluation with experiment prefix: {experiment_prefix}")

    results = evaluate(
        target=target_func,
        data=dataset_name,
        evaluators=evaluators,
        experiment_prefix=experiment_prefix,
        max_concurrency=1,  # Sequential for reproducibility
        num_repetitions=1,
        client=client
    )

    logger.info(f"Component evaluation complete for {component_name}")

    return results


if __name__ == '__main__':
    import sys
    import argparse

    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Parse arguments
    parser = argparse.ArgumentParser(description='Run component-level evaluation')
    parser.add_argument('component', help='Component name (e.g., report-generation)')
    parser.add_argument('--dataset', required=True, help='LangSmith dataset name')
    parser.add_argument('--experiment', default=None, help='Experiment name prefix')

    args = parser.parse_args()

    # Run evaluation
    try:
        results = run_component_evaluation(args.component, args.dataset, args.experiment)
        print(f"\n✅ Evaluation complete!")
        print(f"Results: {results}")

    except Exception as e:
        print(f"\n❌ Evaluation failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
