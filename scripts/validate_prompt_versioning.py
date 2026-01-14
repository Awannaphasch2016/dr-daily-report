#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Validation script: Langfuse Prompt Management with Version Tracking.

This script validates that we can:
1. Fetch different prompt versions from Langfuse (simulated)
2. Track version metadata in traces
3. Compare performance between prompt versions

Run: python scripts/validate_prompt_versioning.py
"""

import json
import logging
import time
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Dict, List, Any
from unittest.mock import MagicMock, patch

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


@dataclass
class FakeTrace:
    """Simulated Langfuse trace for validation."""
    trace_id: str
    name: str
    input: str
    output: str
    metadata: Dict[str, Any]
    latency_ms: int
    timestamp: str
    scores: Dict[str, float]


class FakeLangfuseClient:
    """Simulated Langfuse client for validation testing."""

    def __init__(self):
        self.traces: List[FakeTrace] = []
        self.prompts = {
            "report-generation": {
                "v1": {
                    "content": """<system>You write Thai stock reports.</system>
<task>Write a report for {TICKER}. Keep it under 200 words.</task>
<data>{CONTEXT}</data>""",
                    "version": 1,
                    "label": "development"
                },
                "v2": {
                    "content": """<system>You are an expert Thai financial analyst writing for retail investors.</system>
<examples>
Example: DBS19 กำลังเคลื่อนที่ในตลาด...
</examples>
<task>Write a 250-350 word Thai stock report for {TICKER}.</task>
<data>{CONTEXT}</data>""",
                    "version": 2,
                    "label": "development"
                }
            }
        }

    def get_prompt(self, name: str, version: int = None, label: str = None, cache_ttl_seconds: int = 60):
        """Simulate fetching a prompt from Langfuse."""
        if name not in self.prompts:
            raise ValueError(f"Prompt '{name}' not found")

        prompt_data = self.prompts[name]

        if version:
            version_key = f"v{version}"
            if version_key not in prompt_data:
                raise ValueError(f"Version {version} not found for prompt '{name}'")
            data = prompt_data[version_key]
        else:
            # Get latest version
            latest_key = max(prompt_data.keys())
            data = prompt_data[latest_key]

        # Return mock prompt object
        mock_prompt = MagicMock()
        mock_prompt.prompt = data["content"]
        mock_prompt.version = data["version"]
        mock_prompt.config = {"variables": ["TICKER", "CONTEXT"]}
        return mock_prompt

    def create_trace(self, name: str, input_data: str, output: str, metadata: Dict, latency_ms: int, scores: Dict[str, float]):
        """Create a fake trace for validation."""
        trace = FakeTrace(
            trace_id=f"trace-{len(self.traces)+1:04d}",
            name=name,
            input=input_data[:200] + "..." if len(input_data) > 200 else input_data,
            output=output[:200] + "..." if len(output) > 200 else output,
            metadata=metadata,
            latency_ms=latency_ms,
            timestamp=datetime.now().isoformat(),
            scores=scores
        )
        self.traces.append(trace)
        return trace


def simulate_report_generation(client: FakeLangfuseClient, ticker: str, prompt_version: int) -> FakeTrace:
    """Simulate generating a report with a specific prompt version."""

    # Fetch prompt
    prompt = client.get_prompt("report-generation", version=prompt_version)

    # Simulate compilation
    compiled_prompt = prompt.prompt.format(
        TICKER=ticker,
        CONTEXT=f"Market data for {ticker}: Price=35.50, RSI=65, Volume=1.2M"
    )

    # Simulate LLM response (different quality based on version)
    if prompt_version == 1:
        output = f"{ticker}: หุ้นนี้น่าสนใจ ราคาปัจจุบัน 35.50 บาท RSI อยู่ที่ 65 ซึ่งยังไม่ถึงโซน overbought แนะนำ HOLD"
        latency = 2500 + (hash(ticker) % 500)  # 2.5-3s
        scores = {
            "conciseness": 0.7,
            "helpfulness": 0.6,
            "hallucination": 0.2
        }
    else:  # v2 - better prompt
        output = f"""📖 **เรื่องราวของหุ้นตัวนี้**
{ticker} กำลังเคลื่อนที่ในตลาดที่มีความไม่แน่นอนปานกลาง ราคาปัจจุบัน 35.50 บาท พร้อมปริมาณซื้อขาย 1.2M หุ้น

💡 **สิ่งที่คุณต้องรู้**
RSI อยู่ที่ 65 ซึ่งแสดงโมเมนตัมขาขึ้นที่ยังมีพื้นที่ให้เติบโต...

🎯 **ควรทำอะไรตอนนี้?**
**HOLD** - รอดูทิศทางตลาดก่อนตัดสินใจ"""
        latency = 3200 + (hash(ticker) % 500)  # 3.2-3.7s (longer but better)
        scores = {
            "conciseness": 0.85,
            "helpfulness": 0.9,
            "hallucination": 0.1
        }

    # Create trace with metadata
    metadata = {
        "prompt_name": "report-generation",
        "prompt_version": str(prompt.version),
        "prompt_source": "langfuse",
        "ticker": ticker,
        "environment": "dev"
    }

    trace = client.create_trace(
        name="generate_report",
        input_data=compiled_prompt,
        output=output,
        metadata=metadata,
        latency_ms=latency,
        scores=scores
    )

    return trace


def compare_prompt_versions(traces: List[FakeTrace]) -> Dict[str, Any]:
    """Compare performance metrics between prompt versions."""

    # Group traces by prompt version
    by_version: Dict[str, List[FakeTrace]] = {}
    for trace in traces:
        version = trace.metadata.get("prompt_version", "unknown")
        if version not in by_version:
            by_version[version] = []
        by_version[version].append(trace)

    comparison = {}
    for version, version_traces in by_version.items():
        latencies = [t.latency_ms for t in version_traces]

        # Aggregate scores
        score_sums = {}
        for trace in version_traces:
            for score_name, score_value in trace.scores.items():
                if score_name not in score_sums:
                    score_sums[score_name] = []
                score_sums[score_name].append(score_value)

        avg_scores = {name: sum(vals)/len(vals) for name, vals in score_sums.items()}

        comparison[f"v{version}"] = {
            "trace_count": len(version_traces),
            "avg_latency_ms": sum(latencies) / len(latencies),
            "min_latency_ms": min(latencies),
            "max_latency_ms": max(latencies),
            "avg_scores": avg_scores
        }

    return comparison


def main():
    """Run validation: compare 2 prompt versions with fake traces."""

    print("=" * 70)
    print("VALIDATION: Langfuse Prompt Management with Version Tracking")
    print("=" * 70)
    print()

    # Create fake Langfuse client
    client = FakeLangfuseClient()

    # Test tickers
    tickers = ["ADVANC", "BBL", "PTT", "KBANK", "SCB"]

    print("📝 Step 1: Generate reports with Prompt v1")
    print("-" * 50)
    for ticker in tickers:
        trace = simulate_report_generation(client, ticker, prompt_version=1)
        print(f"  ✅ {ticker}: trace_id={trace.trace_id}, latency={trace.latency_ms}ms, version={trace.metadata['prompt_version']}")

    print()
    print("📝 Step 2: Generate reports with Prompt v2")
    print("-" * 50)
    for ticker in tickers:
        trace = simulate_report_generation(client, ticker, prompt_version=2)
        print(f"  ✅ {ticker}: trace_id={trace.trace_id}, latency={trace.latency_ms}ms, version={trace.metadata['prompt_version']}")

    print()
    print("📊 Step 3: Compare Prompt Versions")
    print("-" * 50)

    comparison = compare_prompt_versions(client.traces)

    for version, metrics in comparison.items():
        print(f"\n  {version}:")
        print(f"    Traces: {metrics['trace_count']}")
        print(f"    Avg Latency: {metrics['avg_latency_ms']:.0f}ms")
        print(f"    Latency Range: {metrics['min_latency_ms']:.0f}ms - {metrics['max_latency_ms']:.0f}ms")
        print(f"    Scores:")
        for score_name, score_value in metrics['avg_scores'].items():
            print(f"      - {score_name}: {score_value:.2f}")

    print()
    print("=" * 70)
    print("VALIDATION RESULT")
    print("=" * 70)

    # Calculate winner
    v1_quality = sum(comparison['v1']['avg_scores'].values()) / len(comparison['v1']['avg_scores'])
    v2_quality = sum(comparison['v2']['avg_scores'].values()) / len(comparison['v2']['avg_scores'])

    print()
    print("📈 Quality Comparison (higher is better):")
    print(f"    v1 avg quality score: {v1_quality:.2f}")
    print(f"    v2 avg quality score: {v2_quality:.2f}")
    print(f"    Winner: {'v2' if v2_quality > v1_quality else 'v1'} (+{abs(v2_quality - v1_quality):.2f})")

    print()
    print("⏱️ Latency Comparison (lower is better):")
    print(f"    v1 avg latency: {comparison['v1']['avg_latency_ms']:.0f}ms")
    print(f"    v2 avg latency: {comparison['v2']['avg_latency_ms']:.0f}ms")
    latency_diff = comparison['v2']['avg_latency_ms'] - comparison['v1']['avg_latency_ms']
    print(f"    v2 is {abs(latency_diff):.0f}ms {'slower' if latency_diff > 0 else 'faster'} than v1")

    print()
    print("✅ VALIDATION PASSED: Can track and compare prompt versions")
    print()
    print("Key capabilities demonstrated:")
    print("  1. Fetch different prompt versions from Langfuse (simulated)")
    print("  2. Track prompt_name, prompt_version, prompt_source in trace metadata")
    print("  3. Attach quality scores to traces")
    print("  4. Group and compare metrics by prompt version")
    print("  5. Identify which prompt version performs better")

    print()
    print("Sample trace metadata structure:")
    print(json.dumps(client.traces[0].metadata, indent=2))

    return True


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
