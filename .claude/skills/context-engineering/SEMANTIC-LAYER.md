# Semantic Layer Architecture

**Reference**: The core pattern for accurate LLM data processing.

---

## The Problem

> "LLMs frequently respond with hallucinations. SQL queries could run but retrieved wrong data."
> — M1 Finance (before semantic layer)

Direct LLM processing of numeric data leads to:
- **~30% accuracy** on business questions
- Hallucinated numbers and statistics
- Inconsistent interpretations
- Unreliable outputs

---

## The Solution: Three-Layer Architecture

```
Layer 1 (Code): Numeric calculations → Ground truth values
    ↓
Layer 2 (Code): Semantic classification → Categorical labels
    ↓
Layer 3 (LLM): Narrative synthesis → Natural language
    ↓
Layer 4 (Code): Post-processing → Inject exact values
```

**Result**: 83% accuracy (dbt Labs benchmark)

---

## Layer 1: Numeric Calculations (Code)

**Purpose**: Establish ground truth values through deterministic computation.

```python
# src/analysis/market_analyzer.py
def calculate_market_conditions(self, indicators: dict) -> dict:
    """Layer 1: Pure numeric calculations."""
    current_price = indicators.get('current_price', 0)
    vwap = indicators.get('vwap', 0)

    # Deterministic calculation
    price_vs_vwap_pct = ((current_price - vwap) / vwap * 100) if vwap > 0 else 0

    return {
        'price_vs_vwap_pct': price_vs_vwap_pct,
        'volume_ratio': indicators.get('volume', 0) / indicators.get('avg_volume', 1),
        'atr_pct': (indicators.get('atr', 0) / current_price * 100) if current_price > 0 else 0,
    }
```

**Key Principle**: Never let LLM calculate numbers. All numeric values come from code.

---

## Layer 2: Semantic Classification (Code)

**Purpose**: Convert numbers to categorical labels that LLM can reason about.

```python
# src/analysis/semantic_state_generator.py
@dataclass
class RiskRegime:
    level: str      # "LOW", "MODERATE", "HIGH", "EXTREME"
    drivers: list   # ["volatility", "uncertainty"]

@dataclass
class MomentumState:
    direction: str  # "BULLISH", "BEARISH", "NEUTRAL"
    strength: str   # "STRONG", "MODERATE", "WEAK"

def classify_risk_regime(self, indicators: dict) -> RiskRegime:
    """Layer 2: Semantic classification."""
    uncertainty = indicators.get('uncertainty_score', 0)
    atr_pct = indicators.get('atr_pct', 0)

    # Threshold-based classification
    if uncertainty > 70 or atr_pct > 5:
        return RiskRegime(level="EXTREME", drivers=["volatility"])
    elif uncertainty > 50 or atr_pct > 3:
        return RiskRegime(level="HIGH", drivers=["uncertainty"])
    elif uncertainty > 30 or atr_pct > 2:
        return RiskRegime(level="MODERATE", drivers=[])
    else:
        return RiskRegime(level="LOW", drivers=[])
```

**Key Principle**: Categorical labels are easier for LLM to reason about than raw numbers.

---

## Layer 3: Narrative Synthesis (LLM)

**Purpose**: Generate natural language narrative from semantic context.

```python
# src/report/context_builder.py
def prepare_context(self, **kwargs) -> str:
    """Layer 3: Build context for LLM narrative synthesis."""
    sections = []

    # Semantic states (not raw numbers)
    semantic_states = self.semantic_generator.generate_all_states(kwargs['indicators'])
    sections.append(f"Risk Regime: {semantic_states.risk.level}")
    sections.append(f"Momentum: {semantic_states.momentum.direction} ({semantic_states.momentum.strength})")

    # Formatted data (structured, not raw)
    sections.append(self.formatter.format_indicators(kwargs['indicators']))

    return "\n".join(sections)
```

**Prompt Template**:
```
Given these semantic states and formatted data, generate a narrative analysis.

Risk Regime: {risk_level}
Momentum: {momentum_direction} ({momentum_strength})

Use placeholders for exact numbers: {{RSI}}, {{ATR_PCT}}, {{PRICE_CHANGE}}

Generate a flowing narrative in Thai language.
```

**Key Principle**: LLM receives categorical labels and produces narrative. No calculations.

---

## Layer 4: Post-Processing (Code)

**Purpose**: Inject exact values into narrative, ensuring numeric accuracy.

```python
# src/report/number_injector.py
def inject_deterministic_numbers(
    self,
    report: str,
    ground_truth: dict,
    indicators: dict,
    percentiles: dict,
    ticker_data: dict,
    comparative_insights: dict,
    strategy_performance: dict = None
) -> str:
    """Layer 4: Replace placeholders with exact values."""
    replacements = {
        '{{RSI}}': f"{indicators.get('rsi', 0):.0f}",
        '{{ATR_PCT}}': f"{ground_truth.get('atr_pct', 0):.1f}%",
        '{{PRICE_CHANGE}}': f"{ticker_data.get('price_change_pct', 0):.2f}%",
        '{{VWAP_PCT}}': f"{ground_truth.get('vwap_pct', 0):.2f}%",
    }

    for placeholder, value in replacements.items():
        report = report.replace(placeholder, value)

    return report
```

**Key Principle**: Single source of truth for all placeholder definitions.

---

## Implementation in DR Reports

### Current Architecture

```
src/report/
├── report_generator_simple.py   # Orchestrates all layers
├── context_builder.py           # Layer 2-3 (semantic context)
├── prompt_builder.py            # Layer 3 (prompt assembly)
└── number_injector.py           # Layer 4 (post-processing)

src/analysis/
├── market_analyzer.py           # Layer 1 (numeric calculations)
└── semantic_state_generator.py  # Layer 2 (semantic classification)
```

### Data Flow

```
1. Raw Data (Aurora) → Market Analyzer (Layer 1)
   - Calculates: price_vs_vwap_pct, volume_ratio, atr_pct

2. Indicators → Semantic Generator (Layer 2)
   - Classifies: RiskRegime, MomentumState, TrendState

3. Semantic States → Context Builder (Layer 3)
   - Formats: Structured context string

4. Context → Prompt Builder → LLM
   - Generates: Narrative with {{PLACEHOLDERS}}

5. LLM Output → Number Injector (Layer 4)
   - Injects: Exact values into narrative
```

---

## Benefits

| Benefit | Before | After |
|---------|--------|-------|
| Accuracy | ~30% | 83% |
| Consistency | Variable | Deterministic numbers |
| Hallucinations | Frequent | Virtually eliminated |
| Maintainability | Hard to debug | Clear layer separation |

---

## Anti-Patterns

### 1. Mixing Layers

```python
# ❌ Bad: LLM calculates
prompt = f"Calculate the RSI and analyze: {raw_data}"

# ✅ Good: Code calculates, LLM analyzes
rsi = calculate_rsi(raw_data)  # Layer 1
prompt = f"RSI is {rsi} (classify as overbought/neutral/oversold)"  # Layer 2-3
```

### 2. Skipping Post-Processing

```python
# ❌ Bad: Trust LLM numbers
report = llm.invoke(prompt)
return report

# ✅ Good: Inject verified values
report = llm.invoke(prompt)
report = number_injector.inject(report, ground_truth)  # Layer 4
return report
```

### 3. Raw Numbers in Context

```python
# ❌ Bad: Raw numeric data
context = f"RSI: 72.3, ATR: 2.5%, Volume: 1234567"

# ✅ Good: Semantic interpretation
context = f"RSI: 72 (OVERBOUGHT), Volatility: MODERATE (ATR 2.5%)"
```

---

## References

- [SKILL.md](SKILL.md) - Overview
- [TOKEN-OPTIMIZATION.md](TOKEN-OPTIMIZATION.md) - Token efficiency
- [HALLUCINATION-PREVENTION.md](HALLUCINATION-PREVENTION.md) - Accuracy patterns
- [dbt Labs Semantic Layer](https://www.getdbt.com/blog/semantic-layer-as-the-data-interface-for-llms)
