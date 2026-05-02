# Stage 3 — Advisory delete + import dispositions (dr-bot replica)

**Date**: 2026-05-02
**Stage**: 3 (Advisory review — keep-vs-delete decisions)
**Plan reference**: `~/.claude/plans/polished-giggling-dewdrop.md`
**Audit baseline**: 2026-04-30 audit + Stage 2 (this conversation)
**Replica**: `dr-bot` (`.claude/replicas/dr-bot.yaml`)

## Why this journal exists (Plug #2)

The /tf-aws skill's blind-spot plug #2 says: capture intent in writing
*before* any destructive verb erases the operator's reasoning. Stage 3
is the first stage that performs **AWS-side deletions** (not just state
mutations); the deletes are unrecoverable. This file captures, per item,
the evidence that motivated the disposition so a future operator (or a
later "why did we delete that?" review) can reconstruct the call.

## Scope

11 ORPHAN candidates surfaced by the 2026-04-30 audit + the Stage 2
dry-run discovery pass. Each gets one of three dispositions:
- **DELETE** — AWS resource is dead/empty/unreferenced
- **IMPORT** — AWS resource is real and in use; bring under TF management
- **CARVE-OUT** — pause for explicit second look (reserved for #5)

## Disposition table

### DELETE (7 items)

| # | Resource | Disposition evidence | Rollback |
|---|---|---|---|
| 1 | `aws_apigatewayv2_api` `ta0g00v0c7` (Name=dr-daily-report-telegram-api-dev) | 0 invocations 7d (CloudWatch); 1 invocation on tracked sibling `ou0ivives1`; CloudFront has no origin pointing here; created 2025-11-30 — pre-split-API era artifact. | Re-create via TF (would generate new api-id; CloudFront re-point not needed since CloudFront never used this one). |
| 2 | `aws_ecs_cluster` `dr-daily-report-ingestion-dev` | ACTIVE, 0 services, 0 tasks (matches `triage.empty_shell_patterns` in dr-bot.yaml). | Re-create via TF. |
| 3 | `aws_ecs_cluster` `dr-data-pipeline-dev` | ACTIVE, 0 services, 0 tasks. | Re-create via TF. |
| 4 | `aws_secretsmanager_secret` `dr-daily-report/grafana-mysql/dev` | LastAccessedDate=null since creation 2026-03-15; matches `triage.empty_shell_patterns`. **Force-delete without recovery window** (AWS default is 30d; we want immediate). | Re-create + repopulate (loss tolerant: never accessed). |
| 7 | `aws_iam_role` `dr-daily-report-ecs-execution-dev` | Created 2026-03-15, LastUsed 2026-03-15 (creation day only); paired with empty cluster #2/#3. Detach: `AmazonECSTaskExecutionRolePolicy` (AWS-managed, leave intact). | Re-create via TF. |
| 8 | `aws_iam_role` `dr-daily-report-ecs-task-dev` | Created 2026-03-15, **LastUsed=null** (never assumed); paired with empty cluster #2/#3. Detach: `dr-daily-report-ecs-task-policy-dev` (customer-managed, **NOT in TFM** — separate disposition needed for the policy itself; not addressed here). | Re-create via TF. |
| 10 | `aws_iam_role` `dr-daily-report-line-bot-role-dev` | LastUsed 2026-01-17; **0 CloudTrail AssumeRole events in 90d**; tag Project=dr-daily-report. Half-completed rename artifact — line-bot Lambda actually uses `line-bot-ticker-report-role` (TFM-managed); this newer-naming-convention role was created but never wired in. Detach: 3 attached managed policies (`AWSLambdaVPCAccessExecutionRole`, `AWSLambdaBasicExecutionRole`, `dr-daily-report-dynamodb-access-dev` — last is TFM-tracked at `aws_iam_policy.dynamodb_access`, leave intact); auto-delete: 1 inline policy `dr-daily-report-line-bot-custom-policy-dev`. | Re-create via TF if a future migration to new naming is desired. |

### IMPORT (3 items)

| # | Resource | Why import | TF address |
|---|---|---|---|
| 6 | `aws_security_group` `dr-daily-report-grafana-dev` (sg-029583f3ff4d682ca) | Real dependency: referenced by Aurora SG ingress (audit 2026-04-30). Component=grafana-security-group, App=shared. | `aws_security_group.grafana` |
| 9 | `aws_iam_role` `dr-daily-report-grafana-role-dev` | Paired with #6 (Managed Grafana VPC connectivity); LastUsed 2026-03-14 confirms creation-day setup. | `aws_iam_role.grafana` |
| 11 | `aws_ecr_repository` `dr-daily-report-telegram-api` | **In active use**: webhook_health and model_catalog_sync Lambdas pull from this repo. ECR repo is unmanaged in TF, while the Lambdas using it now ARE managed (post-Stage-2 absorb). Importing closes the loop. | `aws_ecr_repository.telegram_api` |

### CARVE-OUT (1 item)

| # | Resource | Why pause |
|---|---|---|
| 5 | `aws_security_group` `line-bot-ticker-report-sg` (sg-03e0bb93ea6bd920e) | Tag Project=LineBot; description "Security group for LINE bot Lambda function". 0 ENIs attached, 0 Lambdas reference it via VPC config (verified). LINE Bot is a live product; despite zero apparent dependencies, the SG name and description suggest historical association. **Pausing for explicit second-look** before delete. |

## Customer-managed policies left in place (not addressed in this pass)

Two customer-managed IAM policies are **detached** from deleted roles
but **NOT deleted** themselves:

| Policy | Used by (deleted role) | Why kept | Future disposition |
|---|---|---|---|
| `dr-daily-report-ecs-task-policy-dev` | #8 (ecs-task-dev) | NOT in TFM — could be used by another role we haven't checked | Stage 3.5: investigate `aws iam list-entities-for-policy`; if zero entities, delete |
| `dr-daily-report-dynamodb-access-dev` | #10 (line-bot-role-dev) | TFM-tracked at `aws_iam_policy.dynamodb_access` — definitely keep | n/a — this is correctly managed |

The inline policy `dr-daily-report-line-bot-custom-policy-dev` is
auto-deleted with role #10 (inline policies are part of the role, not
standalone resources).

## Order of operations (this pass)

1. APIGW delete (lowest blast radius)
2. Secret delete (force-delete-without-recovery)
3. IAM role deletes (detach managed policies first; inline auto-deletes; then delete-role) — line-bot, ecs-task, ecs-execution
4. ECS cluster deletes (empty already)
5. (Imports for #6, #9, #11 happen after deletes, in a fresh
   Pattern 12 backup → import → plan-verify cycle)

## Conditions to revisit / re-open this journal

- If LINE Bot starts misbehaving after this pass → check whether
  anything was using the deleted line-bot-role-dev (CloudTrail still has
  the 90d window if quick).
- If a Grafana dashboard suddenly can't reach Aurora → verify the
  imported Grafana SG (#6) is still tracked and unchanged.
- If a future deploy expects the deleted ECS clusters → see commits
  predating 2026-05-02 for what they were used for; recreate via TF.

## Linked artifacts

- `.claude/replicas/dr-bot.yaml` — replica config (filter updated this pass)
- `.claude/plans/polished-giggling-dewdrop.md` — Stage 2-5 plan
- `.claude/journals/architecture/2026-04-30-quant-agent-rename.md` — Stage 2a journal
- `.claude/evolution/2026-05-02-tf-aws-language-standardization-and-noema-anchor-recognition.md` — vocabulary pass
- `terraform/imported_orphans.tf` — import stubs (Chunk A + B + Stage 3)
