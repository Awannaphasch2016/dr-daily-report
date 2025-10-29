#!/bin/bash

echo "=============================================================================="
echo "🔧 LINE Webhook Setup Helper"
echo "=============================================================================="
echo ""

# Check if cloudflared is running
if ! pgrep -f "cloudflared" > /dev/null; then
    echo "⚠️  cloudflared is not running!"
    echo ""
    echo "Please run in another terminal:"
    echo "  cloudflared tunnel --url http://localhost:5500"
    echo ""
    exit 1
fi

echo "✅ cloudflared is running"
echo ""

# Try to get the tunnel URL from cloudflared logs
echo "Looking for tunnel URL..."
echo ""

# Instructions
echo "=============================================================================="
echo "📋 Setup Instructions"
echo "=============================================================================="
echo ""
echo "1. Find your cloudflared URL from the terminal where you ran:"
echo "   cloudflared tunnel --url http://localhost:5500"
echo ""
echo "   It should look like:"
echo "   https://xxxxx-xxx-xxx-xxx-xxx.trycloudflare.com"
echo ""
echo "2. Go to LINE Developers Console:"
echo "   https://developers.line.biz/console/"
echo ""
echo "3. Select your bot"
echo ""
echo "4. Go to 'Messaging API' tab"
echo ""
echo "5. Set Webhook URL to:"
echo "   https://YOUR-CLOUDFLARED-URL/webhook"
echo ""
echo "   Example:"
echo "   https://xxxxx-xxx-xxx-xxx-xxx.trycloudflare.com/webhook"
echo ""
echo "6. Click 'Update' and then 'Verify'"
echo ""
echo "7. Make sure 'Use webhook' is enabled"
echo ""
echo "8. Add the bot as a friend in LINE app"
echo ""
echo "9. Send a ticker symbol like 'DBS19' to test!"
echo ""
echo "=============================================================================="
echo ""
