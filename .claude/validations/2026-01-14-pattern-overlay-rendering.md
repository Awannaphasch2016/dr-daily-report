# Validation Report

**Claim**: "Pattern overlay lines render on chart in browser"
**Type**: behavior (visual rendering)
**Date**: 2026-01-14

---

## Status: ❌ FALSE

Pattern overlay lines are NOT rendering on the chart because the API response contains patterns with **empty coordinate points** (`points: {}`).

---

## Evidence Summary

**Supporting evidence** (0 items):
- None - no pattern lines visible in screenshot

**Contradicting evidence** (4 items):

1. **Screenshot Visual Inspection**:
   - Location: `/tmp/validate_2_chart.png`
   - Data: Chart shows candlesticks + SMA lines only
   - Finding: "No chart patterns detected" message displayed
   - SVG polylines: 0 (no pattern lines rendered)

2. **API Response for VCB19**:
   - Location: `https://4fkoav2wth.execute-api.ap-southeast-1.amazonaws.com/api/v1/report/VCB19`
   - Data: 3 patterns detected, but flags have `points: {}`
   - Finding: Only `double_top` has partial metadata points (prices only, no dates)

   ```json
   {
     "type": "bullish_flag",
     "points": {}  // EMPTY - no coordinate points
   },
   {
     "type": "double_top",
     "points": {
       "peak1_price": 59565.21875,  // Price only, no date coordinate
       "peak2_price": 59565.216589376054,
       "valley_price": 55693.4765625
     }
   }
   ```

3. **Frontend Validation Logic** (`FullChart.tsx`):
   - Location: `frontend/twinbar/src/components/FullChart.tsx:168`
   - Data: `hasValidPoints()` function checks for `[date, price]` tuples
   - Finding: Returns `false` for empty points or metadata-only points

4. **Local Code Test** (verified working):
   - Location: Local Python environment
   - Data: Pattern detector NOW outputs proper coordinate points
   - Finding: Code fix is correct, but Aurora DB has cached old data

   ```python
   # Local test output (CORRECT):
   points={'A': ('2025-07-25', 214.78...), 'B': ('2025-08-01', 201.07...)}
   ```

**Root Cause**:
- Pattern detection code was fixed to output coordinate points
- Lambda functions were updated with new Docker image
- BUT Aurora database still contains cached pattern data from BEFORE the fix
- The precompute workflow didn't regenerate pattern data for existing tickers

---

## Analysis

### Overall Assessment

The pattern overlay feature is **correctly implemented** in both:
- Backend: `chart_patterns.py` now outputs `{A: (date, price), B: (date, price), ...}`
- Frontend: `FullChart.tsx` renders SVG polylines connecting points A→B→C→D→E

However, the **deployed data is stale**. The Aurora database contains pattern data generated BEFORE the fix was deployed. Until reports are regenerated with the new code, pattern overlays will not render.

### Key Findings

1. **Code fix verified locally**: Pattern detector outputs proper coordinate points
2. **Lambda updated**: New Docker image deployed to dev environment
3. **Data not refreshed**: Aurora DB has old cached pattern data
4. **Frontend working**: Would render patterns if data had coordinate points

### Confidence Level: HIGH

**Reasoning**:
- Direct visual inspection confirms no pattern lines
- API response confirms empty `points: {}` for flags
- Local test confirms code fix works correctly
- Root cause clearly identified (cached data)

---

## Recommendations

**Since FALSE**:

1. **DO NOT assume pattern overlays are working** - they render only when data has coordinate points

2. **To fix**: Trigger full report regeneration for tickers
   - Option A: Wait for nightly scheduled precompute job
   - Option B: Manually trigger precompute with `force_refresh=true` for specific tickers
   - Option C: Clear Aurora cache for pattern data and re-run detection

3. **Verification after fix**:
   ```bash
   # Check API response has coordinate points
   curl .../api/v1/report/TICKER | jq '.chart_patterns[].points'
   # Should show: {"A": ["2025-07-25", 214.78], "B": ["2025-08-01", 201.07], ...}
   ```

4. **Alternative quick validation**:
   - Add a new ticker that doesn't exist in Aurora
   - Trigger report generation for that ticker
   - New data will use updated code with coordinate points

---

## Next Steps

- [ ] Wait for nightly precompute job to regenerate reports
- [ ] OR manually trigger regeneration for test ticker
- [ ] Re-validate after data refresh: `/validate "pattern lines render on chart"`
- [ ] Document in journal once confirmed working

---

## References

**Screenshots**:
- `/tmp/validate_2_chart.png` - Chart showing "No chart patterns detected"

**Code**:
- `src/analysis/pattern_detectors/chart_patterns.py` - Fixed to output coordinate points
- `frontend/twinbar/src/components/FullChart.tsx:168` - `hasValidPoints()` validation

**API**:
- Staging: `https://4fkoav2wth.execute-api.ap-southeast-1.amazonaws.com/api/v1/report/{ticker}`

**Commits**:
- `e27c1a5` - feat(patterns): Add coordinate points to custom pattern detector
- `29ee795` - fix(deps): Pin pyarrow to 16.1.0 for Lambda prebuilt wheels
