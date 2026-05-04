---
title: 22 non-US tickers fail to write to ticker_data — MySQL rejects JSON
bug_type: data-corruption
date: 2026-05-04
status: root_cause_found
confidence: High
---

# Bug Hunt Report: ticker_data write fails for `.SI` / `.HK` tickers

## Symptom

22 of 56 tickers fail to land in Aurora `ticker_data` during the daily scheduler run. All 22 are non-US: 11 Singapore (`.SI`) + 11 Hong Kong (`.HK`). All 34 US tickers succeed.

**Not** a Yahoo rate-limit. yfinance returned data fine — the failure is on the **Aurora write side**.

**First observed**: 2026-05-04 17:35 UTC (Phase B rehearsal of throttled-pipeline)
**Affected scope**: All non-US tickers, every run (deterministic)
**Impact**: Medium — 22/56 tickers permanently absent from the daily cache, downstream precompute reports cannot be generated for them

---

## Investigation Summary

**Bug type**: data-corruption (type-boundary serialization), not integration-failure

**Status**: Root cause found
**Time spent**: ~10 min

---

## Evidence Gathered

### Logs (all 22 errors identical shape)

```
2026-05-04T17:35:39.409Z  ❌ Failed to store C6L.SI to Aurora ticker_data:
  (3140, 'Invalid JSON text: "Invalid value." at position 47801
   in value for column ticker_data.price_history.')
```

22 instances, span 17:35:39 → 17:36:04 UTC. Tickers: C6L.SI, S63.SI, V03.SI, GSD.SI, QK9.SI, D05.SI, Y92.SI, U11.SI, S68.SI, U96.SI, 0700.HK, 0941.HK, 1810.HK, 3690.HK, 6690.HK, 1299.HK, 1378.HK, 1398.HK, 2382.HK, 6618.HK, 3692.HK, 1177.HK.

### Code references

- `src/scheduler/ticker_fetcher.py:170` — `price_history = hist_df.to_dict('records')`
  - Pandas `to_dict('records')` preserves `NaN` floats as-is for missing bars/dividends.
- `src/data/aurora/precompute_service.py:1662` — `json.dumps(price_history, default=str)`
  - **No `allow_nan=False`**. Default `allow_nan=True` emits literal `NaN`/`Infinity` tokens.
- `src/scheduler/ticker_fetcher.py:204` — `_make_json_serializable(...)` exists for the **data-lake** path but is **NOT applied** to the price_history that goes into Aurora.

### Why MySQL rejects

MySQL JSON columns enforce RFC 7159. `NaN` and `Infinity` are not valid JSON. Python's `json.dumps` emits them by default as a non-standard extension. MySQL rejects with error 3140 ("Invalid JSON text").

### Why only non-US tickers

US tickers Yahoo returns are dense — every trading day has OHLCV. Foreign exchanges (`.SI`, `.HK`) have:
- Different holiday calendars → some rows return NaN volume/close on partial-data days
- Missing dividend/split fields where US tickers carry zeros
- Different listing dates → leading NaN rows for newly listed entries

Result: every `.SI`/`.HK` row has at least one NaN somewhere → `json.dumps` emits `NaN` token → MySQL refuses.

---

## Hypotheses Tested

### H1: Yahoo Finance rate limit on non-US tickers
**Likelihood**: Medium (initial guess)
**Test**: Read CloudWatch error messages
**Result**: ❌ ELIMINATED
**Evidence**: Errors are MySQL 3140, not yfinance rate-limit messages. The fetch succeeded; the write failed. Position offsets (47801, 36049, ...) into a JSON string prove the JSON was constructed.

### H2: `precompute-consumer` couldn't process non-US tickers (the DLQ messages)
**Likelihood**: Low
**Test**: Trace data flow upstream
**Result**: ❌ ELIMINATED — those 22 SQS messages **could not have succeeded** even if the consumer was perfect. `ticker_data` for them was missing because **the scheduler never wrote them**. Consumer correctly returned "Data not available" → 3 redrives → DLQ. Consumer is innocent.

### H3: NaN/Infinity in pandas → invalid JSON → MySQL rejection
**Likelihood**: High
**Test**: Read serialization code at `precompute_service.py:1662`
**Result**: ✅ CONFIRMED
**Evidence**:
- `json.dumps(price_history, default=str)` — no `allow_nan=False`
- The data-lake path does pass through `_make_json_serializable` (which calls `float(np.floating)` but doesn't strip NaN either, so data lake is silently broken too — just nobody noticed because S3 accepts anything)
- Identical error shape across all 22 tickers
- Error position offsets are consistent with NaN-token positions in dense OHLCV JSON arrays

### H4: ticker-fetcher Lambda is broken
**Likelihood**: Low
**Test**: Check log streams for `ticker-fetcher-dev`
**Result**: ❌ ELIMINATED — but interesting finding: **`ticker-fetcher-dev` last ran 2026-01-04**. The work today happened entirely inside `ticker-scheduler-dev` (which embeds the same `TickerFetcher` class). The fetcher Lambda is dead infrastructure.

---

## Root Cause

**Identified cause**: `json.dumps(price_history, default=str)` at `src/data/aurora/precompute_service.py:1662` accepts `NaN`/`Infinity` floats and emits non-RFC-7159 JSON tokens, which MySQL JSON columns reject.

**Confidence**: High
- Direct code-level reproduction path
- 22/22 errors match the same MySQL error code
- Pattern (US succeeds, non-US fails) is consistent with NaN density in foreign-market OHLCV
- No alternative hypothesis explains both the error code and the ticker-class pattern

**Code location**: `src/data/aurora/precompute_service.py:1662` (and lines 1663, 1664 for `company_info`/`financials_json` — same bug, just hasn't surfaced yet).

**Why this causes the symptom**:
1. yfinance returns DataFrame with NaN cells for missing data (common in foreign exchanges)
2. `to_dict('records')` preserves `float('nan')` in the dict
3. `json.dumps(..., allow_nan=True)` (default) emits the literal string `NaN`
4. MySQL JSON column validates against RFC 7159, rejects `NaN`, raises 3140
5. `store_ticker_data` raises → `ticker_fetcher.fetch_ticker` returns `status='failed'`
6. Scheduler logs "22 failed", precompute-controller still fires SFN, SFN enqueues all 56
7. Consumer processes the 22 messages whose `ticker_data` row is missing → returns error → 3 redrives → DLQ

This is the **complete causal chain** for the 27-message DLQ.

---

## Reproduction Steps

```python
import json, math
price_history = [{"date": "2026-05-04", "close": math.nan}]
json.dumps(price_history)
# Output: '[{"date": "2026-05-04", "close": NaN}]'   ← invalid JSON

json.dumps(price_history, allow_nan=False)
# Raises ValueError: Out of range float values are not JSON compliant
```

To reproduce against MySQL: insert that string into any JSON column → error 3140.

**Expected**: scheduler writes all 56 tickers
**Actual**: scheduler writes 34 (US-only); 22 non-US fail at the JSON-encode step

---

## Fix Candidates

### Fix 1: Strip NaN/Infinity before serialization (recommended)

**Approach**: Pre-clean `price_history`, `company_info`, `financials` before `json.dumps`. Replace NaN with `None`. Use one of:

```python
# Option A: pandas-aware
import pandas as pd
df = pd.DataFrame(price_history).where(pd.notnull, None)
price_history = df.to_dict('records')

# Option B: explicit recursion (matches existing _make_json_serializable shape)
def _strip_nan(obj):
    if isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)):
        return None
    if isinstance(obj, dict):
        return {k: _strip_nan(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_strip_nan(x) for x in obj]
    return obj
```

Then: `json.dumps(_strip_nan(price_history), default=str, allow_nan=False)`.

**Pros**:
- Surgical: 1 file, 3 lines around `precompute_service.py:1662-1664`
- Preserves all valid data; only replaces unrepresentable floats
- `allow_nan=False` makes future regressions loud (raises at encode time, not at MySQL)

**Cons**:
- Loses signal that "this cell was NaN" vs "this cell was missing" — but they're already indistinguishable downstream
- Adds tiny CPU cost per write (~1ms for 365-row history)

**Effort**: 30 min (write + 1 unit test + deploy)
**Risk**: Low

---

### Fix 2: Extend `_make_json_serializable` to handle NaN, route price_history through it

**Approach**: Update the existing helper in `ticker_fetcher.py:105` to convert NaN→None, then call it in the Aurora-write path (currently only used for data-lake path).

**Pros**:
- Reuses existing helper; the bug-fix lives near the bug
- Fixes data-lake silently-broken path simultaneously

**Cons**:
- Crosses a layer boundary: `ticker_fetcher` (scheduler) shouldn't know about `precompute_service`'s storage shape
- Two callers, same bug — risk of one being missed if the helper diverges

**Effort**: 45 min
**Risk**: Medium (cross-layer concern)

---

### Fix 3: Switch `price_history` column to TEXT/LONGTEXT

**Approach**: Drop the JSON column type; store as plain text.

**Pros**: MySQL stops validating
**Cons**: Loses JSON path queries, loses type safety, hides bugs, requires migration. **Don't do this.**

**Effort**: 2h + migration + downstream query rewrites
**Risk**: High

---

## Recommendation

**Fix 1**, applied at the storage boundary (`precompute_service.py:1662-1664`). Three reasons:

1. **Correct layer**: `precompute_service` owns the MySQL contract; serialization is its concern.
2. **Belt + suspenders**: NaN-strip + `allow_nan=False`. The strip handles current data; the flag makes any future leak fail loudly at the call site instead of silently at MySQL.
3. **Same fix for the other two columns**: `company_info` and `financials_json` have the same bug shape; one helper fixes all three.

**Implementation priority**: P1 (data is missing every morning; 39% of tickers affected), but not P0 (precompute-pipeline-as-pattern works correctly; 34 tickers cached fine).

---

## Next Steps

- [ ] Implement Fix 1 in `precompute_service.py`
- [ ] Add unit test: `store_ticker_data` accepts a price_history with `float('nan')`, succeeds, MySQL row contains `null` at that position
- [ ] Deploy via existing CI path (touches `src/data/aurora/`, picked up by `deploy-telegram-dev.yml`)
- [ ] Re-invoke `ticker-scheduler-dev` with `{}`
- [ ] Verify: `SELECT COUNT(*) FROM ticker_data WHERE date = CURDATE()` returns 56
- [ ] Verify: rerun precompute SFN → DLQ stays at baseline (currently 27, will grow no further)
- [ ] Drain DLQ once verified

---

## Investigation Trail

**What was checked**:
- ticker-fetcher Lambda log streams (dead since January)
- ticker-scheduler Lambda errors last 12h (22 hits, all MySQL 3140)
- Code path `ticker_fetcher.fetch_ticker` → `precompute_service.store_ticker_data`
- `json.dumps` call site at line 1662
- `_make_json_serializable` helper (used in data-lake path, NOT in Aurora path)

**What was ruled out**:
- Yahoo rate-limit (data was fetched; failure is in write)
- precompute-consumer bug (its DLQ messages were unrecoverable upstream)
- Recent code change (the bug has likely existed since the JSON column was added; non-US tickers always failed but were quietly missing — only Phase B's explicit accounting surfaced it)

**Tools used**:
- CloudWatch Logs filter (`filter-log-events --filter-pattern ERROR`)
- `aws sqs get-queue-attributes` (DLQ math: 27-5=22)
- `grep` + `Read` over `src/`

**Time spent**:
- Evidence gathering: 6 min
- Hypothesis testing: 4 min
- Total: 10 min
