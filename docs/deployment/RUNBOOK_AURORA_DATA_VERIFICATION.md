# Runbook: Aurora Data Verification

**Generated**: 2025-12-28
**Last Validated**: 2025-12-28
**Estimated Duration**: 2-5 minutes
**Runbook Owner**: Operations Team
**Review Frequency**: Monthly

---

## Overview

**Purpose**: Quickly verify Aurora database has complete data after scheduler fetch and precompute workflow execution.

**When to use**:
- After running scheduler to fetch ticker data
- After precompute workflow completes
- When API returns null/empty data
- Before promoting deployment to production
- During incident response (data availability issues)

**Dependencies**:
- AWS CLI v2 configured
- Doppler configured for environment
- Lambda query tool deployed (`dr-daily-report-query-tool-{env}`)

---

## Prerequisites

### Environment
- [ ] Environment determined: `dev`, `staging`, or `prod`
- [ ] Doppler configured: `doppler setup` completed

### Required Tools
- [x] AWS CLI v2 configured
- [x] Doppler CLI installed
- [x] Python 3.11+ with boto3

### Required Access
- [x] AWS Lambda invoke permission for query-tool
- [x] Doppler read access for environment

---

## Quick Verification (2 minutes)

### Step 1: Check ticker_data Population

**Purpose**: Verify scheduler fetched all 46 tickers for today

**Command**:
```bash
ENV=dev doppler run -- python3 <<'PYTHON'
import boto3
import json
from datetime import datetime, date

lambda_client = boto3.client('lambda', region_name='ap-southeast-1')

payload = {
    "action": "query",
    "sql": """
        SELECT
            date,
            COUNT(DISTINCT symbol) as unique_symbols,
            COUNT(*) as total_records,
            MIN(fetched_at) as first_fetch,
            MAX(fetched_at) as last_fetch
        FROM ticker_data
        WHERE date = CURDATE()
        GROUP BY date
    """
}

response = lambda_client.invoke(
    FunctionName='dr-daily-report-query-tool-dev',
    InvocationType='RequestResponse',
    Payload=json.dumps(payload)
)

result = json.loads(response['Payload'].read())
if result['statusCode'] == 200:
    data = result['body']['results']
    if data:
        r = data[0]
        print(f"✅ ticker_data for {r['date']}")
        print(f"   Symbols: {r['unique_symbols']}/46")
        print(f"   Records: {r['total_records']}")
        print(f"   Fetched: {r['first_fetch']} to {r['last_fetch']}")

        if r['unique_symbols'] == 46:
            print("\n✅ PASS: All 46 tickers fetched")
        else:
            print(f"\n❌ FAIL: Only {r['unique_symbols']}/46 tickers fetched")
    else:
        print("❌ FAIL: No ticker_data for today")
else:
    print(f"❌ ERROR: {result['body']['error']}")
PYTHON
```

**Expected Output**:
```
✅ ticker_data for 2025-12-28
   Symbols: 46/46
   Records: 46
   Fetched: 2025-12-28T22:00:38 to 2025-12-28T22:00:59

✅ PASS: All 46 tickers fetched
```

**Expected Duration**: ~2-3 seconds

**If Failed**:
- **0 symbols**: Scheduler didn't run or failed completely
  - Action: Check scheduler Lambda logs
  - Run: `ENV=dev doppler run -- aws logs tail /aws/lambda/dr-daily-report-ticker-scheduler-dev --since 1h`

- **< 46 symbols**: Partial scheduler run (some tickers failed)
  - Action: Check scheduler response for failed tickers
  - Re-run: `ENV=dev doppler run -- python3 -c "import boto3, json; ..." # Invoke scheduler`

- **Wrong date**: Check timezone configuration (Aurora uses UTC)
  - Verify: Query with explicit date `WHERE date = '2025-12-28'`

---

### Step 2: Check precomputed_reports Completion

**Purpose**: Verify precompute workflow generated all 46 reports for today

**Command**:
```bash
ENV=dev doppler run -- python3 <<'PYTHON'
import boto3
import json

lambda_client = boto3.client('lambda', region_name='ap-southeast-1')

payload = {
    "action": "query",
    "sql": """
        SELECT
            COUNT(*) as total_reports,
            SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed,
            SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pending,
            SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed,
            MAX(computed_at) as latest_computed_at
        FROM precomputed_reports
        WHERE report_date = CURDATE()
    """
}

response = lambda_client.invoke(
    FunctionName='dr-daily-report-query-tool-dev',
    InvocationType='RequestResponse',
    Payload=json.dumps(payload)
)

result = json.loads(response['Payload'].read())
if result['statusCode'] == 200:
    data = result['body']['results']
    if data and data[0]['total_reports'] > 0:
        r = data[0]
        print(f"📊 precomputed_reports for today")
        print(f"   Total: {r['total_reports']}")
        print(f"   ✅ Completed: {r['completed']}")
        print(f"   ⏳ Pending: {r['pending']}")
        print(f"   ❌ Failed: {r['failed']}")
        print(f"   Latest: {r['latest_computed_at']}")

        if r['completed'] == 46:
            print("\n✅ PASS: All 46 reports completed")
        elif r['pending'] > 0:
            print(f"\n⏳ IN PROGRESS: {r['pending']} reports still processing")
        else:
            print(f"\n❌ FAIL: Only {r['completed']}/46 reports completed")
    else:
        print("❌ FAIL: No precomputed_reports for today")
else:
    print(f"❌ ERROR: {result['body']['error']}")
PYTHON
```

**Expected Output**:
```
📊 precomputed_reports for today
   Total: 46
   ✅ Completed: 46
   ⏳ Pending: 0
   ❌ Failed: 0
   Latest: 2025-12-28T20:23:46

✅ PASS: All 46 reports completed
```

**Expected Duration**: ~2-3 seconds

**If Failed**:
- **0 reports**: Precompute workflow didn't run
  - Action: Check precompute controller Lambda logs
  - Run: `ENV=dev doppler run -- aws logs tail /aws/lambda/dr-daily-report-precompute-controller-dev --since 1h`

- **< 46 completed**: Workers failed or still processing
  - Check pending: If > 0, wait 30 seconds and re-check
  - Check failed: Investigate worker logs for error messages
  - Run: `ENV=dev doppler run -- aws logs tail /aws/lambda/dr-daily-report-report-worker-dev --since 1h --filter-pattern "Failed job"`

- **45 failed, 1 completed**: Likely ticker_data missing (scheduler didn't run first)
  - Action: Run Step 1 to verify ticker_data populated
  - Fix: Run scheduler, then re-run precompute

---

### Step 3: Verify Report Content Quality

**Purpose**: Sample check that reports have actual content (not empty/null)

**Command**:
```bash
ENV=dev doppler run -- python3 <<'PYTHON'
import boto3
import json

lambda_client = boto3.client('lambda', region_name='ap-southeast-1')

# Check 3 sample tickers across different markets
sample_symbols = ['NVDA', 'D05.SI', '0700.HK']

print("📝 Sample Report Content Check\n")

for symbol in sample_symbols:
    payload = {
        "action": "query",
        "sql": f"""
            SELECT
                symbol,
                status,
                LENGTH(report_text) as text_len,
                LENGTH(chart_base64) as chart_len,
                JSON_LENGTH(report_json) as json_keys
            FROM precomputed_reports
            WHERE symbol = '{symbol}' AND report_date = CURDATE()
            LIMIT 1
        """
    }

    response = lambda_client.invoke(
        FunctionName='dr-daily-report-query-tool-dev',
        InvocationType='RequestResponse',
        Payload=json.dumps(payload)
    )

    result = json.loads(response['Payload'].read())
    if result['statusCode'] == 200 and result['body']['results']:
        r = result['body']['results'][0]

        status_icon = "✅" if r['status'] == 'completed' else "❌"
        text_ok = "✅" if r['text_len'] > 5000 else "⚠️"
        chart_ok = "✅" if r['chart_len'] > 50000 else "⚠️"
        json_ok = "✅" if r['json_keys'] > 20 else "⚠️"

        print(f"{status_icon} {r['symbol']}")
        print(f"   {text_ok} Text: {r['text_len']:,} chars")
        print(f"   {chart_ok} Chart: {r['chart_len']:,} bytes")
        print(f"   {json_ok} JSON: {r['json_keys']} keys\n")
    else:
        print(f"❌ {symbol} - Not found\n")

print("Note: ✅ = Good, ⚠️ = Low but acceptable, ❌ = Missing/Failed")
PYTHON
```

**Expected Output**:
```
📝 Sample Report Content Check

✅ NVDA
   ✅ Text: 5,423 chars
   ✅ Chart: 73,972 bytes
   ✅ JSON: 26 keys

✅ D05.SI
   ✅ Text: 5,380 chars
   ✅ Chart: 71,856 bytes
   ✅ JSON: 26 keys

✅ 0700.HK
   ✅ Text: 5,429 chars
   ✅ Chart: 72,104 bytes
   ✅ JSON: 26 keys

Note: ✅ = Good, ⚠️ = Low but acceptable, ❌ = Missing/Failed
```

**Expected Duration**: ~3-4 seconds

**Quality Thresholds**:
- Report text: > 5,000 chars (typical: 5,200-6,000)
- Chart image: > 50,000 bytes (typical: 70,000-75,000)
- JSON keys: > 20 (typical: 26)

**If Failed**:
- **Text < 3,000 chars**: Report generation incomplete or LLM error
  - Check: Worker logs for LLM API errors
  - Verify: OpenAI API key valid and has credits

- **Chart < 30,000 bytes**: Chart generation failed or image corrupted
  - Check: matplotlib errors in worker logs
  - Verify: Font files accessible in Lambda

- **JSON < 15 keys**: Data extraction incomplete
  - Check: yfinance API errors
  - Verify: Ticker symbol mapping correct

---

## Complete Verification (5 minutes)

### Step 4: List All Symbols with Status

**Purpose**: See complete inventory of which tickers succeeded/failed

**Command**:
```bash
ENV=dev doppler run -- python3 <<'PYTHON'
import boto3
import json

lambda_client = boto3.client('lambda', region_name='ap-southeast-1')

payload = {
    "action": "query",
    "sql": """
        SELECT symbol, status, LENGTH(report_text) as text_len, computed_at
        FROM precomputed_reports
        WHERE report_date = CURDATE()
        ORDER BY symbol
    """
}

response = lambda_client.invoke(
    FunctionName='dr-daily-report-query-tool-dev',
    InvocationType='RequestResponse',
    Payload=json.dumps(payload)
)

result = json.loads(response['Payload'].read())
if result['statusCode'] == 200:
    results = result['body']['results']

    print(f"{'#':<3} {'Symbol':<15} {'Status':<10} {'Text Length':<12} {'Computed At'}")
    print("-" * 70)

    for i, r in enumerate(results, 1):
        status_icon = "✅" if r['status'] == 'completed' else "❌"
        print(f"{i:<3} {r['symbol']:<15} {status_icon} {r['status']:<9} {r['text_len']:>10,} {r['computed_at']}")

    print("-" * 70)
    print(f"Total: {len(results)} reports")

    completed = sum(1 for r in results if r['status'] == 'completed')
    print(f"Completed: {completed}/46")
else:
    print(f"❌ ERROR: {result['body']['error']}")
PYTHON
```

**Expected Output** (truncated):
```
#   Symbol          Status     Text Length  Computed At
----------------------------------------------------------------------
1   0050.TW         ✅ completed      5,482 2025-12-28T20:23:37
2   0700.HK         ✅ completed      5,429 2025-12-28T20:23:38
3   0941.HK         ✅ completed      5,500 2025-12-28T20:23:39
...
44  VHM.VN          ✅ completed      5,859 2025-12-28T20:23:45
45  VNM.VN          ✅ completed      5,590 2025-12-28T20:23:46
46  Y92.SI          ✅ completed      5,926 2025-12-28T20:23:46
----------------------------------------------------------------------
Total: 46 reports
Completed: 46/46
```

**Expected Duration**: ~3-5 seconds

---

### Step 5: Test API Data Availability

**Purpose**: Verify API endpoints return complete data (end-to-end check)

**Command**:
```bash
curl -s "https://ou0ivives1.execute-api.ap-southeast-1.amazonaws.com/api/v1/rankings?category=trending&limit=3" | python3 -c "
import sys, json
data = json.load(sys.stdin)

print('=' * 60)
print('API Data Availability Test')
print('=' * 60)
print(f'Category: {data[\"category\"]}')
print(f'As of: {data[\"as_of\"]}')
print(f'Tickers returned: {len(data[\"tickers\"])}\n')

all_ok = True
for i, ticker in enumerate(data['tickers'], 1):
    chart_ok = '✅' if ticker.get('chart_data') else '❌'
    scores_ok = '✅' if ticker.get('key_scores') else '❌'

    print(f'{i}. {ticker[\"ticker\"]} - {ticker[\"company_name\"]}')
    print(f'   {chart_ok} Chart data: {\"Present\" if ticker.get(\"chart_data\") else \"NULL\"}')
    print(f'   {scores_ok} Key scores: {\"Present\" if ticker.get(\"key_scores\") else \"NULL\"}')

    if not ticker.get('chart_data') or not ticker.get('key_scores'):
        all_ok = False

print()
if all_ok:
    print('✅ PASS: All API data complete')
else:
    print('❌ FAIL: Some API data missing (chart_data or key_scores NULL)')
"
```

**Expected Output**:
```
============================================================
API Data Availability Test
============================================================
Category: trending
As of: 2025-12-28T20:25:19.397342
Tickers returned: 3

1. HPG19 - HOA PHAT GROUP JSC
   ✅ Chart data: Present
   ✅ Key scores: Present
2. NINTENDO19 - NINTENDO CO LTD
   ✅ Chart data: Present
   ✅ Key scores: Present
3. MWG19 - MOBILE WORLD INVESTMENT CORPORA
   ✅ Chart data: Present
   ✅ Key scores: Present

✅ PASS: All API data complete
```

**Expected Duration**: ~2-3 seconds

**If Failed**:
- **chart_data NULL**: Precompute succeeded but cache lookup failed
  - Check: Rankings service cache query logic
  - Verify: Symbol mapping (friendly name → Yahoo symbol)

- **key_scores NULL**: Scoring calculation incomplete
  - Check: Report JSON structure in Aurora
  - Verify: Key scores extracted correctly

---

## Troubleshooting

### Issue 1: "Unknown column 'data_date' in field list"

**Symptoms**:
- SQL error when querying `ticker_data`
- Column name mismatch

**Cause**: Schema uses `date` column, not `data_date`

**Solution**: Use correct column name in queries
```sql
-- ❌ Wrong
WHERE data_date = CURDATE()

-- ✅ Correct
WHERE date = CURDATE()
```

**Prevention**: Always use `describe_table` action to check schema first

---

### Issue 2: "Unknown column 'generated_at' in field list"

**Symptoms**:
- SQL error when querying `precomputed_reports`
- Column name mismatch

**Cause**: Schema uses `computed_at` column, not `generated_at`

**Solution**: Use correct column name in queries
```sql
-- ❌ Wrong
MAX(generated_at) as latest

-- ✅ Correct
MAX(computed_at) as latest
```

**Reference**: See table schema in Step 0 (Optional)

---

### Issue 3: No Results for Today (Wrong Timezone)

**Symptoms**:
- Query returns 0 results
- Manual query with yesterday's date returns data

**Cause**: Aurora runs in UTC, local time might be different timezone

**Solution**: Use explicit date instead of `CURDATE()`
```sql
-- If running at 1 AM Bangkok (still 2025-12-27 UTC)
WHERE report_date = '2025-12-27'  -- Explicit date

-- Or use UTC-aware date
WHERE report_date = DATE(CONVERT_TZ(NOW(), '+00:00', '+07:00'))
```

**Prevention**: Always verify date range when debugging

---

### Issue 4: Only 1/46 Tickers Has Data

**Symptoms**:
- Step 1: Only 1 ticker in ticker_data
- Step 2: 1 completed, 45 failed

**Cause**: Scheduler was invoked with `{"tickers": ["NVDA"]}` parameter (manual test)

**Solution**: Re-run scheduler without `tickers` parameter
```bash
ENV=dev doppler run -- python3 <<'PYTHON'
import boto3, json
lambda_client = boto3.client('lambda', region_name='ap-southeast-1')
response = lambda_client.invoke(
    FunctionName='dr-daily-report-ticker-scheduler-dev',
    InvocationType='RequestResponse',
    Payload=json.dumps({})  # Empty = fetch all 46
)
print(json.loads(response['Payload'].read()))
PYTHON
```

**Then re-run precompute** to process all 46 tickers

---

### Issue 5: Reports Exist But API Returns Null

**Symptoms**:
- Step 2: All 46 reports completed
- Step 5: API returns `chart_data=null, key_scores=null`

**Cause**: Symbol mismatch between API lookup and Aurora storage

**Root Issue**:
- API searches by friendly name (e.g., "DBS19")
- Aurora stores Yahoo symbol (e.g., "D05.SI")
- Lookup fails → returns null

**Solution**: Use `ticker_resolver` to map symbols
```python
# In rankings_service.py
from src.data.aurora.ticker_resolver import get_ticker_resolver

resolver = get_ticker_resolver()
ticker_info = resolver.resolve("DBS19")  # Returns D05.SI
```

**Prevention**: Always use ticker_resolver for symbol lookups

---

## Optional: Check Table Schemas

### Step 0: Describe Table Structures

**Purpose**: Understand actual column names in Aurora tables

**ticker_data schema**:
```bash
ENV=dev doppler run -- python3 -c "
import boto3, json
client = boto3.client('lambda', region_name='ap-southeast-1')
r = client.invoke(
    FunctionName='dr-daily-report-query-tool-dev',
    InvocationType='RequestResponse',
    Payload=json.dumps({'action': 'describe_table', 'table': 'ticker_data'})
)
print(json.dumps(json.loads(r['Payload'].read())['body']['schema'], indent=2))
"
```

**Key columns**:
- `date` (not `data_date`) - Date of ticker data
- `symbol` - Yahoo Finance symbol (e.g., D05.SI)
- `fetched_at` - When data was fetched
- `price_history` - JSON with OHLCV data

**precomputed_reports schema**:
```bash
ENV=dev doppler run -- python3 -c "
import boto3, json
client = boto3.client('lambda', region_name='ap-southeast-1')
r = client.invoke(
    FunctionName='dr-daily-report-query-tool-dev',
    InvocationType='RequestResponse',
    Payload=json.dumps({'action': 'describe_table', 'table': 'precomputed_reports'})
)
print(json.dumps(json.loads(r['Payload'].read())['body']['schema'], indent=2))
"
```

**Key columns**:
- `report_date` - Date report was generated for
- `symbol` - Yahoo Finance symbol (e.g., D05.SI)
- `computed_at` (not `generated_at`) - When report was generated
- `report_text` - Plain text report
- `chart_base64` - Chart image (base64)
- `report_json` - Structured report data
- `status` - `'completed'`, `'pending'`, or `'failed'`

---

## Success Criteria

**Verification is complete when ALL checks pass**:

- [x] **Step 1**: ticker_data shows 46/46 symbols for today
- [x] **Step 2**: precomputed_reports shows 46 completed, 0 failed
- [x] **Step 3**: Sample reports have > 5,000 chars text, > 50,000 bytes chart
- [x] **Step 5**: API returns complete data (chart_data and key_scores present)

**Estimated Total Time**: 2-5 minutes

---

## Related Resources

### Documentation
- [Automated Precompute](AUTOMATED_PRECOMPUTE.md) - Scheduler + Precompute architecture
- [Principle #2: Progressive Evidence Strengthening](../../.claude/CLAUDE.md) (Tier-0 Core)
- [Principle #3: Aurora-First Architecture](../../.claude/principles/data-principles.md)

### Lambda Functions
- `dr-daily-report-query-tool-{env}` - SQL query execution
- `dr-daily-report-ticker-scheduler-{env}` - Fetch ticker data
- `dr-daily-report-precompute-controller-{env}` - Trigger precompute
- `dr-daily-report-report-worker-{env}` - Generate reports

### Related Commands
- `/observe execution` - Document successful verification run
- `/bug-hunt` - Investigate data availability issues
- `/error-investigation` - Debug Lambda failures

---

## Change Log

**2025-12-28**:
- Initial runbook created
- Based on manual verification performed during Fix #1
- Discovered schema mismatches (data_date → date, generated_at → computed_at)
- Added API end-to-end test (Step 5)
- Documented symbol mapping issue (friendly name vs Yahoo symbol)
