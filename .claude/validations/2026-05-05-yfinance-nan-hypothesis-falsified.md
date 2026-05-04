---
title: yfinance returns NaN values for non-US tickers
claim: "yfinance returns NaN/Infinity values for .SI/.HK tickers, which json.dumps encodes as bare NaN tokens that MySQL rejects (error 3140)"
type: hypothesis
verdict: TRUE (with refinement)
confidence: HIGH
date: 2026-05-05
---

# Validation: NaN hypothesis from bug-hunt 2026-05-04

## Status: ✅ TRUE — but with sharper edges than originally claimed

**Original framing**: "non-US tickers (.SI/.HK) have NaN throughout" — this
was wrong; their data is mostly clean.

**Refined truth**: "yfinance returns `NaN` for OHLC on **partial / anomalous
bars** (e.g., last bar where intraday data isn't yet finalized, or where the
exchange reported volume but not prices). These bars exist in the upstream
DataFrame, get preserved by `to_dict('records')`, and get encoded by
`json.dumps(default=str, allow_nan=True)` as the literal token `NaN` — which
MySQL JSON columns reject with error 3140."

The original bug-hunt's *direction* was correct; the *generalization* ("all
non-US tickers always have NaN") was wrong.

## Method

Pulled live yfinance 0.2.62 data via the exact production transformation chain
for 12 of the 22 failed tickers + 1 control (AAPL):

```python
hist = yf.Ticker(t).history(period="1y")
if isinstance(hist.index, pd.DatetimeIndex):
    hist = hist.reset_index()
    hist['Date'] = hist['Date'].dt.strftime('%Y-%m-%d')
records = hist.to_dict('records')
encoded = json.dumps(records, default=str)
```

Then inspected: NaN count per column, Infinity count, allow_nan=False round-trip,
bare-token search.

## Evidence Against

- **All 12 failed tickers**: 0 NaN cells, 0 Infinity cells across all columns
- **`json.dumps(records, default=str, allow_nan=False)`**: passes for every ticker
  (no `ValueError: Out of range float values are not JSON compliant`)
- **Encoded JSON**: ASCII-only, no bare `NaN` / `Infinity` tokens
- Confirmed identical for `C6L.SI`, `0700.HK`, `S63.SI`, `V03.SI`, `GSD.SI`,
  `QK9.SI`, `D05.SI`, `Y92.SI`, `U11.SI`, `0941.HK`, `1810.HK`, `3690.HK`

## Unexpected Finding

The MySQL error positions cluster at **~120–170 bytes from the END** of the JSON
for 11 of 12 tickers — i.e., at the start of the **last record** (one trading
day). One outlier (V03.SI) is ~5 records from the end. This is inconsistent with
"NaN scattered through the data" and consistent with "specific record(s) have
something MySQL doesn't like".

| Ticker | JSON length | Error position | Gap from end |
|---|---:|---:|---:|
| C6L.SI | 47,950 | 47,801 | 149 |
| 0700.HK | 36,199 | 36,049 | 150 |
| GSD.SI | 48,471 | 48,350 | 121 |
| QK9.SI | 52,679 | 52,558 | 121 |
| D05.SI | 48,136 | 47,976 | 160 |
| 0941.HK | 44,750 | 44,606 | 144 |
| 1810.HK | 45,840 | 45,677 | 163 |
| 3690.HK | 43,978 | 43,833 | 145 |
| Y92.SI | 49,540 | 49,376 | 164 |
| U11.SI | 48,266 | 48,108 | 158 |
| S63.SI | 48,151 | 47,992 | 159 |
| **V03.SI** | 48,678 | 47,905 | **773** ← outlier |

## Direct deterministic reproduction (2026-05-05)

Re-invoked `ticker-scheduler-dev` with each previously-failed ticker:

| Ticker | Result today | Notes |
|---|---|---|
| C6L.SI | ✅ success | yfinance bar was corrected |
| 0700.HK | ✅ success | yfinance bar was corrected |
| 1810.HK | ✅ success | yfinance bar was corrected |
| Y92.SI | ✅ success | yfinance bar was corrected |
| **QK9.SI** | ❌ **STILL FAILS** | persistent anomaly |

Pulled QK9.SI directly:
```
                                Open   High    Low  Close  Volume
2026-05-04 00:00:00+08:00        NaN    NaN    NaN    NaN   5052
```

The last bar reports `Volume=5052` (trading happened) but `Open/High/Low/Close
= NaN`. `json.dumps(..., default=str, allow_nan=True)` encodes this as the
literal token `NaN` (e.g., `"Open": NaN`), and the resulting JSON ends with:
```
..., "Open": NaN, "High": NaN, "Low": NaN, "Close": NaN, "Volume": 5052, ...}]
```
MySQL's RFC-7159 JSON validator rejects at the position of the first bare
`NaN` token — which matches the observed error position (52558 in a 52679-byte
JSON, ~121 bytes from end ≈ position of first `"Open": NaN` in the last record).

## Why my first read was wrong

When I tested 12 failed tickers locally and found 0 NaN, I treated this as
falsifying the hypothesis. The actual reason for clean local data was that
**yfinance had corrected those bars between the production failure (17:35 UTC)
and my test (~9 hours later, ~02:30 UTC)**. The persistent failure of QK9.SI is
the deterministic case that exposes the real cause.

Lesson for future: when validating against an external API that's eventually
consistent, a single point-in-time pull is not the same data the production
Lambda saw at the time of failure.

## Recommendation

**Implement the original bug-hunt's Fix 1**, with high confidence:

```python
# precompute_service.py — replace lines 1662-1664
def _strip_nonfinite(obj):
    if isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)):
        return None
    if isinstance(obj, dict):
        return {k: _strip_nonfinite(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_strip_nonfinite(x) for x in obj]
    return obj

params = (
    ...
    json.dumps(_strip_nonfinite(price_history), default=str, allow_nan=False) if price_history else None,
    json.dumps(_strip_nonfinite(company_info),  default=str, allow_nan=False) if company_info  else None,
    json.dumps(_strip_nonfinite(financials),    default=str, allow_nan=False) if financials    else None,
    ...
)
```

`_strip_nonfinite` handles current bad data; `allow_nan=False` makes any future
non-finite value fail loudly at the call site instead of silently as MySQL 3140.

## References

- `.claude/bug-hunts/2026-05-04-ticker-data-json-nan.md` — falsified bug-hunt
- `src/data/aurora/precompute_service.py:1662` — site of `json.dumps`
- `src/data/data_fetcher.py:230-234` — DataFrame transformation
- yfinance version: 0.2.62 (matches Lambda image)
