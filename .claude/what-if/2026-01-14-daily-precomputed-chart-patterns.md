# What-If Analysis: Daily Precomputed Chart Patterns

**Date**: 2026-01-14
**Question**: Since we already have chart pattern tables in the database, don't you think it's a good idea to have chart patterns be computed daily, similar to how data is fetched and precompute is run?

---

## Current Reality (Baseline)

**Current design**: Chart patterns computed **ad-hoc** on every API request

```
User request → ResponseTransformer._detect_chart_patterns(ticker)
                        ↓
             PatternDetectionService.detect_patterns()
                        ↓
             Fetch 180 days OHLC from Aurora
                        ↓
             Run pattern detection algorithms
                        ↓
             Return patterns in API response
```

**Sources**:
- `src/api/transformer.py:196-197` - transform_report calls _detect_chart_patterns
- `src/api/transformer.py:1062-1063` - transform_cached_report ALSO calls _detect_chart_patterns (inefficient)
- `src/services/pattern_detection_service.py` - Pattern detection logic

**Existing infrastructure (ready but unused)**:
- Migration `020_create_chart_pattern_data.sql` - Table schema exists
- `src/data/aurora/chart_pattern_repository.py` - Full CRUD repository ready
- `src/data/aurora/table_names.py:64` - CHART_PATTERN_DATA constant defined

---

## Under New Assumption: Daily Precomputed Patterns

```
Daily Schedule (EventBridge)
        ↓
PatternPrecomputeHandler (NEW)
        ↓
For each ticker in ticker_master:
    ├── Fetch OHLC data
    ├── Run pattern detection
    └── Store in chart_pattern_data (upsert)
        ↓
API request
        ↓
ChartPatternRepository.get_patterns_for_symbol(ticker)
        ↓
Return cached patterns (instant, no computation)
```

---

## What Changes Immediately

| Aspect | Current (Ad-hoc) | Proposed (Precomputed) |
|--------|-----------------|------------------------|
| **Computation** | Every request | Once daily |
| **Latency** | +200-500ms per request | ~1ms (DB lookup) |
| **Data freshness** | Real-time | 24h max staleness |
| **Infrastructure** | Lambda-only | Lambda + EventBridge + DB |

---

## What Breaks (Potential Issues)

### 1. Data Freshness Gap
- **Issue**: Patterns could be up to 24 hours stale
- **Impact**: A pattern that formed at 3pm won't appear until next day's precompute
- **Severity**: Low - Pattern detection uses 180 days of data; 1 day doesn't significantly change patterns
- **Mitigation**: Run precompute after market close (4pm EST / 5am ICT next day)

### 2. Migration Timing
- **Issue**: Migration 020 must be applied before code deployment
- **Impact**: If code deployed before migration, DB queries will fail
- **Severity**: Medium - Standard deployment coordination
- **Mitigation**: Deploy migration first, verify table exists, then deploy code

### 3. Initial Data Population
- **Issue**: Table will be empty on first deployment
- **Impact**: First day's reports won't have patterns
- **Severity**: Low - One-time issue
- **Mitigation**: Run manual precompute immediately after deployment

---

## What Improves

### 1. Performance (Major Win)

| Metric | Current | Proposed | Improvement |
|--------|---------|----------|-------------|
| Pattern detection time | 200-500ms | 0ms | 100% |
| DB query time | 0ms | ~5ms | N/A (new) |
| **Net per request** | **200-500ms** | **~5ms** | **97-99%** |

**Annual Lambda compute savings**:
- Requests/day: ~10,000 (estimated)
- Compute per request: 0.3s × 10,000 = 3,000s/day saved
- Lambda cost savings: ~$0.05/day × 365 = **~$18/year**
- Real benefit: **Faster user experience**, not cost

### 2. Consistency (Data Stability)

**Current problem**: Same request may return different patterns if:
- Detection algorithms have variance
- Price data slightly different between requests
- Race conditions in data fetching

**Proposed solution**: Patterns computed once, stable for 24h:
- Users see consistent patterns across sessions
- Easier to debug/reproduce issues
- Can version patterns by implementation

### 3. Separation of Concerns

**Current**: API Lambda does two jobs (serve request + detect patterns)
**Proposed**:
- Precompute Lambda: Heavy pattern detection
- API Lambda: Fast data retrieval

Benefits:
- API Lambda more predictable latency
- Pattern detection can have longer timeout without affecting API
- Can run pattern detection with more thorough parameters (not constrained by API timeout)

### 4. A/B Testing & Analytics

**Current**: No historical pattern data
**Proposed**: With `chart_pattern_data` table:
- Track pattern detection accuracy over time
- Compare implementations (stock_pattern vs custom)
- Analyze which patterns correlate with price movements

---

## Cascading Effects Analysis

```
Precomputed Patterns
        ↓
┌───────────────────────────────────────────────────────────┐
│ Level 1 (Direct)                                          │
├───────────────────────────────────────────────────────────┤
│ ✅ API response faster (200-500ms → 5ms)                  │
│ ✅ Cached report path actually uses cache (consistent)    │
│ ⚠️ Patterns up to 24h stale                               │
└───────────────────────────────────────────────────────────┘
        ↓
┌───────────────────────────────────────────────────────────┐
│ Level 2 (Indirect)                                        │
├───────────────────────────────────────────────────────────┤
│ ✅ API Lambda can have tighter timeout (shorter SLA)      │
│ ✅ Less Aurora pressure during peak hours                 │
│ ✅ Pattern detection can be more thorough (off-peak)      │
│ ⚠️ New Lambda function to maintain                        │
│ ⚠️ New EventBridge rule to configure                      │
└───────────────────────────────────────────────────────────┘
        ↓
┌───────────────────────────────────────────────────────────┐
│ Level 3 (System-wide)                                     │
├───────────────────────────────────────────────────────────┤
│ ✅ Historical pattern data enables analytics              │
│ ✅ Implementation comparison (A/B testing)                │
│ ✅ Pattern success rate tracking (future)                 │
│ ⚠️ DB storage growth (~50KB/ticker/day = ~850KB/day)      │
│ ⚠️ Migration coordination required                        │
└───────────────────────────────────────────────────────────┘
```

---

## Implementation Effort

### Already Done (Reuse)
- [x] Migration 020 schema - Ready to apply
- [x] ChartPatternRepository - Full CRUD implemented
- [x] PatternDetectionService - Works with registry

### New Work Required

| Component | Effort | Priority |
|-----------|--------|----------|
| Apply migration 020 | 5 min | P0 |
| PatternPrecomputeHandler Lambda | 2-3 hours | P0 |
| EventBridge rule (daily schedule) | 30 min | P0 |
| Modify ResponseTransformer to use DB | 1 hour | P0 |
| Terraform infrastructure | 1-2 hours | P0 |
| Testing & validation | 2-3 hours | P0 |
| **Total** | **~1 day** | |

### Integration Points

```python
# transformer.py change (simplified)
def _detect_chart_patterns(self, ticker: str) -> list[ChartPattern]:
    # NEW: Try cached patterns first
    from src.data.aurora.chart_pattern_repository import get_chart_pattern_repository
    from datetime import date

    repo = get_chart_pattern_repository()
    cached_patterns = repo.get_patterns_for_symbol(
        symbol=ticker,
        pattern_date=date.today()  # Get today's patterns
    )

    if cached_patterns:
        return [ChartPattern(**p) for p in cached_patterns]

    # FALLBACK: Ad-hoc detection (same as current)
    pattern_service = get_pattern_service()
    result = pattern_service.detect_patterns(ticker, days=180)
    # ... existing logic
```

---

## Comparison Matrix

| Criterion | Ad-hoc (Current) | Precomputed (Proposed) |
|-----------|-----------------|------------------------|
| **Latency** | ❌ 200-500ms | ✅ ~5ms |
| **Freshness** | ✅ Real-time | ⚠️ 24h max stale |
| **Consistency** | ❌ Variable | ✅ Stable |
| **Complexity** | ✅ Simple | ⚠️ More moving parts |
| **Analytics** | ❌ None | ✅ Historical data |
| **Scaling** | ❌ Linear with traffic | ✅ Constant |
| **Storage** | ✅ None | ⚠️ ~850KB/day |
| **Implementation** | ✅ Done | ⚠️ ~1 day work |

---

## Insights Revealed

### Assumptions Exposed

1. **Real-time patterns are not critical**
   - Evidence: Patterns use 180 days of data; 1 day staleness is <0.5% of data
   - Users won't notice difference between "detected 5 seconds ago" vs "detected 8 hours ago"

2. **Current architecture is inefficient for cached reports**
   - Evidence: `transform_cached_report` (line 1062) ALSO runs pattern detection
   - Even when report is cached, patterns are computed fresh
   - This negates much of the caching benefit

3. **Infrastructure already exists**
   - Evidence: Migration 020 + ChartPatternRepository fully implemented
   - Only integration code missing

### Trade-offs Clarified

| Trade-off | Current Choice | Alternative |
|-----------|---------------|-------------|
| Freshness vs Speed | Freshness | **Speed recommended** |
| Simplicity vs Analytics | Simplicity | **Analytics recommended** |
| Per-request vs Batch | Per-request | **Batch recommended** |

---

## Recommendation: ✅ YES, Implement Daily Precomputed Patterns

**Rationale**:

1. **Existing infrastructure**: 90% of the work already done (migration, repository, service)
2. **Significant UX improvement**: 97-99% reduction in pattern detection latency
3. **Consistency win**: Stable patterns across sessions
4. **Analytics enablement**: Historical data for future features
5. **Scaling**: Constant cost regardless of traffic

**Trade-off acceptance**:
- Lose: Real-time pattern freshness (acceptable - patterns don't change by the minute)
- Gain: Speed, consistency, analytics, scalability

---

## Action Items

### Phase 1: Core Implementation (~1 day)

```bash
# 1. Apply migration
just dr migrate-run 020

# 2. Create precompute handler
# src/scheduler/pattern_precompute_handler.py

# 3. Update transformer to use cached patterns
# src/api/transformer.py

# 4. Add EventBridge rule in Terraform
# terraform/scheduler.tf

# 5. Test end-to-end
```

### Phase 2: Optimization (Future)

- [ ] Add pattern success rate tracking
- [ ] Implement A/B testing between implementations
- [ ] Add cache invalidation on significant price moves
- [ ] Consider intraday refresh for active traders

---

## Related Work

- **Existing spec**: `.claude/specs/shared/chart_pattern_data.md`
- **Migration**: `db/migrations/020_create_chart_pattern_data.sql`
- **Repository**: `src/data/aurora/chart_pattern_repository.py`
- **Current detection**: `src/services/pattern_detection_service.py`

---

*What-if analysis complete*
*Recommendation: Proceed with implementation*
*Estimated effort: ~1 day*
*Expected benefit: 97-99% latency reduction for pattern data*
