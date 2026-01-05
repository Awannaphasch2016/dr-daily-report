---
title: Research - stock-pattern Library Learnings
date: 2026-01-05
focus: frontend
type: comparative_analysis
library: https://github.com/BennyThadikaran/stock-pattern
---

# stock-pattern Library Analysis

**Date**: 2026-01-05
**Library**: [BennyThadikaran/stock-pattern](https://github.com/BennyThadikaran/stock-pattern)
**Purpose**: Learn from their pattern detection algorithms to improve our implementation

---

## Executive Summary

Analyzed stock-pattern library's detection algorithms and compared with our JavaScript implementation in `standalone_chart_viewer.html`. Key finding: **Their approach is significantly more rigorous**, using multiple validation layers (technical indicators + geometric patterns) vs our purely geometric approach.

**Decision**: DO NOT integrate library (still server-side Python, violates our data-viz principles), but **adopt their validation techniques** in our JavaScript code.

---

## Library Overview

### What It Is
- **CLI scanner** for detecting chart patterns (not a library for programmatic use)
- **Python-based** with matplotlib visualization
- **Pattern detection** algorithms for flags, triangles, H&S, harmonics, etc.
- **Backtest capabilities** for validating pattern profitability

### Dependencies
```
matplotlib==3.10.3
mplfinance==0.12.10b0
pandas==2.2.2
numpy==2.2.6
```

### Architecture
```
src/
├── utils.py           # 104KB - All pattern detection algorithms
├── Plotter.py         # Visualization (matplotlib/mplfinance)
├── init.py            # CLI entry point
├── backtest.py        # Pattern backtesting
└── loaders/           # OHLC data loaders
```

---

## Pattern Detection Analysis

### 1. Bullish Flag Detection

**Their approach** (`utils.find_bullish_flag`):

```python
def find_bullish_flag(sym, df, pivots, config):
    # 1. Defensive check
    if len(df) < 50:
        return None

    # 2. Find recent high (last 7 days)
    recent_high_idx = df.High.iloc[-7:].idxmax()

    # 3. Validate new high exceeds 30-day and 90-day highs
    monthly_high = df.High.iloc[-30:].max()
    three_month_high = df.High.iloc[-90:].max()

    if recent_high >= monthly_high and recent_high >= three_month_high:
        # 4. Calculate moving averages
        sma20_ser = df.Close.rolling(20).mean()
        sma50_ser = df.Close.rolling(50).mean()

        # 5. Fibonacci 50% retracement
        fib_50 = last_pivot + (recent_high - last_pivot) / 2

        # 6. Validate consolidation
        # - SMA20 < SMA50 * 1.08 (trend not reversed)
        # - Recent low > Fib 50% (not too deep retracement)
        if sma20 < sma50 * 1.08 or recent_low < fib_50:
            return None

        # 7. Return pattern with points
        return dict(
            pattern="FLAGU",
            points=dict(
                A=(last_pivot_idx, last_pivot),
                B=(recent_high_idx, recent_high),
                C=(lastIdx, close),
            )
        )
```

**Our approach** (standalone_chart_viewer.html):

```javascript
function detectFlagPattern(data) {
    // 1. Find flagpole (strong trend)
    const flagpole = findStrongTrend(data);

    // 2. Find consolidation (parallel trendlines)
    const consolidation = findParallelLines(data);

    // 3. Return if structure matches
    if (flagpole && consolidation) {
        return { type: 'flag', points: [...] };
    }
    return null;
}
```

**Comparison**:

| Aspect | stock-pattern (Theirs) | Our Implementation | Winner |
|--------|------------------------|-------------------|--------|
| **Trend validation** | SMA20, SMA50 confirmation | Visual slope only | **Theirs** |
| **Depth validation** | Fibonacci 50% level | None | **Theirs** |
| **Timeframe validation** | 30-day, 90-day high check | None | **Theirs** |
| **Defensive checks** | len < 50 return None | Minimal | **Theirs** |
| **Configurable** | FLAG_MAX_BARS parameter | Hardcoded | **Theirs** |
| **Execution speed** | Slower (pandas operations) | Faster (native JS) | **Ours** |
| **Client-side** | ❌ Server-side Python | ✅ Client-side JS | **Ours** |

**Verdict**: Their **validation logic** is better, our **architecture** (client-side) is better.

---

### 2. Triangle Detection

**Their approach** (`utils.is_triangle`):

```python
def is_triangle(a, b, c, d, e, f, avgBarLength):
    """
    Uses avgBarLength as tolerance for "straight line" detection

    Parameters:
        a, b, c, d, e, f: Price levels at pivot points
        avgBarLength: Average(High - Low) as tolerance

    Returns: "Ascending" | "Descending" | "Symmetric" | None
    """
    # Check if A-C-E forms horizontal line (within tolerance)
    is_ac_straight_line = abs(a - c) <= avgBarLength
    is_ce_straight_line = abs(c - e) <= avgBarLength

    # Ascending triangle: flat resistance, rising support
    if is_ac_straight_line and is_ce_straight_line and b < d < f < e:
        return "Ascending"

    # Descending triangle: flat support, falling resistance
    is_bd_straight_line = abs(b - d) <= avgBarLength
    if is_bd_straight_line and a > c > e > f and f >= d:
        return "Descending"

    # Symmetric triangle: converging trendlines
    if a > c > e and b < d < f and e > f:
        return "Symmetric"

    return None
```

**Our approach** (standalone_chart_viewer.html):

```javascript
function detectTrianglePattern(data) {
    // 1. Fit resistance and support trendlines
    const resistance = fitTrendline(highs);
    const support = fitTrendline(lows);

    // 2. Check slopes
    if (Math.abs(resistance.slope) < 0.01) {
        return 'ascending';  // Flat resistance
    } else if (Math.abs(support.slope) < 0.01) {
        return 'descending'; // Flat support
    } else if (resistance.slope < 0 && support.slope > 0) {
        return 'symmetric';  // Converging
    }
    return null;
}
```

**Comparison**:

| Aspect | stock-pattern (Theirs) | Our Implementation | Winner |
|--------|------------------------|-------------------|--------|
| **Tolerance** | avgBarLength (adaptive) | Fixed 0.01 threshold | **Theirs** |
| **Validation** | Point relationships (a>c>e, b<d<f) | Slope comparison only | **Theirs** |
| **Documentation** | ASCII art showing pattern structure | Comments only | **Theirs** |
| **Adaptive** | Tolerance scales with volatility | Fixed threshold | **Theirs** |

**Key insight**: `avgBarLength` is brilliant - it makes tolerance **adaptive to market volatility**:
- High volatility stock: avgBarLength = $5 → tolerance = $5
- Low volatility stock: avgBarLength = $0.50 → tolerance = $0.50

**Our fixed threshold (0.01 slope)** doesn't adapt to different price scales or volatility.

---

## Data Structures

**Their approach** (Python with type hints):

```python
from typing import NamedTuple

class Point(NamedTuple):
    x: pd.Timestamp
    y: float

class Coordinate(NamedTuple):
    start: Point
    end: Point

class Line(NamedTuple):
    line: Coordinate
    slope: float
    y_int: float
```

**Benefits**:
- ✅ Type safety (Python type hints)
- ✅ Immutable (NamedTuples)
- ✅ Self-documenting (clear field names)
- ✅ Serializable with `make_serializable()` helper

**Our approach** (JavaScript):

```javascript
// Plain objects, no type safety
const point = { x: timestamp, y: price };
const line = { start: point1, end: point2, slope: m, intercept: b };
```

**Improvement opportunity**: Use TypeScript interfaces for type safety.

---

## Validation Criteria Comparison

### Flag Pattern Validation

| Criterion | Their Implementation | Our Implementation |
|-----------|---------------------|-------------------|
| Data length | `len >= 50` | No check |
| Trend strength | SMA20 < SMA50 * 1.08 | No check |
| Retracement depth | `recent_low > fib_50` (50% Fib) | No check |
| New high | Exceeds 30d, 90d high | No check |
| Consolidation bars | Configurable `FLAG_MAX_BARS` | Fixed |

**Their criteria**: 5 validation layers (defensive + technical + geometric)
**Our criteria**: 1 validation layer (geometric only)

### Triangle Pattern Validation

| Criterion | Their Implementation | Our Implementation |
|-----------|---------------------|-------------------|
| Straight line tolerance | `abs(a - c) <= avgBarLength` | `abs(slope) < 0.01` |
| Point relationships | `a > c > e and b < d < f` | Slope comparison |
| Adaptive tolerance | ✅ Yes (avgBarLength) | ❌ Fixed threshold |
| Volatility aware | ✅ Yes | ❌ No |

---

## Key Learnings

### 1. **Adaptive Tolerance Using avgBarLength**

**What it is**:
```python
# Calculate average bar range (High - Low)
avgBarLength = df['Range'].mean()
# where df['Range'] = df['High'] - df['Low']

# Use as tolerance for "straight line" detection
is_horizontal = abs(price1 - price2) <= avgBarLength
```

**Why it's better than fixed thresholds**:
- Adapts to stock price scale ($5 vs $500 stock)
- Adapts to volatility (stable vs volatile stock)
- Makes detection robust across different instruments

**How to implement in JavaScript**:
```javascript
function calculateAvgBarLength(data) {
    const ranges = data.map(d => d.high - d.low);
    return ranges.reduce((sum, r) => sum + r, 0) / ranges.length;
}

function isHorizontalLine(prices, avgBarLength) {
    // Check if price variation within tolerance
    const max = Math.max(...prices);
    const min = Math.min(...prices);
    return (max - min) <= avgBarLength;
}
```

---

### 2. **Multiple Validation Layers**

**Their approach** (flag pattern):
1. Defensive: `len(df) >= 50`
2. Geometric: Flagpole structure
3. Technical: SMA20 < SMA50 * 1.08
4. Fibonacci: Retracement > 50%
5. Timeframe: New high vs 30d/90d

**Our approach** (flag pattern):
1. Geometric: Flagpole + consolidation

**Improvement**: Add validation layers **without** requiring server-side (can calculate SMA, Fib in JavaScript).

---

### 3. **Fibonacci Retracements for Depth Validation**

**What it does**:
```python
# Calculate 50% retracement level
fib_50 = last_pivot + (recent_high - last_pivot) / 2

# Validate consolidation doesn't retrace too deep
if recent_low < fib_50:
    return None  # Retraced more than 50%, not valid flag
```

**Why it matters**:
- Flag patterns should consolidate **shallowly** (< 50% retracement)
- Deep retracements indicate trend reversal, not continuation

**How to implement in JavaScript**:
```javascript
function validateFlagDepth(flagpoleHigh, flagpoleLow, consolidationLow) {
    const fib50 = flagpoleLow + (flagpoleHigh - flagpoleLow) * 0.5;
    return consolidationLow > fib50;  // Should stay above 50%
}
```

---

### 4. **Moving Average Confirmation**

**What it does**:
```python
sma20 = df.Close.rolling(20).mean()
sma50 = df.Close.rolling(50).mean()

# Confirm trend hasn't reversed during consolidation
if sma20 < sma50 * 1.08:
    # SMA20 should be close to but below SMA50 during consolidation
    # If gap widens, trend might be reversing
    return pattern
```

**Why it matters**:
- Confirms uptrend still intact during consolidation
- 8% threshold allows minor pullback without invalidating pattern

**How to implement in JavaScript**:
```javascript
function calculateSMA(prices, period) {
    const sma = [];
    for (let i = period - 1; i < prices.length; i++) {
        const sum = prices.slice(i - period + 1, i + 1)
            .reduce((acc, p) => acc + p, 0);
        sma.push(sum / period);
    }
    return sma;
}

function validateTrendIntact(closes) {
    const sma20 = calculateSMA(closes, 20);
    const sma50 = calculateSMA(closes, 50);

    const currentSma20 = sma20[sma20.length - 1];
    const currentSma50 = sma50[sma50.length - 1];

    // Check if trend intact (SMA20 close to SMA50)
    return currentSma20 < currentSma50 * 1.08;
}
```

---

### 5. **Defensive Programming**

**Their checks**:
```python
# Check 1: Minimum data length
if len(df) < 50:
    return None

# Check 2: Recent high must be recent
if len(df.loc[recent_high_idx:]) < config.get("FLAG_MAX_BARS", 5):
    return None

# Check 3: Handle Series vs scalar
if isinstance(last_pivot, pd.Series):
    last_pivot = last_pivot.max()
```

**Our checks**:
```javascript
// Minimal checks
if (!data || data.length === 0) return null;
```

**Improvement**: Add comprehensive defensive checks:
```javascript
function detectPattern(data, config = {}) {
    // Check 1: Minimum data length
    if (!data || data.length < 50) {
        console.warn('Insufficient data for pattern detection (need 50+ bars)');
        return null;
    }

    // Check 2: Data quality
    const hasInvalidData = data.some(d =>
        d.high < d.low ||
        d.open < 0 ||
        isNaN(d.close)
    );
    if (hasInvalidData) {
        console.error('Invalid OHLC data detected');
        return null;
    }

    // Check 3: Configuration validation
    const flagMaxBars = config.FLAG_MAX_BARS || 5;
    if (flagMaxBars < 1 || flagMaxBars > 20) {
        console.warn('Invalid FLAG_MAX_BARS, using default: 5');
    }

    // ... pattern detection logic
}
```

---

## Proposed Improvements for Our Implementation

### Priority 1: High Impact, Easy Implementation

#### 1.1 Add avgBarLength Tolerance

**Implementation**:
```javascript
// In standalone_chart_viewer.html

function calculateAvgBarLength(ohlcData) {
    const ranges = ohlcData.map(d => d.high - d.low);
    return ranges.reduce((sum, r) => sum + r, 0) / ranges.length;
}

function detectTrianglePattern(ohlcData) {
    const avgBarLength = calculateAvgBarLength(ohlcData);

    // Use adaptive tolerance instead of fixed 0.01
    const resistancePrices = [high1, high2, high3];
    const isHorizontal = isWithinTolerance(resistancePrices, avgBarLength);

    // ...
}

function isWithinTolerance(prices, tolerance) {
    const max = Math.max(...prices);
    const min = Math.min(...prices);
    return (max - min) <= tolerance;
}
```

**Benefit**: Triangle detection adapts to volatility automatically.

---

#### 1.2 Add Fibonacci Retracement for Flag Depth

**Implementation**:
```javascript
function detectFlagPattern(ohlcData) {
    // Find flagpole
    const flagpoleHigh = Math.max(...flagpoleData.map(d => d.high));
    const flagpoleLow = flagpoleData[0].low;

    // Find consolidation
    const consolidationLow = Math.min(...consolidationData.map(d => d.low));

    // Validate depth (should stay above 50% retracement)
    const fib50 = flagpoleLow + (flagpoleHigh - flagpoleLow) * 0.5;

    if (consolidationLow < fib50) {
        return null;  // Too deep, not valid flag
    }

    // ... rest of pattern detection
}
```

**Benefit**: Filters out invalid flags that retrace too deeply.

---

#### 1.3 Add Defensive Data Validation

**Implementation**:
```javascript
function validateOHLCData(data) {
    if (!data || data.length < 50) {
        return { valid: false, error: 'Insufficient data (need 50+ bars)' };
    }

    for (let i = 0; i < data.length; i++) {
        const bar = data[i];

        // Check OHLC relationships
        if (bar.high < bar.low) {
            return { valid: false, error: `Invalid bar at index ${i}: high < low` };
        }

        // Check positive prices
        if (bar.open <= 0 || bar.high <= 0 || bar.low <= 0 || bar.close <= 0) {
            return { valid: false, error: `Invalid bar at index ${i}: non-positive price` };
        }

        // Check for NaN
        if (isNaN(bar.open) || isNaN(bar.high) || isNaN(bar.low) || isNaN(bar.close)) {
            return { valid: false, error: `Invalid bar at index ${i}: NaN value` };
        }
    }

    return { valid: true };
}

function detectAllPatterns(ohlcData) {
    const validation = validateOHLCData(ohlcData);
    if (!validation.valid) {
        console.error('Data validation failed:', validation.error);
        return [];
    }

    // ... pattern detection
}
```

**Benefit**: Fail fast with clear error messages instead of silent failures.

---

### Priority 2: Medium Impact, Moderate Implementation

#### 2.1 Add Moving Average Confirmation

**Implementation**:
```javascript
function calculateSMA(data, period) {
    const sma = [];
    const closes = data.map(d => d.close);

    for (let i = period - 1; i < closes.length; i++) {
        const sum = closes.slice(i - period + 1, i + 1)
            .reduce((acc, p) => acc + p, 0);
        sma.push({ x: data[i].x, y: sum / period });
    }

    return sma;
}

function validateFlagTrendIntact(ohlcData, consolidationStartIdx) {
    const sma20 = calculateSMA(ohlcData, 20);
    const sma50 = calculateSMA(ohlcData, 50);

    const currentSma20 = sma20[sma20.length - 1].y;
    const currentSma50 = sma50[sma50.length - 1].y;

    // During consolidation, SMA20 should be close to SMA50
    return currentSma20 < currentSma50 * 1.08;
}
```

**Benefit**: Confirms trend hasn't reversed during consolidation.

---

#### 2.2 Make Thresholds Configurable

**Implementation**:
```javascript
// Configuration object
const PATTERN_CONFIG = {
    FLAG_MAX_BARS: 5,           // Maximum consolidation bars
    FLAG_FIB_LEVEL: 0.5,        // Fibonacci retracement level
    FLAG_SMA_THRESHOLD: 1.08,   // SMA20/SMA50 ratio threshold
    TRIANGLE_MIN_TOUCHES: 4,    // Minimum trendline touches
    MIN_DATA_LENGTH: 50,        // Minimum bars for detection
};

function detectFlagPattern(ohlcData, config = PATTERN_CONFIG) {
    // Use configurable thresholds
    const flagMaxBars = config.FLAG_MAX_BARS;
    const fibLevel = config.FLAG_FIB_LEVEL;
    const smaThreshold = config.FLAG_SMA_THRESHOLD;

    // ... detection logic using config values
}
```

**Benefit**: Users can tune sensitivity based on their trading style.

---

### Priority 3: Low Impact, Complex Implementation

#### 3.1 TypeScript Interfaces for Type Safety

**Implementation** (if migrating to TypeScript):
```typescript
interface Point {
    x: number;  // Timestamp
    y: number;  // Price
}

interface Coordinate {
    start: Point;
    end: Point;
}

interface Line {
    line: Coordinate;
    slope: number;
    yIntercept: number;
}

interface PatternDetectionResult {
    type: 'flag' | 'triangle' | 'wedge' | 'head_shoulders' | 'double_top';
    points: Record<string, Point>;
    confidence: number;
    metadata: {
        avgBarLength: number;
        sma20: number;
        sma50: number;
    };
}
```

**Benefit**: Compile-time type safety, better IDE autocomplete.

---

## Implementation Roadmap

### Phase 1: Quick Wins (1-2 hours)
1. ✅ Add avgBarLength calculation
2. ✅ Add Fibonacci retracement validation for flags
3. ✅ Add defensive data validation

### Phase 2: Enhanced Validation (2-3 hours)
4. ✅ Add SMA calculation and trend confirmation
5. ✅ Make thresholds configurable
6. ✅ Add validation layers to each pattern type

### Phase 3: Refinement (Optional)
7. ⏸️ Migrate to TypeScript for type safety
8. ⏸️ Add confidence scoring (0-1 score instead of boolean)
9. ⏸️ Add backtesting capabilities

---

## Code Examples: Before & After

### Triangle Detection (Before)

```javascript
function detectTrianglePattern(ohlcData) {
    const resistance = fitTrendline(highs);
    const support = fitTrendline(lows);

    if (Math.abs(resistance.slope) < 0.01) {
        return 'ascending';
    }
    return null;
}
```

### Triangle Detection (After - with learnings)

```javascript
function detectTrianglePattern(ohlcData) {
    // Defensive check
    if (ohlcData.length < 50) {
        return null;
    }

    // Calculate adaptive tolerance
    const avgBarLength = calculateAvgBarLength(ohlcData);

    // Find pivot points
    const pivots = findPivotPoints(ohlcData);
    if (pivots.highs.length < 3 || pivots.lows.length < 3) {
        return null;
    }

    // Check if highs form horizontal line (within tolerance)
    const highPrices = pivots.highs.map(p => p.y);
    const isHorizontalResistance = isWithinTolerance(highPrices, avgBarLength);

    // Check if lows are rising
    const lowPrices = pivots.lows.map(p => p.y);
    const isRisingSupport = lowPrices[0] < lowPrices[1] && lowPrices[1] < lowPrices[2];

    // Ascending triangle: horizontal resistance + rising support
    if (isHorizontalResistance && isRisingSupport) {
        return {
            type: 'ascending_triangle',
            points: pivots,
            metadata: { avgBarLength, confidence: 0.85 }
        };
    }

    return null;
}
```

---

## Conclusion

### DO NOT Integrate Library Directly
- ❌ Server-side Python (violates client-side architecture)
- ❌ matplotlib rendering (incompatible with Chart.js)
- ❌ Violates data-visualization skill principles

### DO Adopt Their Techniques
- ✅ avgBarLength adaptive tolerance
- ✅ Fibonacci retracement validation
- ✅ Moving average confirmation
- ✅ Multiple validation layers
- ✅ Defensive programming patterns
- ✅ Configurable thresholds

### Impact
Implementing these improvements will make our pattern detection:
1. **More accurate** (fewer false positives)
2. **More robust** (handles different volatility levels)
3. **More reliable** (defensive checks prevent crashes)
4. **More flexible** (configurable thresholds)

---

**Next Steps**:
1. Implement Phase 1 improvements (avgBarLength, Fib, defensive checks)
2. Test with real data (DBP, DBS, AAPL)
3. Compare detection accuracy before/after
4. Iterate based on results

---

**Files to modify**:
- `standalone_chart_viewer.html` - Pattern detection functions
- Add configuration object for tunable parameters
- Add validation utilities (avgBarLength, SMA, Fib)

**Estimated effort**: 3-5 hours for Phase 1 + Phase 2 improvements
