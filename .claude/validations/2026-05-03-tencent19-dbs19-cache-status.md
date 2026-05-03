---
name: TENCENT19 and DBS19 not in today's precompute cache
description: Both alias-symbols map to canonical tickers (0700.HK, D05.SI) that are absent from 2026-05-03 batch but present recently
type: validation
date: 2026-05-03
---

# Validation: Are TENCENT19 and DBS19 cached for 2026-05-03?

**Claim**: "Precomputed reports for TENCENT19 and DBS19 are populated."

---

## Status: ❌ FALSE — both missing today (HIGH confidence)

The bot will hit cache-miss for both tickers today and reply with the polite "not ready" message.

---

## Evidence

### What "TENCENT19" / "DBS19" actually are

These are **alias symbols** in the project ticker map (`data/tickers.csv`):

| Alias | Canonical Yahoo symbol | Asset |
|---|---|---|
| `TENCENT19` | `0700.HK` | Tencent Holdings (HKEX) |
| `DBS19` | `D05.SI` (also `DBSM.SI` in funda_data.csv) | DBS Bank (SGX) |

The precompute pipeline writes to `precomputed_reports.symbol` using the **canonical** form, not the alias. So we must check `0700.HK` / `D05.SI`, not the aliases.

### Layer 4 — `precomputed_reports` for those symbols (last 7 days)

```sql
SELECT report_date, symbol, status FROM precomputed_reports
WHERE symbol IN ('0700.HK','D05.SI','DBSM.SI')
  AND report_date >= CURDATE() - INTERVAL 7 DAY;
```

| Date | 0700.HK (TENCENT19) | D05.SI (DBS19) |
|---|:---:|:---:|
| **2026-05-03 (today)** | ❌ missing | ❌ missing |
| 2026-05-02 | ❌ missing | ✅ completed |
| 2026-05-01 | ✅ completed | ✅ completed |
| 2026-04-30 | ✅ completed | ✅ completed |
| 2026-04-29 | ✅ completed | ✅ completed |
| 2026-04-28 | ✅ completed | (not in window) |

`DBSM.SI`: 0 rows ever — that CSV row in `funda_data.csv` is not what precompute writes.

### Layer 4 — full list of today's 42 cached symbols

```
1177.HK 1299.HK 1378.HK 1398.HK 2382.HK 3690.HK 6618.HK 6690.HK
6857.T 7011.T 7267.T 7974.T 8001.T 8306.T 8316.T
AAPL ABBV C6L.SI COST DDOG DELL DIS FPT.VN GLD GSD.SI HPG.VN ISRG
JPM MSFT MSN.HM MU MWG.VN NOW NVDA ORCL PFE QK9.SI QQQM
S63.SI S68.SI SPLG U96.SI
```

Neither `0700.HK` nor `D05.SI` is in the 42 — so today's batch genuinely excluded them, not a query bug.

### Trend: tickers dropping out of daily batch

| Date | Total cached | 0700.HK | D05.SI |
|---|---:|:---:|:---:|
| 2026-04-29 | 42 | ✅ | ✅ |
| 2026-04-30 | 42 | ✅ | ✅ |
| 2026-05-01 | 42 | ✅ | ✅ |
| 2026-05-02 | **46** | ❌ | ✅ |
| 2026-05-03 | 42 | ❌ | ❌ |

Tencent dropped out 2 days ago (2026-05-02). DBS dropped out today.

---

## Why this matters for the bot

`PrecomputeService.get_cached_report(symbol, data_date)` is called with `data_date = today`. So:

- User types `@dr-daily-report DBS19` → matcher maps `DBS19 → D05.SI` → query `(D05.SI, 2026-05-03)` → **NULL** → bot replies "not ready, try later".
- This explains what the user will see today **even though the same query worked yesterday** (when D05.SI *was* in the 2026-05-02 batch).

The user's earlier successful Slack test (yesterday's `@dr-daily-report DBS19`) hit yesterday's cache. Today the same query is a cache miss because the upstream **ticker-list selector** dropped both tickers from today's batch.

---

## Likely root cause (hypothesis, not yet verified)

The daily ticker list is computed dynamically by `dr-daily-report-get-ticker-list-handler-dev` Lambda (`src/scheduler/get_ticker_list_handler.py`). Possible reasons for dropouts:

1. **Volume / liquidity threshold** — selector keeps top-N by recent volume, and 0700.HK / D05.SI fell below the threshold for today's universe.
2. **Stale tickers** filter — selector excludes symbols missing data for N days. (Unlikely, both have multi-day cache history.)
3. **Hardcoded universe shrinkage** — someone trimmed a config/SQL list.
4. **Market-calendar gating** — HK and SG markets had a holiday today and selector excludes ticker on its market's holiday. (Worth checking — today is Sunday, but other Asia tickers like the .T set are present, which weakens this.)

Sunday markets are closed everywhere; some tickers persist via 2D-old data while others get filtered. The selector logic decides — needs reading `get_ticker_list_handler.py`.

---

## Recommendation

**Short term (no code changes)**:
- If the user wants reports for these specific tickers, they can be served from yesterday's cache by querying `data_date = '2026-05-02'` for `DBS19`. There is no way for the user to do that through the bot today — bot is hard-coded to "today".

**Medium term**:
- Add a fallback: if `get_cached_report(symbol, today)` is NULL, fall back to the most recent `report_date` ≤ today (keep within `expires_at`). This converts today's empty batch into "yesterday's report served as the latest" which is what most chat users expect.
- Or: pin a "must-include" set (Tencent, DBS, and other frequently-asked tickers) into the ticker-list selector so the daily batch never drops them.

**Investigative next step**:
- Read `src/scheduler/get_ticker_list_handler.py` and check why 0700.HK + D05.SI dropped. Run the selector locally with today's date and inspect its rationale.

---

## References

- Ticker alias map: `data/tickers.csv:9` (DBS19→D05.SI), `data/tickers.csv:20` (TENCENT19→0700.HK)
- Funda map (different mapping for DBS19): `data/funda_data.csv:142–148` (DBS19→DBSM.SI)
- Cache table: `precomputed_reports`
- Selector Lambda: `dr-daily-report-get-ticker-list-handler-dev` (`src/scheduler/get_ticker_list_handler.py`)
- Bot read path: `src/data/aurora/precompute_service.py:get_cached_report`
- Companion validation (today's overall cache health): `.claude/validations/2026-05-03-precompute-cache-bot-readiness.md`
