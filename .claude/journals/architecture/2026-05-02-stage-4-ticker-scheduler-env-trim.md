# Stage 4 — ticker_scheduler env trim (2 keys removed)

**Date**: 2026-05-02
**Stage**: 4 (DRIFTED reconciliation — ticker_scheduler Lambda subset; **last in Stage 4 per-Lambda pass**)
**Plan reference**: `~/.claude/plans/polished-giggling-dewdrop.md` Stage 4
**Predecessor**: Stage 4 report_worker commit `e459c2a`
**Replica**: `dr-bot` (`.claude/replicas/dr-bot.yaml`, `noema_anchor: aws_currently_working`)

## Why this journal exists (Plug #2)

Closing journal for Stage 4's per-Lambda pass. ticker_scheduler is the
**cleanest** profile of the 4 Lambdas — like LINE Bot, its CI bridge is
healthy and TF declarations match AWS. Just two cruft keys to trim.

## CI deploy bridge status

`gh run list --workflow=deploy-scheduler-dev.yml`:
3 most recent runs all SUCCESSFUL (2026-03-18, 2026-03-18, 2026-03-15).
Healthy bridge — same profile as LINE Bot.

## Stage 4a evidence

`terraform/scheduler.tf:28-58` declares 12 env keys.
AWS dev Lambda has 13 keys.

**Intersection (TF ∩ AWS) = 12 keys**: all TF declarations at AWS.
**TF-only = 0**: no apply-tf gap.
**AWS-only = 1**: `LANGFUSE_RELEASE` (CI-injected post-apply, expected).

## Per-key code-usage analysis

| Key | src/ refs | Verdict |
|---|---|---|
| OPENROUTER_API_KEY | 20 | KEEP |
| ENVIRONMENT | 11 | KEEP |
| AURORA_HOST | 9 | KEEP |
| DATA_LAKE_BUCKET | 8 | KEEP |
| AURORA_USER/PORT/PASSWORD/DATABASE | 3 each | KEEP |
| PDF_BUCKET_NAME | 3 | KEEP |
| PRECOMPUTE_CONTROLLER_ARN | 2 | KEEP |
| **JOBS_TABLE_NAME** | **0** | **TRIM** |
| **LOG_LEVEL** | **0** | **TRIM** |

## Files modified this commit

- `terraform/scheduler.tf`: remove `JOBS_TABLE_NAME` (line 44) and
  `LOG_LEVEL = "INFO"` (line 38) from env block

## Verification plan

`terraform plan -target=aws_lambda_function.ticker_scheduler` should
show:
- env block diff: 3 keys removed (JOBS_TABLE_NAME, LOG_LEVEL trimmed
  from TF; LANGFUSE_RELEASE shows as removed because TF doesn't
  declare it — CI will re-inject post-apply)
- 0 destructive
- Possibly other pre-existing drifts (image_uri, AURORA_HOST cluster-vs-
  proxy) visible but out of scope this commit

## Re-open conditions

1. **A new feature needs LOG_LEVEL or JOBS_TABLE_NAME read at runtime**:
   trivial re-add.
2. **CI's LANGFUSE_RELEASE step is removed**: re-evaluate whether to
   declare it in TF (currently preserved by jq-merge in workflow).

## Stage 4 per-Lambda pass — ALL DONE

| Lambda | Commit | Trim count | Apply-tf deferred | AWS-only documented |
|---|---|---|---|---|
| telegram_api | `2b7e4f5` | 7 | 13 (broken CI) | n/a |
| line_bot | `c163240` | 1 (LOG_LEVEL) | 0 | LANGFUSE_RELEASE, ORIGINAL_HANDLER |
| report_worker | `e459c2a` | 1 (JOBS_TABLE_NAME) | 9 (broken CI) | 6 keys (incl. ENVIRONMENT and PDF_URL_EXPIRATION_HOURS — flagged as ADD candidates) |
| ticker_scheduler | (this commit) | 2 (JOBS_TABLE_NAME, LOG_LEVEL) | 0 | LANGFUSE_RELEASE |

**Asymmetric drift framing finalized**:
- 2 Lambdas with healthy CI (line_bot, ticker_scheduler) — small trim only
- 2 Lambdas sharing broken CI (telegram_api, report_worker via deploy-
  telegram-dev.yml) — major apply-tf gap deferred until CI fix

Stage 4 sub-stages still pending:
- 4d: AURORA_HOST drift (proxy vs cluster endpoint)
- 4e: Aurora engine_version (3.04.0 → 3.10.3)
- 4f: Aurora SG ingress (Grafana SG addition)
- Stage 5: full audit re-run + verification

## Linked artifacts

- `.claude/journals/architecture/2026-05-02-stage-4-telegram-api-env-trim.md`
- `.claude/journals/architecture/2026-05-02-stage-4-line-bot-env-trim.md`
- `.claude/journals/architecture/2026-05-02-stage-4-report-worker-env-trim.md`
