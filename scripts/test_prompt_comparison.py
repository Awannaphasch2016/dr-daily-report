#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Test script: Compare two prompt versions with real Langfuse traces.

Creates traces for two different prompt versions to demonstrate
the A/B testing capability.

Run: doppler run -c dev -- python scripts/test_prompt_comparison.py
"""

import os
import sys
import time

# Check required env vars
required_vars = ["LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY"]
missing = [v for v in required_vars if not os.environ.get(v)]
if missing:
    print(f"❌ Missing environment variables: {missing}")
    print("Run with: doppler run -c dev -- python scripts/test_prompt_comparison.py")
    sys.exit(1)

from langfuse import get_client


def simulate_report_with_prompt_version(langfuse, ticker: str, prompt_version: str):
    """Generate a trace simulating report generation with specific prompt version."""

    # Simulate different prompt content based on version
    prompts = {
        "v1": "Write a brief report for {ticker}. Keep it under 200 words.",
        "v2": "You are an expert Thai analyst. Write a 250-350 word report for {ticker} with sections: Story, Analysis, Action, Risk."
    }

    prompt_content = prompts.get(prompt_version, prompts["v1"])

    with langfuse.start_as_current_observation(
        as_type="span",
        name="generate-report"
    ) as span:
        # Set trace metadata with prompt version
        langfuse.update_current_trace(
            user_id="prompt-comparison-test",
            session_id=f"comparison-{prompt_version}",
            tags=["prompt-comparison", f"prompt-{prompt_version}"],
            metadata={
                "prompt_name": "report-generation",
                "prompt_version": prompt_version,
                "prompt_source": "test-comparison",
                "ticker": ticker,
                "environment": os.environ.get("ENVIRONMENT", "dev")
            }
        )

        trace_id = langfuse.get_current_trace_id()

        # Simulate LLM generation
        with langfuse.start_as_current_observation(
            as_type="generation",
            name="llm-generation",
            model="gpt-4o",
            input=prompt_content.format(ticker=ticker)
        ) as generation:
            # Simulate different quality outputs
            if prompt_version == "v1":
                output = f"{ticker}: หุ้นนี้น่าสนใจ ราคาปัจจุบัน 35.50 บาท แนะนำ HOLD"
                time.sleep(0.1)  # Simulate faster response
            else:
                output = f"""📖 **เรื่องราวของหุ้นตัวนี้**
{ticker} กำลังเคลื่อนที่ในตลาดที่มีความไม่แน่นอนปานกลาง

💡 **สิ่งที่คุณต้องรู้**
RSI อยู่ที่ 65 ซึ่งแสดงโมเมนตัมขาขึ้น

🎯 **ควรทำอะไรตอนนี้?**
**HOLD** - รอดูทิศทางตลาด

⚠️ **ระวังอะไร?**
ถ้า RSI พุ่งเกิน 70 ระวังการปรับฐาน"""
                time.sleep(0.15)  # Simulate slightly slower but better response

            generation.update(
                output=output,
                metadata={"prompt_version": prompt_version}
            )

        span.update(output=f"Report generated for {ticker} with prompt {prompt_version}")

    return trace_id


def main():
    print("=" * 60)
    print("TEST: Compare Two Prompt Versions with Real Traces")
    print("=" * 60)
    print()

    langfuse = get_client()

    # Verify connection
    try:
        auth_ok = langfuse.auth_check()
        print(f"✅ Langfuse auth check: {auth_ok}")
    except Exception as e:
        print(f"❌ Langfuse auth failed: {e}")
        sys.exit(1)

    tickers = ["ADVANC", "BBL", "PTT"]
    trace_ids = []

    print()
    print("📝 Creating traces for Prompt v1...")
    print("-" * 40)
    for ticker in tickers:
        trace_id = simulate_report_with_prompt_version(langfuse, ticker, "v1")
        print(f"  ✅ {ticker}: trace_id={trace_id[:16]}...")
        trace_ids.append(("v1", ticker, trace_id))

    print()
    print("📝 Creating traces for Prompt v2...")
    print("-" * 40)
    for ticker in tickers:
        trace_id = simulate_report_with_prompt_version(langfuse, ticker, "v2")
        print(f"  ✅ {ticker}: trace_id={trace_id[:16]}...")
        trace_ids.append(("v2", ticker, trace_id))

    # Flush all traces
    print()
    print("📤 Flushing traces to Langfuse...")
    langfuse.flush()

    print()
    print("=" * 60)
    print("✅ SUCCESS: 6 traces created (3 per prompt version)")
    print("=" * 60)
    print()
    print("🔗 View traces in Langfuse UI:")
    host = os.environ.get("LANGFUSE_HOST", "https://us.cloud.langfuse.com")
    project_id = "cmjcrupdq01qlad07eopx2bw5"
    print(f"   {host}/project/{project_id}/traces")
    print()
    print("📊 To compare versions, filter by:")
    print("   - tags = 'prompt-v1' for version 1")
    print("   - tags = 'prompt-v2' for version 2")
    print("   - metadata.prompt_version = 'v1' or 'v2'")
    print()
    print("📈 In Langfuse Analytics, group by:")
    print("   - metadata.prompt_version to compare metrics")

    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
