# Report Quality Scoring System

**Version**: 2.0.0
**Last Updated**: 2025-11-01

## Overview

The DR Daily Report system uses a comprehensive **5-dimension scoring system** to evaluate report quality. Each dimension measures a different aspect of quality, from factual accuracy to format compliance to operational performance.

### The Five Scorers

| Scorer | What It Measures | Weight in Overall Quality |
|--------|------------------|---------------------------|
| **Faithfulness** | Factual accuracy - "Are claims accurate?" | 50% |
| **Completeness** | Analytical coverage - "Are all dimensions covered?" | 20% |
| **Reasoning Quality** | Explanation quality - "Is reasoning clear?" | 20% |
| **Compliance** | Format adherence - "Does it follow required format?" | 10% |
| **QoS** | Operational performance - "Is the system performing well?" | N/A (separate) |

### Overall Quality Score

Content quality is calculated as:

```python
overall_quality = (
    faithfulness_score * 0.50 +
    completeness_score * 0.20 +
    reasoning_quality_score * 0.20 +
    compliance_score * 0.10
)
```

QoS is tracked separately as an **operational metric** (not content quality).

---

## Architecture

### How Scorers Work Together

```
┌────────────────────────────────────────────────────────────┐
│  Report Generation (LLM + Data)                            │
│  ↓                                                         │
│  Generated Thai Narrative                                  │
└────────────────────────────────────────────────────────────┘
                    ↓
┌────────────────────────────────────────────────────────────┐
│  Content Quality Scorers (Sequential)                      │
│                                                            │
│  1. Faithfulness Scorer                                    │
│     → Verify all numbers match source data                 │
│     → Check percentile accuracy                            │
│     → Verify news citations                                │
│                                                            │
│  2. Completeness Scorer                                    │
│     → Check all analytical dimensions covered              │
│     → Verify temporal context included                     │
│     → Check narrative structure present                    │
│                                                            │
│  3. Reasoning Quality Scorer                               │
│     → Check clarity of explanations                        │
│     → Verify specificity (not generic)                     │
│     → Check alignment with data                            │
│                                                            │
│  4. Compliance Scorer                                      │
│     → Verify all 4 sections present                        │
│     → Check format compliance (no tables/lists)            │
│     → Verify required content elements                     │
└────────────────────────────────────────────────────────────┘
                    ↓
┌────────────────────────────────────────────────────────────┐
│  Operational Performance Scorer (Parallel)                 │
│                                                            │
│  5. QoS Scorer                                             │
│     → Track latency (timing metrics)                       │
│     → Calculate cost (LLM tokens)                          │
│     → Measure reliability (error rate)                     │
└────────────────────────────────────────────────────────────┘
                    ↓
┌────────────────────────────────────────────────────────────┐
│  Final Scores                                              │
│  • Overall Content Quality: 0-100                          │
│  • Individual Dimension Scores: 0-100 each                 │
│  • QoS Score: 0-100 (operational)                          │
└────────────────────────────────────────────────────────────┘
```

### Integration with Agent Workflow

All scorers are automatically invoked after report generation:

```python
# In agent.py - generate_report method
state["report"] = report

# Score narrative (automatically run all scorers)
faithfulness_score = self._score_narrative_faithfulness(...)
completeness_score = self._score_narrative_completeness(...)
reasoning_quality_score = self._score_reasoning_quality(...)
compliance_score = self._score_compliance(...)
qos_score = self._score_qos(...)

# Store in state
state["faithfulness_score"] = faithfulness_score
state["completeness_score"] = completeness_score
state["reasoning_quality_score"] = reasoning_quality_score
state["compliance_score"] = compliance_score
state["qos_score"] = qos_score
```

---

## 1. Faithfulness Scorer

**Purpose**: Measures factual accuracy - prevents hallucinations and ensures all claims match source data.

### What It Measures

#### Dimensions (Total Weight: 100%)

1. **Numeric Accuracy** (30%)
   - Verifies all numbers in narrative match source data
   - Tolerance: 2% for metrics, 0.5% for prices
   - Examples: uncertainty score, ATR%, VWAP%, volume ratio, RSI, current price

2. **Percentile Accuracy** (25%)
   - Verifies percentile claims match historical calculations
   - Tolerance: Within 5 percentage points
   - Pattern: "เปอร์เซ็นไทล์ 88%" must match actual percentile

3. **News Citation Accuracy** (20%)
   - Verifies news references [1], [2], [3] are valid
   - Citation [1] must reference first news item
   - Invalid citations (e.g., [5] when only 3 news items) are flagged

4. **Interpretation Accuracy** (25%)
   - Verifies qualitative interpretations match quantitative thresholds
   - Uncertainty: 0-25 (stable), 25-50 (moderate), 50-75 (high), 75-100 (extreme)
   - VWAP: >15% (strong buying), >5% (buying), -5 to 5% (neutral), <-5% (selling)

### How It Works

**Ground Truth Preparation**:
```python
ground_truth = {
    'uncertainty_score': 56.6,      # From indicators
    'atr_pct': 3.03,                # ATR / current_price * 100
    'vwap_pct': 43.79,              # (price - vwap) / vwap * 100
    'volume_ratio': 1.0,            # volume / volume_sma
}
```

**Pattern Matching**:
```python
# Extract claims from Thai narrative
r'ความไม่แน่นอน[^0-9]*?(\d+\.?\d*)'  # "ความไม่แน่นอน 56.6"
r'ATR[^0-9]*?(\d+\.?\d*)%'           # "ATR 3.03%"
r'เปอร์เซ็นไทล์[^0-9]*?(\d+\.?\d*)%' # "เปอร์เซ็นไทล์ 88%"
```

**Verification**:
```python
is_accurate = abs(claimed - actual) <= (actual * tolerance)
```

### Score Interpretation

- **90-100**: Excellent - Narrative is highly accurate
- **80-89**: Good - Minor inaccuracies, but trustworthy
- **70-79**: Fair - Some issues, needs review
- **60-69**: Poor - Significant inaccuracies found
- **<60**: Failed - Major hallucinations

### Common Violations

#### Number Swapping
```
❌ "ราคา 3.03% เหนือ VWAP" - Actually 43.79%
```
**Cause**: LLM mixed up similar numbers (3.03 ATR% vs 43.79 VWAP%)

#### Percentile Hallucination
```
❌ "ซึ่งอยู่ในเปอร์เซ็นไทล์ 75%" - Actually 88%
```
**Cause**: LLM rounded or guessed instead of using exact value

#### Wrong Interpretation
```
❌ Uncertainty 56.6 interpreted as 'moderate' but should be 'high'
```
**Cause**: LLM used different threshold than defined

### Example Output

```
================================================================================
FAITHFULNESS SCORE REPORT
================================================================================

📊 Overall Faithfulness Score: 91.7/100

Metric Breakdown:
  ⚠️ numeric_accuracy: 66.7/100
  ✅ percentile_accuracy: 100.0/100
  ✅ news_citation_accuracy: 100.0/100
  ✅ interpretation_accuracy: 100.0/100

⚠️ Faithfulness Violations:
  ❌ vwap_pct mismatch: narrative claims 3.03, actual is 43.79
  ❌ current_price mismatch: narrative claims 43.79, actual is 202.49

✅ Verified Claims: 19

================================================================================
```

---

## 2. Completeness Scorer

**Purpose**: Measures analytical comprehensiveness - checks if report covers all necessary dimensions.

### What It Measures

#### Dimensions (Total Weight: 100%)

1. **Context Completeness** (20%)
   - Company identity (name/ticker mentioned)
   - Current state (current price mentioned)
   - Market context (sector/industry if available)
   - Market positioning (52-week high/low or market cap if available)

2. **Analysis Dimension Completeness** (25%)
   - Technical analysis (RSI, MACD, SMA, Bollinger Bands)
   - Volatility/risk assessment (uncertainty score OR ATR)
   - Market sentiment (VWAP context OR news sentiment)
   - Volume analysis
   - Fundamental context (P/E, EPS, growth if available)
   - Historical context (percentile analysis or historical comparison)

3. **Temporal Completeness** (15%)
   - Current state (current price/indicators)
   - Historical comparison (percentile context OR comparison)
   - Trend direction (up/down/flat or momentum)
   - Timeframe awareness (date mentioned or implied)

4. **Actionability Completeness** (20%)
   - Clear recommendation (BUY/SELL/HOLD explicitly stated)
   - Reasoning provided (explanation for WHY)
   - Risk warnings (mention of risks or concerns)
   - Key decision factors (what drove recommendation)

5. **Narrative Structure Completeness** (10%)
   - Story/context section (📖 section)
   - Analysis/insights section (💡 section)
   - Recommendation section (🎯 section)
   - Risk section (⚠️ section)

6. **Quantitative Context Completeness** (10%)
   - Percentile context when numbers mentioned
   - Threshold interpretation matches quantitative thresholds
   - Comparative context (numbers compared to benchmarks)

### Score Interpretation

- **90-100**: Excellent - Report covers all essential dimensions
- **80-89**: Good - Minor gaps, but generally complete
- **70-79**: Fair - Some important dimensions missing
- **60-69**: Poor - Significant gaps in coverage
- **<60**: Failed - Report is incomplete

### Common Missing Elements

#### Missing Fundamental Analysis
```
❌ Fundamental analysis not mentioned (data available but not used)
```
**Cause**: LLM focused on technical analysis only

#### Missing Historical Context
```
❌ Historical context (percentile analysis) not mentioned
```
**Cause**: Percentile data available but not incorporated

#### Missing Risk Warnings
```
❌ Risk warnings not mentioned
```
**Cause**: LLM focused on positive aspects only

### Example Output

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

---

## 3. Reasoning Quality Scorer

**Purpose**: Measures explanation quality - evaluates how well the narrative explains and justifies claims.

### What It Measures

#### Dimensions (Total Weight: 100%)

1. **Clarity** (20%)
   - Minimizes vague terms (maybe, perhaps, might be)
   - Uses clear cause-effect relationships (because, therefore, ทำให้)
   - Structured format (sections, formatting)
   - Provides explanations (not just statements)
   - Appropriate sentence length

2. **Coverage** (20%)
   - Explains multiple dimensions (technical, volatility, sentiment, volume, historical, fundamental)
   - Explains WHY (not just WHAT)
   - Covers aspects relevant to conclusion

3. **Specificity** (20%)
   - Minimizes generic language (generally, usually, typically)
   - Includes specific numbers/data points
   - Uses specific comparisons (compared to, เทียบกับ)
   - References specific entities/tickers

4. **Alignment** (15%)
   - Percentile claims match actual data
   - Uncertainty interpretations match thresholds
   - VWAP interpretations match actual values

5. **Minimality** (15%)
   - Optimal length (200-800 words)
   - Minimizes repetition
   - Avoids redundant phrases
   - Minimizes filler words

6. **Consistency** (10%)
   - No contradictions
   - Single recommendation (BUY/SELL/HOLD)
   - Consistent risk assessment

### Score Interpretation

- **90-100**: Excellent - Reasoning is clear, specific, and well-aligned
- **80-89**: Good - Minor issues, but generally high quality
- **70-79**: Fair - Some clarity or specificity issues
- **60-69**: Poor - Significant reasoning quality problems
- **<60**: Failed - Reasoning is unclear or inconsistent

### Common Issues

#### Low Clarity
```
❌ Too many vague terms reduce clarity
❌ Missing clear cause-effect relationships
```
**Solution**: Use specific language and explicit cause-effect markers

#### Low Specificity
```
❌ Too many generic phrases (reduce specificity)
❌ Lacks specific numbers/data points
```
**Solution**: Include specific numbers and comparisons

#### Low Alignment
```
❌ Uncertainty interpretation doesn't align with score
❌ Only 2/5 percentile claims aligned
```
**Solution**: Ensure interpretations match actual data values

### Example Output

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

❌ Reasoning Quality Issues:
  ⚠️ Sentences slightly long (650 words)

================================================================================
```

---

## 4. Compliance Scorer

**Purpose**: Measures format adherence - checks if report follows required structure, format, and policy constraints.

### What It Measures

#### Dimensions (Total Weight: 100%)

1. **Structure Compliance** (30%)
   - All 4 sections present (📖, 💡, 🎯, ⚠️)
   - Sections in correct order
   - Section lengths appropriate (story: 2-3 sentences, etc.)

2. **Content Compliance** (25%)
   - All 4 market condition metrics mentioned (uncertainty, ATR%, VWAP%, volume ratio)
   - Metrics in story section
   - Percentile context used when available
   - Specific numbers included

3. **Format Compliance** (15%)
   - NO tables
   - NO numbered lists
   - NO bullet points
   - NO strategy names (e.g., "SMA crossing")

4. **Length Compliance** (10%)
   - Total length under 12-15 lines
   - Word count in reasonable range (200-1200 words)
   - Story section 2-3 sentences

5. **Language Compliance** (10%)
   - Written in Thai
   - Narrative flow (cause-effect relationships)
   - Conversational tone

6. **Citation Compliance** (10%)
   - Citations follow [1], [2] format
   - Valid citations (not [5] when only 3 news items)
   - No forced citations (OK per policy)

### Score Interpretation

- **90-100**: Excellent - Report fully complies with format/policy
- **80-89**: Good - Minor violations, mostly compliant
- **70-79**: Fair - Some format/structure issues
- **60-69**: Poor - Significant compliance violations
- **<60**: Failed - Report doesn't follow required format

### Common Violations

#### Missing Sections
```
❌ Missing required section: Risk Section (⚠️)
```
**Solution**: Ensure all 4 sections are present

#### Format Violations
```
❌ Insights section (💡) contains numbered lists (prohibited)
❌ Contains tables (prohibited)
```
**Solution**: Use narrative style, not lists/tables

#### Content Missing
```
❌ Missing required metric: ATR
❌ Story section should include all 4 metrics, found 2
```
**Solution**: Include all 4 market condition metrics

### Example Output

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
  ✅ All 4 sections present in correct order
  ✅ All 4 required metrics mentioned
  ✅ No tables or lists found
  ✅ Written in Thai with narrative flow

❌ Compliance Violations:
  ⚠️ Story section should be 2-3 sentences (found 4)

================================================================================
```

---

## 5. QoS Scorer

**Purpose**: Measures operational performance - tracks system latency, cost efficiency, reliability, and scalability.

### What It Measures

#### Dimensions (Total Weight: 100%)

1. **Latency** (25%)
   - Data fetch latency
   - News fetch latency
   - Technical analysis latency
   - Chart generation latency
   - LLM generation latency
   - Scoring latency
   - Total end-to-end latency
   - **Thresholds**: <5s (excellent), 5-10s (good), 10-20s (acceptable), >20s (poor)

2. **Cost Efficiency** (20%)
   - LLM token usage (input/output)
   - LLM API cost (estimated or actual)
   - Database operation cost
   - External API calls
   - **Thresholds**: <$0.05 (excellent), $0.05-0.10 (good), $0.10-0.20 (acceptable), >$0.20 (poor)

3. **Determinism** (15%)
   - Data fetch consistency
   - Technical analysis consistency
   - Database query consistency
   - **Note**: LLM output variance NOT penalized (temperature is intentional)

4. **Reliability** (20%)
   - Success rate
   - Error rate
   - Partial success rate
   - Timeout rate
   - **Scoring**: No errors (100), error occurred (30), very high latency (>60s) (-20)

5. **Resource Efficiency** (10%)
   - Database query count (<5 queries: +0, 5-10: -5, >10: -15)
   - LLM call efficiency (1-2 calls: +0, >2 calls: -10)
   - Cache hit rate

6. **Scalability** (10%)
   - Latency trends (performance degradation over time)
   - Concurrent request handling (inferred)
   - Throughput (reports per unit time)

### Overall Score Calculation

```
Overall QoS Score = (
    Latency Score × 0.25 +
    Cost Efficiency Score × 0.20 +
    Determinism Score × 0.15 +
    Reliability Score × 0.20 +
    Resource Efficiency Score × 0.10 +
    Scalability Score × 0.10
)
```

### Score Interpretation

- **90-100**: Excellent - System performs optimally
- **80-89**: Good - Minor optimizations possible
- **70-79**: Acceptable - Some improvements needed
- **60-69**: Needs Improvement - Significant optimization required
- **<60**: Poor - Critical issues need immediate attention

### Example Output

```
======================================================================
QoS SCORE REPORT
======================================================================
Overall QoS Score: 85.5/100

Dimension Scores:
----------------------------------------------------------------------
  Latency                 :  90.0/100 (Excellent)
  Cost Efficiency         :  85.0/100 (Good)
  Determinism             :  90.0/100 (Excellent)
  Reliability             : 100.0/100 (Excellent)
  Resource Efficiency     :  85.0/100 (Good)
  Scalability             :  75.0/100 (Acceptable)

----------------------------------------------------------------------
Metrics:
----------------------------------------------------------------------
  Timing (seconds):
    data_fetch            :   1.20s
    news_fetch            :   2.50s
    technical_analysis    :   1.80s
    chart_generation      :   3.20s
    llm_generation        :   4.50s
    scoring               :   0.80s
    total                 :  14.00s

  Costs (USD):
    LLM Estimated Cost:     $0.000080
    Input Tokens:           3,500
    Output Tokens:          1,200

  Database:
    Query Count:            3
    Cache Hit:              No

----------------------------------------------------------------------
Strengths:
  ✅ Excellent total latency: 14.00s
  ✅ Single LLM call optimized cost
======================================================================
```

---

## Compliance Rules Reference

Reports must follow these structural, content, and format requirements:

### Structure Requirements (CRITICAL)

Reports MUST have exactly 4 sections:

1. **📖 เรื่องราวของหุ้นตัวนี้** (Story Section)
   - Length: 2-3 sentences
   - Required: uncertainty score + ATR% + VWAP% + volume ratio with meanings

2. **💡 สิ่งที่คุณต้องรู้** (Insights Section)
   - Length: 3-4 flowing paragraphs
   - Format: NOT numbered lists, NO tables
   - Required: Continuously reference 4 market condition elements with numbers

3. **🎯 ควรทำอะไรตอนนี้?** (Recommendation Section)
   - Length: 2-3 sentences
   - Required: ONE clear action (BUY MORE/SELL/HOLD) with WHY explanation

4. **⚠️ ระวังอะไร?** (Risk Section)
   - Length: 1-2 key risks
   - Required: Warn about risks using 4 market condition metrics

**Overall Length**: Under 12-15 lines total

### Content Requirements (CRITICAL)

**All 4 Market Condition Metrics** MUST appear throughout narrative:
- Uncertainty score (with context)
- ATR% (with percentile context)
- VWAP% (with percentile context)
- Volume ratio (with percentile context)

**Percentile Context** (CRITICAL when available):
- Format: "RSI 75 ซึ่งอยู่ในเปอร์เซ็นไทล์ 85%"
- Must be woven naturally, not just listed

**Specific Numbers** MUST be included:
- All numbers with specific values
- Numbers should be IN sentences as evidence

**News References** (when applicable):
- Format: [1], [2], [3] citations
- Only when genuinely relevant (don't force)

### Format Prohibitions

- ❌ NO tables
- ❌ NO numbered lists in insights section
- ❌ NO bullet points (use flowing narrative)
- ❌ NO strategy name mention (e.g., "SMA crossing")

### Style Requirements

- **Language**: Written entirely in Thai
- **Tone**: Professional but conversational (like texting friend investor)
- **Format**: Tell STORIES, don't list bullet points
- **Focus**: Explain WHY things matter, not just WHAT they are

---

## Usage

### In Agent Workflow

All scorers run automatically after report generation:

```python
from src.agent import TickerReportAgent

agent = TickerReportAgent()
final_state = agent.graph.invoke({
    'ticker': 'DBS19',
    'messages': []
})

# Access scores
faithfulness_score = final_state.get('faithfulness_score')
completeness_score = final_state.get('completeness_score')
reasoning_quality_score = final_state.get('reasoning_quality_score')
compliance_score = final_state.get('compliance_score')
qos_score = final_state.get('qos_score')
```

### Standalone Usage

Each scorer can be used independently:

```python
from src.faithfulness_scorer import FaithfulnessScorer
from src.completeness_scorer import CompletenessScorer
from src.reasoning_quality_scorer import ReasoningQualityScorer
from src.compliance_scorer import ComplianceScorer
from src.qos_scorer import QoSScorer

# Example: Faithfulness scoring
faithfulness_scorer = FaithfulnessScorer()
score = faithfulness_scorer.score_narrative(
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

print(faithfulness_scorer.format_score_report(score))
```

### API Response Format

Scores are included in API responses:

```json
{
  "faithfulness_score": {
    "overall_score": 91.7,
    "metric_scores": {
      "numeric_accuracy": 66.7,
      "percentile_accuracy": 100.0,
      "news_citation_accuracy": 100.0,
      "interpretation_accuracy": 100.0
    },
    "violations": [
      "vwap_pct mismatch: narrative claims 3.03, actual is 43.79"
    ],
    "verified_claims": 19
  },
  "completeness_score": {...},
  "reasoning_quality_score": {...},
  "compliance_score": {...},
  "qos_score": {...}
}
```

---

## Best Practices

### 1. Review Violations for High-Stakes Reports

Always check violations when scores are low:

```python
if faithfulness_score.overall_score < 90:
    print("⚠️ Review required:")
    for violation in faithfulness_score.violations:
        print(f"  {violation}")
    # Decide: approve, regenerate, or manually correct
```

### 2. Track Scores Over Time

Monitor score trends to identify degradation:

```python
# Store scores in database
db.save_faithfulness_score(ticker, date, score)

# Analyze trends
avg_score = db.get_avg_faithfulness_score(days=30)
if avg_score < 85:
    alert("Faithfulness declining - review prompts")
```

### 3. Use as Deployment Gates

Set minimum thresholds for automated publishing:

```python
# Gate: Only publish if all scores meet thresholds
if (faithfulness_score.overall_score >= 80 and
    completeness_score.overall_score >= 75 and
    reasoning_quality_score.overall_score >= 75 and
    compliance_score.overall_score >= 70):
    # Auto-publish
    publish_report(report)
else:
    # Send to manual review queue
    send_to_approval_queue(report, scores)
```

### 4. Improve Through Prompt Engineering

Enhance scores through better prompts:

**For Faithfulness**:
- "CRITICAL: Use EXACT numbers from data"
- "Show me the data: {ground_truth}"
- Lower temperature (0.5-0.7) for more factual outputs

**For Completeness**:
- "You MUST include all 4 sections: 📖, 💡, 🎯, ⚠️"
- "Cover: technical, volatility, sentiment, volume, fundamental, historical"
- Show examples of complete reports

**For Reasoning Quality**:
- "Use clear cause-effect language (because, therefore, ทำให้)"
- "Include specific numbers, not generic statements"
- "Explain WHY, not just WHAT"

**For Compliance**:
- "NO tables, NO numbered lists, NO bullet points"
- "MUST include all 4 metrics in story section"
- "Write under 12-15 lines total"

### 5. Balance Multiple Dimensions

Don't sacrifice one dimension for another:

```python
# If reasoning quality is high but faithfulness is low, prioritize accuracy
if faithfulness_score.overall_score < 70:
    # Regenerate with focus on accuracy
    regenerate_report(focus='accuracy')

# If both faithfulness and completeness are low, regenerate
if (faithfulness_score.overall_score < 70 and
    completeness_score.overall_score < 70):
    regenerate_report(stricter_prompt=True)
```

---

## Testing

### Unit Tests

```bash
# Test individual scorers
python -m pytest tests/test_faithfulness_scorer.py -v
python -m pytest tests/test_completeness_scorer.py -v
python -m pytest tests/test_reasoning_quality_scorer.py -v
python -m pytest tests/test_compliance_scorer.py -v
python -m pytest tests/test_qos_scorer.py -v
```

### Integration Tests

```bash
# Test full scoring pipeline
python tests/test_pdf_generation.py --ticker NVDA19
python show_scores.py --ticker DBS19
```

---

## Architecture

### Data Classes

All scorers use similar data class structure:

```python
from dataclasses import dataclass
from typing import Dict, List

@dataclass
class FaithfulnessScore:
    overall_score: float              # 0-100
    metric_scores: Dict[str, float]   # Individual metric scores
    violations: List[str]             # Faithfulness violations
    verified_claims: List[str]        # Verified factual claims

@dataclass
class CompletenessScore:
    overall_score: float              # 0-100
    dimension_scores: Dict[str, float]  # Individual dimension scores
    missing_elements: List[str]       # Missing analytical elements
    covered_elements: List[str]       # Successfully covered elements

@dataclass
class ReasoningQualityScore:
    overall_score: float              # 0-100
    dimension_scores: Dict[str, float]  # Individual dimension scores
    issues: List[str]                 # Reasoning quality issues
    strengths: List[str]              # Reasoning quality strengths

@dataclass
class ComplianceScore:
    overall_score: float              # 0-100
    dimension_scores: Dict[str, float]  # Individual dimension scores
    violations: List[str]             # Compliance violations
    compliant_elements: List[str]    # Compliant elements

@dataclass
class QoSScore:
    overall_score: float              # 0-100
    dimension_scores: Dict[str, float]  # Individual dimension scores
    metrics: Dict[str, any]           # Timing, cost, database metrics
    issues: List[str]                 # QoS issues
    strengths: List[str]              # QoS strengths
```

### Scorer Classes

Each scorer follows similar interface:

```python
class BaseScorerInterface:
    def score_narrative(self, narrative: str, **kwargs) -> ScoreDataclass:
        """Main scoring method - returns score dataclass"""
        pass

    def format_score_report(self, score: ScoreDataclass) -> str:
        """Format human-readable report"""
        pass
```

---

## Limitations

### Pattern Matching Limitations
- May miss claims phrased differently than expected patterns
- Thai language regex patterns may not catch all variations
- Synonym detection limited (e.g., "RSI" vs "Relative Strength Index")

### Contextual Understanding Limitations
- Can't verify if coverage is meaningful (just token matching)
- Can't verify semantic correctness of explanations
- Can't detect subtle inconsistencies across claims

### Language-Specific Limitations
- Optimized for Thai language patterns
- May not generalize well to other languages without adaptation

### Data Availability Limitations
- Some metrics only penalize if data exists but is unused
- Can't score what isn't measured (e.g., semantic similarity)

### QoS Limitations
- Scalability inferred from latency, not actual load testing
- Cost estimation depends on model pricing (may need updates)
- Historical comparisons require previous runs

---

## Future Enhancements

### 1. LLM-Based Evaluation

Use LLM to evaluate semantic aspects that pattern matching can't catch:

```python
# Verify semantic correctness
is_meaningful = llm.verify(
    f"Does this mention of RSI provide meaningful analysis?\nText: {narrative}"
)

# Check explanation quality
is_clear = llm.verify(
    f"Is this explanation clear and easy to understand?\nText: {explanation}"
)
```

### 2. Multi-Language Support

Extend scorers to support other languages:

```python
# Language-specific patterns
patterns = {
    'thai': ThaiPatternMatcher(),
    'english': EnglishPatternMatcher(),
    'chinese': ChinesePatternMatcher()
}
```

### 3. Adaptive Scoring

Adjust expectations based on report characteristics:

```python
# Short reports have different expectations
if len(narrative) < 500:
    structure_score = adjust_for_length(structure_score, len(narrative))
```

### 4. Automated Correction

Regenerate reports when scores are too low:

```python
if faithfulness_score.overall_score < 80:
    # Regenerate with stricter prompt including exact numbers
    prompt += "\n\nCRITICAL ERRORS FOUND. Use these EXACT numbers: ..."
    report = llm.invoke(prompt)
```

### 5. Dashboard & Visualization

Visual dashboard for score monitoring:
- Score trends over time
- Dimension breakdowns
- Violation/issue frequency
- Comparative analysis across tickers

---

## References

### Academic Papers
- **RAGAS Framework**: https://docs.ragas.io/en/latest/concepts/metrics/
- **LLM Hallucination Detection**: https://arxiv.org/abs/2305.13534
- **Financial NLP Evaluation**: https://aclanthology.org/2023.findings-acl.1/

### Evaluation Frameworks
- **Answer Completeness**: https://docs.ragas.io/en/latest/concepts/metrics/answer_completeness.html
- **Faithfulness**: https://docs.ragas.io/en/latest/concepts/metrics/faithfulness.html
- **Answer Correctness**: https://docs.ragas.io/en/latest/concepts/metrics/answer_correctness.html

---

## Changelog

### v2.0.0 (2025-11-01)
- ✅ Consolidated 6 separate scoring docs into single comprehensive guide
- ✅ Separated completeness from faithfulness (faithfulness no longer includes "required coverage")
- ✅ Updated faithfulness weights: Numeric 30%, Percentile 25%, News 20%, Interpretation 25%
- ✅ Documented compliance rules reference
- ✅ Added comprehensive usage examples
- ✅ Unified architecture documentation

### v1.0.0 (2025-11-01)
- ✅ Initial implementation of 5 scorers
- ✅ Individual documentation for each scorer
- ✅ Integration with agent workflow
- ✅ Comprehensive test coverage
