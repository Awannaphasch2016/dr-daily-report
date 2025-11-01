# Compliance Scoring for Narrative Reports

## Overview

The Compliance Scorer measures whether the report follows required format, structure, and policy constraints. It answers: "Does it follow required format/policy?"

Unlike other scorers that evaluate content quality, compliance focuses on **adherence to rules** - whether the report meets structural, formatting, and policy requirements specified in the prompt.

## What It Measures

### 1. Structure Compliance (Weight: 30%)

Checks if report has all 4 required sections with correct format:

- **📖 Story Section**: Present with 2-3 sentences
- **💡 Insights Section**: Present with 3-4 paragraphs (NO lists/tables)
- **🎯 Recommendation Section**: Present with ONE clear BUY/SELL/HOLD
- **⚠️ Risk Section**: Present with 1-2 key risks
- **Section Order**: Sections in correct order (📖 → 💡 → 🎯 → ⚠️)

**Rationale**: Structured format ensures consistency and readability

**Examples**:
- ✅ All 4 sections present in correct order
- ❌ Missing risk section (⚠️)
- ❌ Story section has 5 sentences (should be 2-3)

### 2. Content Compliance (Weight: 25%)

Checks if all required content elements are present:

- **4 Market Condition Metrics**: All must be mentioned (uncertainty, ATR%, VWAP%, volume ratio)
- **Metrics in Story Section**: Story section should include all 4 metrics
- **Percentile Context**: Percentile data used when available
- **Specific Numbers**: Includes specific numbers (not just generic statements)

**Rationale**: Required content ensures reports are comprehensive

**Examples**:
- ✅ All 4 metrics mentioned in story section
- ❌ Missing ATR% metric
- ❌ Story section only mentions 2/4 required metrics

### 3. Format Compliance (Weight: 15%)

Checks for prohibited format elements:

- **NO Tables**: No table markers (|, ---)
- **NO Numbered Lists**: Insights section should not have numbered lists
- **NO Bullet Points**: Should use narrative style, not bullets
- **NO Strategy Names**: Should not mention strategy name (e.g., "SMA crossing")

**Rationale**: Format requirements ensure consistent presentation style

**Examples**:
- ✅ No tables, lists, or bullet points found
- ❌ Insights section contains numbered list (1., 2., 3.)
- ❌ Mentions "SMA crossing" strategy name

### 4. Length Compliance (Weight: 10%)

Checks if report meets length requirements:

- **Total Length**: Under 12-15 lines (approximate)
- **Word Count**: Reasonable range (200-1200 words)
- **Section Lengths**: Story section 2-3 sentences

**Rationale**: Appropriate length ensures readability

**Examples**:
- ✅ Report length within acceptable range
- ❌ Report too long (1500+ words)
- ⚠️ Story section too short (1 sentence)

### 5. Language Compliance (Weight: 10%)

Checks if report is written in Thai with proper style:

- **Thai Language**: Written in Thai (not English)
- **Narrative Flow**: Uses cause-effect relationships
- **Conversational Tone**: Uses conversational markers

**Rationale**: Language requirements ensure consistency

**Examples**:
- ✅ Written in Thai with narrative flow
- ❌ Report not in Thai (should be Thai)
- ⚠️ Lacks narrative flow (should tell stories)

### 6. Citation Compliance (Weight: 10%)

Checks if news citations follow format [1], [2]:

- **Citation Format**: Citations use [1], [2], [3] format
- **Valid Citations**: Citations are within valid range (not [5] when only 3 news items)
- **No Forced Citations**: News not cited if not relevant (OK per policy)

**Rationale**: Citation format ensures proper referencing

**Examples**:
- ✅ Citations follow [1], [2] format
- ✅ No forced citations (news available but not cited - OK)
- ❌ Invalid citation [5] when only 3 news items exist

## How It Works

### 1. Structure Detection

Detects sections using emoji markers:

```python
# Check for section emojis
has_story = '📖' in narrative
has_insights = '💡' in narrative
has_recommendation = '🎯' in narrative
has_risk = '⚠️' in narrative

# Extract section content
story_section = extract_section(narrative, '📖')
```

### 2. Content Verification

Verifies required elements are present:

```python
# Check for 4 metrics
required_metrics = ['uncertainty', 'atr', 'vwap', 'volume']
for metric in required_metrics:
    found = any(keyword in narrative_lower for keyword in metric_keywords[metric])
```

### 3. Format Validation

Checks for prohibited elements:

```python
# Check for tables
has_table = bool(re.search(r'\|.*\|', narrative))

# Check for numbered lists in insights section
has_numbered_list = bool(re.search(r'\d+\.\s+', insights_section))
```

### 4. Scoring

```python
overall_score = (
    structure_score * 0.30 +
    content_score * 0.25 +
    format_score * 0.15 +
    length_score * 0.10 +
    language_score * 0.10 +
    citation_score * 0.10
)
```

## Usage

### In Agent Workflow

Compliance scoring happens automatically after report generation:

```python
# In agent.py - generate_report method
state["report"] = report

# Score compliance
compliance_score = self._score_compliance(
    report, indicators, news
)
state["compliance_score"] = compliance_score

# Print report
print("\n" + self.compliance_scorer.format_score_report(compliance_score))
```

### Standalone Usage

```python
from src.compliance_scorer import ComplianceScorer

scorer = ComplianceScorer()

score = scorer.score_narrative(
    narrative=thai_report,
    indicators=indicators,
    news_data=news
)

print(scorer.format_score_report(score))
```

## Example Output

```
================================================================================
COMPLIANCE SCORE REPORT
================================================================================

📊 Overall Compliance Score: 92.5/100

Dimension Breakdown:
  ✅ structure_compliance: 95.0/100
  ✅ content_compliance: 90.0/100
  ✅ format_compliance: 100.0/100
  ✅ length_compliance: 85.0/100
  ✅ language_compliance: 100.0/100
  ✅ citation_compliance: 100.0/100

✅ Compliant Elements:
  ✅ Story Section (📖) present
  ✅ Insights Section (💡) present
  ✅ Recommendation Section (🎯) present
  ✅ Risk Section (⚠️) present
  ✅ Sections in correct order
  ✅ Story section (📖) has correct length (2-3 sentences)
  ✅ Insights section (💡) uses flowing paragraphs (no lists/tables)
  ✅ Recommendation section (🎯) has ONE clear action: BUY
  ✅ Risk section (⚠️) includes risk warnings
  ✅ Required metric 'uncertainty' mentioned
  ✅ Required metric 'atr' mentioned
  ✅ Required metric 'vwap' mentioned
  ✅ Required metric 'volume' mentioned
  ✅ Story section includes 4/4 required metrics
  ✅ Includes percentile context
  ✅ Includes 12 specific numbers
  ✅ No tables found
  ✅ No prohibited strategy name mentions
  ✅ Written in Thai (85.2% Thai characters)
  ✅ Uses narrative flow (cause-effect relationships)
  ✅ Citations follow [1], [2] format
  ✅ All citations valid (2 citations, 2 news items)

❌ Compliance Violations:
  ⚠️ Story section should be 2-3 sentences (found 4)

================================================================================
```

## Interpreting Results

### Score Ranges

- **90-100**: Excellent - Report fully complies with format/policy
- **80-89**: Good - Minor violations, mostly compliant
- **70-79**: Fair - Some format/structure issues
- **60-69**: Poor - Significant compliance violations
- **<60**: Failed - Report doesn't follow required format

### Common Violations

#### 1. Missing Sections
**Problem**: Required section missing
```
❌ Missing required section: Risk Section (⚠️)
```
**Solution**: Ensure all 4 sections are present

#### 2. Format Violations
**Problem**: Prohibited format elements used
```
❌ Insights section (💡) contains numbered lists (prohibited)
❌ Contains tables (prohibited)
```
**Solution**: Use narrative style, not lists/tables

#### 3. Content Missing
**Problem**: Required metrics not mentioned
```
❌ Missing required metric: ATR
❌ Story section should include all 4 metrics, found 2
```
**Solution**: Include all 4 market condition metrics

#### 4. Length Issues
**Problem**: Report length outside acceptable range
```
❌ Report too long (1500+ words)
⚠️ Story section too short (1 sentence)
```
**Solution**: Adjust length to meet requirements

## Relationship to Other Scores

**Compliance** is complementary to other scores:

- **Faithfulness**: "Is what is stated accurate?" (compliance checks format)
- **Completeness**: "Are all important dimensions covered?" (compliance checks required content)
- **Reasoning Quality**: "Is the explanation good?" (compliance checks structure/style)
- **Compliance**: "Does it follow required format/policy?" (format/structure adherence)

Example:
- A report can be **faithful** (accurate) but **non-compliant** (wrong format)
- A report can be **complete** (covers all dimensions) but **non-compliant** (missing sections)
- A report can have **good reasoning** but **non-compliant** (uses tables/lists)

Together, they provide comprehensive quality assessment:

```python
overall_quality = (
    faithfulness_score * 0.5 +
    completeness_score * 0.2 +
    reasoning_quality_score * 0.2 +
    compliance_score * 0.1
)
```

## Architecture

### Class: ComplianceScorer

#### Methods
- `score_narrative()` - Main scoring method
- `_check_structure_compliance()` - Check section structure
- `_check_content_compliance()` - Check required content
- `_check_format_compliance()` - Check prohibited elements
- `_check_length_compliance()` - Check length requirements
- `_check_language_compliance()` - Check language/style
- `_check_citation_compliance()` - Check citation format
- `_extract_section()` - Extract section content
- `format_score_report()` - Format human-readable report

#### Data Classes
```python
@dataclass
class ComplianceScore:
    overall_score: float              # 0-100
    dimension_scores: Dict[str, float]  # Individual dimension scores
    violations: List[str]             # Compliance violations
    compliant_elements: List[str]    # Compliant elements
```

## Testing

### Unit Tests
```bash
python -m pytest tests/test_compliance_scorer.py -v
```

### Integration Test
```bash
python show_scores.py --ticker DBS19
# Check console output for compliance report
```

## Best Practices

### 1. Review Violations

Always check violations for high-stakes reports:

```python
if compliance_score.overall_score < 80:
    print("⚠️ Review required:")
    for violation in compliance_score.violations:
        print(f"  {violation}")
    # Regenerate or manually fix
```

### 2. Prompt Engineering

Enhance compliance through prompts:

- **Emphasize structure**: "You MUST include all 4 sections: 📖, 💡, 🎯, ⚠️"
- **Prohibit formats**: "NO tables, NO numbered lists, NO bullet points"
- **Require content**: "MUST include all 4 metrics in story section"
- **Set length limits**: "Write under 12-15 lines total"

### 3. Validation Before Publishing

Use compliance score as gate:

```python
if compliance_score.overall_score < 70:
    # Don't publish - regenerate
    regenerate_report(stricter_prompt=True)
else:
    # Publish
    publish_report(report)
```

## Limitations

1. **Pattern Matching**: May miss violations phrased differently
2. **Thai Language**: Regex patterns may not catch all Thai variations
3. **Context Understanding**: Can't verify semantic compliance (e.g., "does section actually contain story?")
4. **Length Approximation**: "12-15 lines" is approximate - uses word count as proxy
5. **Order Detection**: May not detect subtle order violations

## Future Enhancements

### 1. Semantic Structure Validation

Use LLM to verify section content:

```python
# Use LLM to verify: "Does this section actually contain a story?"
is_story = llm.verify(
    f"Does this section tell a story?\nSection: {story_section}"
)
```

### 2. Strict Format Checking

More precise format validation:

```python
# Check exact section structure
expected_structure = {
    '📖': {'min_sentences': 2, 'max_sentences': 3},
    '💡': {'min_paragraphs': 3, 'max_paragraphs': 4},
    '🎯': {'must_have': ['BUY', 'SELL', 'HOLD']},
    '⚠️': {'min_risks': 1, 'max_risks': 2}
}
```

### 3. Policy Rule Engine

Configurable policy rules:

```python
compliance_rules = {
    'required_sections': ['📖', '💡', '🎯', '⚠️'],
    'prohibited_formats': ['tables', 'lists', 'bullets'],
    'length_constraints': {'min_words': 200, 'max_words': 1200},
    'language': 'thai'
}
```

## References

- **Format Compliance**: Based on prompt requirements in `agent.py`
- **Structure Requirements**: Derived from `_build_prompt_structure()` method
- **Content Requirements**: Based on "CRITICAL NARRATIVE ELEMENTS" in prompt

## Changelog

### v1.0.0 (2025-11-01)
- ✅ Initial implementation
- ✅ 6 dimension scoring system
- ✅ Structure, content, format, length, language, citation compliance
- ✅ Integration with agent workflow
- ✅ Comprehensive validation
