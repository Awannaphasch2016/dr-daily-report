# Validation Report

**Claim**: "Since we have the data ready, the chart pattern is ready to be displayed on dev telegram miniapp, right?"
**Type**: `config` + `behavior`
**Date**: 2026-01-14

---

## Status: ⚠️ PARTIALLY TRUE

The infrastructure exists but **critical gaps prevent proper display**.

---

## Evidence Summary

### Supporting Evidence (6 items)

1. **Dev API Returns Chart Patterns** ✅
   - Location: `https://ou0ivives1.execute-api.ap-southeast-1.amazonaws.com/api/v1/report/NVDA19`
   - Data: 8 patterns returned (bullish_flag, bearish_flag, triangle, double_bottom, double_top, bullish_vcp, bearish_vcp, head_shoulders)
   - Confidence: High

2. **Frontend Components Exist** ✅
   - `FullChart.tsx` - Has pattern overlay rendering with ReferenceArea
   - `ChartPatternsPanel.tsx` - Pattern list display
   - `MarketModal.tsx` - Passes chart_patterns to components
   - Confidence: High

3. **API Response Structure Correct** ✅
   - Response includes `chart_patterns` array
   - Each pattern has: type, pattern, confidence, start, end, points
   - Confidence: High

4. **Pattern Detection Service Working** ✅
   - `PatternDetectionService` detects patterns
   - `CustomPatternAdapter` extracts coordinate points
   - Confidence: High

5. **Lambda Deployed Recently** ✅
   - `dr-daily-report-telegram-api-dev` last modified: 2026-01-14T05:24:21
   - Confidence: High

6. **Miniapp CloudFront Deployed** ✅
   - URL: `https://d24cidhj2eghux.cloudfront.net/`
   - Confidence: High

---

### Contradicting Evidence (3 items - CRITICAL)

1. **Pattern Points Are EMPTY or Legacy Format** ❌ **CRITICAL**
   - Location: Dev API response
   - Data:
     ```json
     {"type":"bullish_flag","pattern":"flag_pennant","confidence":"low","start":"10","end":"15","points":{}}
     {"type":"triangle","pattern":"triangle","confidence":"medium","start":"5","end":"24","points":{"resistance_level":148.92,"support_level":112.97}}
     ```
   - Impact: **Frontend expects coordinate points like `{A: (date, price), B: (date, price)}` but receives:**
     - Empty `{}` for flags
     - Legacy metadata format (resistance_level, support_level) for others
     - **Lines cannot be drawn on chart without coordinate points**
   - Confidence: High

2. **Start/End Are Bar Indices, Not Dates** ❌ **CRITICAL**
   - Data: `"start":"10","end":"15"` (numeric strings)
   - Impact: Frontend `parseBarIndex()` can handle this, but:
     - No actual date mapping in current data
     - `ReferenceArea` needs X-axis values that map to data points
   - Confidence: High

3. **Migration Not Applied to Dev Aurora** ❌ **MEDIUM**
   - The new `chart_pattern_data` table migration (020) hasn't been applied
   - Current patterns come from live detection, not persisted storage
   - Impact: Patterns regenerated on each request (slow, inconsistent)
   - Confidence: Medium (couldn't verify directly due to SSM tunnel not established)

---

## Root Cause Analysis

The **CustomPatternAdapter** and **ChartPatternDetector** produce coordinate points in their output:

```python
# ChartPatternDetector outputs (chart_patterns.py:240-246)
'points': {
    'A': (self._format_date(segment.index[high_idx_1]), float(highs[high_idx_1])),
    'B': (self._format_date(segment.index[low_idx_1]), float(lows[low_idx_1])),
    ...
}
```

But the data in Aurora's `precomputed_reports` was cached **BEFORE** the coordinate points fix was deployed. The API is returning **stale cached data** with empty/legacy points format.

---

## Verification Steps Performed

1. ✅ Checked dev API endpoint exists
2. ✅ Verified Lambda deployed recently
3. ✅ Confirmed frontend components exist
4. ✅ Retrieved actual API response for NVDA19
5. ✅ Analyzed chart_patterns structure in response
6. ❌ Found points are empty/legacy format

---

## Conclusion

**PARTIALLY TRUE** - The infrastructure chain is complete:
- API returns chart_patterns ✅
- Frontend can render overlays ✅
- Pattern detection code outputs coordinates ✅

**BUT the displayed data is stale** - Aurora's precomputed_reports contains cached data from before the coordinate points fix. The patterns show up in the list but **lines cannot be drawn** because points are empty/legacy.

---

## Recommendations

### Immediate Fix (Required for Display)

1. **Refresh Aurora Cache** - Re-run precompute for tickers to generate fresh data with coordinate points:
   ```bash
   # Option A: Trigger manual precompute
   just dr-precompute-ticker NVDA19 --env dev

   # Option B: Clear cache to force regeneration
   DELETE FROM precomputed_reports WHERE symbol = 'NVDA19';
   ```

2. **Verify After Refresh**:
   ```bash
   curl "https://ou0ivives1.execute-api.ap-southeast-1.amazonaws.com/api/v1/report/NVDA19" | jq '.chart_patterns[0].points'
   # Should return: {"A": ["2026-01-01", 150.25], "B": ["2026-01-05", 155.50], ...}
   ```

### Future Improvements (Optional)

3. **Apply Migration 020** - Create `chart_pattern_data` table for dedicated pattern storage:
   ```bash
   just dr-migrate --env dev
   ```

4. **Integrate Repository** - Store patterns via `ChartPatternDataRepository` instead of embedding in report_json

---

## Next Steps

- [ ] Re-run precompute for test tickers (NVDA19, PFE19, PLTR19)
- [ ] Verify API returns coordinate points after refresh
- [ ] Test pattern overlay rendering in dev miniapp
- [ ] Apply migration 020 to dev Aurora

---

## References

**Code**:
- `src/analysis/pattern_detectors/chart_patterns.py:240-246` (coordinate point output)
- `src/analysis/pattern_detectors/custom_adapter.py:193-224` (point extraction)
- `frontend/twinbar/src/components/FullChart.tsx:168-208` (overlay rendering)

**API**:
- Dev endpoint: `https://ou0ivives1.execute-api.ap-southeast-1.amazonaws.com/api/v1/report/{ticker}`

**Specification**:
- `.claude/specs/shared/chart_pattern_data.md`
