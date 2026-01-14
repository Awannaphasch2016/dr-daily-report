# Telegram Mini App UX Invariants (Pattern Precompute Deploy)

**Domain**: Frontend, API, Telegram, Pattern Detection, Deployment
**Load when**: telegram, miniapp, ux, user experience, pattern precompute, chart pattern
**Purpose**: Ensure user experience remains UNCHANGED after deploying Daily Precomputed Chart Patterns

**Context**: Pattern precompute changes the **data source** (Aurora cache vs ad-hoc detection) but should NOT change what users see or experience.

**Related**:
- [frontend-invariants.md](./frontend-invariants.md)
- [api-invariants.md](./api-invariants.md)
- [chart-pattern-overlay-invariants.md](./chart-pattern-overlay-invariants.md)
- [Specification](../specs/shared/chart_pattern_data.md)

---

## Critical Invariant

```
User Experience Before Deploy = User Experience After Deploy
```

The pattern precompute feature is a **backend optimization** (latency reduction 200-500ms → ~5ms). Users should NOT notice any difference except **faster load times**.

---

## Pre-Deploy Baseline (Capture These)

Before deploying, record current state for comparison:

### Baseline Data to Capture

| Metric | How to Capture | Purpose |
|--------|----------------|---------|
| Pattern count for NVDA19 | `curl .../report/NVDA19 \| jq '.chart_patterns \| length'` | Verify same patterns returned |
| Pattern types | `jq '.chart_patterns[].type'` | Same pattern types detected |
| Coordinate points format | `jq '.chart_patterns[0].points.A'` | Format unchanged (`[date, price]`) |
| API response time | `time curl ...` | Should IMPROVE |
| Visual screenshot | Take screenshot of NVDA19 chart | Visual regression baseline |

### Capture Commands

```bash
# 1. Capture baseline pattern count
API_URL="https://ou0ivives1.execute-api.ap-southeast-1.amazonaws.com"
curl -s "$API_URL/api/v1/report/NVDA19" | jq '.chart_patterns | length' > /tmp/baseline_pattern_count.txt

# 2. Capture pattern types
curl -s "$API_URL/api/v1/report/NVDA19" | jq '[.chart_patterns[].type] | sort' > /tmp/baseline_pattern_types.txt

# 3. Capture response time
time curl -s "$API_URL/api/v1/report/NVDA19" > /tmp/baseline_response.json 2>&1

# 4. Take visual screenshot (manual or Playwright)
# Open Telegram Mini App → Select NVDA19 → Open chart modal → Screenshot
```

---

## Level 4: Configuration Invariants (MUST NOT CHANGE)

### Backend Configuration
- [ ] `CHART_PATTERN_DATA` constant in `table_names.py` → EXISTS (unchanged)
- [ ] `PatternDetectionService` pattern types → SAME (unchanged)
- [ ] API response schema → SAME (unchanged)
- [ ] Environment variables → SAME (unchanged)

### Frontend Configuration (SHOULD BE UNCHANGED)
- [ ] `ChartPattern` TypeScript type → UNCHANGED
- [ ] `chart_patterns` field in API types → UNCHANGED
- [ ] Pattern colors in `FullChart.tsx` → UNCHANGED
- [ ] `patternOverlays` useMemo logic → UNCHANGED

### Verification Commands
```bash
# Verify no frontend changes required
git diff HEAD~5..HEAD frontend/twinbar/src/types/report.ts
# Expected: No changes OR only additions

# Verify API types unchanged
grep -A20 "chart_patterns" frontend/twinbar/src/types/report.ts

# Verify pattern colors unchanged
grep -B5 -A10 "patternColor" frontend/twinbar/src/components/FullChart.tsx
```

---

## Level 3: Infrastructure Invariants (MUST WORK)

### New Infrastructure (Added)
- [ ] `pattern-precompute` Lambda exists and runs
- [ ] Step Functions has `FanOutToPatternWorkers` state
- [ ] CloudWatch log group created
- [ ] IAM permissions allow Step Functions → Lambda invoke

### Existing Infrastructure (UNCHANGED)
- [ ] `telegram-api` Lambda still works
- [ ] API Gateway routes unchanged
- [ ] CloudFront serves frontend
- [ ] Aurora connectivity works

### Verification Commands
```bash
# NEW: Verify pattern Lambda exists
aws lambda get-function \
  --function-name dr-daily-report-pattern-precompute-dev \
  --query 'Configuration.FunctionName'

# EXISTING: Verify API Lambda still works
aws lambda invoke \
  --function-name dr-daily-report-telegram-api-dev \
  --payload '{"httpMethod":"GET","path":"/health"}' \
  /tmp/health.json && cat /tmp/health.json
```

---

## Level 2: Data Invariants (CRITICAL - SAME OUTPUT)

### API Response Structure
- [ ] `chart_patterns` field EXISTS in response
- [ ] `chart_patterns` is ARRAY (not null, not undefined)
- [ ] Each pattern has: `type`, `pattern`, `confidence`, `points`
- [ ] `points` has coordinate format: `{A: [date, price], ...}`

### Data Equivalence
- [ ] Pattern COUNT: Same as baseline (±10% due to daily variance)
- [ ] Pattern TYPES: Same types detected
- [ ] Pattern COORDINATES: Same format `[date, price]`
- [ ] Pattern CONFIDENCE: Same values (high/medium/low)

### Data Source Transparency
- [ ] User CANNOT tell if data is cached or ad-hoc
- [ ] API response format is IDENTICAL regardless of source
- [ ] No new fields added that frontend doesn't expect
- [ ] No fields removed that frontend depends on

### Verification Commands
```bash
# After deploy, compare with baseline
API_URL="https://ou0ivives1.execute-api.ap-southeast-1.amazonaws.com"

# 1. Pattern count comparison
AFTER=$(curl -s "$API_URL/api/v1/report/NVDA19" | jq '.chart_patterns | length')
BEFORE=$(cat /tmp/baseline_pattern_count.txt)
echo "Before: $BEFORE, After: $AFTER"
# Expected: Similar count (daily variance ok)

# 2. Pattern types comparison
curl -s "$API_URL/api/v1/report/NVDA19" | jq '[.chart_patterns[].type] | sort' > /tmp/after_pattern_types.txt
diff /tmp/baseline_pattern_types.txt /tmp/after_pattern_types.txt
# Expected: No difference OR new patterns (not fewer)

# 3. Coordinate format verification
curl -s "$API_URL/api/v1/report/NVDA19" | jq '.chart_patterns[0].points | keys'
# Expected: ["A", "B", ...] or similar

curl -s "$API_URL/api/v1/report/NVDA19" | jq '.chart_patterns[0].points.A'
# Expected: ["2026-01-XX", 123.45] (tuple with date and price)
```

---

## Level 1: Service Invariants (BEHAVIOR UNCHANGED)

### API Behavior
- [ ] `/api/v1/report/{ticker}` returns 200 with patterns
- [ ] `/api/v1/report/{ticker}` returns SAME schema
- [ ] Error handling unchanged (invalid ticker → 404)
- [ ] Response time IMPROVED (not degraded)

### Cache Fallback (NEW BUT INVISIBLE)
- [ ] Cache HIT: Returns cached patterns (~5ms)
- [ ] Cache MISS: Falls back to ad-hoc detection (200-500ms)
- [ ] Fallback is TRANSPARENT to user
- [ ] No error shown on fallback

### Pattern Detection
- [ ] Same patterns detected (coordinate format)
- [ ] Same detection algorithm (custom detector)
- [ ] Same confidence calculation
- [ ] Same error handling (errors → empty array)

### Verification Commands
```bash
# API response time (should IMPROVE)
time curl -s "$API_URL/api/v1/report/NVDA19" > /dev/null
# Expected: Faster than baseline (if cache hit)

# Error handling unchanged
curl -w "\n%{http_code}\n" -s "$API_URL/api/v1/report/INVALID_TICKER"
# Expected: 404 with error message

# Verify patterns in response
curl -s "$API_URL/api/v1/report/NVDA19" | jq '.chart_patterns | length'
# Expected: > 0 (patterns exist)
```

---

## Level 0: User Invariants (UX UNCHANGED)

### Navigation Flow (MUST BE IDENTICAL)
- [ ] Open Telegram → Mini App launches
- [ ] Ticker list loads (46 tickers)
- [ ] Click ticker → Report modal opens
- [ ] Click chart → Full chart modal opens
- [ ] Back navigation works correctly
- [ ] State persists during navigation

### Visual Display (MUST BE IDENTICAL)
- [ ] Candlestick chart renders correctly
- [ ] Pattern overlays visible (if patterns exist)
- [ ] Pattern colors: bullish=green, bearish=red
- [ ] Pattern trendlines align with candles
- [ ] Pattern panel shows pattern list
- [ ] Confidence badges displayed

### Interactions (MUST BE IDENTICAL)
- [ ] Chart zoom works
- [ ] Chart pan works
- [ ] Tooltip shows on hover
- [ ] Mobile touch gestures work
- [ ] Loading spinner shows during fetch

### Performance (SHOULD IMPROVE)
- [ ] Initial load: Same or faster
- [ ] Report load: Same or faster
- [ ] Chart load: FASTER (main benefit)
- [ ] No new loading states
- [ ] No new error states

### Verification Steps (Manual)

**Test Script:**
1. Open Telegram app
2. Open Daily Report Mini App
3. Verify ticker list loads (46 tickers)
4. Select "NVDA19" ticker
5. Verify report modal opens
6. Click "View Chart" button
7. Verify full chart modal opens
8. Verify candlesticks render
9. Verify pattern overlays visible (trendlines)
10. Verify pattern panel shows patterns
11. Test zoom gesture (pinch)
12. Test pan gesture (drag)
13. Press back button
14. Verify navigation returns to report
15. Press back button
16. Verify navigation returns to ticker list

**Expected Result**: All steps work EXACTLY as before deploy.

---

## User Experience Checklist

### Before Deploy (Baseline)
- [ ] Captured pattern count for NVDA19
- [ ] Captured pattern types list
- [ ] Captured screenshot of chart with overlays
- [ ] Captured API response time baseline

### After Deploy (Verification)
- [ ] Pattern count similar (±10%)
- [ ] Pattern types same
- [ ] Screenshot comparison: No visual difference
- [ ] API response time: Same or FASTER

### Regression Testing
- [ ] Navigation flow: No regressions
- [ ] Visual display: No regressions
- [ ] Interactions: No regressions
- [ ] Error states: No new errors

---

## What Should Change (Expected)

| Aspect | Before | After | Status |
|--------|--------|-------|--------|
| API response time (chart patterns) | 200-500ms | ~5ms (cache) or 200-500ms (fallback) | ✅ Improvement |
| Data source | Ad-hoc detection | Aurora cache (with fallback) | ✅ Internal change |
| Pattern data | From detection | From `chart_pattern_data` table | ✅ Internal change |
| Lambda invocations | On every request | Once daily (precompute) | ✅ Cost reduction |

---

## What Should NOT Change (Invariants)

| Aspect | Before | After | Must Be |
|--------|--------|-------|---------|
| API response schema | `{chart_patterns: [...]}` | `{chart_patterns: [...]}` | IDENTICAL |
| Pattern format | `{type, pattern, confidence, points}` | `{type, pattern, confidence, points}` | IDENTICAL |
| Points format | `{A: [date, price], ...}` | `{A: [date, price], ...}` | IDENTICAL |
| Frontend code | `FullChart.tsx` | `FullChart.tsx` | UNCHANGED |
| User flow | Open → Select → View → Chart | Open → Select → View → Chart | UNCHANGED |
| Visual appearance | Trendlines on chart | Trendlines on chart | IDENTICAL |

---

## Claiming "Deploy Complete - UX Unchanged"

```markdown
✅ Pattern Precompute Deploy Complete - UX Unchanged

**Goal**: Deploy Daily Precomputed Chart Patterns
**Risk**: User experience regression

**Invariants Verified**:
- [x] Level 4: Config unchanged (types, constants, env vars)
- [x] Level 3: Infrastructure works (new Lambda + existing)
- [x] Level 2: Data identical (same format, same patterns)
- [x] Level 1: Service behavior unchanged (API schema, errors)
- [x] Level 0: User experience unchanged (navigation, visuals, interactions)

**Performance Impact**:
- Before: {baseline_response_time}
- After: {new_response_time}
- Improvement: {percentage}%

**Confidence**: HIGH
**Evidence**:
- API response diff: No schema changes
- Pattern count: Before={X}, After={Y} (within variance)
- Screenshot comparison: Visually identical
- Manual test: All 15 steps passed
```

---

## Rollback Criteria

If ANY of these fail after deploy, rollback:

| Severity | Condition | Action |
|----------|-----------|--------|
| **CRITICAL** | API returns error (5xx) | Rollback immediately |
| **CRITICAL** | Frontend crashes | Rollback immediately |
| **HIGH** | Patterns not showing | Investigate, rollback if not fixable |
| **HIGH** | Wrong pattern data | Investigate cache, force ad-hoc fallback |
| **MEDIUM** | Response time degraded | Monitor, may indicate fallback loop |
| **LOW** | Slightly different pattern count | Expected (daily variance) |

---

## Post-Deploy Monitoring

After deploy, monitor for 24 hours:

```bash
# Monitor API errors
aws logs filter-log-events \
  --log-group-name /aws/lambda/dr-daily-report-telegram-api-dev \
  --filter-pattern "ERROR" \
  --start-time $(date -d '1 hour ago' +%s000)

# Monitor pattern Lambda
aws logs filter-log-events \
  --log-group-name /aws/lambda/dr-daily-report-pattern-precompute-dev \
  --filter-pattern "ERROR" \
  --start-time $(date -d '1 hour ago' +%s000)

# Check cache hit rate (look for "Cache lookup" in logs)
aws logs filter-log-events \
  --log-group-name /aws/lambda/dr-daily-report-telegram-api-dev \
  --filter-pattern "cached patterns" \
  --start-time $(date -d '1 hour ago' +%s000)
```

---

*Domain: telegram-miniapp-ux*
*Created: 2026-01-15*
*Purpose: Ensure UX unchanged after pattern precompute deploy*
*Related: /deploy, /reconcile, /validate*
