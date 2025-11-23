#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LangSmith Integration Utilities

Provides async evaluation runner and utilities for logging evaluation results
to LangSmith. Handles background scoring to avoid blocking LINE bot responses.
"""

import os
import logging
from typing import Dict, Any, Optional
from datetime import datetime
from dataclasses import asdict
from langsmith import Client
from langsmith.run_helpers import traceable

from .langsmith_evaluators import LangSmithEvaluators
from .scoring_service import ScoringContext

logger = logging.getLogger(__name__)


def get_langsmith_client() -> Optional[Client]:
    """
    Get LangSmith client with proper configuration.

    Returns:
        LangSmith Client instance or None if not configured
    """
    try:
        # Check if LangSmith is configured
        api_key = os.environ.get('LANGSMITH_API_KEY')
        if not api_key:
            logger.warning("LANGSMITH_API_KEY not set, LangSmith logging disabled")
            return None

        # Initialize client
        workspace_id = os.environ.get('LANGSMITH_WORKSPACE_ID')

        # Only use workspace_id if it's set AND the API key is org-scoped
        # Personal API keys will fail with 403 Forbidden if workspace_id is provided
        if workspace_id and api_key.startswith('lsv2_sk_'):
            # Org-scoped key - use workspace_id
            client = Client(
                api_key=api_key,
                api_url=os.environ.get('LANGSMITH_ENDPOINT', 'https://api.smith.langchain.com'),
                workspace_id=workspace_id
            )
            logger.info(f"LangSmith client initialized with workspace: {workspace_id}")
        else:
            # Personal key or no workspace_id - use default (project-based routing)
            client = Client(
                api_key=api_key,
                api_url=os.environ.get('LANGSMITH_ENDPOINT', 'https://api.smith.langchain.com')
            )
            if workspace_id:
                logger.warning(f"workspace_id set but API key is not org-scoped. Using project-based routing instead.")
            logger.info("LangSmith client initialized with default workspace")

        return client

    except Exception as e:
        logger.error(f"Failed to initialize LangSmith client: {e}")
        return None


def log_evaluation_to_langsmith(
    client: Client,
    run_id: str,
    ticker: str,
    quality_scores: Dict[str, Any],
    performance_scores: Dict[str, Any],
    metadata: Optional[Dict[str, Any]] = None
) -> bool:
    """
    Log evaluation results to LangSmith.

    Args:
        client: LangSmith client instance
        run_id: LangSmith run ID to attach evaluations to
        ticker: Stock ticker symbol
        quality_scores: Quality scores (faithfulness, completeness, reasoning, compliance)
        performance_scores: Performance scores (qos, cost)
        metadata: Optional additional metadata

    Returns:
        True if logging succeeded, False otherwise
    """
    try:
        logger.info(f"[LangSmith] Starting feedback logging for {ticker}, run_id={run_id}")

        # Convert scores to LangSmith format
        evaluations = LangSmithEvaluators.evaluate_all(quality_scores, performance_scores)
        logger.info(f"[LangSmith] Converted {len(evaluations)} evaluations")

        # Add metadata
        eval_metadata = {
            'ticker': ticker,
            'timestamp': datetime.utcnow().isoformat(),
            'evaluation_type': 'automated'
        }
        if metadata:
            eval_metadata.update(metadata)

        # Log each evaluation
        for i, evaluation in enumerate(evaluations, 1):
            logger.info(f"[LangSmith] Creating feedback {i}/{len(evaluations)}: {evaluation['key']} = {evaluation['score']:.3f}")
            try:
                client.create_feedback(
                    run_id=run_id,
                    key=evaluation['key'],
                    score=evaluation['score'],
                    comment=evaluation['comment']
                )
                logger.info(f"[LangSmith] ✅ Created feedback: {evaluation['key']}")
            except Exception as fb_error:
                logger.error(f"[LangSmith] ❌ Failed to create feedback {evaluation['key']}: {fb_error}")
                raise

        logger.info(f"[LangSmith] ✅ Successfully logged {len(evaluations)} evaluations to LangSmith for {ticker}")
        return True

    except Exception as e:
        logger.error(f"[LangSmith] ❌ Failed to log evaluations to LangSmith: {e}")
        import traceback
        logger.error(f"[LangSmith] Traceback: {traceback.format_exc()}")
        return False


def async_evaluate_and_log(
    scoring_service,
    qos_scorer,
    cost_scorer,
    database,
    report: str,
    scoring_context: ScoringContext,
    ticker: str,
    date: str,
    timing_metrics: Dict[str, float],
    langsmith_run_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Async background function to compute scores and log to both database and LangSmith.

    This function is designed to run in a background thread and does not block
    the LINE bot response. It performs all scoring operations and logs results
    to both SQLite database (existing behavior) and LangSmith (new behavior).

    Args:
        scoring_service: ScoringService instance
        qos_scorer: QoSScorer instance
        cost_scorer: CostScorer instance
        database: Database instance
        report: Generated report text
        scoring_context: ScoringContext with all necessary data
        ticker: Stock ticker symbol
        date: Report date
        timing_metrics: Timing metrics from workflow
        langsmith_run_id: Optional LangSmith run ID for linking evaluations

    Returns:
        Dict containing all computed scores
    """
    try:
        logger.info(f"Background evaluation started for {ticker}")

        # ============================================
        # STEP 1: Compute Quality Scores (Rule-Based)
        # ============================================
        quality_scores = scoring_service.compute_all_quality_scores(
            report_text=report,
            context=scoring_context
        )

        faithfulness_score = quality_scores.get('faithfulness', {})
        completeness_score = quality_scores.get('completeness', {})
        reasoning_quality_score = quality_scores.get('reasoning_quality', {})
        compliance_score = quality_scores.get('compliance', {})

        # ============================================
        # STEP 1.5: Compute Hallucination Score (LLM-as-Judge, Optional)
        # ============================================
        try:
            hallucination_scores = scoring_service.compute_hallucination_score(
                report_text=report,
                context=scoring_context,
                ticker=ticker
            )

            # Add to quality_scores if successful
            if hallucination_scores:
                quality_scores.update(hallucination_scores)
                hallucination_score = hallucination_scores.get('hallucination_llm', {})
                logger.info(f"Hallucination (LLM) score: {hallucination_score.overall_score:.1f}/100")
            else:
                logger.info("Hallucination scoring skipped (optional)")

        except Exception as hall_error:
            logger.warning(f"Hallucination scoring failed (optional): {hall_error}")
            # Continue without hallucination score - it's optional

        # ============================================
        # STEP 2: Compute Performance Scores
        # ============================================
        # Build database metrics
        database_metrics = {
            'query_count': timing_metrics.get('db_queries', 1),
            'cache_hit': False
        }

        # Extract API costs from timing_metrics (if available)
        api_costs = {
            'openai_api': timing_metrics.get('llm_cost', 0),
            'yahoo_api': 0,  # Yahoo API is free
            'total': timing_metrics.get('llm_cost', 0)
        }

        # QoS Score
        qos_score = qos_scorer.score_qos(
            timing_metrics=timing_metrics,
            database_metrics=database_metrics,
            error_occurred=False,
            cache_hit=False,
            llm_calls=timing_metrics.get('llm_calls', 1),
            historical_data=None
        )

        # Cost Score
        cost_score = cost_scorer.score_cost(
            api_costs=api_costs,
            llm_calls=timing_metrics.get('llm_calls', 1),
            database_metrics=database_metrics,
            cache_hit=False
        )

        performance_scores = {
            'qos': qos_score,
            'cost': cost_score
        }

        # ============================================
        # STEP 3: Save to Database (Existing Behavior)
        # ============================================
        try:
            # Save faithfulness score
            database.save_faithfulness_score(ticker, date, faithfulness_score)

            # Save completeness score
            database.save_completeness_score(ticker, date, completeness_score)

            # Save reasoning quality score
            database.save_reasoning_quality_score(ticker, date, reasoning_quality_score)

            # Save compliance score
            database.save_compliance_score(ticker, date, compliance_score)

            # Save QoS metrics
            database.save_qos_metrics(ticker, date, qos_score)

            # Save cost metrics
            database.save_cost_metrics(ticker, date, cost_score)

            # Save score summary
            database.save_score_summary(ticker, date, {
                'faithfulness': faithfulness_score,
                'completeness': completeness_score,
                'reasoning_quality': reasoning_quality_score,
                'compliance': compliance_score,
                'qos': qos_score,
                'cost': cost_score
            })

            logger.info(f"Successfully saved all scores to database for {ticker}")

        except Exception as db_error:
            logger.error(f"Failed to save scores to database: {db_error}")
            # Continue to LangSmith logging even if DB save fails

        # ============================================
        # STEP 4: Log to LangSmith (New Behavior)
        # ============================================
        if langsmith_run_id:
            try:
                client = get_langsmith_client()
                if client:
                    # Convert score objects to dictionaries
                    quality_scores_dict = {
                        key: asdict(score) if hasattr(score, '__dataclass_fields__') else score
                        for key, score in quality_scores.items()
                    }
                    performance_scores_dict = {
                        key: asdict(score) if hasattr(score, '__dataclass_fields__') else score
                        for key, score in performance_scores.items()
                    }

                    log_evaluation_to_langsmith(
                        client=client,
                        run_id=langsmith_run_id,
                        ticker=ticker,
                        quality_scores=quality_scores_dict,
                        performance_scores=performance_scores_dict,
                        metadata={
                            'date': date,
                            'total_latency': timing_metrics.get('total_elapsed', 0),
                            'mode': 'async_background'
                        }
                    )
                else:
                    logger.warning("LangSmith client not available, skipping LangSmith logging")

            except Exception as langsmith_error:
                logger.error(f"Failed to log to LangSmith: {langsmith_error}")
                # Continue even if LangSmith logging fails

        logger.info(f"Background evaluation completed for {ticker}")

        # Return all scores
        return {
            'quality_scores': quality_scores,
            'performance_scores': performance_scores
        }

    except Exception as e:
        logger.error(f"Background evaluation failed for {ticker}: {e}")
        import traceback
        traceback.print_exc()
        return {}
