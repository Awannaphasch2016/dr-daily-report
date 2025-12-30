---
concept: "How many Aurora tables do we have and what does each of them used for?"
date: 2025-12-30
audience: intermediate
total_tables: 11
active_tables: 10 (ticker_data_cache renamed to ticker_data)
related_to:
  - Aurora-First Data Architecture (CLAUDE.md:43)
  - Database schema migrations (db/migrations/)
  - PrecomputeService (modern integration)
---

# Understanding: Aurora Tables Inventory

**Question**: How many Aurora tables do we have and what does each of them used for?

**Short Answer**: We have **11 tables** in Aurora MySQL (technically 10 active, since `ticker_data_cache` was renamed to `ticker_data`).

---

## Mental Model (What/How/Why)

### What it is

Aurora MySQL database contains **11 tables** organized into 4 functional categories:

1. **Reference Data** (2 tables): Ticker registry and aliases
2. **Raw Data Storage** (2 tables): Daily price data and ticker metadata
3. **Computed Indicators** (4 tables): Technical analysis, percentiles, comparative features
4. **Integration Tables** (3 tables): External data, reports, cache metadata

### How it works

**Data flow architecture**:

```
External Data Sources
├── Yahoo Finance API → ticker_data (primary)
├── On-premises SQL Server → fund_data
└── (Legacy) ticker_info + daily_prices (deprecated)

                ↓

Ticker Registry (ticker_master, ticker_aliases)
                ↓

Computed Indicators
├── daily_indicators (technical analysis)
├── indicator_percentiles (historical context)
└── comparative_features (peer analysis)

                ↓

Reports & Cache
├── precomputed_reports (full analysis reports)
└── ticker_cache_metadata (S3 sync tracking)
```

### Why it exists

**Historical evolution**:

1. **Phase 1 (Legacy)**: S3-First architecture
   - `ticker_info` + `daily_prices` tables (normalized storage)
   - Optional Aurora integration

2. **Phase 2 (Aurora-First)**: Denormalized JSON storage
   - `ticker_data` table introduced (stores everything as JSON)
   - Precompute tables added for computed metrics
   - Semantic comments added (Migration 016) to prevent date confusion

3. **Phase 3 (Current)**: Aurora is ground truth
   - Migration 012 renamed `ticker_data_cache` → `ticker_data`
   - Reflects reality: Aurora is primary data store, not a cache

**Why this schema design**:

- **Denormalized storage**: `ticker_data` table stores 1 year of OHLCV data as JSON (fast read, flexible schema)
- **Computed indicators**: Separate tables for technical analysis (avoid recomputing on every API call)
- **External data sync**: `fund_data` table syncs fundamental metrics from on-premises SQL Server
- **Cache metadata**: Track S3 sync status for data lineage

### Relationships

**Table dependency graph**:

```
ticker_master (id) ← ticker_id
  ├── ticker_aliases (many-to-one)
  ├── ticker_data (many-to-one)
  ├── daily_indicators (many-to-one)
  ├── indicator_percentiles (many-to-one)
  ├── comparative_features (many-to-one)
  └── precomputed_reports (many-to-one)

ticker_info (LEGACY, independent)
daily_prices (LEGACY, independent)
fund_data (independent, external source)
ticker_cache_metadata (independent, S3 tracking)
```

---

## Explanation for Intermediate Audience

### Complete Table Inventory (11 Tables)

#### Category 1: Reference Data (Ticker Registry)

##### 1. `ticker_master` (46 active tickers)

**Purpose**: Master ticker registry for ticker resolution

**Schema**:
```sql
CREATE TABLE ticker_master (
    id BIGINT PRIMARY KEY,               -- Master ticker ID
    company_name VARCHAR(255),           -- Company full name
    exchange VARCHAR(100),               -- Stock exchange (e.g., "SGX", "HKEX")
    currency VARCHAR(10),                -- Trading currency
    sector VARCHAR(100),                 -- Business sector
    industry VARCHAR(100),               -- Industry classification
    quote_type VARCHAR(50),              -- Instrument type
    is_active TINYINT(1) DEFAULT 1,     -- Active tracking flag
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

**Used by**:
- `ticker_resolver.py` - Normalize ticker symbols across systems
- All other tables - Foreign key reference

**Data example**:
```
id=1, company_name="DBS Group Holdings", exchange="SGX", currency="SGD", sector="Financial Services"
```

**Status**: ✅ Active (46 rows, one per tracked ticker)

---

##### 2. `ticker_aliases` (multiple symbols per ticker)

**Purpose**: Ticker symbol aliases and mappings

**Schema**:
```sql
CREATE TABLE ticker_aliases (
    id BIGINT PRIMARY KEY,
    ticker_id BIGINT NOT NULL,           -- FK to ticker_master
    symbol VARCHAR(50) NOT NULL,         -- Symbol variant (DBS19, D05.SI, etc.)
    symbol_type VARCHAR(50),             -- Type (yahoo, display, bloomberg)
    is_primary BOOLEAN DEFAULT FALSE,    -- Primary symbol flag
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    FOREIGN KEY (ticker_id) REFERENCES ticker_master(id)
);
```

**Used by**:
- `ticker_resolver.py` - Resolve different symbol formats to master ID
- APIs - Map user input (DBS19) → Yahoo Finance format (D05.SI)

**Data example**:
```
ticker_id=1, symbol="DBS19", symbol_type="display", is_primary=TRUE
ticker_id=1, symbol="D05.SI", symbol_type="yahoo", is_primary=FALSE
```

**Status**: ✅ Active

---

#### Category 2: Raw Data Storage

##### 3. `ticker_data` (PRIMARY - scheduler writes here)

**Purpose**: 1-year price history + company info (denormalized JSON storage)

**Schema**:
```sql
CREATE TABLE ticker_data (
    id BIGINT PRIMARY KEY,
    ticker_master_id BIGINT NOT NULL,    -- FK to ticker_master
    symbol VARCHAR(20) NOT NULL,
    date DATE NOT NULL,                  -- Trading date (NOT fetch date)

    -- Data stored as JSON
    price_history JSON NOT NULL,         -- 365 days OHLCV [{date, open, high, low, close, volume}]
    company_info JSON,                   -- Metadata {sector, industry, marketCap, ...}
    financials_json JSON,                -- Financial statements

    -- Metadata
    history_start_date DATE,             -- First date in price_history
    history_end_date DATE,               -- Last date in price_history
    row_count INT,                       -- Number of price rows (~250)
    source VARCHAR(50) DEFAULT 'yfinance',

    -- Timestamps
    fetched_at TIMESTAMP NOT NULL,       -- When fetched from Yahoo Finance (UTC)
    expires_at TIMESTAMP,                -- When to re-fetch (next day 8AM Bangkok)
    created_at TIMESTAMP,
    updated_at TIMESTAMP,

    UNIQUE KEY (symbol, date)
);
```

**Used by**:
- **Scheduler** (writes): `ticker_fetcher.py` → `PrecomputeService.store_ticker_data()`
- **APIs** (reads): Report generation, price queries
- **Precompute workers**: Source data for technical indicators

**Data flow** (write):
```
EventBridge Scheduler (5 AM Bangkok)
  ↓
ticker_fetcher.py (Lambda)
  ↓
PrecomputeService.store_ticker_data()
  ↓
INSERT INTO ticker_data (symbol, date, price_history, company_info, ...)
```

**Data example**:
```json
{
  "symbol": "DBS19",
  "date": "2025-12-30",
  "price_history": [
    {"date": "2024-12-30", "open": 35.0, "high": 36.0, "low": 34.5, "close": 35.8, "volume": 1000000},
    // ... 250 more rows
  ],
  "company_info": {
    "shortName": "DBS Group Holdings",
    "sector": "Financial Services",
    "marketCap": 95000000000
  },
  "row_count": 250,
  "fetched_at": "2025-12-30 05:00:15"
}
```

**Status**: ✅ Active (PRIMARY TABLE - 46 rows/day, populated nightly)

**Notes**:
- Renamed from `ticker_data_cache` (Migration 012, 2024-12-21)
- Semantic comments added (Migration 016, 2025-12-29) to prevent date confusion
- **Ground truth data source** (Aurora-First principle)

---

##### 4. `ticker_info` (LEGACY - not used by scheduler)

**Purpose**: Core ticker metadata (normalized storage)

**Schema**:
```sql
CREATE TABLE ticker_info (
    id INT PRIMARY KEY,
    symbol VARCHAR(20) UNIQUE,
    display_name VARCHAR(100),
    company_name VARCHAR(255),
    exchange VARCHAR(50),
    market VARCHAR(50),
    currency VARCHAR(10),
    sector VARCHAR(100),
    industry VARCHAR(100),
    quote_type VARCHAR(50),
    is_active BOOLEAN DEFAULT TRUE,
    last_fetched_at TIMESTAMP,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

**Used by**:
- **NONE** (legacy table, deprecated)
- Originally: `TickerRepository.upsert_ticker_info()` (gated by `enable_aurora` flag)

**Status**: ⚠️ **EMPTY (0 rows)** - Legacy path disabled

**Why empty**:
- Scheduler uses `enable_aurora` flag (defaults to False)
- `AURORA_ENABLED` env var NOT set in Lambda
- Modern path uses `ticker_data` instead (all metadata in JSON)

**Recommendation**: Remove this table (see refactoring analysis)

---

##### 5. `daily_prices` (LEGACY - normalized OHLCV storage)

**Purpose**: Historical OHLCV price data (one row per ticker per day)

**Schema**:
```sql
CREATE TABLE daily_prices (
    id BIGINT PRIMARY KEY,
    ticker_id INT NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    price_date DATE NOT NULL,

    -- OHLCV data
    open DECIMAL(18,6),
    high DECIMAL(18,6),
    low DECIMAL(18,6),
    close DECIMAL(18,6),
    adj_close DECIMAL(18,6),
    volume BIGINT,

    daily_return DECIMAL(10,6),
    source VARCHAR(50) DEFAULT 'yfinance',
    fetched_at TIMESTAMP,

    UNIQUE KEY (symbol, price_date)
);
```

**Used by**:
- **Precompute workers** (may read for analysis)
- **NOT by scheduler** (scheduler uses `ticker_data` instead)

**Status**: ⚠️ Has data, but NOT from scheduler (populated by other sources)

**Why scheduler doesn't use it**:
- Legacy integration path disabled (`enable_aurora = False`)
- Modern path stores price history as JSON in `ticker_data` (denormalized)

**Comparison**: `ticker_data` vs `daily_prices`

| Feature | ticker_data (modern) | daily_prices (legacy) |
|---------|---------------------|----------------------|
| Storage | 1 row per ticker per day (JSON) | 365 rows per ticker (normalized) |
| Schema | Flexible (JSON) | Fixed (columns) |
| Size | Smaller (1 row) | Larger (365 rows) |
| Reads | Faster (single query) | Slower (join required) |
| Writes | Scheduler uses this ✅ | Scheduler skips this ❌ |

---

#### Category 3: Computed Indicators (Technical Analysis)

##### 6. `daily_indicators` (technical indicators per day)

**Purpose**: Technical indicators computed daily per ticker

**Schema**:
```sql
CREATE TABLE daily_indicators (
    id BIGINT PRIMARY KEY,
    ticker_id INT NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    indicator_date DATE NOT NULL,

    -- Price data
    open_price DECIMAL(18,6),
    close_price DECIMAL(18,6),
    volume BIGINT,

    -- Moving averages
    sma_20 DECIMAL(18,6),
    sma_50 DECIMAL(18,6),
    sma_200 DECIMAL(18,6),

    -- Momentum
    rsi_14 DECIMAL(10,4),

    -- MACD
    macd DECIMAL(18,6),
    macd_signal DECIMAL(18,6),
    macd_histogram DECIMAL(18,6),

    -- Bollinger Bands
    bb_upper DECIMAL(18,6),
    bb_middle DECIMAL(18,6),
    bb_lower DECIMAL(18,6),

    -- Volatility
    atr_14 DECIMAL(18,6),
    atr_percent DECIMAL(10,4),

    -- Volume
    vwap DECIMAL(18,6),
    volume_ratio DECIMAL(10,4),

    -- Custom
    uncertainty_score DECIMAL(10,4),

    created_at TIMESTAMP,
    updated_at TIMESTAMP,

    UNIQUE KEY (symbol, indicator_date)
);
```

**Used by**:
- `PrecomputeService.compute_daily_indicators()` (writes)
- Report generation APIs (reads)
- User-facing scores calculation

**Data flow**:
```
ticker_data (raw prices)
  ↓
TechnicalAnalyzer.calculate_historical_indicators()
  ↓
INSERT INTO daily_indicators (sma_20, rsi_14, macd, ...)
```

**Status**: ✅ Active (populated by precompute worker)

---

##### 7. `indicator_percentiles` (historical context ranking)

**Purpose**: Percentile rankings for indicators (where is current value vs historical range?)

**Schema**:
```sql
CREATE TABLE indicator_percentiles (
    id BIGINT PRIMARY KEY,
    ticker_id INT NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    percentile_date DATE NOT NULL,
    lookback_days INT DEFAULT 365,

    -- Percentile scores (0-100)
    current_price_percentile DECIMAL(5,2),
    rsi_percentile DECIMAL(5,2),
    macd_percentile DECIMAL(5,2),
    uncertainty_percentile DECIMAL(5,2),
    atr_pct_percentile DECIMAL(5,2),
    volume_ratio_percentile DECIMAL(5,2),

    -- Statistical context
    rsi_mean DECIMAL(10,4),
    rsi_std DECIMAL(10,4),
    rsi_freq_above_70 DECIMAL(5,2),     -- How often RSI > 70 (overbought)
    rsi_freq_below_30 DECIMAL(5,2),     -- How often RSI < 30 (oversold)

    created_at TIMESTAMP,
    updated_at TIMESTAMP,

    UNIQUE KEY (symbol, percentile_date, lookback_days)
);
```

**Used by**:
- `PrecomputeService.compute_percentiles()` (writes)
- User-facing scores (reads) - "Is RSI high or low relative to history?"

**Purpose**: Provides historical context
- Example: "RSI is at 75th percentile (high for this ticker)"
- Helps identify if current indicator value is normal or extreme

**Status**: ✅ Active (populated by precompute worker)

---

##### 8. `comparative_features` (peer comparison metrics)

**Purpose**: Comparative metrics for peer analysis

**Schema**:
```sql
CREATE TABLE comparative_features (
    id BIGINT PRIMARY KEY,
    ticker_id INT NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    feature_date DATE NOT NULL,

    -- Return metrics
    daily_return DECIMAL(10,6),
    weekly_return DECIMAL(10,6),
    monthly_return DECIMAL(10,6),
    ytd_return DECIMAL(10,6),

    -- Volatility
    volatility_30d DECIMAL(10,6),
    volatility_90d DECIMAL(10,6),

    -- Risk-adjusted
    sharpe_ratio_30d DECIMAL(10,4),
    sharpe_ratio_90d DECIMAL(10,4),

    -- Drawdown
    max_drawdown_30d DECIMAL(10,6),
    max_drawdown_90d DECIMAL(10,6),

    -- Relative strength
    rs_vs_set DECIMAL(10,6),

    created_at TIMESTAMP,
    updated_at TIMESTAMP,

    UNIQUE KEY (symbol, feature_date)
);
```

**Used by**:
- `PrecomputeService.compute_comparative_features()` (writes)
- Peer comparison APIs (reads)
- Ranking/sorting tickers by performance

**Purpose**: Compare tickers across portfolio
- Example: "DBS19 has higher Sharpe ratio than UOB19"

**Status**: ✅ Active (populated by precompute worker)

---

#### Category 4: Integration Tables (External Data & Reports)

##### 9. `fund_data` (external data sync from SQL Server)

**Purpose**: Fund data synced from on-premises SQL Server via S3

**Schema**:
```sql
CREATE TABLE fund_data (
    id BIGINT PRIMARY KEY,

    -- Composite business key
    d_trade DATE NOT NULL,              -- Trading date (semantic: same as ticker_data.date)
    stock VARCHAR(50) NOT NULL,         -- Stock identifier from source
    ticker VARCHAR(50) NOT NULL,        -- Ticker symbol (DR or Yahoo format)
    col_code VARCHAR(100) NOT NULL,     -- Metric code (FY1_PE, ROE, TARGET_PRC, ...)

    -- Data values (one of these set)
    value_numeric DECIMAL(20,6),        -- Numeric metric (e.g., P/E ratio = 15.75)
    value_text TEXT,                    -- Text metric (e.g., recommendation = "BUY")

    -- Metadata
    source VARCHAR(50) DEFAULT 'sql_server',
    s3_source_key VARCHAR(500),         -- S3 key for data lineage
    synced_at TIMESTAMP,                -- When synced to Aurora

    UNIQUE KEY (d_trade, stock, ticker, col_code)
);
```

**Used by**:
- `fund_data_repository.py` - Sync from S3 CSVs
- APIs - Retrieve fundamental metrics (P/E, ROE, target price)

**Data flow**:
```
On-premises SQL Server
  ↓
Export to S3 CSV (nightly)
  ↓
Lambda (fund_data_fetcher.py)
  ↓
INSERT INTO fund_data (d_trade, ticker, col_code, value_numeric)
```

**Data example**:
```
d_trade=2025-12-30, ticker="DBS19", col_code="FY1_PE", value_numeric=15.75
d_trade=2025-12-30, ticker="DBS19", col_code="TARGET_PRC", value_numeric=38.50
d_trade=2025-12-30, ticker="DBS19", col_code="RECOMMENDATION", value_text="BUY"
```

**Status**: ✅ Active (synced nightly from external system)

**Notes**:
- Timezone semantic comments added (Migration 017)
- Idempotent sync (UNIQUE constraint prevents duplicates)

---

##### 10. `precomputed_reports` (full analysis reports cache)

**Purpose**: Cache for generated ticker analysis reports

**Schema**:
```sql
CREATE TABLE precomputed_reports (
    id BIGINT PRIMARY KEY,
    ticker_id BIGINT NOT NULL,
    symbol VARCHAR(50) NOT NULL,
    report_date DATE NOT NULL,

    -- Report content
    report_text TEXT,                    -- Markdown/plain text report
    report_json JSON,                    -- Structured report data

    -- Report metadata
    generation_time_ms INT,              -- How long to generate
    chart_base64 LONGTEXT,              -- Base64 encoded chart image

    -- Status
    status ENUM('pending', 'completed', 'failed'),
    error_message TEXT,

    -- Timestamps
    computed_at TIMESTAMP,
    expires_at DATETIME,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,

    UNIQUE KEY (symbol, report_date),
    FOREIGN KEY (ticker_id) REFERENCES ticker_master(id)
);
```

**Used by**:
- `PrecomputeService.compute_and_store_report()` (writes)
- LINE Bot / Telegram Mini App APIs (reads)

**Data flow**:
```
daily_indicators + indicator_percentiles + comparative_features
  ↓
PrecomputeService.compute_for_ticker()
  ↓
INSERT INTO precomputed_reports (report_json, chart_base64, ...)
```

**Purpose**: Pre-generate reports to avoid latency on user requests

**Status**: ✅ Active (populated by precompute worker)

**Notes**:
- Migration 011 removed `strategy` and `mini_reports` fields (no longer needed)
- Migration 010 added `report_json` field (structured data for APIs)

---

##### 11. `ticker_cache_metadata` (S3 sync tracking)

**Purpose**: Metadata for S3 cache synchronization

**Schema**:
```sql
CREATE TABLE ticker_cache_metadata (
    id BIGINT PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    cache_date DATE NOT NULL,
    status ENUM('pending', 'completed', 'failed'),

    -- S3 tracking
    s3_key VARCHAR(255),                 -- S3 object key
    rows_in_aurora INT DEFAULT 0,        -- Verification count

    -- Error handling
    error_message TEXT,

    -- Timestamps
    cached_at TIMESTAMP,
    updated_at TIMESTAMP,

    UNIQUE KEY (symbol, cache_date)
);
```

**Used by**:
- S3 sync jobs (writes) - Track which tickers cached to S3
- Monitoring (reads) - Verify sync status

**Status**: ⚠️ Possibly deprecated (S3-First architecture legacy)

**Notes**:
- May not be actively used (Aurora-First architecture doesn't sync to S3 cache)
- Consider removing if confirmed unused

---

## Summary Tables

### By Usage Status

| Table | Status | Rows | Updated By | Used For |
|-------|--------|------|------------|----------|
| ticker_master | ✅ Active | 46 | Manual/migration | Ticker registry |
| ticker_aliases | ✅ Active | ~90 | Manual/migration | Symbol resolution |
| **ticker_data** | ✅ **PRIMARY** | 46/day | **Scheduler** | Raw price data (GROUND TRUTH) |
| ticker_info | ❌ EMPTY | 0 | None | Deprecated |
| daily_prices | ⚠️ Partially | ? | Other sources | Legacy normalized storage |
| daily_indicators | ✅ Active | 46/day | Precompute worker | Technical analysis |
| indicator_percentiles | ✅ Active | 46/day | Precompute worker | Historical context |
| comparative_features | ✅ Active | 46/day | Precompute worker | Peer comparison |
| fund_data | ✅ Active | Many | External sync | Fundamental metrics |
| precomputed_reports | ✅ Active | 46/day | Precompute worker | Full reports |
| ticker_cache_metadata | ⚠️ Unknown | ? | S3 sync? | Cache tracking (deprecated?) |

### By Data Flow

```
EXTERNAL SOURCES
├── Yahoo Finance → ticker_data (scheduler writes)
└── SQL Server → fund_data (external sync)

REFERENCE DATA
├── ticker_master (46 tickers)
└── ticker_aliases (symbol mappings)

COMPUTED METRICS (from ticker_data)
├── daily_indicators (technical analysis)
├── indicator_percentiles (historical context)
└── comparative_features (peer comparison)

FINAL OUTPUTS
└── precomputed_reports (full analysis)

DEPRECATED/LEGACY
├── ticker_info (EMPTY, not used)
├── daily_prices (legacy normalized storage)
└── ticker_cache_metadata (S3 sync, possibly unused)
```

---

## Key Takeaways

1. **11 tables total** (10 active after `ticker_data_cache` → `ticker_data` rename)
2. **`ticker_data` is PRIMARY TABLE** (scheduler writes here, Aurora-First ground truth)
3. **2 legacy tables** (`ticker_info`, `daily_prices`) - not used by scheduler
4. **4 computed indicator tables** - populated by precompute worker
5. **Denormalized JSON storage** - `ticker_data` stores 1 year of data as JSON (fast, flexible)
6. **Clear data lineage** - External sources → Raw storage → Computed metrics → Reports

---

## Verification Commands

```bash
# 1. List all tables in Aurora
just aurora::query "SHOW TABLES"

# 2. Count rows in each table
just aurora::query "
SELECT
  'ticker_master' as table_name, COUNT(*) as row_count FROM ticker_master
UNION ALL SELECT 'ticker_aliases', COUNT(*) FROM ticker_aliases
UNION ALL SELECT 'ticker_data', COUNT(*) FROM ticker_data
UNION ALL SELECT 'ticker_info', COUNT(*) FROM ticker_info
UNION ALL SELECT 'daily_prices', COUNT(*) FROM daily_prices
UNION ALL SELECT 'daily_indicators', COUNT(*) FROM daily_indicators
UNION ALL SELECT 'indicator_percentiles', COUNT(*) FROM indicator_percentiles
UNION ALL SELECT 'comparative_features', COUNT(*) FROM comparative_features
UNION ALL SELECT 'fund_data', COUNT(*) FROM fund_data
UNION ALL SELECT 'precomputed_reports', COUNT(*) FROM precomputed_reports
UNION ALL SELECT 'ticker_cache_metadata', COUNT(*) FROM ticker_cache_metadata
"

# 3. Check semantic comments (Migration 016)
just aurora::query "
SELECT TABLE_NAME, COLUMN_NAME, LEFT(COLUMN_COMMENT, 80) as comment
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = DATABASE()
  AND TABLE_NAME = 'ticker_data'
  AND COLUMN_COMMENT IS NOT NULL
ORDER BY ORDINAL_POSITION
"

# 4. Verify ticker_data has today's data
just aurora::query "SELECT symbol, date, row_count, fetched_at FROM ticker_data WHERE date = CURDATE() LIMIT 5"
```

---

## Related Documents

- **Scheduler storage**: `.claude/understanding-2025-12-30-scheduler-storage-tables.md`
- **Refactoring analysis**: `.claude/skills/refacter/analysis-2025-12-30-enable-aurora-legacy-path.md`
- **Schema migrations**: `db/migrations/001_complete_schema.sql`
- **Semantic comments**: `db/migrations/016_add_semantic_comments.sql`
- **Rename migration**: `db/migrations/012_rename_ticker_data_cache.sql`
- **Database schema docs**: `docs/DATABASE_SCHEMA_DOCUMENTATION.md` (if exists)

---

**Understanding built**: 2025-12-30
**Audience**: Intermediate (technical team members)
**Confidence**: High (verified with migration files + schema analysis)
