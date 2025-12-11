# MCP Server Deployment Checklist

**Environment**: [ ] dev [ ] staging [ ] prod  
**Date**: _______________  
**Deployed By**: _______________

---

## Pre-Deployment

- [ ] Terraform state initialized (`terraform init`)
- [ ] Terraform plan reviewed (`terraform plan`)
- [ ] ECR repository exists and accessible
- [ ] Docker installed and configured
- [ ] AWS CLI configured with appropriate permissions
- [ ] Doppler access configured for environment

---

## Infrastructure Deployment

### Step 1: Apply Terraform

```bash
cd terraform
terraform apply -var-file=envs/dev/terraform.tfvars
```

**Verify:**
- [ ] `sec_edgar_mcp_function_name` output exists
- [ ] `sec_edgar_mcp_url` output exists
- [ ] Lambda function created in AWS Console
- [ ] Function URL created and accessible

### Step 2: Deploy Lambda Code

```bash
./scripts/deploy-mcp-server.sh dev sec-edgar
```

**Verify:**
- [ ] Docker image built successfully
- [ ] Image pushed to ECR
- [ ] Lambda function updated
- [ ] Function URL matches Terraform output

---

## Configuration

### Step 3: Set Environment Variables

**For Telegram API Lambda** (consumes MCP):

```bash
# Get Function URL from Terraform
FUNCTION_URL=$(cd terraform && terraform output -raw sec_edgar_mcp_url)

# Set in Doppler
doppler secrets set SEC_EDGAR_MCP_URL="${FUNCTION_URL}/mcp" \
  --project dr-daily-report \
  --config dev

# Optional: Set timeout
doppler secrets set MCP_TIMEOUT=30 \
  --project dr-daily-report \
  --config dev
```

**Verify:**
- [ ] `SEC_EDGAR_MCP_URL` set in Doppler
- [ ] Variable visible in Lambda environment (after redeploy)
- [ ] URL format: `https://*.lambda-url.*.on.aws/mcp`

---

## Verification

### Step 4: Test MCP Server Directly

```bash
./scripts/verify_mcp_server.sh dev sec-edgar
```

**Verify:**
- [ ] `tools/list` returns tool definitions
- [ ] `tools/call` returns filing data for AAPL
- [ ] No errors in CloudWatch logs

### Step 5: Test Integration with Agent

```bash
# Generate report for US ticker
dr util report AAPL --trace

# Check logs for SEC filing data
aws logs tail /aws/lambda/dr-daily-report-telegram-api-dev --follow
```

**Verify:**
- [ ] Agent workflow includes `fetch_sec_filing` node
- [ ] SEC filing data appears in report context
- [ ] No MCP connection errors

---

## Post-Deployment

### Step 6: Monitor

**Check CloudWatch Metrics:**
- [ ] Lambda invocations > 0
- [ ] No errors in logs
- [ ] Duration < timeout (30s)

**Check Costs:**
- [ ] Lambda invocations within free tier
- [ ] No unexpected charges

### Step 7: Documentation

- [ ] Update deployment runbook with MCP URL
- [ ] Document any issues encountered
- [ ] Update team on MCP server availability

---

## Rollback Plan

If deployment fails:

1. **Revert Environment Variable:**
   ```bash
   doppler secrets delete SEC_EDGAR_MCP_URL --project dr-daily-report --config dev
   ```

2. **Disable MCP Node** (if needed):
   - Remove `fetch_sec_filing` from workflow graph temporarily
   - Or: Keep node but ensure graceful fallback (already implemented)

3. **Destroy Infrastructure** (if needed):
   ```bash
   cd terraform
   terraform destroy -var-file=envs/dev/terraform.tfvars
   ```

---

## Troubleshooting

### Issue: Function URL returns 500

**Check:**
- CloudWatch logs: `/aws/lambda/dr-daily-report-sec-edgar-mcp-server-dev`
- Lambda function configuration
- IAM permissions

### Issue: Agent can't connect

**Check:**
- Environment variable `SEC_EDGAR_MCP_URL` set correctly
- Function URL accessible from Lambda VPC (if applicable)
- Network connectivity

### Issue: SEC API errors

**Check:**
- User-Agent header configured
- Rate limiting (add delays if needed)
- Ticker symbol valid (US-listed only)

---

**Deployment Status**: [ ] Complete [ ] Partial [ ] Failed  
**Issues Encountered**: _________________________________  
**Next Steps**: _________________________________________
