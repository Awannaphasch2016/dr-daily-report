"""
Compliance Scorer for Narrative Reports

Measures whether the report follows required format, structure, and policy constraints.
Answers: "Does it follow required format/policy?"
"""

import re
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass


@dataclass
class ComplianceScore:
    """Container for compliance scoring results"""
    overall_score: float  # 0-100
    dimension_scores: Dict[str, float]  # Individual dimension scores
    violations: List[str]  # List of compliance violations
    compliant_elements: List[str]  # List of compliant elements


class ComplianceScorer:
    """
    Score report compliance with format, structure, and policy requirements
    
    Checks:
    1. Structure Compliance - All 4 required sections present with correct format
    2. Content Compliance - All required content elements present
    3. Format Compliance - No prohibited elements (tables, lists, etc.)
    4. Length Compliance - Meets length requirements
    5. Language Compliance - Written in Thai, proper style
    6. Citation Compliance - News citations follow format [1], [2]
    """
    
    def __init__(self):
        """Initialize compliance scorer"""
        pass
    
    def score_narrative(
        self,
        narrative: str,
        indicators: Dict,
        news_data: List[Dict]
    ) -> ComplianceScore:
        """
        Score narrative compliance with format/policy requirements
        
        Args:
            narrative: Generated Thai narrative text
            indicators: Technical indicators
            news_data: List of news items
        
        Returns:
            ComplianceScore object with detailed scoring
        """
        violations = []
        compliant_elements = []
        
        # 1. Structure Compliance (30%)
        structure_score, structure_violations, structure_compliant = self._check_structure_compliance(
            narrative
        )
        violations.extend(structure_violations)
        compliant_elements.extend(structure_compliant)
        
        # 2. Content Compliance (25%)
        content_score, content_violations, content_compliant = self._check_content_compliance(
            narrative, indicators
        )
        violations.extend(content_violations)
        compliant_elements.extend(content_compliant)
        
        # 3. Format Compliance (15%)
        format_score, format_violations, format_compliant = self._check_format_compliance(
            narrative
        )
        violations.extend(format_violations)
        compliant_elements.extend(format_compliant)
        
        # 4. Length Compliance (10%)
        length_score, length_violations, length_compliant = self._check_length_compliance(
            narrative
        )
        violations.extend(length_violations)
        compliant_elements.extend(length_compliant)
        
        # 5. Language Compliance (10%)
        language_score, language_violations, language_compliant = self._check_language_compliance(
            narrative
        )
        violations.extend(language_violations)
        compliant_elements.extend(language_compliant)
        
        # 6. Citation Compliance (10%)
        citation_score, citation_violations, citation_compliant = self._check_citation_compliance(
            narrative, news_data
        )
        violations.extend(citation_violations)
        compliant_elements.extend(citation_compliant)
        
        # Calculate overall score (weighted average)
        overall_score = (
            structure_score * 0.30 +
            content_score * 0.25 +
            format_score * 0.15 +
            length_score * 0.10 +
            language_score * 0.10 +
            citation_score * 0.10
        )
        
        dimension_scores = {
            'structure_compliance': structure_score,
            'content_compliance': content_score,
            'format_compliance': format_score,
            'length_compliance': length_score,
            'language_compliance': language_score,
            'citation_compliance': citation_score
        }
        
        return ComplianceScore(
            overall_score=overall_score,
            dimension_scores=dimension_scores,
            violations=violations,
            compliant_elements=compliant_elements
        )
    
    def _check_structure_compliance(self, narrative: str) -> Tuple[float, List[str], List[str]]:
        """Check if report has all 4 required sections with correct format"""
        violations = []
        compliant_elements = []
        
        # Required sections with emojis
        required_sections = {
            '📖': {
                'name': 'Story Section',
                'keywords': ['เรื่องราว', 'story'],
                'required': True
            },
            '💡': {
                'name': 'Insights Section',
                'keywords': ['สิ่งที่คุณต้องรู้', 'insight', 'สิ่งที่'],
                'required': True
            },
            '🎯': {
                'name': 'Recommendation Section',
                'keywords': ['ควรทำอะไร', 'recommendation', 'ควรทำ'],
                'required': True
            },
            '⚠️': {
                'name': 'Risk Section',
                'keywords': ['ระวัง', 'warning', 'risk', 'ระวังอะไร'],
                'required': True
            }
        }
        
        # Check each section
        found_sections = {}
        for emoji, section_info in required_sections.items():
            # Check for emoji or keywords
            has_emoji = emoji in narrative
            has_keywords = any(keyword in narrative for keyword in section_info['keywords'])
            
            if has_emoji or has_keywords:
                found_sections[emoji] = True
                compliant_elements.append(f"✅ {section_info['name']} ({emoji}) present")
            else:
                found_sections[emoji] = False
                violations.append(f"❌ Missing required section: {section_info['name']} ({emoji})")
        
        # Check section order (should be: 📖, 💡, 🎯, ⚠️)
        section_order = []
        for emoji in ['📖', '💡', '🎯', '⚠️']:
            if emoji in narrative:
                section_order.append(emoji)
        
        # Check if order is correct
        if len(section_order) == 4:
            expected_order = ['📖', '💡', '🎯', '⚠️']
            if section_order == expected_order:
                compliant_elements.append("✅ Sections in correct order")
            else:
                violations.append(f"⚠️ Sections out of order: {section_order} (expected: {expected_order})")
        
        # Check section content requirements
        # 📖 section should be 2-3 sentences
        story_section = self._extract_section(narrative, '📖')
        if story_section:
            sentences = len(re.split(r'[.!?。]', story_section))
            if 2 <= sentences <= 3:
                compliant_elements.append("✅ Story section (📖) has correct length (2-3 sentences)")
            else:
                violations.append(f"❌ Story section (📖) should be 2-3 sentences, found {sentences}")
        
        # 💡 section should be paragraphs (not lists)
        insights_section = self._extract_section(narrative, '💡')
        if insights_section:
            # Check for prohibited elements in insights section
            if re.search(r'\d+\.\s+', insights_section):  # Numbered list
                violations.append("❌ Insights section (💡) contains numbered lists (prohibited)")
            elif '|' in insights_section or '---' in insights_section:  # Table-like
                violations.append("❌ Insights section (💡) contains table-like format (prohibited)")
            else:
                compliant_elements.append("✅ Insights section (💡) uses flowing paragraphs (no lists/tables)")
        
        # 🎯 section should have ONE clear recommendation
        recommendation_section = self._extract_section(narrative, '🎯')
        if recommendation_section:
            recommendations = []
            if 'BUY' in recommendation_section.upper() or 'ซื้อ' in recommendation_section:
                recommendations.append('BUY')
            if 'SELL' in recommendation_section.upper() or 'ขาย' in recommendation_section:
                recommendations.append('SELL')
            if 'HOLD' in recommendation_section.upper() or 'ถือ' in recommendation_section:
                recommendations.append('HOLD')
            
            if len(recommendations) == 1:
                compliant_elements.append(f"✅ Recommendation section (🎯) has ONE clear action: {recommendations[0]}")
            elif len(recommendations) > 1:
                violations.append(f"❌ Recommendation section (🎯) has multiple recommendations: {recommendations}")
            else:
                violations.append("❌ Recommendation section (🎯) missing clear BUY/SELL/HOLD")
        
        # ⚠️ section should warn about risks
        risk_section = self._extract_section(narrative, '⚠️')
        if risk_section:
            if any(keyword in risk_section.lower() for keyword in ['risk', 'risky', 'warning', 'caution', 'ความเสี่ยง', 'ระวัง']):
                compliant_elements.append("✅ Risk section (⚠️) includes risk warnings")
            else:
                violations.append("⚠️ Risk section (⚠️) may not include clear risk warnings")
        
        # Calculate score
        total_sections = len(required_sections)
        found_count = sum(1 for found in found_sections.values() if found)
        score = (found_count / total_sections * 100) if total_sections > 0 else 0
        
        # Penalize order issues
        if violations and any('order' in v for v in violations):
            score -= 5
        
        # Penalize content requirement violations
        content_violations = [v for v in violations if 'sentences' in v or 'numbered lists' in v or 'table' in v or 'multiple recommendations' in v]
        score -= len(content_violations) * 5
        
        return max(0, min(100, score)), violations, compliant_elements
    
    def _extract_section(self, narrative: str, emoji: str) -> Optional[str]:
        """Extract section content between emoji and next section"""
        # Find emoji position
        emoji_pos = narrative.find(emoji)
        if emoji_pos == -1:
            return None
        
        # Find next section emoji
        next_emojis = ['📖', '💡', '🎯', '⚠️']
        next_emojis.remove(emoji)
        
        section_end = len(narrative)
        for next_emoji in next_emojis:
            next_pos = narrative.find(next_emoji, emoji_pos + 1)
            if next_pos != -1:
                section_end = min(section_end, next_pos)
        
        return narrative[emoji_pos:section_end]
    
    def _check_content_compliance(self, narrative: str, indicators: Dict) -> Tuple[float, List[str], List[str]]:
        """Check if all required content elements are present"""
        violations = []
        compliant_elements = []
        
        narrative_lower = narrative.lower()
        
        # Check for 4 market condition metrics
        required_metrics = {
            'uncertainty': {
                'keywords': ['uncertainty', 'ความไม่แน่นอน', 'uncertainty score'],
                'required': True
            },
            'atr': {
                'keywords': ['atr', 'atr%', 'ความผันผวน'],
                'required': True
            },
            'vwap': {
                'keywords': ['vwap', 'price vs vwap', 'แรงซื้อ', 'แรงขาย'],
                'required': True
            },
            'volume': {
                'keywords': ['volume', 'volume ratio', 'ปริมาณ', 'volume_sma'],
                'required': True
            }
        }
        
        found_metrics = {}
        for metric, metric_info in required_metrics.items():
            found = any(keyword in narrative_lower for keyword in metric_info['keywords'])
            found_metrics[metric] = found
            
            if found:
                compliant_elements.append(f"✅ Required metric '{metric}' mentioned")
            else:
                violations.append(f"❌ Missing required metric: {metric}")
        
        # Check if metrics appear in story section (📖)
        story_section = self._extract_section(narrative, '📖')
        if story_section:
            story_lower = story_section.lower()
            story_metrics = sum(1 for metric, _ in required_metrics.items() 
                              if any(kw in story_lower for kw in required_metrics[metric]['keywords']))
            
            if story_metrics >= 3:
                compliant_elements.append(f"✅ Story section includes {story_metrics}/4 required metrics")
            else:
                violations.append(f"❌ Story section (📖) should include all 4 metrics, found {story_metrics}")
        
        # Check for percentile context
        has_percentile = bool(re.search(r'เปอร์เซ็นไทล์\s*\d+\.?\d*%', narrative)) or \
                        bool(re.search(r'percentile\s*\d+\.?\d*%', narrative_lower))
        
        if has_percentile:
            compliant_elements.append("✅ Includes percentile context")
        else:
            # Check if percentiles are available
            if indicators.get('percentiles'):
                violations.append("⚠️ Percentile data available but not used")
        
        # Check for specific numbers (not just generic statements)
        numbers = re.findall(r'\d+\.?\d*', narrative)
        if len(numbers) >= 5:
            compliant_elements.append(f"✅ Includes {len(numbers)} specific numbers")
        else:
            violations.append(f"⚠️ Should include more specific numbers (found {len(numbers)})")
        
        # Calculate score
        total_required = len([m for m in required_metrics.values() if m['required']])
        found_count = sum(1 for found in found_metrics.values() if found)
        score = (found_count / total_required * 100) if total_required > 0 else 0
        
        # Penalize missing metrics in story section
        if violations and any('Story section' in v for v in violations):
            score -= 10
        
        # Penalize missing percentile context if data available
        if violations and any('Percentile' in v for v in violations):
            score -= 5
        
        return max(0, min(100, score)), violations, compliant_elements
    
    def _check_format_compliance(self, narrative: str) -> Tuple[float, List[str], List[str]]:
        """Check for prohibited format elements"""
        violations = []
        compliant_elements = []
        
        # Check for tables (prohibited)
        has_table_markers = bool(re.search(r'\|.*\|', narrative)) or \
                           bool(re.search(r'---+\|', narrative)) or \
                           bool(re.search(r'\+---', narrative))
        
        if has_table_markers:
            violations.append("❌ Contains tables (prohibited)")
        else:
            compliant_elements.append("✅ No tables found")
        
        # Check for numbered lists in insights section (prohibited)
        insights_section = self._extract_section(narrative, '💡')
        if insights_section:
            has_numbered_list = bool(re.search(r'\d+\.\s+[A-Za-z]', insights_section)) or \
                               bool(re.search(r'\d+\.\s+[ก-๙]', insights_section))
            
            if has_numbered_list:
                violations.append("❌ Insights section (💡) contains numbered lists (prohibited)")
            else:
                compliant_elements.append("✅ Insights section has no numbered lists")
        
        # Check for bullet points (prohibited - should use narrative)
        has_bullets = bool(re.search(r'^[-*•]\s+', narrative, re.MULTILINE)) or \
                     bool(re.search(r'^[-*•]\s+', narrative, re.MULTILINE))
        
        if has_bullets:
            violations.append("⚠️ Contains bullet points (should use narrative style)")
        else:
            compliant_elements.append("✅ Uses narrative style (no bullet points)")
        
        # Check for strategy name mention (prohibited)
        prohibited_strategy_names = ['sma crossing', 'sma cross', 'moving average crossover', 
                                    'sma crossover', 'sma strategy']
        narrative_lower = narrative.lower()
        has_strategy_name = any(name in narrative_lower for name in prohibited_strategy_names)
        
        if has_strategy_name:
            violations.append("❌ Mentions strategy name (should use generic 'กลยุทธ์ของเรา')")
        else:
            compliant_elements.append("✅ No prohibited strategy name mentions")
        
        # Calculate score
        score = 100.0
        score -= len(violations) * 25  # Penalize each violation
        
        return max(0, min(100, score)), violations, compliant_elements
    
    def _check_length_compliance(self, narrative: str) -> Tuple[float, List[str], List[str]]:
        """Check if report meets length requirements"""
        violations = []
        compliant_elements = []
        
        # Count lines (non-empty)
        lines = [line.strip() for line in narrative.split('\n') if line.strip()]
        line_count = len(lines)
        
        # Count words
        word_count = len(narrative.split())
        
        # Check line count (should be under 12-15 lines)
        # This is approximate - we'll use a range
        if line_count <= 20:  # Reasonable upper bound
            compliant_elements.append(f"✅ Line count ({line_count}) within acceptable range")
        else:
            violations.append(f"❌ Report too long ({line_count} lines, should be under 12-15)")
        
        # Check word count (reasonable bounds)
        if 200 <= word_count <= 1200:
            compliant_elements.append(f"✅ Word count ({word_count}) within reasonable range")
        elif word_count < 200:
            violations.append(f"⚠️ Report too short ({word_count} words)")
        else:
            violations.append(f"⚠️ Report quite long ({word_count} words)")
        
        # Check section lengths
        story_section = self._extract_section(narrative, '📖')
        if story_section:
            story_words = len(story_section.split())
            if 20 <= story_words <= 100:  # 2-3 sentences
                compliant_elements.append(f"✅ Story section length appropriate ({story_words} words)")
            else:
                violations.append(f"⚠️ Story section should be 2-3 sentences ({story_words} words)")
        
        # Calculate score
        score = 100.0
        
        if violations:
            if any('too long' in v for v in violations):
                score -= 30
            elif any('too short' in v for v in violations):
                score -= 20
            else:
                score -= 10  # Minor length issues
        
        return max(0, min(100, score)), violations, compliant_elements
    
    def _check_language_compliance(self, narrative: str) -> Tuple[float, List[str], List[str]]:
        """Check if report is written in Thai with proper style"""
        violations = []
        compliant_elements = []
        
        # Check for Thai characters
        thai_chars = re.findall(r'[ก-๙]', narrative)
        thai_char_ratio = len(thai_chars) / max(len(narrative.replace(' ', '')), 1)
        
        if thai_char_ratio > 0.3:  # At least 30% Thai characters
            compliant_elements.append(f"✅ Written in Thai ({thai_char_ratio*100:.1f}% Thai characters)")
        else:
            violations.append(f"❌ Report should be written in Thai (found {thai_char_ratio*100:.1f}% Thai characters)")
        
        # Check for narrative style (not bullet points)
        has_narrative_flow = bool(re.search(r'[เพราะ|เนื่องจาก|ดังนั้น|จึง|ทำให้]', narrative)) or \
                            bool(re.search(r'[because|therefore|thus|so]', narrative.lower()))
        
        if has_narrative_flow:
            compliant_elements.append("✅ Uses narrative flow (cause-effect relationships)")
        else:
            violations.append("⚠️ Lacks narrative flow (should tell stories, not lists)")
        
        # Check for conversational tone indicators
        conversational_markers = ['ต้อง', 'ควร', 'ทำให้', 'ส่งผลให้', 'แสดงว่า', 'บ่งบอกว่า']
        has_conversational = any(marker in narrative for marker in conversational_markers)
        
        if has_conversational:
            compliant_elements.append("✅ Uses conversational tone")
        
        # Calculate score
        score = 100.0
        
        if violations:
            if any('should be written in Thai' in v for v in violations):
                score -= 50  # Critical violation
            else:
                score -= 10  # Minor style issues
        
        return max(0, min(100, score)), violations, compliant_elements
    
    def _check_citation_compliance(self, narrative: str, news_data: List[Dict]) -> Tuple[float, List[str], List[str]]:
        """Check if news citations follow format [1], [2]"""
        violations = []
        compliant_elements = []
        
        # Extract citations
        citations = re.findall(r'\[(\d+)\]', narrative)
        
        if not citations:
            if news_data:
                # News available but not cited - this is OK per policy (only cite if relevant)
                compliant_elements.append("✅ No forced news citations (news available but not cited)")
            else:
                # No news, no citations - OK
                compliant_elements.append("✅ No news citations (no news available)")
            return 100.0, violations, compliant_elements
        
        # Check citation format
        for citation in citations:
            try:
                citation_num = int(citation)
                if citation_num >= 1:
                    compliant_elements.append(f"✅ Citation [{citation_num}] follows correct format")
                else:
                    violations.append(f"❌ Invalid citation format: [{citation_num}]")
            except ValueError:
                violations.append(f"❌ Invalid citation format: [{citation}]")
        
        # Check if citations are valid (within range)
        if news_data:
            max_valid = len(news_data)
            invalid_citations = [c for c in citations if int(c) > max_valid]
            
            if invalid_citations:
                violations.append(f"❌ Invalid citations: {invalid_citations} (only {max_valid} news items available)")
            else:
                compliant_elements.append(f"✅ All citations valid ({len(citations)} citations, {max_valid} news items)")
        
        # Check if citations are forced (mentioned but not relevant)
        # This is hard to detect automatically, so we'll just check format
        
        # Calculate score
        score = 100.0
        
        if violations:
            score -= len(violations) * 20
        
        return max(0, min(100, score)), violations, compliant_elements
    
    def format_score_report(self, score: ComplianceScore) -> str:
        """Format compliance score as human-readable report"""
        report_lines = [
            "=" * 80,
            "COMPLIANCE SCORE REPORT",
            "=" * 80,
            "",
            f"📊 Overall Compliance Score: {score.overall_score:.1f}/100",
            "",
            "Dimension Breakdown:",
        ]
        
        for dimension, value in score.dimension_scores.items():
            emoji = "✅" if value >= 80 else ("⚠️" if value >= 60 else "❌")
            report_lines.append(f"  {emoji} {dimension}: {value:.1f}/100")
        
        if score.violations:
            report_lines.extend([
                "",
                "❌ Compliance Violations:",
            ])
            for violation in score.violations:
                report_lines.append(f"  {violation}")
        
        if score.compliant_elements:
            report_lines.extend([
                "",
                "✅ Compliant Elements:",
            ])
            for element in score.compliant_elements[:10]:  # Limit to first 10
                report_lines.append(f"  {element}")
            if len(score.compliant_elements) > 10:
                report_lines.append(f"  ... and {len(score.compliant_elements) - 10} more")
        
        report_lines.extend([
            "",
            "=" * 80
        ])
        
        return "\n".join(report_lines)
