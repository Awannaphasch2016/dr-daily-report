# Reasoning Quality Scoring for Narrative Reports

## Overview

The Reasoning Quality Scorer measures the quality of explanations and reasoning in LLM-generated narratives. Unlike faithfulness (which checks accuracy) and completeness (which checks coverage), reasoning quality evaluates how well the narrative explains and justifies its claims.

## What It Measures

### 1. Clarity (Weight: 20%)

Checks if explanations are clear and easy to understand:

- **Vague Terms**: Minimizes use of vague language (maybe, perhaps, might be)
- **Cause-Effect Relationships**: Uses clear cause-effect markers (because, therefore, ทำให้)
- **Structure**: Uses structured format (sections, formatting)
- **Explanations**: Provides explanations (not just statements)
- **Sentence Length**: Uses appropriate sentence length (not too long or too short)

**Rationale**: Clear explanations help readers understand the reasoning

**Examples**:
- ✅ "ราคาสูงกว่า VWAP 22.06% เพราะแรงซื้อแรงมาก ทำให้ราคาขึ้นสูง"
- ❌ "ราคาอาจจะสูงกว่า VWAP บางทีอาจเป็นเพราะแรงซื้อ"

### 2. Coverage (Weight: 20%)

Checks if reasoning covers all relevant analytical aspects:

- **Multiple Dimensions**: Explains technical, volatility, sentiment, volume, historical, fundamental
- **WHY Explanations**: Explains WHY (not just WHAT)
- **Relevant Aspects**: Covers aspects relevant to the conclusion

**Rationale**: Complete reasoning considers all relevant factors

**Examples**:
- ✅ Covers 5/6 analytical dimensions with WHY explanations
- ❌ Only covers 2/6 dimensions without explaining WHY

### 3. Specificity (Weight: 20%)

Checks if explanations are specific rather than generic:

- **Generic Phrases**: Minimizes generic language (generally, usually, typically)
- **Specific Numbers**: Includes specific numbers/data points
- **Comparisons**: Uses specific comparisons (compared to, เทียบกับ)
- **Named Entities**: References specific entities/tickers

**Rationale**: Specific explanations are more actionable and credible

**Examples**:
- ✅ "RSI 65.36 ซึ่งอยู่ในเปอร์เซ็นไทล์ 88.5% สูงกว่าค่าเฉลี่ย 55.0"
- ❌ "RSI โดยทั่วไปสูงกว่าปกติ"

### 4. Alignment (Weight: 15%)

Checks if explanations align with data/claims:

- **Percentile Alignment**: Percentile claims match actual percentile data
- **Uncertainty Alignment**: Uncertainty interpretations match thresholds
- **VWAP Alignment**: VWAP interpretations match actual values

**Rationale**: Explanations should align with the data they reference

**Examples**:
- ✅ "Uncertainty 51/100 ซึ่งอยู่ในเปอร์เซ็นไทล์ 66% - สูงกว่าปกติ" (matches data)
- ❌ "Uncertainty ต่ำ" when score is 75/100 (doesn't align)

### 5. Minimality (Weight: 15%)

Checks if reasoning is concise without being incomplete:

- **Optimal Length**: 200-800 words (optimal for reports)
- **Repetition**: Minimizes repetition
- **Redundant Phrases**: Avoids redundant phrases (in other words, กล่าวอีกนัยหนึ่ง)
- **Filler Words**: Minimizes filler words (actually, basically)

**Rationale**: Concise reasoning is easier to follow and more professional

**Examples**:
- ✅ 400-word report with no repetition
- ❌ 1500-word report with redundant phrases

### 6. Consistency (Weight: 10%)

Checks if explanations are internally consistent:

- **No Contradictions**: No conflicting statements
- **Single Recommendation**: Single clear recommendation (BUY/SELL/HOLD)
- **Consistent Risk Assessment**: Risk assessment is consistent throughout

**Rationale**: Consistent reasoning is more credible

**Examples**:
- ✅ Single BUY recommendation with consistent risk assessment
- ❌ Both BUY and SELL recommendations in same report

## How It Works

### 1. Pattern Matching

Uses flexible pattern matching to detect reasoning quality indicators:

```python
# Cause-effect relationships
cause_effect_markers = [
    'because', 'เนื่องจาก', 'เพราะว่า', 'ทำให้',
    'therefore', 'ดังนั้น', 'จึง', 'ส่งผลให้'
]

# Specific numbers
number_patterns = [
    r'\d+\.?\d*%',  # Percentages
    r'\$\d+\.?\d*',  # Dollar amounts
    r'เปอร์เซ็นไทล์\s*\d+\.?\d*%',  # Percentile mentions
]
```

### 2. Scoring Per Dimension

Each dimension is scored independently (0-100), then weighted:

```python
clarity_score = evaluate_clarity(narrative)
coverage_score = evaluate_coverage(narrative, indicators, percentiles)
# ... etc
```

### 3. Overall Score Calculation

```python
overall_score = (
    clarity_score * 0.20 +
    coverage_score * 0.20 +
    specificity_score * 0.20 +
    alignment_score * 0.15 +
    minimality_score * 0.15 +
    consistency_score * 0.10
)
```

## Usage

### In Agent Workflow

Reasoning quality scoring happens automatically after report generation:

```python
# In agent.py - generate_report method
state["report"] = report

# Score reasoning quality
reasoning_quality_score = self._score_reasoning_quality(
    report, indicators, percentiles, ticker_data
)
state["reasoning_quality_score"] = reasoning_quality_score

# Print report
print("\n" + self.reasoning_quality_scorer.format_score_report(reasoning_quality_score))
```

### Standalone Usage

```python
from src.reasoning_quality_scorer import ReasoningQualityScorer

scorer = ReasoningQualityScorer()

score = scorer.score_narrative(
    narrative=thai_report,
    indicators=indicators,
    percentiles=percentiles,
    ticker_data=ticker_data
)

print(scorer.format_score_report(score))
```

## Example Output

```
================================================================================
REASONING QUALITY SCORE REPORT
================================================================================

📊 Overall Reasoning Quality Score: 87.5/100

Dimension Breakdown:
  ✅ clarity: 85.0/100
  ✅ coverage: 90.0/100
  ✅ specificity: 95.0/100
  ✅ alignment: 85.0/100
  ✅ minimality: 80.0/100
  ✅ consistency: 100.0/100

✅ Reasoning Quality Strengths:
  ✅ No vague terms - explanations are confident
  ✅ Clear cause-effect relationships present
  ✅ Well-structured narrative format
  ✅ Explains WHY (not just WHAT)
  ✅ Includes 8 specific numbers/data points
  ✅ No internal contradictions found

❌ Reasoning Quality Issues:
  ⚠️ Sentences slightly long (650 words)

================================================================================
```

## Interpreting Results

### Score Ranges

- **90-100**: Excellent - Reasoning is clear, specific, and well-aligned
- **80-89**: Good - Minor issues, but generally high quality
- **70-79**: Fair - Some clarity or specificity issues
- **60-69**: Poor - Significant reasoning quality problems
- **<60**: Failed - Reasoning is unclear or inconsistent

### Common Issues

#### 1. Low Clarity
**Problem**: Too many vague terms or missing cause-effect relationships
```
❌ Too many vague terms reduce clarity
❌ Missing clear cause-effect relationships
```
**Solution**: Use specific language and explicit cause-effect markers

#### 2. Low Specificity
**Problem**: Generic language without specific numbers
```
❌ Too many generic phrases (reduce specificity)
❌ Lacks specific numbers/data points
```
**Solution**: Include specific numbers and comparisons

#### 3. Low Alignment
**Problem**: Explanations don't align with data
```
❌ Uncertainty interpretation doesn't align with score
❌ Only 2/5 percentile claims aligned
```
**Solution**: Ensure interpretations match actual data values

#### 4. Low Minimality
**Problem**: Too long or repetitive
```
❌ Too long (1500 words) - needs conciseness
❌ Too much repetition reduces conciseness
```
**Solution**: Edit for conciseness and remove repetition

## Relationship to Other Scores

**Reasoning Quality** complements **Faithfulness** and **Completeness**:

- **Faithfulness**: "Is what is stated accurate?"
- **Completeness**: "Are all important dimensions covered?"
- **Reasoning Quality**: "Is the explanation good?"

Example:
- A report can be **faithful** (accurate) but have **poor reasoning quality** (unclear explanations)
- A report can be **complete** (covers all dimensions) but have **poor reasoning quality** (generic language)

Together, they provide comprehensive quality assessment:

```python
overall_quality = (
    faithfulness_score * 0.6 +
    completeness_score * 0.2 +
    reasoning_quality_score * 0.2
)
```

## Architecture

### Class: ReasoningQualityScorer

#### Methods
- `score_narrative()` - Main scoring method
- `_check_clarity()` - Check explanation clarity
- `_check_coverage()` - Check reasoning coverage
- `_check_specificity()` - Check explanation specificity
- `_check_alignment()` - Check data alignment
- `_check_minimality()` - Check conciseness
- `_check_consistency()` - Check internal consistency
- `format_score_report()` - Format human-readable report

#### Data Classes
```python
@dataclass
class ReasoningQualityScore:
    overall_score: float              # 0-100
    dimension_scores: Dict[str, float]  # Individual dimension scores
    issues: List[str]                 # Reasoning quality issues
    strengths: List[str]              # Reasoning quality strengths
```

## Testing

### Unit Tests
```bash
python -m pytest tests/test_reasoning_quality_scorer.py -v
```

### Integration Test
```bash
python show_scores.py --ticker DBS19
# Check console output for reasoning quality report
```

## Best Practices

### 1. Review Issues

Always check issues for high-stakes reports:

```python
if reasoning_quality_score.overall_score < 80:
    print("⚠️ Review required:")
    for issue in reasoning_quality_score.issues:
        print(f"  {issue}")
```

### 2. Improve Prompt Engineering

Enhance reasoning quality through prompts:

- **Emphasize clarity**: "Use clear cause-effect language"
- **Require specificity**: "Include specific numbers, not generic statements"
- **Avoid vague terms**: "Use confident language, avoid 'maybe' or 'perhaps'"
- **Require explanations**: "Explain WHY, not just WHAT"

### 3. Balance with Other Scores

Don't sacrifice faithfulness for reasoning quality:

```python
# If reasoning quality is high but faithfulness is low, prioritize accuracy
if faithfulness_score.overall_score < 70:
    # Regenerate with focus on accuracy
    regenerate_report(focus='accuracy')
```

## Limitations

1. **Pattern Matching**: May miss reasoning quality issues phrased differently
2. **Thai Language**: Regex patterns may not catch all Thai variations
3. **Context Understanding**: Can't verify semantic correctness of explanations
4. **Subjective Elements**: Some aspects (e.g., "clarity") are somewhat subjective
5. **Length Optimization**: Optimal length may vary by use case

## Future Enhancements

### 1. Semantic Understanding

Use LLM to evaluate reasoning quality:

```python
# Use LLM to verify: "Is this explanation clear?"
is_clear = llm.verify(
    f"Is this explanation clear and easy to understand?\nText: {narrative}"
)
```

### 2. Domain-Specific Patterns

Add patterns for financial reasoning:

```python
# Check for proper financial reasoning patterns
financial_reasoning_patterns = [
    'risk-return tradeoff',
    'technical support/resistance',
    'fundamental valuation',
    ...
]
```

### 3. Comparative Analysis

Compare reasoning quality across reports:

```python
# Track reasoning quality trends
avg_reasoning_quality = db.get_avg_reasoning_quality_score(days=30)
if avg_reasoning_quality < 75:
    alert("Reasoning quality declining - review prompts")
```

## References

- **Explanation Quality Metrics**: https://arxiv.org/abs/2305.13534
- **Financial Narrative Analysis**: https://aclanthology.org/2023.findings-acl.1/
- **Reasoning Evaluation**: https://docs.ragas.io/en/latest/concepts/metrics/answer_correctness.html

## Changelog

### v1.0.0 (2025-11-01)
- ✅ Initial implementation
- ✅ 6 dimension scoring system
- ✅ Flexible pattern matching for Thai language
- ✅ Integration with agent workflow
- ✅ Comprehensive test coverage
