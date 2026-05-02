# Stage 4 — report_worker env trim (1 key removed; 2 ADD candidates flagged)

**Date**: 2026-05-02
**Stage**: 4 (DRIFTED reconciliation — report_worker Lambda subset)
**Plan reference**: `~/.claude/plans/polished-giggling-dewdrop.md` Stage 4
**Predecessor**: Stage 4 line_bot commit `c163240`
**Replica**: `dr-bot` (`.claude/replicas/dr-bot.yaml`, `noema_anchor: aws_currently_working`)

## Why this journal exists (Plug #2)

report_worker is the third Lambda in Stage 4's per-Lambda evidence pass.
Its drift profile is **mixed** — both directions show drift:
- TF declares 9 keys AWS doesn't have (apply-tf gap, like telegram_api)
- AWS has 6 keys TF doesn't declare (some intentional, some cruft, two
  worth proactively adding to TF)

This is the most divergent profile so far, and the journal needs to
capture per-key disposition reasoning so a future operator can resume.

## CI deploy bridge status

`gh run list --workflow=deploy-telegram-dev.yml`:
all 5 most recent runs **FAILED** (2026-03-18 series). report_worker is
deployed by `deploy-telegram-dev.yml` (confirmed: line 25 path filter,
line 332 `WORKER_FUNCTION` env). Same broken-bridge as telegram_api.

Implication: any TF env edits in report_worker's apply-tf direction
(adding declarations) won't reach AWS until CI is fixed. Trim direction
edits (removing TF declarations) take effect when CI eventually runs:
on first successful apply, AWS will lose the trimmed keys.

## Stage 4a evidence

`terraform/async_report.tf:172-204` declares 19 env keys.
AWS dev Lambda has 16 keys.

**Intersection (TF ∩ AWS) = 10 keys**:
TZ, OPENROUTER_API_KEY, JOBS_TABLE_NAME, PDF_STORAGE_BUCKET,
PDF_BUCKET_NAME, AURORA_HOST, AURORA_PORT, AURORA_DATABASE,
AURORA_USER, AURORA_PASSWORD.

**TF-only (TF ⊋ AWS) = 9 keys** (apply-tf direction; deferred):
LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY, LANGFUSE_HOST,
LANGFUSE_TRACING_ENVIRONMENT, REPORT_GENERATION_MODE,
QUANT_AGENT_FUNCTION_NAME, USE_REPORT_PIPELINE, REPORT_PIPELINE_ARN,
DATA_LAKE_BUCKET.

**AWS-only (AWS ⊋ TF) = 6 keys** (mixed disposition):
BETA_USER_LIMIT, ENVIRONMENT, LANGFUSE_RELEASE, LOG_LEVEL,
METRIC_REGISTRY_VERSION, PDF_URL_EXPIRATION_HOURS.

## Per-key code-usage analysis

| Key | Source side | AWS side | src/ refs | Verdict |
|---|---|---|---|---|
| OPENROUTER_API_KEY | ✓ | ✓ | 20 | KEEP |
| ENVIRONMENT | ❌ | ✓ | **11** | **AWS-only, but used by code → ADD candidate** |
| AURORA_HOST | ✓ | ✓ | 9 | KEEP |
| DATA_LAKE_BUCKET | ✓ | ❌ | 8 | DEFER (apply-tf, broken CI) |
| LANGFUSE_PUBLIC_KEY | ✓ | ❌ | 4 | DEFER (apply-tf, broken CI) |
| TZ | ✓ | ✓ | 3 | KEEP |
| PDF_BUCKET_NAME | ✓ | ✓ | 3 | KEEP |
| AURORA_USER/PORT/PASSWORD/DATABASE | ✓ | ✓ | 3 each | KEEP |
| USE_REPORT_PIPELINE | ✓ | ❌ | 2 | DEFER (apply-tf, broken CI) |
| REPORT_PIPELINE_ARN | ✓ | ❌ | 2 | DEFER (apply-tf, broken CI) |
| LANGFUSE_SECRET_KEY | ✓ | ❌ | 2 | DEFER (apply-tf, broken CI) |
| LANGFUSE_HOST | ✓ | ❌ | 2 | DEFER (apply-tf, broken CI) |
| REPORT_GENERATION_MODE | ✓ | ❌ | 1 | DEFER (apply-tf, broken CI) |
| QUANT_AGENT_FUNCTION_NAME | ✓ | ❌ | 1 | DEFER (apply-tf, broken CI) |
| **PDF_URL_EXPIRATION_HOURS** | ❌ | ✓ | **1** | **AWS-only, but used → ADD candidate** |
| PDF_STORAGE_BUCKET | ✓ | ✓ | 1 | KEEP |
| LANGFUSE_TRACING_ENVIRONMENT | ✓ | ❌ | 1 | DEFER (apply-tf, broken CI) |
| **JOBS_TABLE_NAME** | ✓ | ✓ | **0** | **TRIM (this commit)** |
| METRIC_REGISTRY_VERSION | ❌ | ✓ | 0 | AWS-only cruft (will be cleaned on next apply) |
| LOG_LEVEL | ❌ | ✓ | 0 | AWS-only cruft (will be cleaned on next apply) |
| BETA_USER_LIMIT | ❌ | ✓ | 0 | AWS-only cruft (will be cleaned on next apply) |
| LANGFUSE_RELEASE | ❌ | ✓ | n/a | Deploy-time injection by CI; leave |

## Action this commit

**TRIM**: remove `JOBS_TABLE_NAME` from report_worker TF env block
(0 src/ references via os.environ/os.getenv pattern; declared in 3
other Lambdas with same pattern but those are out of scope here per
the Stage-4 single-Lambda commit rule).

## Two important ADD candidates flagged but NOT acted on this commit

### `ENVIRONMENT` — 11 src/ refs, currently at AWS but TF doesn't declare

If broken CI is ever fixed, the next `terraform apply` will push TF's
view of the env block to AWS, **removing `ENVIRONMENT` because TF doesn't
declare it**. Code calls `os.getenv("ENVIRONMENT")` 11 times — losing
this would break report_worker (e.g., environment-conditional logic
returning "unknown" or breaking branch decisions).

**Recommendation**: in a follow-up small commit, add to TF:
```hcl
ENVIRONMENT = var.environment
```

Why deferred this commit: the user's stated heuristic
("remove now; if we need it, we will add it then") implies don't
proactively expand TF. But this case is specifically defensive: a future
event (CI fix) would silently break report_worker. Worth a deliberate
decision, not a same-commit drive-by.

### `PDF_URL_EXPIRATION_HOURS` — 1 src/ ref, currently at AWS but TF doesn't declare

`src/formatters/pdf_storage.py:36` calls
`os.getenv('PDF_URL_EXPIRATION_HOURS', '24')` with a default. So a
future TF apply that strips this from AWS would silently use the default
"24" — that's the literal value at AWS now, so behavior is preserved by
luck.

**Recommendation**: lower-priority follow-up. The default-value safety
net means this is a behavior-preserving omission, not a behavior-
breaking one. If we want TF to be authoritative, declare it; if we
treat the code default as the source of truth, leave alone.

## Verification plan

`terraform plan -target=aws_lambda_function.report_worker` should show:
- env block diff: 4 keys removed from AWS view (JOBS_TABLE_NAME +
  the 3 cruft AWS-only items LANGFUSE_RELEASE, LOG_LEVEL, METRIC_
  REGISTRY_VERSION, BETA_USER_LIMIT — 4 keys not 3, plus
  PDF_URL_EXPIRATION_HOURS and ENVIRONMENT also showing as removed
  since TF doesn't declare them; 7 total expected to remove)
- 9 keys would be added (the apply-tf set, but `apply` won't run here)
- No destructive change to non-env attributes

## Re-open conditions

1. **CI deploy fix lands** → re-audit; close out the 9 deferred items;
   make the ENVIRONMENT and PDF_URL_EXPIRATION_HOURS decision
   pre-deploy (urgent).
2. **report_worker code starts reading BETA_USER_LIMIT, LOG_LEVEL,
   METRIC_REGISTRY_VERSION** → re-classify as ADD candidates.
3. **A new TF declaration is added to the env block** → re-run the
   evidence recipe to ensure no new regressions.

## Linked artifacts

- `.claude/journals/architecture/2026-05-02-stage-4-telegram-api-env-trim.md` (sibling)
- `.claude/journals/architecture/2026-05-02-stage-4-line-bot-env-trim.md` (sibling)
- `.github/workflows/deploy-telegram-dev.yml` — broken CI workflow (last success: ?)
