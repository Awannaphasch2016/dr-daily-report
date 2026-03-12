# DR Report Prompt Construction Architecture

**Generated**: 2026-01-15
**Purpose**: Context engineering reference for improving DR report prompts

---

## Mental Model (What/How/Why)

**What it is**: A three-layer semantic architecture that separates numeric computation from narrative generation, based on the Damodaran "narrative + number" approach.

**How it works**: The system transforms raw data through progressive refinement layers before reaching the LLM.

**Why it exists**: To prevent LLM number hallucinations (research shows 300% accuracy improvement with semantic layers) and enable deterministic, auditable financial reports.

---

## Complete Data Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    DR REPORT PROMPT CONSTRUCTION PIPELINE                    │
└─────────────────────────────────────────────────────────────────────────────┘

                           ┌──────────────────┐
                           │   USER REQUEST   │
                           │  (ticker: DBS19) │
                           └────────┬─────────┘
                                    │
                                    ▼
┌───────────────────────────────────────────────────────────────────────────┐
│  LAYER 0: DATA FETCHING (WorkflowNodes)                                   │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │ fetch_data()     → Aurora DB → ticker_data, history DataFrame       │  │
│  │ fetch_news()     → NewsFetcher → news[], news_summary              │  │
│  │ analyze_technical() → TechnicalAnalyzer → indicators, percentiles  │  │
│  │ fetch_comparative() → ComparativeAnalyzer → comparative_data       │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│                                                                           │
│  Output: AgentState dict with all raw data                               │
└───────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌───────────────────────────────────────────────────────────────────────────┐
│  LAYER 1: NUMERIC CALCULATIONS (Ground Truth)                             │
│  File: src/analysis/market_analyzer.py                                    │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │ MarketAnalyzer.calculate_market_conditions(indicators)              │  │
│  │                                                                      │  │
│  │ Output: ground_truth = {                                            │  │
│  │   'uncertainty_score': 35.2,  # 0-100 scale                        │  │
│  │   'atr_pct': 1.45,            # ATR as % of price                  │  │
│  │   'vwap_pct': 3.2,            # Price vs VWAP %                    │  │
│  │   'volume_ratio': 1.8         # Volume vs 20-day avg              │  │
│  │ }                                                                   │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│                                                                           │
│  KEY PRINCIPLE: Deterministic, testable, auditable numbers               │
└───────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌───────────────────────────────────────────────────────────────────────────┐
│  LAYER 2: SEMANTIC STATE CLASSIFICATION                                   │
│  File: src/analysis/semantic_state_generator.py                           │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │ SemanticStateGenerator.generate_all_states(ground_truth, indicators)│  │
│  │                                                                      │  │
│  │ Input: uncertainty_score=35.2 → Output: uncertainty_state="moderate"│  │
│  │ Input: atr_pct=1.45          → Output: volatility_regime="moderate" │  │
│  │ Input: vwap_pct=3.2          → Output: pressure="buying"            │  │
│  │ Input: rsi=65                → Output: rsi_zone="approaching_overbought"│
│  │                                                                      │  │
│  │ Returns: SemanticStates {                                           │  │
│  │   risk: RiskRegime(uncertainty_state, volatility_regime, ...)      │  │
│  │   momentum: MomentumState(rsi_zone, macd_signal, ...)              │  │
│  │   trend: TrendState(sma_alignment, price_vs_sma)                   │  │
│  │ }                                                                   │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│                                                                           │
│  KEY PRINCIPLE: Code decides what numbers MEAN, LLM decides how to COMBINE│
└───────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌───────────────────────────────────────────────────────────────────────────┐
│  LAYER 2B: CONTEXT BUILDING                                               │
│  File: src/report/context_builder.py                                      │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │ ContextBuilder.prepare_context(...)                                 │  │
│  │                                                                      │  │
│  │ Sections assembled:                                                 │  │
│  │  1. Market conditions (placeholders only, NO raw numbers)           │  │
│  │  2. Semantic states (categorical labels like "moderate", "buying") │  │
│  │  3. Fundamental section (PE, EPS, Market Cap)                      │  │
│  │  4. Technical section (RSI, MACD, SMAs)                            │  │
│  │  5. News section (headlines with [1], [2] references)              │  │
│  │  6. Comparative section (peer analysis)                            │  │
│  │  7. Strategy section (backtest performance)                        │  │
│  │  8. Constraint satisfaction rules (instructions for LLM)           │  │
│  │                                                                      │  │
│  │ Output: ~4000 char context string                                   │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
└───────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌───────────────────────────────────────────────────────────────────────────┐
│  LAYER 2C: PROMPT BUILDING                                                │
│  File: src/report/prompt_builder.py + src/integrations/prompt_service.py  │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │ PromptService.get_prompt("report-generation")                       │  │
│  │   → Langfuse (if enabled) OR file fallback                         │  │
│  │   → Returns PromptResult(content, source, version)                 │  │
│  │                                                                      │  │
│  │ Template: main_prompt_v4_minimal.txt                                │  │
│  │ ┌─────────────────────────────────────────────────────────────────┐ │  │
│  │ │ <system>                                                        │ │  │
│  │ │ You write Thai stock reports for retail investors.              │ │  │
│  │ │ Core rule: Replace ALL numbers with {PLACEHOLDERS}              │ │  │
│  │ │ </system>                                                       │ │  │
│  │ │                                                                 │ │  │
│  │ │ <examples>                                                      │ │  │
│  │ │ Example 1 - Bullish Case (DBS19):                              │ │  │
│  │ │ 📖 **เรื่องราวของหุ้นตัวนี้**                                   │ │  │
│  │ │ DBS19 กำลังเคลื่อนที่ในตลาดที่มี {UNCERTAINTY}/100...          │ │  │
│  │ │ </examples>                                                     │ │  │
│  │ │                                                                 │ │  │
│  │ │ <task>                                                          │ │  │
│  │ │ Write 250-350 word Thai report for {TICKER}                    │ │  │
│  │ │ Requirements: 4 core metrics, 2-3 fundamentals, clear rec      │ │  │
│  │ │ </task>                                                         │ │  │
│  │ │                                                                 │ │  │
│  │ │ <placeholders>                                                  │ │  │
│  │ │ Risk Metrics: {RISK_METRICS}                                   │ │  │
│  │ │ Fundamentals: {FUNDAMENTAL_VARIABLES}                          │ │  │
│  │ │ </placeholders>                                                 │ │  │
│  │ │                                                                 │ │  │
│  │ │ <data>                                                          │ │  │
│  │ │ {CONTEXT}                                                       │ │  │
│  │ │ </data>                                                         │ │  │
│  │ └─────────────────────────────────────────────────────────────────┘ │  │
│  │                                                                      │  │
│  │ PromptBuilder.build_prompt(ticker, context, ...) fills:             │  │
│  │   {TICKER} → "DBS19"                                                │  │
│  │   {CONTEXT} → 4000 char context from ContextBuilder                │  │
│  │   {RISK_METRICS} → "{UNCERTAINTY}/100, {ATR_PCT}%, ..."            │  │
│  │   {FUNDAMENTAL_VARIABLES} → "{PE_RATIO}, {EPS}, ..."               │  │
│  │                                                                      │  │
│  │ Output: ~6000 char final prompt (~1500 tokens)                      │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
└───────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌───────────────────────────────────────────────────────────────────────────┐
│  LAYER 3: LLM NARRATIVE SYNTHESIS                                         │
│  File: workflow_nodes.py → _generate_report_singlestage()                │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │ llm.invoke([HumanMessage(content=prompt)])                          │  │
│  │                                                                      │  │
│  │ LLM generates Thai narrative WITH PLACEHOLDERS:                     │  │
│  │ ┌─────────────────────────────────────────────────────────────────┐ │  │
│  │ │ 📖 **เรื่องราวของหุ้นตัวนี้**                                   │ │  │
│  │ │ DBS19 กำลังเคลื่อนที่ในตลาดที่มีความไม่แน่นอน {UNCERTAINTY}/100│ │  │
│  │ │ ซึ่งอยู่ในเปอร์เซ็นไทล์ {UNCERTAINTY_SCORE_PERCENTILE}%        │ │  │
│  │ │ แต่ความผันผวนต่ำมาก {ATR_PCT}%...                               │ │  │
│  │ │                                                                 │ │  │
│  │ │ 🎯 **ควรทำอะไรตอนนี้?**                                         │ │  │
│  │ │ **HOLD** - ความไม่แน่นอน {UNCERTAINTY}/100 ยังจัดการได้...      │ │  │
│  │ └─────────────────────────────────────────────────────────────────┘ │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│                                                                           │
│  KEY PRINCIPLE: LLM writes narrative structure, NOT numbers              │
└───────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌───────────────────────────────────────────────────────────────────────────┐
│  LAYER 4: POST-PROCESSING                                                 │
│  File: src/report/number_injector.py                                      │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │ NumberInjector.inject_deterministic_numbers(narrative, ...)         │  │
│  │                                                                      │  │
│  │ Placeholder replacement (ground truth values):                      │  │
│  │   {UNCERTAINTY} → "35.2"                                            │  │
│  │   {ATR_PCT} → "1.45"                                                │  │
│  │   {VWAP_PCT} → "3.20"                                               │  │
│  │   {PE_RATIO} → "12.5"                                               │  │
│  │   {MARKET_CAP} → "155.71B"                                          │  │
│  │                                                                      │  │
│  │ + TransparencyFooter.generate_data_usage_footnote()                 │  │
│  │ + NewsFetcher.get_news_references()                                 │  │
│  │                                                                      │  │
│  │ Final output: Complete Thai report with exact numbers               │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
└───────────────────────────────────────────────────────────────────────────┘
```

---

## Key Components Summary

| Component | File | Purpose |
|-----------|------|---------|
| **WorkflowNodes** | `src/workflow/workflow_nodes.py` | Orchestrates data fetching and LLM calls |
| **MarketAnalyzer** | `src/analysis/market_analyzer.py` | Calculates ground truth (Layer 1) |
| **SemanticStateGenerator** | `src/analysis/semantic_state_generator.py` | Numeric → semantic labels (Layer 2) |
| **ContextBuilder** | `src/report/context_builder.py` | Assembles context sections |
| **PromptService** | `src/integrations/prompt_service.py` | Langfuse integration + file fallback |
| **PromptBuilder** | `src/report/prompt_builder.py` | Fills template with variables |
| **NumberInjector** | `src/report/number_injector.py` | Placeholder → exact value (post-processing) |

---

## Context Engineering Opportunities

### 1. Prompt Template (`main_prompt_v4_minimal.txt`)

The main lever for improvement. Current template is ~107 lines. You can:
- Modify `<system>` instructions for tone/style
- Add/edit `<examples>` for few-shot learning
- Adjust `<task>` requirements (word count, structure)
- Change `<placeholders>` categories

**File**: `src/report/prompt_templates/th/single-stage/main_prompt_v4_minimal.txt`

### 2. Semantic States (`semantic_state_generator.py`)

Controls categorical labels LLM sees. You can:
- Add new states (e.g., `market_regime: "bull" | "bear" | "sideways"`)
- Adjust thresholds (e.g., RSI overbought at 70 vs 80)
- Add combination states (e.g., `divergence_signal`)

**Thresholds defined**:
- Uncertainty: 0-25 stable, 25-50 moderate, 50-75 high_risk, 75+ extreme
- ATR%: <1% low, 1-2% moderate, 2-3% high, 3%+ extreme
- VWAP%: ±1% neutral, ±5% strong pressure
- RSI: <30 oversold, 30-40 approaching, 40-60 neutral, 60-70 approaching, 70+ overbought

### 3. Context Sections (`context_builder.py`)

Controls what data reaches the prompt. You can:
- Reorder sections (priority = order)
- Remove sections to reduce token usage
- Add new sections (e.g., earnings calendar)
- Change formatting (more concise vs detailed)

**Current sections**:
1. Market conditions (placeholders)
2. Semantic states
3. Fundamental section
4. Technical section
5. News section
6. Comparative section
7. Strategy section
8. Constraint satisfaction rules

### 4. Placeholder Categories (`number_injector.py`)

Defines available `{PLACEHOLDERS}`. You can:
- Add new placeholders (e.g., `{EARNINGS_DATE}`)
- Remove unused ones to simplify
- Add formatting logic (e.g., color coding)

**Current categories**:
- `risk_metrics`: UNCERTAINTY, ATR_PCT, VWAP_PCT, VOLUME_RATIO, CURRENT_PRICE
- `momentum_indicators`: RSI, MACD, MACD_SIGNAL
- `trend_indicators`: SMA_20, SMA_50, SMA_200, EMA_12, EMA_26
- `volatility_indicators`: ATR, BOLLINGER_UPPER/LOWER/MIDDLE
- `volume_indicators`: VWAP
- `fundamentals`: PE_RATIO, EPS, MARKET_CAP, REVENUE_GROWTH, PROFIT_MARGIN, etc.
- `comparative`: PERFORMANCE_ADVANTAGE, VOLATILITY_ADVANTAGE, etc.
- `strategy`: STRATEGY_BUY_RETURN, STRATEGY_SELL_RETURN, etc.
- `percentiles`: *_PERCENTILE variants for all indicators

### 5. Langfuse A/B Testing (`prompt_service.py`)

Currently Phase 1 (file fallback). Set `LANGFUSE_PROMPTS_ENABLED=true` to:
- Upload multiple prompt versions to Langfuse
- Label them: `development`, `staging`, `production`
- Compare performance metrics between versions
- Roll out winning prompts via label switching

**Environment variables**:
- `LANGFUSE_PROMPTS_ENABLED`: "true" to enable
- `LANGFUSE_PROMPT_CACHE_TTL`: Cache duration in seconds (default: 60)
- `ENVIRONMENT`: Maps to Langfuse label (dev→development, prod→production)

---

## Quick Reference: How to Improve Prompts

### For Quick Iterations
1. Edit `src/report/prompt_templates/th/single-stage/main_prompt_v4_minimal.txt`
2. Test with `doppler run -c dev -- python -c "from src.report import SimpleReportGenerator; ..."`
3. Compare outputs in Langfuse traces

### For A/B Testing
1. Set `LANGFUSE_PROMPTS_ENABLED=true`
2. Create prompt versions in Langfuse UI
3. Label versions: `development`, `staging`, `production`
4. Deploy and compare metrics

### For Adding New Data
1. Add fetcher in `workflow_nodes.py`
2. Add section formatter in `context_builder.py`
3. Add placeholders in `number_injector.py`
4. Update template to reference new placeholders

---

## Research References

- [Semantic Layer for LLMs](https://www.getdbt.com/blog/semantic-layer-as-the-data-interface-for-llms) - 300% accuracy improvement
- [FinFRE-RAG Semantic Serialization](https://arxiv.org/html/2512.13040)
- [Prompting Techniques for Financial LLMs](https://www.moduleq.com/blog/how-new-prompting-techniques-increase-llm-accuracy-in-financial-applications)
- Damodaran "Narrative + Number" approach - Deterministic numbers, LLM narratives
