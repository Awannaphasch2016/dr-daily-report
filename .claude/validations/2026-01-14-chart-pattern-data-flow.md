# Validation Report: Chart Pattern Data Flow

**Date**: 2026-01-14
**Question**: Is chart pattern generated ad-hoc when clicking on a box, or is it stored somewhere and UI retrieves it to display?

---

## Answer: Ad-Hoc Generation (NOT Stored)

**Chart patterns are computed ad-hoc every time the report is requested.** They are NOT stored in the database.

---

## Data Flow Architecture

```
User clicks ticker → API request → ResponseTransformer._detect_chart_patterns()
                                          ↓
                           PatternDetectionService.detect_patterns()
                                          ↓
                           Fetch OHLC data from Aurora (daily_prices)
                                          ↓
                           Run pattern detection algorithms
                                          ↓
                           Return patterns to API response
                                          ↓
                           Frontend displays overlays on chart
```

---

## Evidence

### 1. API Transformer (src/api/transformer.py)

**Lines 196-197** (in `transform_report`):
```python
# Detect chart patterns
chart_patterns = self._detect_chart_patterns(ticker)
```

**Lines 1062-1063** (in `transform_cached_report`):
```python
# Detect chart patterns
chart_patterns = self._detect_chart_patterns(ticker)
```

Both the fresh report path AND cached report path call `_detect_chart_patterns()` - meaning patterns are **always computed ad-hoc**, even for cached reports.

**Lines 865-894** (`_detect_chart_patterns` method):
```python
def _detect_chart_patterns(self, ticker: str) -> list[ChartPattern]:
    """Detect chart patterns using stock-pattern library"""
    try:
        pattern_service = get_pattern_service()
        result = pattern_service.detect_patterns(ticker, days=180)
        # ... convert to ChartPattern objects
    except Exception as e:
        logger.error(f"❌ Pattern detection failed for {ticker}: {e}")
        return []  # Return empty list on failure (defensive)
```

### 2. Pattern Detection Service (src/services/pattern_detection_service.py)

**Lines 171-203** (`_fetch_ohlc_data`):
- Fetches fresh OHLC data from `daily_prices` table
- Falls back to `precomputed_reports.price_history` if daily_prices empty

**Lines 317-376** (`_detect_all_patterns`):
- Runs pattern detection algorithms on the OHLC data
- Uses registry pattern with fallback (custom detector priority=10, stock-pattern priority=5)
- No database lookup for cached patterns

### 3. No Pattern Storage Table

There is no dedicated table for storing detected patterns. The `chart_pattern_data` table name constant exists in `table_names.py`, but migration 020 was prepared but not yet integrated.

---

## Implications

### Performance
- Pattern detection runs on every report request
- ~180 days of OHLC data processed each time
- Custom detector includes: flags, triangles, double tops/bottoms, head & shoulders, VCP

### Freshness
- Patterns are always up-to-date with latest price data
- No stale pattern cache to invalidate

### Consistency
- Patterns may change between requests if price data changes
- No guaranteed stability of pattern output

---

## Potential Improvement: Pattern Caching

If pattern detection becomes a performance bottleneck, consider:

1. **Store patterns in `chart_pattern_data` table** (migration 020 ready)
2. **Invalidate on price data update** (daily refresh)
3. **Return cached patterns from `transform_cached_report`**

This would change the architecture to:
```
Precompute workflow → Detect patterns → Store in chart_pattern_data
Report request → Check chart_pattern_data → Return cached patterns
```

---

## Summary

| Aspect | Current State |
|--------|---------------|
| **Generation** | Ad-hoc (on every request) |
| **Storage** | None (not persisted) |
| **Data Source** | Aurora `daily_prices` or `precomputed_reports.price_history` |
| **Cache Hit Path** | Still computes patterns ad-hoc |
| **Performance** | Acceptable for current load |

**Confidence**: HIGH
**Evidence Type**: Code analysis (Layer 2)

---

*Validated by: Claude*
*Validation date: 2026-01-14*
