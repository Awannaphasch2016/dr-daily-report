---
title: Chart Pattern Overlay Rendering
focus: api
date: 2026-01-14
status: draft
tags: [chart, pattern, visualization, candlestick]
---

# API Specification: Chart Pattern Overlay Rendering

## Goal

**What problem does this solve?**

Draw detected chart patterns (head-and-shoulders, double tops, triangles, etc.) as visual overlays on candlestick charts. This enables users to see pattern boundaries, key price levels, and trend lines directly on the chart.

**Target consumers:**
- Telegram Mini App (React frontend)
- PDF report generation
- Interactive chart component

---

## Approach Comparison

### Option A: Custom Implementation

**Philosophy**: Build pattern rendering directly using existing chart library primitives.

### Option B: Third-Party Library

**Philosophy**: Use specialized charting libraries with built-in pattern/annotation support.

---

## Option A: Custom Implementation

### API Design

#### Function: `render_pattern_overlay`

```python
def render_pattern_overlay(
    chart_data: pd.DataFrame,
    patterns: List[ChartPattern],
    config: PatternOverlayConfig = None
) -> matplotlib.figure.Figure:
    """
    Render detected patterns as overlays on candlestick chart.

    Args:
        chart_data: OHLC DataFrame with DatetimeIndex
        patterns: List of detected patterns from pattern_detection_service
        config: Optional styling configuration

    Returns:
        Matplotlib figure with patterns rendered
    """
```

#### Data Model: `ChartPattern`

```python
from dataclasses import dataclass
from typing import List, Tuple, Optional
from datetime import date

@dataclass
class PatternPoint:
    """Single point in a pattern (e.g., head, shoulder, neckline)"""
    date: date
    price: float
    label: str  # "left_shoulder", "head", "neckline_start", etc.

@dataclass
class ChartPattern:
    """Detected chart pattern with rendering metadata"""
    pattern_type: str           # "head_and_shoulders", "double_top", "triangle"
    direction: str              # "bullish" | "bearish"
    confidence: float           # 0.0 - 1.0

    # Key points defining the pattern
    points: List[PatternPoint]

    # Derived lines for rendering
    trend_lines: List[Tuple[PatternPoint, PatternPoint]]
    support_levels: List[float]
    resistance_levels: List[float]

    # Pattern boundaries
    start_date: date
    end_date: date

    # Target/stop levels
    price_target: Optional[float]
    stop_loss: Optional[float]

@dataclass
class PatternOverlayConfig:
    """Styling configuration for pattern overlays"""
    # Colors
    bullish_color: str = "#22c55e"     # Green
    bearish_color: str = "#ef4444"     # Red
    neutral_color: str = "#6b7280"     # Gray

    # Line styles
    trend_line_width: float = 1.5
    trend_line_style: str = "--"       # dashed

    support_line_width: float = 1.0
    support_line_style: str = ":"      # dotted

    # Labels
    show_labels: bool = True
    label_font_size: int = 8

    # Shading
    fill_alpha: float = 0.1            # Pattern area fill transparency

    # Target/Stop
    show_targets: bool = True
    target_line_style: str = "-."      # dash-dot
```

#### Rendering Logic

```python
def _render_single_pattern(
    ax: matplotlib.axes.Axes,
    pattern: ChartPattern,
    config: PatternOverlayConfig
) -> None:
    """Render a single pattern on the chart axes."""

    color = (config.bullish_color if pattern.direction == "bullish"
             else config.bearish_color)

    # 1. Draw trend lines
    for start_pt, end_pt in pattern.trend_lines:
        ax.plot(
            [start_pt.date, end_pt.date],
            [start_pt.price, end_pt.price],
            color=color,
            linewidth=config.trend_line_width,
            linestyle=config.trend_line_style,
            alpha=0.8
        )

    # 2. Draw support/resistance levels
    for level in pattern.support_levels:
        ax.axhline(
            y=level,
            color=config.bullish_color,
            linewidth=config.support_line_width,
            linestyle=config.support_line_style,
            alpha=0.5
        )

    for level in pattern.resistance_levels:
        ax.axhline(
            y=level,
            color=config.bearish_color,
            linewidth=config.support_line_width,
            linestyle=config.support_line_style,
            alpha=0.5
        )

    # 3. Mark key points
    if config.show_labels:
        for point in pattern.points:
            ax.annotate(
                point.label.replace("_", " ").title(),
                xy=(point.date, point.price),
                xytext=(5, 5),
                textcoords="offset points",
                fontsize=config.label_font_size,
                color=color,
                alpha=0.8
            )
            ax.scatter(
                [point.date], [point.price],
                color=color, s=30, zorder=5
            )

    # 4. Fill pattern area (optional)
    if config.fill_alpha > 0 and len(pattern.points) >= 3:
        dates = [p.date for p in pattern.points]
        prices = [p.price for p in pattern.points]
        ax.fill(dates, prices, color=color, alpha=config.fill_alpha)

    # 5. Draw target/stop levels
    if config.show_targets:
        if pattern.price_target:
            ax.axhline(
                y=pattern.price_target,
                color=config.bullish_color,
                linewidth=1.0,
                linestyle=config.target_line_style,
                alpha=0.6
            )
            ax.text(
                pattern.end_date, pattern.price_target,
                f" Target: {pattern.price_target:.2f}",
                fontsize=7, color=config.bullish_color
            )

        if pattern.stop_loss:
            ax.axhline(
                y=pattern.stop_loss,
                color=config.bearish_color,
                linewidth=1.0,
                linestyle=config.target_line_style,
                alpha=0.6
            )
```

#### Integration Point

Location: `src/visualization/chart_generator.py`

```python
# Existing chart generation
def generate_chart(ticker: str, data: pd.DataFrame, ...) -> str:
    fig, ax = plt.subplots(...)

    # Draw candlesticks (existing)
    _draw_candlesticks(ax, data)

    # NEW: Draw pattern overlays
    if patterns:
        config = PatternOverlayConfig()
        for pattern in patterns:
            _render_single_pattern(ax, pattern, config)

    # Convert to base64 (existing)
    return fig_to_base64(fig)
```

---

### Supported Patterns (Custom)

| Pattern | Points Required | Rendering Elements |
|---------|-----------------|-------------------|
| Head & Shoulders | 5 (LS, H, RS, NL1, NL2) | Neckline, shoulder lines |
| Double Top/Bottom | 4 (T1, T2, NL1, NL2) | Neckline, peak markers |
| Triangle (Sym/Asc/Desc) | 4+ (highs, lows) | Converging trend lines |
| Wedge | 4+ | Converging lines (steeper) |
| Channel | 4 (top/bottom pairs) | Parallel lines |
| Flag/Pennant | 4+ | Flagpole + pattern |

---

### Pros/Cons: Custom Implementation

**Pros:**
- ✅ Full control over rendering
- ✅ Matches existing chart style
- ✅ No additional dependencies
- ✅ Works with matplotlib (already used)
- ✅ Can customize every detail

**Cons:**
- ❌ More code to maintain
- ❌ Must handle edge cases (overlapping patterns, dense charts)
- ❌ Need to implement each pattern type rendering
- ❌ Z-ordering and layering complexity

---

## Option B: Third-Party Library

### Candidate Libraries

#### 1. mplfinance (Matplotlib Finance)

**Current status**: Already using for candlestick charts

```python
import mplfinance as mpf

# Add pattern lines using addplot
pattern_lines = [
    mpf.make_addplot(neckline_series, color='blue', linestyle='--'),
    mpf.make_addplot(target_series, color='green', linestyle=':'),
]

mpf.plot(data, type='candle', addplot=pattern_lines)
```

**Pros:**
- ✅ Already in codebase
- ✅ Native matplotlib integration
- ✅ `addplot` for custom overlays

**Cons:**
- ❌ No built-in pattern annotations
- ❌ Limited to line/scatter overlays
- ❌ Manual coordinate calculation still needed

---

#### 2. Plotly

```python
import plotly.graph_objects as go

fig = go.Figure(data=[go.Candlestick(...)])

# Add pattern shapes
fig.add_shape(
    type="line",
    x0=start_date, y0=start_price,
    x1=end_date, y1=end_price,
    line=dict(color="blue", dash="dash")
)

# Add annotations
fig.add_annotation(
    x=point_date, y=point_price,
    text="Head",
    showarrow=True
)
```

**Pros:**
- ✅ Rich annotation API
- ✅ Interactive charts
- ✅ Built-in shapes (lines, rectangles, polygons)
- ✅ Hover tooltips for patterns

**Cons:**
- ❌ New dependency
- ❌ Different rendering pipeline
- ❌ Not compatible with current PDF generation
- ❌ Heavier bundle for frontend

---

#### 3. Lightweight Charts (TradingView)

```typescript
// Frontend (React)
import { createChart } from 'lightweight-charts';

const chart = createChart(container);
const candlestickSeries = chart.addCandlestickSeries();

// Add pattern markers
candlestickSeries.setMarkers([
    { time: '2026-01-10', position: 'aboveBar', color: 'blue', shape: 'circle', text: 'H' },
    { time: '2026-01-05', position: 'belowBar', color: 'blue', shape: 'circle', text: 'LS' },
]);

// Add trend lines (requires plugin or custom)
// Note: Native trend lines limited, need workaround
```

**Pros:**
- ✅ Professional TradingView-style charts
- ✅ Interactive (zoom, pan, crosshair)
- ✅ Built-in markers
- ✅ Lightweight (~40KB)

**Cons:**
- ❌ Frontend-only (TypeScript/JS)
- ❌ Limited annotation primitives
- ❌ No native polygon/area fill
- ❌ Would need backend changes for consistency

---

#### 4. Apache ECharts

```typescript
import * as echarts from 'echarts';

const option = {
    series: [{
        type: 'candlestick',
        data: ohlcData
    }],
    graphic: [{
        type: 'line',
        shape: {
            x1: 100, y1: 200,
            x2: 300, y2: 250
        },
        style: {
            stroke: 'blue',
            lineDash: [5, 5]
        }
    }, {
        type: 'polygon',
        shape: {
            points: [[100, 200], [200, 150], [300, 200]]
        },
        style: {
            fill: 'rgba(0, 100, 255, 0.1)'
        }
    }]
};
```

**Pros:**
- ✅ Rich graphic primitives
- ✅ Polygons, lines, text, markers
- ✅ Good performance
- ✅ Can render to canvas or SVG

**Cons:**
- ❌ Large bundle (~800KB min)
- ❌ Complex API
- ❌ Backend/PDF generation needs different approach

---

#### 5. stock-indicators (Python)

```python
from stock_indicators import indicators

# This library is for CALCULATING indicators, not rendering
# Still need separate rendering solution
```

**Verdict**: Not a rendering library, only calculations.

---

### Recommendation Matrix

| Library | Backend (Python) | Frontend (React) | PDF Export | Interactive | Bundle Size | Verdict |
|---------|-----------------|------------------|------------|-------------|-------------|---------|
| mplfinance | ✅ Yes | ❌ No | ✅ Yes | ❌ No | N/A | **Best for backend** |
| Plotly | ✅ Yes | ✅ Yes | ⚠️ Complex | ✅ Yes | 3MB+ | Good but heavy |
| Lightweight Charts | ❌ No | ✅ Yes | ❌ No | ✅ Yes | 40KB | **Best for frontend** |
| ECharts | ❌ No | ✅ Yes | ⚠️ Complex | ✅ Yes | 800KB | Overkill |
| Custom (matplotlib) | ✅ Yes | ❌ No | ✅ Yes | ❌ No | 0 | **Most flexible** |

---

## Recommended Approach: Hybrid

### Backend (Python): Custom + mplfinance

```python
# src/visualization/pattern_overlay.py

import mplfinance as mpf
import matplotlib.pyplot as plt

def render_chart_with_patterns(
    data: pd.DataFrame,
    patterns: List[ChartPattern],
    style: str = "yahoo"
) -> matplotlib.figure.Figure:
    """
    Render candlestick chart with pattern overlays.
    Uses mplfinance for base chart, custom rendering for patterns.
    """
    # Create figure with mplfinance
    fig, axes = mpf.plot(
        data,
        type='candle',
        style=style,
        returnfig=True,
        figsize=(10, 6)
    )

    ax = axes[0]  # Main price axis

    # Overlay patterns using custom rendering
    config = PatternOverlayConfig()
    for pattern in patterns:
        _render_single_pattern(ax, pattern, config)

    return fig
```

### Frontend (React): Lightweight Charts + Custom SVG

```typescript
// frontend/twinbar/src/components/PatternOverlay.tsx

import { createChart, IChartApi, ISeriesApi } from 'lightweight-charts';

interface PatternOverlayProps {
    patterns: ChartPattern[];
    chartApi: IChartApi;
    series: ISeriesApi<'Candlestick'>;
}

export function PatternOverlay({ patterns, chartApi, series }: PatternOverlayProps) {
    useEffect(() => {
        // Add markers for key pattern points
        const markers = patterns.flatMap(pattern =>
            pattern.points.map(point => ({
                time: point.date,
                position: point.price > currentPrice ? 'aboveBar' : 'belowBar',
                color: pattern.direction === 'bullish' ? '#22c55e' : '#ef4444',
                shape: 'circle',
                text: point.label[0].toUpperCase()
            }))
        );

        series.setMarkers(markers);

        // For complex shapes (trend lines, fills), use SVG overlay
        // positioned absolutely over the chart
    }, [patterns, series]);

    return (
        <svg className="pattern-overlay">
            {patterns.map(pattern => (
                <PatternShape key={pattern.id} pattern={pattern} />
            ))}
        </svg>
    );
}
```

---

## Implementation Plan

### Phase 1: Backend (Custom + mplfinance)

1. Create `PatternOverlayConfig` dataclass
2. Implement `_render_single_pattern()` for each pattern type
3. Integrate into existing `chart_generator.py`
4. Test with detected patterns from `pattern_detection_service`

**Effort**: ~2-3 hours

### Phase 2: Frontend (Lightweight Charts)

1. Add markers for pattern points (built-in feature)
2. Create SVG overlay component for trend lines
3. Position overlay relative to chart coordinates
4. Handle zoom/pan synchronization

**Effort**: ~4-6 hours

### Phase 3: Enhancement

1. Add pattern legend/tooltip
2. Toggle pattern visibility
3. Pattern click → detail view

**Effort**: ~2-3 hours

---

## Open Questions

- [ ] Should patterns be rendered on PDF charts? (Currently yes)
- [ ] How many patterns to show at once? (Risk of visual clutter)
- [ ] Should overlapping patterns be handled? (Z-order, transparency)
- [ ] Interactive features needed? (Click pattern for details)
- [ ] Color scheme for different pattern types vs direction?

---

## Next Steps

- [ ] Review this specification
- [ ] Decide: Custom only vs Hybrid approach
- [ ] If approved, implement Phase 1 (backend)
- [ ] Test with sample detected patterns
- [ ] Iterate on styling/UX
