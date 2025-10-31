# REST API Usage Guide

## Overview

The REST API endpoint provides programmatic access to ticker analysis functionality. It returns structured JSON data containing comprehensive analysis including fundamentals, technical indicators, news sentiment, and AI-generated Thai language reports.

## Architecture

```
API Gateway
├── /webhook (POST)      → lambda_handler.py → LineBot → Agent (returns Thai text to LINE)
└── /analyze (GET)       → api_handler.py → Agent (returns JSON with structured data)
```

## Endpoint

**URL:** `https://your-api-gateway-url.execute-api.region.amazonaws.com/stage/analyze`

**Method:** `GET`

**Query Parameters:**
- `ticker` (required): Ticker symbol (e.g., `AAPL`, `DBS19`, `UOB19`)

## Request Examples

### Using curl

```bash
# Basic request
curl "https://your-api-gateway-url.execute-api.region.amazonaws.com/stage/analyze?ticker=AAPL"

# With URL encoding
curl "https://your-api-gateway-url.execute-api.region.amazonaws.com/stage/analyze?ticker=DBS19"
```

### Using Python

```python
import requests

url = "https://your-api-gateway-url.execute-api.region.amazonaws.com/stage/analyze"
params = {"ticker": "AAPL"}

response = requests.get(url, params=params)
data = response.json()

print(f"Ticker: {data['ticker']}")
print(f"Price: ${data['ticker_data']['close']}")
print(f"Report: {data['report']}")
```

### Using JavaScript/Node.js

```javascript
const axios = require('axios');

const url = 'https://your-api-gateway-url.execute-api.region.amazonaws.com/stage/analyze';
const params = { ticker: 'AAPL' };

axios.get(url, { params })
  .then(response => {
    const data = response.data;
    console.log(`Ticker: ${data.ticker}`);
    console.log(`Price: $${data.ticker_data.close}`);
    console.log(`Report: ${data.report}`);
  })
  .catch(error => {
    console.error('Error:', error.response.data);
  });
```

## Response Format

### Success Response (200 OK)

```json
{
  "ticker": "AAPL",
  "ticker_data": {
    "date": "2024-01-15",
    "open": 178.50,
    "high": 180.00,
    "low": 178.00,
    "close": 179.25,
    "volume": 45000000,
    "market_cap": 2800000000000,
    "pe_ratio": 29.5,
    "eps": 6.05,
    "dividend_yield": 0.0052,
    "sector": "Technology",
    "industry": "Consumer Electronics",
    "company_name": "Apple Inc.",
    "forward_pe": 27.8,
    "revenue_growth": 0.085,
    "earnings_growth": 0.12,
    "profit_margin": 0.25,
    "target_mean_price": 185.50,
    "recommendation": "buy",
    "analyst_count": 45,
    "fifty_two_week_high": 195.00,
    "fifty_two_week_low": 165.00
  },
  "indicators": {
    "sma_20": 176.20,
    "sma_50": 172.50,
    "sma_200": 168.00,
    "rsi": 58.3,
    "macd": 1.25,
    "macd_signal": 1.15,
    "bb_upper": 182.00,
    "bb_middle": 176.20,
    "bb_lower": 170.40,
    "volume_sma": 42000000,
    "current_price": 179.25,
    "volume": 45000000,
    "uncertainty_score": 22.5,
    "atr": 2.15,
    "vwap": 178.90
  },
  "news": [
    {
      "title": "Apple Reports Strong Q4 Earnings",
      "link": "https://example.com/news/1",
      "publisher": "Reuters",
      "timestamp": "2024-01-14T10:30:00",
      "sentiment": "positive",
      "impact_score": 85.0
    },
    {
      "title": "Analyst Upgrades Apple Price Target",
      "link": "https://example.com/news/2",
      "publisher": "Bloomberg",
      "timestamp": "2024-01-13T14:20:00",
      "sentiment": "positive",
      "impact_score": 72.0
    }
  ],
  "news_summary": {
    "total_count": 5,
    "positive_count": 3,
    "negative_count": 1,
    "neutral_count": 1,
    "avg_impact_score": 68.5,
    "has_recent_news": true,
    "dominant_sentiment": "positive"
  },
  "report": "📖 **เรื่องราวของหุ้นตัวนี้**\nApple กำลังอยู่ในโมเมนต์ที่น่าสนใจ - ตลาดเสถียร (ความไม่แน่นอน 22/100) ATR แค่ 1.2% ราคาเคลื่อนไหวช้า แต่ราคา 2.4% เหนือ VWAP แสดงแรงซื้อชนะ ปริมาณซื้อขาย 1.3x ของเฉลี่ยแสดงนักลงทุนสนใจเพิ่มขึ้น หลังข่าวผลประกอบการที่เกินคาด [1]\n\n💡 **สิ่งที่คุณต้องรู้**\n..."
}
```

### Error Response (400 Bad Request)

**Missing ticker parameter:**
```json
{
  "error": "Missing required parameter: ticker",
  "message": "Please provide a ticker symbol as a query parameter. Example: /analyze?ticker=AAPL"
}
```

**Invalid ticker:**
```json
{
  "error": "ไม่พบข้อมูล ticker สำหรับ INVALID",
  "ticker": "INVALID"
}
```

### Error Response (500 Internal Server Error)

```json
{
  "error": "Internal server error",
  "message": "Error details here"
}
```

## Response Fields

### ticker_data

Fundamental and price data for the ticker.

| Field | Type | Description |
|-------|------|-------------|
| `date` | string | Date of the data (ISO format) |
| `open` | number | Opening price |
| `high` | number | High price |
| `low` | number | Low price |
| `close` | number | Closing price |
| `volume` | number | Trading volume |
| `market_cap` | number | Market capitalization |
| `pe_ratio` | number | Price-to-Earnings ratio |
| `eps` | number | Earnings per share |
| `dividend_yield` | number | Dividend yield (as decimal) |
| `sector` | string | Industry sector |
| `industry` | string | Industry |
| `company_name` | string | Company full name |
| `forward_pe` | number | Forward P/E ratio |
| `revenue_growth` | number | Revenue growth rate (as decimal) |
| `earnings_growth` | number | Earnings growth rate (as decimal) |
| `profit_margin` | number | Profit margin (as decimal) |
| `target_mean_price` | number | Average analyst target price |
| `recommendation` | string | Analyst recommendation (buy/hold/sell) |
| `analyst_count` | number | Number of analysts |
| `fifty_two_week_high` | number | 52-week high price |
| `fifty_two_week_low` | number | 52-week low price |

### indicators

Technical analysis indicators.

| Field | Type | Description |
|-------|------|-------------|
| `sma_20` | number | 20-day Simple Moving Average |
| `sma_50` | number | 50-day Simple Moving Average |
| `sma_200` | number | 200-day Simple Moving Average |
| `rsi` | number | Relative Strength Index (0-100) |
| `macd` | number | MACD line value |
| `macd_signal` | number | MACD signal line value |
| `bb_upper` | number | Bollinger Band upper |
| `bb_middle` | number | Bollinger Band middle |
| `bb_lower` | number | Bollinger Band lower |
| `volume_sma` | number | 20-day volume moving average |
| `current_price` | number | Current stock price |
| `volume` | number | Current trading volume |
| `uncertainty_score` | number | Pricing uncertainty score (0-100) |
| `atr` | number | Average True Range (volatility) |
| `vwap` | number | Volume Weighted Average Price |

### news

Array of high-impact news articles with sentiment analysis.

Each news item contains:
- `title` (string): News headline
- `link` (string): URL to full article
- `publisher` (string): News source
- `timestamp` (string): Publication time (ISO format)
- `sentiment` (string): "positive", "negative", or "neutral"
- `impact_score` (number): Impact score (0-100)

### news_summary

Aggregated news statistics.

| Field | Type | Description |
|-------|------|-------------|
| `total_count` | number | Total number of high-impact news items |
| `positive_count` | number | Number of positive news items |
| `negative_count` | number | Number of negative news items |
| `neutral_count` | number | Number of neutral news items |
| `avg_impact_score` | number | Average impact score |
| `has_recent_news` | boolean | True if any news is less than 24 hours old |
| `dominant_sentiment` | string | Overall sentiment trend |

### report

AI-generated comprehensive analysis report in Thai language. Includes:
- Market story and context
- Technical and fundamental insights
- Investment recommendation (BUY/SELL/HOLD)
- Risk warnings
- News references

## Supported Tickers

The API supports all tickers listed in `data/tickers.csv`. This includes:

- **Singapore**: DBS19, UOB19, OCBC, etc.
- **Japan**: 7203.T (Toyota), 6758.T (Sony), etc.
- **Hong Kong**: 0700.HK (Tencent), etc.
- **Vietnam**: VNM, FPT, etc.
- **Taiwan**: 2330.TW (Taiwan Semiconductor), etc.
- **US**: AAPL, TSLA, MSFT, etc.

## Rate Limits

- No explicit rate limits enforced by the API
- Limited by AWS Lambda concurrency limits
- Recommended: Max 10 requests/second per API key

## CORS Support

The API includes CORS headers, allowing cross-origin requests from web browsers:

```
Access-Control-Allow-Origin: *
```

## Error Handling

### Missing Ticker Parameter

```bash
curl "https://api.example.com/analyze"
# Returns 400 with error message
```

### Invalid Ticker

```bash
curl "https://api.example.com/analyze?ticker=INVALID"
# Returns 400 with error message indicating ticker not found
```

### Service Unavailable

If the service is temporarily unavailable, you'll receive a 500 error with details about the issue.

## AWS Lambda Configuration

### Handler Setup

- **Handler:** `src.api_handler.api_handler`
- **Runtime:** Python 3.11
- **Timeout:** 60 seconds (minimum recommended)
- **Memory:** 512 MB (minimum recommended)

### Environment Variables

Required:
- `OPENAI_API_KEY`: Your OpenAI API key

**Note:** Unlike the LINE bot handler, the API handler does NOT require LINE credentials.

### API Gateway Setup

1. Create REST API in API Gateway
2. Create resource: `/analyze`
3. Create method: `GET`
4. Integration type: Lambda Function
5. Select your Lambda function (ticker-api-handler)
6. Enable CORS if needed
7. Deploy API to a stage (e.g., `prod`)

### Example API Gateway Response

The API Gateway expects Lambda to return:

```python
{
    'statusCode': 200,
    'headers': {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*'
    },
    'body': '{"json": "string"}'
}
```

## Best Practices

1. **Caching**: Cache responses for 5-15 minutes to reduce API calls and costs
2. **Error Handling**: Always check `statusCode` before processing response
3. **Rate Limiting**: Implement client-side rate limiting to avoid overwhelming the service
4. **Ticker Validation**: Validate ticker symbols client-side before making requests
5. **Retry Logic**: Implement exponential backoff for 500 errors

## Example: Full Integration

```python
import requests
import time
from typing import Optional, Dict

class TickerAPI:
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.cache = {}
        self.cache_ttl = 900  # 15 minutes
    
    def analyze(self, ticker: str, use_cache: bool = True) -> Optional[Dict]:
        """Analyze a ticker and return structured data"""
        
        # Check cache
        if use_cache and ticker.upper() in self.cache:
            cached_data, cached_time = self.cache[ticker.upper()]
            if time.time() - cached_time < self.cache_ttl:
                return cached_data
        
        # Make API request
        try:
            response = requests.get(
                f"{self.base_url}/analyze",
                params={"ticker": ticker.upper()},
                timeout=60
            )
            response.raise_for_status()
            
            data = response.json()
            
            # Cache response
            if use_cache:
                self.cache[ticker.upper()] = (data, time.time())
            
            return data
            
        except requests.exceptions.RequestException as e:
            print(f"Error fetching analysis for {ticker}: {e}")
            return None
    
    def get_recommendation(self, ticker: str) -> Optional[str]:
        """Extract investment recommendation from report"""
        data = self.analyze(ticker)
        if not data:
            return None
        
        report = data.get('report', '')
        
        # Extract recommendation (BUY/SELL/HOLD)
        if 'BUY' in report.upper() or 'ซื้อ' in report:
            return 'BUY'
        elif 'SELL' in report.upper() or 'ขาย' in report:
            return 'SELL'
        else:
            return 'HOLD'

# Usage
api = TickerAPI("https://your-api-gateway-url.execute-api.region.amazonaws.com/stage")

# Get full analysis
data = api.analyze("AAPL")
if data:
    print(f"Price: ${data['ticker_data']['close']}")
    print(f"RSI: {data['indicators']['rsi']:.2f}")
    print(f"Recommendation: {api.get_recommendation('AAPL')}")
```

## Troubleshooting

### Slow Response Times

- Increase Lambda memory allocation (512MB → 1024MB)
- Check if it's a cold start (first request after inactivity)
- Verify network connectivity to Yahoo Finance and OpenAI

### Missing Data Fields

Some fields may be `null` if:
- Yahoo Finance doesn't provide the data
- The ticker is newly listed
- Market is closed

### JSON Parsing Errors

Ensure you're parsing the `body` field correctly:

```python
response = requests.get(url, params=params)
data = json.loads(response.text)  # Correct
# NOT: data = response.json()['body']  # Wrong
```

## Support

For issues or questions:
1. Check CloudWatch logs for detailed error messages
2. Verify Lambda function is deployed correctly
3. Test with a known ticker (e.g., "AAPL") first
4. Review API Gateway logs for request/response issues

## Cost Estimate

Per 1000 API requests:
- AWS Lambda: ~$0.20 (free tier: 1M requests/month)
- OpenAI API: ~$1.00 (GPT-4o at ~$0.001/report)
- API Gateway: ~$0.35 (free tier: 1M requests/month)
- **Total: ~$1.55/1000 requests**

## Performance

- **Cold start:** 3-5 seconds (first request after inactivity)
- **Warm execution:** 2-10 seconds (subsequent requests)
- **Response size:** ~5-50 KB JSON (depending on news count)
