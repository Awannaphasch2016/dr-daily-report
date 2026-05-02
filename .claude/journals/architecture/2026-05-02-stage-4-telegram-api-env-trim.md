# Stage 4 — telegram_api env trim (7 keys removed; 13 deferred)

**Date**: 2026-05-02
**Stage**: 4 (DRIFTED reconciliation — telegram_api Lambda subset)
**Plan reference**: `~/.claude/plans/polished-giggling-dewdrop.md` Stage 4
**Predecessor**: Stage 3 commit `5dedc33`; KEEP-FOR-NOW commit `b343c76`
**Replica**: `dr-bot` (`.claude/replicas/dr-bot.yaml`, `noema_anchor: aws_currently_working`)

## Why this journal exists (Plug #2)

The verb here is "edit `terraform/telegram_api.tf`" — not destructive in the
AWS sense, but **does erase intent** (the env declarations themselves).
Without this journal, a future operator might re-add `LOG_LEVEL` or
`TELEGRAM_APP_ID` thinking "the Lambda needs them" without realizing the
2026-04-30 audit confirmed they were never read by code.

This journal also captures the **reframe** that emerged during Stage 4a:
plan v2 hypothesized "Doppler injects at runtime → trim-spec direction
for all keys"; reality is "broken CI deploy → AWS is stale → trim 7
unused, defer 13 because direction is actually apply-tf for those."

## Stage 4a evidence (the 20-key table)

`terraform/telegram_api.tf` declares 27 env keys. AWS dev Lambda has 9.
Intersection is 7 (Aurora* + DYNAMODB_WATCHLIST_TABLE + LANGFUSE_HOST).
**TF-only set is 20 keys.** AWS-only set is 2 (`LANGFUSE_RELEASE` set by
CI on each deploy, `DOPPLER_TOKEN_ANAK` vestigial — no code reads it).

For each TF-only key, grepped `src/` / `dr_cli/` / `tests/` for actual
`os.environ.get` / `os.getenv` calls (not just substring matches —
docstring-only matches do not count).

| Key | Read in code | Verdict | Action this pass |
|---|---|---|---|
| OPENROUTER_API_KEY | 20 sites | apply-tf | **DEFER** (broken CI) |
| ENVIRONMENT | 11 sites | apply-tf | **DEFER** (broken CI) |
| DATA_LAKE_BUCKET | 8 sites | apply-tf | **DEFER** (broken CI) |
| LANGFUSE_PUBLIC_KEY | 4 sites | apply-tf | **DEFER** (broken CI) |
| PDF_BUCKET_NAME | 3 sites | apply-tf | **DEFER** (broken CI) |
| USE_REPORT_PIPELINE | 2 sites | apply-tf | **DEFER** (broken CI) |
| REPORT_PIPELINE_ARN | 2 sites | apply-tf | **DEFER** (broken CI) |
| LANGFUSE_SECRET_KEY | 2 sites | apply-tf | **DEFER** (broken CI) |
| TELEGRAM_BOT_TOKEN | 1 site | apply-tf | **DEFER** (broken CI) |
| REPORT_WORKER_FUNCTION_NAME | 1 site | apply-tf | **DEFER** (broken CI) |
| PDF_URL_EXPIRATION_HOURS | 1 site | apply-tf | **DEFER** (broken CI) |
| PDF_STORAGE_BUCKET | 1 site | apply-tf | **DEFER** (broken CI) |
| LANGFUSE_TRACING_ENVIRONMENT | 1 site | apply-tf | **DEFER** (broken CI) |
| TELEGRAM_WEBAPP_URL | 0 (unused) | trim-spec | **REMOVE** |
| TELEGRAM_APP_ID | 0 (docstring only) | trim-spec | **REMOVE** |
| TELEGRAM_APP_HASH | 0 (docstring only) | trim-spec | **REMOVE** |
| LOG_LEVEL | 0 (docstring only) | trim-spec | **REMOVE** |
| JOBS_TABLE_NAME | 0 (unused) | trim-spec | **REMOVE** |
| CACHE_TTL_HOURS | 0 (unused) | trim-spec | **REMOVE** |
| CACHE_BACKEND | 0 (unused) | trim-spec | **REMOVE** |

## Why "DEFER" for the 13 apply-tf keys

The drift mechanism is *not* "TF over-declares because Doppler injects
at runtime" (plan v2 hypothesis — falsified by:
- No `doppler` binary in `Dockerfile`
- No `doppler-python` in `requirements.txt`
- No code references `DOPPLER_TOKEN_ANAK` or imports doppler
- Handler returns 500 with `❌ Missing required environment variables`
  on dev as of CloudWatch event 2026-04-28T08:42:55Z).

The actual mechanism is: **the only path from TF declaration to AWS
Lambda env is `terraform apply`**, run by CI as `doppler run -- tf
apply`. Doppler is a **deploy-time secret injector**, not a runtime
client.

`gh run list` shows the `Deploy Telegram App - Dev Environment` workflow
last ran 2026-03-18 with `conclusion: failure` (and many failures
before). Since CI hasn't successfully deployed in 6 weeks, every TF env
change since then is stuck on the source side of the bridge.

Editing TF cannot push the 13 apply-tf keys to AWS. Fixing the broken
CI deploy is the right action; that is a **separate concern**, not
within `/tf-aws` skill scope.

By contrast, **LINE Bot dev/prod work fine** — its CI (`Deploy LINE Bot
- Dev Environment`) succeeded 2026-03-18, and AWS Lambda env reflects
TF: `dr-daily-report-line-bot-dev` has 15 keys including
OPENROUTER_API_KEY. The user confirmed runtime: "line bot for dev and
prod are working fine."

So drift is asymmetric:
- LINE Bot: TF ≈ AWS (deploy bridge intact)
- telegram_api: TF ⊋ AWS (deploy bridge broken)
- Same TF source patterns; different bridge health.

## Why "REMOVE" for the 7 trim-spec keys

For TELEGRAM_APP_ID, TELEGRAM_APP_HASH, TELEGRAM_WEBAPP_URL,
JOBS_TABLE_NAME, CACHE_TTL_HOURS, CACHE_BACKEND, LOG_LEVEL:

- 0 references via `os.environ` / `os.getenv` patterns in
  `src/` / `dr_cli/` / `tests/`
- The 4 single-substring matches were all in **docstrings** of
  `src/telegram_lambda_handler.py:54-62` (a "documented as required"
  comment block that the actual `required_vars` validator below does
  not enforce)
- `LOG_LEVEL` literal usage: `logging.basicConfig(level=logging.INFO)`
  in `src/telegram_lambda_handler.py:13` — code is hard-coded INFO,
  doesn't read the env

User authorization (verbatim 2026-05-02): "1. yes 2. remove now. if we
need it, we will add it then. 3. CI is separate issue. 4. remove now.
if we need it, we will add it then."

Cross-file scoping rules applied:
- `LOG_LEVEL = "INFO"` is also declared in 9 other Lambda env blocks
  (ticker_fetcher, fund_data_sync, pdf_workflow, schema_manager,
  query_tool, scheduler, main, precompute_workflow). Same "unused but
  declared" pattern. **Out of scope this commit** — telegram_api only.
- `JOBS_TABLE_NAME` is also declared in 3 other Lambdas (scheduler,
  async_report, report_pipeline). **Out of scope this commit.**
- `var.telegram_app_id`, `var.telegram_app_hash` are referenced **only**
  in telegram_api.tf:177-178, so the variable declarations + 4-tfvars
  values are also orphaned. Remove.
- `var.telegram_webapp_url` is also referenced in `api_gateway.tf:23`
  (CORS allow-list) — **keep** the variable declaration; only remove
  the env-block usage.

## Files modified this pass

| File | Change |
|---|---|
| `terraform/telegram_api.tf` | Remove 7 lines from env block + their section comments |
| `terraform/variables.tf` | Remove `variable "telegram_app_id"` + `variable "telegram_app_hash"` declarations |
| `terraform/terraform.dev.tfvars` | Remove `telegram_app_id`, `telegram_app_hash` lines |
| `terraform/terraform.staging.tfvars` | Remove `telegram_app_id`, `telegram_app_hash` lines |
| `terraform/terraform.prod.tfvars` | Remove `telegram_app_id`, `telegram_app_hash` lines |
| `terraform/terraform.feature-alerts.tfvars` | Remove `telegram_app_id`, `telegram_app_hash` lines |

## Verification (Stage 4g)

`terraform plan -target=aws_lambda_function.telegram_api` should show:
- Reduced env-add diff (was 18 keys to add → now 11 keys to add)
- No destructive change to AWS resources
- TF state mutation only at `terraform apply` time (which CI cannot
  currently run, so no AWS-side change actually occurs from this commit)

## Re-open conditions

1. **CI deploy fix lands**: After `Deploy Telegram App - Dev Environment`
   succeeds, AWS Lambda env will receive the 13 apply-tf keys. Re-audit
   then to confirm convergence; close out the 13 deferred items.
2. **A new feature needs one of the removed keys**: just re-add it. The
   variable declarations for telegram_app_id/_hash are gone but trivial
   to re-add. The webapp_url variable was kept (still used by CORS).
3. **Audit shows new env-key drift**: re-run the same Stage-4a
   evidence-gathering recipe against the new keys.

## Linked artifacts

- `.claude/journals/architecture/2026-04-30-quant-agent-rename.md` — Stage 2a
- `.claude/journals/architecture/2026-04-30-legacy-state-cleanup.md` — Stage 1
- `.claude/journals/architecture/2026-05-02-stage-3-advisory-deletes.md` — Stage 3 + Item-#5 KEEP-FOR-NOW
- `.claude/replicas/dr-bot.yaml` — replica config (filter updated 2026-05-02)
- `~/.claude/plans/polished-giggling-dewdrop.md` — Plan v2 (Stage 4 framing partially falsified by 4a evidence; this journal records the reframe)

## What this journal does NOT do

- Does not fix the broken CI deploy. That is a separate `/step` to be
  scheduled/owned per user direction.
- Does not touch other Lambdas' env declarations. `LINE Bot`,
  `report_worker`, `ticker_scheduler` etc. are out of scope this commit.
- Does not handle the broader cross-Lambda `LOG_LEVEL` / `JOBS_TABLE_NAME`
  cruft (declared in many Lambdas). A future Stage 4 sweep can address.
