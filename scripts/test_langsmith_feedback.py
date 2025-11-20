#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LangSmith Feedback Diagnostic Tool

Queries LangSmith to check if feedback is being recorded on traces.
"""

import os
import sys
from datetime import datetime, timedelta
from langsmith import Client

def check_langsmith_feedback():
    """Check recent LangSmith traces for feedback"""

    # Initialize client
    api_key = os.getenv('LANGSMITH_API_KEY')
    if not api_key:
        print("❌ LANGSMITH_API_KEY not set")
        return

    print("🔍 Connecting to LangSmith...")
    client = Client(api_key=api_key)

    try:
        # Get project info
        print(f"✅ Connected to LangSmith")
        print()

        # List all projects first
        print("📂 Fetching projects...")
        try:
            # Try to get project name from environment or use default
            project_name = os.getenv('LANGSMITH_PROJECT', 'default')
            print(f"   Using project: {project_name}")
        except:
            project_name = 'default'

        # List recent runs (last hour)
        print("\n📊 Fetching recent traces (last 1 hour)...")
        print("-" * 80)

        # Calculate time range
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=1)

        # Query runs with project name
        runs = list(client.list_runs(
            project_name=project_name,
            start_time=start_time,
            limit=10
        ))

        if not runs:
            print("⚠️  No traces found in the last hour")
            print("   Try running: dr --doppler util report SIA19")
            return

        print(f"Found {len(runs)} trace(s):\n")

        # Check each run for feedback
        for i, run in enumerate(runs, 1):
            print(f"{'='*80}")
            print(f"Trace {i}: {run.name}")
            print(f"{'='*80}")
            print(f"  Run ID: {run.id}")
            print(f"  Started: {run.start_time}")
            print(f"  Duration: {(run.end_time - run.start_time).total_seconds():.2f}s" if run.end_time else "Running...")
            print(f"  Status: {run.status if hasattr(run, 'status') else 'completed'}")

            # Get inputs/outputs
            if run.inputs:
                ticker = run.inputs.get('ticker', 'N/A')
                print(f"  Input: ticker={ticker}")

            # Check for feedback
            print(f"\n  🔍 Checking for feedback...")
            try:
                # List feedback for this run
                feedback_list = list(client.list_feedback(run_ids=[str(run.id)]))

                if feedback_list:
                    print(f"  ✅ Found {len(feedback_list)} feedback entries:")
                    for fb in feedback_list:
                        print(f"     • {fb.key}: {fb.score:.3f} - {fb.comment[:80]}...")
                else:
                    print(f"  ❌ NO FEEDBACK FOUND")
                    print(f"  ⚠️  This trace has no evaluation scores attached!")

            except Exception as e:
                print(f"  ❌ Error checking feedback: {e}")

            print()

        # Summary
        print(f"{'='*80}")
        print("📋 Summary")
        print(f"{'='*80}")

        total_traces = len(runs)
        traces_with_feedback = sum(1 for run in runs if list(client.list_feedback(run_ids=[str(run.id)])))
        traces_without_feedback = total_traces - traces_with_feedback

        print(f"  Total traces: {total_traces}")
        print(f"  Traces with feedback: {traces_with_feedback}")
        print(f"  Traces without feedback: {traces_without_feedback}")

        if traces_without_feedback > 0:
            print(f"\n  ⚠️  {traces_without_feedback} trace(s) are missing feedback!")
            print(f"  Possible causes:")
            print(f"    1. Background evaluation thread not completing")
            print(f"    2. Errors in async_evaluate_and_log()")
            print(f"    3. client.create_feedback() failing silently")
            print(f"    4. Run ID not being captured correctly")
            print(f"\n  💡 Next steps:")
            print(f"    1. Check logs for errors during evaluation")
            print(f"    2. Verify background thread completes")
            print(f"    3. Add explicit logging to create_feedback() calls")

    except Exception as e:
        print(f"❌ Error querying LangSmith: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    check_langsmith_feedback()
