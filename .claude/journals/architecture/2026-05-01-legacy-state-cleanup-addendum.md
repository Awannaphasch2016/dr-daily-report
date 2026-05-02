---
title: Legacy state cleanup — Stage 1 dry-run addendum (counts revised, HALT category surfaced, Option B selected)
category: architecture
date: 2026-05-01
status: adopted
related_adrs: []
tags: [tf-aws, replica, dr-bot, plug-2, state-rm, double, ghost, halt, legacy-state, addendum]
---

# Legacy state cleanup — addendum to 2026-04-30 journal

## Why this addendum exists

The 2026-04-30 journal (`2026-04-30-legacy-state-cleanup.md`) declared intent to `state rm` **14 DOUBLE + 2 GHOST = 16 entries** from the deprecating state file. It explicitly listed re-open conditions, including:

> "Discovery of additional DOUBLEs not enumerated above. The audit said 14; if `prune --apply` Phase F surfaces more or fewer, halt and reconcile the count."

The Stage 1 dry-run on 2026-05-01 surfaced **24 entries**, not 16. Per the re-open clause, this addendum reconciles the count and captures intent for the additional 8 entries **before** any destructive verb fires (Plug #2 / BS-2: state-file mutations erase the original disagreement; the journal preserves the reason).

## Reconciled inventory

The deprecating state file (`s3://dr-daily-report-tf-state/dev/terraform.tfstate`) holds 24 dr-bot-scoped managed resources. Partition:

### DOUBLE — 18 entries (14 in original journal + 4 new)

The 14 originally enumerated remain. The 4 newly-discovered:

| # | Address | AWS ID | Note |
|---|---|---|---|
| +1 | `aws_cloudfront_origin_access_identity.webapp` | `ECE3O34PLCE64` (deprecating) / `E3TW52UDU2O6GX` (primary) | **DIVERGED-IDS** — same TF address binds different AWS objects in the two state files. After rm from deprecating, `ECE3O34PLCE64` becomes a true ORPHAN-DELETE (advisory). |
| +2 | `aws_iam_role_policy_attachment.get_report_list_vpc` | `dr-daily-report-get-report-list-role-dev-20260103040833490000000002` | Vanilla DOUBLE (sub-resource of `get_report_list_role`). |
| +3 | `aws_iam_role_policy_attachment.get_ticker_list_vpc` | `dr-daily-report-get-ticker-list-role-dev-20251229173644418500000003` | Vanilla DOUBLE (sub-resource of `get_ticker_list_role`). |
| +4 | `aws_iam_role_policy_attachment.pdf_worker_vpc` | `dr-daily-report-pdf-worker-role-dev-20260103040833530500000003` | Vanilla DOUBLE (sub-resource of `pdf_worker_role`). |

These 4 were in the original journal's footnote ("8 other entries: 4 IAM policy attachments + 4 legacy-only-with-live-AWS"); they're now promoted to first-class DOUBLE entries because the dry-run confirmed they're true DOUBLEs (same address bound to same AWS resource in both files, except DB1 which is the special diverged-IDs case).

The original journal also tagged 5 of the 14 as un-prefixed addresses: `aws_cloudwatch_metric_alarm.dlq_messages`, `.message_age`, `.queue_depth`, `aws_sqs_queue.dlq`, `aws_sqs_queue.main`. The dry-run revealed these are actually module-prefixed in both state files: `module.fund_data_sync_queue.aws_cloudwatch_metric_alarm.dlq_messages`, etc. The corrected addresses are what `terraform state rm` will be invoked with.

### GHOST — 3 entries (2 in original journal + 1 new)

The 2 SQS queues (`pdf_jobs`, `pdf_jobs_dlq`) remain. The new entry:

| # | Address | AWS ID (claimed) | AWS reality |
|---|---|---|---|
| +1 | `aws_iam_role_policy.pdf_worker_sqs_policy` | `dr-daily-report-pdf-worker-role-dev:dr-daily-report-pdf-worker-sqs-dev` | Inline policy not present (verified via `aws iam get-role-policy` returning `NoSuchEntity`) |

This was the inline policy that gave `pdf_worker_role` access to the deleted `pdf_jobs` SQS queue. It was deleted from AWS alongside the queues but never removed from state. Same root cause as G1 and G2 — the SQS-based PDF pipeline → Step Functions migration left state stragglers.

### HALT — 3 entries (NEW category not in original journal)

These are legacy-only state bindings whose AWS resources are still live and **not bound in primary**:

| # | Address (deprecating only) | Live AWS ID | AWS evidence |
|---|---|---|---|
| H1 | `aws_cloudwatch_metric_alarm.dlq_messages` (root) | `dr-daily-report-dlq-messages-dev` | `describe-alarms` returns the alarm |
| H2 | `aws_sqs_queue.report_jobs` | `dr-daily-report-telegram-queue-dev` (active telegram queue) | `get-queue-url` returns the queue |
| H3 | `aws_sqs_queue.report_jobs_dlq` | `dr-daily-report-report-jobs-dlq-dev` | `get-queue-url` returns the queue |

H2 (`dr-daily-report-telegram-queue-dev`) is the **active telegram report queue** — load-bearing.

## Decision

### For the 18 DOUBLE + 3 GHOST = 21 vanilla entries

`terraform state rm` from deprecating. Same justification as the original journal:

- DOUBLE: primary holds the canonical binding; deprecating's binding is duplicate.
- GHOST: AWS resource is gone; binding is dead-letter.

No AWS-side change. Pre-mutation backup automatic.

### For the 3 HALT entries — Option B

User-selected on 2026-05-01: **`state rm` from deprecating now; accept temporary un-management; treat as ORPHANs in next audit and re-absorb (import to primary) later.**

**Why Option B over Option A (import-then-rm)**:

- The 3 HALT bindings are leftover from a pre-Apr-2026 state split that this journal is closing out. Deferring them in deprecating just to keep them "managed" perpetuates the split-state problem the cleanup exists to solve.
- After rm, the 3 AWS resources continue to function unchanged (an SQS queue doesn't notice TF un-managing it). They are "ORPHAN per audit, healthy per AWS."
- The next `/tf-aws audit` will surface them as ORPHAN ENTRIES (in AWS, not in any state). Phase D's "import-now" verdict will fire for H2 (recent activity expected — telegram queue) and H3 (DLQ paired). H1 (alarm) is observer-class — `triage.always_import_classes` fires `import-now`.
- Net cost: one extra audit + absorb cycle for these 3 resources. Net benefit: deprecating state file fully drained → archival-eligible on schedule.

**Why NOT Option A**: it requires writing `.tf` blocks for each into the primary tree first (or generating import stubs), then running `terraform import` 3× before the state rm. That's a longer human path and can't be completed in this Stage 1 pass. Option C (defer entirely) was considered but leaves the deprecating file half-drained, which means "deprecating" is only nominally so until next pass.

### Risk accepted under Option B

For the duration between Stage 1's state rm and the follow-up import:

- The 3 AWS resources will not appear in any `terraform plan`. Manual changes to them will not be detected by IaC drift checks.
- The active telegram report queue is on this list. If something modifies it via console between Stage 1 and the follow-up import, that change will be invisible to TF.
- **Mitigation**: the follow-up `/tf-aws audit + absorb` pass should run within 24–48 hours of Stage 1's `state rm`. ETA target: 2026-05-02 to 2026-05-03.

## Conditions to re-open

Re-open this addendum if any of:

- The Stage 1 `state rm` produces a count residual ≠ 0 after running 24 commands. Means a 25th binding was missed by enumeration.
- Primary state file's managed resource count changes during Stage 1 (must remain at 208). Would mean we accidentally pointed at primary.
- The follow-up audit on 2026-05-02/03 surfaces the 3 HALT-now-ORPHAN entries with verdict ≠ `import-now`. Means classification logic is mistaken about them.
- A CI workflow or developer recipe is discovered to be wired to the deprecating state file during the Stage 1 window (Phase F.5 should catch this; if it doesn't, audit the sweep coverage).

## Verification (Layer 4)

Post-state-rm assertions:

```bash
# Deprecating: expect 0 dr-bot-scoped managed resources
aws s3 cp s3://dr-daily-report-tf-state/dev/terraform.tfstate /tmp/legacy_after.json
jq '[.resources[] | select(.mode == "managed")] | length' /tmp/legacy_after.json
# Expected: 0

# Primary: expect 208 (unchanged)
aws s3 cp s3://dr-daily-report-tf-state/telegram-api/dev/terraform.tfstate /tmp/primary_after.json
jq '[.resources[] | select(.mode == "managed")] | length' /tmp/primary_after.json
# Expected: 208

# Live AWS: 3 HALT resources still present (Option B)
aws cloudwatch describe-alarms --alarm-names "dr-daily-report-dlq-messages-dev" --query 'MetricAlarms[].AlarmName' --output text
aws sqs get-queue-url --queue-name "dr-daily-report-telegram-queue-dev" --output text
aws sqs get-queue-url --queue-name "dr-daily-report-report-jobs-dlq-dev" --output text
# Expected: all three return successfully
```

## Reversibility

Pre-mutation backup at `.terraform-state-backups/<timestamp>/dev_terraform.tfstate.backup.json`. To restore:

```bash
aws s3 cp .terraform-state-backups/<ts>/dev_terraform.tfstate.backup.json \
  s3://dr-daily-report-tf-state/dev/terraform.tfstate
```

## Linked plan

`/home/anak/.claude/plans/polished-giggling-dewdrop.md` — Stage 1.

## References

- `.claude/journals/architecture/2026-04-30-legacy-state-cleanup.md` — original journal (count baseline, re-open clause)
- `.claude/replicas/dr-bot.yaml` — `state.role` schema (added 2026-05-01) declaring deprecating role
- `.claude/commands/tf-aws.md` § BS-2 — Plug #2 principle
- `.claude/commands/tf-aws.md` § Phase A.5, § Phase H self-test — added 2026-05-01 in the same evolve pass
- `docs/architecture/c4-plantuml/rendered/replica_explorer_dr-bot.html` — Reconcile tab (DOUBLE/GHOST/HALT tables, updated 2026-05-01)
- 2026-05-01 dry-run output — embedded in this conversation's `/step` Stage 1 dry-run section
