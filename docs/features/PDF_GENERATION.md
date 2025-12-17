# PDF Report Generation Guide

**Date:** 2025-11-01
**Version:** 1.0

---

## Overview

The PDF Report Generator creates professional, comprehensive investment analysis reports in PDF format. Each report follows a structured format with:

1. **Title** - Company name, ticker, sector, and analysis date
2. **Quick Summary** - Key metrics at a glance
3. **Technical Analysis Chart** - 4-panel chart with indicators and annotations
4. **Investment Analysis Narrative** - Thai language story-driven analysis
5. **News References** - Recent news with sentiment and impact scores
6. **Investment Scoring** - Comprehensive scoring across multiple categories

---

## Features

### 1. Professional Layout

- **A4 page size** (210mm x 297mm)
- **Clean typography** with custom styles
- **Color-coded elements** for quick visual parsing
- **Structured sections** with emoji headers

### 2. Comprehensive Content

#### Title Section
- Company name and ticker symbol
- Sector and industry classification
- Analysis date

#### Quick Summary Table
- Current price
- Market capitalization
- P/E ratio
- RSI status (with color coding: red for overbought, green for oversold)
- Analyst rating
- News sentiment (color-coded)

#### Technical Analysis Chart
- **4-panel chart** (1400x1000 pixels):
  - Panel 1: Candlestick price chart with SMA overlays
  - Panel 2: Volume bars
  - Panel 3: RSI subplot with overbought/oversold zones
  - Panel 4: MACD subplot with signal line and histogram
- **Key indicator annotations** with percentile context
- **Trend indicators** (Golden Cross/Death Cross, Bullish/Bearish MACD)

#### Investment Analysis Narrative
- **Thai language** narrative in Aswath Damodaran style
- **Structured sections:**
  - 📖 Story of the stock (what's happening)
  - 💡 Key insights (why it matters)
  - 🎯 Recommendation (BUY/SELL/HOLD with reasoning)
  - ⚠️ Risk warnings (what to watch)
  - 📊 Percentile analysis (detailed statistics)

#### News References Table
- **Recent high-impact news** (minimum impact score 40/100)
- **Sentiment classification** (positive/negative/neutral) with color coding
- **Impact scores** (0-100)
- **Reference numbers** matching narrative citations

#### Investment Scoring Section
- **Overall investment score** (0-100) with letter grade
- **Category breakdown:**
  - Technical Analysis (35% weight)
  - Fundamental Strength (25% weight)
  - Momentum Indicators (25% weight)
  - News Sentiment (15% weight)
- **Score interpretation** with recommendations
- **Disclaimer** about investment advice

---

## Usage

### Basic Usage

```python
from src.agent import TickerAnalysisAgent

# Initialize agent
agent = TickerAnalysisAgent()

# Generate PDF report
pdf_bytes = agent.generate_pdf_report(
    ticker="NVDA19",
    output_path="nvda_report.pdf"  # Optional: saves to file
)

# If output_path not provided, returns PDF bytes
# pdf_bytes = agent.generate_pdf_report(ticker="NVDA19")
```

### Command-Line Testing

```bash
# Test with single ticker
python tests/test_pdf_generation.py --ticker NVDA19

# Test with multiple tickers
python tests/test_pdf_generation.py --multi
```

### Example Output

```
================================================================================
PDF REPORT GENERATION TEST - NVDA19
================================================================================

🔄 Initializing agent...
✅ Agent initialized

📊 Generating PDF report for NVDA19...
   This will:
   1. Fetch ticker data from Yahoo Finance
   2. Calculate technical indicators
   3. Fetch and analyze news
   4. Generate chart visualization
   5. Create narrative report with GPT-4o
   6. Compile everything into PDF

⏳ Please wait... (this may take 10-15 seconds)

✅ Chart generated for NVDA19
✅ PDF report saved to: NVDA19_report_20251101_160120.pdf
✅ PDF report generated successfully!

📁 Report Details:
   File: NVDA19_report_20251101_160120.pdf
   Size: 155,015 bytes (151.4 KB)

📖 Report Structure:
   1. ✅ Title with company info
   2. ✅ Quick Summary (price, P/E, RSI, analyst rating, sentiment)
   3. ✅ Technical Analysis Chart (4-panel with indicators)
   4. ✅ Investment Analysis Narrative (Thai story-style)
   5. ✅ News References (with sentiment and impact scores)
   6. ✅ Investment Scoring (technical, fundamental, momentum, sentiment)

💡 You can now open 'NVDA19_report_20251101_160120.pdf' with any PDF viewer

🎯 Test Result: PASSED ✅
```

---

## Technical Details

### Dependencies

```
reportlab>=4.0.0
```

Install with:
```bash
pip install reportlab>=4.0.0
```

### Performance

- **Generation time:** 10-15 seconds (includes full analysis pipeline)
- **File size:** ~150 KB typical (varies based on chart complexity and news count)
- **Memory usage:** ~250 MB peak (includes chart generation)

### PDF Specifications

- **Page size:** A4 (210mm x 297mm)
- **Margins:** 20mm all sides
- **Fonts:**
  - Helvetica (default)
  - Helvetica-Bold (headers, emphasis)
  - Thai Unicode support (via built-in fonts)

### Color Scheme

| Element | Color | Hex Code |
|---------|-------|----------|
| Primary (headers) | Blue | `#1f77b4` |
| Success (positive) | Green | `#2ca02c` |
| Warning (caution) | Orange | `#ff7f0e` |
| Danger (negative) | Red | `#d62728` |
| Neutral | Gray | `#7f7f7f` |

---

## Report Sections in Detail

### 1. Title Section

**Content:**
- Company name (e.g., "NVIDIA Corporation")
- Ticker symbol (e.g., "NVDA19")
- Sector (e.g., "Technology")
- Industry (e.g., "Semiconductors")
- Analysis date

**Example:**
```
NVIDIA Corporation (NVDA19)
Technology | Semiconductors
Analysis Date: 2025-11-01
```

---

### 2. Quick Summary

**Format:** 6-row table with key metrics

| Metric | Value |
|--------|-------|
| Price | **$135.50** |
| Market Cap | $3.34T |
| P/E Ratio | 65.23 |
| RSI | 81.12 (Overbought) [red if >70] |
| Analyst Rating | BUY |
| News Sentiment | POSITIVE [green] |

**Visual Features:**
- Alternating row backgrounds for readability
- Right-aligned values
- Color-coded RSI status
- Color-coded sentiment

---

### 3. Technical Analysis Chart

**Chart Specifications:**
- **Dimensions:** 6.5" width x 4.64" height (fits within A4 margins)
- **Resolution:** 100 DPI
- **Format:** PNG (base64 decoded)

**Chart Components:**

**Panel 1: Candlestick Chart**
- Green candles (up days), red candles (down days)
- SMA-20, SMA-50, SMA-200 overlays
- Bollinger Bands (optional)

**Panel 2: Volume Bars**
- Volume bars colored by price direction
- Volume SMA overlay

**Panel 3: RSI Subplot**
- RSI line (0-100 scale)
- Overbought zone (>70, red shaded)
- Oversold zone (<30, green shaded)

**Panel 4: MACD Subplot**
- MACD line (blue)
- Signal line (orange)
- Histogram (green/red bars)

**Key Indicator Annotations:**
Below the chart, displays:
- RSI value with percentile rank
- MACD trend (Bullish/Bearish)
- SMA trend (Golden Cross/Death Cross)

**Example:**
```
Key Indicators:
• RSI: 81.12 (Percentile: 94.2%)
• MACD: 6.32 vs Signal 5.88 (Bullish)
• SMA Trend: Golden Cross
```

---

### 4. Investment Analysis Narrative

**Structure:** 4-6 sections identified by emoji headers

#### 📖 Story Section
**Length:** 2-3 sentences
**Content:** What's happening with the stock right now
**Example:**
```
📖 เรื่องราวของหุ้นตัวนี้
NVIDIA Corporation ตอนนี้อยู่ในสถานการณ์ที่น่าสนใจ ด้วยราคาปัจจุบันที่
$135.50 และมีความไม่แน่นอนในระดับ 68/100 ซึ่งอยู่ในเปอร์เซ็นไทล์ 82%
แสดงว่าตลาดมีความผันผวนสูงกว่าปกติ...
```

#### 💡 Key Insights Section
**Length:** 3-4 flowing paragraphs
**Content:** Why this matters to investors
**Features:**
- Weaves technical + fundamental + news seamlessly
- Includes specific numbers with percentile context
- Explains implications, not just facts

#### 🎯 Recommendation Section
**Length:** 2-3 sentences
**Content:** Clear BUY/SELL/HOLD recommendation with reasoning
**Example:**
```
🎯 ควรทำอะไรตอนนี้?
ในสถานการณ์นี้ คำแนะนำที่ดีที่สุดคือ HOLD แม้ราคาจะสูงกว่าราคา
เป้าหมายเฉลี่ย แต่ความไม่แน่นอนที่สูงและ RSI ที่ Overbought บ่งบอกถึง
การเปลี่ยนแปลงที่อาจเกิดขึ้นในอนาคตอันใกล้
```

#### ⚠️ Risk Warnings Section
**Length:** 1-2 key risks
**Content:** What volatility/pressure/volume signals should trigger concern

#### 📎 News References (Appended)
Lists news articles with reference numbers [1], [2], [3]...

#### 📊 Percentile Analysis (Appended)
Detailed statistical breakdown of all indicators

---

### 5. News References Table

**Format:** Table with 4 columns

| # | Title | Sentiment | Impact |
|---|-------|-----------|--------|
| [1] | NVIDIA announces new AI chip... | 📈 POSITIVE | 85/100 |
| [2] | Tech sector sees rotation... | 📊 NEUTRAL | 45/100 |
| [3] | Competition heats up in GPU market | 📉 NEGATIVE | 72/100 |

**Features:**
- Title truncated to 60 characters
- Sentiment color-coded (green/red/gray)
- Impact score 0-100
- Reference numbers match citations in narrative

---

### 6. Investment Scoring Section

#### Overall Score Display

**Format:** Large, color-coded score

```
Overall Investment Score: 72.5/100 (B)
```

**Color Coding:**
- 75-100: Green (strong opportunity)
- 60-74: Light green (good opportunity)
- 40-59: Orange (moderate opportunity)
- 0-39: Red (weak opportunity)

#### Category Breakdown Table

| Category | Score | Weight | Grade |
|----------|-------|--------|-------|
| Technical Analysis | 65.0/100 | 35% | B- |
| Fundamental Strength | 80.0/100 | 25% | A- |
| Momentum Indicators | 70.0/100 | 25% | B |
| News Sentiment | 75.0/100 | 15% | B+ |

**Overall Score Calculation:**
```
Overall = (Technical × 0.35) + (Fundamental × 0.25) +
          (Momentum × 0.25) + (Sentiment × 0.15)
```

#### Score Interpretation

**Text interpretation** based on overall score:
- **75-100:** "Strong investment opportunity. Favorable conditions across multiple factors."
- **60-74:** "Good investment potential. Most indicators are positive."
- **50-59:** "Moderate investment opportunity. Mixed signals - proceed with caution."
- **40-49:** "Below average investment opportunity. Consider alternative options."
- **0-39:** "Weak investment opportunity. High risk or unfavorable conditions."

#### Disclaimer

Standard investment disclaimer at bottom of scoring section.

---

## Scoring Methodology

### Technical Analysis Score (0-100)

**Base:** 50

**Adjustments:**
- **RSI:**
  - Ideal range (40-60): +20
  - Normal range (30-70): +10
  - Extreme (>70 or <30): -10

- **MACD:**
  - Bullish (MACD > Signal): +15
  - Bearish (MACD < Signal): -10

**Example:**
```python
tech_score = 50  # Base
if 40 <= rsi <= 60:
    tech_score += 20  # Ideal RSI
if macd > signal:
    tech_score += 15  # Bullish MACD
# Result: 50 + 20 + 15 = 85
```

---

### Fundamental Strength Score (0-100)

**Base:** 50

**Adjustments:**
- **P/E Ratio:**
  - Reasonable (10-25): +20
  - Undervalued (<10): +10
  - Overvalued (>40): -15

- **Profit Margin:**
  - High (>20%): +15
  - Good (>10%): +10

**Example:**
```python
fund_score = 50  # Base
if 10 <= pe_ratio <= 25:
    fund_score += 20  # Reasonable valuation
if profit_margin > 0.20:
    fund_score += 15  # High margin
# Result: 50 + 20 + 15 = 85
```

---

### Momentum Indicators Score (0-100)

**Base:** 50

**Adjustments:**
- **RSI Percentile:**
  - Neutral (40-60): +15
  - Strong momentum (>70): +10
  - Weak momentum (<30): -10

- **Volume Percentile:**
  - High interest (>70): +10

**Example:**
```python
mom_score = 50  # Base
if 40 <= rsi_percentile <= 60:
    mom_score += 15  # Neutral momentum
if volume_percentile > 70:
    mom_score += 10  # High volume
# Result: 50 + 15 + 10 = 75
```

---

### News Sentiment Score (0-100)

**Default:** 60 (neutral)

**Future Enhancement:** Will incorporate news_summary data
- Positive sentiment: +20
- Negative sentiment: -20
- High impact news: +10

---

## Letter Grades

| Score Range | Grade |
|-------------|-------|
| 90-100 | A+ |
| 85-89 | A |
| 80-84 | A- |
| 75-79 | B+ |
| 70-74 | B |
| 65-69 | B- |
| 60-64 | C+ |
| 55-59 | C |
| 50-54 | C- |
| 45-49 | D+ |
| 40-44 | D |
| 0-39 | F |

---

## Customization

### Changing Color Scheme

Edit `src/pdf_generator.py`:

```python
class PDFReportGenerator:
    def __init__(self, use_thai_font: bool = True):
        # Color scheme
        self.primary_color = HexColor('#1f77b4')  # Blue
        self.success_color = HexColor('#2ca02c')  # Green
        self.warning_color = HexColor('#ff7f0e')  # Orange
        self.danger_color = HexColor('#d62728')   # Red
        self.neutral_color = HexColor('#7f7f7f')  # Gray
```

### Changing Page Size

```python
from reportlab.lib.pagesizes import letter, A4

# In PDFReportGenerator.__init__:
self.page_width, self.page_height = letter  # US Letter instead of A4
```

### Adding Thai Font Support

Currently uses default Helvetica with Thai Unicode support. For better Thai rendering:

```python
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# Register Thai font (user must install font file)
pdfmetrics.registerFont(TTFont('THSarabunNew', '/path/to/THSarabunNew.ttf'))

# Update style
self.styles['ThaiBody'].fontName = 'THSarabunNew'
```

---

## Troubleshooting

### Issue: "Analysis failed: ไม่พบข้อมูล ticker"

**Cause:** Ticker not in `data/tickers.csv`

**Solution:** Add ticker to CSV file:
```csv
AAPL19,AAPL
TSLA19,TSLA
```

---

### Issue: Chart not appearing in PDF

**Cause:** Chart generation failed (memory limits, matplotlib error)

**Solution:**
- Chart generation is fault-tolerant - PDF will still generate
- Check logs for chart generation errors
- Increase memory if running in Lambda

---

### Issue: Thai text not rendering correctly

**Cause:** Default Helvetica font has limited Thai glyph support

**Solution:**
- Install Thai TrueType font (e.g., THSarabunNew)
- Register font with reportlab (see Customization section)
- Update paragraph styles to use Thai font

---

### Issue: PDF file size too large

**Cause:** High-resolution chart or many news articles

**Solution:**
- Reduce chart size: `days=60` instead of `days=90`
- Limit news articles: `max_news=3` instead of `max_news=5`
- Compress images before encoding to base64

---

## API Integration

### REST API Endpoint (Future Enhancement)

```python
# src/api_handler.py

def api_handler(event, context):
    ticker = event['queryStringParameters']['ticker']
    format = event['queryStringParameters'].get('format', 'json')  # json or pdf

    if format == 'pdf':
        # Generate PDF
        agent = get_agent()
        pdf_bytes = agent.generate_pdf_report(ticker=ticker)

        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/pdf',
                'Content-Disposition': f'attachment; filename="{ticker}_report.pdf"'
            },
            'body': base64.b64encode(pdf_bytes).decode('utf-8'),
            'isBase64Encoded': True
        }
```

### LINE Bot Integration (Future Enhancement)

```python
# Send PDF as file attachment via LINE Messaging API

from linebot.models import MessageEvent, FlexMessage

# Generate PDF
pdf_bytes = agent.generate_pdf_report(ticker=ticker)

# Upload to cloud storage (S3, Google Cloud Storage, etc.)
pdf_url = upload_to_s3(pdf_bytes, f"{ticker}_report.pdf")

# Send as LINE message with download link
line_bot_api.reply_message(
    event.reply_token,
    TextSendMessage(
        text=f"📊 {ticker} Analysis Report Ready!\n"
             f"Download: {pdf_url}"
    )
)
```

---

## Performance Optimization

### Caching

Cache generated PDFs for 5-10 minutes:

```python
import time
from functools import lru_cache

@lru_cache(maxsize=100)
def generate_cached_pdf(ticker: str, timestamp: int):
    """Generate PDF with cache (timestamp for cache invalidation)"""
    agent = TickerAnalysisAgent()
    return agent.generate_pdf_report(ticker=ticker)

# Usage
cache_key = int(time.time() / 300)  # 5-minute buckets
pdf_bytes = generate_cached_pdf("NVDA19", cache_key)
```

### Async Generation

For web applications, generate PDFs asynchronously:

```python
import asyncio
from concurrent.futures import ThreadPoolExecutor

async def generate_pdf_async(ticker: str):
    loop = asyncio.get_event_loop()
    with ThreadPoolExecutor() as executor:
        pdf_bytes = await loop.run_in_executor(
            executor,
            agent.generate_pdf_report,
            ticker
        )
    return pdf_bytes
```

---

## Future Enhancements

1. **Multi-language support** - Generate reports in English, Chinese, Japanese
2. **Custom branding** - Add company logo, custom color schemes
3. **Interactive elements** - Hyperlinked news references, clickable table of contents
4. **Comparative reports** - Compare multiple tickers in single PDF
5. **Portfolio reports** - Consolidated report for entire portfolio
6. **Historical tracking** - Include price history charts, performance tracking
7. **Email delivery** - Automated email delivery with PDF attachment
8. **Batch generation** - Generate PDFs for multiple tickers in parallel

---

## Example Code

### Generate and Save PDF

```python
from src.agent import TickerAnalysisAgent

# Initialize agent
agent = TickerAnalysisAgent()

# Generate PDF and save to file
pdf_bytes = agent.generate_pdf_report(
    ticker="NVDA19",
    output_path="reports/nvda_analysis_20251101.pdf"
)

print(f"PDF generated: {len(pdf_bytes)} bytes")
```

### Generate PDF in Memory

```python
from src.agent import TickerAnalysisAgent

# Initialize agent
agent = TickerAnalysisAgent()

# Generate PDF in memory (no file saved)
pdf_bytes = agent.generate_pdf_report(ticker="NVDA19")

# Send via email, upload to S3, etc.
send_email_with_attachment(
    recipient="investor@example.com",
    subject="NVDA19 Analysis Report",
    attachment=pdf_bytes,
    filename="nvda19_report.pdf"
)
```

### Batch Generate PDFs

```python
from src.agent import TickerAnalysisAgent
from concurrent.futures import ThreadPoolExecutor, as_completed

tickers = ["NVDA19", "TSLA19", "MSFT19", "GOOGL19"]

def generate_report(ticker):
    agent = TickerAnalysisAgent()
    return ticker, agent.generate_pdf_report(
        ticker=ticker,
        output_path=f"reports/{ticker}_report.pdf"
    )

# Generate in parallel
with ThreadPoolExecutor(max_workers=4) as executor:
    futures = [executor.submit(generate_report, ticker) for ticker in tickers]

    for future in as_completed(futures):
        ticker, pdf_bytes = future.result()
        print(f"✅ {ticker}: {len(pdf_bytes)} bytes")
```

---

## Testing

### Run Tests

```bash
# Single ticker test
python tests/test_pdf_generation.py --ticker NVDA19

# Multi-ticker test
python tests/test_pdf_generation.py --multi
```

### Manual Inspection Checklist

Open generated PDF and verify:

- [ ] Title section displays correctly with company info
- [ ] Quick summary table has all 6 metrics
- [ ] Chart appears and is readable
- [ ] Key indicators annotations below chart
- [ ] Thai narrative renders correctly (no garbled characters)
- [ ] All emoji headers (📖 💡 🎯 ⚠️) display
- [ ] News references table formatted properly
- [ ] Sentiment colors correct (green=positive, red=negative)
- [ ] Overall score displays with correct color
- [ ] Category breakdown table complete
- [ ] Letter grades correct
- [ ] Disclaimer appears at bottom

---

## Conclusion

The PDF Report Generator provides a professional, comprehensive way to present ticker analysis results. With its structured format, visual appeal, and detailed scoring methodology, it serves as an excellent tool for investment research and client reporting.

**Key Benefits:**
- ✅ Professional presentation
- ✅ Comprehensive analysis in single document
- ✅ Portable format (PDF)
- ✅ Print-ready
- ✅ Easy to share via email/cloud storage

For questions or feature requests, please open an issue on GitHub.

---

**Generated:** 2025-11-01
**Test Results:** ✅ PASSED (NVDA19 report: 151.4 KB)
**Maintainer:** Development Team
