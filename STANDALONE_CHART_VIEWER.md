# Standalone Chart Viewer

**Client-Side Candlestick Chart with Pattern Detection** (Telegram Approach)

A separate, standalone web application that visualizes candlestick charts with pattern detection using client-side rendering - the same approach used by the Telegram Mini App frontend.

---

## Overview

This implementation demonstrates the **Telegram Mini App approach** to charting:
- **Client-side rendering**: JavaScript Chart.js library renders charts in the browser
- **API-driven**: Backend provides JSON data, frontend renders interactively
- **Real-time pattern detection**: Python pattern detectors analyze charts
- **Mobile-optimized**: Responsive design, touch-friendly interactions

---

## Architecture

```
┌─────────────────────────────────────────────────┐
│  Browser (Client-Side)                          │
│  ┌───────────────────────────────────────────┐ │
│  │  standalone_chart_viewer.html             │ │
│  │  - Chart.js candlestick rendering         │ │
│  │  - Pattern overlays (wedge trendlines)    │ │
│  │  - Support/Resistance levels              │ │
│  │  - Interactive tooltips                    │ │
│  └───────────────────────────────────────────┘ │
└─────────────────────────────────────────────────┘
                     ↕ HTTP/JSON
┌─────────────────────────────────────────────────┐
│  Backend Server (Python Flask)                  │
│  ┌───────────────────────────────────────────┐ │
│  │  standalone_chart_server.py               │ │
│  │  - /api/chart-data/<symbol>               │ │
│  │  - yfinance OHLC data fetching            │ │
│  │  - Pattern detection integration          │ │
│  │  - JSON serialization                     │ │
│  └───────────────────────────────────────────┘ │
└─────────────────────────────────────────────────┘
                     ↕
┌─────────────────────────────────────────────────┐
│  Pattern Detection Engine                       │
│  ┌───────────────────────────────────────────┐ │
│  │  src/analysis/pattern_detectors/          │ │
│  │  - ChartPatternDetector (wedges, etc.)    │ │
│  │  - SupportResistanceDetector              │ │
│  │  - Pattern types and constants            │ │
│  └───────────────────────────────────────────┘ │
└─────────────────────────────────────────────────┘
```

---

## Features

### ✅ Client-Side Rendering
- **Chart.js** with Financial plugin for candlestick charts
- Smooth animations and interactions
- Responsive canvas rendering
- Touch-friendly for mobile devices

### ✅ Real Pattern Detection
- **Wedge patterns** (rising/falling) with trendline overlays
- **Support/Resistance levels** displayed as dashed lines
- **Pattern metadata** shown in cards (confidence, slopes, dates)

### ✅ Interactive UI
- **Ticker selector**: Load any stock symbol (AAPL, MSFT, etc.)
- **Period selector**: 30d, 60d, 90d, 6mo time ranges
- **Live data**: Fetches from yfinance in real-time
- **Pattern cards**: Visual summary of detected patterns

### ✅ Professional Design
- Gradient header design
- Color-coded patterns (green=bullish, red=bearish)
- Confidence badges (high, medium, low)
- Clean, modern UI with proper spacing

---

## Installation & Usage

### 1. Install Dependencies

```bash
# Install flask-cors (if not already installed)
pip install flask-cors>=4.0.0

# Or install all requirements
pip install -r requirements.txt
```

### 2. Start the Server

```bash
# Run the Flask server
python standalone_chart_server.py
```

**Server Output**:
```
============================================================
🚀 Standalone Chart Server Starting
============================================================

📊 Chart Viewer: http://localhost:8080
🔌 API Endpoint: http://localhost:8080/api/chart-data/<symbol>?period=60d

Press Ctrl+C to stop
============================================================
```

### 3. Open in Browser

Navigate to: **http://localhost:8080**

### 4. Use the Interface

1. **Enter ticker symbol** (e.g., AAPL, MSFT, GOOGL, NVDA, TSLA)
2. **Select period** (30d, 60d, 90d, or 6mo)
3. **Click "Load Chart"**
4. **View candlestick chart** with pattern overlays
5. **Scroll down** to see detected pattern cards

---

## API Endpoints

### `GET /api/chart-data/<symbol>`

Fetch OHLC data and detected patterns for a ticker.

**Parameters**:
- `symbol` (path): Ticker symbol (e.g., `AAPL`)
- `period` (query, optional): Time period (`30d`, `60d`, `90d`, `6mo`). Default: `60d`

**Example Request**:
```bash
curl "http://localhost:8080/api/chart-data/AAPL?period=60d"
```

**Example Response**:
```json
{
  "symbol": "AAPL",
  "ohlc": [
    {
      "x": 1704067200000,
      "o": 185.28,
      "h": 186.40,
      "l": 184.35,
      "c": 185.92
    },
    ...
  ],
  "patterns": {
    "chart_patterns": [
      {
        "pattern": "wedge_rising",
        "type": "bearish",
        "confidence": "medium",
        "start_date": "2024-12-15T00:00:00",
        "end_date": "2025-01-03T00:00:00",
        "resistance_slope": 0.05,
        "support_slope": 0.15,
        "convergence_ratio": 0.65
      }
    ],
    "support_resistance": {
      "support": [178.5, 182.3],
      "resistance": [189.7, 192.4],
      "current_price": 185.92
    }
  }
}
```

### `GET /health`

Health check endpoint.

**Response**:
```json
{
  "status": "healthy"
}
```

---

## Technology Stack

### Backend
- **Python 3.12+**
- **Flask 3.0+**: Lightweight web framework
- **Flask-CORS**: Cross-origin resource sharing
- **yfinance**: Real-time stock data
- **Pattern detectors**: From `src/analysis/pattern_detectors/`

### Frontend
- **Chart.js 4.4**: Canvas-based charting library
- **chartjs-chart-financial**: Candlestick chart plugin
- **Luxon**: Date/time handling
- **Vanilla JavaScript**: No framework dependencies

---

## Comparison: Standalone vs Telegram Mini App

| Feature | Standalone Chart Viewer | Telegram Mini App Frontend |
|---------|-------------------------|---------------------------|
| **Rendering** | Client-side (Chart.js) | Client-side (Recharts) |
| **Framework** | Vanilla JS | React 19 + TypeScript |
| **Chart Library** | Chart.js (Canvas) | Recharts (SVG) |
| **Bundle Size** | ~150KB (Chart.js + plugins) | ~198KB (Recharts + React) |
| **Backend** | Flask + yfinance (live) | FastAPI + Aurora (precomputed) |
| **Use Case** | Standalone demo/testing | Production Telegram app |
| **Pattern Overlays** | ✅ Wedge trendlines | ⚠️ Not implemented yet |
| **Interactivity** | ✅ Zoom, pan, tooltips | ✅ Touch, tooltips, modal |

---

## Pattern Detection

### Supported Patterns

**Chart Patterns**:
- ✅ **Wedge Rising** (bearish) - Converging trendlines, upward bias
- ✅ **Wedge Falling** (bullish) - Converging trendlines, downward bias
- ✅ **Head & Shoulders** (bearish reversal)
- ✅ **Triangles** (continuation/reversal)
- ✅ **Double Top/Bottom** (reversal)

**Support & Resistance**:
- ✅ **Support levels** (price floors)
- ✅ **Resistance levels** (price ceilings)
- ✅ **Current price** indicator

### Pattern Visualization

**Wedge Patterns**:
- **Resistance trendline**: Red solid line (upper boundary)
- **Support trendline**: Teal solid line (lower boundary)
- **Shaded area**: Pattern convergence zone
- **Annotation**: Pattern name with arrow pointer

**Support/Resistance**:
- **Support**: Green dashed horizontal lines
- **Resistance**: Red dashed horizontal lines

---

## Customization

### Change Chart Colors

Edit `standalone_chart_viewer.html` CSS:

```css
/* Candlestick colors */
.legend-item.candle-up::before {
    background: #26A69A;  /* Bullish candle color */
}

.legend-item.candle-down::before {
    background: #EF5350;  /* Bearish candle color */
}

/* Trendline colors */
.legend-item.resistance::before {
    background: #FF6B6B;  /* Resistance line color */
}

.legend-item.support::before {
    background: #4ECDC4;  /* Support line color */
}
```

### Add More Patterns

1. **Detect pattern** in `src/analysis/pattern_detectors/`
2. **Add rendering logic** in `standalone_chart_viewer.html`:
   ```javascript
   // In renderPatternsSummary() function
   if (pattern.pattern === 'your_new_pattern') {
       // Add custom visualization
   }
   ```

### Change Default Ticker/Period

Edit `standalone_chart_viewer.html`:

```html
<input type="text" id="ticker" value="NVDA" placeholder="e.g., AAPL, MSFT">

<select id="period">
    <option value="90d" selected>90 Days</option>  <!-- Change default -->
</select>
```

---

## Troubleshooting

### Port 8080 Already in Use

```bash
# Use a different port
# Edit standalone_chart_server.py line 127:
app.run(host='0.0.0.0', port=8081, debug=True)
```

### CORS Errors in Browser Console

Make sure `flask-cors` is installed:

```bash
pip install flask-cors
```

### "No data available for AAPL" Error

- Check internet connection (yfinance fetches from Yahoo Finance)
- Verify ticker symbol is valid
- Try a different period (some stocks lack historical data)

### Pattern Detection Not Showing

- Patterns may not exist in the selected time period
- Try different tickers (AAPL, MSFT, NVDA usually have patterns)
- Increase period to 90d or 6mo for more data

---

## Development

### Run in Development Mode

```bash
# Flask debug mode (auto-reload on file changes)
FLASK_ENV=development python standalone_chart_server.py
```

### Test API Endpoint

```bash
# Test AAPL data
curl "http://localhost:8080/api/chart-data/AAPL?period=60d" | jq .

# Test health check
curl "http://localhost:8080/health"
```

### Add Logging

Edit `standalone_chart_server.py`:

```python
import logging
logging.basicConfig(level=logging.DEBUG)  # More verbose logging
```

---

## File Structure

```
dr-daily-report_telegram/
├── standalone_chart_viewer.html    # Frontend HTML (Chart.js)
├── standalone_chart_server.py      # Backend Flask API
├── STANDALONE_CHART_VIEWER.md      # This documentation
└── src/analysis/pattern_detectors/ # Pattern detection engine
    ├── chart_patterns.py           # Chart pattern detection
    ├── support_resistance.py       # S/R level detection
    └── pattern_types.py            # Pattern constants
```

---

## Next Steps

### Integrate with Telegram Mini App

To add pattern overlays to the Telegram Mini App:

1. **Update API transformer** (`src/api/transformer.py`):
   ```python
   # Add pattern data to report response
   patterns = detect_patterns_from_ticker_data(ticker_data)
   return {
       ...existing fields...,
       "patterns": patterns  # NEW
   }
   ```

2. **Update frontend** (`frontend/twinbar/src/components/FullChart.tsx`):
   ```tsx
   // Add pattern overlay rendering
   {patterns?.chart_patterns.map(pattern => (
       <ReferenceLine ... /> // Wedge trendlines
   ))}
   ```

### Add More Chart Types

- **Volume bars** below candlesticks
- **RSI indicator** subplot
- **MACD indicator** subplot
- **Bollinger Bands** overlays

### Export Functionality

- **Download as PNG**: Add button to save chart image
- **Export data as CSV**: Allow downloading OHLC data
- **Share link**: Generate shareable URLs with ticker/period

---

## Credits

**Approach**: Inspired by Telegram Mini App frontend architecture (client-side rendering with API-driven data)

**Chart Library**: Chart.js Financial Plugin (https://github.com/chartjs/chartjs-chart-financial)

**Data Source**: yfinance (Yahoo Finance API wrapper)

**Pattern Detection**: Custom implementation in `src/analysis/pattern_detectors/`

---

## License

This standalone viewer is part of the dr-daily-report_telegram project and follows the same license.
