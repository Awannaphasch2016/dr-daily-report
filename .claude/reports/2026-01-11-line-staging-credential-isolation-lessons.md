# LINE Bot Staging Deployment - Lessons Learned

**Date**: 2026-01-11
**Context**: Deploying LINE bot to staging environment
**Outcome**: Successfully deployed after resolving credential isolation issue

---

## Executive Summary

Deployed LINE bot to staging environment. Encountered three distinct errors before success:
1. Missing environment variables (quick fix)
2. Wrong Lambda handler (quick fix)
3. **Wrong LINE credentials** (root cause: used dev credentials for staging)

The third error revealed a fundamental gap in our deployment principles: **external service credentials require per-environment isolation** because webhooks are per-channel, not per-deployment.

---

## Error Timeline

### Error 1: HTTP 500 - Missing Environment Variables
- **Symptom**: Lambda returned 500 with "Missing required environment variables: DYNAMODB_WATCHLIST_TABLE, PDF_STORAGE_BUCKET"
- **Root Cause**: Incomplete environment variable configuration during manual Lambda creation
- **Fix**: Updated Lambda environment with missing variables
- **Time to Resolve**: ~5 minutes
- **Principle Applied**: Principle #1 (Defensive Programming - fail fast on missing config)

### Error 2: HTTP 404 - Not Found
- **Symptom**: Lambda returned 404 instead of processing LINE webhook
- **Root Cause**: Default handler was `telegram_lambda_handler.handler` (FastAPI for Telegram) not `lambda_handler.lambda_handler` (LINE bot)
- **Fix**: Updated Lambda image config with correct handler command
- **Time to Resolve**: ~5 minutes
- **Principle Applied**: Principle #15 (Infrastructure-Application Contract)

### Error 3: LINE "Account Cannot Reply" Message
- **Symptom**: User received Thai auto-response: "ขอบคุณที่ส่งข้อความถึงเรา ต้องขออภัยเป็นอย่างยิ่งที่บัญชีนี้ไม่สามารถตอบข้อความใดๆ ได้"
- **Initial Hypothesis**: LINE Official Account Response mode not set to "Bot"
- **Investigation Path**:
  1. Verified Lambda returned HTTP 200 (Layer 1 - weak evidence)
  2. Checked CloudWatch logs - no errors (Layer 3 - observability)
  3. Realized: Lambda succeeding but replying to **wrong channel**
- **Actual Root Cause**: Used dev LINE credentials (`LINE_CHANNEL_ACCESS_TOKEN`, `LINE_CHANNEL_SECRET`) for staging Lambda
- **Why This Matters**: LINE webhooks are per-channel. Using dev credentials meant staging Lambda was trying to reply via dev channel, not staging channel.
- **Fix**: User provided staging LINE channel credentials, updated Lambda configuration
- **Time to Resolve**: ~30 minutes (including hypothesis exploration)

---

## Key Insight: External Service Credential Isolation

### The Pattern
External services with **per-channel webhooks** require **per-environment credentials**:

| Service | Webhook Scope | Credential Scope | Implication |
|---------|---------------|------------------|-------------|
| LINE | Per-channel | Per-channel | Each env needs own channel + credentials |
| Telegram | Per-bot | Per-bot | Each env needs own bot + token |
| Slack | Per-workspace | Per-app | Each env needs own app installation |
| Stripe | Per-account | Per-account | Test mode vs live mode keys |

### Why Copying Dev Credentials Fails
```
Dev Environment:
  LINE Channel A (Webhook → Dev Lambda)
  Credentials: Token A, Secret A

Staging Environment (WRONG):
  LINE Channel B (Webhook → Staging Lambda)
  Credentials: Token A, Secret A  ← PROBLEM!

  Result: Staging Lambda receives webhook from Channel B
          Staging Lambda replies using Token A (Channel A)
          User on Channel B receives nothing
          User on Channel A receives unexpected reply
```

### Why HTTP 200 Was Misleading
```
Evidence Layers:
  Layer 1 (Surface): HTTP 200 ✓ - Lambda executed successfully
  Layer 2 (Content): Response body valid ✓ - LINE SDK returned success
  Layer 3 (Observability): No errors in logs ✓ - Code path completed
  Layer 4 (Ground Truth): User received message? ✗ - FAILED

Gap: We stopped at Layer 3. Layer 4 (user actually receives message)
     requires testing from the user's perspective.
```

---

## Recommended Principle Updates

### New Principle #24: External Service Credential Isolation

External services with webhook-based integrations require **per-environment credentials**. Copying credentials across environments creates **silent routing failures** where operations succeed technically but fail functionally.

**Isolation checklist for new environments**:
1. Create new channel/bot/app in external service
2. Generate new credentials for that channel
3. Configure webhook URL to point to new environment
4. Store credentials in Doppler under environment-specific config
5. Verify end-to-end: user action → webhook → Lambda → reply → user receives

**Services requiring isolation**: LINE, Telegram, Slack, Discord, Stripe webhooks, GitHub Apps, OAuth providers.

**Anti-patterns**:
- Copying dev credentials to staging "to test quickly"
- Sharing webhook channels across environments
- Assuming HTTP 200 from external SDK = message delivered

### Update to Principle #2: Progressive Evidence Strengthening

Add explicit layer for external integrations:

```
Layer 4b (External Integration Ground Truth):
  - LINE: User receives message in chat
  - Telegram: Message appears in chat
  - Email: Message arrives in inbox
  - SMS: Message received on phone

  This layer cannot be verified programmatically in most cases.
  Requires manual verification or dedicated test accounts.
```

### Update to Principle #15: Infrastructure-Application Contract

Add to deployment order:
```
Deployment order (updated):
  (1) Update code
  (2) Create schema migration
  (3) Update Terraform env vars
  (4) Update Doppler secrets
  (5) **Provision external service credentials** ← NEW
  (6) Deploy migration FIRST
  (7) Deploy code
  (8) Verify ground truth
  (9) **Verify external integration E2E** ← NEW
```

---

## Testing Recommendations

### E2E Verification Checklist for External Services

```markdown
## LINE Bot E2E Verification
- [ ] Lambda returns HTTP 200 (Layer 1)
- [ ] CloudWatch logs show successful execution (Layer 3)
- [ ] LINE SDK reports message sent (Layer 2)
- [ ] **User receives message in LINE app** (Layer 4)
- [ ] Response content matches expected format

## Credential Isolation Verification
- [ ] `LINE_CHANNEL_ACCESS_TOKEN` is unique to this environment
- [ ] `LINE_CHANNEL_SECRET` is unique to this environment
- [ ] Webhook URL in LINE Developer Console matches this Lambda
- [ ] Test message from correct LINE channel triggers correct Lambda
```

---

## Artifacts Created

### Staging LINE Bot Infrastructure
- **Lambda**: `dr-daily-report-line-bot-staging`
- **Alias**: `live` (version 5)
- **Function URL**: `https://6x4fn5g45wtypsks7qa52py6ne0olvvl.lambda-url.ap-southeast-1.on.aws/`
- **IAM Role**: `dr-daily-report-line-bot-role-staging`

### Environment Variables (Final)
```json
{
  "AURORA_USER": "admin",
  "AURORA_DATABASE": "ticker_data",
  "AURORA_HOST": "dr-daily-report-aurora-dev.cluster-c9a0288e4hqm.ap-southeast-1.rds.amazonaws.com",
  "AURORA_PORT": "3306",
  "ENVIRONMENT": "staging",
  "LOG_LEVEL": "INFO",
  "DYNAMODB_WATCHLIST_TABLE": "dr-daily-report-telegram-watchlist-staging",
  "PDF_STORAGE_BUCKET": "line-bot-pdf-reports-755283537543",
  "PDF_BUCKET_NAME": "line-bot-pdf-reports-755283537543",
  "PDF_URL_EXPIRATION_HOURS": "24",
  "LINE_CHANNEL_ACCESS_TOKEN": "[staging-specific-token]",
  "LINE_CHANNEL_SECRET": "[staging-specific-secret]",
  "OPENROUTER_API_KEY": "[shared-across-envs]",
  "AURORA_PASSWORD": "[from-doppler]"
}
```

---

## Action Items

### Immediate
- [x] Staging LINE bot deployed and verified working

### Follow-up (Documentation Updates)
- [ ] Add Principle #24 to CLAUDE.md
- [ ] Update Principle #2 with external integration layer
- [ ] Update Principle #15 with external service credential step
- [ ] Create `.claude/skills/deployment/EXTERNAL_SERVICES.md` skill

### Process Improvements
- [ ] Add E2E verification step to deployment runbook
- [ ] Create checklist for provisioning new environments
- [ ] Document LINE Developer Console configuration requirements

---

## References

- [LINE Developer Console](https://developers.line.biz/console/)
- [LINE Messaging API Documentation](https://developers.line.biz/en/docs/messaging-api/)
- Related Principles: #1 (Defensive Programming), #2 (Progressive Evidence), #15 (Infrastructure Contract)
