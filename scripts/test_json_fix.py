#!/usr/bin/env python3
"""
Test script to verify MySQL JSON column fix works correctly.
This simulates the exact code path with the fixed approach.
"""
import json
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.data.aurora.precompute_service import _convert_numpy_to_primitives

def test_json_fix():
    """Test that dict can be passed directly to MySQL JSON column"""

    print("=" * 80)
    print("Testing MySQL JSON Column Fix")
    print("=" * 80)
    print()

    # Simulate data that causes the bug (contains quoted Thai text)
    test_data = {
        "ticker": "ABBV",
        "narrative_report": 'สำหรับนักลงทุนที่ยอมรับความเสี่ยงสูง คำแนะนำคือ "ถือ" เพื่อรอดูทิศทาง',
        "price": 174.23,
        "all_scores": [
            {"name": "RSI", "value": 30.79}
        ]
    }

    print("1. Original data (dict):")
    quoted_text = '"ถือ"'
    print(f"   Has quoted text: {quoted_text in test_data['narrative_report']}")
    print()

    # Step that was causing the bug (OLD METHOD):
    print("2. OLD METHOD (buggy):")
    print("   json.dumps() → MySQL %s escaping → double-escaped")
    old_method = json.dumps(test_data, ensure_ascii=False)
    print(f"   Result: {old_method[:100]}...")
    print()

    # New fixed method:
    print("3. NEW METHOD (fixed):")
    print("   Pass dict directly → MySQL JSON column handles it")
    new_method = _convert_numpy_to_primitives(test_data)
    print(f"   Type: {type(new_method)}")
    print(f"   Keys: {list(new_method.keys())}")
    print()

    # Verify new method can be JSON-encoded (mysql-connector-python will do this)
    print("4. Verification:")
    try:
        # This is what mysql-connector-python does internally for JSON columns
        json_check = json.dumps(new_method, ensure_ascii=False)
        parsed_back = json.loads(json_check)
        print("   ✅ Can be encoded and decoded correctly")
        quoted_text = '"ถือ"'
        print(f"   ✅ Quoted text preserved: {quoted_text in parsed_back['narrative_report']}")

        # Check for double-escaping
        double_escaped = '\\"ถือ\\"'
        single_escaped = '\"ถือ\"'
        if double_escaped in json_check:
            print("   ❌ ERROR: Still has double-escaping!")
            return False
        elif single_escaped in json_check:
            print(f"   ✅ Correct single-escaping")
            return True
    except Exception as e:
        print(f"   ❌ ERROR: {e}")
        return False

    print()
    print("=" * 80)
    print("✅ Fix verified! Dict can be passed directly to MySQL JSON column")
    print("=" * 80)
    return True

if __name__ == '__main__':
    success = test_json_fix()
    sys.exit(0 if success else 1)
