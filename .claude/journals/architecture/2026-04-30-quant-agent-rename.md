---
title: Rename `aws_lambda_function.quant_agent_report` → `aws_lambda_function.quant_agent` (path-A)
category: architecture
date: 2026-04-30
status: adopted
related_adrs: []
tags: [tf-aws, replica, reconciliation, dr-bot, plug-2, address-mismatch]
---

# Rename `quant_agent_report` → `quant_agent` (Plug #2 journal — BEFORE destructive verb)

## Context

The 2026-04-28 `/tf-aws audit` of the dr-bot replica reported `dr-daily-report-quant-agent-dev` (live AWS Lambda) as **ORPHAN #3** — i.e. AWS exists, no `.tf` declaration. This is a false positive of the audit's name-match heuristic: `terraform/quant_agent.tf:97` already declares `aws_lambda_function.quant_agent_report`, which **does** manage that live Lambda. The TF address (`quant_agent_report`) just doesn't tag-match the AWS function name (`quant-agent-dev`), so the audit failed to auto-bind them.

This is the **ADDRESS-MISMATCH** finding (❓) shown on the Reconcile Diagram tab of `orphan_audit_2026-04-28.html`.

Two resolution paths surfaced in the conversation 2026-04-29:
- **path-A**: rename TF code `quant_agent_report` → `quant_agent` so address matches AWS name; then `terraform import aws_lambda_function.quant_agent dr-daily-report-quant-agent-dev` if needed (or rely on existing binding if state already maps the Lambda under the old address).
- **path-B**: leave TF address as `quant_agent_report`; `terraform import aws_lambda_function.quant_agent_report dr-daily-report-quant-agent-dev` (manual, bypassing `/tf-aws absorb`); accept that future audits will continue to surface the address-mismatch.

User chose **path-A** on 2026-04-30 ("we import and rename").

## Decision

Rename the TF resource address in source code, in **9 references across 3 files**, BEFORE running `terraform apply` or `/tf-aws absorb --apply`.

| File | References | Notes |
|---|---|---|
| `terraform/quant_agent.tf` | 5 | declaration L97 + 4 self-refs (L167, L168, L189) |
| `terraform/report_pipeline.tf` | ≥4 | invoke / IAM policy refs (L147, L321, L452, L528) |
| `terraform/async_report.tf` | 1 | invoke ref (L197) |

Mechanical `quant_agent_report` → `quant_agent` substitution.

## Why path-A

1. **Audit-clean**: future `/tf-aws audit` runs will not flag the address-mismatch again. δ_membership stays at 0 once everything else is reconciled.
2. **Replica coherence**: TF address matches AWS function name. The replica's three views become consistent on this resource.
3. **One operation, not two**: path-B requires `terraform import` to the old address now, plus a future `terraform state mv` + code edit when the rename is finally done. Path-A does it once.
4. **No state ambiguity**: by renaming in code first, when `terraform plan` runs it will see the rename and emit "state will be moved" — Terraform's safe state-move path. No `state mv` ceremony required.

## Cost accepted

- **9-line refactor** across 3 files. Mechanical `sed` / Edit. Risk: a missed reference → broken plan. Mitigated by `terraform plan` verification after the rename (expected output: state-move-only, no destroy+create).
- **Symbol churn**: any external script or doc that references `aws_lambda_function.quant_agent_report` becomes stale. Search hits: only the 9 in-repo references (verified by `grep -rn quant_agent_report terraform/`).

## Conditions to re-open

Re-open this decision if any of:
- A `terraform plan` after the rename shows **destroy+create** instead of state-move (would mean Terraform doesn't recognize the rename as the same resource — possibly because of provider version differences). In that case, fall back to `terraform state mv aws_lambda_function.quant_agent_report aws_lambda_function.quant_agent` BEFORE running `apply`.
- A future audit reveals additional dependencies on `quant_agent_report` outside the 3 files enumerated (e.g. external scripts, Grafana datasources, docs in CI). Update the rename scope to cover them.
- Convention shifts: if the project later standardizes on the `_report` suffix for all report-producing Lambdas, this rename would create inconsistency. Currently only this Lambda has the suffix, so consistency is improved by removing it.

## Verification

**Correction 2026-04-30 (post-audit)**: This section's original claim was wrong. The 2026-04-30 `/tf-aws audit` revealed that **the live Lambda `dr-daily-report-quant-agent-dev` is not bound in the TF state at all** — it's a true ORPHAN. The `aws_iam_role.quant_agent_role` and IAM policy attachments are tracked, but the `aws_lambda_function` resource block at `terraform/quant_agent.tf:97` was never bound by `terraform apply`. Edge A (`.tf` ↔ `.tfstate`) is broken for this resource (BS-5 in `tf-aws.md`).

Therefore, after applying the rename:

```bash
cd terraform && terraform plan
# Actual expectation: terraform plan shows CREATE for aws_lambda_function.quant_agent
# (because source declares the resource but state has no binding for any name).
# NOT a state-move — there's no state to move.
# import is MANDATORY before any apply, otherwise terraform apply will fail with
# "function already exists" against the live AWS Lambda.
```

The corrective step is to run `terraform import aws_lambda_function.quant_agent dr-daily-report-quant-agent-dev` immediately after the rename. The original "state-move-only" claim conflated this with a hypothetical scenario where the resource was already bound under the old name — it never was.

## Reversibility

Until committed and pushed: `git checkout -- terraform/quant_agent.tf terraform/report_pipeline.tf terraform/async_report.tf`. After commit: `git revert <commit>`.

After `terraform import`: rollback is `terraform state rm aws_lambda_function.quant_agent` to remove the binding (returning to the pre-import "source declares but state doesn't bind" state). The original `terraform state mv` rollback hint was wrong — there's no prior binding to move back to.

## Linked plan

`/home/anak/.claude/plans/polished-giggling-dewdrop.md` — Step 2.

## References

- `orphan_audit_2026-04-28.html` § "Reconcile Diagram" — the ❓ ADDRESS-MISMATCH cell in `quant_agent.tf` group, with the dotted edge `o3 -.-> qa6`.
- `.claude/commands/tf-aws.md` § "Blind spots and limits" → BS-2 (Post-action amnesia) — the principle this journal exists to enforce.
- `.claude/replicas/dr-bot.yaml` — replica scope that includes this Lambda.
