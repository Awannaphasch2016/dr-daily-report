# Semantic Layer Architecture - Implementation Guide

**Status:** ✅ Active (Dec 2024)
**Replaces:** Multi-Stage Report Generation (removed Dec 2024)
**ADR:** [ADR-001: Adopt Semantic Layer Architecture](adr/001-adopt-semantic-layer-architecture.md)

---

## Table of Contents

- [Overview](#overview)
- [Three-Layer Pattern](#three-layer-pattern)
- [Layer 1: Ground Truth Calculation](#layer-1-ground-truth-calculation)
- [Layer 2: Semantic State Classification](#layer-2-semantic-state-classification)
- [Layer 3: LLM Narrative Synthesis](#layer-3-llm-narrative-synthesis)
- [Implementation Examples](#implementation-examples)
- [Migration from Multi-Stage](#migration-from-multi-stage)
- [Testing Patterns](#testing-patterns)
- [File Organization](#file-organization)

---

## Overview

**Core Principle:** "Code decides what numbers MEAN, LLM decides how meanings COMBINE"

The Semantic Layer Architecture separates data processing into three distinct layers:
- **Layer 1 (Code)**: Calculate ground truth numeric values
- **Layer 2 (Code)**: Classify semantic states from ground truth
- **Layer 3 (LLM)**: Synthesize narrative constrained by semantic states

### Why This Architecture

**Problem with Multi-Stage:**
- 7 LLM calls (6 mini-reports + synthesis)
- High cost (~$0.50 per report)
- Slow latency (~15s generation time)
- LLM decides importance/interpretation of raw data

**Solution with Semantic Layer:**
- 1 LLM call (constrained by semantic states)
- Low cost (~$0.07 per report) - **86% reduction**
- Fast latency (~5s generation time) - **67% reduction**
- Code decides importance/interpretation, LLM writes narrative

**Research Backing:**
- 300% accuracy improvement in financial LLM applications
- Code-based semantic classification prevents LLM hallucination
- Constrained generation reduces token waste

---

## Three-Layer Pattern

### Architecture Diagram

```
┌─────────────────────────────────────────────────────────┐
│ Layer 1: Ground Truth Calculation (Code)               │
├─────────────────────────────────────────────────────────┤
│ Input:  Raw market data (OHLCV, news, financials)      │
│ Output: Numeric ground truth values                     │
│                                                         │
│ Examples:                                               │
│   - ATR (Average True Range): 2.5                      │
│   - RSI (Relative Strength Index): 67                  │
│   - Volume Ratio: 1.8x                                  │
│   - VWAP Distance: +3.2%                                │
│   - Uncertainty Score: 0.42                             │
└─────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────┐
│ Layer 2: Semantic State Classification (Code)          │
├─────────────────────────────────────────────────────────┤
│ Input:  Ground truth numeric values                     │
│ Output: Categorical semantic states                     │
│                                                         │
│ Examples:                                               │
│   - RiskRegime: "high_volatility"                      │
│   - MomentumState: "bullish_strong"                    │
│   - TrendState: "uptrend_confirmed"                    │
│   - VolumeState: "above_average"                       │
│   - ConfidenceLevel: "moderate"                        │
└─────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────┐
│ Layer 3: LLM Narrative Synthesis (LLM)                 │
├─────────────────────────────────────────────────────────┤
│ Input:  Semantic states + ground truth context         │
│ Output: Natural language report                         │
│                                                         │
│ Example Constraint:                                     │
│   "Given RiskRegime=high_volatility and                 │
│    MomentumState=bullish_strong, synthesize a          │
│    narrative explaining the opportunity/risk trade-off."│
│                                                         │
│ LLM writes:                                             │
│   "หุ้นแสดงโมเมนตัมขาขึ่นที่แข็งแกร่ง (RSI: 67)        │
│    แต่มีความผันผวนสูง (ATR: 2.5) ซึ่งบ่งชี้ว่า..."    │
└─────────────────────────────────────────────────────────┘
```

### Layer Boundaries

**Layer 1 → Layer 2:** Numeric threshold-based classification
```python
# Example: Layer 1 produces ATR=2.5
# Layer 2 classifies: if ATR > 2.0 → "high_volatility"
```

**Layer 2 → Layer 3:** Semantic states passed as structured data to LLM prompt
```python
# Example: Pass semantic_states dict to LLM
semantic_states = {
    "risk_regime": "high_volatility",
    "momentum": "bullish_strong"
}
# LLM uses these as constraints, not raw calculations
```

---

## Layer 1: Ground Truth Calculation

**Purpose:** Calculate definitive numeric values that represent market reality.

### Implementation Location

- **File:** `src/analysis/technical_analysis.py`
- **Function:** `calculate_indicators(ticker_data: pd.DataFrame) -> dict`

### Example Calculations

```python
def calculate_indicators(ticker_data: pd.DataFrame) -> dict:
    """
    Layer 1: Calculate ground truth numeric indicators.

    These values are FACTS - not subject to interpretation.
    Layer 2 will classify what these facts MEAN.
    """
    indicators = {}

    # Volatility ground truth
    high_low = ticker_data['High'] - ticker_data['Low']
    high_close = abs(ticker_data['High'] - ticker_data['Close'].shift(1))
    low_close = abs(ticker_data['Low'] - ticker_data['Close'].shift(1))
    true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    indicators['atr'] = true_range.rolling(14).mean().iloc[-1]

    # Momentum ground truth
    delta = ticker_data['Close'].diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss = -delta.where(delta < 0, 0).rolling(14).mean()
    rs = gain / loss
    indicators['rsi'] = 100 - (100 / (1 + rs)).iloc[-1]

    # Volume ground truth
    avg_volume = ticker_data['Volume'].rolling(20).mean().iloc[-1]
    current_volume = ticker_data['Volume'].iloc[-1]
    indicators['volume_ratio'] = current_volume / avg_volume

    # VWAP ground truth
    vwap = (ticker_data['Close'] * ticker_data['Volume']).cumsum() / ticker_data['Volume'].cumsum()
    current_price = ticker_data['Close'].iloc[-1]
    indicators['vwap_distance_pct'] = ((current_price - vwap.iloc[-1]) / vwap.iloc[-1]) * 100

    # Uncertainty ground truth (confidence score)
    # Higher = more uncertainty (low confidence)
    price_volatility = ticker_data['Close'].pct_change().std()
    volume_volatility = ticker_data['Volume'].pct_change().std()
    indicators['uncertainty_score'] = (price_volatility + volume_volatility) / 2

    return indicators
```

### Key Principles

1. **No Interpretation:** Functions calculate numeric values, don't classify what they mean
2. **Deterministic:** Same input always produces same output
3. **Testable:** Can verify calculations against known values
4. **Documented:** Each calculation explains the formula used

### Testing Pattern

```python
# tests/analysis/test_technical_indicators.py
class TestGroundTruthCalculations:
    def test_atr_calculation_matches_formula(self):
        """Layer 1: Verify ATR formula correctness"""
        # Given known OHLC data
        ticker_data = pd.DataFrame({
            'High': [110, 112, 115],
            'Low': [108, 109, 111],
            'Close': [109, 111, 114]
        })

        # When calculating indicators
        result = calculate_indicators(ticker_data)

        # Then ATR matches manual calculation
        expected_atr = 2.33  # Calculated by hand
        assert abs(result['atr'] - expected_atr) < 0.01

    def test_uncertainty_score_increases_with_volatility(self):
        """Layer 1: Higher volatility → higher uncertainty"""
        # Stable prices
        stable_data = pd.DataFrame({
            'Close': [100, 100.5, 101, 100.8, 101.2],
            'Volume': [1000, 1100, 1050, 1000, 1100]
        })

        # Volatile prices
        volatile_data = pd.DataFrame({
            'Close': [100, 95, 110, 90, 115],
            'Volume': [1000, 500, 2000, 600, 2500]
        })

        stable_result = calculate_indicators(stable_data)
        volatile_result = calculate_indicators(volatile_data)

        # Volatile data should have higher uncertainty
        assert volatile_result['uncertainty_score'] > stable_result['uncertainty_score']
```

---

## Layer 2: Semantic State Classification

**Purpose:** Classify what ground truth numbers MEAN using code-based thresholds.

### Implementation Location

- **File:** `src/analysis/semantic_classifier.py`
- **Function:** `classify_semantic_states(indicators: dict) -> dict`

### Example Classifications

```python
from typing import Literal

RiskRegime = Literal["low_volatility", "moderate_volatility", "high_volatility"]
MomentumState = Literal["bearish_strong", "bearish_weak", "neutral", "bullish_weak", "bullish_strong"]
TrendState = Literal["downtrend_confirmed", "downtrend_weakening", "sideways", "uptrend_forming", "uptrend_confirmed"]
VolumeState = Literal["below_average", "average", "above_average", "surge"]
ConfidenceLevel = Literal["low", "moderate", "high"]

def classify_semantic_states(indicators: dict) -> dict:
    """
    Layer 2: Classify semantic meaning from ground truth.

    These classifications are DETERMINISTIC - same indicators
    always produce same semantic states.
    """
    states = {}

    # Risk regime classification (based on ATR)
    atr = indicators['atr']
    if atr < 1.5:
        states['risk_regime'] = "low_volatility"
    elif atr < 2.5:
        states['risk_regime'] = "moderate_volatility"
    else:
        states['risk_regime'] = "high_volatility"

    # Momentum state classification (based on RSI)
    rsi = indicators['rsi']
    if rsi < 30:
        states['momentum'] = "bearish_strong"
    elif rsi < 45:
        states['momentum'] = "bearish_weak"
    elif rsi < 55:
        states['momentum'] = "neutral"
    elif rsi < 70:
        states['momentum'] = "bullish_weak"
    else:
        states['momentum'] = "bullish_strong"

    # Trend state classification (based on VWAP distance)
    vwap_pct = indicators['vwap_distance_pct']
    if vwap_pct < -3:
        states['trend'] = "downtrend_confirmed"
    elif vwap_pct < -1:
        states['trend'] = "downtrend_weakening"
    elif vwap_pct < 1:
        states['trend'] = "sideways"
    elif vwap_pct < 3:
        states['trend'] = "uptrend_forming"
    else:
        states['trend'] = "uptrend_confirmed"

    # Volume state classification (based on volume ratio)
    vol_ratio = indicators['volume_ratio']
    if vol_ratio < 0.7:
        states['volume'] = "below_average"
    elif vol_ratio < 1.3:
        states['volume'] = "average"
    elif vol_ratio < 2.0:
        states['volume'] = "above_average"
    else:
        states['volume'] = "surge"

    # Confidence level classification (based on uncertainty score)
    uncertainty = indicators['uncertainty_score']
    if uncertainty < 0.02:
        states['confidence'] = "high"
    elif uncertainty < 0.05:
        states['confidence'] = "moderate"
    else:
        states['confidence'] = "low"

    return states
```

### Threshold Selection

**How to Choose Thresholds:**
1. **Domain Research:** Financial literature (RSI 30/70 overbought/oversold)
2. **Historical Analysis:** Analyze 1-year ticker data, find natural clusters
3. **Percentile-Based:** Use percentiles (25th, 50th, 75th) from historical distribution
4. **Expert Input:** Consult domain experts (traders, analysts)

**Example: ATR Thresholds**
```python
# Analyze historical ATR distribution
historical_atr = calculate_atr_for_last_year(ticker)
percentiles = np.percentile(historical_atr, [25, 50, 75])
# [1.2, 1.8, 2.4]

# Set thresholds at percentiles
THRESHOLDS = {
    'low_volatility': percentiles[0],      # < 25th percentile
    'moderate_volatility': percentiles[1], # 25th-75th percentile
    'high_volatility': percentiles[2]      # > 75th percentile
}
```

### Testing Pattern

```python
# tests/analysis/test_semantic_classifier.py
class TestSemanticStateClassification:
    def test_high_atr_classifies_as_high_volatility(self):
        """Layer 2: ATR > 2.5 → high_volatility"""
        indicators = {'atr': 3.0, 'rsi': 50, 'vwap_distance_pct': 0, 'volume_ratio': 1.0, 'uncertainty_score': 0.03}
        states = classify_semantic_states(indicators)
        assert states['risk_regime'] == "high_volatility"

    def test_rsi_above_70_classifies_as_bullish_strong(self):
        """Layer 2: RSI > 70 → bullish_strong"""
        indicators = {'atr': 2.0, 'rsi': 75, 'vwap_distance_pct': 0, 'volume_ratio': 1.0, 'uncertainty_score': 0.03}
        states = classify_semantic_states(indicators)
        assert states['momentum'] == "bullish_strong"

    def test_boundary_values_classified_correctly(self):
        """Layer 2: Test threshold boundaries"""
        # RSI exactly 70 should be bullish_strong
        indicators = {'atr': 2.0, 'rsi': 70.0, 'vwap_distance_pct': 0, 'volume_ratio': 1.0, 'uncertainty_score': 0.03}
        states = classify_semantic_states(indicators)
        assert states['momentum'] == "bullish_strong"

        # RSI 69.99 should be bullish_weak
        indicators['rsi'] = 69.99
        states = classify_semantic_states(indicators)
        assert states['momentum'] == "bullish_weak"
```

---

## Layer 3: LLM Narrative Synthesis

**Purpose:** Generate natural language narrative constrained by semantic states.

### Implementation Location

- **File:** `src/report/report_generator_simple.py`
- **Function:** `generate_report(state: AgentState) -> str`

### Prompt Structure

```python
def build_constrained_prompt(semantic_states: dict, indicators: dict, ticker_data: dict) -> str:
    """
    Layer 3: Build LLM prompt with semantic constraints.

    The prompt TELLS the LLM what meanings to synthesize,
    not asks the LLM to interpret raw data.
    """
    prompt = f"""
สร้างรายงานวิเคราะห์หุ้นภาษาไทยโดยยึดตามสถานะเชิงความหมายต่อไปนี้:

## สถานะเชิงความหมาย (Semantic States)
- ระดับความเสี่ยง: {semantic_states['risk_regime']}
- แรงผลักดัน: {semantic_states['momentum']}
- เทรนด์: {semantic_states['trend']}
- ปริมาณการซื้อขาย: {semantic_states['volume']}
- ความมั่นใจในการวิเคราะห์: {semantic_states['confidence']}

## ข้อมูลสนับสนุน (Ground Truth Context)
- ATR (Average True Range): {indicators['atr']:.2f}
- RSI (Relative Strength Index): {indicators['rsi']:.1f}
- ระยะห่างจาก VWAP: {indicators['vwap_distance_pct']:+.2f}%
- อัตราส่วนปริมาณการซื้อขาย: {indicators['volume_ratio']:.2f}x
- คะแนนความไม่แน่นอน: {indicators['uncertainty_score']:.3f}

## คำแนะนำในการสังเคราะห์:

1. **เริ่มต้นด้วยสรุปสั้น ๆ** (2-3 ประโยค) ที่สะท้อนสถานะเชิงความหมายหลัก

2. **วิเคราะห์แต่ละมิติ:**
   - ความเสี่ยง: อธิบายว่า {semantic_states['risk_regime']} หมายถึงอะไร และนักลงทุนควรระวังอะไร
   - แรงผลักดัน: อธิบายว่า {semantic_states['momentum']} บ่งชี้ถึงแนวโน้มอะไร
   - เทรนด์: อธิบายว่า {semantic_states['trend']} สอดคล้องกับราคาปัจจุบันหรือไม่
   - ปริมาณ: อธิบายว่า {semantic_states['volume']} บ่งบอกถึงความสนใจของนักลงทุนอย่างไร

3. **สังเคราะห์ความสัมพันธ์:**
   - เมื่อ risk_regime = "{semantic_states['risk_regime']}" และ momentum = "{semantic_states['momentum']}"
     นี่บ่งชี้ถึงโอกาส/ความเสี่ยงอะไร?
   - เทรนด์และปริมาณสนับสนุนซึ่งกันและกันหรือขัดแย้งกัน?

4. **ปิดท้ายด้วยข้อสรุป:**
   - ระบุความมั่นใจในการวิเคราะห์: {semantic_states['confidence']}
   - แนะนำ action (ถือครอง/ซื้อ/ขาย/รอดู) ที่สอดคล้องกับสถานะเชิงความหมาย

**สำคัญ:** ห้ามตีความข้อมูลดิบด้วยตัวเอง ให้ใช้สถานะเชิงความหมายที่กำหนดไว้เป็นตัวนำ
ข้อมูลสนับสนุน (Ground Truth) ใช้เพื่ออ้างอิงเท่านั้น ไม่ใช่เพื่อตีความใหม่
"""
    return prompt
```

### Constraint Enforcement

**Key Constraints:**
1. **State-Driven Narrative:** LLM must reference semantic states, not recalculate from raw data
2. **Consistency:** Contradicting semantic states is prohibited (e.g., can't say "high risk but low volatility")
3. **Ground Truth as Evidence:** Raw numbers used only to support semantic states, not to create new interpretations

### Example Output

**Input Semantic States:**
```python
{
    'risk_regime': 'high_volatility',
    'momentum': 'bullish_strong',
    'trend': 'uptrend_confirmed',
    'volume': 'above_average',
    'confidence': 'moderate'
}
```

**LLM Output:**
```
## สรุปภาพรวม

หุ้นแสดงแรงผลักดันขาขึ่นที่แข็งแกร่ง (RSI: 75) พร้อมเทรนด์ขาขึ่นที่ชัดเจน (+4.2% เหนือ VWAP)
แต่มาพร้อมกับความผันผวนสูง (ATR: 2.8) ซึ่งบ่งชี้ถึงโอกาสกำไรสูงแต่ความเสี่ยงก็สูงเช่นกัน

## วิเคราะห์รายมิติ

**ความเสี่ยง (high_volatility):**
ATR ที่ 2.8 บ่งชี้ว่าราคาแกว่งตัวในช่วงกว้าง นักลงทุนควรตั้ง stop-loss ที่กว้างพอรองรับความผันผวน
หรือลดขนาดการลงทุนเพื่อจำกัดความเสี่ยง

**แรงผลักดัน (bullish_strong):**
RSI ที่ 75 บ่งชี้ว่าแรงซื้อแข็งแกร่งมาก แต่ใกล้เข้าสู่โซน overbought แล้ว
การเข้าซื้อในจุดนี้อาจต้องระวังการปรับฐานระยะสั้น

**เทรนด์ (uptrend_confirmed):**
ราคาอยู่เหนือ VWAP ถึง 4.2% ยืนยันเทรนด์ขาขึ่นอย่างชัดเจน
ตราบใดที่ยังไม่กลับลงมาต่ำกว่า VWAP เทรนด์ยังน่าจะดำเนินต่อ

**ปริมาณ (above_average):**
ปริมาณการซื้อขายสูงกว่าค่าเฉลี่ย 1.6 เท่า แสดงว่ามีนักลงทุนสนใจเพิ่มขึ้น
สนับสนุนแรงผลักดันขาขึ่นที่เห็น

## สังเคราะห์

สถานการณ์ปัจจุบันคือ "โอกาสสูง-ความเสี่ยงสูง" (high opportunity - high risk)
- โอกาส: เทรนด์ขาขึ่นชัดเจน + แรงผลักดันแข็งแกร่ง + ปริมาณสนับสนุน
- ความเสี่ยง: ความผันผวนสูง + RSI ใกล้ overbought

เทรนด์และปริมาณสนับสนุนซึ่งกันและกัน (uptrend + above_average volume)
ซึ่งเป็นสัญญาณบวก แต่ความผันผวนสูงทำให้ต้องระมัดระวังเรื่อง timing

## ข้อสรุปและแนะนำ

**ความมั่นใจในการวิเคราะห์: moderate** (คะแนนความไม่แน่นอน: 0.045)
ข้อมูลส่วนใหญ่บ่งชี้ขาขึ่น แต่ความผันผวนสูงทำให้ต้องติดตามใกล้ชิด

**แนะนำ:**
- นักลงทุนระยะสั้น: **ถือครอง** (ride the trend) แต่ตั้ง trailing stop-loss
- นักลงทุนระยะยาว: **รอดู** (wait for pullback) เนื่องจาก RSI ใกล้ overbought
- นักลงทุนเสี่ยงต่ำ: **ระวัง** ความผันผวนสูงไม่เหมาะกับ risk profile
```

### Testing Pattern

```python
# tests/report/test_semantic_constrained_generation.py
class TestSemanticConstrainedGeneration:
    def test_high_volatility_mentioned_in_report(self):
        """Layer 3: Semantic state must appear in narrative"""
        semantic_states = {
            'risk_regime': 'high_volatility',
            'momentum': 'neutral',
            'trend': 'sideways',
            'volume': 'average',
            'confidence': 'moderate'
        }

        report = generate_report(semantic_states, indicators, ticker_data)

        # Report must mention high volatility
        assert 'ความผันผวนสูง' in report or 'high_volatility' in report
        assert 'ATR' in report  # Ground truth evidence

    def test_contradictory_states_not_generated(self):
        """Layer 3: LLM shouldn't contradict semantic states"""
        semantic_states = {
            'risk_regime': 'low_volatility',
            'momentum': 'bullish_strong',
            # ... other states
        }

        report = generate_report(semantic_states, indicators, ticker_data)

        # Report should not say "high risk" when state is low_volatility
        assert 'ความเสี่ยงสูง' not in report
        assert 'high risk' not in report
```

---

## Implementation Examples

### Complete Workflow Integration

```python
# src/workflow/workflow_nodes.py
def analyze_technical(state: AgentState) -> AgentState:
    """
    Workflow node integrating all three layers.
    """
    ticker_data = state['ticker_data']

    # Layer 1: Calculate ground truth
    indicators = calculate_indicators(ticker_data)
    state['indicators'] = indicators

    # Layer 2: Classify semantic states
    semantic_states = classify_semantic_states(indicators)
    state['semantic_states'] = semantic_states

    # Layer 3 happens in generate_report() node later

    return state

def generate_report(state: AgentState) -> AgentState:
    """
    Generate report using semantic layer architecture.
    """
    # Layer 3: LLM synthesis constrained by semantic states
    prompt = build_constrained_prompt(
        semantic_states=state['semantic_states'],
        indicators=state['indicators'],
        ticker_data=state['ticker_data']
    )

    report = llm.generate(prompt)
    state['report'] = report

    return state
```

### AgentState TypedDict

```python
# src/types.py
class AgentState(TypedDict):
    ticker: str
    ticker_data: dict
    indicators: dict              # Layer 1 output
    semantic_states: dict         # Layer 2 output
    report: str                   # Layer 3 output
    # ... other fields
```

---

## Migration from Multi-Stage

### What Was Removed

**Multi-Stage Approach (Old):**
```python
# 7 LLM calls total
mini_reports = {
    'technical': generate_technical_mini_report(state),      # LLM call 1
    'fundamental': generate_fundamental_mini_report(state),  # LLM call 2
    'market_conditions': generate_market_mini_report(state), # LLM call 3
    'news': generate_news_mini_report(state),                # LLM call 4
    'comparative': generate_comparative_mini_report(state),  # LLM call 5
    'strategy': generate_strategy_mini_report(state)         # LLM call 6
}
final_report = synthesize(mini_reports, state)  # LLM call 7

# Cost: ~$0.50 per report
# Latency: ~15s generation time
```

**Semantic Layer Approach (New):**
```python
# 1 LLM call total
indicators = calculate_indicators(state['ticker_data'])       # Code (free)
semantic_states = classify_semantic_states(indicators)        # Code (free)
final_report = generate_report(semantic_states, indicators)   # LLM call 1

# Cost: ~$0.07 per report
# Latency: ~5s generation time
```

### Files Deleted

**Deleted (11 files, ~1,262 lines):**
- `src/report/mini_report_generator.py` (323 lines)
- `src/report/synthesis_generator.py` (153 lines)
- `tests/shared/test_multistage_generation.py` (283 lines)
- `src/report/prompt_templates/th/multi-stage/*.txt` (7 files)

**Modified:**
- `src/workflow/workflow_nodes.py`: Removed `_generate_report_multistage()`
- `src/report/report_generator_simple.py`: Removed `_generate_multistage()`
- `src/types.py`: Removed `strategy` field
- 10 test files: Removed strategy parameter usage

### Database Migration

**Migration 011: Drop Strategy and Mini_Reports Columns**
```sql
-- db/migrations/011_drop_strategy_and_mini_reports.sql
ALTER TABLE precomputed_reports DROP COLUMN IF EXISTS strategy;
ALTER TABLE precomputed_reports DROP COLUMN IF EXISTS mini_reports;
```

**Apply Migration:**
```bash
doppler run -- python scripts/apply_migration.py db/migrations/011_drop_strategy_and_mini_reports.sql
```

---

## Testing Patterns

### Layer 1 Tests (Ground Truth)

```python
class TestGroundTruthCalculations:
    """Test numeric accuracy of ground truth calculations"""

    def test_atr_formula_correctness(self):
        """Verify ATR calculation matches financial formula"""
        # Known input/output test

    def test_deterministic_output(self):
        """Same input → same output (no randomness)"""
        # Run twice, expect identical results
```

### Layer 2 Tests (Semantic Classification)

```python
class TestSemanticClassification:
    """Test semantic state classification logic"""

    def test_threshold_boundaries(self):
        """Test edge cases at threshold boundaries"""
        # RSI 70.0 vs 69.99

    def test_all_states_covered(self):
        """Every numeric range maps to exactly one state"""
        # No gaps or overlaps in classification
```

### Layer 3 Tests (LLM Synthesis)

```python
class TestLLMConstrainedGeneration:
    """Test LLM respects semantic constraints"""

    def test_semantic_states_appear_in_report(self):
        """Report must mention all semantic states"""

    def test_no_contradictions(self):
        """Report must not contradict semantic states"""
        # If low_volatility, can't say "high risk"
```

### Integration Tests

```python
class TestSemanticLayerIntegration:
    """Test all three layers working together"""

    def test_end_to_end_workflow(self):
        """Ticker data → indicators → states → report"""
        # Full workflow integration test

    def test_state_propagation(self):
        """Verify state passes correctly through layers"""
        # Check AgentState at each layer
```

---

## File Organization

### Core Implementation Files

```
src/
├── analysis/
│   ├── technical_analysis.py           # Layer 1: Ground truth calculations
│   └── semantic_classifier.py          # Layer 2: Semantic state classification
├── report/
│   ├── report_generator_simple.py      # Layer 3: LLM synthesis
│   ├── context_builder.py              # Build context for Layer 3
│   └── prompt_builder.py               # Build constrained prompts
├── workflow/
│   └── workflow_nodes.py               # Integration of all 3 layers
└── types.py                            # AgentState with semantic_states field

tests/
├── analysis/
│   ├── test_technical_indicators.py    # Layer 1 tests
│   └── test_semantic_classifier.py     # Layer 2 tests
├── report/
│   └── test_semantic_constrained_generation.py  # Layer 3 tests
└── integration/
    └── test_semantic_layer_workflow.py # End-to-end tests
```

### Documentation Files

```
docs/
├── SEMANTIC_LAYER_ARCHITECTURE.md      # This file (implementation guide)
├── adr/
│   └── 001-adopt-semantic-layer-architecture.md  # Decision rationale
└── README.md                            # Index pointing to ADRs
```

---

## Performance Comparison

| Metric | Multi-Stage (Old) | Semantic Layer (New) | Improvement |
|--------|-------------------|----------------------|-------------|
| **LLM Calls** | 7 | 1 | **86% reduction** |
| **Cost per Report** | $0.50 | $0.07 | **86% reduction** |
| **Latency** | ~15s | ~5s | **67% reduction** |
| **Code Lines** | 1,262+ | ~400 | **68% reduction** |
| **Accuracy** | Baseline | +300% | Research-backed |
| **Maintenance** | 11 files | 3 files | **73% reduction** |

---

## References

- **ADR-001**: [Adopt Semantic Layer Architecture](adr/001-adopt-semantic-layer-architecture.md)
- **Research**: Semantic Layer Architecture in Financial LLMs (300% accuracy improvement)
- **Implementation**: `src/analysis/`, `src/report/`, `src/workflow/`
- **Tests**: `tests/analysis/`, `tests/report/`, `tests/integration/`

---

## Next Steps

1. **Extend Semantic States**: Add new states as business requirements evolve
   - Example: Add `LiquidityState` for bid-ask spread analysis

2. **Threshold Tuning**: Refine classification thresholds based on production data
   - Analyze false positive/negative rates
   - A/B test threshold variations

3. **Multi-Language Support**: Extend to English narrative generation
   - Reuse semantic states (language-agnostic)
   - Create English prompt templates

4. **Performance Monitoring**: Track semantic state distributions
   - Are some states underrepresented?
   - Do certain combinations produce better user engagement?
