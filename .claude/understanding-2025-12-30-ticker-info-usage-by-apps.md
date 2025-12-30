---
concept: "How do LINE Bot and Telegram Mini App use ticker_info?"
date: 2025-12-30
audience: intermediate
finding: "NEITHER app uses ticker_info table (0 rows, never queried)"
actual_usage: "Both apps use CSV file (data/tickers.csv) for ticker metadata"
related_to:
  - ticker_info vs ticker_data comparison
  - Aurora tables inventory
  - TickerService implementation
---

# Understanding: ticker_info Usage by LINE Bot and Telegram Mini App

**Question**: How do LINE Bot and Telegram Mini App use ticker_info?

**Short Answer**: **NEITHER application uses `ticker_info` table**. Both use `data/tickers.csv` file for ticker metadata instead.

---

## Mental Model (What/How/Why)

### What it is

**Current reality**:
- `ticker_info` table: EXISTS (schema defined) but EMPTY (0 rows)
- `data/tickers.csv` file: Contains all ticker metadata (46 tickers)
- **Both LINE Bot and Telegram Mini App**: Load metadata from CSV, NOT Aurora

**Why this is confusing**:
- `ticker_info` table exists in schema
- `TickerRepository` has methods to read/write `ticker_info`
- But NO production code actually queries `ticker_info`

### How it works

**Data flow for ticker metadata** (actual implementation):

```
data/tickers.csv (46 rows)
  ├── Symbol: DBS19
  ├── Ticker: D05.SI (Yahoo Finance format)
  └── (No other metadata in CSV)

        ↓

TickerService (Telegram Mini App)
  ├── Loads CSV at startup
  ├── Builds in-memory dict: ticker_info = {...}
  ├── Hardcoded company names (name_map)
  ├── Derives exchange from Yahoo ticker suffix (.SI, .HK, .T)
  └── Derives currency from exchange

DataFetcher (LINE Bot)
  ├── Loads CSV via load_tickers()
  ├── ticker_map = {'DBS19': 'D05.SI', ...}
  └── Uses ticker_resolver for symbol resolution
```

**NOT used**:
```
ticker_info table (Aurora) ❌
  - 0 rows
  - Never queried by LINE Bot or Telegram Mini App
  - Only written by scheduler (if enable_aurora=True, which is False)
```

### Why it exists (but isn't used)

**Historical context**:

1. **Original design** (S3-First):
   - `ticker_info` was meant to be metadata registry
   - Would store: company names, exchanges, sectors, industries
   - TickerRepository.get_all_tickers() would query Aurora

2. **Implementation reality**:
   - Scheduler writes to `ticker_info` only if `enable_aurora=True`
   - But `AURORA_ENABLED` env var NOT set → scheduler never writes
   - `ticker_info` table remains empty (0 rows)

3. **Workaround**:
   - Instead of waiting for `ticker_info` to be populated
   - Apps use simple CSV file (`data/tickers.csv`)
   - Hardcode company names and derive metadata from Yahoo ticker format

4. **Current state**:
   - `ticker_info` table: Schema exists, but unused
   - `data/tickers.csv`: Actual source of truth for both apps
   - No migration to Aurora metadata registry

### Relationships

**Metadata sources (3 overlapping sources)**:

```
1. data/tickers.csv (ACTUALLY USED) ✅
   - 46 rows
   - Columns: Symbol, Ticker
   - Used by: LINE Bot, Telegram Mini App

2. ticker_info table (NOT USED) ❌
   - 0 rows
   - Schema: symbol, display_name, company_name, exchange, sector, industry, ...
   - Written by: NOBODY (scheduler disabled)
   - Read by: NOBODY (no queries in production code)

3. ticker_data.company_info JSON (USED by report generation) ✅
   - 46 rows/day
   - Embedded metadata from Yahoo Finance
   - Used by: Report generation, APIs
```

**Why 3 sources**:
- CSV: Simple, easy to edit, no database dependency
- ticker_info: Originally planned, but never populated
- ticker_data JSON: Metadata embedded with time-series data

---

## Explanation for Intermediate Audience

### LINE Bot Usage

**File**: `src/integrations/line_bot.py`

**Data sources**:
```python
# Line 12-13: Imports
from src.data.data_fetcher import DataFetcher
from src.data.aurora.precompute_service import PrecomputeService

# Line 24-25: Loads CSV, NOT ticker_info
data_fetcher = DataFetcher()
ticker_map = data_fetcher.load_tickers()  # Loads data/tickers.csv
```

**What it loads**:
```python
# data/tickers.csv content (example)
# Symbol,Ticker
# DBS19,D05.SI
# UOB19,U11.SI
# NVDA19,NVDA
# ...

# Result in memory:
ticker_map = {
    'DBS19': 'D05.SI',
    'UOB19': 'U11.SI',
    'NVDA19': 'NVDA',
    # ... 46 tickers total
}
```

**Does NOT query ticker_info**:
- No `SELECT * FROM ticker_info` calls
- No `TickerRepository.get_all_tickers()` calls
- All metadata from CSV + Yahoo Finance API

---

### Telegram Mini App Usage

**File**: `src/api/ticker_service.py`

**Data source**:
```python
# Line 11-23: Loads CSV at initialization
def __init__(self, ticker_csv_path: str | None = None):
    if ticker_csv_path is None:
        # Default: data/tickers.csv
        ticker_csv_path = str(Path(__file__).parent.parent.parent / "data" / "tickers.csv")

    self.ticker_map: dict[str, str] = {}  # Symbol -> Yahoo ticker
    self.ticker_info: dict[str, dict] = {}  # Symbol -> full info (IN-MEMORY, not Aurora!)
    self._load_tickers(ticker_csv_path)  # Loads CSV
```

**Metadata derivation** (hardcoded logic):

```python
# Line 25-50: Build in-memory ticker_info dict
def _load_tickers(self, csv_path: str):
    with open(csv_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            symbol = row['Symbol']  # DBS19
            yahoo_ticker = row['Ticker']  # D05.SI

            # Parse metadata from ticker format and hardcoded map
            company_name = self._extract_company_name(symbol)  # From hardcoded dict
            exchange = self._extract_exchange(yahoo_ticker)    # From suffix (.SI → SGX)
            currency = self._extract_currency(exchange)        # From exchange map

            self.ticker_info[symbol] = {
                'symbol': symbol,
                'yahoo_ticker': yahoo_ticker,
                'company_name': company_name,  # ← Hardcoded!
                'exchange': exchange,          # ← Derived from suffix!
                'currency': currency,          # ← Derived from exchange!
                'type': 'equity'
            }
```

**Hardcoded company names** (line 55-102):
```python
def _extract_company_name(self, symbol: str) -> str:
    name_map = {
        'DBS19': 'DBS Group Holdings',  # ← Hardcoded
        'UOB19': 'United Overseas Bank',
        'NVDA19': 'NVIDIA Corporation',
        # ... 43 more hardcoded entries
    }
    return name_map.get(symbol, symbol.replace('19', ''))
```

**Exchange derivation** (line 105-118):
```python
def _extract_exchange(self, yahoo_ticker: str) -> str:
    if yahoo_ticker.endswith('.SI'):
        return 'SGX'  # ← Derived from Yahoo ticker suffix
    elif yahoo_ticker.endswith('.HK'):
        return 'HKEX'
    elif yahoo_ticker.endswith('.T'):
        return 'TSE'
    # ...
```

**Does NOT query ticker_info table**:
- No database connection
- No `SELECT * FROM ticker_info` calls
- All metadata from CSV + hardcoded logic

---

### API Endpoints (Telegram Mini App)

**Search endpoint** (`/api/v1/search`):

```python
# src/api/app.py:177-203
@app.get("/api/v1/search")
async def search_tickers(query: str, limit: int = 10):
    ticker_service = get_ticker_service()  # Loads CSV
    results = ticker_service.search(query, limit)
    return {"results": results}
```

**What happens**:
1. TickerService loads `data/tickers.csv` at startup
2. Builds in-memory `ticker_info` dict (hardcoded company names)
3. Search queries in-memory dict (NOT Aurora `ticker_info` table)

**Report endpoint** (`/api/v1/report/{ticker}`):

```python
# src/api/app.py:206-327
@app.get("/api/v1/report/{ticker}")
async def get_report(ticker: str):
    # Uses PrecomputeService, which queries:
    # - ticker_data (price history + company_info JSON)
    # - daily_indicators
    # - precomputed_reports
    #
    # Does NOT query ticker_info table
```

---

### Evidence: No ticker_info Queries in Production

**All actual ticker_info queries** (from codebase grep):

```python
# src/data/aurora/repository.py (methods exist, but NEVER called)
def get_ticker_info(self, symbol: str):
    query = "SELECT * FROM ticker_info WHERE symbol = %s"
    return self.client.fetch_one(query, (symbol,))  # ← NOT called by any app

def get_all_tickers(self):
    query = "SELECT * FROM ticker_info WHERE is_active = TRUE"
    return self.client.fetch_all(query)  # ← NOT called by any app
```

**Only references** (debug/stats, not production):
```python
# src/scheduler/schema_manager_handler.py:439 (debug query)
'sql': 'SELECT COUNT(*) FROM ticker_info;'

# src/scheduler/query_tool_handler.py:537 (stats query)
'sql': 'SELECT COUNT(*) as total FROM ticker_info;'

# src/data/aurora/client.py:58 (example in docstring)
cursor.execute("SELECT * FROM ticker_info LIMIT 10")
```

**Conclusion**: ticker_info is NEVER queried by production code (LINE Bot or Telegram Mini App)

---

## Why CSV Instead of ticker_info?

### Advantages of CSV approach

1. **Simplicity**
   - No database dependency for basic ticker lookup
   - Easy to edit (add new ticker = add CSV row)
   - No migration scripts needed

2. **Fast startup**
   - Load 46 tickers from CSV in <10ms
   - No database connection required
   - In-memory dict for instant lookups

3. **Version control**
   - CSV in git repository
   - Changes tracked in commit history
   - Easy to review ticker additions/removals

4. **No dependency on scheduler**
   - Apps work even if scheduler hasn't run yet
   - No waiting for ticker_info to be populated
   - Independent of `AURORA_ENABLED` flag

### Disadvantages of CSV approach

1. **Hardcoded company names**
   - Must manually maintain `name_map` dict
   - Adding new ticker requires code change (not just CSV)
   - Risk of stale/incorrect names

2. **Metadata derivation**
   - Exchange derived from Yahoo ticker suffix (brittle)
   - Currency mapped from exchange (assumptions)
   - Sector/industry not available (would need Aurora)

3. **No is_active flag**
   - Cannot soft-delete tickers
   - Must physically remove from CSV
   - No audit trail

4. **Duplication**
   - Company names in 2 places: TickerService code + CSV comments
   - Same derivation logic in multiple files
   - Not DRY (Don't Repeat Yourself)

---

## What Would Change If ticker_info Was Used?

**Hypothetical migration to ticker_info**:

```python
# CURRENT (CSV-based)
class TickerService:
    def __init__(self):
        self.ticker_info = {}  # In-memory dict
        self._load_tickers('data/tickers.csv')  # Load from file

    def search(self, query):
        # Search in-memory dict
        for symbol, info in self.ticker_info.items():
            if query in symbol or query in info['company_name']:
                results.append(info)

# HYPOTHETICAL (Aurora-based)
class TickerService:
    def __init__(self):
        self.repo = TickerRepository()  # Database connection

    def search(self, query):
        # Query Aurora ticker_info table
        query_sql = """
            SELECT * FROM ticker_info
            WHERE symbol LIKE %s OR company_name LIKE %s
            AND is_active = TRUE
        """
        results = self.repo.client.fetch_all(query_sql, (f"%{query}%", f"%{query}%"))
```

**Benefits**:
- ✅ Company names from Yahoo Finance API (accurate, fresh)
- ✅ Sector/industry data available
- ✅ is_active flag for soft deletes
- ✅ last_fetched_at for staleness tracking
- ✅ No hardcoded name_map maintenance

**Costs**:
- ❌ Database dependency (slower startup, requires connection)
- ❌ Requires scheduler to populate ticker_info first
- ❌ Additional Aurora read queries (cost)
- ❌ More complex deployment (schema migration needed)

---

## Summary: Actual Data Sources

### LINE Bot

```
User message: "DBS19"
  ↓
DataFetcher.load_tickers() → data/tickers.csv
  ├── ticker_map['DBS19'] = 'D05.SI'
  └── Resolve symbol to Yahoo format
  ↓
Yahoo Finance API (yfinance library)
  ├── Get price history
  └── Get company info (sector, industry, etc.)
  ↓
PrecomputeService.get_precomputed_report()
  ├── Query: ticker_data (price_history JSON)
  ├── Query: daily_indicators
  └── Query: precomputed_reports
  ↓
Generate report with LLM
```

**ticker_info usage**: ❌ NONE

---

### Telegram Mini App

```
User searches: "DBS"
  ↓
TickerService (initialized at startup)
  ├── Load data/tickers.csv
  ├── Build in-memory ticker_info dict
  │   ├── company_name from hardcoded name_map
  │   ├── exchange from Yahoo ticker suffix
  │   └── currency from exchange mapping
  └── Search in-memory dict
  ↓
Return results: [{symbol: 'DBS19', company_name: 'DBS Group Holdings', ...}]

User clicks ticker → Get report
  ↓
PrecomputeService.compute_for_ticker()
  ├── Query: ticker_data (price_history JSON)
  ├── Query: daily_indicators
  ├── Query: indicator_percentiles
  └── Query: comparative_features
  ↓
Return report JSON
```

**ticker_info usage**: ❌ NONE

---

## Key Takeaways

1. **ticker_info table is NOT used** by LINE Bot or Telegram Mini App
   - Table exists (schema) but has 0 rows
   - No production queries to ticker_info

2. **Both apps use data/tickers.csv** for ticker metadata
   - Simple CSV with 2 columns: Symbol, Ticker
   - In-memory dict for fast lookups
   - Hardcoded company names in TickerService

3. **Metadata sources are fragmented**:
   - CSV: Symbol → Yahoo ticker mapping
   - Hardcoded dict: Company names
   - Derivation logic: Exchange from suffix, currency from exchange
   - ticker_data JSON: Sector, industry from Yahoo Finance API

4. **ticker_info was designed but never populated**:
   - Scheduler would write if `enable_aurora=True`
   - But flag disabled → ticker_info empty
   - Apps built workaround using CSV

5. **Migration to ticker_info would require**:
   - Enable scheduler writes (AURORA_ENABLED=true)
   - Backfill ticker_info (46 rows)
   - Update TickerService to query Aurora
   - Remove hardcoded name_map dict
   - Add database dependency to Telegram Mini App

6. **Current approach works** (CSV-based):
   - Fast (no database queries for ticker lookup)
   - Simple (no schema migrations)
   - Independent (no scheduler dependency)
   - But: Hardcoded, not DRY, limited metadata

---

## Related Documents

- **ticker_info vs ticker_data**: Previous understanding document
- **Aurora tables inventory**: `.claude/understanding-2025-12-30-aurora-tables-inventory.md`
- **Refactoring analysis**: `.claude/skills/refacter/analysis-2025-12-30-enable-aurora-legacy-path.md`
- **Ticker CSV**: `data/tickers.csv`
- **TickerService**: `src/api/ticker_service.py`
- **LINE Bot**: `src/integrations/line_bot.py`

---

**Understanding built**: 2025-12-30
**Audience**: Intermediate (technical team members)
**Confidence**: High (verified with code grep + file reads)
**Finding**: Neither app uses ticker_info table (uses CSV instead)
