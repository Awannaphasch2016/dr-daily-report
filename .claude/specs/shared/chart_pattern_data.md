# Specification: Chart Pattern Data Storage & Display

**Status**: Complete ✅
**Created**: 2026-01-14
**Updated**: 2026-01-14
**Completed**: 2026-01-14
**Table Name**: `chart_pattern_data`
**Delta**: 0 violations ✅

---

## Current State (Delta Tracking)

| Level | Invariant | Status | Fix Required |
|-------|-----------|--------|--------------|
| L4 | Migration 020 applied | ✅ | - |
| L2 | Coordinate points in tuple format | ✅ | - |
| L0 | Overlays visible on chart | ✅ | - |

**Delta**: 0 violations ✅
**Verified**: 2026-01-14 via Playwright (10 recharts-reference-area elements on VNM19)

---

## Invariant Envelope

| Level | Invariant | Verification | Status |
|-------|-----------|--------------|--------|
| L0 (User) | User sees pattern overlays on chart | Visual: shaded regions on candlesticks | ✅ Verified |
| L1 (Service) | API returns chart_patterns with coordinate points | `jq '.chart_patterns[0].points.A'` returns tuple | ✅ Verified |
| L2 (Data) | Points have format `{A: [date, price], B: [date, price]}` | Response points are arrays with 2 elements | ✅ Verified |
| L3 (Infra) | Pattern detection pipeline produces coordinates | Run `detect_patterns()` locally | ✅ Works |
| L4 (Config) | Table, constants, types defined | grep table_names.py, types/report.ts | ✅ Defined |

---

## Schema Design

### Table: `chart_pattern_data`

```sql
CREATE TABLE IF NOT EXISTS chart_pattern_data (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,

    -- Ticker reference (matches existing pattern)
    ticker_id BIGINT NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    pattern_date DATE NOT NULL COMMENT 'Date pattern was detected (analysis date)',

    -- Pattern identification
    pattern_type VARCHAR(50) NOT NULL COMMENT 'Pattern category: bullish_flag, head_shoulders, wedge, etc.',
    pattern_code VARCHAR(20) NOT NULL COMMENT 'Short code: FLAGU, FLAGD, HS, IHS, WDGU, WDGD, etc.',

    -- Implementation provenance (CRITICAL for debugging)
    implementation VARCHAR(50) NOT NULL COMMENT 'Which detector: stock_pattern, custom, talib',
    impl_version VARCHAR(20) NOT NULL COMMENT 'Version of implementation: 1.0.0, 2.1.3',

    -- Detection metadata
    confidence ENUM('high', 'medium', 'low') NOT NULL DEFAULT 'medium',
    start_date DATE COMMENT 'Pattern start date in price data',
    end_date DATE COMMENT 'Pattern end date in price data',

    -- Pattern data (flexible JSON for varying pattern structures)
    pattern_data JSON NOT NULL COMMENT 'Pattern-specific data: points, prices, measurements',

    -- Timestamps
    detected_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'When detection ran',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    -- Constraints
    UNIQUE KEY uk_symbol_date_pattern_impl (symbol, pattern_date, pattern_type, implementation),
    FOREIGN KEY (ticker_id) REFERENCES ticker_master(id),

    -- Indexes for common queries
    INDEX idx_pattern_symbol (symbol),
    INDEX idx_pattern_date (pattern_date DESC),
    INDEX idx_pattern_type (pattern_type),
    INDEX idx_pattern_impl (implementation)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

### Pattern Data JSON Structure (Storage)

```json
{
  "points": {
    "A": {"date": "2026-01-01", "price": 150.25},
    "B": {"date": "2026-01-05", "price": 155.50},
    "C": {"date": "2026-01-10", "price": 152.00}
  },
  "measurements": {
    "pole_height": 10.5,
    "flag_depth": 3.5,
    "breakout_target": 165.75
  },
  "raw_output": {}
}
```

---

## Coordinate Points Contract (CRITICAL for Frontend)

The frontend **requires** coordinate points in tuple format to draw overlay lines. This is the most common failure point.

### Required API Response Format

```json
{
  "chart_patterns": [
    {
      "type": "bullish_flag",
      "pattern": "flag_pennant",
      "confidence": "high",
      "start": "2026-01-01",
      "end": "2026-01-10",
      "points": {
        "A": ["2026-01-01", 150.25],
        "B": ["2026-01-05", 155.50],
        "C": ["2026-01-10", 152.00]
      }
    }
  ]
}
```

### Point Tuple Structure

| Index | Type | Description | Example |
|-------|------|-------------|---------|
| 0 | string | ISO date or bar index | `"2026-01-01"` or `"bar_10"` |
| 1 | number | Price value | `150.25` |

### Valid vs Invalid Points

**✅ Valid (renders overlay)**:
```json
{"A": ["2026-01-01", 150.25], "B": ["2026-01-05", 155.50]}
```

**❌ Invalid - Empty (no overlay)**:
```json
{"points": {}}
```

**❌ Invalid - Legacy metadata (no overlay)**:
```json
{"points": {"resistance_level": 148.92, "support_level": 112.97}}
```

**❌ Invalid - Object format (no overlay)**:
```json
{"points": {"A": {"date": "2026-01-01", "price": 150.25}}}
```

### Verification Command

```bash
# Check points are tuples with 2 elements
curl -s "https://<api>/api/v1/report/NVDA19" | \
  jq '.chart_patterns[0].points | to_entries[] | select(.value | length != 2)'
# Expected: empty output (all points have 2 elements)
```

---

## Implementation Checklist

- [x] Specification created
- [x] Migration file: `db/migrations/020_create_chart_pattern_data.sql`
- [x] Table constant: `CHART_PATTERN_DATA` in `table_names.py`
- [x] Repository class: `ChartPatternDataRepository` in `src/data/aurora/chart_pattern_repository.py`
- [x] Boundary tests: `tests/data/test_chart_pattern_repository.py` (21 tests)
- [ ] Integration: Connect to `PatternDetectionService` (future task)

---

## Principle Compliance

| Principle | Status | Notes |
|-----------|--------|-------|
| #1 Defensive Programming | ✅ | ALLOWED_PATTERN_TYPES + ALLOWED_IMPLEMENTATIONS validation |
| #3 Aurora-First | ✅ | Data persists to Aurora |
| #4 Type System | ✅ | `_convert_numpy_to_primitives()` at boundary |
| #5 Database Migrations | ✅ | Idempotent with IF NOT EXISTS |
| #14 Table Names | ✅ | Centralized in `table_names.py` |
| #16 Timezone | ✅ | DATE for pattern dates, TIMESTAMP for system |
| #19 Boundary Tests | ✅ | 21 tests covering validation, type conversion, CRUD |

---

## Allowed Values

### Pattern Types
- `bullish_flag`, `bearish_flag`
- `head_shoulders`, `inverse_head_shoulders`
- `ascending_wedge`, `descending_wedge`
- `double_top`, `double_bottom`
- `ascending_triangle`, `descending_triangle`, `symmetrical_triangle`
- `cup_handle`
- `vcp` (Volatility Contraction Pattern)

### Implementations
- `stock_pattern` - External stock-pattern library
- `custom` - Our ChartPatternDetector
- `talib` - TA-Lib (future)
- `ml_detector` - ML-based detector (future)

### Confidence Levels
- `high` - Strong pattern with clear structure
- `medium` - Pattern detected with some ambiguity
- `low` - Weak or forming pattern

---

## Migration Sequence

```
020_create_chart_pattern_data.sql
├── CREATE TABLE chart_pattern_data
├── FOREIGN KEY to ticker_master
└── Indexes for common queries
```

---

## Verification Commands

```bash
# Check table exists
just dr-dev "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = 'chart_pattern_data'"

# Verify schema
just dr-dev "DESCRIBE chart_pattern_data"

# Test insert (dry run)
just dr-dev "EXPLAIN INSERT INTO chart_pattern_data (ticker_id, symbol, pattern_date, pattern_type, pattern_code, implementation, impl_version, confidence, pattern_data) VALUES (1, 'AAPL', '2026-01-14', 'bullish_flag', 'FLAGU', 'custom', '1.0.0', 'high', '{}')"
```

---

## Resolution Path (Convergence to Delta = 0)

### Step 1: Apply Migration to Dev (L4 Fix)

```bash
just dr-migrate --env dev
```

**Verify**:
```bash
just dr-dev "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = 'chart_pattern_data'"
# Expected: 1
```

### Step 2: Refresh Aurora Cache (L2 Fix)

The stale cache contains patterns with empty/legacy points. Force regeneration:

```bash
# Option A: Re-run precompute for test tickers
just dr-precompute-ticker NVDA19 --env dev

# Option B: Clear cached report to force regeneration
just dr-dev "DELETE FROM precomputed_reports WHERE symbol = 'NVDA19'"
# Then hit the API to regenerate
```

**Verify**:
```bash
curl -s "https://ou0ivives1.execute-api.ap-southeast-1.amazonaws.com/api/v1/report/NVDA19" | \
  jq '.chart_patterns[0].points | keys'
# Expected: ["A", "B", "C", ...] (not empty, not legacy keys)

curl -s "https://ou0ivives1.execute-api.ap-southeast-1.amazonaws.com/api/v1/report/NVDA19" | \
  jq '.chart_patterns[0].points.A'
# Expected: ["2026-01-05", 155.50] (tuple format)
```

### Step 3: Visual Verification (L0 Fix)

1. Open dev miniapp: `https://d24cidhj2eghux.cloudfront.net/`
2. Select ticker with patterns (NVDA19)
3. Open chart modal
4. Verify shaded overlay regions appear on chart
5. Verify colors match pattern type (green=bullish, red=bearish)

**Verify**:
```bash
# Optional: Screenshot test if Playwright available
npx playwright test tests/e2e/test_pattern_overlay.ts
```

### Step 4: Update Delta Tracking

After all steps complete, update this specification:

```markdown
## Current State (Delta Tracking)

| Level | Invariant | Status | Fix Required |
|-------|-----------|--------|--------------|
| L4 | Migration 020 applied | ✅ | - |
| L2 | Coordinate points in tuple format | ✅ | - |
| L0 | Overlays visible on chart | ✅ | - |

**Delta**: 0 violations
```

---

## Convergence History

| Date | Action | Delta Before | Delta After |
|------|--------|--------------|-------------|
| 2026-01-14 | Initial specification created | - | 3 |
| 2026-01-14 | Added coordinate points contract | 3 | 3 |
| 2026-01-14 | Applied migration 020 (L4 fix) | 3 | 2 |
| 2026-01-14 | Swapped detector priority, deployed v165 (L2 fix) | 2 | 1 |
| 2026-01-14 | Playwright verification: 10 overlay elements on VNM19 (L0 fix) | 1 | 0 |

---

## Related Files

| File | Purpose |
|------|---------|
| `db/migrations/020_create_chart_pattern_data.sql` | Table schema |
| `src/data/aurora/chart_pattern_repository.py` | Data access layer |
| `src/analysis/pattern_detectors/chart_patterns.py` | Coordinate point generation |
| `src/analysis/pattern_detectors/custom_adapter.py` | Point extraction adapter |
| `frontend/twinbar/src/components/FullChart.tsx` | Overlay rendering |
| `.claude/invariants/chart-pattern-overlay-invariants.md` | Full invariant checklist |
| `.claude/validations/2026-01-14-chart-pattern-display-readiness.md` | Validation report |
