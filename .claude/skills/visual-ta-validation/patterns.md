# Chart Pattern Visual Reference

**Purpose**: Visual reference for validating chart pattern overlays on candlestick charts.

**Rendering style**: Trendlines connecting pattern coordinate points

---

## How Patterns Render in Our System

Our system renders pattern overlays as **SVG lines connecting pattern coordinate points**. Each pattern type has specific points (A, B, C, D, E) that define the pattern shape.

```
Pattern Data:
{
  "type": "bullish_flag",
  "points": {
    "A": ["3", 57750.54],   // Upper left
    "B": ["11", 55351.95],  // Lower left
    "C": ["13", 56828.00],  // Upper right
    "D": ["16", 55444.21]   // Lower right
  }
}

Rendered As:
┌─────────────────────────────────────────────────────────┐
│  Price                                                  │
│    ▲                                                    │
│    │        A━━━━━━━━━━━━━━━━━━━━━C                    │
│    │         ╲                   ╱                      │
│ $55├          ╲  candlesticks  ╱                       │
│    │           ╲              ╱                         │
│    │            ╲            ╱                          │
│    │        B━━━━━━━━━━━━━━━D                          │
│    │                                                    │
│    └────────────────────────────────────────────────────▶
│                                                    Time │
└─────────────────────────────────────────────────────────┘
```

**Key visual elements**:
1. **Solid lines** connecting primary pattern boundaries
2. **Dashed lines** for secondary connections (optional)
3. **Color coding**: Green (bullish), Red (bearish), Blue (neutral)
4. **Lines overlay on top of candlesticks**

---

## Pattern Types and Trendline Mappings

### Flag Patterns (Bullish/Bearish)

**Points**: A (upper-left), B (lower-left), C (upper-right), D (lower-right)

**Lines drawn**:
- `A → C` (solid): Upper channel boundary
- `B → D` (solid): Lower channel boundary

```
Bullish Flag:
Price
  │        A━━━━━━━━━━━━C
  │   ██    ╲          ╱
  │  ████    ╲   ██   ╱
  │ ██████    ╲ ████ ╱
  │  ████      ╲██████
  │   ██   B━━━━━━━━━D
  │ ← Pole     Flag →
  └──────────────────────── Time
```

**What to verify**:
- [ ] Two diagonal lines forming a channel
- [ ] Lines converge slightly (flag narrows)
- [ ] Green color for bullish, red for bearish
- [ ] Lines pass through or near candlestick highs/lows

---

### Triangle Patterns

**Points**: A, B, C, D (forming converging boundaries)

**Ascending Triangle**:
- Upper line: `A → C` (solid) - horizontal resistance
- Lower line: `B → D` (solid) - rising support

```
Ascending Triangle:
Price
  │  A━━━━━━━━━━━━━━━━━━━━━C  ← Flat resistance
  │   ██████      ██████
  │    ████        ████
  │   B━━━━━━━━━━━━━━━━━━D    ← Rising support
  │    ↗ Converging ↗
  └──────────────────────────── Time
```

**Descending Triangle**:
- Upper line: Falling resistance
- Lower line: Flat support

**Symmetrical Triangle**:
- Both lines converge toward apex

**What to verify**:
- [ ] Two lines forming triangle shape
- [ ] Lines converge toward the right
- [ ] Ascending = green, Descending = red, Symmetrical = blue

---

### Wedge Patterns

**Points**: A (upper-left), B (lower-left), C (upper-right), D (lower-right)

**Lines drawn**:
- `A → C` (solid): Upper boundary
- `B → D` (solid): Lower boundary

```
Rising Wedge (Bearish):
Price
  │              C
  │            ╱
  │          ╱    ← Both lines rise
  │        A━━━━━━━━
  │      ╱        D
  │    ╱        ╱
  │  B━━━━━━━━╱
  └──────────────────── Time

Falling Wedge (Bullish):
Price
  │  A━━━━━━━━
  │    ╲        B
  │      ╲    ╱    ← Both lines fall
  │        ╲╱
  │      C━━━━━━D
  └──────────────────── Time
```

**What to verify**:
- [ ] Two converging lines
- [ ] Rising wedge = red (bearish)
- [ ] Falling wedge = green (bullish)

---

### Head and Shoulders

**Points**: A (left shoulder), B (left neck), C (head), D (right neck), E (right shoulder)

**Lines drawn**:
- `B → D` (solid): Neckline
- `A → C` (dashed): Left shoulder to head
- `C → E` (dashed): Head to right shoulder

```
Head and Shoulders:
Price
  │            C ← Head
  │           ╱╲
  │    A     ╱  ╲     E
  │   ╱╲    ╱    ╲   ╱╲
  │  ╱  ╲  ╱      ╲ ╱  ╲
  │ ╱    ╲╱        ╲╱    ╲
  │      B━━━━━━━━━D ← Neckline (solid)
  └────────────────────────── Time
```

**What to verify**:
- [ ] Solid neckline connecting B and D
- [ ] Dashed lines connecting peaks (A→C→E)
- [ ] Red color (bearish pattern)

---

### Double Top / Double Bottom

**Points**: A (first peak/trough), B (middle), C (second peak/trough)

**Lines drawn**:
- `A → C` (solid): Connect the two tops/bottoms
- `A → B` (dashed): First movement
- `B → C` (dashed): Second movement

```
Double Top:
Price
  │    A━━━━━━━━━━━━━━━C ← Horizontal resistance
  │   ╱╲              ╱╲
  │  ╱  ╲            ╱  ╲
  │ ╱    ╲    B     ╱    ╲
  │       ╲  ╱╲    ╱
  │        ╲╱  ╲  ╱
  │             ╲╱
  └────────────────────────── Time

Double Bottom:
Price
  │        ╱╲
  │       ╱  ╲  ╱╲
  │      ╱    ╲╱  ╲
  │     ╱     B    ╲
  │    ╱╲          ╱╲
  │   ╱  ╲        ╱  ╲
  │  A━━━━━━━━━━━━━━━C ← Horizontal support
  └────────────────────────── Time
```

**What to verify**:
- [ ] Solid horizontal line at A and C level
- [ ] Dashed lines showing the W or M shape
- [ ] Double top = red, Double bottom = green

---

## Color Reference

| Pattern Type | Color | Hex |
|--------------|-------|-----|
| `bullish_flag` | Green | `#22c55e` |
| `bearish_flag` | Red | `#ef4444` |
| `ascending_triangle` | Green | `#22c55e` |
| `descending_triangle` | Red | `#ef4444` |
| `symmetrical_triangle` | Blue | `#3b82f6` |
| `falling_wedge` | Green | `#22c55e` |
| `rising_wedge` | Red | `#ef4444` |
| `head_shoulders` | Red | `#ef4444` |
| `reverse_head_shoulders` | Green | `#22c55e` |
| `double_top` | Red | `#ef4444` |
| `double_bottom` | Green | `#22c55e` |

---

## Visual Validation Summary

When validating pattern overlays, check:

1. **Lines present**: Diagonal/horizontal lines visible on chart
2. **Correct connections**: Lines connect logical pattern points
3. **Color correct**: Green (bullish), Red (bearish), Blue (neutral)
4. **Line style**: Solid for primary boundaries, dashed for secondary
5. **Alignment**: Lines pass through or near candlestick pivot points
6. **Legend**: Pattern shown with line indicator (not box)
7. **Panel**: Pattern listed in ChartPatternsPanel

---

## What We NO LONGER Render

**REMOVED**: Shaded rectangular bounding boxes

```
OLD (removed):
┌─────────────────┐
│ ░░░░░░░░░░░░░░░ │ ← NO MORE shaded rectangles
│ ░░░░░░░░░░░░░░░ │
└─────────────────┘

NEW (current):
    A━━━━━━━━━━━C
     ╲          ╱
      ╲        ╱     ← Actual trendlines
       ╲      ╱
    B━━━━━━━━━D
```

---

*Reference document for visual-ta-validation skill*
*Last updated: 2026-01-14*
*Rendering changed from bounding boxes to trendlines*
