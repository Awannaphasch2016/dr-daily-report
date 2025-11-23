# News Integration Feature

## Overview

The Daily Report LINE Bot now includes **high-impact news integration** from Yahoo Finance API. This feature automatically fetches, filters, and incorporates relevant news into the narrative reports with proper citations.

## Features

### 1. **Automatic News Fetching**
- Pulls latest news from Yahoo Finance API for each ticker
- Fetches up to 20 news items per ticker
- Works with all supported tickers (stocks, ETFs, etc.)

### 2. **Intelligent News Filtering**
- **Impact Scoring Algorithm** (0-100 scale):
  - High-impact keywords (earnings, merger, acquisition, etc.): +10 points each (max 40)
  - Recency: +20 if < 24h, +10 if < 7 days (max 20)
  - Sentiment strength: +15 if strong, +7 if moderate (max 15)
  - Publisher credibility (Reuters, Bloomberg, etc.): +10 (max 10)
  - Earnings-specific boost: +15 (max 15)

- **Default Filters**:
  - Minimum impact score: 40/100
  - Maximum news items: 5 per report
  - Only includes news that can meaningfully impact price

### 3. **Sentiment Analysis**
- Classifies news as **POSITIVE**, **NEGATIVE**, or **NEUTRAL**
- Based on keyword analysis of titles
- Used to provide balanced perspective in reports

### 4. **Seamless Report Integration**
- News context is provided to the AI analyst
- References are automatically inserted using [1], [2], [3] format
- News references added at the end of report with links
- Only references news when truly relevant to the analysis

## Architecture

```
┌─────────────┐
│   Agent     │
│  Workflow   │
└──────┬──────┘
       │
       ├─── 1. fetch_data (DataFetcher)
       │         │
       │         └─── Yahoo Finance Price/Fundamental Data
       │
       ├─── 2. fetch_news (NewsFetcher) ← NEW
       │         │
       │         ├─── Fetch all news (max 20)
       │         ├─── Calculate impact scores
       │         ├─── Filter high-impact (min 40/100)
       │         ├─── Classify sentiment
       │         └─── Generate summary statistics
       │
       ├─── 3. analyze_technical (TechnicalAnalyzer)
       │         │
       │         └─── Calculate indicators
       │
       └─── 4. generate_report (LLM)
                 │
                 ├─── Context includes:
                 │    - Technical data
                 │    - Fundamental data
                 │    - News with scores & sentiment ← NEW
                 │
                 ├─── Generate narrative with [1], [2] references
                 │
                 └─── Append news reference links ← NEW
```

## Code Structure

### New Files

#### `src/news_fetcher.py`
Main news fetching and filtering module.

**Key Classes:**
- `NewsFetcher`: Main class for news operations

**Key Methods:**
- `fetch_news(ticker, max_news)`: Fetch all news
- `filter_high_impact_news(ticker, min_score, max_news)`: Get filtered news
- `calculate_impact_score(news_item)`: Score news impact (0-100)
- `classify_sentiment(news_item)`: Classify as positive/negative/neutral
- `get_news_summary(news_items)`: Get statistics
- `format_news_for_report(news_items)`: Format for Thai report
- `get_news_references(news_items)`: Generate reference links

### Modified Files

#### `src/agent.py`
Updated agent workflow to include news.

**Key Changes:**
- Added `news_fetcher: NewsFetcher` instance
- Added `fetch_news` node to workflow graph
- Updated `AgentState` to include `news` and `news_summary`
- Modified `prepare_context()` to include news data
- Updated LLM prompt to reference news with [1], [2], etc.
- Append news references to final report

## Usage

### Basic Usage (Automatic)

The news integration works automatically. No code changes needed:

```python
from src.agent import TickerAnalysisAgent

agent = TickerAnalysisAgent()
report = agent.analyze_ticker("AAPL")
print(report)
```

**Output will include:**
```
📖 เรื่องราวของหุ้นตัวนี้
Apple กำลังในช่วงที่น่าสนใจ - หลังจากประกาศผลประกอบการที่แข็งแกร่ง [1]
ราคาทะลุ SMA 200 แสดงแรงซื้อกลับมา...

💡 สิ่งที่คุณต้องรู้
...อย่างไรก็ตาม ข่าวการลดลงของยอดขายใน China [2] อาจส่งผลกระทบ...

📎 แหล่งข้อมูลข่าว:
[1] Reuters: https://finance.yahoo.com/...
[2] Bloomberg: https://finance.yahoo.com/...
```

### Advanced Usage

#### Customize News Filters

```python
from src.news_fetcher import NewsFetcher

fetcher = NewsFetcher()

# Fetch with custom settings
high_impact = fetcher.filter_high_impact_news(
    ticker="AAPL",
    min_score=50.0,    # More strict (default: 40.0)
    max_news=3         # Fewer news (default: 5)
)

# Get summary
summary = fetcher.get_news_summary(high_impact)
print(f"Positive: {summary['positive_count']}")
print(f"Negative: {summary['negative_count']}")
print(f"Dominant: {summary['dominant_sentiment']}")
```

#### Access Raw News Data

```python
from src.news_fetcher import NewsFetcher

fetcher = NewsFetcher()

# Fetch all news (unfiltered)
all_news = fetcher.fetch_news("AAPL", max_news=20)

for news in all_news:
    print(f"Title: {news['title']}")
    print(f"Publisher: {news['publisher']}")
    print(f"Link: {news['link']}")
    print(f"Time: {news['timestamp']}")
```

## Testing

Run the comprehensive test suite:

```bash
python test_news_integration.py
```

**Test Suite includes:**
1. News Fetcher functionality test
2. Impact scoring algorithm test
3. Full agent integration test (optional)

## Configuration

### Adjust Impact Score Thresholds

Edit `src/agent.py`, line ~104:

```python
high_impact_news = self.news_fetcher.filter_high_impact_news(
    yahoo_ticker,
    min_score=40.0,  # Change this (0-100)
    max_news=5       # Change this (1-10 recommended)
)
```

### Modify High-Impact Keywords

Edit `src/news_fetcher.py`, line ~11-45:

```python
HIGH_IMPACT_KEYWORDS = [
    'earnings', 'revenue', 'profit',  # Add/remove keywords
    'merger', 'acquisition',
    # ... more keywords
]
```

### Adjust Sentiment Keywords

Edit `src/news_fetcher.py`, line ~47-68:

```python
NEGATIVE_KEYWORDS = [
    'loss', 'miss', 'decline',  # Customize
    # ...
]

POSITIVE_KEYWORDS = [
    'beat', 'surge', 'soar',    # Customize
    # ...
]
```

## Impact Scoring Details

### Scoring Components

| Component | Max Points | Criteria |
|-----------|------------|----------|
| Keywords | 40 | +10 per high-impact keyword match |
| Recency | 20 | +20 if < 24h, +10 if < 7 days |
| Sentiment | 15 | +15 if 2+ sentiment words, +7 if 1 |
| Publisher | 10 | +10 if major outlet (Reuters, Bloomberg, etc.) |
| Earnings | 15 | +15 if earnings-related |
| **Total** | **100** | Sum capped at 100 |

### Example Scoring

**News**: "Apple reports record quarterly earnings, beats analyst expectations"
- Keywords: "earnings" (+10), "beats" (+10) = 20 points
- Recency: 2 hours ago = 20 points
- Sentiment: "record" (+1), "beats" (+1) = 15 points (strong)
- Publisher: Reuters = 10 points
- Earnings: Yes = 15 points
- **Total: 80/100** ✅ High Impact

**News**: "Apple CEO discusses company vision in interview"
- Keywords: "ceo" (+10) = 10 points
- Recency: 5 days ago = 10 points
- Sentiment: Neutral = 0 points
- Publisher: TechCrunch = 0 points
- Earnings: No = 0 points
- **Total: 20/100** ❌ Low Impact (filtered out)

## Benefits

### 1. **Context-Aware Analysis**
The AI now has access to recent news when generating reports, providing more timely and relevant insights.

### 2. **Explainable Recommendations**
Investment recommendations can now reference specific news events, making them more credible.

### 3. **Time-Sensitive Trading**
Traders can see which news is impacting the stock right now, helping with short-term decisions.

### 4. **News Sentiment Integration**
The dominant news sentiment (positive/negative/neutral) provides additional context beyond just price data.

### 5. **Source Credibility**
Links to original sources allow users to verify information and read full articles.

## Limitations

### 1. **Yahoo Finance API Constraints**
- News availability varies by ticker
- Some tickers may have no news or limited news
- API rate limits may apply

### 2. **English-Only News**
- News titles are in English (from Yahoo Finance)
- Report narrative is in Thai
- May be language mixing in the report

### 3. **Sentiment Analysis Limitations**
- Keyword-based (not ML-based)
- May misclassify complex news
- Works best with clear positive/negative language

### 4. **No Historical News**
- Only fetches recent news (typically last 7-30 days)
- Cannot analyze news from >1 month ago

## Future Enhancements

### Potential Improvements

1. **ML-Based Sentiment Analysis**
   - Use transformer models (BERT, FinBERT) for better sentiment classification
   - Context-aware sentiment (not just keywords)

2. **Multi-Language Support**
   - Translate news to Thai automatically
   - Support Thai news sources

3. **News Categorization**
   - Classify news by type (earnings, M&A, regulatory, etc.)
   - Allow filtering by category

4. **Historical News Database**
   - Store news in SQLite for historical analysis
   - Track news impact on price movements

5. **News-Price Correlation**
   - Analyze which news types move prices the most
   - Adjust impact scores based on historical correlation

6. **Real-Time News Alerts**
   - Push notifications for high-impact news
   - Integrate with LINE Bot for instant alerts

## Troubleshooting

### Issue: No news appearing in reports

**Possible causes:**
1. Ticker has no news on Yahoo Finance
2. All news scored below threshold (40/100)
3. API connectivity issues

**Solutions:**
- Lower `min_score` threshold
- Check Yahoo Finance website manually
- Test with popular ticker (AAPL, TSLA, etc.)

### Issue: News not relevant to analysis

**Possible causes:**
1. Impact scoring needs tuning
2. Wrong keywords for this ticker/sector

**Solutions:**
- Increase `min_score` threshold
- Customize keywords for specific sector
- Adjust keyword weights in scoring algorithm

### Issue: Too many/too few news items

**Solutions:**
- Adjust `max_news` parameter (default: 5)
- Adjust `min_score` threshold
- Modify scoring algorithm weights

## Example Output

```
📖 เรื่องราวของหุ้นตัวนี้
Apple กำลังอยู่ในจังหวะที่น่าสนใจ - ตลาดเสถียรมาก ATR แค่ 1.2%
ราคาเคลื่อนไหวช้า ทะลุ SMA 200 ขึ้นมา ($175 vs $168) แสดงว่าแรงซื้อกลับมา
หลังข่าวผลประกอบการไตรมาสล่าสุดที่แข็งแกร่ง [1] แต่รายได้จาก China
ลดลง 8% ต้องระวัง [2]

💡 สิ่งที่คุณต้องรู้

ราคากำลังขึ้นแรง - ทะลุ SMA ทั้ง 3 เส้น ($175 vs $172 vs $168) และ
ที่สำคัญ ATR แค่ 1.2% ความผันผวนต่ำ แรงซื้อขายสมดุล หมายความว่า
นักลงทุนเห็นตรงกัน ไม่มีใครรีบขายออก เหมาะสะสมระยะยาว

แต่ระวัง - หลังจากนักวิเคราะห์ดาวน์เกรดจาก Buy เป็น Hold [3]
P/E 28.5 แพงขึ้นจากเดิม และแรงซื้อเริ่มอ่อนแรง ราคา 1.8% เหนือ VWAP
แสดงว่าคนซื้อวันนี้จ่ายแพงกว่าเฉลี่ย

นักวิเคราะห์ให้ราคาเป้า $180 สูงกว่าราคาปัจจุบัน $175 และปริมาณ
ซื้อขายสูง 1.4x ของค่าเฉลี่ย แสดงว่านักลงทุนสนใจเพิ่มขึ้น

🎯 ควรทำอะไรตอนนี้?

แนะนำ BUY - ตลาดเสถียร ราคาในเทรนด์ขาขึ้น ผลประกอบการดี [1]
แม้มีความกังวลเรื่อง China [2] แต่ราคาเป้ายังอยู่ด้านบน เหมาะ
เข้าซื้อสะสม ตั้ง stop-loss ที่ $170

⚠️ ระวังอะไร?

ระวังถ้าความผันผวนพุ่งขึ้น (ATR เกิน 2%) พร้อมกับข่าวลบเพิ่มเติม
จาก China แสดงว่าตลาดเริ่มกังวล ราคาอาจปรับฐานลงมาที่ $170

📎 แหล่งข้อมูลข่าว:
[1] Reuters: https://finance.yahoo.com/news/apple-q4-earnings-beat-123456
[2] Bloomberg: https://finance.yahoo.com/news/apple-china-revenue-decline-789012
[3] CNBC: https://finance.yahoo.com/news/analyst-downgrades-apple-345678
```

## Summary

The news integration feature enhances the Daily Report LINE Bot by:
- ✅ Automatically fetching relevant news from Yahoo Finance
- ✅ Filtering only high-impact news using intelligent scoring
- ✅ Classifying news sentiment (positive/negative/neutral)
- ✅ Seamlessly integrating news into narrative reports with [1], [2] references
- ✅ Providing source links for verification
- ✅ Giving AI analyst real-time context for better recommendations

This makes the reports more timely, credible, and actionable for day traders and investors.
