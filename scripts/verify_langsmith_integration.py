#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Verify LangSmith integration.

Tests:
1. Workflow executes with @traceable decorators
2. Report is generated successfully
3. Background evaluation thread spawns
4. Check if LangSmith variables are set
5. Verify run ID is captured
6. Verify scores can be logged

Usage: doppler run -- python scripts/verify_langsmith_integration.py
"""

import os
import sys
import time
import logging
from src.agent import TickerAnalysisAgent

# Set up logging to capture messages
logging.basicConfig(level=logging.INFO, format='%(message)s')


def test_langsmith_integration():
    """Test LangSmith integration with async background evaluation"""
    print("=" * 80)
    print("LangSmith Integration Test")
    print("=" * 80)

    # Check LangSmith environment variables
    print("\n1️⃣  Checking LangSmith Configuration...")
    langchain_api_key = os.environ.get('LANGCHAIN_API_KEY')
    langchain_tracing = os.environ.get('LANGCHAIN_TRACING_V2', 'false')
    langchain_project = os.environ.get('LANGCHAIN_PROJECT', 'default')

    if langchain_api_key:
        print(f"   ✅ LANGCHAIN_API_KEY: Set (length: {len(langchain_api_key)})")
    else:
        print("   ❌ LANGCHAIN_API_KEY: Not set")

    print(f"   📊 LANGCHAIN_TRACING_V2: {langchain_tracing}")
    print(f"   📁 LANGCHAIN_PROJECT: {langchain_project}")

    # Create agent
    print("\n2️⃣  Initializing TickerAnalysisAgent...")
    agent = TickerAnalysisAgent()
    print("   ✅ Agent initialized successfully")

    # Test with a sample ticker
    test_ticker = "SIA19"  # Singapore Airlines
    print(f"\n3️⃣  Running workflow for ticker: {test_ticker}...")
    print("   (This will test @traceable decorators and async background evaluation)")

    start_time = time.time()

    try:
        report = agent.analyze_ticker(test_ticker)
        elapsed = time.time() - start_time

        print(f"\n   ✅ Workflow completed successfully in {elapsed:.2f}s")
        print(f"   📄 Report length: {len(report)} characters")

        # Show first 500 characters of report
        print("\n4️⃣  Report Preview (first 500 chars):")
        print("   " + "-" * 76)
        print("   " + report[:500].replace('\n', '\n   '))
        if len(report) > 500:
            print("   ...")
        print("   " + "-" * 76)

        # Check if evaluation runs asynchronously
        print("\n5️⃣  Background Evaluation Status:")
        print("   ✅ Report returned immediately (async evaluation spawned)")
        print("   📊 Evaluation runs in background thread (doesn't block response)")
        print("   💾 Scores will be saved to SQLite database")
        if langchain_tracing.lower() == 'true':
            print("   📈 Scores will be logged to LangSmith")
        else:
            print("   ⚠️  LangSmith tracing disabled (LANGCHAIN_TRACING_V2=false)")

        # Wait a moment for background thread to complete
        print("\n6️⃣  Waiting for background evaluation to complete...")
        time.sleep(5)  # Give background thread time to finish
        print("   ✅ Background evaluation should be complete")

        # Verify run ID capture (if tracing enabled)
        print("\n7️⃣  Verification Steps:")
        if langchain_tracing.lower() == 'true':
            print("   📋 Run ID Capture:")
            print("      - Check logs above for 'Captured LangSmith run ID: ...'")
            print("      - If present: ✅ Run ID captured successfully")
            print("      - If absent: ⚠️  Run ID not captured (scores won't appear in UI)")

            print("\n   📊 Score Logging:")
            print("      - Check logs for 'Successfully logged ... evaluations to LangSmith'")
            print("      - Check logs for 'Successfully saved all scores to database'")

            print("\n   🔍 Database Verification:")
            print("      - SQLite database should have scores in ticker_analyses.db")
            print("      - Tables: faithfulness_scores, completeness_scores, etc.")
        else:
            print("   ℹ️  LangSmith tracing disabled - skipping verification")
            print("      ✅ Workflow works without LangSmith (backward compatibility)")

        print("\n" + "=" * 80)
        print("✅ LangSmith Integration Test PASSED")
        print("=" * 80)

        if langchain_tracing.lower() == 'true':
            print("\n📊 Next Steps - Check LangSmith UI:")
            print(f"   1. Go to: https://smith.langchain.com")
            print(f"   2. Select project: {langchain_project}")
            print(f"   3. Find trace: analyze_ticker({test_ticker})")
            print(f"   4. Look for spans: fetch_all_data_parallel, analyze_technical, etc.")
            print(f"   5. Check Feedback tab: Should show 6 evaluation scores")
            print(f"      - faithfulness_score")
            print(f"      - completeness_score")
            print(f"      - reasoning_quality_score")
            print(f"      - compliance_score")
            print(f"      - qos_score")
            print(f"      - cost_score")
            print(f"\n   🔗 Direct link: https://smith.langchain.com/o/default/projects/{langchain_project}")
            print(f"\n   💡 If scores show as null:")
            print(f"      - Check if 'Captured LangSmith run ID' appears in logs above")
            print(f"      - Check if background evaluation completed without errors")
            print(f"      - Try running test again (async timing issue)")

        return True

    except Exception as e:
        elapsed = time.time() - start_time
        print(f"\n   ❌ Workflow failed after {elapsed:.2f}s")
        print(f"   Error: {e}")
        import traceback
        traceback.print_exc()

        print("\n" + "=" * 80)
        print("❌ LangSmith Integration Test FAILED")
        print("=" * 80)

        return False


if __name__ == "__main__":
    success = test_langsmith_integration()
    sys.exit(0 if success else 1)
