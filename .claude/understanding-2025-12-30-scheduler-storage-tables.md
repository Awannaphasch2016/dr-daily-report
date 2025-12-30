---
concept: "Which table does scheduler store data to?"
date: 2025-12-30
audience: intermediate
related_to:
  - Aurora-First Data Architecture (CLAUDE.md:43)
  - ticker_fetcher.py refactoring analysis
  - enable_aurora flag removal
---

# Understanding: Scheduler Data Storage Tables

**Question**: Which table does the scheduler store data to?

**Short Answer**: The scheduler stores data to **`ticker_data`** table (primary, modern integration) and optionally to **`ticker_info`** and **`daily_prices`** tables (legacy integration, currently disabled).

---

## Mental Model (What/How/Why)

### What it is

The **scheduler** (implemented in `src/scheduler/ticker_fetcher.py`) is a Lambda function triggered by EventBridge Scheduler to fetch ticker data from Yahoo Finance every day at 5 AM Bangkok time.

**Two storage paths exist**:

1. **Modern Path (ENABLED)**: `PrecomputeService` → `ticker_data` table
2. **Legacy Path (DISABLED)**: `TickerRepository` → `ticker_info` + `daily_prices` tables

### How it works

**Modern Path (Current, Always Enabled)**:

```python
# src/scheduler/ticker_fetcher.py:72-83
# PrecomputeService is ALWAYS initialized (no feature flag)
from src.data.aurora.precompute_service import PrecomputeService
self.precompute_service = PrecomputeService()
logger.info("PrecomputeService initialized for ticker_data storage")
```

**Data flow**:
```
Yahoo Finance API
  ↓
ticker_fetcher.py (Lambda)
  ↓
PrecomputeService.store_ticker_data()
  ↓
INSERT INTO ticker_data (
  symbol, date, price_history, company_info, financials_json
)
```

**Legacy Path (Disabled by Default)**:

```python
# src/scheduler/ticker_fetcher.py:60
# TickerRepository only initialized if enable_aurora=True
self.enable_aurora = os.environ.get('AURORA_ENABLED', 'false').lower() == 'true'

if self.enable_aurora:  # FALSE in production
    from src.data.aurora import TickerRepository
    self._aurora_repo = TickerRepository()
```

**Data flow (when enabled)**:
```
Yahoo Finance API
  ↓
ticker_fetcher.py (Lambda)
  ↓
TickerRepository.upsert_ticker_info()
  ↓
INSERT INTO ticker_info (symbol, display_name, company_name, ...)
  +
TickerRepository.bulk_upsert_from_dataframe()
  ↓
INSERT INTO daily_prices (symbol, date, open, high, low, close, volume)
```

### Why it exists

**Historical context**:

1. **Phase 1 (Legacy)**: S3-First Architecture
   - Ticker data stored in S3 cache
   - Optional Aurora integration via `enable_aurora` flag
   - Tables: `ticker_info` (metadata) + `daily_prices` (OHLCV rows)

2. **Phase 2 (Migration)**: Aurora-First Architecture
   - New principle: "Aurora is source of truth"
   - `ticker_data` table introduced (denormalized, stores everything as JSON)
   - `PrecomputeService` added (always-on integration)
   - **But**: Old `TickerRepository` code NOT removed

3. **Phase 3 (Current)**: Inconsistent State
   - Modern path works (ticker_data populated daily)
   - Legacy path disabled (ticker_info empty, daily_prices not used)
   - Technical debt: Two Aurora integrations coexist

**Why ticker_data is better**:

- **Denormalized**: All data in one table (price_history, company_info, financials)
- **JSON storage**: Flexible schema (no ALTER TABLE for new fields)
- **Expiration**: `expires_at` field for automatic cache invalidation
- **Semantic naming**: "ticker_data" not "ticker_data_cache" (Aurora is ground truth)

**Why legacy path was kept** (originally):

- Backward compatibility concerns
- Gradual migration strategy
- Uncertainty about new approach

**Why legacy path should be removed** (now):

- ticker_info table: **0 rows** (never populated)
- daily_prices table: Not used by scheduler
- Production APIs: Load from ticker_data, not ticker_info
- Violates Aurora-First principle (opt-in vs always-on)

### Relationships

**Tables in scheduler data flow**:

```
ticker_master (reference data)
  ↓ ticker_master_id
ticker_data (PRIMARY - scheduler writes here)
  ├── symbol (VARCHAR)
  ├── date (DATE)
  ├── price_history (JSON) ← 1 year OHLCV data (~365 rows)
  ├── company_info (JSON) ← Metadata from Yahoo Finance
  └── financials_json (JSON) ← Financial statements

ticker_info (LEGACY - scheduler does NOT write here currently)
  ├── symbol
  ├── display_name
  ├── company_name
  └── ... (metadata fields)

daily_prices (LEGACY - scheduler does NOT write here currently)
  ├── symbol
  ├── date
  ├── open, high, low, close, volume
  └── ... (OHLCV fields)
```

**Related concepts**:
- Aurora-First Data Architecture (CLAUDE.md:43)
- PrecomputeService (modern integration)
- TickerRepository (legacy integration)
- enable_aurora flag (technical debt)
- EventBridge Scheduler (trigger mechanism)

---

## Explanation for Intermediate Audience

### Current State: One Active Table

**The scheduler stores data to the `ticker_data` table.**

**Table structure**:

```sql
CREATE TABLE ticker_data (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    ticker_master_id BIGINT NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    date DATE NOT NULL,

    -- Data stored as JSON (flexible schema)
    price_history JSON NOT NULL,      -- 1-year OHLCV data (~365 rows)
    company_info JSON,                 -- Metadata from Yahoo Finance
    financials_json JSON,              -- Financial statements

    -- Metadata
    history_start_date DATE,           -- First date in price_history
    history_end_date DATE,             -- Last date in price_history
    row_count INT,                     -- Number of price rows

    -- Timestamps
    fetched_at TIMESTAMP NOT NULL,     -- When data was fetched
    expires_at TIMESTAMP NULL,         -- When data expires (next day 8AM Bangkok)

    UNIQUE KEY (symbol, date)
);
```

**How data gets there**:

1. **EventBridge Scheduler** triggers Lambda at 5 AM Bangkok daily
2. **Lambda** (`ticker_fetcher.py`) fetches data from Yahoo Finance for 46 tickers
3. **PrecomputeService.store_ticker_data()** writes to Aurora:
   ```python
   self.precompute_service.store_ticker_data(
       symbol="DBS19",
       data_date=datetime.now(bangkok_tz).date(),
       price_history=[...],  # 1 year of OHLCV data
       company_info={...},   # Company metadata
       financials=None       # Financial statements
   )
   ```
4. **Aurora** stores data as JSON in `ticker_data` table
5. **APIs** query `ticker_data` to generate reports

**Example data** (what gets stored):

```json
{
  "symbol": "DBS19",
  "date": "2025-12-30",
  "price_history": [
    {"date": "2024-12-30", "open": 35.0, "high": 36.0, "low": 34.5, "close": 35.8, "volume": 1000000},
    {"date": "2024-12-31", "open": 35.8, "high": 36.5, "low": 35.2, "close": 36.2, "volume": 1200000},
    // ... ~365 rows total
  ],
  "company_info": {
    "shortName": "DBS Group Holdings",
    "longName": "DBS Group Holdings Ltd",
    "exchange": "SGX",
    "currency": "SGD",
    "sector": "Financial Services",
    "industry": "Banks - Regional"
  },
  "fetched_at": "2025-12-30 05:00:00",
  "expires_at": "2025-12-31 08:00:00"  // Next day 8AM Bangkok
}
```

### Legacy Tables (Not Currently Used)

**Two other tables exist but are NOT populated by the scheduler**:

1. **`ticker_info`** (metadata table)
   - **Status**: Empty (0 rows)
   - **Why**: `enable_aurora` flag defaults to False
   - **AURORA_ENABLED env var**: Not set in Lambda

2. **`daily_prices`** (normalized price data)
   - **Status**: Has data, but NOT from scheduler
   - **Source**: Other parts of system (precompute worker, migrations)
   - **Why scheduler doesn't use it**: Legacy path disabled

**Historical note**: These tables were part of the original S3-First architecture. When Aurora-First architecture was introduced, `ticker_data` replaced them, but the old code path was kept for "backward compatibility." In practice, the legacy path has never been enabled in production.

---

## Code References

### Modern Path (Active)

**Initialization** (always enabled):
```python
# src/scheduler/ticker_fetcher.py:72-83
# PrecomputeService for ticker_data table (ground truth storage)
# Always enabled - Aurora is the primary data store
try:
    from src.data.aurora.precompute_service import PrecomputeService
    self.precompute_service = PrecomputeService()
    logger.info("PrecomputeService initialized for ticker_data storage")
except Exception as e:
    logger.error(f"Failed to initialize PrecomputeService: {e}")
    self.precompute_service = None
```

**Storage** (unconditional):
```python
# src/scheduler/ticker_fetcher.py:164-196
# Store to Aurora ticker_data table (PRIMARY STORAGE - GROUND TRUTH)
# This must succeed before other storage operations
if self.precompute_service:
    try:
        self.precompute_service.store_ticker_data(
            symbol=ticker,
            data_date=datetime.now(bangkok_tz).date(),
            price_history=price_history,
            company_info=company_info,
            financials=None
        )
        logger.info(f"✅ Stored {ticker} to Aurora ticker_data table ({len(price_history)} rows)")
    except Exception as e:
        logger.error(f"Failed to store {ticker} to Aurora ticker_data: {e}")
```

**Implementation**:
```python
# src/data/aurora/precompute_service.py:1458-1536
def store_ticker_data(
    self,
    symbol: str,
    data_date: date,
    price_history: List[Dict[str, Any]],
    company_info: Optional[Dict[str, Any]] = None,
    financials: Optional[Dict[str, Any]] = None
) -> int:
    """Store ticker data in Aurora (primary data store)."""

    query = """
        INSERT INTO ticker_data (
            ticker_master_id, symbol, date, fetched_at,
            price_history, company_info, financials_json,
            history_start_date, history_end_date, row_count,
            expires_at
        ) VALUES (
            %s, %s, %s, NOW(), %s, %s, %s, %s, %s, %s, %s
        )
        ON DUPLICATE KEY UPDATE
            price_history = VALUES(price_history),
            company_info = VALUES(company_info),
            financials_json = VALUES(financials_json),
            fetched_at = NOW()
    """

    return self.client.execute(query, params, commit=True)
```

### Legacy Path (Disabled)

**Initialization** (gated by flag):
```python
# src/scheduler/ticker_fetcher.py:60-70
# Aurora MySQL integration (optional)
self.enable_aurora = enable_aurora or os.environ.get('AURORA_ENABLED', 'false').lower() == 'true'
self._aurora_repo = None

if self.enable_aurora:  # FALSE in production (AURORA_ENABLED not set)
    try:
        from src.data.aurora import TickerRepository
        self._aurora_repo = TickerRepository()
        logger.info("Aurora MySQL integration enabled")
    except Exception as e:
        logger.warning(f"Failed to initialize Aurora repository: {e}")
        self.enable_aurora = False
```

**Storage** (conditional, never executed):
```python
# src/scheduler/ticker_fetcher.py:240-244
# Store in Aurora MySQL (optional)
aurora_rows = 0
if self.enable_aurora and self._aurora_repo:  # FALSE, skipped
    aurora_rows = self._write_to_aurora(yahoo_ticker, data)
```

**Implementation** (unused):
```python
# src/scheduler/ticker_fetcher.py:262-303
def _write_to_aurora(self, ticker: str, data: Dict[str, Any]) -> int:
    """Write ticker data to Aurora MySQL via TickerRepository."""

    # Upsert ticker info
    self._aurora_repo.upsert_ticker_info(
        symbol=ticker,
        display_name=info.get('shortName', ticker),
        company_name=info.get('longName'),
        # ... more fields
    )

    # Upsert historical prices
    rows = self._aurora_repo.bulk_upsert_from_dataframe(ticker, history)

    return rows
```

---

## Verification

### Check what data exists in Aurora

```bash
# 1. Start SSM tunnel to Aurora
just aurora::tunnel  # In separate terminal

# 2. Query ticker_data (modern, should have data)
just aurora::query "SELECT symbol, date, row_count, fetched_at FROM ticker_data WHERE date = '2025-12-30' LIMIT 5"

# Expected output:
# symbol | date       | row_count | fetched_at
# DBS19  | 2025-12-30 | 250       | 2025-12-30 05:00:15
# D05.SI | 2025-12-30 | 250       | 2025-12-30 05:00:18
# ...

# 3. Query ticker_info (legacy, should be empty)
just aurora::query "SELECT COUNT(*) as total FROM ticker_info"

# Expected output:
# total
# 0

# 4. Verify ticker_data contains all tickers
just aurora::query "SELECT COUNT(DISTINCT symbol) as tickers FROM ticker_data WHERE date = '2025-12-30'"

# Expected output:
# tickers
# 46
```

### Check Lambda execution logs

```bash
# Check logs for "Stored to Aurora ticker_data" messages
ENV=dev doppler run -- aws logs filter-log-events \
  --log-group-name /aws/lambda/dr-daily-report-ticker-scheduler-dev \
  --start-time $(date -d '1 hour ago' +%s)000 \
  --filter-pattern "ticker_data"

# Expected output:
# ✅ Stored DBS19 to Aurora ticker_data table (250 rows)
# ✅ Stored D05.SI to Aurora ticker_data table (250 rows)
# ... (46 tickers)
```

---

## Key Takeaways

1. **Scheduler writes to `ticker_data` table** (primary storage, always enabled)
2. **Scheduler does NOT write to `ticker_info` or `daily_prices`** (legacy path disabled)
3. **Two Aurora integrations coexist**:
   - Modern: PrecomputeService → ticker_data (ACTIVE)
   - Legacy: TickerRepository → ticker_info + daily_prices (DISABLED)
4. **ticker_data stores everything as JSON** (denormalized, flexible schema)
5. **ticker_info is empty** (0 rows, never populated by scheduler)
6. **Legacy path is technical debt** (violates Aurora-First principle, should be removed)

---

## Related Documents

- **Refactoring Analysis**: `.claude/skills/refacter/analysis-2025-12-30-enable-aurora-legacy-path.md`
- **Validation**: `.claude/validations/2025-12-30-ticker-info-data-populated.md`
- **Architecture Principle**: `.claude/CLAUDE.md:43` (Aurora-First Data Architecture)
- **Migration**: `db/migrations/012_rename_ticker_data_cache.sql` (ticker_data_cache → ticker_data)
- **Table Schema**: `db/migrations/005_create_ticker_data_cache.sql`

---

**Understanding built**: 2025-12-30
**Audience**: Intermediate (technical team members)
**Confidence**: High (verified with code analysis + database queries)
