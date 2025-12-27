# Explanation: Data Sources for Precompute Workflow

**Audience**: Beginner
**Format**: Tutorial
**Last updated**: 2025-12-24

---

## Quick Summary

The precompute workflow uses **pre-fetched data from Aurora database** (not live APIs) to generate reports. This data was already collected earlier by the scheduler at 5 AM Bangkok time. The workflow reads this cached data, runs AI analysis, and stores the final reports.

**Key Point**: Precompute doesn't fetch new data—it uses data that was already fetched and stored!

---

## Data Flow: Two Separate Phases

### PHASE 1: Data Collection (5:00 AM - 5:15 AM)
```
Scheduler Lambda runs at 5 AM
   ↓
Fetch from Yahoo Finance API (price, company info)
   ↓
Fetch from Yahoo Finance News API
   ↓
Store raw data to Aurora ticker_data table
```

### PHASE 2: Report Generation (5:15 AM - 5:25 AM)
```
Precompute workflow starts
   ↓
Read pre-fetched data from Aurora (NO API calls!)
   ↓
Run AI analysis on cached data
   ↓
Generate and store reports
```

**Why separate?**
- ✅ Faster: Data already available (no waiting for APIs)
- ✅ Reliable: APIs called once per day (not 46+ times during report gen)
- ✅ Cost-effective: Fewer API calls = lower costs

---

## Data Source #1: Aurora ticker_data Table

This is the **primary and ONLY data source** for precompute. All data comes from here!

### What's in ticker_data Table?

```sql
ticker_data
├─ symbol (e.g., 'NVDA')
├─ data_date (e.g., '2025-12-24')
├─ price_history (JSON array - 365 days of prices)
├─ company_info (JSON object - company details)
├─ financials (JSON object - balance sheet, income statement)
├─ created_at
└─ updated_at
```

### Example Data Structure

**1. Price History** (365 days)
```json
{
  "price_history": [
    {
      "Date": "2024-12-24",
      "Open": 138.50,
      "High": 142.30,
      "Low": 137.80,
      "Close": 141.75,
      "Volume": 45123000
    },
    {
      "Date": "2024-12-23",
      "Open": 136.20,
      "High": 139.10,
      "Low": 135.90,
      "Close": 138.45,
      "Volume": 42891000
    },
    // ... 363 more days
  ]
}
```

**2. Company Info**
```json
{
  "company_info": {
    "longName": "NVIDIA Corporation",
    "sector": "Technology",
    "industry": "Semiconductors",
    "marketCap": 3450000000000,
    "currency": "USD",
    "exchange": "NMS",
    "quoteType": "EQUITY",
    "previousClose": 138.45,
    "fiftyTwoWeekHigh": 152.89,
    "fiftyTwoWeekLow": 39.23,
    "averageVolume": 48567000,
    "sharesOutstanding": 24330000000,
    "dividendYield": 0.0003,
    "trailingPE": 65.23,
    "forwardPE": 42.15
  }
}
```

**3. Financials** (Optional)
```json
{
  "financials": {
    "totalRevenue": 26974000000,
    "grossProfit": 17472000000,
    "netIncome": 9243000000,
    "totalAssets": 65728000000,
    "totalDebt": 9703000000,
    "cashAndEquivalents": 25984000000
  }
}
```

---

## Data Source #2: Fund Data (Fundamental Metrics)

This comes from a separate Aurora table populated by the ETL pipeline.

### What's in fund_data Table?

```sql
fund_data
├─ ticker (e.g., 'NVDA')
├─ d_trade (trading date)
├─ col_code (metric name)
├─ value_numeric (number value)
├─ value_text (text value for SECTOR)
└─ updated_at
```

### Example Metrics

```
Ticker: NVDA
Date: 2025-12-18

| col_code      | value_numeric | Description              |
|---------------|---------------|--------------------------|
| FY1_PE        | 39.52         | Forward P/E ratio        |
| P/E           | 44.00         | Current P/E ratio        |
| P/BV          | 4.32          | Price to Book Value      |
| ROE           | 12.5          | Return on Equity (%)     |
| FY1_DIV_YIELD | 0.712         | Forward dividend yield   |
| TARGET_PRC    | 165.00        | Analyst target price     |
| SECTOR        | (text)        | "Technology"             |
```

**Note**: This data is optional for some tickers. Not all tickers have fundamental metrics.

---

## Data Source #3: News Articles

News is actually fetched LIVE during precompute (not pre-cached).

**Why?**
- News changes rapidly (within hours)
- Yahoo Finance News API is fast (~1-2 seconds)
- Only needs to be called once per ticker during precompute

### What's in News Data?

```json
{
  "news": [
    {
      "title": "NVIDIA Announces Record Q4 Earnings",
      "publisher": "Reuters",
      "link": "https://...",
      "providerPublishTime": 1703462400,
      "timestamp": "2025-12-24T10:00:00Z",
      "high_impact": true,
      "sentiment": "positive"
    },
    {
      "title": "AI Chip Demand Surges",
      "publisher": "Bloomberg",
      "link": "https://...",
      "providerPublishTime": 1703376000,
      "high_impact": true,
      "sentiment": "positive"
    }
    // ... up to 20 recent articles
  ],
  "news_summary": {
    "total_count": 18,
    "high_impact_count": 5,
    "positive_count": 12,
    "negative_count": 3,
    "neutral_count": 3
  }
}
```

---

## Complete Data Assembly: Step-by-Step

When precompute worker processes one ticker (e.g., NVDA), here's exactly what happens:

### Step 1: Read from Aurora ticker_data
```python
# Code: src/workflow/workflow_nodes.py:287-290
from src.data.aurora.precompute_service import PrecomputeService

precompute_service = PrecomputeService()
ticker_data = precompute_service.get_ticker_data(
    symbol="NVDA",
    data_date=datetime.utcnow().date()  # Today's date
)

# Returns:
# {
#   'price_history': [...365 days...],
#   'company_info': {...},
#   'financials': {...}
# }
```

### Step 2: Reconstruct Data Format
```python
# Code: src/workflow/workflow_nodes.py:305
data = self._reconstruct_data_from_aurora(ticker_data, "NVDA", "NVDA")

# Converts JSON arrays to pandas DataFrame:
# {
#   'history': pd.DataFrame(price_history),  # DataFrame with 365 rows
#   'info': company_info,                    # Dict
#   'financials': financials                 # Dict (optional)
# }
```

### Step 3: Fetch News (Live API Call)
```python
# Code: src/workflow/workflow_nodes.py:342-348
from src.data.news_fetcher import NewsFetcher

news_fetcher = NewsFetcher()
news = news_fetcher.fetch_news("NVDA", max_news=20)

# Returns list of news articles
```

### Step 4: Fetch Fundamental Metrics
```python
# Code: src/data/aurora/fund_data_fetcher.py:19-128
from src.data.aurora.fund_data_fetcher import fetch_fund_data_metrics

metrics = fetch_fund_data_metrics("NVDA")

# Returns:
# {
#   'FY1_PE': 39.52,
#   'P/E': 44.00,
#   'P/BV': 4.32,
#   'ROE': 12.5,
#   'FY1_DIV_YIELD': 0.712,
#   'TARGET_PRC': 165.00,
#   'SECTOR': 'Technology'
# }
```

### Step 5: Calculate Technical Indicators
```python
# Code: src/analysis/technical_analysis.py
from src.analysis.technical_analysis import TechnicalAnalyzer

analyzer = TechnicalAnalyzer()
indicators = analyzer.analyze(data['history'])

# Calculates:
# - Moving averages (SMA 20, SMA 50, SMA 200)
# - RSI (Relative Strength Index)
# - MACD (Moving Average Convergence Divergence)
# - Bollinger Bands
# - Volume analysis
```

### Step 6: Run Backtesting
```python
# Code: src/utils/strategy.py
from src.utils.strategy import SMAStrategyBacktester

backtester = SMAStrategyBacktester(fast_period=20, slow_period=50)
performance = backtester.backtest(data['history'])

# Returns:
# {
#   'total_return': 0.42,      # 42% return
#   'sharpe_ratio': 1.85,
#   'max_drawdown': -0.15,     # -15% max loss
#   'win_rate': 0.62,          # 62% winning trades
#   'trades': 24               # Number of trades
# }
```

### Step 7: Comparative Analysis
```python
# Code: src/analysis/comparative_analysis.py
from src.analysis.comparative_analysis import ComparativeAnalyzer

comp_analyzer = ComparativeAnalyzer()
comparative = comp_analyzer.analyze("NVDA", data)

# Compares to:
# - Sector peers (other semiconductor companies)
# - Market index (S&P 500)
# - Historical performance
```

### Step 8: Generate AI Report
```python
# Code: src/report/prompt_builder.py + LLM API
from src.report import PromptBuilder, ContextBuilder

# Build context with ALL collected data
context = ContextBuilder.build({
    'ticker_data': data,
    'indicators': indicators,
    'news': news,
    'fund_data': metrics,
    'performance': performance,
    'comparative': comparative
})

# Generate prompt
prompt = PromptBuilder.build_prompt(context)

# Call LLM (OpenRouter API)
report = llm.generate(prompt)

# Returns Thai language narrative report (~2000 words)
```

---

## Data Assembly Diagram

```
┌────────────────────────────────────────────────────────────────┐
│                    DATA SOURCES (Pre-fetched)                   │
├────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────┐ │
│  │ ticker_data      │  │ fund_data        │  │ News API     │ │
│  │ (Aurora)         │  │ (Aurora)         │  │ (Live call)  │ │
│  ├──────────────────┤  ├──────────────────┤  ├──────────────┤ │
│  │ Price history    │  │ FY1_PE: 39.52    │  │ 20 articles  │ │
│  │ Company info     │  │ P/E: 44.00       │  │ Sentiment    │ │
│  │ Financials       │  │ ROE: 12.5        │  │ Impact level │ │
│  │ (365 days)       │  │ TARGET_PRC       │  └──────────────┘ │
│  └──────────────────┘  └──────────────────┘                    │
│                                                                 │
└──────┬─────────────────────┬────────────────────┬──────────────┘
       │                     │                    │
       ↓                     ↓                    ↓
┌──────────────────────────────────────────────────────────────────┐
│              COMPUTED FEATURES (Calculated on-the-fly)            │
├──────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌──────────────────┐  ┌──────────────────┐  ┌────────────────┐ │
│  │ Technical        │  │ Backtesting      │  │ Comparative    │ │
│  │ Indicators       │  │ Results          │  │ Analysis       │ │
│  ├──────────────────┤  ├──────────────────┤  ├────────────────┤ │
│  │ SMA 20/50/200    │  │ Total return:42% │  │ vs Sector avg  │ │
│  │ RSI: 68.5        │  │ Sharpe: 1.85     │  │ vs S&P 500     │ │
│  │ MACD: 2.35       │  │ Max DD: -15%     │  │ vs Peers       │ │
│  │ Bollinger Bands  │  │ Win rate: 62%    │  │ Percentile rank│ │
│  └──────────────────┘  └──────────────────┘  └────────────────┘ │
│                                                                   │
└──────┬────────────────────────────────────────────────────────────┘
       │
       │ All data combined into context
       ↓
┌──────────────────────────────────────────────────────────────────┐
│                   AI REPORT GENERATION                            │
├──────────────────────────────────────────────────────────────────┤
│                                                                   │
│  Context Builder → Prompt Builder → LLM API (GPT-4)              │
│                                                                   │
│  Input: All data above                                           │
│  Output: Thai language narrative report (~2000 words)            │
│                                                                   │
└──────┬────────────────────────────────────────────────────────────┘
       │
       ↓
┌──────────────────────────────────────────────────────────────────┐
│                  FINAL REPORT (Stored in Aurora)                  │
├──────────────────────────────────────────────────────────────────┤
│  {                                                                │
│    "narrative_report": "## NVDA Analysis...",                    │
│    "chart_base64": "iVBORw0KGgo...",                             │
│    "user_facing_scores": {...},                                  │
│    "timing_metrics": {...},                                      │
│    "api_costs": {...}                                            │
│  }                                                                │
└──────────────────────────────────────────────────────────────────┘
```

---

## Data Freshness Timeline

| Data Type | Last Updated | Refresh Frequency | Source |
|-----------|--------------|-------------------|--------|
| **Price data** | Today 5 AM | Daily | Yahoo Finance (via scheduler) |
| **Company info** | Today 5 AM | Daily | Yahoo Finance (via scheduler) |
| **Financials** | Today 5 AM | Daily | Yahoo Finance (via scheduler) |
| **Fund data** | Last ETL run | Weekly (varies) | OnPrime database (via ETL) |
| **News** | Real-time | During precompute | Yahoo Finance News API |
| **Technical indicators** | Computed now | Every precompute run | Calculated from price data |
| **Backtesting** | Computed now | Every precompute run | Calculated from price data |
| **Comparative** | Computed now | Every precompute run | Calculated from all tickers |

---

## What Precompute Does NOT Use

❌ **Does NOT call Yahoo Finance API** during report generation
- Price data already cached in Aurora

❌ **Does NOT call external financial data APIs** during report generation
- All data pre-fetched or cached

❌ **Does NOT access S3 Data Lake** during report generation
- Aurora is the primary data source (faster)

❌ **Does NOT query external databases** during report generation
- Everything comes from Aurora MySQL

---

## Try It Yourself

### Exercise 1: Inspect Cached Ticker Data

```bash
# Connect to Aurora
mysql -h localhost -P 3307 -u admin -p

# See what data is available
SELECT
  symbol,
  data_date,
  JSON_LENGTH(price_history) as days_of_data,
  JSON_KEYS(company_info) as company_fields,
  created_at
FROM ticker_data
WHERE symbol = 'NVDA'
ORDER BY data_date DESC
LIMIT 1;

# Expected output:
# symbol | data_date  | days_of_data | company_fields         | created_at
# NVDA   | 2025-12-24 | 365          | ["longName","sector",...] | 2025-12-24 05:05:23
```

### Exercise 2: See Sample Price History

```bash
# Extract first 5 days of price data
SELECT
  symbol,
  JSON_EXTRACT(price_history, '$[0]') as latest_day,
  JSON_EXTRACT(price_history, '$[1]') as previous_day
FROM ticker_data
WHERE symbol = 'NVDA';

# Expected output (formatted):
# {
#   "Date": "2025-12-24",
#   "Open": 138.50,
#   "High": 142.30,
#   "Low": 137.80,
#   "Close": 141.75,
#   "Volume": 45123000
# }
```

### Exercise 3: Check Fund Data Availability

```bash
# See what fundamental metrics are available
SELECT
  ticker,
  col_code,
  value_numeric,
  d_trade
FROM fund_data
WHERE ticker = 'NVDA'
AND d_trade = (SELECT MAX(d_trade) FROM fund_data WHERE ticker = 'NVDA')
ORDER BY col_code;

# Expected output:
# ticker | col_code      | value_numeric | d_trade
# NVDA   | FY1_DIV_YIELD | 0.712         | 2025-12-18
# NVDA   | FY1_PE        | 39.52         | 2025-12-18
# NVDA   | P/BV          | 4.32          | 2025-12-18
# ...
```

---

## Common Questions

### Q: Why doesn't precompute fetch fresh data from Yahoo Finance?

**A**: Data was already fetched at 5 AM by the scheduler! Fetching again would be wasteful:
- ❌ Slower (5-15 seconds per ticker)
- ❌ More expensive (API costs)
- ❌ Risk hitting rate limits
- ❌ Data hasn't changed anyway (markets closed)

### Q: What if ticker_data is missing for a ticker?

**A**: The workflow **fails immediately** with a clear error:
```
"Data not available in Aurora for NVDA.
Run scheduler to populate ticker data before generating reports."
```

This is **intentional** (Aurora-First principle) - no fallback to live APIs.

### Q: How much data does each ticker have in Aurora?

**A**: For each ticker:
- Price history: 365 days (~73 KB JSON)
- Company info: ~20 fields (~5 KB JSON)
- Financials: ~30 fields (~8 KB JSON)
- **Total**: ~86 KB per ticker × 46 tickers = ~4 MB total

### Q: Is news data cached?

**A**: No! News is fetched LIVE during precompute because:
- News changes rapidly (every hour)
- News API is fast (~1-2 seconds)
- We want the freshest news for reports

### Q: Can we use stale data if Aurora is down?

**A**: No. Aurora is the **ground truth**. If Aurora is down, precompute fails. This is by design (fail-fast principle).

---

## Key Takeaways

1. **Aurora is the single source of truth**
   - All price/company data comes from Aurora ticker_data table
   - Populated nightly by scheduler at 5 AM

2. **Pre-fetched vs Real-time**
   - Price data: Pre-fetched (from 5 AM scheduler)
   - News data: Real-time (fetched during precompute)
   - Fund data: Pre-loaded (from ETL pipeline)

3. **No live API calls** (except news)
   - Yahoo Finance price API: NOT called during precompute
   - All data cached in Aurora for instant access

4. **Computed features are fresh**
   - Technical indicators: Calculated every precompute run
   - Backtesting: Run every time on latest price data
   - Comparative analysis: Recalculated with current data

5. **Fail-fast if data missing**
   - No fallback to live APIs
   - Clear error messages guide troubleshooting
   - Ensures consistent, fast performance

---

## Sources

**From this project:**
- Code: `src/workflow/workflow_nodes.py:257-327` (fetch_data node)
- Code: `src/data/aurora/precompute_service.py` (Aurora data access)
- Code: `src/data/aurora/fund_data_fetcher.py:19-128` (Fund data)
- Code: `src/data/news_fetcher.py:58-100` (News fetching)
- CLAUDE.md: Aurora-First Data Architecture principle

**Related explanations:**
- `.claude/explanations/data-pipelines-overview.md` (Data collection phase)
- `.claude/explanations/precompute-workflow-explained.md` (Workflow process)

---

*Explanation generated by `/explain "precompute data sources"`*
*Generated: 2025-12-24*
