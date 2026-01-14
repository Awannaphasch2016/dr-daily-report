# Visual Technical Analysis Validation Skill

**Purpose**: Help Claude validate that chart patterns are rendered correctly on candlestick charts.

**When to use**:
- After implementing or modifying pattern overlay rendering
- Before claiming L0 (User) invariant is satisfied
- When visual verification screenshots are taken
- When debugging pattern display issues

**Key files**:
- `patterns.md` - Visual reference for each chart pattern type
- `validation-checklist.md` - Step-by-step validation procedure

---

## Quick Reference

### What Pattern Overlays Should Look Like

Pattern overlays in this project are rendered as **shaded rectangular regions** on the chart using Recharts `ReferenceArea` components.

```
┌─────────────────────────────────────────────────────────┐
│  Chart                                                  │
│                                                         │
│   ██    ┌─────────────────────────────┐                │
│  ████   │      Shaded Region          │   ██           │
│ ██████  │    (Pattern Overlay)        │  ████          │
│  ████   │                             │ ██████         │
│   ██    └─────────────────────────────┘  ████          │
│                                           ██           │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

**What to look for**:
1. **Rectangular shaded area** spanning from pattern start date to end date
2. **Vertical extent** covering the price range (low to high) of the pattern period
3. **Color coding**: Green = bullish, Red = bearish, Blue = neutral
4. **Dashed border** around the shaded area
5. **Pattern abbreviation label** in top-right corner of area

---

## What Pattern Overlays Are NOT

Our implementation does NOT draw:
- Trendlines connecting pattern points
- Diagonal lines showing support/resistance
- The actual geometric shape of the pattern (e.g., flag outline, head-shoulders silhouette)

This is by design - our overlay style uses **bounding box shading** rather than **line drawing**.

---

## Validation Workflow

```bash
# 1. Take screenshot
npx playwright test tests/e2e/test_pattern_overlay.ts

# 2. Check screenshot using this skill's checklist
# See validation-checklist.md

# 3. Verify against expected visual
# See patterns.md for each pattern type
```

---

## Related Files

| File | Purpose |
|------|---------|
| `frontend/twinbar/src/components/FullChart.tsx` | Pattern overlay rendering |
| `frontend/twinbar/src/components/ChartPatternsPanel.tsx` | Pattern list display |
| `.claude/specs/shared/chart_pattern_data.md` | Feature specification |
| `.claude/invariants/chart-pattern-overlay-invariants.md` | Invariant checklist |

---

## Common Validation Failures

| Symptom | Cause | Fix |
|---------|-------|-----|
| No shaded regions | Empty/legacy points format | Refresh Aurora cache |
| Patterns listed but no overlay | Points missing coordinate tuples | Check API response format |
| Wrong color | Pattern type not in bullish/bearish list | Update `getPatternColor()` |
| Overlay misaligned | Bar index parsing failed | Check `parseBarIndex()` |
| No patterns shown | Pattern detection failed | Check backend service |

---

*Skill created: 2026-01-14*
*Domain: chart-pattern-overlay*
