# Completeness Scoring for Narrative Reports

## Overview

The Completeness Scorer measures how comprehensively the LLM-generated narrative covers all necessary analytical dimensions. Unlike faithfulness (which checks accuracy), completeness focuses on conceptual coverage - whether the report addresses all important aspects of analysis.

## What It Measures

### 1. Context Completeness (Weight: 20%)

Checks if the report provides sufficient context about the ticker:

- **Company Identity**: Company name or ticker symbol mentioned
- **Current State**: Current price mentioned
- **Market Context**: Sector/industry mentioned (if available)
- **Market Positioning**: 52-week high/low or market cap mentioned (if available)

**Rationale**: Reader needs to know what they're analyzing

**Examples**:
- ✅ "บริษัท Apple Inc. (AAPL) มีราคาปัจจุบัน $202.49"
- ❌ Missing company name or ticker symbol
- ❌ Missing current price

### 2. Analysis Dimension Completeness (Weight: 25%)

Checks if the report covers all relevant analytical dimensions:

- **Technical Analysis**: Mention of technical indicators (RSI, MACD, SMA, Bollinger Bands, etc.)
- **Volatility/Risk Assessment**: Mention of uncertainty score OR volatility (ATR)
- **Market Sentiment**: Mention of buying/selling pressure (VWAP context) OR news sentiment
- **Volume Analysis**: Mention of volume or trading activity
- **Fundamental Context**: If fundamental data available (P/E, EPS, growth), mention at least one fundamental metric
- **Historical Context**: Use of percentile analysis or historical comparison

**Rationale**: A complete analysis should cover multiple dimensions, not just one

**Examples**:
- ✅ "RSI 65.36 แสดงภาวะ Overbought, ATR 3.03% แสดงความผันผวนสูง, VWAP แสดงแรงซื้อแรงมาก, ปริมาณซื้อขาย 1.8x ของเฉลี่ย"
- ❌ Only mentions technical indicators without volatility or sentiment
- ❌ Fundamental data available but not mentioned

### 3. Temporal Completeness (Weight: 15%)

Checks if the report provides temporal context:

- **Current State**: Current price/indicators mentioned
- **Historical Comparison**: Percentile context OR comparison to historical values
- **Trend Direction**: Implicit or explicit mention of trend (up/down/flat) or momentum
- **Timeframe Awareness**: Context about when this analysis is valid (date mentioned or implied)

**Rationale**: Investors need to understand if current state is unusual historically

**Examples**:
- ✅ "ราคาปัจจุบัน $202.49 ซึ่งอยู่ในเปอร์เซ็นไทล์ 88% - สูงมากในอดีต แสดงแนวโน้มขาขึ้นในช่วง 3 เดือนที่ผ่านมา"
- ❌ Mentions current state but no historical comparison
- ❌ No mention of trend direction

### 4. Actionability Completeness (Weight: 20%)

Checks if the report provides actionable insights:

- **Clear Recommendation**: BUY/SELL/HOLD explicitly stated
- **Reasoning Provided**: Explanation for why the recommendation is made
- **Risk Warnings**: Mention of risks or concerns (even if minimal)
- **Key Decision Factors**: Identifies what factors drove the recommendation

**Rationale**: The report should help readers make decisions

**Examples**:
- ✅ "🎯 **ควรทำอะไรตอนนี้?** แนะนำ BUY เพราะ uncertainty score ต่ำและมีแรงซื้อแรงมาก อย่างไรก็ตาม ควรระวังความผันผวนที่อาจเกิดขึ้น"
- ❌ No clear recommendation
- ❌ Recommendation without reasoning

### 5. Narrative Structure Completeness (Weight: 10%)

Checks if the report has proper narrative structure:

- **Story/Context Section**: Opening section that sets context (📖 section)
- **Analysis/Insights Section**: Middle section with analysis (💡 section)
- **Recommendation Section**: Action-oriented section (🎯 section)
- **Risk Section**: Warning section (⚠️ section)

**Rationale**: Structured narrative is easier to follow and more professional

**Examples**:
- ✅ Report has all 4 sections: 📖, 💡, 🎯, ⚠️
- ❌ Missing story/context section
- ❌ Missing risk section

### 6. Quantitative Context Completeness (Weight: 10%)

Checks if numbers are properly contextualized:

- **Percentile Context**: When numbers are mentioned, percentile context provided (if available)
- **Threshold Interpretation**: Qualitative interpretation matches quantitative thresholds (e.g., "high uncertainty" for >50)
- **Comparative Context**: Numbers compared to benchmarks, averages, or historical values

**Rationale**: Raw numbers without context are less useful

**Examples**:
- ✅ "Uncertainty 52/100 ซึ่งอยู่ในเปอร์เซ็นไทล์ 88% - สูงกว่าปกติในอดีต"
- ❌ "Uncertainty 52/100" without percentile context
- ❌ Numbers mentioned but no comparative context

## How It Works

### 1. Pattern Matching

Uses flexible pattern matching to detect coverage:

```python
# Company identity
has_company = (
    company_name.lower() in narrative_lower or
    ticker_symbol.lower() in narrative_lower or
    any(keyword in narrative_lower for keyword in ['บริษัท', 'company', 'หุ้น'])
)

# Technical analysis
has_technical = any(keyword in narrative_lower for keyword in [
    'rsi', 'macd', 'sma', 'bollinger', 'technical', 'ทางเทคนิค'
])
```

### 2. Scoring Per Dimension

Each dimension is scored independently (0-100), then weighted:

```python
context_score = (covered_elements / total_checks) * 100
analysis_score = (covered_dimensions / total_dimensions) * 100
# ... etc
```

### 3. Overall Score Calculation

```python
overall_score = (
    context_score * 0.20 +
    analysis_score * 0.25 +
    temporal_score * 0.15 +
    action_score * 0.20 +
    structure_score * 0.10 +
    quant_score * 0.10
)
```

## Usage

### In Agent Workflow

Completeness scoring happens automatically after report generation:

```python
# In agent.py - generate_report method
state["report"] = report

# Score narrative completeness
completeness_score = self._score_narrative_completeness(
    report, ticker_data, indicators, percentiles, news
)
state["completeness_score"] = completeness_score

# Print report
print("\n" + self.completeness_scorer.format_score_report(completeness_score))
```

### Standalone Usage

```python
from src.completeness_scorer import CompletenessScorer

scorer = CompletenessScorer()

score = scorer.score_narrative(
    narrative=thai_report,
    ticker_data={
        'company_name': 'Apple Inc.',
        'ticker': 'AAPL',
        'current_price': 202.49,
        'sector': 'Technology',
        'pe_ratio': 28.5
    },
    indicators=indicators,
    percentiles=percentiles,
    news_data=news
)

print(scorer.format_score_report(score))
```

## Example Output

```
================================================================================
COMPLETENESS SCORE REPORT
================================================================================

📊 Overall Completeness Score: 87.5/100

Dimension Breakdown:
  ✅ context_completeness: 100.0/100
  ✅ analysis_dimensions: 83.3/100
  ✅ temporal_completeness: 100.0/100
  ✅ actionability: 75.0/100
  ✅ narrative_structure: 100.0/100
  ✅ quantitative_context: 100.0/100

❌ Missing Elements:
  ❌ Fundamental analysis not mentioned (data available but not used)
  ❌ Reasoning for recommendation not provided

✅ Covered Elements: 18

================================================================================
```

## Interpreting Results

### Score Ranges

- **90-100**: Excellent - Report covers all essential dimensions comprehensively
- **80-89**: Good - Minor gaps, but generally complete
- **70-79**: Fair - Some important dimensions missing
- **60-69**: Poor - Significant gaps in coverage
- **<60**: Failed - Report is incomplete

### Common Missing Elements

#### 1. Missing Fundamental Analysis
**Problem**: Fundamental data available but not mentioned
```
❌ Fundamental analysis not mentioned (data available but not used)
```
**Cause**: LLM focused on technical analysis only, ignored fundamental metrics

#### 2. Missing Historical Context
**Problem**: Numbers mentioned without percentile context
```
❌ Historical context (percentile analysis) not mentioned
```
**Cause**: Percentile data available but not incorporated into narrative

#### 3. Missing Risk Warnings
**Problem**: Recommendation without risk considerations
```
❌ Risk warnings not mentioned
```
**Cause**: LLM focused on positive aspects only

#### 4. Missing Narrative Structure
**Problem**: Report doesn't follow structured format
```
❌ Risk section (⚠️) missing
```
**Cause**: LLM didn't follow prompt structure requirements

## Edge Cases

### What if fundamental data is not available?

**Answer**: Completeness scorer does NOT penalize missing fundamental analysis if data is not available. Only penalizes if data exists but is not mentioned.

```python
# If fundamental data not available
fundamental_available = any([
    ticker_data.get('pe_ratio'),
    ticker_data.get('eps'),
    ...
])

if fundamental_available:
    # Check if mentioned
    if not has_fundamental:
        missing.append("Fundamental analysis not mentioned")
# Don't penalize if not available
```

### What if percentiles are not available?

**Answer**: Quantitative context completeness adjusts scoring to not penalize missing percentile context if percentiles are not available.

```python
# If no numbers mentioned, can't check percentile context
has_numbers = bool(re.search(r'\d+\.?\d*', narrative))
if has_numbers:
    if has_percentile_context:
        covered.append("Numbers include percentile context")
    else:
        missing.append("Percentile context missing")
else:
    covered.append("No numbers to contextualize")
```

### What if news is not available?

**Answer**: Analysis dimension completeness checks for market sentiment via VWAP OR news sentiment. If news is not available, VWAP analysis is sufficient.

```python
has_sentiment = (
    any(keyword in narrative_lower for keyword in ['vwap', 'buying pressure', ...]) or
    len(news_data) > 0 and any('[1]' in narrative or ...)
)
```

## Architecture

### Class: CompletenessScorer

#### Methods
- `score_narrative()` - Main scoring method
- `_check_context_completeness()` - Check context elements
- `_check_analysis_dimensions()` - Check analytical coverage
- `_check_temporal_completeness()` - Check temporal context
- `_check_actionability()` - Check actionable insights
- `_check_narrative_structure()` - Check report structure
- `_check_quantitative_context()` - Check number contextualization
- `format_score_report()` - Format human-readable report

#### Data Classes
```python
@dataclass
class CompletenessScore:
    overall_score: float              # 0-100
    dimension_scores: Dict[str, float]  # Individual dimension scores
    missing_elements: List[str]       # Missing analytical elements
    covered_elements: List[str]       # Successfully covered elements
```

## Testing

### Unit Tests
```bash
python -m pytest tests/test_completeness_scorer.py -v
```

### Integration Test
```bash
python tests/test_pdf_generation.py --ticker NVDA19
# Check console output for completeness report
```

## Relationship to Faithfulness

**Completeness** and **Faithfulness** are complementary but separate:

- **Faithfulness**: "Is what is stated accurate?"
- **Completeness**: "Are all important dimensions covered?"

Example:
- A report can be **faithful** (all numbers accurate) but **incomplete** (missing risk warnings)
- A report can be **complete** (covers all dimensions) but **unfaithful** (numbers are wrong)

Together, they provide a comprehensive quality assessment:

```python
overall_quality = (faithfulness_score * 0.8) + (completeness_score * 0.2)
```

See [FAITHFULNESS_SCORING.md](./FAITHFULNESS_SCORING.md) for faithfulness scoring details.

## Best Practices

### 1. Review Missing Elements

Always check missing elements for high-stakes reports:

```python
if completeness_score.overall_score < 80:
    print("⚠️ Review required:")
    for missing in completeness_score.missing_elements:
        print(f"  {missing}")
    # Decide: approve, regenerate, or manually enhance
```

### 2. Track Over Time

Monitor completeness trends:

```python
# Store scores in database
db.save_completeness_score(ticker, date, score)

# Analyze trends
avg_score = db.get_avg_completeness_score(days=30)
if avg_score < 75:
    alert("Completeness declining - review prompts")
```

### 3. Prompt Engineering

Improve completeness through prompts:

- **Emphasize structure**: "You MUST include all 4 sections: 📖, 💡, 🎯, ⚠️"
- **List dimensions**: "Cover: technical, volatility, sentiment, volume, fundamental, historical"
- **Show examples**: Demonstrate complete reports with all dimensions

### 4. Balance with Faithfulness

Don't sacrifice faithfulness for completeness:

```python
# If both scores are low, regenerate
if faithfulness_score.overall_score < 70 and completeness_score.overall_score < 70:
    # Regenerate with stricter prompt
    regenerate_report()
```

## Limitations

1. **Pattern Matching**: May miss coverage phrased differently
2. **Thai Language**: Regex patterns may not catch all Thai variations
3. **Synonym Detection**: May not recognize all synonyms (e.g., "RSI" vs "Relative Strength Index")
4. **Contextual Understanding**: Can't verify if coverage is meaningful or just token mentions
5. **Optional Elements**: Some elements (e.g., market cap) are optional, scoring adjusts accordingly

## Future Enhancements

### 1. Semantic Understanding

Use LLM to check if coverage is meaningful, not just token matching:

```python
# Use LLM to verify: "Does this mention of RSI actually provide analysis?"
is_meaningful = llm.verify(
    f"Does this text provide meaningful analysis of RSI?\nText: {narrative}"
)
```

### 2. Weighted Dimensions

Allow customization of dimension weights based on use case:

```python
scorer = CompletenessScorer(
    weights={
        'context': 0.15,
        'analysis': 0.30,  # Higher weight for analysis
        'temporal': 0.15,
        'actionability': 0.25,
        'structure': 0.10,
        'quantitative': 0.05
    }
)
```

### 3. Adaptive Scoring

Adjust expectations based on report length:

```python
# Short reports (< 500 words) may not cover all dimensions
if len(narrative) < 500:
    # Reduce expectations for structure completeness
    structure_score = adjust_for_length(structure_score, len(narrative))
```

## References

- **RAGAS Completeness**: https://docs.ragas.io/en/latest/concepts/metrics/answer_completeness.html
- **Evaluation Frameworks**: https://arxiv.org/abs/2305.13534
- **Financial Report Quality**: https://aclanthology.org/2023.findings-acl.1/

## Changelog

### v1.0.0 (2025-11-01)
- ✅ Initial implementation
- ✅ 6 dimension scoring system
- ✅ Flexible pattern matching for Thai language
- ✅ Integration with agent workflow
- ✅ Comprehensive test coverage
