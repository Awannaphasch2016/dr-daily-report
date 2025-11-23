#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Agent-Level Evaluation Runner

Runs end-to-end workflow evaluation using LangSmith's evaluate() function.
Compares agent output against ground truth using all 7 evaluators.
"""

import logging
from typing import Dict, Any
from langsmith import Client
from langsmith.evaluation import evaluate

from src.agent import TickerAnalysisAgent
from src.langsmith_evaluator_adapters import get_all_evaluators

logger = logging.getLogger(__name__)


def target_agent(inputs: Dict[str, Any]) -> Dict[str, Any]:
    """
    Target function for agent-level evaluation.

    This runs the full TickerAnalysisAgent workflow and returns the generated report.

    Args:
        inputs: Dict containing:
            - ticker: Stock ticker symbol (e.g., "PTT")
            - date: Date for analysis (e.g., "2025-11-20")

    Returns:
        Dict containing:
            - narrative: Generated report text
    """
    ticker = inputs.get("ticker")
    date = inputs.get("date", None)

    logger.info(f"Running agent for {ticker} (date: {date})")

    # Initialize agent
    agent = TickerAnalysisAgent()

    # Run full workflow
    # Note: Agent will fetch data for the specified date from database
    try:
        report = agent.analyze_ticker(ticker)

        return {
            "narrative": report
        }

    except Exception as e:
        logger.error(f"Agent evaluation error for {ticker}: {e}")
        # Return empty report on error
        return {
            "narrative": f"Error generating report: {str(e)}"
        }


def run_agent_evaluation(dataset_name: str, experiment_prefix: str = None, workspace_id: str = None) -> Any:
    """
    Run agent-level evaluation against a LangSmith dataset.

    Args:
        dataset_name: Name of LangSmith dataset to evaluate against
        experiment_prefix: Optional experiment name prefix
        workspace_id: Optional workspace ID (overrides environment variable)

    Returns:
        Evaluation results from LangSmith
    """
    logger.info(f"Starting agent evaluation with dataset: {dataset_name}")

    # Get LangSmith client
    from src.langsmith_integration import get_langsmith_client
    client = get_langsmith_client(workspace_id=workspace_id)

    # Default experiment name
    if not experiment_prefix:
        from datetime import datetime
        experiment_prefix = f"dr-agent-{dataset_name}-{datetime.now().strftime('%Y%m%d-%H%M%S')}"

    # Get all 7 evaluators
    evaluators = get_all_evaluators()

    logger.info(f"Using {len(evaluators)} evaluators:")
    for evaluator in evaluators:
        logger.info(f"  - {evaluator.__name__}")

    # Run evaluation
    logger.info(f"Running evaluation with experiment prefix: {experiment_prefix}")

    results = evaluate(
        target=target_agent,
        data=dataset_name,
        evaluators=evaluators,
        experiment_prefix=experiment_prefix,
        max_concurrency=1,  # Sequential for reproducibility
        num_repetitions=1,
        client=client
    )

    logger.info("Agent evaluation complete")

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
    parser = argparse.ArgumentParser(description='Run agent-level evaluation')
    parser.add_argument('--dataset', required=True, help='LangSmith dataset name')
    parser.add_argument('--experiment', default=None, help='Experiment name prefix')
    parser.add_argument('--workspace', default=None, help='LangSmith workspace ID (use "none" to disable)')

    args = parser.parse_args()

    # Run evaluation
    try:
        results = run_agent_evaluation(args.dataset, args.experiment, args.workspace)
        print(f"\n✅ Evaluation complete!")
        print(f"Results: {results}")

    except Exception as e:
        print(f"\n❌ Evaluation failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
