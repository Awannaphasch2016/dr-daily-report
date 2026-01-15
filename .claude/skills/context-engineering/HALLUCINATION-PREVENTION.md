# Hallucination Prevention

**Reference**: Patterns for ensuring accurate, grounded LLM outputs.

---

## The Problem

> "LLMs frequently respond with hallucinations—inventing numbers, statistics, and facts that don't exist in the source data."

### Common Hallucination Types

| Type | Example | Risk Level |
|------|---------|------------|
| **Numeric** | "Stock rose 15.3%" (actual: 12.1%) | HIGH |
| **Attribution** | "According to Reuters..." (no source) | MEDIUM |
| **Temporal** | "Yesterday's earnings..." (wrong date) | MEDIUM |
| **Factual** | "Company founded in 1985" (wrong year) | HIGH |

---

## Pattern 1: Placeholder Injection

**Problem**: LLM generates approximate numbers.

**Solution**: Use placeholders for all numeric values, inject exact values post-processing.

### Implementation

```python
# In prompt template
TEMPLATE = """
Analyze the stock. Use these placeholders for exact values:
- Price change: {{PRICE_CHANGE}}
- RSI: {{RSI}}
- Volatility: {{ATR_PCT}}

Generate narrative using placeholders. DO NOT invent numbers.
"""

# Post-processing
def inject_values(report: str, data: dict) -> str:
    replacements = {
        '{{PRICE_CHANGE}}': f"{data['price_change']:.2f}%",
        '{{RSI}}': f"{data['rsi']:.0f}",
        '{{ATR_PCT}}': f"{data['atr_pct']:.1f}%",
    }
    for placeholder, value in replacements.items():
        report = report.replace(placeholder, value)
    return report
```

### Placeholder Catalog

```python
# src/report/number_injector.py - Single source of truth
PLACEHOLDER_DEFINITIONS = {
    # Price placeholders
    '{{PRICE}}': 'Current price',
    '{{PRICE_CHANGE}}': 'Price change percentage',
    '{{PRICE_CHANGE_ABS}}': 'Absolute price change',

    # Technical indicators
    '{{RSI}}': 'Relative Strength Index',
    '{{ATR_PCT}}': 'ATR as percentage of price',
    '{{VWAP_PCT}}': 'Price vs VWAP percentage',

    # Volume
    '{{VOLUME}}': 'Trading volume',
    '{{VOLUME_RATIO}}': 'Volume vs average ratio',
}
```

---

## Pattern 2: Semantic Grounding

**Problem**: LLM misinterprets numeric thresholds.

**Solution**: Provide semantic classification alongside numbers.

### Before (Ungrounded)

```
RSI: 72
→ LLM might say "neutral momentum" (incorrect)
```

### After (Grounded)

```
RSI: 72 (OVERBOUGHT - above 70 threshold)
→ LLM correctly identifies overbought condition
```

### Implementation

```python
def ground_indicator(name: str, value: float) -> str:
    """Provide semantic grounding for indicators."""
    thresholds = {
        'rsi': [
            (30, 'OVERSOLD'),
            (70, 'NEUTRAL'),
            (100, 'OVERBOUGHT'),
        ],
        'atr_pct': [
            (2, 'LOW'),
            (4, 'MODERATE'),
            (100, 'HIGH'),
        ],
    }

    for threshold, label in thresholds.get(name, []):
        if value <= threshold:
            return f"{value:.1f} ({label})"

    return f"{value:.1f}"
```

---

## Pattern 3: Citation Requirements

**Problem**: LLM invents sources or attributions.

**Solution**: Require explicit citation of provided sources.

### Implementation

```python
TEMPLATE = """
You have access to these sources ONLY:
1. Technical Data: {technical_summary}
2. News: {news_items}

RULES:
- Only cite information from the sources above
- Use format: "According to [source 1/2]..."
- If information not in sources, say "Data not available"
- DO NOT invent sources or attributions
"""
```

---

## Pattern 4: Output Validation

**Problem**: Hallucinations slip through despite precautions.

**Solution**: Validate output against ground truth before returning.

### Implementation

```python
def validate_report(report: str, ground_truth: dict) -> tuple[bool, list[str]]:
    """Validate report against ground truth."""
    issues = []

    # Check for unreplaced placeholders
    if '{{' in report and '}}' in report:
        issues.append("Unreplaced placeholders found")

    # Check for invented numbers (not from ground truth)
    numbers_in_report = extract_numbers(report)
    valid_numbers = set(ground_truth.values())

    for num in numbers_in_report:
        if num not in valid_numbers and not is_common_number(num):
            issues.append(f"Potentially hallucinated number: {num}")

    return len(issues) == 0, issues
```

### Malformed Placeholder Detection

```python
def fix_malformed_placeholders(report: str) -> str:
    """Fix common placeholder malformations."""
    # LLM sometimes adds extra characters
    patterns = [
        (r'\{\{(\w+)\}\}\.', r'{{\1}}'),  # {{X}}. → {{X}}
        (r'\{\{(\w+)\}\}%', r'{{\1}}'),   # {{X}}% → {{X}}
        (r'\{ \{(\w+)\} \}', r'{{\1}}'),  # { {X} } → {{X}}
    ]

    for pattern, replacement in patterns:
        report = re.sub(pattern, replacement, report)

    return report
```

---

## Pattern 5: Constrained Generation

**Problem**: LLM generates outside expected bounds.

**Solution**: Constrain output format and validate structure.

### Implementation

```python
from pydantic import BaseModel, Field, validator

class StockAnalysis(BaseModel):
    """Constrained output schema."""
    trend: Literal["BULLISH", "BEARISH", "NEUTRAL"]
    risk_level: Literal["LOW", "MODERATE", "HIGH", "EXTREME"]
    recommendation: Literal["BUY", "HOLD", "SELL"]
    confidence: float = Field(ge=0.0, le=1.0)

    @validator('confidence')
    def validate_confidence(cls, v):
        if v < 0 or v > 1:
            raise ValueError("Confidence must be between 0 and 1")
        return v
```

### Structured Output Prompt

```python
TEMPLATE = """
Analyze the stock and return JSON matching this schema:
{
    "trend": "BULLISH|BEARISH|NEUTRAL",
    "risk_level": "LOW|MODERATE|HIGH|EXTREME",
    "recommendation": "BUY|HOLD|SELL",
    "confidence": 0.0-1.0
}

Data: {context}

Return ONLY valid JSON, no explanation.
"""
```

---

## Pattern 6: Explicit Uncertainty

**Problem**: LLM presents uncertain information as fact.

**Solution**: Require explicit uncertainty markers.

### Implementation

```python
TEMPLATE = """
When analyzing, use these uncertainty markers:
- CERTAIN: Based on provided data
- LIKELY: Reasonable inference from data
- UNCERTAIN: Limited data, low confidence

Example: "The stock is CERTAIN in an uptrend (based on MA crossover),
         LIKELY to continue (based on volume), but UNCERTAIN about
         target price (insufficient data)."
"""
```

---

## Hallucination Prevention Checklist

Before deploying a prompt:

- [ ] All numbers use placeholders?
- [ ] Semantic grounding provided for thresholds?
- [ ] Citation requirements explicit?
- [ ] Output validation implemented?
- [ ] Schema constraints defined?
- [ ] Uncertainty markers required?
- [ ] Malformed placeholder handling?

---

## Monitoring

### Metrics to Track

| Metric | Target | Action if Exceeded |
|--------|--------|-------------------|
| Unreplaced placeholders | 0% | Fix template |
| Validation failures | <5% | Review prompts |
| User-reported inaccuracies | <1% | Investigate |

### Logging

```python
def log_hallucination_metrics(report: str, ground_truth: dict):
    """Track hallucination indicators."""
    is_valid, issues = validate_report(report, ground_truth)

    if not is_valid:
        logger.warning(f"Potential hallucinations: {issues}")

    # Track for analysis
    metrics.increment('report.validation.total')
    if not is_valid:
        metrics.increment('report.validation.failed')
```

---

## References

- [SKILL.md](SKILL.md) - Overview
- [SEMANTIC-LAYER.md](SEMANTIC-LAYER.md) - Core architecture
- [TOKEN-OPTIMIZATION.md](TOKEN-OPTIMIZATION.md) - Efficiency patterns
- [src/report/number_injector.py](../../../src/report/number_injector.py) - Implementation
