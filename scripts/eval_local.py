#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Local Evaluation Runner

Run evaluations locally without LangSmith. Loads ground truth from local JSON files,
runs target functions, evaluates with all 7 evaluators, and saves results locally.
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime
from unittest.mock import Mock
import uuid

# IMPORTANT: Disable LangSmith tracing for local evaluation
# This must be set BEFORE importing any LangSmith modules
os.environ['LANGSMITH_TRACING_V2'] = 'false'

from langsmith.schemas import Run, Example
from langsmith.evaluation import EvaluationResult

logger = logging.getLogger(__name__)


def run_local_evaluation(
    dataset_path: str,
    evaluation_type: str,
    component_name: Optional[str] = None,
    output_dir: str = "evaluation_results"
) -> Dict[str, Any]:
    """
    Run evaluation locally without LangSmith.

    Args:
        dataset_path: Path to ground truth directory (e.g., "ground_truth/")
        evaluation_type: "agent" or "component"
        component_name: Component name (required for component evaluation)
        output_dir: Directory to save results

    Returns:
        Dictionary containing evaluation results
    """
    logger.info(f"Starting local {evaluation_type} evaluation from {dataset_path}")

    # Load ground truth files
    dataset_path = Path(dataset_path)
    ground_truth_files = sorted(dataset_path.glob("ground_truth_*.json"))

    if not ground_truth_files:
        raise ValueError(f"No ground truth files found in {dataset_path}")

    logger.info(f"Found {len(ground_truth_files)} ground truth examples")

    # Get evaluators
    from src.langsmith_evaluator_adapters import get_all_evaluators
    evaluators = get_all_evaluators()

    # Results storage
    results = {
        "evaluation_type": evaluation_type,
        "component_name": component_name if evaluation_type == "component" else None,
        "timestamp": datetime.now().isoformat(),
        "dataset_path": str(dataset_path),
        "examples": [],
        "summary": {
            "total": len(ground_truth_files),
            "avg_scores": {}
        }
    }

    # Evaluate each example
    for i, gt_file in enumerate(ground_truth_files, 1):
        logger.info(f"Evaluating example {i}/{len(ground_truth_files)}: {gt_file.name}")

        try:
            # Load ground truth
            with open(gt_file, 'r', encoding='utf-8') as f:
                ground_truth = json.load(f)

            ticker = ground_truth['ticker']
            date = ground_truth['date']

            # Prepare inputs
            inputs = {
                "ticker": ticker,
                "date": date
            }

            # For component evaluation, include all data
            if evaluation_type == "component":
                inputs.update(ground_truth.get('data', {}))

            # Run target function
            if evaluation_type == "agent":
                from scripts.eval_agent import target_agent
                output = target_agent(inputs)
            else:
                if component_name == "report-generation":
                    from scripts.eval_component import target_report_generation
                    output = target_report_generation(inputs)
                else:
                    raise ValueError(f"Unknown component: {component_name}")

            # Create mock Run and Example for evaluators
            run = Mock(spec=Run)
            run.id = f"local-{uuid.uuid4()}"
            run.outputs = output
            run.inputs = inputs
            run.metadata = {}

            example = Mock(spec=Example)
            example.inputs = ground_truth.get('data', {})

            # Run evaluators
            eval_results = {}
            for evaluator in evaluators:
                try:
                    result = evaluator(run, example)
                    eval_results[result.key] = {
                        "score": result.score,
                        "comment": result.comment
                    }
                except Exception as e:
                    logger.warning(f"Evaluator {evaluator.__name__} failed: {e}")
                    eval_results[evaluator.__name__] = {
                        "score": 0.0,
                        "comment": f"Error: {str(e)}"
                    }

            # Store result
            example_result = {
                "ticker": ticker,
                "date": date,
                "ground_truth_file": gt_file.name,
                "scores": eval_results,
                "output_preview": output.get("narrative", "")[:200] + "..." if len(output.get("narrative", "")) > 200 else output.get("narrative", "")
            }

            results["examples"].append(example_result)

            logger.info(f"  ✓ Evaluated {ticker} ({date})")

        except Exception as e:
            logger.error(f"Failed to evaluate {gt_file.name}: {e}")
            results["examples"].append({
                "ticker": "unknown",
                "date": "unknown",
                "ground_truth_file": gt_file.name,
                "error": str(e)
            })

    # Calculate average scores
    all_scores = {}
    for example in results["examples"]:
        if "scores" in example:
            for key, value in example["scores"].items():
                if key not in all_scores:
                    all_scores[key] = []
                all_scores[key].append(value["score"])

    for key, scores in all_scores.items():
        results["summary"]["avg_scores"][key] = sum(scores) / len(scores) if scores else 0.0

    # Save results
    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = os.path.join(output_dir, f"eval_{timestamp}.json")

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    logger.info(f"Results saved to {output_file}")

    results["output_file"] = output_file

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
    parser = argparse.ArgumentParser(description='Run local evaluation')
    parser.add_argument('--dataset-path', required=True, help='Path to ground truth directory')
    parser.add_argument('--type', choices=['agent', 'component'], required=True, help='Evaluation type')
    parser.add_argument('--component', help='Component name (for component evaluation)')
    parser.add_argument('--output-dir', default='evaluation_results', help='Output directory')

    args = parser.parse_args()

    # Run evaluation
    try:
        results = run_local_evaluation(
            dataset_path=args.dataset_path,
            evaluation_type=args.type,
            component_name=args.component,
            output_dir=args.output_dir
        )

        print(f"\n✅ Local evaluation complete!")
        print(f"📊 Evaluated {results['summary']['total']} examples")
        print(f"\nAverage Scores:")
        for metric, score in results['summary']['avg_scores'].items():
            print(f"  {metric}: {score:.3f}")
        print(f"\n📁 Results: {results['output_file']}")

    except Exception as e:
        print(f"\n❌ Evaluation failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
