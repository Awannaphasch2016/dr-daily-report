# Telegram Bot Setup Guide

## Step 1: Create Bot via @BotFather

1. Open Telegram and search for `@BotFather`
2. Send `/newbot` command
3. Choose a name: `DR Daily Report` (display name)
4. Choose a username: `dr_daily_report_bot` (must end with `_bot`)
5. Copy the **Bot Token** (looks like `123456789:ABCdefGHI...`)

## Step 2: Enable Mini App (Web App)

1. Send `/mybots` to @BotFather
2. Select your bot
3. Click **Bot Settings** → **Menu Button**
4. Click **Configure Menu Button**
5. Enter:
   - **URL**: Your webapp URL (e.g., `https://your-domain.com/telegram-webapp/`)
   - **Text**: `📊 Open App`

Or use `/setmenubutton` command:
```
/setmenubutton
```
Then provide the webapp URL.

## Step 3: Configure Web App URL

For development:
```
https://your-ngrok-url.ngrok.io/telegram-webapp/
```

For production:
```
https://your-cloudfront-domain.cloudfront.net/
```

## Step 4: Set Bot Commands (Optional)

Send to @BotFather:
```
/setcommands
```

Then paste:
```
start - Start the bot
help - Show help message
report - Get ticker analysis
watchlist - View your watchlist
```

## Step 5: Add Environment Variables

Add to Doppler (or your secrets manager):

```bash
# Required
TELEGRAM_BOT_TOKEN=your_bot_token_here

# Optional (for advanced features)
TELEGRAM_WEBAPP_URL=https://your-webapp-url.com/
```

## Step 6: Update Lambda Environment

Update Terraform variables or Lambda console:

```hcl
# terraform/layers/03-apps/telegram-api/variables.tf
variable "telegram_bot_token" {
  type        = string
  sensitive   = true
  description = "Telegram Bot Token from @BotFather"
}
```

## Step 7: Test Bot

1. Search for your bot in Telegram
2. Send `/start`
3. Click the Menu Button to open the Mini App

## Troubleshooting

### Bot not responding
- Check bot token is correct
- Verify Lambda logs for errors

### Mini App not opening
- Ensure HTTPS URL (Telegram requires secure connection)
- Check CORS headers allow `https://telegram.org`
- Verify webapp files are deployed

### Authentication failing
- Verify `initData` is being sent from webapp
- Check HMAC validation in `telegram_auth.py`
- Ensure bot token matches in validation

## API Endpoints Summary

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/health` | GET | Health check |
| `/api/v1/search?q=NVDA` | GET | Search tickers |
| `/api/v1/report/{ticker}` | GET | Get analysis report |
| `/api/v1/rankings?category=top_gainers` | GET | Market rankings |
| `/api/v1/watchlist` | GET | Get user watchlist |
| `/api/v1/watchlist` | POST | Add to watchlist |
| `/api/v1/watchlist/{ticker}` | DELETE | Remove from watchlist |

## Headers

### Production (from Telegram)
```
X-Telegram-Init-Data: <initData from WebApp>
```

### Development (testing)
```
X-Telegram-User-Id: <user_id>
```
