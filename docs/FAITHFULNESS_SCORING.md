# Faithfulness Scoring for Narrative Reports

## Overview

The Faithfulness Scorer measures how accurately LLM-generated narratives reflect the actual data. It prevents hallucinations and ensures all claims are grounded in facts.

## What It Measures

### 1. Numeric Accuracy (Weight: 25%)
Verifies that all numbers in the narrative match the source data:
- **Uncertainty Score**: e.g., "56.6/100" must match calculated uncertainty
- **ATR %**: e.g., "3.03%" must match actual ATR percentage
- **VWAP %**: e.g., "43.8% เหนือ VWAP" must match price vs VWAP calculation
- **Volume Ratio**: e.g., "1.0x" must match volume/volume_sma ratio
- **RSI**: e.g., "65.36" must match calculated RSI value
- **Current Price**: e.g., "$202.49" must match actual stock price

**Tolerance**: 2% for most metrics, 0.5% for prices

### 2. Percentile Accuracy (Weight: 20%)
Verifies that percentile claims match historical calculations:
- **Pattern**: "เปอร์เซ็นไทล์ 88%" must match actual percentile for that metric
- **Tolerance**: Within 5 percentage points

Example violations:
```
✅ "RSI 65.36 ซึ่งอยู่ในเปอร์เซ็นไทล์ 90.2%" - Matches RSI percentile
❌ "Uncertainty 56/100 ซึ่งอยู่ในเปอร์เซ็นไทล์ 75%" - Actual is 88%
```

### 3. News Citation Accuracy (Weight: 15%)
Verifies that news references [1], [2], [3] are valid:
- Citation [1] must reference first news item
- Citation [2] must reference second news item
- Invalid citations (e.g., [5] when only 3 news items exist) are flagged

### 4. Required Coverage (Weight: 20%)
Checks if all critical elements are mentioned:
- ✅ **Uncertainty** - Must mention "ความไม่แน่นอน" or "uncertainty"
- ✅ **ATR** - Must mention "ATR" or "ความผันผวน"
- ✅ **VWAP** - Must mention "VWAP" or "แรงซื้อ"/"แรงขาย"
- ✅ **Volume** - Must mention "ปริมาณ" or "volume"

### 5. Interpretation Accuracy (Weight: 20%)
Verifies that qualitative interpretations match quantitative thresholds:

#### Uncertainty Interpretation
- **0-25**: Should say "เสถียร" (stable)
- **25-50**: Should say "ปานกลาง" (moderate)
- **50-75**: Should say "สูง" or "ผันผวน" (high/volatile)
- **75-100**: Should say "รุนแรง" (extreme)

#### VWAP Interpretation
- **>15%**: Should say "แรงซื้อแรงมาก" (strong buying pressure)
- **>5%**: Should say "แรงซื้อ" (buying pressure)
- **-5% to +5%**: Should say "สมดุล" (neutral)
- **<-5%**: Should say "แรงขาย" (selling pressure)
- **<-15%**: Should say "แรงขายแรงมาก" (strong selling pressure)

## How It Works

### 1. Ground Truth Preparation
```python
ground_truth = {
    'uncertainty_score': 56.6,      # From indicators
    'atr_pct': 3.03,                # ATR / current_price * 100
    'vwap_pct': 43.79,              # (price - vwap) / vwap * 100
    'volume_ratio': 1.0,            # volume / volume_sma
}
```

### 2. Pattern Matching
Uses regular expressions to extract claims from Thai narrative:
```python
# Uncertainty pattern
r'ความไม่แน่นอน[^0-9]*?(\d+\.?\d*)'  # Matches "ความไม่แน่นอน 56.6"

# ATR pattern
r'ATR[^0-9]*?(\d+\.?\d*)%'           # Matches "ATR 3.03%"

# Percentile pattern
r'เปอร์เซ็นไทล์[^0-9]*?(\d+\.?\d*)%' # Matches "เปอร์เซ็นไทล์ 88%"
```

### 3. Verification
Compares extracted claims against ground truth:
```python
claimed_value = 3.03
actual_value = 43.79
tolerance = 0.02  # 2%

is_accurate = abs(claimed_value - actual_value) <= (actual_value * tolerance)
```

### 4. Scoring
```python
overall_score = (
    numeric_accuracy * 0.25 +
    percentile_accuracy * 0.20 +
    news_citation_accuracy * 0.15 +
    required_coverage * 0.20 +
    interpretation_accuracy * 0.20
)
```

## Usage

### In Agent Workflow
Faithfulness scoring happens automatically after report generation:

```python
# In agent.py - generate_report method
state["report"] = report

# Score narrative faithfulness
faithfulness_score = self._score_narrative_faithfulness(
    report, indicators, percentiles, news, ticker_data
)
state["faithfulness_score"] = faithfulness_score

# Print report
print("\n" + self.faithfulness_scorer.format_score_report(faithfulness_score))
```

### Standalone Usage
```python
from src.faithfulness_scorer import FaithfulnessScorer

scorer = FaithfulnessScorer()

score = scorer.score_narrative(
    narrative=thai_report,
    ground_truth={
        'uncertainty_score': 56.6,
        'atr_pct': 3.03,
        'vwap_pct': 43.79,
        'volume_ratio': 1.0
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
FAITHFULNESS SCORE REPORT
================================================================================

📊 Overall Faithfulness Score: 91.7/100

Metric Breakdown:
  ⚠️ numeric_accuracy: 66.7/100
  ✅ percentile_accuracy: 100.0/100
  ✅ news_citation_accuracy: 100.0/100
  ✅ required_coverage: 100.0/100
  ✅ interpretation_accuracy: 100.0/100

⚠️ Faithfulness Violations:
  ❌ vwap_pct mismatch: narrative claims 3.03, actual is 43.79
  ❌ current_price mismatch: narrative claims 43.79, actual is 202.49

✅ Verified Claims: 19

================================================================================
```

## Interpreting Results

### Score Ranges
- **90-100**: Excellent - Narrative is highly accurate
- **80-89**: Good - Minor inaccuracies, but trustworthy
- **70-79**: Fair - Some issues, needs review
- **60-69**: Poor - Significant inaccuracies found
- **<60**: Failed - Narrative has major hallucinations

### Common Violations

#### 1. Number Swapping
**Problem**: LLM confuses similar numbers
```
❌ "ราคา 3.03% เหนือ VWAP" - Actually 43.79%
❌ "ราคา $43.79" - Actually $202.49
```
**Cause**: The LLM saw both 3.03 (ATR%) and 43.79 (VWAP%) and mixed them up

#### 2. Percentile Hallucination
**Problem**: LLM invents percentile values
```
❌ "ซึ่งอยู่ในเปอร์เซ็นไทล์ 75%" - Actually 88%
```
**Cause**: LLM rounded or guessed instead of using exact value

#### 3. Missing Context
**Problem**: LLM omits required elements
```
❌ Required element 'volume' not mentioned
```
**Cause**: Prompt didn't emphasize importance, or token limit reached

#### 4. Wrong Interpretation
**Problem**: Qualitative claim doesn't match quantitative threshold
```
❌ Uncertainty 56.6 interpreted as 'moderate' but should be 'high'
```
**Cause**: LLM used different threshold than defined

## Improving Faithfulness

### 1. Prompt Engineering
- **Emphasize accuracy**: "CRITICAL: Use EXACT numbers from data"
- **Repeat important metrics**: Include them multiple times in prompt
- **Show examples**: Demonstrate correct "narrative + number" style

### 2. Temperature Control
- **Lower temperature** (0.5-0.7) for more factual narratives
- **Higher temperature** (0.8-1.0) for creative style (current setting)
- **Trade-off**: Creativity vs. Accuracy

### 3. Verification Prompts
Add second pass to verify claims:
```python
verify_prompt = f"""
Review this narrative and verify all numbers match the data:
Data: {ground_truth}
Narrative: {report}

Are all numbers accurate? Fix any errors.
"""
```

### 4. Constrained Generation
Use structured output with specific fields:
```python
{
  "uncertainty": 56.6,
  "uncertainty_percentile": 88,
  "atr_percent": 3.03,
  "vwap_percent": 43.79,
  "narrative": "..."
}
```

## Architecture

### Class: FaithfulnessScorer

#### Methods
- `score_narrative()` - Main scoring method
- `_check_numeric_accuracy()` - Verify numbers
- `_check_percentile_accuracy()` - Verify percentiles
- `_check_news_citations()` - Verify citations
- `_check_required_coverage()` - Verify all elements present
- `_check_interpretation_accuracy()` - Verify qualitative claims
- `format_score_report()` - Format human-readable report

#### Data Classes
```python
@dataclass
class FaithfulnessScore:
    overall_score: float              # 0-100
    metric_scores: Dict[str, float]   # Individual metric scores
    violations: List[str]             # Faithfulness violations
    verified_claims: List[str]        # Verified factual claims
    missing_required: List[str]       # Required elements not mentioned
```

## Testing

### Unit Tests
```bash
python -m pytest tests/test_faithfulness_scorer.py -v
```

### Integration Test
```bash
python tests/test_pdf_generation.py --ticker NVDA19
# Check console output for faithfulness report
```

## Future Enhancements

### 1. Automatic Correction
Regenerate narrative when faithfulness score < 80:
```python
if faithfulness_score.overall_score < 80:
    # Regenerate with stricter prompt
    prompt += "\n\nCRITICAL ERRORS FOUND. Use these EXACT numbers: ..."
    report = llm.invoke(prompt)
```

### 2. Citation Context Checking
Verify that cited news actually supports the claim:
```python
# Check: Does news [1] really mention "earnings beat"?
claim = "Apple earnings beat expectations [1]"
news_1_title = "Apple forecasts double-digit iPhone growth..."
# Use LLM to verify semantic alignment
```

### 3. Mathematical Consistency
Check derived claims match calculations:
```python
# If ATR = 6.14 and price = $202.49
# Then ATR% should be 3.03%, not 3.5%
claimed_atr_pct = extract_atr_percent(narrative)
calculated_atr_pct = (atr / price) * 100
assert abs(claimed_atr_pct - calculated_atr_pct) < 0.1
```

### 4. Confidence Scoring
Add confidence to each verification:
```python
{
    "claim": "ราคา 43.8% เหนือ VWAP",
    "verified": True,
    "confidence": 0.95,  # Pattern match + numeric match
    "method": "regex_extraction + tolerance_check"
}
```

## Best Practices

### 1. Review Violations
Always check violations for high-stakes reports:
```python
if faithfulness_score.overall_score < 90:
    print("⚠️ Review required:")
    for violation in faithfulness_score.violations:
        print(f"  {violation}")
    # Decide: approve, regenerate, or manually correct
```

### 2. Track Over Time
Monitor faithfulness trends:
```python
# Store scores in database
db.save_faithfulness_score(ticker, date, score)

# Analyze trends
avg_score = db.get_avg_faithfulness_score(days=30)
if avg_score < 85:
    alert("Faithfulness declining - review prompts")
```

### 3. Domain-Specific Patterns
Add patterns for your specific metrics:
```python
# For Thai financial terms
patterns = {
    'market_cap': [r'มูลค่าตลาด[^0-9]*?(\d+\.?\d*)', ...],
    'dividend_yield': [r'เงินปันผล[^0-9]*?(\d+\.?\d*)%', ...],
    ...
}
```

### 4. Human-in-the-Loop
For critical reports, require human approval:
```python
if faithfulness_score.overall_score < 85 or len(violations) > 2:
    # Trigger manual review workflow
    send_to_approval_queue(report, score)
else:
    # Auto-approve
    publish_report(report)
```

## Limitations

1. **Pattern Matching**: May miss claims phrased differently
2. **Thai Language**: Regex patterns may not catch all Thai variations
3. **Context Understanding**: Can't verify semantic correctness (e.g., "bullish" interpretation)
4. **Implicit Claims**: Can't detect omitted information
5. **Cross-Claim Consistency**: Doesn't check if multiple claims contradict each other

## References

- **RAGAS Faithfulness**: https://docs.ragas.io/en/latest/concepts/metrics/faithfulness.html
- **LLM Hallucination Detection**: https://arxiv.org/abs/2305.13534
- **Financial NLP Evaluation**: https://aclanthology.org/2023.findings-acl.1/

## Changelog

### v1.0.0 (2025-11-01)
- ✅ Initial implementation
- ✅ 5 metric scoring system
- ✅ Thai language pattern matching
- ✅ Integration with agent workflow
- ✅ Comprehensive test coverage
