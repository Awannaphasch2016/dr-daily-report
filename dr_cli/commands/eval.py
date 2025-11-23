#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Evaluation CLI Commands

Provides commands for:
1. Generating ground truth examples from historical data
2. Uploading datasets to LangSmith
3. Running agent-level evaluations
4. Running component-level evaluations
"""

import os
import json
import click
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any
import logging
from langsmith import Client

logger = logging.getLogger(__name__)


@click.group()
def eval():
    """Evaluation commands for offline LangSmith evaluation"""
    pass


@eval.command(name="list-components")
def list_components():
    """
    List all available components for evaluation.

    Example:
        dr eval list-components
    """
    click.echo("📦 Available Components for Evaluation")
    click.echo("=" * 60)
    click.echo()

    components = {
        "report-generation": {
            "description": "Report generation node (LLM call)",
            "input": "Pre-fetched data (indicators, prices, news)",
            "output": "Thai narrative report",
            "usage": "dr eval component report-generation --dataset <name>"
        }
    }

    for name, info in components.items():
        click.echo(f"🔧 {name}")
        click.echo(f"   Description: {info['description']}")
        click.echo(f"   Input: {info['input']}")
        click.echo(f"   Output: {info['output']}")
        click.echo(f"   Usage: {info['usage']}")
        click.echo()

    click.echo("=" * 60)
    click.echo(f"Total: {len(components)} component(s)")
    click.echo()
    click.echo("For more details, use:")
    click.echo("  dr eval describe component <name>")


@eval.command(name="list-datasets")
@click.option(
    '--local',
    is_flag=True,
    default=False,
    help='List local datasets only'
)
@click.option(
    '--remote',
    is_flag=True,
    default=False,
    help='List remote LangSmith datasets only'
)
def list_datasets(local: bool, remote: bool):
    """
    List available datasets for evaluation.

    Examples:
        dr eval list-datasets              # List both local and remote
        dr eval list-datasets --local      # Local only
        dr eval list-datasets --remote     # Remote only
    """
    # Default: show both if neither flag specified
    show_local = local or (not local and not remote)
    show_remote = remote or (not local and not remote)

    if show_local:
        click.echo("📁 Local Datasets (Ground Truth)")
        click.echo("=" * 60)
        click.echo()

        # Check for ground truth directory
        gt_dir = Path("ground_truth")
        if gt_dir.exists():
            gt_files = list(gt_dir.glob("ground_truth_*.json"))
            if gt_files:
                # Group by ticker
                # Filename format: ground_truth_TICKER_DATE.json
                by_ticker = {}
                for f in gt_files:
                    parts = f.stem.split('_')
                    if len(parts) >= 4:  # ground, truth, TICKER, DATE
                        ticker = parts[2]
                        date = parts[3]
                        if ticker not in by_ticker:
                            by_ticker[ticker] = []
                        by_ticker[ticker].append(date)

                click.echo(f"📊 ground_truth/")
                click.echo(f"   {len(gt_files)} example(s)")
                if by_ticker:
                    for ticker, dates in sorted(by_ticker.items()):
                        date_range = f"{min(dates)} to {max(dates)}" if len(dates) > 1 else dates[0]
                        click.echo(f"   - {ticker}: {len(dates)} date(s) ({date_range})")
                click.echo(f"   Usage: dr eval agent --dataset ground_truth/ --local")
                click.echo()
            else:
                click.echo("   (No ground truth files found)")
                click.echo()
        else:
            click.echo("   (ground_truth/ directory not found)")
            click.echo()

        # Check for evaluation results
        results_dir = Path("evaluation_results")
        if results_dir.exists():
            result_files = list(results_dir.glob("eval_*.json"))
            if result_files:
                click.echo(f"📊 Past Evaluation Results: {len(result_files)} file(s)")
                for f in sorted(result_files)[-5:]:  # Show last 5
                    # Parse timestamp from filename
                    try:
                        with open(f, 'r') as rf:
                            data = json.load(rf)
                            click.echo(f"   - {f.name}: {data.get('summary', {}).get('total', 0)} examples")
                    except:
                        click.echo(f"   - {f.name}")
                click.echo()

        click.echo("=" * 60)
        click.echo()

    if show_remote:
        click.echo("☁️  Remote Datasets (LangSmith)")
        click.echo("=" * 60)
        click.echo()

        try:
            from src.langsmith_integration import get_langsmith_client

            client = get_langsmith_client()
            if not client:
                click.echo("❌ Failed to connect to LangSmith")
                click.echo("   Make sure LANGSMITH_API_KEY is set")
                click.echo()
                return

            # List datasets
            datasets = list(client.list_datasets())

            if datasets:
                for ds in datasets:
                    click.echo(f"📊 {ds.name}")
                    if ds.description:
                        click.echo(f"   Description: {ds.description}")
                    click.echo(f"   ID: {ds.id}")
                    click.echo(f"   Usage: dr eval agent --dataset {ds.name}")
                    click.echo()

                click.echo("=" * 60)
                click.echo(f"Total: {len(datasets)} dataset(s)")
                click.echo()
                click.echo(f"🔗 View all at: https://smith.langchain.com/datasets")
            else:
                click.echo("   (No datasets found in LangSmith)")
                click.echo()
                click.echo("To create a dataset:")
                click.echo("  dr eval upload-dataset --from ground_truth/ --name my-dataset --type agent")

        except Exception as e:
            click.echo(f"❌ Error listing remote datasets: {e}")
            click.echo()

        click.echo()

    if not show_local and not show_remote:
        click.echo("Use --local or --remote to filter datasets")


@eval.command(name="status")
def status():
    """
    Show evaluation system status and quick overview.

    Example:
        dr eval status
    """
    click.echo("🔍 Evaluation System Status")
    click.echo("=" * 60)
    click.echo()

    # Components
    click.echo("📦 Components: 1 available")
    click.echo("   - report-generation")
    click.echo()

    # Local datasets
    gt_dir = Path("ground_truth")
    if gt_dir.exists():
        gt_files = list(gt_dir.glob("ground_truth_*.json"))
        click.echo(f"📁 Local Ground Truth: {len(gt_files)} example(s)")
        if gt_files:
            # Get tickers
            # Filename format: ground_truth_TICKER_DATE.json
            tickers = set()
            for f in gt_files:
                parts = f.stem.split('_')
                if len(parts) >= 4:  # ground, truth, TICKER, DATE
                    tickers.add(parts[2])
            if tickers:
                ticker_list = ', '.join(sorted(tickers))
                click.echo(f"   Tickers: {ticker_list}")
    else:
        click.echo("📁 Local Ground Truth: Not set up")
        click.echo("   Run: dr eval generate-ground-truth --num 5")
    click.echo()

    # Evaluation results
    results_dir = Path("evaluation_results")
    if results_dir.exists():
        result_files = list(results_dir.glob("eval_*.json"))
        if result_files:
            click.echo(f"📊 Evaluation Results: {len(result_files)} run(s)")
            # Show most recent
            latest = sorted(result_files)[-1]
            try:
                with open(latest, 'r') as f:
                    data = json.load(f)
                    timestamp = data.get('timestamp', 'unknown')
                    total = data.get('summary', {}).get('total', 0)
                    click.echo(f"   Latest: {latest.name} ({total} examples, {timestamp[:10]})")
            except:
                pass
        else:
            click.echo("📊 Evaluation Results: None yet")
    else:
        click.echo("📊 Evaluation Results: None yet")
    click.echo()

    # LangSmith connection
    try:
        from src.langsmith_integration import get_langsmith_client

        client = get_langsmith_client()
        if client:
            try:
                datasets = list(client.list_datasets(limit=1))
                click.echo("☁️  LangSmith: Connected ✅")
                all_datasets = list(client.list_datasets())
                click.echo(f"   Datasets: {len(all_datasets)}")
            except:
                click.echo("☁️  LangSmith: Connection error ❌")
        else:
            click.echo("☁️  LangSmith: Not configured")
            click.echo("   Set LANGSMITH_API_KEY to enable remote features")
    except:
        click.echo("☁️  LangSmith: Not configured")
    click.echo()

    click.echo("=" * 60)
    click.echo()
    click.echo("Quick Start:")
    click.echo("  dr eval list-components      # See available components")
    click.echo("  dr eval list-datasets        # See available datasets")
    click.echo("  dr eval agent --dataset ground_truth/ --local  # Run evaluation")


@eval.command(name="describe")
@click.argument('type', type=click.Choice(['component', 'dataset']))
@click.argument('name')
def describe(type: str, name: str):
    """
    Show detailed information about a component or dataset.

    Examples:
        dr eval describe component report-generation
        dr eval describe dataset ground_truth/
        dr eval describe dataset my-dataset-v1
    """
    if type == 'component':
        # Component details
        components = {
            "report-generation": {
                "name": "Report Generation",
                "description": "Isolated LLM call for generating Thai narrative reports",
                "type": "Component-level evaluation",
                "input": {
                    "ticker": "Stock ticker symbol",
                    "date": "Date for report",
                    "indicators": "Technical indicators (RSI, MACD, etc.)",
                    "prices": "Price data (open, high, low, close)",
                    "news": "News articles",
                    "percentiles": "Historical percentile rankings"
                },
                "output": {
                    "narrative": "Thai language report text"
                },
                "evaluators": [
                    "faithfulness - Numeric accuracy vs ground truth",
                    "completeness - Coverage of analytical dimensions",
                    "reasoning_quality - Quality of explanations",
                    "compliance - Format/policy adherence",
                    "hallucination_llm - LLM-as-judge semantic validation",
                    "qos - System performance metrics",
                    "cost - Operational costs"
                ],
                "usage": [
                    "# Remote (LangSmith)",
                    "dr eval component report-generation --dataset my-dataset",
                    "",
                    "# Local",
                    "dr eval component report-generation --dataset ground_truth/ --local"
                ]
            }
        }

        if name not in components:
            click.echo(f"❌ Unknown component: {name}")
            click.echo()
            click.echo("Available components:")
            click.echo("  dr eval list-components")
            return

        comp = components[name]
        click.echo(f"🔧 {comp['name']}")
        click.echo("=" * 60)
        click.echo()
        click.echo(f"Description: {comp['description']}")
        click.echo(f"Type: {comp['type']}")
        click.echo()
        click.echo("Input:")
        for key, desc in comp['input'].items():
            click.echo(f"  - {key}: {desc}")
        click.echo()
        click.echo("Output:")
        for key, desc in comp['output'].items():
            click.echo(f"  - {key}: {desc}")
        click.echo()
        click.echo("Evaluators (7 total):")
        for evaluator in comp['evaluators']:
            click.echo(f"  - {evaluator}")
        click.echo()
        click.echo("Usage:")
        for line in comp['usage']:
            if line:
                click.echo(f"  {line}")
            else:
                click.echo()

    elif type == 'dataset':
        # Dataset details
        click.echo(f"📊 Dataset: {name}")
        click.echo("=" * 60)
        click.echo()

        # Check if it's a local path
        dataset_path = Path(name)
        if dataset_path.exists() and dataset_path.is_dir():
            # Local dataset
            click.echo("Type: Local (Ground Truth)")
            click.echo(f"Path: {dataset_path.absolute()}")
            click.echo()

            gt_files = list(dataset_path.glob("ground_truth_*.json"))
            if gt_files:
                click.echo(f"Examples: {len(gt_files)} total")
                click.echo()

                # Group by ticker
                # Filename format: ground_truth_TICKER_DATE.json
                by_ticker = {}
                for f in gt_files:
                    parts = f.stem.split('_')
                    if len(parts) >= 4:  # ground, truth, TICKER, DATE
                        ticker = parts[2]
                        date = parts[3]
                        if ticker not in by_ticker:
                            by_ticker[ticker] = []
                        by_ticker[ticker].append(date)

                click.echo("Breakdown:")
                for ticker, dates in sorted(by_ticker.items()):
                    click.echo(f"  - {ticker}: {len(dates)} date(s) ({min(dates)} to {max(dates)})")
                click.echo()

                # Load one example to show structure
                try:
                    with open(gt_files[0], 'r') as f:
                        example = json.load(f)
                        click.echo("Example Structure:")
                        click.echo(f"  - ticker: {example.get('ticker', 'N/A')}")
                        click.echo(f"  - date: {example.get('date', 'N/A')}")
                        click.echo(f"  - data: {len(example.get('data', {}))} field(s)")
                        click.echo(f"  - ground_truth_report: {len(example.get('ground_truth_report', ''))} chars")
                        metadata = example.get('metadata', {})
                        click.echo(f"  - quality_tier: {metadata.get('quality_tier', 'unknown')}")
                        click.echo(f"  - status: {metadata.get('status', 'unknown')}")
                except:
                    pass

                click.echo()
                click.echo("Usage:")
                click.echo(f"  dr eval agent --dataset {name} --local")
                click.echo(f"  dr eval component report-generation --dataset {name} --local")
            else:
                click.echo("(No ground truth files found)")

        else:
            # Remote dataset (LangSmith)
            click.echo("Type: Remote (LangSmith)")
            click.echo()

            try:
                from src.langsmith_integration import get_langsmith_client

                client = get_langsmith_client()
                if not client:
                    click.echo("❌ Failed to connect to LangSmith")
                    return

                # Find dataset
                datasets = [ds for ds in client.list_datasets() if ds.name == name]
                if not datasets:
                    click.echo(f"❌ Dataset '{name}' not found in LangSmith")
                    click.echo()
                    click.echo("Available datasets:")
                    click.echo("  dr eval list-datasets --remote")
                    return

                ds = datasets[0]
                click.echo(f"Name: {ds.name}")
                click.echo(f"ID: {ds.id}")
                if ds.description:
                    click.echo(f"Description: {ds.description}")
                click.echo()
                click.echo(f"🔗 View at: https://smith.langchain.com/datasets/{ds.id}")
                click.echo()
                click.echo("Usage:")
                click.echo(f"  dr eval agent --dataset {name}")
                click.echo(f"  dr eval component report-generation --dataset {name}")

            except Exception as e:
                click.echo(f"❌ Error: {e}")


@eval.command(name="generate-ground-truth")
@click.option(
    '--num',
    type=int,
    default=5,
    help='Number of ground truth examples to generate'
)
@click.option(
    '--ticker',
    type=str,
    default=None,
    help='Specific ticker to generate for (default: random selection)'
)
@click.option(
    '--output-dir',
    type=click.Path(),
    default='ground_truth',
    help='Output directory for ground truth JSON files'
)
@click.option(
    '--quality-tier',
    type=click.Choice(['mock', 'silver', 'gold']),
    default='mock',
    help='Quality tier: mock (current model), silver (expensive model), gold (manually refined)'
)
@click.option(
    '--days-back',
    type=int,
    default=7,
    help='How many days back to look for historical data'
)
def generate_ground_truth(num: int, ticker: str, output_dir: str, quality_tier: str, days_back: int):
    """
    Generate ground truth examples from historical data.

    This command:
    1. Queries historical data from database
    2. Generates reports using current model
    3. Saves as JSON files for manual refinement

    Example:
        dr eval generate-ground-truth --num 5
        dr eval generate-ground-truth --num 10 --ticker PTT
    """
    from src.database import TickerDatabase
    from src.agent import TickerAnalysisAgent
    from dataclasses import asdict

    click.echo(f"🔧 Generating {num} ground truth examples (quality tier: {quality_tier})...")
    click.echo(f"📁 Output directory: {output_dir}")

    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)

    # Initialize database and agent
    db = TickerDatabase()
    agent = TickerAnalysisAgent()

    # Get available tickers and dates from database
    conn = sqlite3.connect('data/ticker_data.db')
    cursor = conn.cursor()

    # Query for historical reports with complete data
    query = """
    SELECT DISTINCT r.ticker, r.date, r.context_json, r.report_text
    FROM reports r
    WHERE r.context_json IS NOT NULL
      AND r.context_json != ''
      AND r.report_text IS NOT NULL
      AND r.report_text != ''
    """

    if ticker:
        query += f" AND r.ticker = '{ticker}'"

    query += f" ORDER BY r.date DESC LIMIT {num}"

    cursor.execute(query)
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        click.echo("❌ No historical data found. Please generate some reports first.")
        return

    click.echo(f"📊 Found {len(rows)} historical reports to use")
    click.echo()

    generated_count = 0
    scores_summary = []

    for row in rows:
        ticker_sym = row[0]
        date = row[1]
        context_json_str = row[2]
        existing_report = row[3]

        try:
            # Parse context data
            context_data = json.loads(context_json_str)

            # For mock tier, use existing report (LLM-generated)
            # For silver/gold tier, would generate with expensive model (future)
            if quality_tier == 'mock':
                ground_truth_report = existing_report
                click.echo(f"📝 Using existing report for {ticker_sym} ({date})")
            else:
                # Future: Generate with expensive model
                click.echo(f"⚠️  {quality_tier} tier not yet implemented, using mock")
                ground_truth_report = existing_report

            # Get scores from database if available
            score_row = db.get_historical_scores(ticker_sym, days=1)
            scores = {}
            if score_row:
                # Find the score for this specific date
                for s in score_row:
                    if s.get('date') == date:
                        scores = {
                            'faithfulness': s.get('faithfulness_score', 0),
                            'completeness': s.get('completeness_score', 0),
                            'reasoning_quality': s.get('reasoning_quality_score', 0),
                            'compliance': s.get('compliance_score', 0),
                            'qos': s.get('qos_score', 0),
                            'cost': s.get('cost_efficiency_score', 0)
                        }
                        break

            # Build ground truth JSON
            ground_truth = {
                "ticker": ticker_sym,
                "date": date,
                "data": context_data,
                "ground_truth_report": ground_truth_report,
                "metadata": {
                    "quality_tier": quality_tier,
                    "needs_refinement": quality_tier == 'mock',
                    "generated_by": "gpt-4o-mini" if quality_tier == 'mock' else "unknown",
                    "generated_at": datetime.utcnow().isoformat(),
                    "status": "DRAFT" if quality_tier == 'mock' else "REFINED",
                    "scores": scores
                }
            }

            # Save to file
            filename = f"ground_truth_{ticker_sym}_{date}.json"
            filepath = os.path.join(output_dir, filename)

            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(ground_truth, f, ensure_ascii=False, indent=2)

            generated_count += 1
            avg_score = sum(scores.values()) / len(scores) if scores else 0
            scores_summary.append(avg_score)

            # Show progress
            score_str = f"avg: {avg_score:.2f}" if scores else "no scores"
            click.echo(f"✅ Generated: {filename} ({score_str})")

        except Exception as e:
            click.echo(f"❌ Error generating for {ticker_sym} ({date}): {e}")
            continue

    # Summary
    click.echo()
    click.echo("=" * 60)
    click.echo(f"✅ Generated {generated_count}/{num} ground truth examples")
    click.echo(f"📊 Quality tier: {quality_tier.upper()}")

    if scores_summary:
        avg_score = sum(scores_summary) / len(scores_summary)
        click.echo(f"📈 Average score: {avg_score:.2f}")

    click.echo(f"📁 Location: {output_dir}/")
    click.echo("=" * 60)

    if quality_tier == 'mock':
        click.echo()
        click.echo("⚠️  IMPORTANT: These are MOCK placeholders")
        click.echo("   Manual refinement recommended before using as gold standard")
        click.echo()
        click.echo("Next steps:")
        click.echo(f"1. Review reports in {output_dir}/")
        click.echo("2. Manually refine to fix issues")
        click.echo("3. Upload to LangSmith:")
        click.echo(f"   dr eval upload-dataset --from {output_dir}/ --name my-gold-v1")


@eval.command(name="upload-dataset")
@click.option(
    '--from',
    'from_dir',
    type=click.Path(exists=True),
    required=True,
    help='Directory containing ground truth JSON files'
)
@click.option(
    '--name',
    'dataset_name',
    type=str,
    required=True,
    help='Dataset name in LangSmith'
)
@click.option(
    '--type',
    'dataset_type',
    type=click.Choice(['agent', 'component']),
    default='agent',
    help='Dataset type: agent (end-to-end) or component (isolated LLM)'
)
@click.option(
    '--description',
    type=str,
    default='',
    help='Dataset description'
)
def upload_dataset(from_dir: str, dataset_name: str, dataset_type: str, description: str):
    """
    Upload ground truth examples to LangSmith dataset.

    Example:
        dr eval upload-dataset --from ground_truth/ --name dr-eval-v1 --type agent
    """
    click.echo(f"📤 Uploading dataset to LangSmith...")
    click.echo(f"📁 Source: {from_dir}")
    click.echo(f"🏷️  Name: {dataset_name}")
    click.echo(f"🔧 Type: {dataset_type}")
    click.echo()

    # Get LangSmith client using helper that handles personal vs org API keys
    from src.langsmith_integration import get_langsmith_client

    try:
        client = get_langsmith_client()
        if not client:
            click.echo("❌ Failed to initialize LangSmith client")
            click.echo("   Make sure LANGSMITH_API_KEY is set in environment")
            return
    except Exception as e:
        click.echo(f"❌ Failed to initialize LangSmith client: {e}")
        click.echo("   Make sure LANGSMITH_API_KEY is set in environment")
        return

    # Load ground truth files
    ground_truth_files = list(Path(from_dir).glob("ground_truth_*.json"))

    if not ground_truth_files:
        click.echo(f"❌ No ground truth files found in {from_dir}")
        click.echo("   Expected files matching pattern: ground_truth_*.json")
        return

    click.echo(f"📊 Found {len(ground_truth_files)} ground truth files")

    # Create or get dataset
    try:
        # Try to create new dataset
        dataset = client.create_dataset(
            dataset_name=dataset_name,
            description=description or f"DR evaluation dataset ({dataset_type}-level)"
        )
        click.echo(f"✅ Created new dataset: {dataset_name}")
    except Exception as e:
        # Dataset might already exist, try to get it
        try:
            datasets = list(client.list_datasets(dataset_name=dataset_name))
            if datasets:
                dataset = datasets[0]
                click.echo(f"ℹ️  Using existing dataset: {dataset_name}")
            else:
                click.echo(f"❌ Failed to create or find dataset: {e}")
                return
        except Exception as e2:
            click.echo(f"❌ Failed to get dataset: {e2}")
            return

    # Upload examples
    uploaded_count = 0

    for filepath in ground_truth_files:
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                ground_truth = json.load(f)

            ticker = ground_truth['ticker']
            date = ground_truth['date']
            data = ground_truth['data']
            report = ground_truth['ground_truth_report']
            metadata = ground_truth['metadata']

            # Build inputs based on dataset type
            if dataset_type == 'agent':
                # Agent-level: only ticker and date
                inputs = {
                    "ticker": ticker,
                    "date": date
                }
            else:
                # Component-level: include all pre-fetched data
                inputs = {
                    "ticker": ticker,
                    "date": date,
                    **data  # Unpack all context data
                }

            # Build outputs
            outputs = {
                "narrative": report
            }

            # Build example metadata
            example_metadata = {
                **metadata,
                "dataset_type": dataset_type,
                "source_file": filepath.name
            }

            # Create example in LangSmith
            client.create_example(
                inputs=inputs,
                outputs=outputs,
                metadata=example_metadata,
                dataset_id=dataset.id
            )

            uploaded_count += 1
            click.echo(f"✅ Uploaded: {ticker} ({date})")

        except Exception as e:
            click.echo(f"❌ Error uploading {filepath.name}: {e}")
            continue

    # Summary
    click.echo()
    click.echo("=" * 60)
    click.echo(f"✅ Uploaded {uploaded_count}/{len(ground_truth_files)} examples")
    click.echo(f"🏷️  Dataset: {dataset_name}")
    click.echo(f"🔗 View at: https://smith.langchain.com/datasets")
    click.echo("=" * 60)
    click.echo()
    click.echo("Next steps:")
    click.echo(f"  dr eval agent --dataset {dataset_name}")
    click.echo(f"  dr eval component report-generation --dataset {dataset_name}")


@eval.command(name="agent")
@click.option(
    '--dataset',
    type=str,
    required=True,
    help='Dataset name (LangSmith dataset name or local directory path)'
)
@click.option(
    '--experiment',
    type=str,
    default=None,
    help='Experiment name (default: auto-generated with timestamp)'
)
@click.option(
    '--local',
    is_flag=True,
    default=False,
    help='Run evaluation locally without LangSmith (saves results to JSON)'
)
@click.option(
    '--ticker',
    type=str,
    default=None,
    help='Filter evaluation to specific ticker (e.g., D05.SI, PTT). Default: evaluate all tickers'
)
@click.pass_context
def eval_agent(ctx, dataset: str, experiment: str, local: bool, ticker: str):
    """
    Run agent-level evaluation (end-to-end workflow).

    Examples:
        # Remote (LangSmith)
        dr eval agent --dataset dr-eval-v1

        # Local (no LangSmith needed)
        dr eval agent --dataset ground_truth/ --local
    """
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

    if local:
        # Local evaluation
        from scripts.eval_local import run_local_evaluation

        click.echo(f"🚀 Running LOCAL agent-level evaluation...")
        click.echo(f"📁 Dataset path: {dataset}")
        if ticker:
            click.echo(f"🎯 Filtering to ticker: {ticker}")
        click.echo()

        try:
            results = run_local_evaluation(
                dataset_path=dataset,
                evaluation_type="agent",
                output_dir="evaluation_results",
                ticker_filter=ticker
            )

            click.echo()
            click.echo("=" * 60)
            click.echo("✅ Local evaluation complete!")
            click.echo(f"📊 Evaluated {results['summary']['total']} examples")

            # Show ticker summary
            ticker_stats = results['summary'].get('tickers', {})
            if ticker_stats:
                tickers = sorted(ticker_stats.keys())
                if len(tickers) == 1:
                    click.echo(f"🏷️  Ticker: {tickers[0]}")
                else:
                    ticker_list = ', '.join(tickers)
                    click.echo(f"🏷️  Tickers: {ticker_list} ({len(tickers)} total)")

            click.echo()
            click.echo("Average Scores:")
            for metric, score in results['summary']['avg_scores'].items():
                click.echo(f"  {metric}: {score:.3f}")
            click.echo()
            click.echo(f"📁 Results: {results['output_file']}")
            click.echo("=" * 60)

        except Exception as e:
            click.echo(f"❌ Evaluation failed: {e}")
            import traceback
            traceback.print_exc()
            return

    else:
        # Remote evaluation (LangSmith)
        from scripts.eval_agent import run_agent_evaluation

        # Get workspace from context
        workspace = ctx.obj.get('workspace')

        click.echo(f"🚀 Running agent-level evaluation...")
        click.echo(f"📊 Dataset: {dataset}")

        if experiment:
            click.echo(f"🧪 Experiment: {experiment}")
        else:
            experiment = f"dr-agent-{dataset}-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
            click.echo(f"🧪 Experiment: {experiment} (auto-generated)")

        click.echo()

        try:
            results = run_agent_evaluation(dataset, experiment, workspace)

            click.echo()
            click.echo("=" * 60)
            click.echo("✅ Evaluation complete!")
            click.echo(f"🔗 View results: https://smith.langchain.com/")
            click.echo("=" * 60)

        except Exception as e:
            click.echo(f"❌ Evaluation failed: {e}")
            import traceback
            traceback.print_exc()
            return


@eval.command(name="component")
@click.argument('component_name')
@click.option(
    '--dataset',
    type=str,
    required=True,
    help='Dataset name (LangSmith dataset name or local directory path)'
)
@click.option(
    '--experiment',
    type=str,
    default=None,
    help='Experiment name (default: auto-generated with timestamp)'
)
@click.option(
    '--local',
    is_flag=True,
    default=False,
    help='Run evaluation locally without LangSmith (saves results to JSON)'
)
@click.option(
    '--ticker',
    type=str,
    default=None,
    help='Filter evaluation to specific ticker (e.g., D05.SI, PTT). Default: evaluate all tickers'
)
@click.pass_context
def eval_component(ctx, component_name: str, dataset: str, experiment: str, local: bool, ticker: str):
    """
    Run component-level evaluation (isolated LLM call).

    Available components:
      - report-generation: Report generation node

    Examples:
        # Remote (LangSmith)
        dr eval component report-generation --dataset dr-eval-v1

        # Local (no LangSmith needed)
        dr eval component report-generation --dataset ground_truth/ --local
    """
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

    # Validate component name
    valid_components = ['report-generation']
    if component_name not in valid_components:
        click.echo(f"❌ Unknown component: {component_name}")
        click.echo(f"   Valid components: {', '.join(valid_components)}")
        return

    if local:
        # Local evaluation
        from scripts.eval_local import run_local_evaluation

        click.echo(f"🚀 Running LOCAL component-level evaluation...")
        click.echo(f"🔧 Component: {component_name}")
        click.echo(f"📁 Dataset path: {dataset}")
        if ticker:
            click.echo(f"🎯 Filtering to ticker: {ticker}")
        click.echo()

        try:
            results = run_local_evaluation(
                dataset_path=dataset,
                evaluation_type="component",
                component_name=component_name,
                output_dir="evaluation_results",
                ticker_filter=ticker
            )

            click.echo()
            click.echo("=" * 60)
            click.echo("✅ Local evaluation complete!")
            click.echo(f"📊 Evaluated {results['summary']['total']} examples")

            # Show ticker summary
            ticker_stats = results['summary'].get('tickers', {})
            if ticker_stats:
                tickers = sorted(ticker_stats.keys())
                if len(tickers) == 1:
                    click.echo(f"🏷️  Ticker: {tickers[0]}")
                else:
                    ticker_list = ', '.join(tickers)
                    click.echo(f"🏷️  Tickers: {ticker_list} ({len(tickers)} total)")

            click.echo()
            click.echo("Average Scores:")
            for metric, score in results['summary']['avg_scores'].items():
                click.echo(f"  {metric}: {score:.3f}")
            click.echo()
            click.echo(f"📁 Results: {results['output_file']}")
            click.echo("=" * 60)

        except Exception as e:
            click.echo(f"❌ Evaluation failed: {e}")
            import traceback
            traceback.print_exc()
            return

    else:
        # Remote evaluation (LangSmith)
        from scripts.eval_component import run_component_evaluation

        # Get workspace from context
        workspace = ctx.obj.get('workspace')

        click.echo(f"🚀 Running component-level evaluation...")
        click.echo(f"🔧 Component: {component_name}")
        click.echo(f"📊 Dataset: {dataset}")

        if experiment:
            click.echo(f"🧪 Experiment: {experiment}")
        else:
            experiment = f"dr-component-{component_name}-{dataset}-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
            click.echo(f"🧪 Experiment: {experiment} (auto-generated)")

        click.echo()

        try:
            results = run_component_evaluation(component_name, dataset, experiment, workspace)

            click.echo()
            click.echo("=" * 60)
            click.echo("✅ Evaluation complete!")
            click.echo(f"🔗 View results: https://smith.langchain.com/")
            click.echo("=" * 60)

        except Exception as e:
            click.echo(f"❌ Evaluation failed: {e}")
            import traceback
            traceback.print_exc()
            return
