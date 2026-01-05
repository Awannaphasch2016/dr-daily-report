---
title: Proper Chart Pattern Visualization Research
date: 2026-01-05
focus: accuracy
status: complete
---

# Research: How Flag/Pennant and Triangle Patterns Should Look

## Problem

**Current implementation**: Drawing flag/pennant patterns with:
- Horizontal dashed lines (high/low range)
- Triangle point markers at start/end
- This is INCORRECT visualization

**User feedback**: "aren't pattern suppose to look like flag pennant + triangle? do research on what they look like. I don't think you know what it suppose to look like."

**User is correct** - I implemented the visualization without researching proper technical analysis pattern drawing.

---

## Proper Pattern Visualization

### Flag Pattern

**What it actually looks like**:
- **Flagpole**: Sharp vertical price move (the pole)
- **Flag body**: Small rectangular consolidation that slopes AGAINST the trend
- **Two parallel trendlines**: Top and bottom of rectangle, slightly tilted

**From StockCharts.com**:
> "Flags look like rectangles that tilt against the prevailing trend, marked by price moves that are roughly parallel as highlighted by top and bottom trendlines forming a channel."

**Key characteristics**:
- Rectangular shape (NOT horizontal lines)
- Slopes against trend direction
- Two PARALLEL trendlines connecting highs and lows
- Duration: 1-4 weeks typically

**Visual structure**:
```
Bullish Flag (slopes downward against uptrend):

     /|
    / |  ← Flagpole (sharp up move)
   /  |
  /   |
 /   /← Flag body (tilted rectangle)
    /   ← Two parallel lines sloping DOWN
```

### Pennant Pattern

**What it actually looks like**:
- **Flagpole**: Sharp vertical price move (same as flag)
- **Pennant body**: Small SYMMETRICAL TRIANGLE that narrows
- **Two converging trendlines**: Price ranges get tighter toward apex

**From StockCharts.com**:
> "A pennant looks like a small symmetrical triangle, with price ranges becoming more and more narrow toward the end of the formation."

**Key characteristics**:
- Triangular shape (NOT rectangle)
- Converges to a point (narrows)
- Two trendlines that MEET at apex
- Symmetrical (both lines converge equally)

**Visual structure**:
```
Bullish Pennant (symmetrical triangle after uptrend):

     /|
    / |  ← Flagpole
   /  |
  /   |\
 /    | \ ← Pennant (converging triangle)
      |  \
       ---  ← Apex (narrow point)
```

### Triangle Patterns

**Three types**, each with distinct trendline structure:

#### 1. Ascending Triangle (Bullish)
- **Top trendline**: FLAT (horizontal resistance)
- **Bottom trendline**: RISING (higher lows)
- **Converges upward**

```
Ascending Triangle:
      ----------  ← Flat resistance
     /
    /  ← Rising support
   /
  /
```

#### 2. Descending Triangle (Bearish)
- **Top trendline**: FALLING (lower highs)
- **Bottom trendline**: FLAT (horizontal support)
- **Converges downward**

```
Descending Triangle:
  \
   \  ← Falling resistance
    \
     \
      ----------  ← Flat support
```

#### 3. Symmetrical Triangle (Neutral)
- **Top trendline**: FALLING (lower highs)
- **Bottom trendline**: RISING (higher lows)
- **Converges to apex**

```
Symmetrical Triangle:
    \
     \  ← Falling resistance
      \
      /\ ← Apex
     /  \
    /    ← Rising support
```

---

## What I Drew (INCORRECT)

**Flag/Pennant visualization I implemented**:
```javascript
// Draw consolidation range box (top and bottom lines)
datasets.push({
    type: 'line',
    label: 'Flag High',
    data: [
        { x: startDate, y: highPrice },
        { x: endDate, y: highPrice }
    ],
    borderDash: [8, 4],  // Dashed horizontal line
    // ...
});

datasets.push({
    type: 'line',
    label: 'Flag Low',
    data: [
        { x: startDate, y: lowPrice },
        { x: endDate, y: lowPrice }
    ],
    borderDash: [8, 4],  // Dashed horizontal line
    // ...
});

// Triangle markers at start/end
datasets.push({
    type: 'line',
    data: [
        { x: startDate, y: avgPrice },
        { x: endDate, y: avgPrice }
    ],
    pointStyle: 'triangle',  // Triangle markers
    // ...
});
```

**Problems**:
1. ❌ Horizontal lines (should be SLOPED for flags)
2. ❌ Doesn't show consolidation trendlines
3. ❌ Triangle markers irrelevant (confused with triangle pattern)
4. ❌ Doesn't show flagpole
5. ❌ Can't distinguish flag from pennant

---

## What I SHOULD Draw

### For Flag Patterns

**Need**:
1. **Flagpole line**: Vertical line from trend start to flag beginning
2. **Top trendline**: Connect highs during consolidation (sloped)
3. **Bottom trendline**: Connect lows during consolidation (sloped)
4. **Parallel lines**: Top and bottom should be roughly parallel

**Implementation approach**:
```javascript
if (pattern.pattern === 'flag_pennant') {
    // Determine if it's a flag or pennant by analyzing shape
    // For now, treat as flag (rectangular)

    const rangeData = data.ohlc.filter(d => d.x >= startDate && d.x <= endDate);

    // Extract highs and lows for trendline fitting
    const highs = rangeData.map((d, i) => ({ x: i, y: d.h }));
    const lows = rangeData.map((d, i) => ({ x: i, y: d.l }));

    // Fit linear trendlines to highs and lows
    const topTrendline = fitLinearTrendline(highs, rangeData);
    const bottomTrendline = fitLinearTrendline(lows, rangeData);

    // Draw top trendline (resistance during consolidation)
    datasets.push({
        type: 'line',
        label: 'Flag Resistance',
        data: topTrendline,
        borderColor: color,
        borderWidth: 2,
        borderDash: [5, 5],
        pointRadius: 0
    });

    // Draw bottom trendline (support during consolidation)
    datasets.push({
        type: 'line',
        label: 'Flag Support',
        data: bottomTrendline,
        borderColor: color,
        borderWidth: 2,
        borderDash: [5, 5],
        pointRadius: 0
    });
}
```

### For Triangle Patterns

**Need**:
1. **Top trendline**: Connect descending highs
2. **Bottom trendline**: Connect ascending lows
3. **Converging**: Lines should meet at apex
4. **Type-specific**:
   - Ascending: Flat top, rising bottom
   - Descending: Falling top, flat bottom
   - Symmetrical: Both converging

**Implementation approach**:
```javascript
if (pattern.pattern === 'triangle') {
    const rangeData = data.ohlc.filter(d => d.x >= startDate && d.x <= endDate);

    // Identify highs and lows
    const highs = rangeData.map((d, i) => ({ x: i, y: d.h }));
    const lows = rangeData.map((d, i) => ({ x: i, y: d.l }));

    // Fit trendlines
    const resistanceLine = fitLinearTrendline(highs, rangeData);
    const supportLine = fitLinearTrendline(lows, rangeData);

    // Draw converging trendlines
    datasets.push({
        type: 'line',
        label: 'Triangle Resistance',
        data: resistanceLine,
        borderColor: '#FF6B6B',
        borderWidth: 2,
        pointRadius: 0
    });

    datasets.push({
        type: 'line',
        label: 'Triangle Support',
        data: supportLine,
        borderColor: '#4ECDC4',
        borderWidth: 2,
        pointRadius: 0
    });
}
```

---

## Key Insight: Trendline Fitting Required

**Critical realization**: Proper pattern visualization requires **LINEAR REGRESSION** to fit trendlines through price points.

**Algorithm**:
```javascript
function fitLinearTrendline(points, rangeData) {
    // Linear regression: y = mx + b
    const n = points.length;
    const sumX = points.reduce((sum, p) => sum + p.x, 0);
    const sumY = points.reduce((sum, p) => sum + p.y, 0);
    const sumXY = points.reduce((sum, p) => sum + p.x * p.y, 0);
    const sumX2 = points.reduce((sum, p) => sum + p.x * p.x, 0);

    const slope = (n * sumXY - sumX * sumY) / (n * sumX2 - sumX * sumX);
    const intercept = (sumY - slope * sumX) / n;

    // Generate line points
    return rangeData.map((d, i) => ({
        x: d.x,
        y: slope * i + intercept
    }));
}
```

---

## Comparison: Current vs Proper

### Current (WRONG)
```
Flag Pattern Rendering:
  ─────────────────  ← Horizontal dashed line (high)
  ▲               ▲  ← Triangle markers
  ─────────────────  ← Horizontal dashed line (low)
```

**Issues**:
- No slope (flags should tilt)
- No trendline fitting
- Triangle markers confusing
- Doesn't match technical analysis standards

### Proper (CORRECT)
```
Flag Pattern Rendering:
    ─────────────  ← Top trendline (sloped, connects highs)
   /            /
  /            /   ← Flag body (rectangular consolidation)
 /────────────    ← Bottom trendline (sloped, connects lows)
```

**Features**:
- Sloped parallel lines
- Fits actual highs/lows
- Matches technical analysis textbooks
- Recognizable as flag pattern

---

## Recommendations

### Immediate Fix (P0)

**Implement proper trendline fitting for flag/pennant patterns**:

1. Add `fitLinearTrendline()` helper function
2. Replace horizontal lines with fitted trendlines
3. Remove triangle point markers (irrelevant)
4. Use actual highs/lows for regression

**Estimated effort**: 30 minutes

**Risk**: Low (algorithmic change, no breaking changes)

---

### Future Enhancement (P1)

**Distinguish flags from pennants**:

Flags and pennants are currently grouped as `flag_pennant` pattern. Should differentiate:

- **Flag**: Parallel trendlines (rectangular)
- **Pennant**: Converging trendlines (triangular)

**Detection logic**:
```python
# In chart_patterns.py
def classify_flag_or_pennant(segment):
    top_slope = fit_trendline(highs)
    bottom_slope = fit_trendline(lows)

    if abs(top_slope - bottom_slope) < 0.01:
        return 'flag'  # Parallel
    else:
        return 'pennant'  # Converging
```

**Estimated effort**: 1 hour (backend + frontend changes)

---

### Triangle Pattern Support (P2)

**Add rendering for actual triangle patterns**:

Currently only flags/pennants and wedges render. Need:
- Ascending triangle visualization
- Descending triangle visualization
- Symmetrical triangle visualization

**Depends on**: Pattern detector implementing triangle detection (currently returns empty)

---

## Sources

### Flag and Pennant Patterns

- [StockCharts - Flag and Pennant Patterns](https://chartschool.stockcharts.com/table-of-contents/chart-analysis/chart-patterns/flag-pennant)
- [Britannica Money - Flag & Pennant Technical Analysis](https://www.britannica.com/money/flag-pennant-technical-analysis)
- [StocksToTrade - Pennant and Flag Chart Patterns Explained](https://stockstotrade.com/flags-and-pennants/)
- [Incredible Charts - Flag and Pennant Patterns](https://www.incrediblecharts.com/technical/flags_and_pennants.php)
- [Wikipedia - Flag and Pennant Patterns](https://en.wikipedia.org/wiki/Flag_and_pennant_patterns)

### Triangle Patterns

- [FXOpen - Triangle Chart Patterns](https://fxopen.com/blog/en/triangle-chart-patterns-how-to-identify-and-trade-them/)
- [Corporate Finance Institute - Triangle Patterns Technical Analysis](https://corporatefinanceinstitute.com/resources/career-map/sell-side/capital-markets/triangle-patterns/)
- [ChartMill - Triangle Chart Patterns](https://www.chartmill.com/documentation/technical-analysis/chart-patterns/401-Triangle-Chart-Patterns)
- [TradingView - Triangle Chart Pattern Education](https://www.tradingview.com/education/triangle/)
- [Wall Street Mojo - Triangle Chart Pattern Guide](https://www.wallstreetmojo.com/triangle-chart-pattern/)

---

## Conclusion

**User is absolutely correct** - my implementation does NOT match proper technical analysis pattern visualization.

**What I learned**:
1. Flags are TILTED rectangles (not horizontal boxes)
2. Pennants are CONVERGING triangles (not rectangles)
3. Both require LINEAR REGRESSION to fit trendlines
4. Triangle patterns have 3 types with distinct trendline configurations

**Next action**: Implement proper trendline fitting algorithm and replace current horizontal line approach.

**Priority**: P0 (current visualization is misleading/incorrect)
