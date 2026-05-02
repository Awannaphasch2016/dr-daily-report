# Stage 4 Aurora trio — 4d (no-op), 4e (engine_version refresh), 4f (Grafana SG ingress declaration)

**Date**: 2026-05-02
**Stage**: 4 (DRIFTED reconciliation — Aurora subset; final Stage 4 sub-stages)
**Plan reference**: `~/.claude/plans/polished-giggling-dewdrop.md` Stage 4
**Predecessor**: Stage 4 ticker_scheduler env trim
**Replica**: `dr-bot` (`.claude/replicas/dr-bot.yaml`, `noema_anchor: aws_currently_working`)

## Why this journal exists (Plug #2)

Closes Stage 4 by reconciling three Aurora-scoped drifts against the
canonical axis (`aws_currently_working`). One sub-stage is a deliberate
no-op (4d AURORA_HOST per-Lambda asymmetry) and needs intent recorded so
a future operator doesn't "fix" what isn't broken.

## 4d — AURORA_HOST per-Lambda asymmetry (NO TF EDIT)

### Evidence

`terraform/aurora.tf:60-62` — `var.use_rds_proxy` defaults to **false**.
`terraform/aurora.tf:173`:
```hcl
aurora_connection_endpoint = var.use_rds_proxy ? aws_db_proxy.aurora.endpoint : aws_rds_cluster.aurora.endpoint
```

So **TF intent is cluster endpoint** (no proxy unless var flipped).

### Per-Lambda AWS reality

| Lambda | AURORA_HOST runtime value | Endpoint type | Matches TF intent? |
|---|---|---|---|
| line_bot | `dr-daily-report-aurora-dev.cluster-...` | cluster | ✅ |
| telegram_api | `dr-daily-report-aurora-proxy-dev.proxy-...` | **PROXY** | ❌ outlier |
| report_worker | `dr-daily-report-aurora-dev.cluster-...` | cluster | ✅ |
| ticker_scheduler | `dr-daily-report-aurora-dev.cluster-...` | cluster | ✅ |

### Disposition: NO TF EDIT

3/4 Lambdas already match the TF default (cluster). The 4th
(telegram_api dev) is a manual proxy override applied during the broken-
CI window — it will self-resolve when the broken `deploy-telegram-dev.yml`
CI is fixed and the next successful apply pushes TF intent back to AWS
(setting AURORA_HOST = cluster endpoint via `local.aurora_connection_endpoint`).

**Why not "refresh-tf to proxy":** that would force the other 3 healthy
Lambdas onto the proxy unnecessarily — proxy adds latency and an extra
failure point. The proxy path exists for a future use case (e.g. high
connection churn) that hasn't materialized.

**Re-open conditions:**
1. CI deploy fix lands → re-audit telegram_api AURORA_HOST; should
   converge to cluster automatically.
2. New use case warrants proxy adoption → flip `use_rds_proxy = true`
   in tfvars; this is a deliberate, documented change.

## 4e — engine_version refresh (CRITICAL)

### Evidence

`terraform/aurora.tf:221`:
```hcl
engine_version = "8.0.mysql_aurora.3.04.0"
```
AWS reality: `8.0.mysql_aurora.3.10.3` (auto-upgraded by AWS — Aurora
MySQL minor version auto-upgrades cannot be opted out).

### Why this is dangerous if left unfixed

A future `terraform apply` would attempt to set engine_version back to
3.04.0 (a **downgrade**), AWS would reject, terraform would fail with a
non-obvious error, and the operator would have to debug it cold.

### Action this commit

Two edits to `aws_rds_cluster.aurora` (terraform/aurora.tf):

1. Bump declaration: `"8.0.mysql_aurora.3.04.0"` → `"8.0.mysql_aurora.3.10.3"`
2. Add lifecycle block:
   ```hcl
   lifecycle {
     ignore_changes = [engine_version]
   }
   ```
   This prevents future auto-upgrades from causing terraform plan churn.

The instance (`aws_rds_cluster_instance.aurora` line 266) already
inherits `engine_version = aws_rds_cluster.aurora.engine_version`, so no
edit needed there.

## 4f — Aurora SG ingress: Grafana SG declaration

### Evidence

AWS Aurora SG `sg-01436f923724febb6` ingress rules (3 total):
| Source | Reason | TF declared? |
|---|---|---|
| sg-0185a0d8d92968d03 (lambda_aurora SG) | Lambda → Aurora MySQL | ✅ inline in `aws_security_group.aurora` |
| 172.31.0.0/16 (VPC CIDR) | VPC-internal access | ✅ inline in `aws_security_group.aurora` |
| **sg-029583f3ff4d682ca (Grafana SG)** | **Managed Grafana → Aurora** | ❌ **TF-undeclared (drift)** |

The Grafana SG was imported in Stage 3 (`terraform/imported_orphans.tf:400`)
as `aws_security_group.grafana`. The ingress rule referencing it was not
declared.

### Pattern reference

`terraform/codebuild.tf:135` (`aurora_from_codebuild`) and
`terraform/rds_proxy.tf:123` (`aurora_from_proxy`) follow the same
pattern: separate `aws_security_group_rule` resource (not inline ingress
in the aurora SG block). Match that pattern for consistency.

### Action this commit

Add `aws_security_group_rule.aurora_from_grafana` to a sensible TF file
(co-located with grafana SG → `terraform/imported_orphans.tf`).

```hcl
resource "aws_security_group_rule" "aurora_from_grafana" {
  type                     = "ingress"
  from_port                = 3306
  to_port                  = 3306
  protocol                 = "tcp"
  security_group_id        = aws_security_group.aurora.id
  source_security_group_id = aws_security_group.grafana.id
  description              = "Allow Managed Grafana to connect to Aurora MySQL"
}
```

## Files modified this commit

- `terraform/aurora.tf:221` — engine_version bump
- `terraform/aurora.tf:217-255` — add `lifecycle { ignore_changes = [engine_version] }` block
- `terraform/imported_orphans.tf` (append) — new `aws_security_group_rule.aurora_from_grafana`

## Verification plan — RESULT (2026-05-02)

`doppler run -- terraform plan -var-file=terraform.dev.tfvars \
  -target=aws_rds_cluster.aurora \
  -target=aws_security_group.aurora \
  -target=aws_security_group_rule.aurora_from_grafana`

**Output**: `Plan: 1 to add, 1 to change, 0 to destroy.` ✅

Decomposition:
- **`aws_rds_cluster.aurora`**: NO DIFF. The lifecycle.ignore_changes
  block masks the engine_version drift; the declaration bump from
  3.04.0 → 3.10.3 aligns TF intent with AWS reality cleanly.
- **`aws_security_group.aurora`**: 1 in-place change. AWS state holds 3
  inline ingress rules (Lambda + VPC + **Grafana**); TF source declares
  2 inline rules (Lambda + VPC). Plan removes the inline Grafana rule
  to migrate it to the external `aws_security_group_rule` declaration.
- **`aws_security_group_rule.aurora_from_grafana`**: 1 ADD. New external
  declaration matching the rule that's about to be removed inline.

### Apply-ordering caveat (read before next CI deploy)

The `aws_security_group.aurora` change (revoke inline rule) and the
`aws_security_group_rule.aurora_from_grafana` create reference the same
underlying AWS rule (3306/tcp from sg-029583f3ff4d682ca → Aurora SG).

Terraform's default parallel apply could attempt:
- (A) revoke first → re-add: brief connectivity gap (Grafana queries
  fail for ~1s)
- (B) re-add first → InvalidPermission.Duplicate error → terraform
  fails

To eliminate ambiguity, the next operator can either:
1. **Two-phase apply** (preferred for live):
   ```bash
   terraform apply -target=aws_security_group_rule.aurora_from_grafana
   # creates duplicate; AWS dedupes silently
   terraform apply -target=aws_security_group.aurora
   # revokes the now-redundant inline rule
   ```
2. **Single-phase apply with import** (cleaner state):
   ```bash
   terraform import aws_security_group_rule.aurora_from_grafana \
     sg-01436f923724febb6_ingress_tcp_3306_3306_sg-029583f3ff4d682ca
   terraform apply  # plan now shows only the inline removal as a clean op
   ```

Either approach avoids the gap. Document choice in the apply commit's
journal.

## Re-open conditions

1. `var.use_rds_proxy` flipped to `true` → reconsider 4d disposition.
2. CI deploy fix lands → verify telegram_api AURORA_HOST converges to
   cluster (4d temporal closure).
3. AWS announces forced-upgrade past 3.10.x → revisit engine_version
   declaration.
4. Managed Grafana retired → delete `aurora_from_grafana` rule and the
   imported `aws_security_group.grafana`.

## Stage 4 — DONE

| Sub-stage | Action | Files | Commits |
|---|---|---|---|
| 4a evidence | per-Lambda env var classification | (research) | (no-op) |
| 4b journal | trim-spec direction documented | 4 journals | (already committed) |
| 4c trims | env block edits | telegram_api, line_bot, report_worker, ticker_scheduler TF | 4 commits |
| 4d AURORA_HOST | NO EDIT (asymmetry doc) | (this journal) | (this commit) |
| 4e engine_version | refresh + lifecycle.ignore_changes | aurora.tf | (this commit) |
| 4f Grafana SG | declare ingress rule | imported_orphans.tf | (this commit) |
| 4g verify | targeted plan | (CLI run) | (verification) |

Stage 5 (audit re-run + Lambda invoke smoke test) follows.

## Linked artifacts

- `.claude/journals/architecture/2026-05-02-stage-4-telegram-api-env-trim.md`
- `.claude/journals/architecture/2026-05-02-stage-4-line-bot-env-trim.md`
- `.claude/journals/architecture/2026-05-02-stage-4-report-worker-env-trim.md`
- `.claude/journals/architecture/2026-05-02-stage-4-ticker-scheduler-env-trim.md`
- `.claude/consolidate/2026-05-02-stage-1-4-asymmetric-drift-framing.md`
