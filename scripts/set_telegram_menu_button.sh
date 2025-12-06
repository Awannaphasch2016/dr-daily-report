#!/bin/bash
# Register Telegram Menu Button for TwinBar Mini App
#
# This script calls the Telegram Bot API to set the menu button (⚡)
# that appears in the bot chat interface. When clicked, it opens the TwinBar webapp.
#
# Usage:
#   ENV=dev doppler run -- ./scripts/set_telegram_menu_button.sh
#
# Requirements:
#   - TELEGRAM_BOT_TOKEN in Doppler secrets
#   - terraform/envs/${ENV}/terraform.tfvars with telegram_webapp_url

set -e  # Exit on error

# Validate environment
if [ -z "$ENV" ]; then
    echo "❌ Error: ENV variable not set (dev|staging|prod)"
    exit 1
fi

echo "📱 Setting Telegram Menu Button for environment: ${ENV}"

# Get bot token from Doppler
BOT_TOKEN=$(doppler secrets get TELEGRAM_BOT_TOKEN --plain 2>/dev/null)
if [ -z "$BOT_TOKEN" ]; then
    echo "❌ Error: TELEGRAM_BOT_TOKEN not found in Doppler"
    exit 1
fi

# Get webapp URL from terraform tfvars
TFVARS_FILE="terraform/envs/${ENV}/terraform.tfvars"
if [ ! -f "$TFVARS_FILE" ]; then
    echo "❌ Error: terraform.tfvars not found at $TFVARS_FILE"
    exit 1
fi

# Extract telegram_webapp_url from tfvars (format: telegram_webapp_url = "https://...")
WEBAPP_URL=$(grep 'telegram_webapp_url' "$TFVARS_FILE" | sed 's/.*"\(.*\)".*/\1/')
if [ -z "$WEBAPP_URL" ]; then
    echo "❌ Error: telegram_webapp_url not found in $TFVARS_FILE"
    exit 1
fi

echo "🌐 WebApp URL: $WEBAPP_URL"

# Call Telegram Bot API to set menu button
RESPONSE=$(curl -s -X POST "https://api.telegram.org/bot${BOT_TOKEN}/setChatMenuButton" \
  -H "Content-Type: application/json" \
  -d '{
    "menu_button": {
      "type": "web_app",
      "text": "Open TwinBar",
      "web_app": {"url": "'"${WEBAPP_URL}"'"}
    }
  }')

# Parse response
OK=$(echo "$RESPONSE" | jq -r '.ok')

if [ "$OK" = "true" ]; then
    echo "✅ Menu button registered successfully!"
    echo "📋 Response: $RESPONSE"
    echo ""
    echo "Next steps:"
    echo "  1. Open your Telegram bot"
    echo "  2. Look for the ⚡ button next to the message input"
    echo "  3. Click it to launch TwinBar"
else
    echo "❌ Failed to register menu button"
    echo "📋 Response: $RESPONSE"
    exit 1
fi
