# Validation Report

**Claim**: "In prod, when I send NOW19, LINE Bot doesn't respond with NOW19 report"
**Type**: behavior + config
**Date**: 2026-01-22T13:00:00+07:00

---

## Status: ✅ TRUE (Line Bot NOT responding to NOW19)

## Root Cause: LINE Bot Lambda has OLD Docker image

| Component | Expected | Actual | Status |
|-----------|----------|--------|--------|
| Aurora `ticker_aliases` | NOW19 registered | ✅ NOW19 present | OK |
| Aurora `precomputed_reports` | Report for NOW | ✅ Report exists (completed) | OK |
| LINE Bot Lambda image | `ticker-update-20260121-201359` | ❌ `sha-29ee795-20260114-053331` | **WRONG** |

---

## Evidence Summary

### 1. Aurora Data - Complete ✅

```sql
-- NOW19 is registered in Aurora
SELECT symbol, symbol_type, company_name FROM ticker_aliases ta
JOIN ticker_master tm ON ta.ticker_id = tm.id
WHERE symbol IN ('NOW19', 'NOW');

-- Result:
-- NOW19 | dr    | ServiceNow Inc.
-- NOW   | yahoo | ServiceNow Inc.
```

```sql
-- Precomputed report exists for NOW
SELECT symbol, DATE(report_date), status, LEFT(report_text, 100)
FROM precomputed_reports WHERE symbol = 'NOW' ORDER BY report_date DESC LIMIT 2;

-- Result:
-- NOW | 2026-01-22 | completed | 📖 **เรื่องราวของหุ้นตัวนี้**\n\nNOW19 กำลังอยู่ในตลาด...
-- NOW | 2026-01-21 | completed | 📖 **เรื่องราวของหุ้น NOW19**\n\nหุ้น NOW19 ของ ServiceNow...
```

### 2. LINE Bot Lambda - WRONG IMAGE ❌

```bash
# LINE Bot Lambda is using OLD image from January 14th
aws lambda get-function --function-name dr-daily-report-line-bot-prod \
  --query "Code.ImageUri" --output text

# Result:
755283537543.dkr.ecr.ap-southeast-1.amazonaws.com/dr-daily-report-lambda-prod:sha-29ee795-20260114-053331
#                                                                              ^^^^^^^^^^^^^^^^^^^^^^^^
#                                                                              Jan 14th - DOES NOT have NOW19
```

**Expected image**: `ticker-update-20260121-201359` (Jan 21st - has NOW19)

### 3. Code Path Analysis

When user sends "NOW19" to LINE Bot:

```
1. LineBot.__init__() loads ticker_map from DataFetcher.load_tickers()
   └── Reads from tickers.csv BAKED INTO Docker image
   └── Old image (Jan 14) has 46 tickers, NOT 56

2. handle_message() calls ticker_matcher.match_with_suggestion("NOW19")
   └── TickerMatcher checks if "NOW19" in ticker_map
   └── NOW19 NOT in old tickers.csv → No exact match
   └── Fuzzy matching may match to something else or fail

3. precompute.get_cached_report(matched_ticker)
   └── If fuzzy match found different ticker → returns wrong report
   └── If no match → returns None → "รายงานยังไม่พร้อม" message
```

---

## Analysis

### Why NOW19 doesn't work

1. **tickers.csv is baked into Docker image at build time** (Dockerfile.lambda.container line 20)
2. **LINE Bot Lambda was NOT updated** after new tickers were added
3. **10 new tickers added on Jan 21st** but LINE Bot still uses Jan 14th image

### Which Lambdas were updated vs not

| Lambda | Current Image | Has NOW19? |
|--------|---------------|------------|
| `dr-daily-report-line-bot-prod` | `sha-29ee795-20260114` | ❌ NO |
| `dr-daily-report-ticker-scheduler-prod` | `ticker-update-20260121` | ✅ YES |
| `dr-daily-report-ticker-fetcher-prod` | `ticker-update-20260121` | ✅ YES |
| `dr-daily-report-report-worker-prod` | `ticker-update-20260121` | ✅ YES |

**Gap**: LINE Bot Lambda was missed when updating Lambdas with new tickers.

---

## Confidence Level: HIGH

**Reasoning**:
- Direct verification of Lambda image tag shows old date
- Code path clearly shows tickers.csv dependency
- Aurora data verified complete (reports exist for NOW)
- Root cause identified with certainty

---

## Recommendations

**Fix Required**: Update LINE Bot Lambda to use new image

```bash
# Update LINE Bot Lambda with new image
aws lambda update-function-code \
  --function-name dr-daily-report-line-bot-prod \
  --image-uri 755283537543.dkr.ecr.ap-southeast-1.amazonaws.com/dr-daily-report-lambda-prod:ticker-update-20260121-201359
```

**After fix**:
1. All 10 new tickers (including NOW19) will work
2. No other changes needed - Aurora data is already complete

---

## Affected Tickers (10 total)

These tickers won't work until LINE Bot Lambda is updated:

1. AAPL19 (Apple)
2. ADVANT19 (Advantest)
3. DDOG19 (Datadog)
4. HANSOH19 (Hansoh Pharmaceutical)
5. ISRG19 (Intuitive Surgical)
6. MICRON19 (Micron Technology)
7. MSFT19 (Microsoft)
8. MSN19 (Masan Group)
9. **NOW19 (ServiceNow)** ← User's question
10. SINOBIO19 (Sino Biopharmaceutical)

---

## References

**AWS Resources**:
- LINE Bot Lambda: `dr-daily-report-line-bot-prod`
- Old image: `sha-29ee795-20260114-053331` (Jan 14)
- New image: `ticker-update-20260121-201359` (Jan 21)

**Code Files**:
- `src/integrations/line_bot.py:32-34` - loads ticker_map
- `src/data/data_fetcher.py:478-491` - load_tickers() from CSV
- `Dockerfile.lambda.container:20` - copies tickers.csv into image

**Related Commits**:
- `83e7d0c` (Jan 21) - Added 10 new tickers to tickers.csv
