---
claim: Terraform state is up-to-date with the real deployed state of daily DR report infrastructure
type: config
date: 2026-04-27
verdict: FALSE
confidence: HIGH
---

# Validation: Terraform state vs deployed infrastructure (dev)

## Status: ❌ FALSE — significant drift detected

**Method**: `terraform plan -refresh-only` against S3 backend
`s3://dr-daily-report-tf-state/telegram-api/dev/terraform.tfstate` (region `ap-southeast-1`),
AWS account `755283537543`, IAM user `anak`.

The plan is **incomplete** — 5 errors prevented full refresh — but evidence already gathered is sufficient to conclude state is not in sync.

---

## Evidence

### Drift detected: **34 resources changed in AWS, not yet reflected in state**

Categorized:

| Category | Count | Examples | Likely cause |
|----------|-------|----------|--------------|
| **Lambda code/version** | 5 | `aws_lambda_function.{telegram_api,report_worker,line_bot}`, both `_live` aliases | CI/CD deployments (versions advanced 4→15 and 175→177 between refreshes) |
| **CloudWatch log groups** | 13 | `aws_cloudwatch_log_group.{slack_notifier,telegram_api_logs,…}` | Retention changed in AWS (e.g. `sec_edgar_mcp_server`: `retention_in_days 7 → 365`) |
| **IAM roles/policies** | 6 | `aws_iam_role.{report_worker_role,telegram_lambda_role,rds_proxy,…}`, `aws_iam_policy.lambda_aurora_access` | Manual edits or attachments outside Terraform |
| **Aurora cluster + RDS Proxy** | 3 | `aws_rds_cluster.aurora`, `aws_rds_cluster_instance.aurora`, `aws_db_proxy.aurora` | Likely engine auto-upgrade / parameter-group / endpoint change |
| **Security groups** | 3 | `aws_security_group.aurora`, **deleted**: `aws_security_group_rule.aurora_from_codebuild`, `aws_security_group_rule.aurora_from_proxy` | Two SG rules **deleted in AWS console**, still in state — investigate intent |
| **S3 / CloudFront** | 2 | `aws_s3_bucket.static_api[0]`, `aws_cloudfront_origin_access_identity.webapp` | Manual edit |
| **SQS module** | 2 | `module.fund_data_sync_queue.aws_sqs_queue.{main,policy}` | Manual edit |

**Layer-4 ground-truth corroboration** (Lambda last-modified):

| Function | Live last-modified | Status drift |
|----------|--------------------|--------------|
| `dr-daily-report-telegram-api-dev` | 2026-03-18 | confirms version 175→177 was deployed after last `terraform apply` |
| `dr-daily-report-report-worker-dev` | 2026-03-18 | confirms 4→15 |
| `dr-daily-report-line-bot-dev` | 2026-03-18 | confirms drift |

---

### Errors that blocked a clean plan (5)

These are **not** infrastructure drift — they are issues with the local working tree and IAM:

| # | Error | Root cause | Severity |
|---|-------|------------|----------|
| 1 | `precompute_workflow.tf:106` — `aws_sfn_state_machine.report_pipeline is empty tuple` | `var.use_report_pipeline = false` so the `count`-gated resource has 0 elements; locals index `[0]` unconditionally | Local code bug |
| 2 | `report_pipeline.tf:661` — same `[0]` index on output | Same as #1 | Local code bug |
| 3 | `report_pipeline.tf:666` — same | Same as #1 | Local code bug |
| 4 | `cloudfront:GetOriginAccessControl` AccessDenied (`E9HIOD3QXRUUD`) | IAM user `anak` lacks the action — fixable per CLAUDE.md "Full IAM permissions available" policy | Permission gap |
| 5 | `cloudfront:GetResponseHeadersPolicy` AccessDenied (`8c0698cc-…`) | Same as #4 | Permission gap |

**Working-tree context that explains errors 1–3**:

```
?? terraform/report_pipeline.tf            ← UNTRACKED (new, not committed)
?? terraform/step_functions/report_pipeline.json
 M terraform/precompute_workflow.tf        ← modified
 M terraform/terraform.dev.tfvars          ← modified
 M terraform/async_report.tf               ← modified
 M terraform/telegram_api.tf               ← modified
```

`report_pipeline.tf` is a **work-in-progress** file referenced from `precompute_workflow.tf` and its own outputs, but the resource is feature-flagged off (`use_report_pipeline=false` in the dev tfvars). The outputs/locals need `try()` or `length() > 0 ?` guards.

---

### Plan was unable to refresh (so this list may understate drift)

Because errors 4–5 prevented the CloudFront resources from being read, drift on the CloudFront distribution itself, the Origin Access Control, and the Response Headers Policy is **unknown**. Real drift count could be higher than 34.

---

## Analysis

### Overall assessment

State is **out of sync** by ~6 weeks across three independent dimensions:

1. **Routine CI/CD lag** (Lambda versions). Expected if the CI/CD pipeline doesn't run `terraform apply -refresh-only` after each deploy. Mitigation: schedule a nightly `apply -refresh-only` or accept the lag.
2. **Manual changes** (IAM roles, log retention, SQS, S3, Aurora SG rules). Real configuration drift — someone (Console, automation, or a sister tool) is editing resources outside Terraform. **Two security-group rules have been deleted from AWS** but still exist in state — this is the highest-risk item.
3. **Service-level changes** (Aurora cluster, RDS Proxy). Could be benign auto-upgrades or could indicate an intentional change that should be codified.

### Confidence

- **HIGH** that drift exists (concrete diff evidence from `terraform plan -refresh-only`).
- **MEDIUM** on completeness — the 5 plan errors mean some resources weren't refreshed.

### Risk

- Re-running `terraform apply` from the current `.tf` files would attempt to **recreate the deleted Aurora SG rules** (state still has them), which may or may not match operator intent. Verify before applying.
- IAM role drift means deployed Lambdas may have permissions Terraform doesn't know about → harder to reason about least-privilege.

---

## Recommendations

In priority order:

1. **Investigate the deleted Aurora SG rules** (`aurora_from_codebuild`, `aurora_from_proxy`).
   ```bash
   aws ec2 describe-security-groups --group-ids $(aws ec2 describe-security-groups \
     --filters Name=tag:Name,Values=*aurora* --query 'SecurityGroups[].GroupId' --output text)
   ```
   Decide: were they removed intentionally (then `terraform state rm` and remove from `.tf`) or accidentally (then `terraform apply` to recreate)?

2. **Fix the local `report_pipeline.tf` outputs** so `terraform plan` runs cleanly. The file is untracked and references a feature-flagged resource without count-aware indexing:
   ```hcl
   value = var.use_report_pipeline && length(aws_sfn_state_machine.report_pipeline) > 0 \
           ? aws_sfn_state_machine.report_pipeline[0].arn : null
   ```
   Or use `try(aws_sfn_state_machine.report_pipeline[0].arn, null)`.

3. **Grant the missing CloudFront read permissions** to the `anak` IAM user (per CLAUDE.md policy: create policy, attach, don't ask):
   ```json
   {"Effect":"Allow","Action":["cloudfront:GetOriginAccessControl",
     "cloudfront:GetResponseHeadersPolicy","cloudfront:GetDistribution"],"Resource":"*"}
   ```
   Then re-run the plan to surface any CloudFront drift.

4. **Reconcile the routine drift** with `terraform apply -refresh-only -auto-approve` (after verifying the per-resource diffs are all benign — Lambda versions, log retention, etc.). This rewrites state to match reality without touching any AWS resource.

5. **Repeat for `staging` and `prod`**. This validation only covered `dev` (the currently-initialized backend). Re-init with `envs/staging/backend.hcl` and `envs/prod/backend.hcl` to get the full picture before any release.

6. **Prevent future drift**: add a CI job that runs `terraform plan -refresh-only -detailed-exitcode` weekly and alerts on drift.

---

## References

- Plan log: `/tmp/tf_refresh_plan.log` (this session)
- Backend: `s3://dr-daily-report-tf-state/telegram-api/dev/terraform.tfstate`
- AWS account: `755283537543`, region `ap-southeast-1`
- Local edits: `terraform/{report_pipeline.tf,precompute_workflow.tf,async_report.tf,telegram_api.tf,terraform.dev.tfvars}`
- Tier-0 principle invoked: **#2 Progressive Evidence** (Layer 1 plan output + Layer 4 Lambda metadata)
