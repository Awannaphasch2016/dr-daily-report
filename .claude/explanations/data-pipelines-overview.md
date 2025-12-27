# Explanation: Data Pipeline Architecture

**Audience**: Beginner
**Format**: Tutorial
**Last updated**: 2025-12-24

---

## Quick Summary

This project has **two separate data pipelines** that collect different types of financial data and store them in Aurora MySQL database:

1. **Yahoo Finance Pipeline** - Collects **price data and news** (daily stock prices, company info, news articles)
2. **Fund Data Pipeline** - Collects **fundamental metrics** (P/E ratio, ROE, dividend yield, analyst targets)

Both pipelines run automatically and store data in Aurora so that when users request reports, the data is already available (fast response!).

---

## Why Do We Need Two Different Data Sources?

Think of it like getting information about a car:

- **Yahoo Finance** = Looking at the speedometer, gas gauge, and recent news about the car
  - Current price (like speed right now)
  - Price history (like trip log)
  - News articles (like car reviews)

- **Fund Data** = Looking under the hood for technical specs
  - P/E ratio (like miles-per-gallon efficiency)
  - ROE (like horsepower)
  - Dividend yield (like warranty coverage)
  - Target price (like trade-in value estimate)

We need BOTH to create a complete financial report!

---

## Pipeline 1: Yahoo Finance Data (Price & News)

### What Data Does It Collect?

```
For each stock (e.g., NVDA, DBS, TSLA):
├─ Price History (365 days)
│  ├─ Date
│  ├─ Open, High, Low, Close
│  └─ Volume
│
├─ Company Information
│  ├─ Company name
│  ├─ Sector
│  ├─ Market cap
│  └─ Description
│
└─ News Articles (up to 20 recent)
   ├─ Title
   ├─ Publisher
   ├─ Link
   └─ Publish date
```

### How Does the Pipeline Work?

**Step-by-step flow:**

```
1. TRIGGER (Daily at 5 AM Bangkok)
   EventBridge (AWS alarm clock) wakes up Scheduler Lambda
   ↓

2. SCHEDULER LAMBDA
   "Hey DataFetcher, go get data for these 46 tickers!"
   ↓

3. DATA FETCHER
   For each ticker:
   - Call Yahoo Finance API → Get price history
   - Call Yahoo Finance API → Get company info
   - Call Yahoo Finance API → Get news articles
   ↓

4. STORAGE (Multiple destinations)
   ┌─ Aurora MySQL (ticker_data table) ← PRIMARY STORAGE
   ├─ S3 Data Lake (raw/yahoo_finance/) ← Backup/archive
   └─ S3 Cache (for faster lookups) ← Temporary
   ↓

5. DONE!
   All 46 tickers now have fresh data in database
```

**In Code** (simplified):

```python
# Scheduler Lambda runs daily
def lambda_handler(event, context):
    # Step 1: Get list of tickers to fetch
    tickers = ['NVDA', 'DBS', 'TSLA', ...]  # 46 total

    # Step 2: Fetch data for each ticker
    for ticker in tickers:
        # Call Yahoo Finance API
        data = fetch_from_yahoo_finance(ticker)

        # Store to Aurora database
        store_to_aurora(ticker, data)

        # Also save to S3 for backup
        save_to_s3_data_lake(ticker, data)
```

**Real File**: `src/scheduler/ticker_fetcher.py:133-220`

---

## Pipeline 2: Fund Data (Fundamental Metrics)

### What Data Does It Collect?

```
For each stock:
├─ Valuation Metrics
│  ├─ FY1_PE (Forward P/E ratio)
│  ├─ P/E (Current P/E ratio)
│  └─ P/BV (Price to Book Value)
│
├─ Profitability Metrics
│  ├─ ROE (Return on Equity)
│  ├─ ROA (Return on Assets)
│  └─ Profit margins
│
├─ Income Metrics
│  └─ FY1_DIV_YIELD (Dividend yield)
│
├─ Analyst Data
│  └─ TARGET_PRC (Analyst target price)
│
└─ Classification
   └─ SECTOR (Industry sector)
```

### How Does the Pipeline Work?

**Step-by-step flow:**

```
1. EXTERNAL SOURCE
   OnPrime system (external database) exports CSV file
   ↓

2. UPLOAD TO S3
   CSV file uploaded to S3 Data Lake bucket
   Example: s3://data-lake-dev/raw/sql_server/fund_data/2025-12-09/export.csv
   ↓

3. S3 EVENT NOTIFICATION
   S3 automatically sends message to SQS queue:
   "Hey! New file arrived at this location!"
   ↓

4. ETL LAMBDA (triggered by SQS)
   - Download CSV from S3
   - Parse CSV (handle encoding, convert types)
   - Validate data
   ↓

5. BATCH UPSERT TO AURORA
   Insert or update fund_data table
   (If ticker already exists, update it; if new, insert it)
   ↓

6. DONE!
   Fundamental metrics now available in database
```

**In Code** (simplified):

```python
# ETL Lambda triggered when CSV arrives
def lambda_handler(event, context):
    # Step 1: Extract S3 location from SQS message
    bucket = event['bucket']  # e.g., 'data-lake-dev'
    key = event['key']        # e.g., 'raw/fund_data/export.csv'

    # Step 2: Download CSV file
    csv_content = download_from_s3(bucket, key)

    # Step 3: Parse CSV into structured records
    records = parse_csv(csv_content)
    # records = [
    #     {'ticker': 'NVDA', 'col_code': 'FY1_PE', 'value': 39.52},
    #     {'ticker': 'NVDA', 'col_code': 'ROE', 'value': 12.5},
    #     ...
    # ]

    # Step 4: Save to Aurora database
    batch_upsert_to_aurora(records)
```

**Real File**: `src/data/etl/fund_data_sync.py:71-133`

---

## Storage: Where Does Data Live?

### Aurora MySQL Database (PRIMARY STORAGE)

```
ticker_data_db
├─ ticker_data table (Yahoo Finance data)
│  ├─ symbol (e.g., 'NVDA')
│  ├─ data_date (e.g., '2025-12-24')
│  ├─ price_history (JSON: array of daily prices)
│  ├─ company_info (JSON: company details)
│  └─ created_at, updated_at
│
└─ fund_data table (Fundamental metrics)
   ├─ ticker (e.g., 'NVDA')
   ├─ d_trade (trading date)
   ├─ col_code (metric name, e.g., 'FY1_PE')
   ├─ value_numeric (number value, e.g., 39.52)
   ├─ value_text (text value, e.g., 'Technology')
   └─ source, updated_at
```

**Why Aurora?**
- ✅ Fast queries (<50ms)
- ✅ Can handle complex SQL joins
- ✅ Reliable (AWS managed)
- ✅ Supports JSON columns (for flexible price history)

### S3 Data Lake (BACKUP & ARCHIVE)

```
s3://dr-daily-report-data-lake-dev/
├─ raw/yahoo_finance/
│  └─ 2025-12-24/
│     ├─ NVDA.json
│     ├─ DBS.json
│     └─ ...
│
└─ raw/sql_server/fund_data/
   └─ 2025-12-09/
      └─ export.csv
```

**Why S3 Data Lake?**
- ✅ Preserve original API responses (data lineage)
- ✅ Cheap long-term storage
- ✅ Can reprocess if needed
- ✅ Compliance/audit trail

---

## Complete Data Flow Diagram

```
┌────────────────────────────────────────────────────────────────┐
│                    DATA SOURCES (External)                      │
├────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Yahoo Finance API          OnPrime Database (SQL Server)      │
│  ├─ Price data              ├─ P/E ratios                      │
│  ├─ Company info            ├─ ROE, ROA                        │
│  └─ News articles           └─ Analyst targets                 │
│                                                                 │
└──────┬──────────────────────────────────┬───────────────────────┘
       │                                  │
       │ Daily at 5 AM                    │ When CSV uploaded
       ↓                                  ↓
┌─────────────────────┐          ┌─────────────────────┐
│  Scheduler Lambda   │          │   S3 Data Lake      │
│  (ticker_fetcher)   │          │   (CSV storage)     │
└──────┬──────────────┘          └──────┬──────────────┘
       │                                │
       │ Fetch via yfinance             │ S3 Event Notification
       │                                │
       ↓                                ↓
┌─────────────────────┐          ┌─────────────────────┐
│  DataFetcher        │          │   SQS Queue         │
│  (API wrapper)      │          │   (event buffer)    │
└──────┬──────────────┘          └──────┬──────────────┘
       │                                │
       │                                │ Trigger Lambda
       │                                ↓
       │                         ┌─────────────────────┐
       │                         │  ETL Lambda         │
       │                         │  (fund_data_sync)   │
       │                         └──────┬──────────────┘
       │                                │
       │ Store                          │ Parse & Upsert
       ↓                                ↓
┌──────────────────────────────────────────────────────────────┐
│              AURORA MySQL (PRIMARY STORAGE)                   │
├──────────────────────────────────────────────────────────────┤
│  ticker_data table          fund_data table                  │
│  ├─ Price history            ├─ FY1_PE                       │
│  ├─ Company info             ├─ P/E, P/BV                    │
│  └─ News                     └─ ROE, TARGET_PRC              │
└───────┬──────────────────────────────────────────────────────┘
        │
        │ User requests report
        ↓
┌──────────────────────┐
│  Report Generator    │
│  (reads from Aurora) │
└──────────────────────┘
        │
        │ Fast response (<500ms)
        ↓
┌──────────────────────┐
│  User (Telegram)     │
└──────────────────────┘
```

---

## How User Requests Work (Aurora-First Pattern)

When a user asks for a stock report:

```
1. User: "Give me NVDA report" (via Telegram)
   ↓

2. API checks Aurora database:
   ┌─ Query ticker_data → Get price history + news
   └─ Query fund_data → Get P/E, ROE, etc.
   ↓

3. Combine data + Generate report with AI
   ↓

4. Send report to user (takes ~300ms)
```

**Key Point**: API does NOT call Yahoo Finance or OnPrime during user request!
All data is pre-fetched (already in Aurora) so responses are super fast.

---

## Try It Yourself

### Exercise 1: Check Latest Yahoo Finance Data

```bash
# Connect to Aurora (assumes SSM tunnel running)
mysql -h localhost -P 3307 -u admin -p

# See latest ticker data
SELECT
  symbol,
  data_date,
  JSON_LENGTH(price_history) as days,
  created_at
FROM ticker_data
ORDER BY created_at DESC
LIMIT 5;

# Expected output:
# symbol | data_date  | days | created_at
# NVDA   | 2025-12-24 | 365  | 2025-12-24 05:10:23
# AAPL   | 2025-12-24 | 365  | 2025-12-24 05:10:45
# ...
```

### Exercise 2: Check Latest Fund Data

```bash
# See latest fundamental metrics
SELECT
  ticker,
  d_trade,
  col_code,
  value_numeric
FROM fund_data
WHERE ticker = 'NVDA'
AND d_trade = (SELECT MAX(d_trade) FROM fund_data WHERE ticker = 'NVDA')
ORDER BY col_code;

# Expected output:
# ticker | d_trade    | col_code      | value_numeric
# NVDA   | 2025-12-18 | FY1_DIV_YIELD | 0.712
# NVDA   | 2025-12-18 | FY1_PE        | 39.52
# NVDA   | 2025-12-18 | P/BV          | 4.32
# NVDA   | 2025-12-18 | P/E           | 44.00
# ...
```

### Exercise 3: Trace a Manual Scheduler Run

```bash
# Trigger scheduler manually (test mode - only 2 tickers)
aws lambda invoke \
  --function-name dr-daily-report-ticker-scheduler-dev \
  --payload '{"tickers":["NVDA","AAPL"]}' \
  /tmp/scheduler-test.json

# Check response
cat /tmp/scheduler-test.json | jq .

# Expected:
# {
#   "statusCode": 200,
#   "body": {
#     "success_count": 2,
#     "failed_count": 0,
#     "duration_seconds": 1.5
#   }
# }

# Verify data arrived in Aurora
mysql -h localhost -P 3307 -u admin -p -e \
  "SELECT symbol, data_date, created_at FROM ticker_data WHERE symbol IN ('NVDA','AAPL') ORDER BY created_at DESC LIMIT 2;"
```

---

## Common Questions

### Q: Why do we fetch data at 5 AM Bangkok time?
**A**: Stock markets close in the evening (US markets close around 4:00 AM Bangkok time). We fetch at 5 AM to ensure we get complete end-of-day data.

### Q: What happens if Yahoo Finance API is down?
**A**: The scheduler has retry logic with exponential backoff:
- Try 1: Immediate
- Try 2: Wait 2 seconds
- Try 3: Wait 4 seconds
- Try 4: Wait 8 seconds
- Give up after 4 attempts

The ticker is marked as "failed" but other tickers continue processing.

### Q: How often does fund data update?
**A**: It depends on when OnPrime exports the CSV file. Usually weekly or when there are significant updates to fundamental metrics.

### Q: Can we fetch data for tickers not in the 46 ticker list?
**A**: Not automatically. The scheduler only fetches the 46 tickers defined in `data/tickers.csv`. To add a new ticker, you need to:
1. Add it to `tickers.csv`
2. Wait for next scheduler run (or trigger manually)

### Q: What if Aurora database is down?
**A**: The scheduler will FAIL and log errors. Aurora is the primary storage - without it, the system cannot work. The S3 Data Lake has backups we can use to rebuild Aurora if needed.

---

## Key Takeaways

1. **Two data sources** = Two different types of financial data
   - Yahoo Finance: Prices + News (daily updates)
   - Fund Data: Fundamental metrics (weekly updates)

2. **Two separate pipelines** = Different triggers and flows
   - Yahoo: Scheduled daily at 5 AM
   - Fund Data: Triggered when CSV uploaded to S3

3. **Aurora is the source of truth** = User APIs only read from Aurora
   - No external API calls during user requests
   - Fast, predictable response times

4. **S3 Data Lake is backup** = Preserves original data
   - Can reprocess if needed
   - Audit trail for compliance

5. **Automation is key** = Everything runs automatically
   - No manual intervention needed
   - Monitoring alerts if anything fails

---

## Sources

**From this project:**
- CLAUDE.md: Aurora-First Data Architecture principle
- Code: `src/scheduler/ticker_fetcher.py:133-220` (Yahoo Finance pipeline)
- Code: `src/data/etl/fund_data_sync.py:71-133` (Fund Data ETL)
- Code: `src/data/data_fetcher.py:1-100` (Yahoo Finance API wrapper)
- Code: `src/data/aurora/fund_data_fetcher.py:19-128` (Fund Data query service)

**Architecture:**
- EventBridge daily trigger (5 AM Bangkok)
- Step Functions for parallel processing
- SQS for event-driven ETL

---

*Explanation generated by `/explain "data pipelines"`*
*Generated: 2025-12-24*
