# Stage 4 — line_bot env trim (1 key removed; AWS-only extras documented)

**Date**: 2026-05-02
**Stage**: 4 (DRIFTED reconciliation — line_bot Lambda subset)
**Plan reference**: `~/.claude/plans/polished-giggling-dewdrop.md` Stage 4
**Predecessor**: Stage 4 telegram_api commit `2b7e4f5`
**Replica**: `dr-bot` (`.claude/replicas/dr-bot.yaml`, `noema_anchor: aws_currently_working`)

## Why this journal exists (Plug #2)

Symmetric to the telegram_api journal but with a **structurally different
finding**: LINE Bot's CI is healthy (last successful deploy 2026-03-18,
user-confirmed working), so its TF↔AWS drift profile is **converged for
declared keys**, with two AWS-only extras that need explicit
classification.

This is a Plug #2 case where the verb is small (one trim) but the
**discovery is large**: documenting the deploy-interceptor cruft pattern
and the post-apply LANGFUSE_RELEASE injection pattern is the real value
of this journal.

## Stage 4a evidence (LINE Bot)

`terraform/main.tf:260-285` declares 13 env keys for `aws_lambda_function.
line_bot`. AWS dev Lambda has 15 keys.

**Intersection (TF ∩ AWS) = 13 keys** — full convergence:
LINE_CHANNEL_ACCESS_TOKEN, LINE_CHANNEL_SECRET, OPENROUTER_API_KEY,
AURORA_HOST, AURORA_DATABASE, AURORA_USER, AURORA_PASSWORD, AURORA_PORT,
PDF_STORAGE_BUCKET, PDF_BUCKET_NAME, PDF_URL_EXPIRATION_HOURS,
ENVIRONMENT, LOG_LEVEL.

**TF-only set = 0** (no drift in the trim direction)
**AWS-only set = 2**: `LANGFUSE_RELEASE`, `ORIGINAL_HANDLER`

### Per-key code-usage analysis (`os.environ`/`os.getenv` grep)

| Key | Read sites in src/ | Verdict |
|---|---|---|
| OPENROUTER_API_KEY | 20 | KEEP |
| ENVIRONMENT | 11 | KEEP |
| AURORA_HOST | 9 | KEEP |
| PDF_BUCKET_NAME | 3 | KEEP |
| LINE_CHANNEL_ACCESS_TOKEN | 3 | KEEP |
| AURORA_USER | 3 | KEEP |
| AURORA_PORT | 3 | KEEP |
| AURORA_PASSWORD | 3 | KEEP |
| AURORA_DATABASE | 3 | KEEP |
| LINE_CHANNEL_SECRET | 2 | KEEP |
| PDF_URL_EXPIRATION_HOURS | 1 | KEEP |
| PDF_STORAGE_BUCKET | 1 | KEEP |
| **LOG_LEVEL** | **0** | **REMOVE** |

`LOG_LEVEL` is hard-coded `INFO` in `src/lambda_handler.py:13`
(`logging.basicConfig(level=logging.INFO)`); the env-declared value is
unread. Same pattern as telegram_api — cruft.

## AWS-only key classification

### `LANGFUSE_RELEASE` — deploy-time injection (KEEP)

Set by CI workflow post-`terraform apply`. Pattern (from
`.github/workflows/deploy-line-dev.yml:252-268` and
`deploy-line-staging.yml:184-199`):

```bash
CURRENT_VARS=$(aws lambda get-function-configuration ... 2>/dev/null)
UPDATED_VARS=$(echo "$CURRENT_VARS" | jq --arg release "$RELEASE" \
  '. + {LANGFUSE_RELEASE: $release}')
aws lambda update-function-configuration --environment "Variables=$UPDATED_VARS"
```

The jq merge preserves all TF-set keys and adds `LANGFUSE_RELEASE`. So
the ordering is: terraform apply (which DOES strip LANGFUSE_RELEASE if
present) → CI re-injects within seconds. There is a brief window of
mismatch between `terraform apply` and the CI follow-up step, but in
practice it doesn't affect runtime correctness because Langfuse uses
the `release` field for trace versioning, not for connectivity.

**Action**: leave alone. Do **not** declare in TF (would fight CI).
Do **not** add `lifecycle.ignore_changes` (the post-apply injection
pattern handles the round-trip correctly).

### `ORIGINAL_HANDLER` — dead deploy-interceptor cruft (LEAVE; documented)

Read by `src/request_interceptor.py:52`:
```python
handler_path = os.environ.get("ORIGINAL_HANDLER")
```

The interceptor is a wrapper: it logs HTTP requests, then dynamically
imports + delegates to the handler whose dotted path is in
`ORIGINAL_HANDLER`. Activated via `scripts/deploy-interceptor.sh`,
which:
1. Sets `ORIGINAL_HANDLER` env var to e.g., `lambda_handler.lambda_handler`
2. Changes the Lambda's `image_config.command` to point to
   `request_interceptor.lambda_handler`

**Current AWS reality (LINE Bot dev, 2026-05-02)**:
- `ImageConfig: null` (Lambda runs Dockerfile CMD = `lambda_handler.lambda_handler`)
- `ORIGINAL_HANDLER = "lambda_handler.lambda_handler"`

So the interceptor is **NOT active** — the Lambda runs lambda_handler
directly via the Dockerfile CMD. The `ORIGINAL_HANDLER` env var is
leftover from a past activation that was reverted (probably by
`terraform apply`, which sets `image_config.command` back to
`lambda_handler.lambda_handler`, breaking the interceptor's chain).

**Action**: leave alone for now. Do **not** declare in TF (would
re-activate dead config). Do **not** delete via `aws cli` here (the
deploy-interceptor pattern may be re-activated for debugging at any
time; removing the env adds friction). Mark as a follow-up item:
either re-activate the interceptor cleanly via TF, or remove the
script + env.

## Files modified this pass

| File | Change |
|---|---|
| `terraform/main.tf` | Remove `LOG_LEVEL = "INFO"` from line_bot env block (line 283) |

No tfvars or variable changes — `LOG_LEVEL` was a literal "INFO", not a
variable reference.

## Verification (Stage 4g)

`terraform plan -target=aws_lambda_function.line_bot` should show:
- `update in-place` only; no destructive
- env block diff: AWS variables map being replaced → `(known after
  apply)` (normal behavior). The actual delta will be: AWS shrinks
  by 3 keys: `LOG_LEVEL` (TF stops declaring, no longer set),
  `LANGFUSE_RELEASE` (TF doesn't declare; CI re-injects), and
  `ORIGINAL_HANDLER` (TF doesn't declare; not re-injected → genuinely
  removed)
- **Risk**: removing `ORIGINAL_HANDLER` on next apply means if
  `request_interceptor.py` is ever re-activated, this env var needs to
  be re-set. Currently the interceptor isn't active, so the removal is
  benign.

## Re-open conditions

1. **`request_interceptor.py` is re-activated**: the env-var sweep
   triggered by `terraform apply` will erase `ORIGINAL_HANDLER` from
   AWS, breaking the interceptor. Either declare it in TF, or add
   `lifecycle.ignore_changes = [environment]`.
2. **Future env-var added that needs runtime configurability via
   LOG_LEVEL**: re-add the TF declaration. Trivial.
3. **CI's LANGFUSE_RELEASE step is removed**: re-evaluate whether to
   declare LANGFUSE_RELEASE in TF (currently it's preserved by CI's
   jq-merge; without that step, TF apply would strip it).

## Asymmetric drift framing — comparison with telegram_api

| Lambda | CI status | TF declares | At AWS | Direction of drift |
|---|---|---|---|---|
| telegram_api dev | **broken** since 2026-03-18 | 27 (now 20 post-trim) | 9 | TF intent → AWS reality (apply-tf direction; deferred until CI fix) |
| line_bot dev | **healthy** | 13 (now 12 post-trim) | 15 (= 13 TF + 2 deploy-time extras) | converged for declared; AWS-only extras documented |

This asymmetry is the central finding of Stage 4a/4b/4c. The same
"audit shows drift" symptom maps to two completely different root
causes — only because we did per-Lambda evidence collection.

## Linked artifacts

- `.claude/journals/architecture/2026-05-02-stage-4-telegram-api-env-trim.md` — sibling journal
- `.claude/journals/architecture/2026-05-02-stage-3-advisory-deletes.md` — Stage 3
- `scripts/deploy-interceptor.sh` — dormant interceptor activation script
- `src/request_interceptor.py` — interceptor wrapper code (currently inactive)
- `.github/workflows/deploy-line-dev.yml:252-268` — LANGFUSE_RELEASE injection step
