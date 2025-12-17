# AWS MCP Quick Start

Quick setup guide for AWS MCP tools in Cursor IDE.

---

## One-Command Setup

```bash
just setup-mcp
```

This will:
1. ✅ Install `uv` package manager (if needed)
2. ✅ Verify Python installation
3. ✅ Create `.cursor/mcp.json` configuration
4. ✅ Check AWS credentials

---

## Manual Setup (3 Steps)

### Step 1: Install `uv`

**Windows:**
```powershell
Set-ExecutionPolicy RemoteSigned -Scope CurrentUser
irm https://astral.sh/uv/install.ps1 | iex
```

**Linux/macOS:**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Step 2: Create MCP Configuration

Copy `.cursor/mcp.json.template` to `.cursor/mcp.json`:

```bash
# Windows
copy .cursor\mcp.json.template .cursor\mcp.json

# Linux/macOS
cp .cursor/mcp.json.template .cursor/mcp.json
```

### Step 3: Configure AWS Credentials

```bash
aws configure
# Or set environment variables:
# AWS_ACCESS_KEY_ID=...
# AWS_SECRET_ACCESS_KEY=...
```

---

## Verify Setup

1. **Restart Cursor IDE** (required!)

2. **Ask Cursor:**
   ```
   What AWS MCP tools are available?
   ```

3. **Test AWS Access:**
   ```
   List all Lambda functions in ap-southeast-1
   ```

---

## What You Can Do

Once set up, you can ask Cursor to:

- ✅ **Deploy Lambda functions**: "Update telegram-api Lambda with image sha-abc123"
- ✅ **Query CloudWatch logs**: "Show errors from telegram-api Lambda in the last hour"
- ✅ **Manage S3 buckets**: "List all objects in the PDF bucket"
- ✅ **Inspect DynamoDB**: "Show all items in the watchlist table"
- ✅ **Check API Gateway**: "List all API Gateway endpoints"
- ✅ **And more AWS services...**

---

## Troubleshooting

**"uv: command not found"**
→ Run setup script again or install manually

**"AWS credentials not found"**
→ Run `aws configure` or set environment variables

**MCP tools not appearing**
→ Restart Cursor IDE completely

**"Permission denied" errors**
→ Check AWS IAM permissions (see `docs/AWS_SETUP.md`)

---

## Full Documentation

See [MCP Setup Guide](MCP_SETUP.md) for detailed instructions and troubleshooting.

