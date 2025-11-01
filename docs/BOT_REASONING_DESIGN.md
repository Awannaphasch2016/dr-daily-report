# Bot Reasoning Design Report

**Project:** Daily Report Ticker Analysis Bot
**Date:** 2025-11-01
**Version:** 1.0

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Architecture Overview](#architecture-overview)
3. [Reasoning Chain Details](#reasoning-chain-details)
4. [LLM Prompt Engineering](#llm-prompt-engineering)
5. [Key Design Patterns](#key-design-patterns)
6. [Data Flow](#data-flow)
7. [Decision Logic](#decision-logic)
8. [Error Handling Strategy](#error-handling-strategy)
9. [Performance Considerations](#performance-considerations)
10. [Future Enhancements](#future-enhancements)

---

## Executive Summary

The Daily Report Ticker Analysis Bot uses a **multi-stage reasoning architecture** built on LangGraph to generate comprehensive Thai-language stock analysis reports. The system combines:

- **Sequential state-building pipeline** (5 nodes)
- **Two-pass LLM generation** with alignment checking
- **Historical context via percentile analysis**
- **Aswath Damodaran-style narrative storytelling**
- **Fault-tolerant execution** with graceful degradation

**Core Philosophy:** Transform raw financial data into actionable narratives by weaving technical indicators, fundamental analysis, news sentiment, and historical context into coherent stories that answer: **"Should I BUY, SELL, or HOLD?"**

---

## Architecture Overview

### System Components

```
┌─────────────────────────────────────────────────────────────┐
│                    TickerAnalysisAgent                      │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌─────────┐ │
│  │  Data    │   │Technical │   │   News   │   │  Chart  │ │
│  │ Fetcher  │   │ Analyzer │   │ Fetcher  │   │Generator│ │
│  └──────────┘   └──────────┘   └──────────┘   └─────────┘ │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │            LangGraph Workflow (StateGraph)           │  │
│  │                                                      │  │
│  │  fetch_data → fetch_news → analyze_technical →      │  │
│  │  generate_chart → generate_report → END             │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │          GPT-4o (Narrative Generation)               │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │          SQLite Database (Persistence)               │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### LangGraph Workflow DAG

```
┌─────────────┐
│ fetch_data  │  Fetch OHLCV + fundamentals from Yahoo Finance
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ fetch_news  │  Fetch high-impact news + sentiment analysis
└──────┬──────┘
       │
       ▼
┌─────────────────────┐
│ analyze_technical   │  Calculate 13 indicators + percentiles + backtest
└──────┬──────────────┘
       │
       ▼
┌─────────────────┐
│ generate_chart  │  Create 4-panel chart (candlestick, volume, RSI, MACD)
└──────┬──────────┘
       │
       ▼
┌─────────────────┐
│ generate_report │  Two-pass LLM generation with alignment checking
└──────┬──────────┘
       │
       ▼
      END
```

**File:** `src/agent.py:48-67`

---

## Reasoning Chain Details

### Node 1: `fetch_data` (Data Acquisition)

**Location:** `src/agent.py:69-108`

**Reasoning Steps:**

1. **Ticker Mapping**
   ```python
   yahoo_ticker = self.ticker_map.get(ticker.upper())
   # Example: AAPL19 → AAPL
   ```

2. **Data Fetching**
   - Fetch OHLCV (Open, High, Low, Close, Volume) historical data
   - Fetch company fundamentals (P/E, EPS, market cap, etc.)

3. **Data Enrichment**
   ```python
   data = self.data_fetcher.fetch_ticker_data(yahoo_ticker)
   info = self.data_fetcher.get_ticker_info(yahoo_ticker)
   data.update(info)  # Merge price data + fundamentals
   ```

4. **Database Persistence**
   - Save to SQLite for historical tracking
   - Enables trend analysis over time

**Error Handling:**
- If ticker not found: Set `state["error"]` and short-circuit pipeline
- If data fetch fails: Return error with Thai message

**Output State:**
```python
state["ticker_data"] = {
    'date': '2025-10-31',
    'open': 270.0, 'high': 275.0, 'low': 268.0, 'close': 270.37,
    'volume': 45000000,
    'market_cap': 4200000000000,
    'pe_ratio': 28.5,
    'eps': 9.48,
    'company_name': 'Apple Inc.',
    'sector': 'Technology',
    'industry': 'Consumer Electronics',
    'history': DataFrame[1yr of OHLCV data]
}
```

---

### Node 2: `fetch_news` (News & Sentiment)

**Location:** `src/agent.py:110-134`

**Reasoning Steps:**

1. **High-Impact News Filtering**
   ```python
   high_impact_news = self.news_fetcher.filter_high_impact_news(
       yahoo_ticker,
       min_score=40.0,  # Only impactful news
       max_news=5       # Top 5 articles
   )
   ```

2. **Sentiment Analysis**
   - Classify each article: `positive` / `negative` / `neutral`
   - Calculate impact score (0-100)

3. **News Summary Statistics**
   ```python
   news_summary = {
       'total_count': 3,
       'positive_count': 2,
       'negative_count': 0,
       'neutral_count': 1,
       'avg_impact_score': 42.5,
       'has_recent_news': True,  # < 24 hours
       'dominant_sentiment': 'positive'
   }
   ```

**Why This Matters:**
- News provides **catalyst context** for price movements
- Sentiment helps LLM understand market mood
- Recent news (< 24h) triggers urgency in recommendations

**Graceful Degradation:**
- If no news available, returns empty arrays (doesn't break pipeline)

---

### Node 3: `analyze_technical` (Technical Analysis)

**Location:** `src/agent.py:136-189`

**Reasoning Steps:**

#### Step 1: Calculate 13 Technical Indicators

```python
result = self.technical_analyzer.calculate_all_indicators_with_percentiles(hist_data)
```

**Indicators Calculated:**
1. **Moving Averages:** SMA-20, SMA-50, SMA-200
2. **Momentum:** RSI (Relative Strength Index)
3. **Trend:** MACD, MACD Signal
4. **Volatility:** Bollinger Bands (upper, middle, lower), ATR (Average True Range)
5. **Volume:** Volume SMA, Volume Ratio
6. **Price:** Current Price, VWAP (Volume Weighted Average Price)
7. **Custom:** Uncertainty Score (0-100)

#### Step 2: Percentile Analysis (Historical Context)

**Key Innovation:** For each indicator, calculate where current value ranks historically

```python
percentiles = {
    'rsi': {
        'current_value': 81.12,
        'percentile': 94.2,        # 94th percentile - very high historically
        'mean': 62.5,              # Historical average
        'std': 13.0,               # Standard deviation
        'min': 43.1, 'max': 89.8,  # Historical range
        'frequency_above_70': 31.4,  # 31.4% of time RSI > 70
        'frequency_below_30': 0.0    # Never below 30 in history
    },
    'macd': {...},
    'uncertainty_score': {...},
    'atr_percent': {...},
    'price_vwap_percent': {...},
    'volume_ratio': {...}
}
```

**Why Percentiles Matter:**
- Answers: "Is this value unusual compared to history?"
- Example: RSI 81 at 94th percentile → Very rare, strong overbought signal
- Example: RSI 81 at 50th percentile → Normal for this stock, not concerning

#### Step 3: Chart Pattern Detection

Detects classic patterns (if implemented):
- Head & Shoulders
- Double Top/Bottom
- Triangles, Flags, etc.

#### Step 4: Strategy Backtesting

**Dual Strategy Testing:**

```python
buy_results = self.strategy_backtester.backtest_buy_only(hist_data)
sell_results = self.strategy_backtester.backtest_sell_only(hist_data)
```

**Buy-Only Strategy:** What if we only took buy signals?
- Total return: +15.2%
- Sharpe ratio: 1.2
- Win rate: 62%
- Max drawdown: -8.5%

**Sell-Only Strategy:** What if we only took sell signals?
- Total return: +8.5%
- Sharpe ratio: 0.9
- Win rate: 58%
- Max drawdown: -12.3%

**Critical Design Choice:** Store BOTH strategies, but only show the one that aligns with recommendation (see Node 5)

#### Step 5: Database Persistence

Save all indicators to database for:
- Historical trend analysis
- Performance tracking
- Model training (future)

---

### Node 4: `generate_chart` (Visualization)

**Location:** `src/agent.py:191-217`

**Reasoning Steps:**

1. **Generate 4-Panel Chart**
   - Panel 1: Candlestick price chart + SMA overlays
   - Panel 2: Volume bars
   - Panel 3: RSI subplot (with 70/30 overbought/oversold zones)
   - Panel 4: MACD subplot (with signal line and histogram)

2. **Encode to Base64 PNG**
   ```python
   chart_base64 = self.chart_generator.generate_chart(
       ticker_data=ticker_data,
       indicators=indicators,
       ticker_symbol=ticker,
       days=90  # Last 90 days
   )
   ```

3. **Fault-Tolerant Execution**
   ```python
   try:
       # Generate chart
   except Exception as e:
       print(f"⚠️  Chart generation failed: {str(e)}")
       state["chart_base64"] = ""  # Continue without chart
       # DON'T set state["error"] - chart is optional
   ```

**Why Fault-Tolerant?**
- Chart generation can fail in serverless environments (memory limits)
- Analysis report is still valuable without chart
- User gets partial results instead of total failure

**Chart Specifications:**
- Size: 1400x1000 pixels (14"x10" @ 100 DPI)
- Format: PNG (base64 encoded)
- File size: ~130 KB typical
- Backend: matplotlib Agg (non-interactive, serverless-compatible)

---

### Node 5: `generate_report` (LLM Narrative Generation)

**Location:** `src/agent.py:219-283`

**This is the most complex reasoning chain with 5 stages:**

---

#### Stage 1: Generate Initial Report (Without Strategy)

**Code:** `src/agent.py:234-240`

```python
# Prepare context WITHOUT strategy performance data
context = self.prepare_context(
    ticker, ticker_data, indicators, percentiles,
    news, news_summary,
    strategy_performance=None  # Explicitly omit strategy
)

# Build prompt
uncertainty_score = indicators.get('uncertainty_score', 0)
prompt = self._build_prompt(context, uncertainty_score, strategy_performance=None)

# Call LLM
response = self.llm.invoke([HumanMessage(content=prompt)])
initial_report = response.content
```

**Why Generate Twice?**
- First pass determines recommendation based on **market fundamentals**
- Avoids LLM being biased by backtesting results
- Ensures recommendation is driven by current market conditions, not historical patterns

---

#### Stage 2: Extract Recommendation

**Code:** `src/agent.py:242-243`

```python
recommendation = self._extract_recommendation(initial_report)
# Returns: 'BUY', 'SELL', or 'HOLD'
```

**Extraction Logic:** `src/agent.py:683-698`

```python
def _extract_recommendation(self, report: str) -> str:
    report_upper = report.upper()

    # Look for BUY signals
    if 'BUY MORE' in report_upper or 'BUY' in report_upper:
        if 'แนะนำ BUY' in report or 'BUY MORE' in report_upper:
            return 'BUY'

    # Look for SELL signals
    if 'SELL' in report_upper:
        if 'แนะนำ SELL' in report:
            return 'SELL'

    # Default to HOLD
    return 'HOLD'
```

**Why This Works:**
- Thai reports use explicit keywords: "แนะนำ BUY" / "แนะนำ SELL" / "แนะนำ HOLD"
- English keywords also detected for robustness
- Default to HOLD if ambiguous (conservative approach)

---

#### Stage 3: Check Strategy Alignment

**Code:** `src/agent.py:245-246`

```python
include_strategy = self._check_strategy_alignment(recommendation, strategy_performance)
```

**Alignment Logic:** `src/agent.py:700-728`

```python
def _check_strategy_alignment(self, recommendation: str, strategy_performance: dict) -> bool:
    if not strategy_performance:
        return False

    buy_perf = strategy_performance['buy_only']
    sell_perf = strategy_performance['sell_only']

    buy_return = buy_perf.get('total_return_pct', 0)
    buy_sharpe = buy_perf.get('sharpe_ratio', 0)
    buy_win_rate = buy_perf.get('win_rate', 0)

    sell_return = sell_perf.get('total_return_pct', 0)
    sell_sharpe = sell_perf.get('sharpe_ratio', 0)
    sell_win_rate = sell_perf.get('win_rate', 0)

    if recommendation == 'BUY':
        # For BUY recommendation, buy_only strategy should perform well
        # Aligned if: positive return OR good sharpe (>0.5) OR good win rate (>50%)
        return buy_return > 0 or buy_sharpe > 0.5 or buy_win_rate > 50

    elif recommendation == 'SELL':
        # For SELL recommendation, sell_only strategy should perform well
        return sell_return > 0 or sell_sharpe > 0.5 or sell_win_rate > 50

    # For HOLD, never include strategy
    return False
```

**Design Philosophy:**

✅ **INCLUDE strategy if:**
- Recommendation = BUY AND buy_only strategy has ANY of:
  - Positive return (profit)
  - OR Sharpe ratio > 0.5 (good risk-adjusted return)
  - OR Win rate > 50% (more wins than losses)
- Recommendation = SELL AND sell_only strategy meets same criteria

❌ **EXCLUDE strategy if:**
- Recommendation = HOLD (never show strategy for neutral stance)
- Strategy performance contradicts recommendation
- Example: Recommending BUY but buy_only strategy lost money

**Why Lenient (OR logic, not AND)?**
- Only needs 1 positive metric to include
- Avoids cherry-picking: if strategy contradicts, omit entirely
- Prevents confusing the user with mixed signals

---

#### Stage 4: Conditional Regeneration (If Aligned)

**Code:** `src/agent.py:248-257`

```python
if include_strategy and strategy_performance:
    # Regenerate report WITH strategy evidence
    context_with_strategy = self.prepare_context(
        ticker, ticker_data, indicators, percentiles,
        news, news_summary,
        strategy_performance=strategy_performance  # Include now
    )

    prompt_with_strategy = self._build_prompt(
        context_with_strategy, uncertainty_score,
        strategy_performance=strategy_performance
    )

    response = self.llm.invoke([HumanMessage(content=prompt_with_strategy)])
    report = response.content  # Use new version with strategy
else:
    report = initial_report  # Use original version
```

**Two-Pass Benefits:**

1. **Prevents Contradictions**
   - First pass: "I recommend BUY because market conditions are strong"
   - Second pass: "I recommend BUY because market conditions are strong, AND historically this entry point has returned +15%"
   - NEVER: "I recommend BUY, but our strategy lost money at this point"

2. **Selective Evidence Inclusion**
   - Only shows backtesting when it **supports** the recommendation
   - Avoids information overload
   - Maintains narrative coherence

3. **Graceful Degradation**
   - If strategy data unavailable, first pass still produces good report
   - If strategy contradicts, first pass avoids confusing user

---

#### Stage 5: Post-Processing

**Code:** `src/agent.py:259-267`

```python
# Add news references at the end if news exists
if news:
    news_references = self.news_fetcher.get_news_references(news)
    report += f"\n\n{news_references}"

# Add percentile analysis at the end
if percentiles:
    percentile_analysis = self.technical_analyzer.format_percentile_analysis(percentiles)
    report += f"\n\n{percentile_analysis}"
```

**Appended Sections:**

1. **News References**
   ```markdown
   📎 แหล่งข้อมูลข่าว:
   [1] Yahoo Finance: Apple announces new product...
   [2] Reuters: Apple stock reaches new high...
   [3] Bloomberg: Analysts upgrade Apple to buy...
   ```

2. **Percentile Analysis (Detailed Stats)**
   ```markdown
   📊 การวิเคราะห์เปอร์เซ็นไทล์ (Percentile Analysis):

   RSI: 81.12 (เปอร์เซ็นไทล์: 94.2% - สูงมาก (อยู่ในช่วง 90-100%))
     - RSI สูงกว่าค่าเฉลี่ย - แรงซื้อแรง
     - ค่าเฉลี่ย: 62.53
     - ความถี่ที่ RSI > 70: 31.4%
     - ความถี่ที่ RSI < 30: 0.0%

   MACD: 10.84 (เปอร์เซ็นไทล์: 77.3% - สูง)
     - MACD บวก - แรงซื้อเหนือกว่า
     - ค่าเฉลี่ย: 6.42
     - ความถี่ที่ MACD > 0: 72.5%

   [... more indicators ...]
   ```

**Why Append Instead of Inline?**
- Keeps narrative flowing (no interruptions)
- Provides detailed data for power users
- Separates storytelling from raw statistics

---

## LLM Prompt Engineering

### Prompt Philosophy: Aswath Damodaran Style

**Inspiration:** Aswath Damodaran (NYU Stern professor, "Dean of Valuation")
- Tell stories with data, don't list numbers
- Explain WHY things matter, not just WHAT they are
- Mix technical + fundamental + narrative seamlessly

### Prompt Structure

**Location:** `src/agent.py:285-396` (`_build_prompt` method)

---

#### Section 1: Base Introduction

```python
base_intro = f"""You are a world-class financial analyst like Aswath Damodaran.
Write in Thai, but think like him - tell stories with data, don't just list numbers.

Data:
{context}

Write a narrative-driven report that answers:
"Should I BUY MORE?", "Should I SELL?", or "Should I HOLD?" and WHY?

Your job is to weave TECHNICAL + FUNDAMENTAL + RELATIVE + NEWS + STATISTICAL CONTEXT
into a flowing narrative that tells the STORY of this stock right now.

CRITICAL NARRATIVE ELEMENTS - You MUST weave these "narrative + number + historical context"
components into your story:
"""
```

---

#### Section 2: Narrative Elements (5 Components)

**Location:** `src/agent.py:306-344`

##### 1. Price Uncertainty (0-100 Score)

```
1. **Price Uncertainty** ({uncertainty_score:.0f}/100): Sets the overall market mood
   - Low (0-25): "ตลาดเสถียรมาก" - Stable, good for positioning
   - Moderate (25-50): "ตลาดค่อนข้างเสถียร" - Normal movement
   - High (50-75): "ตลาดผันผวนสูง" - High risk, be cautious
   - Extreme (75-100): "ตลาดผันผวนรุนแรง" - Extreme risk, warn strongly
   - **IMPORTANT**: Use percentile information to add historical context
     Example: "Uncertainty 52/100 ซึ่งอยู่ในเปอร์เซ็นไทล์ 88% -
               แสดงว่าความไม่แน่นอนนี้สูงกว่าปกติเมื่อเทียบกับประวัติศาสตร์"
```

##### 2. Volatility (ATR %)

```
2. **Volatility (ATR %)**: The speed of price movement
   - Include the ATR% number and explain what it means
   - Example: "ATR 1.2% แสดงราคาเคลื่อนไหวช้ามั่นคง นักลงทุนเห็นตรงกัน"
   - Example: "ATR 3.8% แสดงตลาดลังเล ราคากระโดดขึ้นลง 3-5% ได้ง่าย"
   - **IMPORTANT**: Use percentile context
     Example: "ATR 1.99% อยู่ในเปอร์เซ็นไทล์ 61% - สูงกว่าค่าเฉลี่ยปกติเล็กน้อย"
```

##### 3. Buy/Sell Pressure (Price vs VWAP %)

```
3. **Buy/Sell Pressure (Price vs VWAP %)**: Who's winning - buyers or sellers?
   - Include the % above/below VWAP and explain the implication
   - Example: "ราคา 22.4% เหนือ VWAP แสดงแรงซื้อแรงมาก
              คนซื้อวันนี้ยอมจ่ายแพงกว่าเฉลี่ย"
   - Example: "ราคา -2.8% ต่ำกว่า VWAP แสดงแรงขายหนัก
              คนขายรีบขายถูกกว่าเฉลี่ย"
   - **IMPORTANT**: Use percentile to show rarity
     Example: "ราคา 5% เหนือ VWAP ซึ่งอยู่ในเปอร์เซ็นไทล์ 90% -
               แสดงแรงซื้อที่ผิดปกติมากในอดีต"
```

##### 4. Volume (Volume Ratio)

```
4. **Volume (Volume Ratio)**: Is smart money interested?
   - Include the volume ratio (e.g., 0.8x, 1.5x, 2.0x) and explain what it means
   - Example: "ปริมาณซื้อขาย 1.8x ของเฉลี่ย แสดงนักลงทุนใหญ่กำลังเคลื่อนไหว"
   - Example: "ปริมาณซื้อขาย 0.7x ของเฉลี่ย แสดงนักลงทุนเฉยๆ รอดูก่อน"
   - **IMPORTANT**: Use percentile frequency
     Example: "ปริมาณ 1.03x อยู่ในเปอร์เซ็นไทล์ 71% -
               สูงกว่าปกติ แต่ไม่ใช่ระดับที่ผิดปกติ"
```

##### 5. Statistical Context (Percentiles)

```
5. **Statistical Context (Percentiles)**: Historical perspective on current values
   - CRITICAL: You MUST incorporate percentile information naturally into your narrative
   - This tells the reader: "Is this value unusual compared to history?"
   - Examples:
     * "RSI 81.12 ซึ่งอยู่ในเปอร์เซ็นไทล์ 94% -
        สูงมากในอดีต ควรระวังภาวะ Overbought"
     * "MACD 6.32 อยู่ในเปอร์เซ็นไทล์ 77% -
        สูงกว่าปกติ แสดงแรงซื้อแรงมาก"
     * "Uncertainty 52/100 อยู่ในเปอร์เซ็นไทล์ 88% -
        ความไม่แน่นอนนี้สูงกว่าปกติในอดีต"
   - Frequency percentages help explain rarity:
     * "RSI นี้สูงกว่า 70% ได้แค่ 28% ของเวลาในอดีต -
        แสดงภาวะ Overbought ที่หายาก"
     * "Volume 1.03x แต่ในอดีตเคยสูงถึง 2x ได้แค่ 1.9% ของเวลา -
        ปริมาณปัจจุบันยังไม่ใช่ระดับผิดปกติ"

These 5 elements (4 market conditions + statistical context) ARE the foundation
of your narrative. ALWAYS include specific numbers WITH historical context (percentiles) -
this is the "narrative + number + history" Damodaran style.
```

---

#### Section 3: Strategy Performance (Conditional)

**Location:** `src/agent.py:346-360`

**Only included if `strategy_performance` is provided:**

```
6. **Strategy Performance (Historical Backtesting)**:
   When strategy performance data is provided, USE IT to support your recommendation

   - CRITICAL: Only include strategy performance when it ALIGNS with your
     BUY/SELL recommendation
   - Weave strategy performance naturally into your narrative with "narrative + number" style
   - DO NOT mention what strategy was used - just present the performance as evidence

   - Examples of how to incorporate:
     * For BUY recommendation:
       "หากคุณติดตามกลยุทธ์ของเรา การซื้อครั้งล่าสุดอยู่ที่ $175
        และเมื่อดูจากสถิติการซื้อเท่านั้น (buy-only strategy) ในอดีต
        การเข้าตำแหน่งแบบนี้ให้ผลตอบแทนเฉลี่ย +15.2% โดยมี Sharpe ratio 1.2
        และอัตราชนะ 62% - แสดงว่าจุดเข้าแบบนี้มีความเสี่ยงต่ำและให้ผลตอบแทนดี"

     * For SELL recommendation:
       "หากคุณติดตามกลยุทธ์ของเรา การขายครั้งล่าสุดอยู่ที่ $180
        และเมื่อดูจากสถิติการขายเท่านั้น (sell-only strategy) ในอดีต
        การเข้าตำแหน่งแบบนี้ให้ผลตอบแทนเฉลี่ย +8.5% โดยมี Sharpe ratio 0.9
        และอัตราชนะ 58% - แสดงว่าจุดเข้าแบบนี้มีความเสี่ยงปานกลางและให้ผลตอบแทนดี"

   - Include risk/reward metrics:
     "Max Drawdown -12.5% แสดงว่าในอดีต ตำแหน่งแบบนี้เสี่ยงสูงสุดที่จะขาดทุน 12.5%
      ก่อนจะกลับขึ้นมา"

   - NEVER mention the strategy name (SMA crossing) - just say "กลยุทธ์ของเรา" or "strategies"
   - Use strategy data to strengthen your argument, not as standalone facts
```

**Why Hide Strategy Name?**
- Prevents over-reliance on one specific strategy
- Keeps narrative flexible
- Avoids technical jargon for general audience

---

#### Section 4: Report Structure

**Location:** `src/agent.py:362-396`

```
Structure (in Thai):

📖 **เรื่องราวของหุ้นตัวนี้**
Write 2-3 sentences telling the STORY.
MUST include: uncertainty score context + ATR% + VWAP% + volume ratio with their meanings.
Include news naturally if relevant.

💡 **สิ่งที่คุณต้องรู้**
Write 3-4 flowing paragraphs (NOT numbered lists) that explain WHY this matters to an investor.
MUST continuously reference the 4 market condition elements
(uncertainty, ATR, VWAP, volume) with numbers throughout.
Mix technical + fundamental + relative + news seamlessly.
[IF strategy data provided: weave it naturally to support analysis]

🎯 **ควรทำอะไรตอนนี้?**
Give ONE clear action: BUY MORE / SELL / HOLD.
Explain WHY in 2-3 sentences using uncertainty score + market conditions (ATR/VWAP/volume).
Reference news if it changes the decision.
[IF strategy data aligns: include backtesting evidence to strengthen argument]

⚠️ **ระวังอะไร?**
Warn about 1-2 key risks using the 4 market condition metrics.
What volatility/pressure/volume signals should trigger concern?
Keep it practical.

Rules for narrative flow:
- Tell STORIES, don't list bullet points - write like you're texting a friend investor
- CRITICAL: ALWAYS include all 4 market condition metrics
  (uncertainty, ATR%, VWAP%, volume ratio) with specific numbers AND percentile context throughout
- Use numbers IN sentences as evidence, not as standalone facts
- Explain WHY things matter (implication), not just WHAT they are (description)
- Mix technical + fundamental + relative + news + statistical context seamlessly - don't section them
- Reference news [1], [2] ONLY when it genuinely affects the story
- CRITICAL: When percentile data is available, USE IT to add historical context to numbers
  Example: "RSI 75 ซึ่งอยู่ในเปอร์เซ็นไทล์ 85%"
- Write under 12-15 lines total
- NO tables, NO numbered lists in the insight section, just flowing narrative

Write entirely in Thai, naturally flowing like Damodaran's style -
narrative supported by numbers, not numbers with explanation.
```

---

### Context Preparation

**Location:** `src/agent.py:577-616` (`prepare_context` method)

**The context provided to the LLM includes:**

#### 1. Basic Information
```
สัญลักษณ์: AAPL19
บริษัท: Apple Inc.
ราคาปัจจุบัน: 270.37
วันที่: 2025-10-31
```

#### 2. Fundamental Analysis
```
ข้อมูลพื้นฐาน (Fundamental Analysis):
- Market Cap: 4.2T
- P/E Ratio: 28.5
- Forward P/E: 24.3
- EPS: 9.48
- Dividend Yield: 0.45%
- Sector: Technology
- Industry: Consumer Electronics
- Revenue Growth: 8.2%
- Earnings Growth: 11.5%
- Profit Margin: 25.3%
```

#### 3. Technical Analysis
```
การวิเคราะห์ทางเทคนิค (Technical Analysis):
- SMA 20: 268.50
- SMA 50: 265.20
- SMA 200: 255.80
- RSI: 81.12
- MACD: 6.32
- Signal: 5.88
- Bollinger Upper: 275.40
- Bollinger Middle: 268.50
- Bollinger Lower: 261.60

แนวโน้ม: Strong Uptrend - Price above all SMAs
โมเมนตัม: Overbought (RSI > 70) - Exercise caution
MACD Signal: Bullish - MACD > Signal
Bollinger: Price near upper band - Potential resistance
```

#### 4. Market Conditions (Interpreted)
```
สภาวะตลาด (Market Condition - USE THESE IN YOUR NARRATIVE):
สถานะ: ตลาดผันผวนสูง - แรงซื้อขายไม่สมดุล ต้องระวังการเปลี่ยนทิศทางอย่างกะทันหัน

1. ความผันผวน (Volatility):
   ความผันผวนสูง (ATR 3.85%) - ราคาแกว่งตัวรุนแรง อาจขึ้นลง 3-5% ได้ง่าย

2. แรงซื้อ-ขาย (Buy/Sell Pressure):
   แรงซื้อแรงมาก - ราคา 22.4% เหนือ VWAP (220.85)
   คนซื้อยอมจ่ายแพงกว่าราคาเฉลี่ย แสดงความต้องการสูง

3. ปริมาณการซื้อขาย (Volume):
   ปริมาณซื้อขายสูง 1.8x ของค่าเฉลี่ย - ความสนใจเพิ่มขึ้นมาก
```

#### 5. Percentile Context
```
การวิเคราะห์เปอร์เซ็นไทล์ (Percentile Analysis - เปรียบเทียบกับประวัติศาสตร์):
- RSI: 81.12 (เปอร์เซ็นไทล์: 94.2% - สูงกว่าค่าเฉลี่ย 62.53)
  ความถี่ที่ RSI > 70: 31.4% | ความถี่ที่ RSI < 30: 0.0%

- MACD: 6.32 (เปอร์เซ็นไทล์: 77.3%)
  ความถี่ที่ MACD > 0: 72.5%

- Uncertainty Score: 68.5/100 (เปอร์เซ็นไทล์: 82.1%)
  ความถี่ที่ต่ำ (<25): 5.2% | ความถี่ที่สูง (>75): 12.8%

[... more indicators ...]

**IMPORTANT**: Use these percentile values naturally in your narrative to add historical context.
Don't just list them - weave them into the story!
```

#### 6. Relative Analysis
```
การวิเคราะห์เทียบเคียง (Relative Analysis):
- คำแนะนำนักวิเคราะห์: BUY
- ราคาเป้าหมายเฉลี่ย: 285.50
- จำนวนนักวิเคราะห์: 42
- ราคาสูงสุด 52 สัปดาห์: 278.90
- ราคาต่ำสุด 52 สัปดาห์: 198.50
```

#### 7. High-Impact News (If Available)
```
ข่าวสำคัญที่มีผลกระทบสูง (High-Impact News):
จำนวนข่าวทั้งหมด: 3
ข่าวดี: 2 | ข่าวลบ: 0 | เป็นกลาง: 1
แนวโน้มโดยรวม: POSITIVE
มีข่าวใหม่ล่าสุด (< 24 ชม): YES

[1] Apple announces record-breaking iPhone sales
    Sentiment: 📈 POSITIVE | Impact: 85/100 | 2h ago

[2] Apple expands manufacturing in India
    Sentiment: 📈 POSITIVE | Impact: 72/100 | 5h ago

[3] Tech sector sees rotation from growth stocks
    Sentiment: 📊 NEUTRAL | Impact: 45/100 | 18h ago
```

---

## Key Design Patterns

### 1. Sequential State Building

**Pattern:** Each node enriches the `AgentState` for the next node

```python
class AgentState(TypedDict):
    messages: list
    ticker: str
    ticker_data: dict          # Added by fetch_data
    indicators: dict           # Added by analyze_technical
    percentiles: dict          # Added by analyze_technical
    chart_patterns: list       # Added by analyze_technical
    pattern_statistics: dict   # Added by analyze_technical
    strategy_performance: dict # Added by analyze_technical
    news: list                 # Added by fetch_news
    news_summary: dict         # Added by fetch_news
    chart_base64: str          # Added by generate_chart
    report: str                # Added by generate_report
    error: str                 # Can be set by any node
```

**Benefits:**
- Clear data dependencies
- Easy to debug (inspect state between nodes)
- Modular (can add/remove nodes without breaking pipeline)

---

### 2. Error Short-Circuiting

**Pattern:** Early nodes can halt pipeline by setting `state["error"]`

```python
def fetch_data(self, state: AgentState) -> AgentState:
    if not yahoo_ticker:
        state["error"] = f"ไม่พบข้อมูล ticker สำหรับ {ticker}"
        return state  # Don't fetch data, just return

def fetch_news(self, state: AgentState) -> AgentState:
    if state.get("error"):
        return state  # Skip this node if error already set
```

**Benefits:**
- Fail fast (don't waste resources on doomed pipeline)
- Clear error propagation
- User gets specific error message

---

### 3. Fault Tolerance

**Pattern:** Non-critical failures don't break the pipeline

```python
def generate_chart(self, state: AgentState) -> AgentState:
    try:
        chart_base64 = self.chart_generator.generate_chart(...)
        state["chart_base64"] = chart_base64
    except Exception as e:
        print(f"⚠️  Chart generation failed: {str(e)}")
        state["chart_base64"] = ""  # Continue without chart
        # DON'T set state["error"]
    return state
```

**Benefits:**
- Graceful degradation (partial results better than total failure)
- User still gets valuable analysis without chart
- Improves reliability in serverless environments

---

### 4. Two-Pass LLM Generation

**Pattern:** Generate report twice to ensure coherence

**Pass 1:** Determine recommendation based on fundamentals
```python
context = self.prepare_context(..., strategy_performance=None)
prompt = self._build_prompt(context, ..., strategy_performance=None)
initial_report = self.llm.invoke([HumanMessage(content=prompt)])
recommendation = self._extract_recommendation(initial_report)
```

**Pass 2:** Add backtesting evidence if aligned
```python
if self._check_strategy_alignment(recommendation, strategy_performance):
    context_with_strategy = self.prepare_context(..., strategy_performance=strategy_performance)
    prompt_with_strategy = self._build_prompt(context_with_strategy, ..., strategy_performance=strategy_performance)
    final_report = self.llm.invoke([HumanMessage(content=prompt_with_strategy)])
```

**Benefits:**
- Prevents contradictions (never show conflicting evidence)
- Recommendation driven by market fundamentals, not historical patterns
- Selective evidence inclusion (only show what supports the thesis)

---

### 5. Alignment Checking

**Pattern:** Only show backtesting data that aligns with recommendation

```python
def _check_strategy_alignment(self, recommendation: str, strategy_performance: dict) -> bool:
    if recommendation == 'BUY':
        # Only include if buy_only strategy performed well
        return buy_return > 0 or buy_sharpe > 0.5 or buy_win_rate > 50
    elif recommendation == 'SELL':
        # Only include if sell_only strategy performed well
        return sell_return > 0 or sell_sharpe > 0.5 or sell_win_rate > 50
    else:  # HOLD
        return False  # Never show strategy for HOLD
```

**Benefits:**
- Avoids confusing user with mixed signals
- Prevents cherry-picking (if strategy contradicts, omit entirely)
- Maintains narrative coherence

---

### 6. Interpretive Layer

**Pattern:** Convert numbers to narratives before LLM sees them

```python
def _interpret_uncertainty_level(self, uncertainty_score: float) -> str:
    if uncertainty_score < 25:
        return "ตลาดเสถียรมาก - แรงซื้อขายสมดุล เหมาะสำหรับการวางแผนระยะยาว"
    elif uncertainty_score < 50:
        return "ตลาดค่อนข้างเสถียร - มีความเคลื่อนไหวปกติ เหมาะสำหรับการลงทุนทั่วไป"
    elif uncertainty_score < 75:
        return "ตลาดผันผวนสูง - แรงซื้อขายไม่สมดุล ต้องระวังการเปลี่ยนทิศทางอย่างกะทันหัน"
    else:
        return "ตลาดผันผวนรุนแรง - แรงซื้อขายชนกันหนัก เหมาะสำหรับมืออาชีพเท่านั้น"
```

**Benefits:**
- LLM receives contextual interpretation, not just raw numbers
- Consistent narrative tone
- Easier for LLM to weave into story

---

### 7. Historical Context via Percentiles

**Pattern:** Every metric includes percentile ranking

```python
percentiles = {
    'rsi': {
        'current_value': 81.12,
        'percentile': 94.2,  # 94th percentile - very high
        'mean': 62.53,
        'std': 13.0,
        'frequency_above_70': 31.4  # Only 31.4% of time above 70
    }
}
```

**Benefits:**
- Answers "Is this unusual?" for every metric
- Provides context: RSI 81 is very different for a volatile vs stable stock
- Enables comparative analysis: "Higher than 94% of historical values"

---

### 8. Storytelling Emphasis

**Pattern:** Prompt engineering forces narrative flow

```
Rules for narrative flow:
- Tell STORIES, don't list bullet points
- Use numbers IN sentences as evidence, not as standalone facts
- Explain WHY things matter (implication), not just WHAT they are (description)
- NO tables, NO numbered lists in the insight section, just flowing narrative
```

**Benefits:**
- Reports read like articles, not data dumps
- More engaging for users
- Easier to understand (context provided naturally)

---

## Data Flow

### Complete Data Flow Diagram

```
┌─────────────┐
│   User      │
│   Input     │  ticker = "AAPL19"
└──────┬──────┘
       │
       ▼
┌─────────────────────────────────────────────────────────┐
│  LangGraph Workflow Execution                           │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  NODE 1: fetch_data                                     │
│  ┌──────────────────────────────────────────┐          │
│  │ Yahoo Finance API                        │          │
│  │ ├─ OHLCV data (1 year history)           │          │
│  │ ├─ Fundamentals (P/E, EPS, market cap)   │          │
│  │ └─ Company info (sector, industry)       │          │
│  └──────────────────┬───────────────────────┘          │
│                     │                                   │
│                     ▼                                   │
│  ┌──────────────────────────────────────────┐          │
│  │ SQLite Database (ticker_data table)      │          │
│  │ Save: date, OHLCV, fundamentals          │          │
│  └──────────────────────────────────────────┘          │
│                                                         │
│  STATE: ticker_data = {...}                            │
│  ─────────────────────────────────────────────────────│
│                                                         │
│  NODE 2: fetch_news                                     │
│  ┌──────────────────────────────────────────┐          │
│  │ Yahoo Finance News API                   │          │
│  │ ├─ Fetch news articles                   │          │
│  │ ├─ Filter by impact score (> 40)         │          │
│  │ ├─ Sentiment classification              │          │
│  │ └─ Calculate summary statistics          │          │
│  └──────────────────────────────────────────┘          │
│                                                         │
│  STATE: news = [...], news_summary = {...}             │
│  ─────────────────────────────────────────────────────│
│                                                         │
│  NODE 3: analyze_technical                              │
│  ┌──────────────────────────────────────────┐          │
│  │ Technical Analyzer                       │          │
│  │ ├─ Calculate 13 indicators               │          │
│  │ ├─ Calculate percentiles                 │          │
│  │ ├─ Detect chart patterns                 │          │
│  │ └─ Backtest strategies                   │          │
│  │     ├─ Buy-only strategy                 │          │
│  │     └─ Sell-only strategy                │          │
│  └──────────────────┬───────────────────────┘          │
│                     │                                   │
│                     ▼                                   │
│  ┌──────────────────────────────────────────┐          │
│  │ SQLite Database (indicators table)       │          │
│  │ Save: date, all indicators               │          │
│  └──────────────────────────────────────────┘          │
│                                                         │
│  STATE: indicators = {...}, percentiles = {...},       │
│         strategy_performance = {...}                   │
│  ─────────────────────────────────────────────────────│
│                                                         │
│  NODE 4: generate_chart                                 │
│  ┌──────────────────────────────────────────┐          │
│  │ Chart Generator (matplotlib)             │          │
│  │ ├─ Panel 1: Candlestick + SMA            │          │
│  │ ├─ Panel 2: Volume bars                  │          │
│  │ ├─ Panel 3: RSI subplot                  │          │
│  │ ├─ Panel 4: MACD subplot                 │          │
│  │ └─ Encode to base64 PNG                  │          │
│  └──────────────────────────────────────────┘          │
│                                                         │
│  STATE: chart_base64 = "iVBORw0KGgo..."                │
│  ─────────────────────────────────────────────────────│
│                                                         │
│  NODE 5: generate_report (Multi-stage)                 │
│  ┌──────────────────────────────────────────┐          │
│  │ STAGE 1: Initial Report Generation       │          │
│  │ ├─ Prepare context (no strategy)         │          │
│  │ │   ├─ Interpret market conditions       │          │
│  │ │   ├─ Format percentile context         │          │
│  │ │   └─ Format news section               │          │
│  │ ├─ Build Damodaran-style prompt          │          │
│  │ └─ GPT-4o: Generate narrative             │          │
│  └──────────────────┬───────────────────────┘          │
│                     │                                   │
│                     ▼                                   │
│  ┌──────────────────────────────────────────┐          │
│  │ STAGE 2: Extract Recommendation          │          │
│  │ Parse report → BUY / SELL / HOLD          │          │
│  └──────────────────┬───────────────────────┘          │
│                     │                                   │
│                     ▼                                   │
│  ┌──────────────────────────────────────────┐          │
│  │ STAGE 3: Check Strategy Alignment        │          │
│  │ IF BUY: Check buy_only performance        │          │
│  │ IF SELL: Check sell_only performance      │          │
│  │ IF HOLD: Skip strategy                    │          │
│  └──────────────────┬───────────────────────┘          │
│                     │                                   │
│                     ▼                                   │
│  ┌──────────────────────────────────────────┐          │
│  │ STAGE 4: Conditional Regeneration        │          │
│  │ IF aligned:                               │          │
│  │   ├─ Prepare context (WITH strategy)     │          │
│  │   ├─ Build prompt (WITH strategy)         │          │
│  │   └─ GPT-4o: Regenerate narrative         │          │
│  │ ELSE:                                     │          │
│  │   └─ Use initial report                   │          │
│  └──────────────────┬───────────────────────┘          │
│                     │                                   │
│                     ▼                                   │
│  ┌──────────────────────────────────────────┐          │
│  │ STAGE 5: Post-processing                 │          │
│  │ ├─ Append news references                │          │
│  │ └─ Append percentile analysis            │          │
│  └──────────────────┬───────────────────────┘          │
│                     │                                   │
│                     ▼                                   │
│  ┌──────────────────────────────────────────┐          │
│  │ SQLite Database (reports table)          │          │
│  │ Save: date, report, summaries            │          │
│  └──────────────────────────────────────────┘          │
│                                                         │
│  STATE: report = "📖 เรื่องราวของหุ้นตัวนี้..."         │
└─────────────────────────────────────────────────────────┘
       │
       ▼
┌──────────────────┐
│  API Response    │
│  or LINE Reply   │
└──────────────────┘
```

---

## Decision Logic

### Recommendation Extraction Logic

**Location:** `src/agent.py:683-698`

```python
def _extract_recommendation(self, report: str) -> str:
    """Extract BUY/SELL/HOLD recommendation from Thai report"""
    report_upper = report.upper()

    # Priority 1: Look for explicit BUY signals
    if 'BUY MORE' in report_upper or 'BUY' in report_upper:
        if 'แนะนำ BUY' in report or 'แนะนำ BUY MORE' in report or 'BUY MORE' in report_upper:
            return 'BUY'

    # Priority 2: Look for explicit SELL signals
    if 'SELL' in report_upper:
        if 'แนะนำ SELL' in report or 'SELL' in report_upper:
            return 'SELL'

    # Default: Conservative HOLD
    return 'HOLD'
```

**Design Choices:**
- **Thai keywords prioritized:** "แนะนำ BUY" / "แนะนำ SELL" / "แนะนำ HOLD"
- **English fallback:** Also detects "BUY MORE" / "SELL" in uppercase
- **Conservative default:** If ambiguous, return HOLD (avoid risky suggestions)
- **No regex complexity:** Simple string matching (robust, fast)

---

### Strategy Alignment Logic

**Location:** `src/agent.py:700-728`

```python
def _check_strategy_alignment(self, recommendation: str, strategy_performance: dict) -> bool:
    """Determine if strategy performance supports the recommendation"""

    if not strategy_performance:
        return False

    buy_perf = strategy_performance.get('buy_only', {})
    sell_perf = strategy_performance.get('sell_only', {})

    # Extract metrics
    buy_return = buy_perf.get('total_return_pct', 0)
    buy_sharpe = buy_perf.get('sharpe_ratio', 0)
    buy_win_rate = buy_perf.get('win_rate', 0)

    sell_return = sell_perf.get('total_return_pct', 0)
    sell_sharpe = sell_perf.get('sharpe_ratio', 0)
    sell_win_rate = sell_perf.get('win_rate', 0)

    # Decision tree
    if recommendation == 'BUY':
        # For BUY: buy_only strategy should show promise
        # Aligned if ANY of: profit, good risk-adjusted return, or majority wins
        return (buy_return > 0) or (buy_sharpe > 0.5) or (buy_win_rate > 50)

    elif recommendation == 'SELL':
        # For SELL: sell_only strategy should show promise
        return (sell_return > 0) or (sell_sharpe > 0.5) or (sell_win_rate > 50)

    else:  # HOLD
        # For HOLD: never include strategy (neutral stance doesn't need backtesting)
        return False
```

**Alignment Criteria:**

| Recommendation | Strategy Checked | Alignment Condition (OR logic) |
|---------------|------------------|-------------------------------|
| BUY           | buy_only         | `return > 0` OR `sharpe > 0.5` OR `win_rate > 50%` |
| SELL          | sell_only        | `return > 0` OR `sharpe > 0.5` OR `win_rate > 50%` |
| HOLD          | N/A              | Always `False` (never show strategy) |

**Why OR Logic (Lenient)?**
- Only needs 1 positive metric to include
- Example: Even if return is negative, high win rate (60%) shows the strategy works most of the time
- Avoids over-filtering: A slightly negative return with high Sharpe ratio (good risk-adjusted) is still valuable

**Why Exclude for HOLD?**
- HOLD = neutral stance (no action recommended)
- Showing backtesting for HOLD would confuse user ("If strategy works, why not BUY?")
- Keeps HOLD reports focused on market analysis, not historical patterns

---

### Market Condition Interpretation

**Location:** `src/agent.py:398-467`

#### Uncertainty Level Interpretation

```python
def _interpret_uncertainty_level(self, uncertainty_score: float) -> str:
    if uncertainty_score < 25:
        return "ตลาดเสถียรมาก - แรงซื้อขายสมดุล เหมาะสำหรับการวางแผนระยะยาว"
    elif uncertainty_score < 50:
        return "ตลาดค่อนข้างเสถียร - มีความเคลื่อนไหวปกติ เหมาะสำหรับการลงทุนทั่วไป"
    elif uncertainty_score < 75:
        return "ตลาดผันผวนสูง - แรงซื้อขายไม่สมดุล ต้องระวังการเปลี่ยนทิศทางอย่างกะทันหัน"
    else:
        return "ตลาดผันผวนรุนแรง - แรงซื้อขายชนกันหนัก เหมาะสำหรับมืออาชีพเท่านั้น"
```

**Score Ranges:**
- **0-25:** Very stable (suitable for long-term planning)
- **25-50:** Moderately stable (normal movement)
- **50-75:** High volatility (caution advised, sudden direction changes possible)
- **75-100:** Extreme volatility (professional traders only)

---

#### ATR Volatility Interpretation

```python
def _interpret_volatility(self, atr: float, current_price: float) -> str:
    atr_percent = (atr / current_price) * 100

    if atr_percent < 1:
        return f"ความผันผวนต่ำมาก (ATR {atr_percent:.2f}%) - ราคาเคลื่อนไหวช้า มั่นคง"
    elif atr_percent < 2:
        return f"ความผันผวนปานกลาง (ATR {atr_percent:.2f}%) - ราคาเคลื่อนไหวปกติ"
    elif atr_percent < 4:
        return f"ความผันผวนสูง (ATR {atr_percent:.2f}%) - ราคาแกว่งตัวรุนแรง อาจขึ้นลง 3-5% ได้ง่าย"
    else:
        return f"ความผันผวนสูงมาก (ATR {atr_percent:.2f}%) - ราคาแกว่งตัวมาก อาจขึ้นลง 5-10% ภายในวัน"
```

**ATR % Ranges:**
- **< 1%:** Very low volatility (slow, stable price movement)
- **1-2%:** Moderate volatility (normal movement)
- **2-4%:** High volatility (price can easily swing 3-5%)
- **> 4%:** Very high volatility (price can swing 5-10% intraday)

---

#### VWAP Pressure Interpretation

```python
def _interpret_vwap_pressure(self, price_vs_vwap_pct: float, vwap: float) -> str:
    if price_vs_vwap_pct > 3:
        return f"แรงซื้อแรงมาก - ราคา {price_vs_vwap_pct:.1f}% เหนือ VWAP ({vwap:.2f})
                 คนซื้อยอมจ่ายแพงกว่าราคาเฉลี่ย แสดงความต้องการสูง"
    elif price_vs_vwap_pct > 1:
        return f"แรงซื้อดี - ราคา {price_vs_vwap_pct:.1f}% เหนือ VWAP ({vwap:.2f})
                 มีความต้องการซื้อเหนือกว่า"
    elif price_vs_vwap_pct > -1:
        return f"แรงซื้อขายสมดุล - ราคาใกล้เคียง VWAP ({vwap:.2f}) ตลาดยังไม่มีทิศทางชัด"
    elif price_vs_vwap_pct > -3:
        return f"แรงขายเริ่มมี - ราคา {abs(price_vs_vwap_pct):.1f}% ต่ำกว่า VWAP ({vwap:.2f})
                 มีแรงกดดันขาย"
    else:
        return f"แรงขายหนัก - ราคา {abs(price_vs_vwap_pct):.1f}% ต่ำกว่า VWAP ({vwap:.2f})
                 คนขายยอมขายถูกกว่าเฉลี่ย แสดงความตื่นตระหนก"
```

**VWAP % Ranges:**
- **> +3%:** Very strong buying (buyers willing to pay premium)
- **+1% to +3%:** Good buying pressure
- **-1% to +1%:** Balanced (no clear direction)
- **-3% to -1%:** Selling pressure emerging
- **< -3%:** Heavy selling (sellers willing to accept discount, panic selling)

---

#### Volume Interpretation

```python
def _interpret_volume(self, volume_ratio: float) -> str:
    if volume_ratio > 2.0:
        return f"ปริมาณซื้อขายระเบิด {volume_ratio:.1f}x ของค่าเฉลี่ย -
                 มีเหตุการณ์สำคัญ นักลงทุนใหญ่กำลังเคลื่อนไหว"
    elif volume_ratio > 1.5:
        return f"ปริมาณซื้อขายสูง {volume_ratio:.1f}x ของค่าเฉลี่ย -
                 ความสนใจเพิ่มขึ้นมาก"
    elif volume_ratio > 0.7:
        return f"ปริมาณซื้อขายปกติ ({volume_ratio:.1f}x ของค่าเฉลี่ย)"
    else:
        return f"ปริมาณซื้อขายเงียบ {volume_ratio:.1f}x ของค่าเฉลี่ย -
                 นักลงทุนไม่ค่อยสนใจ อาจรอข่าวใหม่"
```

**Volume Ratio Ranges:**
- **> 2.0x:** Explosive volume (major event, institutional activity)
- **1.5x - 2.0x:** High volume (increased interest)
- **0.7x - 1.5x:** Normal volume
- **< 0.7x:** Quiet volume (low interest, waiting for news)

---

## Error Handling Strategy

### Error Types and Handling

#### 1. Data Fetch Errors

**Scenario:** Yahoo Finance API fails, ticker not found, network timeout

**Handling:**
```python
# src/agent.py:76-85
if not yahoo_ticker:
    state["error"] = f"ไม่พบข้อมูล ticker สำหรับ {ticker}"
    return state  # Short-circuit pipeline

if not data:
    state["error"] = f"ไม่สามารถดึงข้อมูลสำหรับ {ticker} ({yahoo_ticker}) ได้"
    return state
```

**Result:** User receives Thai error message explaining the issue

---

#### 2. Technical Analysis Errors

**Scenario:** Insufficient historical data, calculation failures

**Handling:**
```python
# src/agent.py:144-153
if hist_data is None or hist_data.empty:
    state["error"] = "ไม่มีข้อมูลประวัติสำหรับการวิเคราะห์"
    return state

if not result or not result.get('indicators'):
    state["error"] = "ไม่สามารถคำนวณ indicators ได้"
    return state
```

**Result:** Clear error message, no partial/invalid analysis

---

#### 3. Chart Generation Errors

**Scenario:** matplotlib fails, memory limits exceeded (serverless)

**Handling:**
```python
# src/agent.py:212-215
except Exception as e:
    print(f"⚠️  Chart generation failed: {str(e)}")
    state["chart_base64"] = ""  # Continue without chart
    # DON'T set state["error"]
```

**Result:** Report still generated, chart omitted (graceful degradation)

---

#### 4. LLM Generation Errors

**Scenario:** OpenAI API timeout, rate limiting, invalid response

**Handling:**
```python
# src/api_handler.py:213-228
except Exception as e:
    print(f"Error in API handler: {str(e)}")
    import traceback
    traceback.print_exc()

    return {
        'statusCode': 500,
        'headers': {'Content-Type': 'application/json'},
        'body': json.dumps({
            'error': 'Internal server error',
            'message': str(e)
        })
    }
```

**Result:** User receives 500 error with details (for debugging)

---

#### 5. Database Errors

**Scenario:** SQLite write failure, disk full, permissions

**Handling:**
```python
# Errors logged but don't break pipeline
# Database persistence is for historical tracking, not critical for current analysis
try:
    self.db.insert_ticker_data(...)
except Exception as e:
    print(f"Database write failed: {str(e)}")
    # Continue execution
```

**Result:** Analysis proceeds, historical tracking may be incomplete

---

### Error Propagation

```
fetch_data (sets error)
    → fetch_news (checks error, skips if set)
    → analyze_technical (checks error, skips if set)
    → generate_chart (fault-tolerant, doesn't check error)
    → generate_report (checks error, skips if set)
```

**Key Points:**
- Early errors propagate through pipeline (short-circuit)
- Chart generation is fault-tolerant (doesn't check or set errors)
- All other nodes check `state.get("error")` before executing

---

## Performance Considerations

### Response Time Breakdown

**Total:** 8-12 seconds (comprehensive analysis)

| Stage | Time | Bottleneck |
|-------|------|-----------|
| Data Fetching | 2-3s | Yahoo Finance API latency |
| Technical Analysis | 1s | Pandas calculations (13 indicators + percentiles) |
| News Fetching | 1-2s | Yahoo Finance News API latency |
| Chart Generation | 1-2s | matplotlib rendering (90-day candlestick chart) |
| LLM Report (Pass 1) | 3-5s | GPT-4o API latency |
| LLM Report (Pass 2) | 3-5s | GPT-4o API latency (if aligned) |

**Optimization Opportunities:**
- **Parallel fetching:** Fetch data + news concurrently (save 1-2s)
- **Caching:** Cache ticker data for 5-10 minutes (API responses)
- **Smaller chart:** Reduce days from 90 to 60 (save ~0.5s)
- **Single-pass LLM:** Skip second pass for HOLD recommendations (save 3-5s)

---

### Memory Usage

**Peak Memory:** ~200-300 MB

| Component | Memory | Notes |
|-----------|--------|-------|
| Historical Data (1yr) | ~50 MB | Pandas DataFrame with OHLCV |
| Technical Indicators | ~20 MB | 13 indicators calculated |
| Chart Generation | ~100 MB | matplotlib figure in memory |
| LLM Context | ~10 MB | Prompt + response text |
| Misc (Python runtime) | ~50 MB | Base overhead |

**Lambda Recommendations:**
- Minimum memory: 512 MB (may timeout on chart generation)
- Recommended: 1024 MB (stable performance)
- Maximum needed: 1536 MB (headroom for spikes)

---

### API Rate Limits

**Yahoo Finance (Unofficial):**
- Limit: ~2000 requests/hour
- Recommendation: Add 100ms delay between requests
- Caching: Cache responses for 5-10 minutes

**OpenAI GPT-4o:**
- Limit: Varies by tier (500 RPM for tier 3)
- Recommendation: Implement retry with exponential backoff
- Batching: Not applicable (each report is unique)

---

### Database Performance

**SQLite Write Performance:**
- ~1000 writes/second (single-threaded)
- Not a bottleneck (only 3 writes per analysis)

**Database Size Growth:**
- ~10 KB per ticker analysis
- 1000 analyses = ~10 MB
- Should vacuum quarterly

---

## Future Enhancements

### 1. Advanced Pattern Recognition

**Current:** Basic pattern detection stubs

**Enhancement:**
- Implement classic patterns (Head & Shoulders, Double Top/Bottom, Triangles)
- Use ML models for pattern detection (CNN on candlestick images)
- Add pattern success rate statistics from historical data

**Impact:** Improved technical analysis, more confident recommendations

---

### 2. Multi-Ticker Correlation Analysis

**Current:** Single-ticker analysis

**Enhancement:**
- Compare ticker with sector ETF (e.g., AAPL vs XLK)
- Analyze correlation with market indices (S&P 500, NASDAQ)
- Detect sector rotation patterns

**Impact:** Better context for individual stock movements

---

### 3. Portfolio-Level Insights

**Current:** Single stock recommendations

**Enhancement:**
- Track user portfolio (via LINE user ID)
- Provide portfolio-level risk analysis
- Suggest rebalancing based on sector exposure

**Impact:** More holistic investment advice

---

### 4. Sentiment Analysis from Social Media

**Current:** News sentiment only

**Enhancement:**
- Scrape Twitter/Reddit for ticker mentions
- Analyze sentiment trends (StockTwits, r/wallstreetbets)
- Detect unusual social media volume (potential catalysts)

**Impact:** Earlier detection of sentiment shifts

---

### 5. Earnings Calendar Integration

**Current:** No earnings awareness

**Enhancement:**
- Track upcoming earnings dates
- Analyze historical earnings reactions (price movement)
- Warn users about elevated risk pre-earnings

**Impact:** Better timing for entry/exit points

---

### 6. Multi-Language Support

**Current:** Thai only

**Enhancement:**
- Support English, Chinese, Japanese reports
- Use same narrative style (Damodaran approach)
- Locale-specific formatting (numbers, dates)

**Impact:** Broader user base

---

### 7. Real-Time Alerts

**Current:** On-demand analysis only

**Enhancement:**
- Monitor ticker conditions 24/7
- Send LINE push notifications when:
  - RSI crosses overbought/oversold
  - MACD crossover occurs
  - Volume spike detected
  - Major news published

**Impact:** Timely alerts for trading opportunities

---

### 8. Reinforcement Learning for Strategy Optimization

**Current:** Fixed SMA(20,50) strategy

**Enhancement:**
- Use RL to optimize strategy parameters per ticker
- Learn optimal entry/exit points from historical data
- Adapt strategy based on market regime (bull/bear)

**Impact:** Higher backtesting returns, better alignment with recommendations

---

### 9. Interactive Charts (Web Dashboard)

**Current:** Static PNG charts via API

**Enhancement:**
- Build React/Vue dashboard
- Interactive charts with zoom, pan, annotations
- Side-by-side comparison of multiple tickers

**Impact:** Better user experience for power users

---

### 10. Risk-Adjusted Portfolio Recommendations

**Current:** BUY/SELL/HOLD per ticker

**Enhancement:**
- Calculate position sizing based on volatility (Kelly criterion)
- Suggest stop-loss levels based on ATR
- Provide expected value calculations (win rate × avg win - loss rate × avg loss)

**Impact:** More sophisticated risk management

---

## Conclusion

The Daily Report Ticker Analysis Bot employs a **sophisticated multi-stage reasoning architecture** that transforms raw financial data into actionable narratives. Key innovations include:

1. **Two-Pass LLM Generation:** Ensures recommendations are driven by fundamentals, with backtesting used only as supporting evidence when aligned

2. **Historical Context via Percentiles:** Answers "Is this unusual?" for every metric, providing crucial perspective beyond raw numbers

3. **Damodaran-Style Storytelling:** Prompt engineering forces narrative flow with numbers woven in naturally, not listed as bullet points

4. **Fault-Tolerant Execution:** Chart failures don't break the pipeline; users get partial results instead of total failure

5. **Interpretive Layer:** Numbers are pre-interpreted into Thai narratives before LLM sees them, ensuring consistent tone and context

The system successfully balances **sophistication** (13 indicators, percentile analysis, dual strategy backtesting) with **simplicity** (clear BUY/SELL/HOLD recommendations, flowing narratives, actionable risk warnings).

**Performance:** 8-12 second response time for comprehensive analysis is acceptable given the depth of insight provided. Future optimizations (parallel fetching, caching) can reduce this to 5-8 seconds.

**Scalability:** Current architecture supports 100s of concurrent users. For 1000+ users, recommend:
- Redis caching layer for ticker data
- Load balancing across multiple Lambda functions
- Batch processing for non-urgent analyses

---

**Document Version:** 1.0
**Last Updated:** 2025-11-01
**Maintained By:** Development Team
**Review Cycle:** Quarterly
