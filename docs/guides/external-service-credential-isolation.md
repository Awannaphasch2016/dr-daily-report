# External Service Credential Isolation Guide

**Principle #24** | External services with webhook-based integrations require per-environment credentials.

---

## Overview

### Core Problem
External services like LINE, Telegram, and Slack use **per-channel webhooks**. When you copy credentials from one environment to another, the new environment's Lambda responds via the **wrong channel**, causing silent failures where HTTP returns 200 but users receive nothing.

### Key Insight
Credentials for webhook-based services are **context-bound, not portable**. They appear copyable (just strings) but are actually tied to specific channels/accounts.

---

## The Pattern

### Webhook Credential Binding

```
┌─────────────────────────────────────────────────────────────┐
│                    LINE Bot Architecture                     │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Dev Environment:                                           │
│    LINE Channel A ──webhook──> Dev Lambda                   │
│    Credentials: Token A, Secret A                           │
│    Reply: Token A → Channel A → User on Channel A ✓         │
│                                                             │
│  Staging Environment (WRONG):                               │
│    LINE Channel B ──webhook──> Staging Lambda               │
│    Credentials: Token A, Secret A  ← COPIED FROM DEV!       │
│    Reply: Token A → Channel A → User on Channel A           │
│    User on Channel B receives nothing ✗                     │
│                                                             │
│  Staging Environment (CORRECT):                             │
│    LINE Channel B ──webhook──> Staging Lambda               │
│    Credentials: Token B, Secret B  ← NEW FOR STAGING        │
│    Reply: Token B → Channel B → User on Channel B ✓         │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Services Requiring Isolation

| Service | Webhook Scope | Credential Scope | Isolation Required |
|---------|---------------|------------------|-------------------|
| LINE | Per-channel | Per-channel | YES |
| Telegram | Per-bot | Per-bot | YES |
| Slack | Per-workspace | Per-app | YES |
| Discord | Per-server | Per-bot | YES |
| Stripe | Per-account | Per-account | YES (test vs live) |
| GitHub Apps | Per-installation | Per-app | YES |

### Services That CAN Be Shared

| Service | Why Shareable |
|---------|---------------|
| OpenRouter | Stateless API, no webhooks |
| Aurora | Database connection, no callbacks |
| S3 | Storage, no callbacks |
| CloudWatch | Logging, no callbacks |

---

## Environment Provisioning Checklist

When creating a new environment, use this checklist for external services:

### Per-Environment Isolation Checklist

```markdown
## External Service Setup for {environment}

### LINE Bot (if applicable)
- [ ] Create new LINE channel in Developer Console
- [ ] Issue channel access token (long-lived)
- [ ] Copy channel secret
- [ ] Configure webhook URL: https://{lambda-url}/
- [ ] Set webhook to "Use webhook" mode
- [ ] Store in Doppler:
  - [ ] LINE_CHANNEL_ACCESS_TOKEN
  - [ ] LINE_CHANNEL_SECRET

### Telegram Bot (if applicable)
- [ ] Create new bot via @BotFather
- [ ] Copy bot token
- [ ] Set webhook via API: setWebhook
- [ ] Store in Doppler:
  - [ ] TELEGRAM_BOT_TOKEN

### Verification
- [ ] Lambda responds HTTP 200
- [ ] CloudWatch logs show execution
- [ ] **User receives message in app** (ground truth!)
```

---

## Verification: Why HTTP 200 Is Insufficient

### Progressive Evidence for External Services

| Layer | Evidence | What It Proves | Sufficient? |
|-------|----------|----------------|-------------|
| 1 | HTTP 200 | Lambda executed | NO |
| 2 | Response body valid | SDK accepted request | NO |
| 3 | No errors in CloudWatch | Code path completed | NO |
| **4** | **User receives message** | **Credentials correct** | **YES** |

### The Verification Gap

```
Layer 1-3 pass, Layer 4 fails when:
  - Wrong channel credentials (today's incident)
  - Webhook not configured
  - Channel suspended/disabled
  - Rate limiting
  - User blocked bot
```

**Always verify Layer 4 for external services.**

---

## Real Incident: LINE Staging (2026-01-11)

### Timeline

1. **13:00** - Created staging Lambda by copying dev config
2. **13:15** - Tested with curl, got HTTP 200 ✓
3. **13:20** - Checked CloudWatch, no errors ✓
4. **13:30** - User tested, received auto-response "Account cannot reply"
5. **14:00** - Diagnosed: using dev LINE credentials for staging
6. **14:30** - Created staging LINE channel, updated credentials
7. **14:45** - User tested again, received correct response ✓

### Root Cause

```
Staging Lambda Configuration:
  LINE_CHANNEL_ACCESS_TOKEN = {dev_token}  ← WRONG
  LINE_CHANNEL_SECRET = {dev_secret}        ← WRONG

Result:
  1. User sends message to Staging LINE channel
  2. Webhook calls Staging Lambda
  3. Lambda processes correctly
  4. Lambda replies using Dev token
  5. Reply goes to Dev channel, not Staging
  6. User on Staging channel receives nothing
  7. LINE shows auto-response "Account cannot reply"
```

### Lesson Learned

External service credentials are **context-bound** (tied to specific channel), not **portable** (can copy between environments).

---

## Integration with Contextual Transfer Framework

This principle is derived from the [Contextual Transfer Framework](../../.claude/abstractions/workflow-2026-01-11-contextual-transfer-framework.md).

### Step 5 (UNTANGLE) for External Services

When provisioning new environments, explicitly categorize:

**Portable** (can copy):
- Lambda configuration (handler, memory, timeout)
- IAM policy shapes
- Environment variable keys
- OpenRouter API key (stateless)
- Aurora connection strings (if shared DB)

**Context-Bound** (must isolate):
- LINE_CHANNEL_ACCESS_TOKEN
- LINE_CHANNEL_SECRET
- TELEGRAM_BOT_TOKEN
- SLACK_BOT_TOKEN
- Resource names (add env suffix)
- Function URLs (auto-generated)

---

## Anti-Patterns

### 1. Copying All Environment Variables
```bash
# WRONG: Copy all env vars from dev to staging
aws lambda get-function-configuration --function-name dev-lambda \
  | jq '.Environment.Variables' \
  | aws lambda update-function-configuration --function-name staging-lambda --environment
```

**Why it fails**: Copies context-bound credentials along with portable ones.

**Correct approach**: Explicitly identify which variables are portable vs context-bound.

### 2. Skipping E2E Verification
```bash
# WRONG: Assume deployment succeeded because Lambda responds
curl -X POST https://staging-lambda-url/ -d '{"test": true}'
# HTTP 200 → "Success!"
```

**Why it fails**: HTTP 200 doesn't prove messages reach users.

**Correct approach**: Have a human test the actual user flow.

### 3. Sharing Test Accounts
```bash
# WRONG: Use same LINE channel for dev and staging
Dev webhook URL → https://dev-lambda/
Staging webhook URL → https://staging-lambda/  # Same channel!
```

**Why it fails**: One channel can only have one webhook URL.

**Correct approach**: Create separate channel per environment.

---

## Related Principles

| Principle | Relationship |
|-----------|-------------|
| #1 Defensive Programming | Validate credentials at startup |
| #2 Progressive Evidence | Layer 4 verification for external services |
| #13 Secret Management | Per-environment Doppler configs |
| #15 Infrastructure Contract | External credentials are part of contract |

---

## See Also

- [LINE Staging Lessons](../../.claude/reports/2026-01-11-line-staging-credential-isolation-lessons.md) - Full incident report
- [Contextual Transfer Framework](../../.claude/abstractions/workflow-2026-01-11-contextual-transfer-framework.md) - Parent abstraction
- [/provision-env](../../.claude/commands/provision-env.md) - Environment provisioning command
- [Doppler Config Guide](../deployment/DOPPLER_CONFIG.md) - Secret management

---

*Guide version: 2026-01-11*
*Principle: #24 External Service Credential Isolation*
*Status: Active - derived from LINE staging incident*
