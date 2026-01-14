# Chart Pattern Overlay Invariants

**Domain**: Frontend, API, Data, Pattern Detection
**Load when**: chart pattern, overlay, pattern detection, candlestick, visualization, FullChart
**Feature**: Display detected chart patterns as overlays on candlestick charts

**Related**:
- [frontend-invariants.md](./frontend-invariants.md)
- [api-invariants.md](./api-invariants.md)
- [data-invariants.md](./data-invariants.md)
- [Specification](.claude/specs/shared/chart_pattern_data.md)

---

## Critical Path

```
Pattern Detection → API Response → Frontend Render → User Sees Overlay
     (Backend)         (JSON)        (Recharts)       (Visual)
```

Every pattern overlay operation must preserve this invariant: **Patterns align with price data, coordinate points enable line drawing.**

---

## Level 4: Configuration Invariants

### Backend Configuration
- [ ] `CHART_PATTERN_DATA` constant in `table_names.py`
- [ ] Pattern detection enabled in `PatternDetectionService`
- [ ] `ALLOWED_PATTERN_TYPES` includes all supported patterns
- [ ] `ALLOWED_IMPLEMENTATIONS` includes active detectors

### Frontend Configuration
- [ ] `ChartPattern` type defined in `types/report.ts`
- [ ] `chart_patterns` field in API types
- [ ] Pattern colors defined in `FullChart.tsx`

### Verification Commands
```bash
# Backend: Check table constant
grep "CHART_PATTERN_DATA" src/data/aurora/table_names.py

# Backend: Check allowed patterns
grep -A20 "ALLOWED_PATTERN_TYPES" src/data/aurora/chart_pattern_repository.py

# Frontend: Check type definition
grep -A10 "interface ChartPattern" frontend/twinbar/src/types/report.ts
```

---

## Level 3: Infrastructure Invariants

### Pattern Detection Pipeline
- [ ] `PatternDetectionService` can fetch OHLC data
- [ ] `ChartPatternDetector` produces coordinate points
- [ ] `CustomPatternAdapter` extracts points correctly
- [ ] Fallback to custom detector if stock-pattern unavailable

### Data Flow
- [ ] Lambda → Aurora: Pattern data persisted (or cached)
- [ ] API Gateway → Lambda: Report endpoint accessible
- [ ] CloudFront → Frontend: Static assets served

### Verification Commands
```bash
# Test pattern detection locally
python -c "
from src.services.pattern_detection_service import get_pattern_service
svc = get_pattern_service()
result = svc.detect_patterns('NVDA', days=180)
print(f'Patterns: {len(result.get(\"patterns\", []))}')
for p in result.get('patterns', [])[:2]:
    print(f'  {p[\"type\"]}: points={list(p.get(\"points\", {}).keys())}')
"

# Test API endpoint
curl -s "https://<api-gateway>/api/v1/report/NVDA19" | jq '.chart_patterns | length'
```

---

## Level 2: Data Invariants

### Coordinate Points Format (CRITICAL)
- [ ] Points are tuples: `{A: (date, price), B: (date, price), ...}`
- [ ] Date format: ISO string `"YYYY-MM-DD"` or bar index `"bar_N"`
- [ ] Price format: floating point number
- [ ] Points keys: `A`, `B`, `C`, `D`, `E` or pattern-specific names

**Valid Point Structure**:
```json
{
  "points": {
    "A": ["2026-01-01", 150.25],
    "B": ["2026-01-05", 155.50],
    "C": ["2026-01-10", 152.00]
  }
}
```

**Invalid Point Structures** (will not render):
```json
// Empty points
{"points": {}}

// Legacy metadata format (no coordinates)
{"points": {"resistance_level": 148.92, "support_level": 112.97}}

// Missing price
{"points": {"A": ["2026-01-01"]}}
```

### Pattern Data Fields
- [ ] `type`: Pattern type (bullish_flag, head_shoulders, etc.)
- [ ] `pattern`: Pattern code (flag_pennant, triangle, etc.)
- [ ] `confidence`: high | medium | low
- [ ] `start`: Start date/index
- [ ] `end`: End date/index
- [ ] `points`: Coordinate points dict (REQUIRED for overlay)

### Data Freshness
- [ ] Patterns regenerated when Aurora cache refreshed
- [ ] Stale cached data contains empty/legacy points
- [ ] Fresh data contains coordinate tuples

### Verification Commands
```bash
# Check API response for coordinate points
curl -s "https://<api>/api/v1/report/NVDA19" | \
  jq '.chart_patterns[] | {type, points_keys: (.points | keys)}'

# Verify points have tuple format
curl -s "https://<api>/api/v1/report/NVDA19" | \
  jq '.chart_patterns[0].points.A'
# Expected: ["2026-01-01", 150.25] (tuple with date and price)

# Check for stale cache (empty/legacy points)
curl -s "https://<api>/api/v1/report/NVDA19" | \
  jq '[.chart_patterns[] | select(.points | keys | length == 0)] | length'
# Expected: 0 (no patterns with empty points)
```

---

## Level 1: Service Invariants

### API Response Contract
- [ ] `chart_patterns` array in ReportResponse
- [ ] Each pattern has required fields (type, pattern, confidence, points)
- [ ] Response serializable to JSON
- [ ] NumPy types converted to primitives

### Pattern Detection Service
- [ ] `detect_patterns()` returns patterns with coordinate points
- [ ] Patterns limited to top N (no overwhelming data)
- [ ] Detection errors logged, don't crash API
- [ ] Empty patterns array returned on failure (not null)

### Frontend Rendering
- [ ] `FullChart` receives `chartPatterns` prop
- [ ] `patternOverlays` computed from patterns
- [ ] `ReferenceArea` components generated
- [ ] Colors determined by pattern type (bullish=green, bearish=red)

### Verification Commands
```bash
# Backend: Test detection returns coordinate points
python -c "
from src.services.pattern_detection_service import get_pattern_service
svc = get_pattern_service()
result = svc.detect_patterns('NVDA', days=180)
for p in result.get('patterns', []):
    points = p.get('points', {})
    if not points:
        print(f'❌ {p[\"type\"]}: EMPTY POINTS')
    elif not any(isinstance(v, (list, tuple)) and len(v) == 2 for v in points.values()):
        print(f'⚠️ {p[\"type\"]}: LEGACY FORMAT - {list(points.keys())}')
    else:
        print(f'✅ {p[\"type\"]}: {list(points.keys())}')
"

# Frontend: Check rendering logic exists
grep -A30 "patternOverlays" frontend/twinbar/src/components/FullChart.tsx | head -40
```

---

## Level 0: User Invariants

### Visual Display
- [ ] Pattern overlays visible on chart
- [ ] Overlays align with candlesticks at correct dates
- [ ] Bullish patterns: green tint
- [ ] Bearish patterns: red tint
- [ ] Neutral patterns: blue tint

### Interaction
- [ ] Pattern panel lists detected patterns
- [ ] Pattern names readable in panel
- [ ] Confidence level displayed
- [ ] Clicking pattern highlights on chart (future)

### Error States
- [ ] No patterns: Panel shows "No patterns detected"
- [ ] Detection error: Silent (no overlay, patterns array empty)
- [ ] Stale data: Patterns listed but overlays don't render (current bug)

### Verification Steps (Manual)
1. Open dev Telegram Mini App
2. Navigate to ticker with known patterns (NVDA19)
3. Click to view full chart
4. Verify pattern overlays visible as shaded regions
5. Verify colors match pattern type
6. Verify pattern panel lists patterns with confidence

### Verification Commands
```bash
# Take screenshot for visual verification (if Playwright available)
npx playwright test tests/e2e/test_pattern_overlay.ts

# Or manual verification:
# 1. Open https://d24cidhj2eghux.cloudfront.net/
# 2. Select NVDA19
# 3. View chart modal
# 4. Confirm overlays render
```

---

## Current State (2026-01-14)

### Delta: 0 violations ✅

All invariants satisfied. Pattern overlays render correctly.

| Level | Invariant | Status | Verified |
|-------|-----------|--------|----------|
| L4 | Migration 020 applied | ✅ | 2026-01-14 |
| L2 | Coordinate points in tuple format | ✅ | 2026-01-14 |
| L0 | Overlays visible on chart | ✅ | 2026-01-14 via Playwright |

### Resolution History
- Fixed migration FK type (BIGINT → INT to match ticker_master.id)
- Swapped detector priority (custom=10, stock-pattern=5) for coordinate tuples
- Deployed Lambda v165, cleared Aurora cache
- Verified 10 `recharts-reference-area` elements on VNM19

---

## Visual Validation Reference

**IMPORTANT**: See `.claude/skills/visual-ta-validation/` for visual reference.

Our pattern overlays render as **shaded rectangular regions** (bounding boxes), NOT:
- Trendlines connecting points
- Pattern shape outlines
- Line drawings between A, B, C points

```
┌─────────────────────────────────────────────────────────┐
│  What we render:                                        │
│                                                         │
│   ██    ┌─────────────────────────────┐                │
│  ████   │      Shaded Region          │   ██           │
│ ██████  │    (Pattern Overlay)        │  ████          │
│  ████   │                             │ ██████         │
│   ██    └─────────────────────────────┘  ████          │
│              ↑ ReferenceArea component                  │
└─────────────────────────────────────────────────────────┘
```

See `patterns.md` in the skill for visual reference of each pattern type.

---

## Invariant Summary Table

| Level | Invariant | Verification |
|-------|-----------|--------------|
| **L4** | `CHART_PATTERN_DATA` constant exists | grep table_names.py |
| **L4** | `ChartPattern` type defined | grep types/report.ts |
| **L3** | Pattern detection pipeline works | Run detect_patterns() |
| **L3** | API returns chart_patterns | curl /report/NVDA19 |
| **L2** | Points have coordinate format | jq '.chart_patterns[0].points.A' |
| **L2** | Points are tuples `[date, price]` | Verify array with 2 elements |
| **L2** | No empty points objects | Count patterns with empty points |
| **L1** | Detection errors don't crash API | Test with invalid ticker |
| **L1** | Frontend computes overlays | Check patternOverlays useMemo |
| **L0** | Overlays visible on chart | Visual inspection |
| **L0** | Colors match pattern type | Bullish=green, bearish=red |
| **L0** | Pattern panel shows list | Visual inspection |

---

## Claiming "Chart Pattern Overlay Done"

```markdown
✅ Chart Pattern Overlay complete

**Invariants Verified**:
- [x] Level 4: Constants defined, types exist, migration applied
- [x] Level 3: Pipeline works, API returns patterns
- [x] Level 2: Coordinate points in tuple format, fresh data
- [x] Level 1: Detection stable, frontend computes overlays
- [x] Level 0: Overlays visible, colors correct, panel works

**Confidence**: HIGH
**Evidence**:
- API response: chart_patterns[0].points.A = ["2026-01-05", 155.50]
- Screenshot: overlays visible on NVDA19 chart
- Console: No React errors during render
```

---

## Related Resources

| Resource | Purpose |
|----------|---------|
| `.claude/specs/shared/chart_pattern_data.md` | Feature specification |
| `.claude/skills/visual-ta-validation/` | Visual validation skill |
| `.claude/skills/visual-ta-validation/patterns.md` | Pattern visual reference |
| `.claude/skills/visual-ta-validation/validation-checklist.md` | Validation procedure |
| `frontend/twinbar/src/components/FullChart.tsx` | Pattern overlay rendering |
| `src/services/pattern_detection_service.py` | Backend pattern detection |

---

*Domain: chart-pattern-overlay*
*Last updated: 2026-01-14*
*Status: Delta = 0 ✅*
*Related commands: /reconcile, /validate, /visual-ta-validation*
