# Testing with Real LINE Bot

## ✅ Server Status: RUNNING

Your LINE bot server is now running and ready to receive messages!

- **Server**: http://localhost:5500
- **Status**: ✅ Healthy
- **Cloudflared Tunnel**: Running on your other terminal

---

## 🔧 Setup Steps

### 1. Get Your Cloudflared URL

In the terminal where you ran `cloudflared tunnel --url http://localhost:5500`, you should see output like:

```
+--------------------------------------------------------------------------------------------+
|  Your quick Tunnel has been created! Visit it at (it may take some time to be reachable): |
|  https://xxxxx-xxx-xxx-xxx-xxx.trycloudflare.com                                          |
+--------------------------------------------------------------------------------------------+
```

**Copy that URL!** (e.g., `https://xxxxx-xxx-xxx-xxx-xxx.trycloudflare.com`)

---

### 2. Configure LINE Webhook

1. Go to **LINE Developers Console**: https://developers.line.biz/console/

2. Select your **Messaging API Channel**

3. Go to **"Messaging API"** tab

4. Scroll to **"Webhook settings"**

5. Set **Webhook URL** to:
   ```
   https://YOUR-CLOUDFLARED-URL/webhook
   ```

   Example:
   ```
   https://xxxxx-xxx-xxx-xxx-xxx.trycloudflare.com/webhook
   ```

6. Click **"Update"**

7. Click **"Verify"** - You should see a success message

8. Make sure **"Use webhook"** is **ENABLED**

9. (Optional) Disable **"Auto-reply messages"** if you don't want the default replies

---

### 3. Test the Bot

1. **Add the bot as a friend** in LINE app:
   - Open LINE app
   - Go to the QR code from LINE Developers Console
   - Or search by bot ID

2. **Send a message** to the bot:
   ```
   DBS19
   ```

3. **Wait a few seconds** (5-15 seconds) for the bot to:
   - Fetch data from Yahoo Finance
   - Calculate technical indicators
   - Generate AI report using GPT-4o
   - Reply with comprehensive Thai report

4. **You should receive** a narrative-driven report like:
   ```
   📖 เรื่องราวของหุ้นตัวนี้

   DBS Group Holdings Ltd กำลังเดินไปในทิศทางที่มั่นคง...

   💡 สิ่งที่คุณต้องรู้

   การทะลุผ่านเส้น SMA 20, 50 และ 200...

   🎯 ควรทำอะไรตอนนี้?

   แนะนำให้ HOLD LONGER...

   ⚠️ ระวังอะไร?

   ควรจับตาดูการเติบโตของกำไร...
   ```

---

## 🧪 Test with Different Tickers

Try sending these messages to test:

### Valid Tickers:
- `DBS19` - DBS Bank (Singapore)
- `HONDA19` - Honda Motor (Japan)
- `TENCENT19` - Tencent (Hong Kong)
- `UOB19` - UOB Bank (Singapore)
- `NINTENDO19` - Nintendo (Japan)

### Invalid Ticker (to test error handling):
- `INVALID123` - Should return: "❌ เกิดข้อผิดพลาด: ไม่พบข้อมูล ticker"

---

## 📊 Monitor Server Logs

The server terminal will show real-time logs when messages come in:

```
================================================================================
📥 Received LINE Webhook
================================================================================
Time: Wed, 30 Oct 2024 04:00:00 GMT
Signature: xxxxxxxxxxxxxxxxxxxxx...
Body length: 234 bytes
User message: 'DBS19'

================================================================================
📤 Response Status
================================================================================
Status Code: 200
✅ Successfully processed
```

---

## 🐛 Troubleshooting

### Bot doesn't respond?

1. **Check server is running**:
   ```bash
   curl http://localhost:5500/health
   ```
   Should return: `{"status":"healthy",...}`

2. **Check cloudflared is running**:
   - Look at the terminal where you ran cloudflared
   - Should show tunnel is active

3. **Check LINE webhook configuration**:
   - Verify webhook URL ends with `/webhook`
   - Make sure "Use webhook" is enabled
   - Click "Verify" to test connection

4. **Check server logs**:
   - Look at the terminal running the bot server
   - Should see "📥 Received LINE Webhook" when messages arrive

### Bot responds with error?

1. **"ไม่พบข้อมูล ticker"**:
   - Ticker not in the list (see `tickers.csv`)
   - Try one of the supported tickers above

2. **"ไม่สามารถดึงข้อมูล"**:
   - Yahoo Finance might be temporarily unavailable
   - Try again in a few seconds

3. **No response at all**:
   - Check internet connection
   - Check OpenAI API key is valid
   - Check server logs for errors

---

## 🎯 What to Expect

### Response Time:
- First message: ~10-15 seconds (cold start)
- Subsequent messages: ~5-10 seconds

### Response Length:
- ~1000-1500 characters
- Single message (won't be split)

### Response Quality:
- ✅ Narrative-driven (tells stories with data)
- ✅ Investment recommendation (BUY/SELL/HOLD)
- ✅ Risk warnings
- ✅ Thai language
- ✅ Easy to read with emojis

---

## 🛑 Stop Server

When you're done testing:

1. Press `Ctrl+C` in the server terminal
2. Press `Ctrl+C` in the cloudflared terminal

Or kill the process:
```bash
pkill -f "python3 run_server.py"
pkill -f "cloudflared"
```

---

## ✅ Current Status

- **Server**: Running on http://localhost:5500
- **Cloudflared**: You need to provide the URL
- **LINE Bot**: Ready to receive messages
- **Environment**: All credentials configured

**Next**: Configure LINE webhook with your cloudflared URL and start testing! 🚀
