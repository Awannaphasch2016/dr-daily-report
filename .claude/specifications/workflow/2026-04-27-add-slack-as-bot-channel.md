---
title: Add Slack as bot channel
focus: workflow
date: 2026-04-27
status: draft
tags: [integration, slack, notification-channel, multi-app]
---

# Workflow Specification: Add Slack as bot channel

## Goal

Add Slack as a third delivery channel alongside the existing LINE Bot (legacy)
and Telegram Mini App. Bot posts ticker reports and/or alerts to Slack via an
**incoming webhook URL** stored in Doppler (`rag-chatbot-worktree` / `dev`).

**Scope assumption**: Slack incoming webhooks are **outbound-only** (we POST,
Slack receives). True two-way "interaction" (slash commands, message events)
needs a separate Slack app + Events API endpoint — flagged as open question.

---

## Workflow Diagram

```
┌──────────────────── Existing daily pipeline ────────────────────┐
│ EventBridge → ticker_fetcher → Step Functions → report_worker   │
│                                                       │          │
│                                                       ↓          │
│                                            ┌──────────────────┐  │
│                                            │ Delivery Fanout  │  │
│                                            └─────┬────────────┘  │
└──────────────────────────────────────────────────┼───────────────┘
                                                   │
                ┌──────────────────┬───────────────┼───────────────┐
                ↓                  ↓               ↓               ↓
          [LINE reply]     [Telegram cache]  [NEW: Slack]   [PDF in S3]
                                                   │
                                                   ↓
                                       Slack incoming webhook
                                       (channel chosen at URL creation)
```

**Trigger candidates** (pick one or more — open question):
1. Per-ticker on daily pipeline completion (47× messages/day — noisy)
2. Daily summary digest (1× message/day with all tickers)
3. On-demand report request from Telegram/LINE (mirror to Slack)
4. Errors/alerts from CloudWatch (ops channel)

---

## Nodes

### Node 1: SlackNotifier (new)

**Purpose**: Post a formatted Slack message to the configured webhook URL.

**Location**: `src/integrations/slack.py` (new — mirrors `src/integrations/line_bot.py`)

**Input**:
```python
{
  "ticker": "AAPL",
  "report_summary": "...",           # short text, ≤ 3000 chars
  "pdf_url": "https://...",          # 24h presigned S3 URL
  "metrics": { "rsi": 45.2, "trend": "bullish" }
}
```

**Processing**:
1. Read `SLACK_WEBHOOK_URL` from env (loaded once at Lambda init — Principle #23)
2. Build Slack Block Kit payload (header + summary + button to PDF)
3. POST to webhook URL with retry/backoff (`tenacity`, 3 attempts)
4. On 4xx (bad payload), log and surface error; do not retry
5. On 5xx / network, retry with exponential backoff; mark job warning if exhausted

**Output**:
```python
{
  "delivered": True,
  "slack_response_status": 200,
  "duration_ms": 142
}
```

**Error conditions**:
- `403 invalid_token` → webhook revoked → fail loudly (Principle #1), alarm
- `429 rate_limited` → respect `Retry-After`, queue for later
- `5xx` → retry up to 3× with backoff
- Network timeout → same as 5xx

---

### Node 2: Delivery Fanout (modify existing report_worker)

**Purpose**: Add Slack as one branch of post-generation fanout. Existing LINE
and Telegram caching stays untouched.

**Location**: end of `src/report_worker_handler.py` after PDF upload + Aurora cache.

**Pseudo**:
```python
if SLACK_ENABLED and not is_user_initiated_request:
    SlackNotifier.send(ticker, summary, pdf_url, metrics)
```

**Feature flag**: `SLACK_ENABLED` env var (default false in dev/staging until
verified, true in prod after testing). Matches existing
`var.use_report_pipeline` pattern in `terraform/report_pipeline.tf`.

---

## State Management

No new persistent state in Aurora/DynamoDB for v1. If we later add Slack-side
delivery tracking (was-delivered, message ts), it can live in DynamoDB
alongside the job table.

---

## Configuration (Principle #23)

| Variable | Where | Source |
|----------|-------|--------|
| `SLACK_WEBHOOK_URL` | Doppler secret | `doppler --project rag-chatbot-worktree --config dev` ⚠️ see Q1 |
| `SLACK_ENABLED` | Doppler env var | per-env: dev=false, staging=false, prod=true (after rollout) |
| `SLACK_DEFAULT_CHANNEL` | (implicit in webhook URL) | n/a — channel is fixed at webhook creation |

**Wiring**: extend `terraform/async_report.tf` to inject these into the
`report_worker` Lambda env (mirror Doppler→Lambda pattern already used for
OpenRouter/Langfuse keys).

---

## Error Handling

- Slack delivery is **best-effort**: a Slack failure must NOT fail the report
  generation job. Aurora/S3 are the source of truth; Slack is a notification.
- Log Slack outcome at INFO (success) / WARNING (transient failure) / ERROR
  (auth failure) per Principle #18.
- Add CloudWatch alarm on `SlackDeliveryFailureRate > 5%` over 5 min.

---

## Performance

- Webhook POST: ~150 ms typical, 1 s p99
- Adds <2% to report_worker duration; acceptable
- Retry budget: 3 attempts × 2 s = 6 s worst case (well under Lambda 120 s timeout)

---

## Open Questions

- [ ] **Q1: Doppler project name.** Webhook URL location says
  `rag-chatbot-worktree` — but this repo's other secrets live under a different
  Doppler project (likely `dr-daily-report` or `openclaw` based on
  `scripts/generate_c4_diagrams.py:401`). Confirm: is the webhook genuinely in
  `rag-chatbot-worktree` (cross-project secret), or should it be copied into
  this repo's Doppler project?
- [ ] **Q2: One-way vs two-way.** Incoming webhook = outbound-only. Do we also
  need to receive Slack slash commands / @mentions (e.g. `/dr AAPL`)? That
  requires a separate Slack app + Events API Lambda + signature verification.
  If yes, scope this as a Phase 2 spec.
- [ ] **Q3: Trigger.** Which of the four trigger candidates above? Default
  recommendation: start with **#3 on-demand mirroring** (lowest noise, easiest
  rollback), then add **#2 daily digest** if useful.
- [ ] **Q4: Targeting.** One channel for all users/tickers, or per-user
  channels? Incoming webhooks are 1:1 with channels — multi-channel needs a
  proper Slack app with `chat.postMessage`.
- [ ] **Q5: Message format.** Plain text, Block Kit blocks, or both? Block
  Kit gives buttons (e.g. "Open PDF") but is more code.
- [ ] **Q6: AWS resource tagging.** New `App = slack-bot` tag, or fold into
  existing `App = shared`? The LINE/Telegram split uses dedicated tags.
- [ ] **Q7: Rate limits.** Slack incoming webhooks are limited to ~1/sec per
  channel. The 47-ticker fanout needs throttling if we go with trigger #1.

---

## Next Steps

- [ ] Resolve Q1 (Doppler project) — likely a 30-second check with the user
- [ ] Resolve Q2 (one-way scope) — defines whether this is one PR or two
- [ ] Pick Q3 trigger — defines insertion point in report_worker
- [ ] Spike: send one hand-crafted webhook payload with `curl` to confirm URL works
- [ ] If approved, `EnterPlanMode` for full implementation plan covering:
  - `src/integrations/slack.py` module
  - Hook into `src/report_worker_handler.py`
  - Terraform env-var wiring
  - Tests (unit + integration with `responses` library for HTTP mocking)
  - Feature-flag rollout: dev → staging (smoke test) → prod
