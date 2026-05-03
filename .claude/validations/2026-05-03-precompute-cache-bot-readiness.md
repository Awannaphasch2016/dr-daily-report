---
name: Precompute cache populated for 2026-05-03 — bot can serve text but not PDF
description: Validates whether today's 5 AM BKK precompute populated the bot-readable cache (Aurora `precomputed_reports`)
type: validation
date: 2026-05-03
---

# Validation: Precompute cache for 2026-05-03 (bot readiness)

**Claim**: "Precomputed report was computed at 5 AM earlier today (2026-05-03 11:43 BKK), so the bot can use it as cache to reply to users."

**Type**: hypothesis (combines config + behavior + ground-truth check)

---

## Status: ⚠️ PARTIALLY TRUE — text yes, PDF no

**Confidence: HIGH** (Layer 4 ground-truth verified)

The bot **can** reply with cached **report text** for today's tickers. It **cannot** include a PDF link because the PDF column is NULL for every row today (and for the last 5 days).

---

## Evidence

### Layer 1 — Schedule fired & Step Functions succeeded

- **Schedule** (`terraform/scheduler.tf:221`): `cron(0 5 * * ? *)` tz `Asia/Bangkok` ⇒ 22:00 UTC trigger.
- **Step Functions execution** (`precompute-20260503-050051`):
  - Started 2026-05-03 05:00:52 BKK
  - Stopped  2026-05-03 05:06:53 BKK
  - Status: SUCCEEDED ✓
- Previous 4 daily runs (2026-04-29 → 2026-05-02) also SUCCEEDED.

### Layer 4 — Aurora `precomputed_reports` rows for today

Query (via `dr-daily-report-query-tool-dev`):

```sql
SELECT report_date, status, COUNT(*), SUM(report_text NOT NULL),
       SUM(pdf_s3_key NOT NULL), SUM(pdf_presigned_url NOT NULL)
FROM precomputed_reports
WHERE report_date >= CURDATE() - INTERVAL 4 DAY
GROUP BY report_date, status;
```

| report_date | status | rows | with_text | with_pdf_s3 | with_pdf_url |
|---|---|---:|---:|---:|---:|
| 2026-05-03 | completed | **42** | **42** | 0 | 0 |
| 2026-05-02 | completed | 46 | 46 | 0 | 0 |
| 2026-05-01 | completed | 42 | 42 | 0 | 0 |
| 2026-04-30 | completed | 42 | 42 | 0 | 0 |
| 2026-04-29 | completed | 42 | 42 | 0 | 0 |

### Layer 4 — sample row for AAPL

```
symbol            : AAPL
status            : completed
computed_at       : 2026-05-03 05:02:15
expires_at        : 2026-05-04 05:02:15  ← still valid until tomorrow 5 AM
text_len          : 7364 chars
pdf_s3_key        : NULL
pdf_presigned_url : NULL
```

---

## What this means for the Slack bot path

`SlackBot.handle_app_mention()` calls `PrecomputeService.get_cached_report(symbol, today)`:

| Bot output element | Source column | Today's reality |
|---|---|---|
| Text reply (≤ 7 KB) | `report_text` | ✅ 42 tickers populated, ~7 KB each |
| `📄 PDF: <url>` line | `pdf_presigned_url` | ❌ NULL for every ticker |

The bot will return **text only** (no PDF link line) — which is exactly the partial-success path the bot code is already designed to handle (the formatter omits the PDF line when the column is NULL).

---

## Why PDFs are missing

This is **Obstacle A** from `.claude/research/2026-05-02-pdf-generation-broken.md`:
- `pdf_workflow` has been failing on `1040 'Too many connections'` due to scheduling collision with `precompute_workflow`.
- 0 PDFs in S3 for 22 days.
- Recommended fix (still pending): **A2** = move `pdf_workflow` to 05:45 UTC + **B1** = wire `update_pdf_presigned_url()` in `pdf_worker_handler`.

The precompute Step Function "SUCCEEDED" is misleading — it succeeds because writing the **report row** is a separate task from generating the PDF. PDF generation is in the downstream `pdf_workflow`, which hasn't run successfully in 22 days. The text path was always working; the PDF path is what's broken.

---

## Eliminated alternatives

| Hypothesis | Why ruled out |
|---|---|
| Schedule didn't fire | Step Functions execution `precompute-20260503-050051` exists, status SUCCEEDED |
| Aurora had no data because of 1040 error | 42 rows with `report_text` populated today |
| Cache expired before bot could read it | `expires_at = 2026-05-04 05:02:15` — 17 hours of remaining validity |
| All rows are status=`pending` or `failed` | All 42 rows are `completed` |

---

## Recommendation

**Proceed with bot use today** — text-only replies will work for any of the 42 tickers in today's run. Examples confirmed: `AAPL`. (Caveat: tickers must be in the precompute set; `DBS19` was in yesterday's set but isn't today — the matcher will need to suggest a near-match if the user types one not in the day's batch.)

**Do not promise PDFs** until A2 + B1 ship. Until then, bot replies will silently omit the `📄 PDF:` line.

**Next concrete step**: run `/specify "PDF generation fix — A2 + B1"` to convert the GORE plan into an executable implementation spec.

---

## References

- Schedule: `terraform/scheduler.tf:208-222`
- Step Functions execution: `precompute-20260503-050051` (region ap-southeast-1)
- Cache table: `precomputed_reports`
- Bot read path: `src/data/aurora/precompute_service.py:get_cached_report`
- Bot reply formatter: `src/integrations/slack_bot.py:format_report_response`
- PDF problem analysis: `.claude/research/2026-05-02-pdf-generation-broken.md`
- PDF GORE diagram: `.claude/research/2026-05-02-pdf-generation-broken-gore.md`
