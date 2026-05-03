---
name: Prod cache "all tickers" — claim true, but no patch found in code/config
description: Validates that prod cache covers full ticker universe today and audits whether a recent fix is responsible
type: validation
date: 2026-05-03
---

# Validation: "I patched dr-daily-report in prod so all tickers produce reports"

**Claim**: User patched something in production around 2026-05-02 such that **all** prod-universe tickers now produce precomputed reports daily.

**Type**: hypothesis (combines code/config audit + ground-truth coverage)

---

## Status: ⚠️ PARTIALLY TRUE — coverage claim ✅ TRUE, patch attribution ❌ FALSE

**Confidence: HIGH**

- "All tickers produce report" today ⇒ **TRUE** (56/56).
- "I made a patch that caused this" ⇒ **No supporting evidence found.** No code, image, or config change in the relevant window. The improved coverage looks data-driven (upstream APIs recovering), not patch-driven.

---

## Evidence

### A. Coverage today (Layer 4) — TRUE

```sql
SELECT report_date, COUNT(*) FROM precomputed_reports
WHERE report_date >= CURDATE() - INTERVAL 14 DAY
GROUP BY report_date;
```

| Date | completed rows |
|---|---:|
| **2026-05-03** | **56** |
| 2026-05-02 | 56 |
| 2026-05-01 | 53 |
| 2026-04-30 | 53 |
| 2026-04-29 | 53 |
| 2026-04-28 | 54 |

**56 = full universe.** `data/tickers.csv` has 56 alias rows; `ticker_master` has 56 active DR aliases (`symbol_type='dr' AND is_active=TRUE`). Today's batch matches exactly.

### B. The 3 symbols that started appearing on 2026-05-02

```sql
SELECT symbol FROM precomputed_reports
WHERE report_date='2026-05-02' AND symbol NOT IN
  (SELECT symbol FROM precomputed_reports WHERE report_date='2026-05-01');
```

→ **`GSD.SI`** (GOLD19, SPDR Gold Shares SG), **`QK9.SI`** (INDIAESG19, India ESG ETF), **`0050.TW`** (Taiwan ETF). All three are Asia-listed ETFs.

### C. No code/config change in the relevant window — counter-evidence to "patch"

| Audit dimension | Finding |
|---|---|
| Prod Lambda `LastModified` (report-worker, precompute-controller, ticker-scheduler, get-ticker-list) | All between **2026-01-13 and 2026-01-21**. None redeployed since January. |
| Prod ECR repo `dr-daily-report-lambda-prod` | Last image push: **2026-01-22** (`beta-unlimited-20260122-114723`). No new images. |
| Currently-deployed image tag on report-worker-prod | `ticker-update-20260121-201359` (pushed 2026-01-21, four months ago). |
| `data/tickers.csv` git history | Last change `83e7d0c` on **2026-01-21** — adds 10 new aliases. Nothing more recent. |
| `git log --since="3 days ago"` | All commits are dev branch (slack-bot + replica refactor). No prod-relevant changes. |
| Working tree | Modified file: only `replica_explorer_dr-bot.html` (this session's GORE diagram). No code/TF/config diff. |
| `ticker_master.updated_at` for the 3 new symbols (id=6 GSD.SI, id=7 QK9.SI; 0050.TW similar) | **2026-01-14** — all `is_active=TRUE` since January. Not flipped recently. |
| `ticker_aliases.created_at >= 2026-04-30` | **NO ROWS.** No new aliases were registered in the relevant window. |

### D. Signature of an external/upstream cause, not a code patch

- `0050.TW` has an **intermittent** history: present 2026-04-28, missing 4-29 → 5-1, returns 5-2. That's the signature of a flaky external data dependency (yfinance, etc.), not a deploy.
- The 3 ETFs have **no rows in `daily_prices`, `daily_indicators`, `fund_data`**, yet their `precomputed_reports` rows exist with full Thai-narrative text. Reports for these symbols are generated from live API fetches at run time. So success/failure tracks live-API availability, not stored data.
- All 3 reports have `generation_time_ms = 0` — different from the AAPL pattern, suggesting a partial-data path through the report worker. (Worth investigating separately.)

---

## What likely actually happened

On 2026-05-02 the upstream data source(s) yfinance / equivalent — started returning workable responses for these 3 Asia-listed ETFs that previously timed out or returned empty payloads. The report worker, unchanged since January, simply succeeded where it had been failing. That's why:

- The change happened *between* the 2026-05-01 and 2026-05-02 scheduled runs (a one-day step function).
- Nothing in the deployment artifacts changed.
- The new symbols are exactly the kind of tickers that are commonly flaky on yfinance (low-volume Asian ETFs).

This is **not a fix**. It's data-source recovery. There is no patch to credit.

---

## Why the user might believe they patched it

Possible explanations for the perception:
1. **Confusion with the dev-environment Slack bot work.** Two Lambdas (`ticker-scheduler-dev`, `report-worker-dev`) *were* updated on 2026-05-02 13:56 UTC. None of those touched prod.
2. **A no-op manual operation.** Re-running a workflow, restarting a container, or re-applying Terraform without changes can feel like fixing something but doesn't change behavior.
3. **Dashboard reload.** Coverage metric improved between two consecutive views and got attributed to a recent action.

Without additional evidence (e.g. a Doppler audit log, a manual Aurora INSERT/UPDATE, or a CloudShell history showing a fix command), the prod-side root cause is **upstream data recovery, not a patch**.

---

## Recommendation

**Don't mark this as fixed.** The 56/56 coverage today is fragile because it depends on external API availability for low-volume tickers. Expect it to regress without warning when upstream stutters again. To make it actually robust:

1. **Add a real fix** that decouples report generation from live-API availability:
   - Backfill `daily_prices` / `daily_indicators` for all active tickers via a scheduled job, so the report worker reads from cached tables when live fetch fails.
   - Or add per-ticker retry-with-backoff in the report worker for known-flaky tickers.

2. **Add a coverage alarm** (CloudWatch metric on `precomputed_reports row count by date`) that pages when below the 56-ticker baseline. Today's 56/56 is invisible to ops; a regression to 53/56 will be silent.

3. **If the user did make a manual change** (manual SQL, AWS Console flip, Doppler tweak), that change is **not in version control**. Capture it now via a `/journal` entry — otherwise it'll be lost and we won't know how to reproduce it next time.

---

## Eliminated alternatives

| Hypothesis | Why ruled out |
|---|---|
| Code patch deployed to prod | No Lambda redeployed since 2026-01-21; no ECR push since 2026-01-22 |
| `tickers.csv` updated | Last commit affecting it: 2026-01-21 |
| New rows added to `ticker_master`/`ticker_aliases` | No `created_at` or `updated_at` after 2026-04-30 |
| `is_active` flag flipped | All 3 symbols had `is_active=TRUE` since 2026-01-14 |
| New ticker_id mapping | ticker_ids 6 and 7 (GOLD19, INDIAESG19) created in January |
| Doppler config change | Not directly verifiable, but no Lambda env-var update would persist without a Lambda update event |
| Step Functions definition change | Would show in TF diff and Lambda LastModified for SFN-invoking funcs |

---

## References

- Cache table: `precomputed_reports` (prod Aurora)
- Selector: `src/scheduler/get_ticker_list_handler.py:71-77` (queries `is_active=TRUE AND symbol_type='dr'`)
- Schedule: `terraform/scheduler.tf:208-222` (5 AM BKK)
- Prod Lambdas: `dr-daily-report-{report-worker,precompute-controller,ticker-scheduler,get-ticker-list}-prod`
- Prod ECR repo: `dr-daily-report-lambda-prod` (current image: `ticker-update-20260121-201359`)
- Companion validations:
  - `.claude/validations/2026-05-03-precompute-cache-bot-readiness.md` (dev cache today)
  - `.claude/validations/2026-05-03-tencent19-dbs19-cache-status.md` (dev: missing TENCENT19/DBS19)
