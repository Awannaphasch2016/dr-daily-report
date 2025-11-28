# Telegram Mini App API

REST API backend for the DR Daily Report Telegram Mini App.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Telegram Mini App                            │
│  (HTML/CSS/JS + Telegram WebApp SDK)                            │
└────────────────────────────┬────────────────────────────────────┘
                             │ HTTPS
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    API Gateway (HTTP API)                        │
│  ou0ivives1.execute-api.ap-southeast-1.amazonaws.com            │
└────────────────────────────┬────────────────────────────────────┘
                             │ Lambda Proxy
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Lambda Function                               │
│  dr-daily-report-telegram-api-dev                               │
│  (FastAPI + Mangum adapter)                                     │
└────────────────────────────┬────────────────────────────────────┘
                             │
           ┌─────────────────┼─────────────────┐
           ▼                 ▼                 ▼
    ┌─────────────┐   ┌─────────────┐   ┌─────────────┐
    │  DynamoDB   │   │    S3       │   │  yfinance   │
    │  Watchlist  │   │  PDF Cache  │   │  API        │
    └─────────────┘   └─────────────┘   └─────────────┘
```

## API Endpoints

### Health Check
```
GET /api/v1/health
```
Response: `{"status": "ok", "version": "1.0.0"}`

### Search Tickers
```
GET /api/v1/search?q=NVDA&limit=10
```
Search tickers by symbol or company name.

### Get Report
```
GET /api/v1/report/{ticker}
```
Generate AI-powered analysis report for a ticker.

### Get Rankings
```
GET /api/v1/rankings?category=top_gainers&limit=10
```
Categories: `top_gainers`, `top_losers`, `volume_surge`, `trending`

### Watchlist (Authenticated)
```
GET    /api/v1/watchlist          # Get user's watchlist
POST   /api/v1/watchlist          # Add ticker {"ticker": "NVDA19"}
DELETE /api/v1/watchlist/{ticker} # Remove ticker
```

## Authentication

### Production (Telegram WebApp)
```
X-Telegram-Init-Data: <initData from Telegram.WebApp>
```
HMAC-SHA256 validated against bot token.

### Development
```
X-Telegram-User-Id: <any_user_id>
```
Simple header for testing.

## Local Development

```bash
# Start FastAPI server
just dev-api

# Or with Doppler
dr --doppler dev api-server

# Test endpoints
curl http://localhost:8001/api/v1/health
curl http://localhost:8001/api/v1/search?q=NVDA
```

## Deployment

```bash
# Build Docker image
docker build -f Dockerfile.lambda.container -t dr-daily-report-lambda:latest .

# Push to ECR
aws ecr get-login-password --region ap-southeast-1 | docker login --username AWS --password-stdin <account>.dkr.ecr.ap-southeast-1.amazonaws.com
docker tag dr-daily-report-lambda:latest <account>.dkr.ecr.ap-southeast-1.amazonaws.com/dr-daily-report-lambda-dev:latest
docker push <account>.dkr.ecr.ap-southeast-1.amazonaws.com/dr-daily-report-lambda-dev:latest

# Update Lambda
aws lambda update-function-code --function-name dr-daily-report-telegram-api-dev --image-uri <image-uri>
```

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `OPENROUTER_API_KEY` | OpenRouter API key | Yes |
| `TELEGRAM_BOT_TOKEN` | Telegram bot token from @BotFather | Yes |
| `DYNAMODB_WATCHLIST_TABLE` | DynamoDB table name | Yes |
| `DYNAMODB_CACHE_TABLE` | Cache table name | Yes |
| `PDF_STORAGE_BUCKET` | S3 bucket for PDFs | Yes |
| `ENVIRONMENT` | dev/staging/prod | No |
| `LOG_LEVEL` | DEBUG/INFO/WARNING | No |

## Error Handling

All errors follow the format:
```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human readable message"
  }
}
```

Error codes:
- `INVALID_REQUEST` - Bad input or missing parameters
- `TICKER_NOT_SUPPORTED` - Unknown ticker symbol
- `AUTH_FAILED` - Authentication failure
- `INTERNAL_ERROR` - Server error

## Rate Limits

API Gateway default limits:
- 50 requests/second (steady state)
- 100 requests burst

yfinance API may rate limit during heavy usage.

## Monitoring

CloudWatch logs: `/aws/lambda/dr-daily-report-telegram-api-dev`

Key metrics:
- Lambda duration
- Error count
- Cold start frequency
- DynamoDB read/write capacity
