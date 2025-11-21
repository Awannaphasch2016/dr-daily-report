#!/usr/bin/env python3
"""
LangSmith Runner - Standalone script for executing LangSmith commands

This module is designed to be executed as a subprocess with doppler environment
variables. It contains all LangSmith API logic separated from the CLI command
definitions.

Usage:
    python -m dr_cli.commands.langsmith_runner --command list-runs --limit 10
    doppler run -- python -m dr_cli.commands.langsmith_runner --command show-feedback --run-id abc123
"""

import sys
import os
import argparse
from datetime import datetime, timedelta
from typing import List, Dict, Any
from langsmith import Client


def get_langsmith_client() -> Client:
    """Get authenticated LangSmith client"""
    api_key = os.getenv('LANGSMITH_API_KEY')
    if not api_key:
        print("❌ LANGSMITH_API_KEY not set", file=sys.stderr)
        print("   Run with --doppler flag: dr --doppler langsmith <command>", file=sys.stderr)
        sys.exit(1)

    return Client(api_key=api_key)


def format_duration(seconds: float) -> str:
    """Format duration in seconds to human-readable string"""
    if seconds < 1:
        return f"{seconds*1000:.0f}ms"
    elif seconds < 60:
        return f"{seconds:.1f}s"
    else:
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes}m {secs}s"


def format_score(score: float) -> str:
    """Format score with color and percentage"""
    percentage = score * 100

    if percentage >= 90:
        return f"✅ {percentage:.1f}%"
    elif percentage >= 75:
        return f"⚠️  {percentage:.1f}%"
    else:
        return f"❌ {percentage:.1f}%"


def cmd_list_runs(client: Client, limit: int, project: str, hours: int) -> int:
    """List recent traces with feedback summary"""
    try:
        print(f"\n📊 Recent Traces (last {hours} hours, project: {project})")
        print("=" * 100)

        # Calculate time range
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=hours)

        # Fetch runs
        runs = list(client.list_runs(
            project_name=project,
            start_time=start_time,
            limit=limit
        ))

        if not runs:
            print(f"⚠️  No traces found in the last {hours} hours")
            return 0

        print(f"\nFound {len(runs)} trace(s):\n")

        # Display runs
        runs_with_feedback = 0
        for i, run in enumerate(runs, 1):
            # Get feedback count
            feedback_list = list(client.list_feedback(run_ids=[str(run.id)]))
            feedback_count = len(feedback_list)
            if feedback_count > 0:
                runs_with_feedback += 1

            # Format output
            duration = format_duration((run.end_time - run.start_time).total_seconds()) if run.end_time else "Running..."
            status = "✅" if run.status == 'success' else "❌" if run.error else "⏳"
            feedback_str = f"📊 {feedback_count}" if feedback_count > 0 else "No feedback"

            # Get ticker from inputs
            ticker = "N/A"
            if run.inputs and 'ticker' in run.inputs:
                ticker = run.inputs['ticker']

            print(f"{i}. {status} {run.name} (ticker: {ticker})")
            print(f"   Run ID: {run.id}")
            print(f"   Started: {run.start_time}")
            print(f"   Duration: {duration}")
            print(f"   Feedback: {feedback_str}")
            print()

        # Summary
        print("=" * 100)
        print(f"📋 Summary: {len(runs)} traces, {runs_with_feedback} with feedback ({runs_with_feedback/len(runs)*100:.1f}%)")
        return 0

    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        return 1


def cmd_show_run(client: Client, run_id: str) -> int:
    """Show detailed information about a specific trace"""
    try:
        # Fetch run
        run = client.read_run(run_id)

        print(f"\n📊 Trace Details")
        print("=" * 100)

        # Basic info
        print(f"\nRun ID: {run.id}")
        print(f"Name: {run.name}")
        print(f"Status: {run.status if hasattr(run, 'status') else 'completed'}")
        print(f"Started: {run.start_time}")
        if run.end_time:
            duration = format_duration((run.end_time - run.start_time).total_seconds())
            print(f"Duration: {duration}")

        # Inputs
        if run.inputs:
            print(f"\n📥 Inputs:")
            for key, value in run.inputs.items():
                if len(str(value)) > 100:
                    print(f"  {key}: {str(value)[:100]}...")
                else:
                    print(f"  {key}: {value}")

        # Outputs
        if run.outputs:
            print(f"\n📤 Outputs:")
            for key, value in run.outputs.items():
                if len(str(value)) > 200:
                    print(f"  {key}: {str(value)[:200]}...")
                else:
                    print(f"  {key}: {value}")

        # Feedback summary
        feedback_list = list(client.list_feedback(run_ids=[str(run.id)]))

        print(f"\n📊 Feedback: {len(feedback_list)} evaluation(s)")
        if feedback_list:
            for fb in feedback_list:
                print(f"  • {fb.key}: {fb.score:.3f}")

        print("\n" + "=" * 100)
        print(f"💡 Use 'dr langsmith show-feedback {run_id}' to see detailed feedback")
        return 0

    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        return 1


def cmd_show_feedback(client: Client, run_id: str) -> int:
    """Show evaluation feedback for a trace"""
    try:
        # Fetch run info
        try:
            run = client.read_run(run_id)
            run_name = run.name
            ticker = run.inputs.get('ticker', 'N/A') if run.inputs else 'N/A'
        except:
            run_name = "Unknown"
            ticker = "N/A"

        print(f"\n📊 Evaluation Scores")
        print("=" * 100)
        print(f"Trace: {run_name} (ticker: {ticker})")
        print(f"Run ID: {run_id}")
        print("=" * 100)

        # Fetch feedback
        feedback_list = list(client.list_feedback(run_ids=[run_id]))

        if not feedback_list:
            print("\n⚠️  No feedback found for this run")
            print("   Evaluation may not have completed yet or failed.")
            return 0

        # Sort feedback by key
        feedback_order = [
            'faithfulness_score',
            'completeness_score',
            'reasoning_quality_score',
            'compliance_score',
            'qos_score',
            'cost_score'
        ]

        feedback_dict = {fb.key: fb for fb in feedback_list}

        # Display feedback
        print()
        for key in feedback_order:
            if key in feedback_dict:
                fb = feedback_dict[key]
                score_formatted = format_score(fb.score)

                print(f"{score_formatted} {key}: {fb.score:.3f} ({fb.score*100:.1f}%)")
                if fb.comment:
                    # Wrap comment to 80 chars
                    import textwrap
                    wrapped = textwrap.fill(fb.comment, width=95, initial_indent='   ', subsequent_indent='   ')
                    print(wrapped)
                print()

        print("=" * 100)
        return 0

    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        return 1


def cmd_stats(client: Client, limit: int, hours: int, project: str) -> int:
    """Show aggregate statistics across recent traces"""
    try:
        print(f"\n📈 LangSmith Statistics")
        print("=" * 100)
        print(f"Period: Last {hours} hours")
        print(f"Project: {project}")
        print(f"Analyzing up to {limit} traces")
        print("=" * 100)

        # Calculate time range
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=hours)

        # Fetch runs
        runs = list(client.list_runs(
            project_name=project,
            start_time=start_time,
            limit=limit
        ))

        if not runs:
            print(f"\n⚠️  No traces found in the last {hours} hours")
            return 0

        # Collect feedback from all runs
        all_scores = {
            'faithfulness_score': [],
            'completeness_score': [],
            'reasoning_quality_score': [],
            'compliance_score': [],
            'qos_score': [],
            'cost_score': []
        }

        runs_with_feedback = 0
        total_duration = 0
        successful_runs = 0

        for run in runs:
            if run.end_time:
                total_duration += (run.end_time - run.start_time).total_seconds()

            if run.status == 'success' or (hasattr(run, 'error') and not run.error):
                successful_runs += 1

            feedback_list = list(client.list_feedback(run_ids=[str(run.id)]))

            if feedback_list:
                runs_with_feedback += 1
                for fb in feedback_list:
                    if fb.key in all_scores:
                        all_scores[fb.key].append(fb.score)

        # Calculate statistics
        print(f"\n📊 Overall Statistics:")
        print(f"  Total Traces: {len(runs)}")
        print(f"  With Feedback: {runs_with_feedback} ({runs_with_feedback/len(runs)*100:.1f}%)")
        print(f"  Avg Duration: {format_duration(total_duration/len(runs)) if runs else 'N/A'}")
        print(f"  Success Rate: {successful_runs/len(runs)*100:.1f}%")

        # Score statistics
        if runs_with_feedback > 0:
            print(f"\n📈 Evaluation Scores (average across {runs_with_feedback} traces):")

            for key, scores in all_scores.items():
                if scores:
                    avg = sum(scores) / len(scores)
                    min_score = min(scores)
                    max_score = max(scores)

                    avg_formatted = format_score(avg)

                    print(f"  {avg_formatted} {key:25s} avg: {avg*100:.1f}%  (min: {min_score*100:.1f}%, max: {max_score*100:.1f}%)")
        else:
            print("\n⚠️  No feedback data available for statistics")

        print("\n" + "=" * 100)
        return 0

    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        return 1


def cmd_projects(client: Client) -> int:
    """List available LangSmith projects"""
    try:
        print("\n📂 LangSmith Projects")
        print("=" * 100)

        # Note: The LangSmith SDK doesn't have a direct list_projects method
        # This is a placeholder that shows the default project
        print("\n✅ Using project: default")
        print("\n💡 Tip: Set LANGSMITH_PROJECT environment variable to use a different project")
        print("   Or use --project flag with other commands")

        print("\n" + "=" * 100)
        return 0

    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        return 1


def main():
    """Main entry point for langsmith runner"""
    parser = argparse.ArgumentParser(description='LangSmith CLI Runner')
    parser.add_argument('--command', required=True,
                       choices=['list-runs', 'show-run', 'show-feedback', 'stats', 'projects'],
                       help='Command to execute')

    # list-runs options
    parser.add_argument('--limit', type=int, default=10, help='Number of runs to show')
    parser.add_argument('--project', default='default', help='Project name')
    parser.add_argument('--hours', type=int, default=24, help='Look back hours')

    # show-run, show-feedback options
    parser.add_argument('--run-id', help='Run ID for show-run and show-feedback commands')

    args = parser.parse_args()

    # Get client
    client = get_langsmith_client()

    # Execute command
    if args.command == 'list-runs':
        return cmd_list_runs(client, args.limit, args.project, args.hours)
    elif args.command == 'show-run':
        if not args.run_id:
            print("❌ Error: --run-id required for show-run command", file=sys.stderr)
            return 1
        return cmd_show_run(client, args.run_id)
    elif args.command == 'show-feedback':
        if not args.run_id:
            print("❌ Error: --run-id required for show-feedback command", file=sys.stderr)
            return 1
        return cmd_show_feedback(client, args.run_id)
    elif args.command == 'stats':
        return cmd_stats(client, args.limit, args.hours, args.project)
    elif args.command == 'projects':
        return cmd_projects(client)
    else:
        print(f"❌ Error: Unknown command: {args.command}", file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
