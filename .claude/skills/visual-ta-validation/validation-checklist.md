# Chart Pattern Visual Validation Checklist

**Purpose**: Step-by-step procedure for validating chart pattern overlays.

**When to use**:
- After taking a screenshot of the chart
- Before marking L0 (User) invariant as satisfied
- When debugging "patterns don't render" issues

---

## Pre-Validation: Data Check (L2)

Before visual validation, verify data is correct:

```bash
# 1. Check API returns patterns with coordinate points
curl -s "https://ou0ivives1.execute-api.ap-southeast-1.amazonaws.com/api/v1/report/<SYMBOL>" | \
  jq '.chart_patterns | length'
# Expected: > 0

# 2. Verify points are in tuple format
curl -s "https://ou0ivives1.execute-api.ap-southeast-1.amazonaws.com/api/v1/report/<SYMBOL>" | \
  jq '.chart_patterns[0].points'
# Expected: {"A": ["bar_N", price], "B": ["bar_M", price], ...}

# 3. Check for empty points (stale cache indicator)
curl -s "https://ou0ivives1.execute-api.ap-southeast-1.amazonaws.com/api/v1/report/<SYMBOL>" | \
  jq '[.chart_patterns[] | select(.points | keys | length == 0)] | length'
# Expected: 0 (no patterns with empty points)
```

**If data check fails**: Stop - fix L2 before visual validation.

---

## Visual Validation Checklist

### Step 1: Identify Pattern Overlay Elements

Look for shaded rectangular regions on the candlestick chart.

**Check**:
- [ ] At least one colored shaded region visible
- [ ] Region is semi-transparent (can see candlesticks through it)
- [ ] Region has dashed border

**If NOT visible**: Check browser console for errors, verify `chartPatterns` prop passed to FullChart.

---

### Step 2: Verify Color Coding

| Pattern Sentiment | Expected Color | RGB Check |
|-------------------|----------------|-----------|
| Bullish | Green | `rgba(34, 197, 94, ...)` |
| Bearish | Red | `rgba(239, 68, 68, ...)` |
| Neutral | Blue | `rgba(59, 130, 246, ...)` |

**Check**:
- [ ] Bullish patterns (bullish_flag, double_bottom, etc.) = Green
- [ ] Bearish patterns (bearish_flag, double_top, head_shoulders) = Red
- [ ] Neutral patterns (symmetrical_triangle) = Blue

---

### Step 3: Verify Position Alignment

The shaded region should align with the pattern's time period.

**Check**:
- [ ] Left edge of region aligns with pattern start date
- [ ] Right edge of region aligns with pattern end date
- [ ] Region covers candlesticks within that date range
- [ ] Region height spans from lowest low to highest high in that period

**Common misalignments**:
- Region shifted left/right = Bar index parsing issue
- Region too tall/short = Y-axis domain calculation issue
- Region not visible = Start/end indices out of bounds

---

### Step 4: Verify Pattern Label

Each region should have an abbreviation label.

**Check**:
- [ ] Label visible in top-right corner of region
- [ ] Label matches pattern type (e.g., "BF" for Bullish Flag)
- [ ] Label color matches stroke color

---

### Step 5: Verify Legend Display

Check the indicator/pattern legend above the chart.

**Check**:
- [ ] "Patterns:" section visible in legend
- [ ] Pattern type names shown with color swatches
- [ ] If >3 patterns, shows "+N more" indicator

---

### Step 6: Verify Panel Display

Check the ChartPatternsPanel component.

**Check**:
- [ ] Panel lists all detected patterns
- [ ] Each pattern shows: type, confidence, date range
- [ ] Bullish patterns have up arrow indicator
- [ ] Bearish patterns have down arrow indicator
- [ ] Confidence badge colored appropriately

---

## Playwright Verification (Automated)

Use Playwright to verify DOM elements:

```typescript
// Count pattern overlay elements
const overlayCount = await page.locator('.recharts-reference-area').count();
expect(overlayCount).toBeGreaterThan(0);

// Verify pattern panel exists
const patternPanel = await page.locator('[data-testid="chart-patterns-panel"]');
await expect(patternPanel).toBeVisible();

// Check pattern items in panel
const patternItems = await page.locator('[data-testid="pattern-item"]').count();
expect(patternItems).toBeGreaterThan(0);
```

---

## Verification Evidence Template

After validation, document evidence:

```markdown
## L0 Verification Evidence

**Date**: YYYY-MM-DD
**Symbol**: <SYMBOL>
**Environment**: dev / stg / prd

### Screenshot
![Pattern Overlay Screenshot](path/to/screenshot.png)

### Overlay Count
- Playwright detected: N `recharts-reference-area` elements

### Visual Checks
- [x] Shaded regions visible
- [x] Colors match sentiment (green=bullish, red=bearish)
- [x] Regions align with pattern dates
- [x] Labels visible on regions
- [x] Legend shows pattern types
- [x] Panel lists patterns with confidence

### Pattern Details (from screenshot)
| Pattern | Color | Position | Confidence |
|---------|-------|----------|------------|
| Bullish Flag | Green | Bar 13-18 | Low |
| Double Bottom | Green | Bar 5-25 | Medium |

### Conclusion
- [ ] L0 PASS: Overlays render correctly
- [ ] L0 FAIL: Issue with ___________
```

---

## Common Issues and Fixes

### Issue: No shaded regions visible

**Symptoms**: Chart shows candlesticks and SMAs but no pattern overlays

**Debug steps**:
1. Check console for React errors
2. Verify `chartPatterns` prop is not empty array
3. Check if `patternOverlays` useMemo returns non-empty array
4. Verify bar indices are within data bounds

**Common causes**:
- Empty `points` object in API response (stale cache)
- Start/end indices exceed data length
- `parseBarIndex()` returning null

---

### Issue: Regions appear but wrong position

**Symptoms**: Shaded regions visible but don't align with candlesticks

**Debug steps**:
1. Check `pattern.start` and `pattern.end` format
2. Verify `parseBarIndex()` extracts correct number
3. Check X-axis uses same date format as pattern data

**Common causes**:
- Date format mismatch (ISO string vs bar index)
- Off-by-one error in data slice

---

### Issue: Wrong colors

**Symptoms**: Patterns have unexpected colors

**Debug steps**:
1. Check pattern `type` field spelling
2. Verify pattern type in bullish/bearish arrays in `getPatternColor()`

**Common causes**:
- Pattern type not in recognition arrays
- Underscore vs space in pattern type name

---

### Issue: Patterns in panel but no overlay

**Symptoms**: ChartPatternsPanel shows patterns, chart has no overlays

**Debug steps**:
1. Check if `points` object has coordinate tuples
2. Verify `startIdx` and `endIdx` are not null
3. Check if indices are within `data.length`

**Common causes**:
- Legacy point format (metadata instead of coordinates)
- Points have wrong structure

---

## Quick Validation Commands

```bash
# Full validation flow
npm run dev  # Start frontend locally

# Open browser to mini app
# Navigate to ticker with patterns
# Take screenshot manually or via Playwright

# Verify programmatically
npx playwright test tests/e2e/pattern-overlay.spec.ts
```

---

*Checklist for visual-ta-validation skill*
*Last updated: 2026-01-14*
