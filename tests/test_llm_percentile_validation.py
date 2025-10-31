#!/usr/bin/env python3
"""
Test script to validate LLM responses include percentile analysis in narrative
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

def validate_llm_response_contains_percentiles(report_text):
    """Validate that LLM response includes percentile information"""
    report_lower = report_text.lower()
    
    # Check for percentile-related keywords
    percentile_keywords = [
        'เปอร์เซ็นไทล์',
        'percentile',
        '%'  # Percentile values usually have %
    ]
    
    has_percentile_keywords = any(keyword in report_lower for keyword in percentile_keywords)
    
    # Check for percentile context patterns
    patterns = [
        'อยู่ในเปอร์เซ็นไทล์',
        'เปอร์เซ็นไทล์',
        'ในอดีต',
        'เทียบกับประวัติศาสตร์',
        'ค่าที่',
        'ผิดปกติ',
        'สูงกว่า',
        'ต่ำกว่า'
    ]
    
    has_context_patterns = any(pattern in report_text for pattern in patterns)
    
    # Check for numbers with percentile context (e.g., "RSI 75 ซึ่งอยู่ในเปอร์เซ็นไทล์ 85%")
    import re
    # Look for patterns like "ตัวเลข (เปอร์เซ็นไทล์ XX%)" or "ตัวเลข อยู่ในเปอร์เซ็นไทล์"
    percentile_pattern = r'เปอร์เซ็นไทล์\s*\d+[.,]?\d*\s*%'
    has_percentile_pattern = bool(re.search(percentile_pattern, report_text))
    
    return {
        'has_percentile_keywords': has_percentile_keywords,
        'has_context_patterns': has_context_patterns,
        'has_percentile_pattern': has_percentile_pattern,
        'passed': has_percentile_keywords and (has_context_patterns or has_percentile_pattern)
    }

def test_validate_sample_report():
    """Test validation with sample reports"""
    print("\n🔍 Test: Validate LLM Response Contains Percentiles")
    
    # Good example - includes percentile context
    good_report = """
    📖 **เรื่องราวของหุ้นตัวนี้**
    Apple กำลังอยู่ในโมเมนต์ที่น่าสนใจ - ตลาดเสถียร (ความไม่แน่นอน 22/100 อยู่ในเปอร์เซ็นไทล์ 15% - ต่ำมากในอดีต) 
    ATR แค่ 1.2% (เปอร์เซ็นไทล์ 25%) ราคาเคลื่อนไหวช้ามั่นคง นักลงทุนเห็นตรงกัน 
    แต่ราคา 2.4% เหนือ VWAP (เปอร์เซ็นไทล์ 60%) แสดงแรงซื้อชนะ 
    ปริมาณซื้อขาย 1.3x ของเฉลี่ย (เปอร์เซ็นไทล์ 65%) แสดงนักลงทุนสนใจเพิ่มขึ้น
    
    💡 **สิ่งที่คุณต้องรู้**
    RSI 81.12 ซึ่งอยู่ในเปอร์เซ็นไทล์ 94% - สูงมากในอดีต ควรระวังภาวะ Overbought
    """
    
    # Bad example - no percentile context
    bad_report = """
    📖 **เรื่องราวของหุ้นตัวนี้**
    Apple กำลังอยู่ในโมเมนต์ที่น่าสนใจ - ตลาดเสถียร (ความไม่แน่นอน 22/100) 
    ATR แค่ 1.2% ราคาเคลื่อนไหวช้า แต่ราคา 2.4% เหนือ VWAP แสดงแรงซื้อชนะ 
    ปริมาณซื้อขาย 1.3x ของเฉลี่ยแสดงนักลงทุนสนใจเพิ่มขึ้น
    
    💡 **สิ่งที่คุณต้องรู้**
    RSI 81.12 แสดงภาวะ Overbought
    """
    
    good_result = validate_llm_response_contains_percentiles(good_report)
    bad_result = validate_llm_response_contains_percentiles(bad_report)
    
    print(f"Good report validation:")
    print(f"  Has percentile keywords: {good_result['has_percentile_keywords']}")
    print(f"  Has context patterns: {good_result['has_context_patterns']}")
    print(f"  Has percentile pattern: {good_result['has_percentile_pattern']}")
    print(f"  Passed: {good_result['passed']}")
    
    print(f"\nBad report validation:")
    print(f"  Has percentile keywords: {bad_result['has_percentile_keywords']}")
    print(f"  Has context patterns: {bad_result['has_context_patterns']}")
    print(f"  Has percentile pattern: {bad_result['has_percentile_pattern']}")
    print(f"  Passed: {bad_result['passed']}")
    
    assert good_result['passed'], "Good report should pass validation"
    assert not bad_result['passed'], "Bad report should fail validation"
    
    print("✅ Test passed: Validation correctly identifies percentile usage")

def run_validation_tests():
    """Run all validation tests"""
    print("=" * 80)
    print("LLM RESPONSE VALIDATION TEST SUITE")
    print("=" * 80)
    
    tests = [
        ("Validate Sample Report", test_validate_sample_report),
    ]
    
    results = []
    
    for name, test_func in tests:
        try:
            test_func()
            results.append(True)
        except Exception as e:
            print(f"❌ {name} test failed: {str(e)}")
            import traceback
            traceback.print_exc()
            results.append(False)
    
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    passed = sum(results)
    total = len(results)
    print(f"Passed: {passed}/{total}")
    
    if passed == total:
        print("🎉 All validation tests passed!")
    else:
        print("⚠️  Some tests failed. Please review the errors above.")
    
    return passed == total

if __name__ == "__main__":
    success = run_validation_tests()
    sys.exit(0 if success else 1)
