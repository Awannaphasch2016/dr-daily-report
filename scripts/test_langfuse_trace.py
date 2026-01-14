#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Test script: Create real Langfuse trace to verify connectivity.

This script creates an actual trace in Langfuse to verify:
1. Langfuse credentials are working
2. Traces appear in the UI
3. Prompt metadata is correctly attached

Run: doppler run -c dev -- python scripts/test_langfuse_trace.py

Based on Langfuse SDK v3 documentation:
https://langfuse.com/docs/observability/sdk/overview
"""

import os
import sys

# Check required env vars
required_vars = ["LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY"]
missing = [v for v in required_vars if not os.environ.get(v)]
if missing:
    print(f"❌ Missing environment variables: {missing}")
    print("Run with: doppler run -c dev -- python scripts/test_langfuse_trace.py")
    sys.exit(1)

from langfuse import get_client, observe

def main():
    print("=" * 60)
    print("TEST: Create Real Langfuse Trace")
    print("=" * 60)
    print()

    # Initialize Langfuse client (v3 API)
    print("📡 Connecting to Langfuse...")
    langfuse = get_client()

    # Verify connection
    try:
        auth_ok = langfuse.auth_check()
        print(f"✅ Langfuse auth check: {auth_ok}")
    except Exception as e:
        print(f"❌ Langfuse auth failed: {e}")
        sys.exit(1)

    # Create a test trace using context manager (v3 API)
    print()
    print("📝 Creating test trace...")

    trace_id = None

    with langfuse.start_as_current_observation(
        as_type="span",
        name="prompt-version-test"
    ) as span:
        # Update trace with metadata
        langfuse.update_current_trace(
            user_id="test-user",
            session_id="test-session",
            tags=["test", "prompt-validation"],
            metadata={
                "prompt_name": "report-generation",
                "prompt_version": "test-v1",
                "prompt_source": "test-script",
                "ticker": "TEST",
                "environment": os.environ.get("ENVIRONMENT", "dev"),
                "test_purpose": "Validate Langfuse connectivity"
            }
        )

        # Get trace ID
        trace_id = langfuse.get_current_trace_id()

        # Add a generation span (simulating LLM call)
        with langfuse.start_as_current_observation(
            as_type="generation",
            name="test-generation",
            model="test-model",
            input="Test input: Generate report for TEST ticker"
        ) as generation:
            # Simulate LLM output
            generation.update(
                output="Test output: This is a simulated report for validation purposes.",
                metadata={"prompt_version": "test-v1"}
            )

        # Update span output
        span.update(output="Test trace completed successfully")

    # Add a score (using create_score for v3 API)
    if trace_id:
        try:
            langfuse.create_score(
                trace_id=trace_id,
                name="test-score",
                value=0.95,
                comment="Test score for validation"
            )
        except AttributeError:
            # SDK may not have create_score, skip scoring
            print("⚠️ Score API not available, skipping score creation")

    # Flush to ensure data is sent
    print("📤 Flushing traces to Langfuse...")
    langfuse.flush()

    print()
    print("=" * 60)
    print("✅ SUCCESS: Trace created!")
    print("=" * 60)
    print()
    print(f"Trace ID: {trace_id}")
    print()
    print("🔗 View in Langfuse UI:")
    host = os.environ.get("LANGFUSE_HOST", "https://us.cloud.langfuse.com")
    project_id = "cmjcrupdq01qlad07eopx2bw5"  # From user's URL
    print(f"   {host}/project/{project_id}/traces")
    print()
    print("Filter by: tags = 'test' or name = 'prompt-version-test'")

    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
