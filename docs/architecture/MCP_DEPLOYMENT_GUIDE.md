# MCP Server Deployment Guide

**Status**: Infrastructure Ready ✅  
**Last Updated**: 2025-01-15

---

## Overview

This guide covers deploying and configuring MCP (Model Context Protocol) servers for the DR Daily Report agent. The first MCP server implemented is the SEC EDGAR server for fetching US stock filings.

---

## Architecture

```
LangGraph Agent (Lambda)
  ↓ HTTP/HTTPS
MCP Client (src/integrations/mcp_client.py)
  ↓
SEC EDGAR MCP Server (Lambda Function URL)
  ↓
SEC EDGAR API (data.sec.gov)
```

---

## Prerequisites

1. **Terraform Applied**: MCP server infrastructure deployed
2. **ECR Repository**: Container images pushed to ECR
3. **Doppler Access**: Environment variables configured
4. **AWS CLI**: Configured with appropriate permissions

---

## Deployment Steps

### Step 1: Deploy Infrastructure (Terraform)

```bash
cd terraform
terraform init -backend-config=envs/dev/backend.hcl
terraform plan -var-file=envs/dev/terraform.tfvars
terraform apply -var-file=envs/dev/terraform.tfvars
```

**Expected Outputs:**
- `sec_edgar_mcp_url`: Function URL for SEC EDGAR MCP server
- `sec_edgar_mcp_function_name`: Lambda function name

### Step 2: Deploy Lambda Function Code

```bash
# Build and push container image, then update Lambda
./scripts/deploy-mcp-server.sh dev sec-edgar
```

**What this does:**
1. Builds Docker image with MCP server handler
2. Pushes to ECR with versioned tag
3. Updates Lambda function code
4. Waits for deployment to complete
5. Outputs Function URL

### Step 3: Configure Environment Variables

**For Telegram API Lambda** (consumes MCP server):

```bash
# Set SEC EDGAR MCP URL in Doppler
doppler secrets set SEC_EDGAR_MCP_URL=https://<function-url>.lambda-url.ap-southeast-1.on.aws/mcp --project dr-daily-report --config dev

# Optional: Configure timeout
doppler secrets set MCP_TIMEOUT=30 --project dr-daily-report --config dev
```

**For MCP Server Lambda** (if needed):

```bash
# Set User-Agent for SEC EDGAR API
doppler secrets set SEC_EDGAR_USER_AGENT="dr-daily-report/1.0 (contact: support@dr-daily-report.com)" --project dr-daily-report --config dev
```

### Step 4: Verify Deployment

```bash
# Test MCP server directly
./scripts/verify_mcp_server.sh dev sec-edgar

# Test integration with agent
dr util report AAPL --trace
```

---

## Verification

### Test MCP Server Directly

```bash
# Get Function URL from Terraform
FUNCTION_URL=$(cd terraform && terraform output -raw sec_edgar_mcp_url)

# Test tools/list
curl -X POST "${FUNCTION_URL}/mcp" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/list",
    "id": 1
  }'

# Test tools/call
curl -X POST "${FUNCTION_URL}/mcp" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/call",
    "params": {
      "name": "get_latest_filing",
      "arguments": {
        "ticker": "AAPL",
        "form_type": "10-Q"
      }
    },
    "id": 1
  }'
```

### Expected Response (tools/list)

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "tools": [
      {
        "name": "get_latest_filing",
        "description": "Get the latest SEC filing...",
        "inputSchema": {
          "type": "object",
          "properties": {
            "ticker": {"type": "string"},
            "form_type": {"type": "string", "default": "10-Q"}
          },
          "required": ["ticker"]
        }
      }
    ]
  }
}
```

### Expected Response (tools/call)

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "content": [
      {
        "type": "text",
        "text": "{\"ticker\": \"AAPL\", \"form_type\": \"10-Q\", \"filing_date\": \"2024-01-15\", ...}"
      }
    ]
  }
}
```

---

## Troubleshooting

### Issue: MCP Server Returns 500 Error

**Check CloudWatch Logs:**
```bash
aws logs tail /aws/lambda/dr-daily-report-sec-edgar-mcp-server-dev --follow
```

**Common Causes:**
- SEC EDGAR API rate limiting (add delays between requests)
- Invalid ticker symbol (CIK lookup failed)
- Network timeout (increase Lambda timeout)

### Issue: Agent Can't Connect to MCP Server

**Verify Environment Variable:**
```bash
# Check if SEC_EDGAR_MCP_URL is set in Lambda environment
aws lambda get-function-configuration \
  --function-name dr-daily-report-telegram-api-dev \
  --query 'Environment.Variables.SEC_EDGAR_MCP_URL'
```

**Check Function URL:**
```bash
# Verify Function URL is accessible
curl -X POST "${SEC_EDGAR_MCP_URL}" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc": "2.0", "method": "tools/list", "id": 1}'
```

### Issue: Circuit Breaker Opens Frequently

**Symptoms:**
- MCP calls fail silently
- Logs show "Circuit breaker OPEN"

**Solutions:**
1. Check MCP server health (CloudWatch metrics)
2. Increase circuit breaker timeout (default: 60s)
3. Reduce failure threshold (default: 5 failures)
4. Fix underlying issue (SEC API, network, etc.)

---

## Cost Monitoring

### Expected Costs (Free Tier)

- **Lambda Invocations**: 1M requests/month free
- **Lambda Duration**: 400,000 GB-seconds/month free
- **Function URL**: No additional cost (included in Lambda)
- **SEC EDGAR API**: Free (public data)

**Estimated Monthly Cost**: $0 (within free tier for moderate usage)

### Monitoring

```bash
# Check Lambda invocations
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Invocations \
  --dimensions Name=FunctionName,Value=dr-daily-report-sec-edgar-mcp-server-dev \
  --start-time $(date -u -d '1 day ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 3600 \
  --statistics Sum
```

---

## Next Steps

1. **Add More MCP Servers**:
   - Alpaca MCP (financial data)
   - Financial Markets MCP (market data)

2. **Enhance SEC EDGAR Server**:
   - Implement proper HTML parsing (use BeautifulSoup)
   - Add XBRL parsing for structured data
   - Cache filings (90-day validity)

3. **Add Resilience**:
   - SQS async pattern for high-volume calls
   - Dead-letter queue for failed requests
   - CloudWatch alarms for failures

---

## References

- [MCP Implementation Status](./MCP_IMPLEMENTATION_STATUS.md)
- [AWS MCP Infrastructure Research](./AWS_MCP_INFRASTRUCTURE_RESEARCH.md)
- [MCP Client Documentation](../CODE_STYLE.md#mcp-integration)
