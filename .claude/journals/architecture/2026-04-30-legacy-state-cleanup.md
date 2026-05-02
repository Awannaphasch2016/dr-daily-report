---
title: Legacy state file cleanup — `state rm` for 14 DOUBLE + 2 GHOST entries (Plug #2 journal)
category: architecture
date: 2026-04-30
status: adopted
related_adrs: []
tags: [tf-aws, replica, dr-bot, plug-2, state-rm, double, ghost, legacy-state]
---

# Legacy state cleanup — Plug #2 journal BEFORE `state rm` batch

## Context

The 2026-04-30 `/tf-aws audit` of the dr-bot replica revealed two findings invisible to the 2026-04-28 audit because the prior run only read the primary state file (`s3://dr-daily-report-tf-state/telegram-api/dev/terraform.tfstate`). The replica config `.claude/replicas/dr-bot.yaml` declares both files:

```yaml
x:
  primary: s3://dr-daily-report-tf-state/telegram-api/dev/terraform.tfstate
  legacy:
    - s3://dr-daily-report-tf-state/dev/terraform.tfstate
```

Reading both produces:

| Finding | Count | What |
|---|---|---|
| **DOUBLE** | 14 | Resources bound in BOTH state files (3 alarms, 6 IAM roles, 1 log group, 1 SNS topic, 1 RDS parameter group, 2 SQS queues) |
| **GHOST** | 2 | SQS queues bound only in the **legacy** state file, but the queues no longer exist in AWS (`pdf_jobs`, `pdf_jobs_dlq`) |

Both categories live entirely in the legacy state file, which is leftover from a prior migration phase that split bot infrastructure into per-app state files. The primary state file is authoritative for the dr-bot replica today; the legacy file's continued existence is dead weight that confuses every future audit.

## Decision

Run `terraform state rm` against the legacy state file for all 16 entries (14 DOUBLE + 2 GHOST). The primary state file's bindings remain authoritative. After the operation:

- The legacy state file will be empty of dr-bot-scoped resources (it may still hold non-dr-bot entries from other replicas; those are out of scope for this pass).
- The 14 DOUBLE-bound resources will continue to be managed via the primary state file — no AWS-side change, no service interruption.
- The 2 GHOST SQS queues will be removed from state; they don't exist in AWS, so removal aligns state with reality.

**This is a state-only operation. No AWS API writes. No service impact.**

## Why now

The next phase of the reconciliation (Stage 2 imports + Stage 4 drift edits) targets the **primary** state file. Leaving DOUBLEs in place would mean each `terraform plan` against the primary file produces correct output, but each `terraform plan` against the legacy file produces phantom diffs against AWS resources that another state file already manages. The cleanup happens first to clear the noise floor before anything more delicate runs.

## DOUBLEs being removed (14)

(Inventory below summarized; exact addresses surfaced by `/tf-aws prune --apply` Phase F preview.)

- 3 CloudWatch alarms (alarm names beginning with `dr-daily-report-*-errors-dev`)
- 6 IAM roles (Lambda execution roles for the legacy LINE bot configuration)
- 1 CloudWatch log group (legacy aggregator)
- 1 SNS topic (alert routing target)
- 1 RDS DB cluster parameter group
- 2 SQS queues (no longer in active use; primary state has the same bindings)

For each, the action is `terraform state rm <addr>` against the **legacy** state. The same `<addr>` continues to bind in the primary state.

## GHOSTs being removed (2)

- `aws_sqs_queue.pdf_jobs` — legacy state binding; queue does not exist in AWS
- `aws_sqs_queue.pdf_jobs_dlq` — legacy state binding; queue does not exist in AWS

These were the SQS-based PDF job pipeline that was replaced by the Step Functions–driven `pdf_workflow` (see `terraform/pdf_workflow.tf`). The SQS resources were deleted from AWS but never removed from the legacy state file.

## Conditions to re-open this decision

Re-open if any of:

- A `terraform plan` against the legacy state file (run before `state rm`) shows that the legacy file has bindings for resources NOT in the primary file. In that case, those entries are not DOUBLEs — they're singletons under legacy management — and removing them would leave them unmanaged. The Phase F preview from `/tf-aws prune --apply` will confirm pure-DOUBLE status; abort if any binding is unique to legacy (other than the GHOSTs we explicitly handle).
- A future module starts referencing the legacy state file by S3 URI (e.g., as a remote state data source). Currently no module does. If one starts, the empty legacy file becomes a contract surface, and we'd want to either populate it or delete the file outright.
- Discovery of additional DOUBLEs not enumerated above. The audit said 14; if `prune --apply` Phase F surfaces more or fewer, halt and reconcile the count.

## Verification

After the `state rm` batch:

```bash
# Re-parse legacy state file → expect 0 dr-bot-scoped resources matching y.filter
aws s3 cp s3://dr-daily-report-tf-state/dev/terraform.tfstate /tmp/legacy.json
jq '.resources[] | select(.mode == "managed") | .type + "." + .name' /tmp/legacy.json | wc -l
# Expected: 0 (or only resources outside the dr-bot replica scope)
```

Also: re-run `/tf-aws audit` Stage 5c — δ_membership should show 0 DOUBLE, 0 GHOST.

## Reversibility

Pre-mutation backup is automatic via Phase G of `/tf-aws prune --apply` — backup lands at `.terraform-state-backups/<timestamp>/`. To restore:

```bash
aws s3 cp .terraform-state-backups/<ts>/terraform_dev_state.json \
  s3://dr-daily-report-tf-state/dev/terraform.tfstate
```

This restores the legacy state file's full pre-mutation contents, including the 16 entries this journal removes.

## Linked plan

`/home/anak/.claude/plans/polished-giggling-dewdrop.md` — Stage 1.

## References

- `.claude/replicas/dr-bot.yaml` — `x.primary` + `x.legacy` declaration that the audit reads
- `.claude/commands/tf-aws.md` § "Blind spots and limits" — BS-2 (Post-action amnesia), the principle this journal exists to enforce
- `.claude/commands/tf-aws.md` § "DOUBLE detection" — the audit logic that surfaces these findings
- 2026-04-30 audit results — embedded in plan v2 Context section
