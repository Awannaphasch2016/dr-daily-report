#!/usr/bin/env python3
"""
Quick test runner for LINE Bot Lambda Function
Runs all local tests in sequence
"""

import os
import sys
import subprocess

def run_test(name, script, description):
    """Run a test script and report results"""
    print("\n" + "=" * 80)
    print(f"🧪 {name}")
    print("=" * 80)
    print(f"Description: {description}")
    print("-" * 80)
    
    try:
        result = subprocess.run(
            [sys.executable, script],
            cwd=os.path.dirname(__file__),
            capture_output=False,
            text=True
        )
        
        if result.returncode == 0:
            print(f"\n✅ {name} PASSED")
            return True
        else:
            print(f"\n❌ {name} FAILED (exit code: {result.returncode})")
            return False
            
    except Exception as e:
        print(f"\n❌ {name} ERROR: {str(e)}")
        return False

def main():
    """Run all tests"""
    print("=" * 80)
    print("🚀 LINE Bot Lambda Function - Test Suite")
    print("=" * 80)
    print()
    
    # Check environment variables first
    print("📋 Checking Environment Variables...")
    required_vars = [
        'OPENAI_API_KEY',
        'LINE_CHANNEL_ACCESS_TOKEN',
        'LINE_CHANNEL_SECRET'
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
            print(f"  ❌ {var}: NOT SET")
        else:
            print(f"  ✅ {var}: Set")
    
    if missing_vars:
        print("\n⚠️  Warning: Missing environment variables!")
        print("   Set them before running tests:")
        for var in missing_vars:
            print(f"   export {var}=your_value")
        print("\n   Continuing with tests anyway (some may fail)...")
        print()
    
    # Run tests
    tests = [
        (
            "Lambda Handler Test",
            "test_lambda_handler.py",
            "Tests the Lambda handler function directly with mock event"
        ),
        (
            "Function URL Event Test",
            "test_lambda_function_url.py",
            "Tests Lambda handler with Function URL event format"
        ),
        (
            "LINE Integration Test",
            "tests/test_line_integration.py",
            "Tests LINE bot integration with mocked replies"
        ),
    ]
    
    results = []
    for name, script, description in tests:
        if os.path.exists(script):
            success = run_test(name, script, description)
            results.append((name, success))
        else:
            print(f"\n⚠️  Skipping {name}: {script} not found")
            results.append((name, None))
    
    # Summary
    print("\n" + "=" * 80)
    print("📊 Test Summary")
    print("=" * 80)
    
    passed = sum(1 for _, result in results if result is True)
    failed = sum(1 for _, result in results if result is False)
    skipped = sum(1 for _, result in results if result is None)
    
    for name, result in results:
        if result is True:
            print(f"  ✅ {name}")
        elif result is False:
            print(f"  ❌ {name}")
        else:
            print(f"  ⏭️  {name} (skipped)")
    
    print()
    print(f"Total: {len(results)} tests")
    print(f"  ✅ Passed: {passed}")
    print(f"  ❌ Failed: {failed}")
    print(f"  ⏭️  Skipped: {skipped}")
    print()
    
    if failed > 0:
        print("❌ Some tests failed. Check the output above for details.")
        sys.exit(1)
    elif skipped > 0:
        print("⚠️  Some tests were skipped.")
        sys.exit(0)
    else:
        print("✅ All tests passed!")
        sys.exit(0)

if __name__ == "__main__":
    main()
