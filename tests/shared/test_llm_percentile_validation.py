# -*- coding: utf-8 -*-
"""
Tests for LLM response percentile validation

Validates that LLM responses include proper percentile analysis
in the narrative for transparent reporting.
"""

import re
import pytest


class TestPercentileValidation:
    """Tests for percentile validation in LLM responses"""

    def _validate_llm_response_contains_percentiles(self, report_text: str) -> dict:
        """Validate that LLM response includes percentile information"""
        report_lower = report_text.lower()

        # Check for percentile-related keywords
        percentile_keywords = [
            'เปอร์เซ็นไทล์',
            'percentile',
            '%'
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
        percentile_pattern = r'เปอร์เซ็นไทล์\s*\d+[.,]?\d*\s*%'
        has_percentile_pattern = bool(re.search(percentile_pattern, report_text))

        return {
            'has_percentile_keywords': has_percentile_keywords,
            'has_context_patterns': has_context_patterns,
            'has_percentile_pattern': has_percentile_pattern,
            'passed': has_percentile_keywords and (has_context_patterns or has_percentile_pattern)
        }

    def test_good_report_passes_validation(self):
        """Test that report with proper percentile context passes validation"""
        good_report = """
        📖 **เรื่องราวของหุ้นตัวนี้**
        Apple กำลังอยู่ในโมเมนต์ที่น่าสนใจ - ตลาดเสถียร (ความไม่แน่นอน 22/100 อยู่ในเปอร์เซ็นไทล์ 15% - ต่ำมากในอดีต)
        ATR แค่ 1.2% (เปอร์เซ็นไทล์ 25%) ราคาเคลื่อนไหวช้ามั่นคง นักลงทุนเห็นตรงกัน
        แต่ราคา 2.4% เหนือ VWAP (เปอร์เซ็นไทล์ 60%) แสดงแรงซื้อชนะ
        ปริมาณซื้อขาย 1.3x ของเฉลี่ย (เปอร์เซ็นไทล์ 65%) แสดงนักลงทุนสนใจเพิ่มขึ้น

        💡 **สิ่งที่คุณต้องรู้**
        RSI 81.12 ซึ่งอยู่ในเปอร์เซ็นไทล์ 94% - สูงมากในอดีต ควรระวังภาวะ Overbought
        """

        result = self._validate_llm_response_contains_percentiles(good_report)

        assert result['has_percentile_keywords'], "Should have percentile keywords"
        assert result['has_context_patterns'], "Should have context patterns"
        assert result['has_percentile_pattern'], "Should have percentile pattern"
        assert result['passed'], "Good report should pass validation"

    def test_bad_report_fails_validation(self):
        """Test that report without percentile context fails validation"""
        bad_report = """
        📖 **เรื่องราวของหุ้นตัวนี้**
        Apple กำลังอยู่ในโมเมนต์ที่น่าสนใจ - ตลาดเสถียร (ความไม่แน่นอน 22/100)
        ATR แค่ 1.2% ราคาเคลื่อนไหวช้า แต่ราคา 2.4% เหนือ VWAP แสดงแรงซื้อชนะ
        ปริมาณซื้อขาย 1.3x ของเฉลี่ยแสดงนักลงทุนสนใจเพิ่มขึ้น

        💡 **สิ่งที่คุณต้องรู้**
        RSI 81.12 แสดงภาวะ Overbought
        """

        result = self._validate_llm_response_contains_percentiles(bad_report)

        assert not result['passed'], "Bad report should fail validation"

    def test_report_with_only_percent_symbol(self):
        """Test that report with just % symbols without context is insufficient"""
        minimal_report = """
        ราคาหุ้นขึ้น 5% วันนี้
        เป้าหมายราคา 10% จากปัจจุบัน
        """

        result = self._validate_llm_response_contains_percentiles(minimal_report)

        # Has % but no percentile context
        assert result['has_percentile_keywords'], "Should detect % symbol"
        assert not result['has_percentile_pattern'], "Should not have Thai percentile pattern"

    def test_report_with_percentile_keyword_only(self):
        """Test report with percentile keyword but no numeric context"""
        keyword_only = """
        เราใช้เปอร์เซ็นไทล์ในการวิเคราะห์
        ดูข้อมูลในอดีตประกอบ
        """

        result = self._validate_llm_response_contains_percentiles(keyword_only)

        assert result['has_percentile_keywords'], "Should have percentile keyword"
        assert result['has_context_patterns'], "Should have context patterns"
        # May pass due to context patterns even without numeric pattern


class TestPercentilePatternDetection:
    """Tests for specific percentile pattern detection"""

    def test_thai_percentile_pattern(self):
        """Test Thai percentile pattern detection"""
        pattern = r'เปอร์เซ็นไทล์\s*\d+[.,]?\d*\s*%'

        # Should match
        valid_texts = [
            "เปอร์เซ็นไทล์ 85%",
            "เปอร์เซ็นไทล์85%",
            "เปอร์เซ็นไทล์ 94.5%",
            "เปอร์เซ็นไทล์ 15 %",
        ]

        for text in valid_texts:
            assert re.search(pattern, text), f"Should match: {text}"

    def test_non_thai_percentile_not_matched(self):
        """Test that English percentile doesn't match Thai pattern"""
        pattern = r'เปอร์เซ็นไทล์\s*\d+[.,]?\d*\s*%'

        # Should not match
        invalid_texts = [
            "percentile 85%",
            "85th percentile",
            "RSI is 85%",
        ]

        for text in invalid_texts:
            assert not re.search(pattern, text), f"Should not match Thai pattern: {text}"
