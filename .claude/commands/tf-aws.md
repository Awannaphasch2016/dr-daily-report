# tf-aws Command

**Purpose**: Reconcile a replica's three profiles (`.tf` source, `.tfstate`, AWS-live) for the dr daily report bot. Detect both **membership drift** (ORPHAN / GHOST / DOUBLE / HALT — disagreement on whether a resource is bound and by which state file) and **config drift** (TRACKED-but-DRIFTED — exists on both sides but configurations disagree), import orphans, prune ghosts — without ever mutating AWS itself.

**Operational scope**: Mutations land only on `.tfstate` and `.tf`. AWS-live is read but never written by this skill. Verbs that would push to AWS (`apply-tf` outcomes) are delegated to `terraform apply` invoked outside this command. All mutating verbs of this skill require explicit `--apply`.

## Vocabulary

This skill operates on three **profiles** of one **intent-noema** (the dr-bot system as currently working). Each profile is produced by a different realization-act:

| Profile | Produced by | Operational name in this skill |
|---|---|---|
| `.tf` source | human-edited HCL | the contract |
| `.tfstate` | `terraform apply` / `import` / `state rm` | the cache |
| AWS-live | AWS control plane | the deployment |

**No profile is intrinsically canonical.** The replica config field `noema_anchor` (in `.claude/replicas/dr-bot.yaml`) declares which profile is the working approximation of the noema for this replica right now. For dr-bot today: `noema_anchor: aws_currently_working` — we treat AWS-live as the closest available approximation of "what the user wants" because the bot is currently serving traffic. A pre-deployment / greenfield replica would anchor differently (e.g. `tf_intent_pre_deployment`).

The skill's verbs (`audit / diff / absorb / prune / sync`) align profiles toward whichever profile is anchored. **The "AWS = reality" framing this skill carried before 2026-05-02 was an epistemic overreach** — AWS is *operationally* read-only here, but it is not intrinsically canonical. What's canonical is the noema (the bot working for users); AWS-live is currently the best available proxy.

**Profile-disagreement findings** at the sub-noema (per-resource) level: `ORPHAN`, `GHOST`, `DOUBLE`, `HALT`, `DIVERGED-IDS`, `DRIFTED`, `UNREALIZED-INTENT`, `UNDECLARED-IMPORT`. Their phenomenological categorization (kinds-of-partiality) lives in the Phenomenology tab of `replica_explorer_dr-bot.html` and is not load-bearing for skill operation.

**Three-axis δ**: A replica is converged only when **all three** sets are empty:
- `δ_source` = 0 — `.tf` source files agree with `.tfstate` (Edge A; no UNREALIZED-INTENT, no UNDECLARED-IMPORT)
- `δ_membership = 0` — `.tfstate` and AWS reality describe the same set of resources, with a single canonical state-file binding per resource (Edge B; no ORPHAN / GHOST / DOUBLE / HALT)
- `δ_config = 0` — for every resource in both sets, the per-type fingerprint fields declared in `projection.fingerprint_fields` (see `.claude/replicas/dr-bot.yaml`) match between `.tfstate` and AWS live config (Edge B; no DRIFTED)

A TRACKED Lambda whose live `Environment.Variables` is missing keys the TF config declares is invisible to a membership-only audit but is a real drift — Phase C2 catches it. A `.tf` block edited but never `apply`-ed is invisible to a Phase C2 audit but is a real source-state divergence — Phase A.5 catches it.

**Three views, three edges of disagreement** (one structural, two data):

```
.tf source      ──edge A──►   .tfstate         ──edge B──►   AWS-live
(contract;        (apply /                       (terraform        (deployment;
 human-edited)     import)    cache: binding      SDK push/pull)    AWS-managed)
                              TF↔AWS)
```

`/tf-aws audit` reads **all three views** and measures **all three edges**:
- **Edge A** (`.tf` ↔ `.tfstate`) → Phase A.5: HCL parse → block-level diff → produces UNREALIZED-INTENT (declared in `.tf`, not in `.tfstate`) and UNDECLARED-IMPORT (in `.tfstate`, not in `.tf`).
- **Edge B membership** (`.tfstate` ↔ AWS) → Phases A/B/C: produces ORPHAN, GHOST, DOUBLE (incl. DIVERGED-IDS sub-case), HALT.
- **Edge B fingerprint** (`.tfstate` ↔ AWS, per declared fields) → Phase C2: produces DRIFTED.

A replica is fully converged only when all three δ are 0, **plus** runtime smoke succeeds (BS-1). The historical framing of "Edge A is outside this audit's scope" was wrong: it implicitly assumed every `.tf` edit is followed by an immediate `terraform apply`, which is empirically false (this project has shipped phantom `terraform plan` outputs under that assumption — see CI workflow regression 2026-04-30). Edge A is now a first-class concern of `/tf-aws`.

**The three profiles play different roles — don't conflate them**:

| Profile | Role in this skill | Mutated by |
|---|---|---|
| `.tf` source | **Contract** — declared intent; the law against which `terraform plan` decides | humans editing files |
| `.tfstate` | **Cache** — last-known binding of TF address ↔ AWS ID; not authoritative on its own | `terraform apply`, `terraform import`, `terraform state rm` |
| AWS-live | **Deployment** — what currently exists and serves traffic; the proxy for the noema while `noema_anchor: aws_currently_working` | the AWS control plane (TF apply, console, CLI, drift) |

The cache (`.tfstate`) can disagree with the contract (`.tf`) **in either direction**: contract declares a resource the cache hasn't recorded (UNREALIZED-INTENT), or cache holds a binding the contract doesn't authorize (UNDECLARED-IMPORT). `terraform import` writes the cache *without* writing the contract — so importing alone leaves Edge A broken; the next `terraform plan` will propose a destroy. This is why Phase A.5 must run before any verb that emits imports.

**When to use**:
- Audit drift between TF state and deployed AWS infra (both membership and config)
- Import orphan resources (deployed but not in state) into Terraform management
- Prune ghost entries (in state but no longer in AWS)
- Detect config drift on tracked resources (Lambda env vars, SG rules, API GW routes, etc.)
- After manual console changes, restore IaC discipline
- Before promoting infra changes across environments

**When NOT to use**:
- Routine `terraform plan` — `terraform plan -refresh-only` is faster for simple drift
- Single-resource import — `terraform import <addr> <id>` is more direct
- Cross-account / cross-region work — this command is scoped to one declared replica
- Mutating AWS (deleting orphans from cloud) — do that via console or separate scripts

---

## Tuple Effects (Universal Kernel Integration)

**Part of the Agent Kernel** — Reconciliation operation between three profiles (`.tf` source, `.tfstate`, AWS-live) of a single intent-noema, anchored per-replica via `noema_anchor`.

**Mode Type**: `reconcile`

**Tier**: 1 (Specialized: handles one declared replica pair; Replica concept is internal scaffolding, not promoted to kernel-level type per Rule of Three)

| Tuple Component | Effect |
|-----------------|--------|
| **Constraints** | **EXPAND**: Adds SRC set (parsed `.tf` HCL blocks), TFM set (tracked state), LIVE set (deployed reality), TRACKED set (TFM ∩ LIVE), per-type fingerprint specs, filter scope, replica `state.role` map |
| **Invariant** | **DEFINE**: `δ_source(SRC, TFM) = 0` AND `δ_membership(TFM, LIVE) = 0` AND `δ_config(TRACKED) = 0` for the dr-bot replica |
| **Principles** | **NONE**: Inherits Tier-0 (#1 defensive, #2 progressive evidence, #25 invariant verification) |
| **Strategy** | HCL parse → Source-state diff (Phase A.5) → Discovery → Membership diff → Config-fingerprint diff (TRACKED only) → Triage (3 axes) → Verb dispatch (per-ORPHAN absorb fork: hand-write vs auto-generate) → (optional Apply, bracketed by pre/post invariant assertion that auto-restores on scope violation) → Verification (with audit self-test) |
| **Check** | **EVALUATE**: Reports residual δ after apply on all three axes; PASS iff UNREALIZED-INTENT=UNDECLARED-IMPORT=ORPHAN=GHOST=DOUBLE=HALT=DRIFTED=0 AND audit self-test confirms full coverage |

**Local Check** (mode completion):
- Replica config loaded (including `projection.fingerprint_fields` and `state.role` per file)
- Phase A.5 (Edge A: HCL parse + diff) executed
- Both passes (push, observer) executed
- Phase C (membership diff) AND Phase C2 (config-fingerprint diff) executed
- Triage verdict assigned to every δ item (all three axes)
- Audit self-test (Phase H) confirms: every state file in `x.primary` + `x.legacy` was read; every TRACKED resource of a fingerprintable type was hit; both Phase B passes ran; Edge A diff covered every `terraform/*.tf` file
- If `--apply`: confirmation gate cleared AND post-apply re-verification ran

---

## Verb dispatch

| Verb | Reads | Writes | Default | Description |
|---|---|---|---|---|
| `audit` | TF + AWS | — | dry-run | Summary table: counts of LIVE, TFM, TRACKED, ORPHAN, GHOST, DOUBLE, HALT, **DRIFTED** (TRACKED with config mismatch) |
| `diff` | TF + AWS | — | dry-run | Detailed listing of every δ item across both axes (membership + config) with triage verdict |
| `absorb` | TF + AWS | TF state | dry-run | Generate `terraform import` + `.tf` stubs for ORPHANs (membership only) |
| `prune` | TF + AWS | TF state | dry-run | Generate `terraform state rm` for GHOSTs and DOUBLEs (membership only) |
| `sync` | TF + AWS | TF state | dry-run | `absorb` then `prune` in sequence (membership only; DRIFTED items require human direction-of-change choice — see "DRIFTED reconciliation" below) |

**Crucial safety property**: AWS itself is never mutated. Only Terraform state files are written. Empty-shell deletions (e.g., empty ECS clusters) are *suggested* via output but require human action via console.

---

## Quick Reference

```bash
# Default — read-only audit
/tf-aws

# Natural-language verb dispatch (recommended)
/tf-aws what's drifted
/tf-aws absorb the untracked resources
/tf-aws prune dead state entries
/tf-aws full audit and apply

# Structured verb form (power users / scripts)
/tf-aws audit
/tf-aws diff
/tf-aws absorb --apply
/tf-aws prune --apply
/tf-aws sync --apply

# Override target replica (default: dr-bot)
/tf-aws audit --replica=other-bot
```

---

## NL surface → verb resolution

When parsing the user's free-form input, classify intent into a verb:

| User phrase keywords | Resolved verb |
|---|---|
| "audit", "summary", "status", "what's the state" | `audit` |
| "diff", "drift", "what's different", "show changes" | `diff` |
| "absorb", "import", "pull in", "adopt", "bring under TF" | `absorb` |
| "prune", "remove from state", "delete dead entries", "clean state" | `prune` |
| "sync", "reconcile", "fix everything" | `sync` |
| "apply", "do it", "go ahead" (combined with mutating verb) | adds `--apply` |

If intent is ambiguous, default to `audit` (safest).

---

## Algorithm (executable workflow)

When invoked, execute these steps using the available tools (`Bash`, `Read`, `Write`, etc.):

### Phase 0 — Load replica config

1. **Read** `.claude/replicas/dr-bot.yaml` (or the file specified by `--replica`).
2. Extract:
   - `x.primary` — primary TF state S3 URI
   - `x.legacy` — optional legacy state S3 URI(s)
   - `y.account` — AWS account ID
   - `y.region` — AWS region
   - `y.filter` — tag/name patterns scoping the replica
   - `policy` — default reconciliation rules
   - `triage` — empty-shell patterns and always-import classes

### Phase A — Read TF state (TFM)

For each state file in `x.primary` + `x.legacy`:

```bash
# Download state to local tmp
aws s3 cp <s3_uri> /tmp/tf_state_$(basename <s3_uri>).json

# Parse to extract: ARN/ID, terraform address, resource type
# Use jq:
jq -r '.resources[] | select(.mode=="managed") | .instances[] |
        {address: ..., id: .attributes.id, arn: .attributes.arn, type: ...}'
```

Build set `TFM = { (terraform_address, aws_id, aws_arn, source_state_file) }`.

For each entry, also record `state.role` for `source_state_file` from the replica config (`primary` vs `deprecating`). DOUBLEs detected here are partitioned later by which state file owns the canonical binding (Phase D).

If a resource appears in multiple state files → add to `DOUBLE`.

### Phase A.5 — Read TF source (SRC) and diff against TFM (Edge A)

Edge A — `.tf` ↔ `.tfstate` — is part of this audit's measurement scope. The historical "outside scope, run `terraform plan`" framing is incorrect: it implicitly assumes every `.tf` edit is followed by an immediate `terraform apply`, which is false in practice and produces silent CI regressions (e.g. CI plan output 2026-04-30, where a backend pointed at a sparse legacy state file produced phantom mass-CREATE diffs that bypassed PR review).

```bash
# Walk every .tf file in the replica's terraform/ tree
find terraform -type f -name '*.tf' \
  -not -path 'terraform/.terraform/*' \
  -not -path 'terraform/imported_orphans.tf'  # imported stubs lag .tf by design

# Parse with hcl2json (or `terraform-config-inspect` for module-level), build SRC set:
#   SRC = { (terraform_address, source_file, line_no) }
#   address = "<resource_type>.<name>"            for `resource "..." "..."` blocks
#           = "data.<resource_type>.<name>"        for `data "..." "..."` blocks    (excluded)
#           = "module.<name>.<inner_address>"      for `module "..."` (recursed if local module)
hcl2json terraform/*.tf | jq '... build SRC ...'
```

Diff:

```python
UNREALIZED_INTENT  = SRC - TFM     # declared in .tf, not bound in any state file
UNDECLARED_IMPORT  = TFM - SRC     # bound in state, no .tf block declaring it
SRC_TFM_INTERSECT  = SRC ∩ TFM     # declared and bound (the healthy case)
```

**Equality semantics for Edge A**: address-level only. This phase does NOT diff field values inside the block — that is Phase C2's job (which compares `.tfstate` to AWS, the canonical view of "field as TF currently sees it"). Edge A's job is to confirm every block has a binding and every binding has a block.

**Triage at this phase** (full classification in Phase D, but record signal now):

```
UNREALIZED_INTENT entry r:
  if grep "lifecycle.*ignore_changes" finds r in source     → review (intentional drift envelope; Phase C2 will see it)
  elif r.source_file in .gitignore or matches *.tfvars      → ignore (variable, not a resource)
  else                                                       → unrealized-intent (run `terraform apply`?)

UNDECLARED_IMPORT entry r:
  if r.source_state_file.role == "deprecating"               → likely-stale-state (candidate for Phase 1 prune)
  elif r in terraform/imported_orphans.tf (recently imported)→ pending-stub (write `.tf` block)
  else                                                       → undeclared-import (audit failure — investigate)
```

The audit fails loud (per Principle #1) if any UNDECLARED_IMPORT lacks a triage verdict — refusing a passing ✅ when an unreviewed gap exists is the whole point of having Edge A in scope.

### Phase B — Discover LIVE (AWS reality, scoped)

#### Phase B1 — Push pass (traffic + outbound config)

Read CloudTrail events for the last 7 days, scoped to the account/region:

```bash
aws cloudtrail lookup-events \
  --start-time "$(date -u -d '7 days ago' +%Y-%m-%dT%H:%M:%SZ)" \
  --max-results 5000 \
  --region <region> | \
  jq '[.Events[] | .Resources[] | select(.ResourceType | startswith("AWS::")) | .ResourceName]'
```

For each ARN seen, query its outbound configs:

```bash
# Lambda push targets
aws lambda list-event-source-mappings --function-name <name>

# S3 replication
aws s3api get-bucket-replication --bucket <name> 2>/dev/null

# DynamoDB streams
aws dynamodb describe-table --table-name <name> | jq '.Table.StreamSpecification'

# API GW integrations
aws apigatewayv2 get-integrations --api-id <id>
```

Filter to scope: keep only resources matching `y.filter.tag_app` or `y.filter.name_glob`.

Add to `LIVE`.

#### Phase B2 — Observer enumeration (resources that watch silently)

These cannot be discovered by traffic — they must be enumerated:

```bash
# CloudWatch alarms watching scoped resources
aws cloudwatch describe-alarms --region <region> | \
  jq '.MetricAlarms[] | select(.Dimensions[]?.Value | test("'"<scope_pattern>"'"))'

# CloudTrail trails (account-level)
aws cloudtrail describe-trails --region <region>

# CloudWatch log groups for scoped Lambdas
aws logs describe-log-groups --log-group-name-prefix /aws/lambda/<scope_prefix>

# RDS automated snapshots for scoped clusters
aws rds describe-db-cluster-snapshots --snapshot-type automated \
  --db-cluster-identifier <scope_cluster>

# Secrets Manager (with usage check)
aws secretsmanager list-secrets --filters Key=name,Values=<scope_prefix>
# For each secret: aws secretsmanager describe-secret → check LastAccessedDate

# DynamoDB streams enabled
# (already covered in B1 if table is in scope)
```

Add to `LIVE`. Tag each as `observer-class: true` so triage knows to default-import them.

#### Phase B3 — Dependency closure (1-hop)

For each resource in `LIVE`, fetch dependencies:

```bash
# Lambda → role, log group, SG, subnets, KMS
aws lambda get-function --function-name <name> | \
  jq '{role: .Configuration.Role, vpc: .Configuration.VpcConfig, kms: .Configuration.KMSKeyArn}'

# RDS → SG, subnet group, parameter group, KMS
aws rds describe-db-clusters --db-cluster-identifier <id>

# S3 → bucket policy, replication role, KMS
aws s3api get-bucket-policy --bucket <name>
aws s3api get-bucket-encryption --bucket <name>

# API GW → integration role, authorizer Lambda, custom domain
aws apigatewayv2 get-api --api-id <id>
```

Add all dependencies to `LIVE`. Tag as `dependency-of: <parent_arn>`.

#### Phase B3.5 — Reverse-reference walk (incoming dependencies)

Forward-walk discovers what each LIVE resource consumes. Reverse-walk discovers what consumes each candidate ORPHAN. This matters for `delete-empty-shell` triage: a Security Group with 0 ENIs can still be load-bearing if **another SG's ingress/egress rule references it as a peer**, or a KMS key can be referenced by 0 visible resources but be the encryption key for a snapshot.

Without this pass, `delete-empty-shell` produces commands that fail in AWS at delete time (or worse — succeed and silently break a peer). The 2026-04-30 SG validation (`sg-03e0bb93ea6bd920e`: 0 ENIs but referenced by an out-of-scope `sg-02530c9c16142e463` ingress) is the canonical instance.

Per-type queries:

```bash
# SG → who references this SG in their ingress/egress?
aws ec2 describe-security-groups \
  --filters "Name=ip-permission.group-id,Values=<sg-id>" \
  --query 'SecurityGroups[].{id:GroupId, name:GroupName}'
aws ec2 describe-security-groups \
  --filters "Name=egress.ip-permission.group-id,Values=<sg-id>" \
  --query 'SecurityGroups[].{id:GroupId, name:GroupName}'

# IAM role → who has this role in their AssumeRolePolicy / instance profile / Lambda config?
# (closed-world: enumerate Lambdas, ECS task defs, EC2 instance profiles, EventBridge rules)
aws lambda list-functions --query 'Functions[?Role==`<arn>`].FunctionName'
aws iam list-instance-profiles-for-role --role-name <name>

# S3 bucket policy → who reads/writes this bucket?
# (closed-world: enumerate Lambdas/StepFunctions/CodeBuild that mention the bucket ARN)
grep -l '<bucket-arn>' /tmp/lambda_envs.json /tmp/sfn_definitions.json

# KMS key → who has it in their KMSKeyArn / encryption config?
aws lambda list-functions --query 'Functions[?KMSKeyArn==`<arn>`].FunctionName'
aws rds describe-db-clusters --query 'DBClusters[?KmsKeyId==`<arn>`].DBClusterIdentifier'
aws s3api list-buckets --query 'Buckets[].Name' \
  | jq -r '.[]' | xargs -I{} aws s3api get-bucket-encryption --bucket {} 2>/dev/null \
  | jq 'select(.ServerSideEncryptionConfiguration.Rules[].ApplyServerSideEncryptionByDefault.KMSMasterKeyID == "<arn>")'

# CloudFront OAI → who uses this OAI in their origin config?
aws cloudfront list-distributions \
  --query 'DistributionList.Items[?Origins.Items[?S3OriginConfig.OriginAccessIdentity==`origin-access-identity/cloudfront/<id>`]].Id'
```

Annotate each LIVE resource with `incoming_refs: [<arn>...]` (possibly empty). Used by Phase D's `delete-empty-shell` triage:

```
verdict = "delete-empty-shell" only if:
  resource matches triage.empty_shell_patterns AND
  incoming_refs is [] OR every entry in incoming_refs is itself out-of-scope/dead
```

If `incoming_refs` includes any in-scope live resource, escalate to `review` regardless of empty-shell pattern match.

### Phase C — Membership diff

`TFM` is the union across all in-scope state files. Each entry carries the `state.role` of the file it came from (`primary` | `deprecating` | `archived`). The role is what makes membership categories meaningful when more than one state file is in play.

```python
ORPHAN  = LIVE - TFM                       # in AWS, not in any state
GHOST   = TFM - LIVE  (filtered to scope)  # in state, not in AWS
DOUBLE  = same TF address bound in ≥2 state files                    # see DIVERGED-IDS sub-case below
HALT    = bound in deprecating-role state ONLY, AWS resource is live # primary doesn't claim it; AWS still serves it
TRACKED = LIVE ∩ TFM                       # in both — input to Phase C2
```

**HALT** is the fourth membership category. It surfaces only when `x.files` declares more than one role. A HALT entry is "managed by the deprecating state, abandoned by primary, healthy in AWS." Pruning it from deprecating leaves AWS serving traffic with no TF custodian — so HALT is **not** a vanilla DOUBLE (no peer binding in primary) and **not** a GHOST (AWS resource exists). The triage choice is independent: keep it managed by importing into primary first, or accept temporary un-management and re-absorb on a follow-up audit (then it shows up as ORPHAN). See Phase D.

**DIVERGED-IDS** is a sub-case of DOUBLE — same TF address appears in two state files but is bound to **different AWS IDs**. Detect by comparing `instances[].attributes.id` across the two state entries, not just the address. Treatment: rm the duplicate from `deprecating`; the freed AWS ID then surfaces as a true ORPHAN on the next audit (or as a delete-empty-shell candidate if it's no longer load-bearing).

### Phase C2 — Config-fingerprint diff (NEW)

Inputs:
- `TRACKED` set from Phase C
- `projection.fingerprint_fields` from `dr-bot.yaml` — declares which fields matter, per resource type

For each resource `r` in `TRACKED`:

```python
fields = projection.fingerprint_fields.get(r.terraform_type)
if fields is None:
    continue   # type has no declared fingerprint → skip (config drift not in scope for this type)

tf_config  = parse_state_attributes(r.tfm_entry, fields)        # already in memory from Phase A
aws_config = read_live_config(r.aws_id, r.terraform_type, fields)  # AWS API call

drift = {f: (tf_config[f], aws_config[f]) for f in fields if not equal(tf_config[f], aws_config[f])}

if drift:
    DRIFTED.add(DriftEntry(
        terraform_address = r.terraform_address,
        aws_id            = r.aws_id,
        resource_type     = r.terraform_type,
        field_diffs       = drift,
    ))
```

**Live-config readers** (per resource type — extend as fingerprints are declared):

```bash
# aws_lambda_function: last_modified, code_sha256, environment
aws lambda get-function-configuration --function-name <name> | \
  jq '{last_modified: .LastModified, code_sha256: .CodeSha256, environment: .Environment.Variables}'

# aws_rds_cluster: engine_version, parameter_group_name
aws rds describe-db-clusters --db-cluster-identifier <id> | \
  jq '.DBClusters[0] | {engine_version: .EngineVersion, parameter_group_name: .DBClusterParameterGroup}'

# aws_security_group: ingress, egress
aws ec2 describe-security-groups --group-ids <id> | \
  jq '.SecurityGroups[0] | {ingress: .IpPermissions, egress: .IpPermissionsEgress}'

# aws_apigatewayv2_api: routes, integrations
aws apigatewayv2 get-routes       --api-id <id> | jq '.Items'
aws apigatewayv2 get-integrations --api-id <id> | jq '.Items'
```

**Equality semantics** (avoid false drift from cosmetic differences):
- Strings: trim trailing whitespace, normalize unicode
- Lists/sets of rules (SG ingress/egress, API GW routes): order-independent set comparison; compare by stable identity (cidr+port+protocol for SG; method+route_key for API GW)
- Maps (Lambda environment): key-by-key comparison; report missing keys, extra keys, and value mismatches separately
- Numbers: exact equality (no floating-point tolerance — fingerprint fields are discrete config)
- Timestamps (Lambda `last_modified`): excluded from "drift" by default — see triage below; treated as informational only

### Phase D — Triage membership δ

Tri-state classification: every δ item resolves to **keep** (bring under TF management), **delete** (remove from AWS or state), or **review** (human decides). The default is `review` when intent is ambiguous — never auto-import or auto-delete past doubt.

For each ORPHAN:

```
keep family:
  if r.observer_class is True:                                   verdict = "import-now"
  elif r matches triage.always_import_classes:                   verdict = "import-now"
  elif r had_recent_activity (last 7d via CloudTrail or metrics) AND incoming_refs is non-empty:
                                                                  verdict = "import-now"

delete family:
  elif r matches triage.empty_shell_patterns AND incoming_refs is empty:
                                                                  verdict = "delete-empty-shell"
  elif r matches triage.empty_shell_patterns AND every entry in incoming_refs is dead/out-of-scope:
                                                                  verdict = "delete-empty-shell"  (multi-step — see below)

review family:
  elif r matches policy.exceptions[*].resource_pattern:           verdict = "review"
  elif r matches triage.empty_shell_patterns AND incoming_refs has live in-scope entries:
                                                                  verdict = "review"
  elif r had_recent_activity AND incoming_refs is empty:          verdict = "review"   # active but unreferenced — investigate
  else:                                                           verdict = "review"
```

For each GHOST:

```
keep family:
  (none — by definition GHOST has no AWS presence)

delete family:
  if r.source_state_file.role == "primary":                       verdict = "state-rm-now"
  elif r.source_state_file.role == "deprecating":                 verdict = "state-rm-from-deprecating"
                                                                  # priority: drain `deprecating` first

review family:
  if r matches policy.exceptions[*].resource_pattern:             verdict = "review"
```

For each DOUBLE:

```
delete family:
  if both bindings reference the same AWS ID:
                                                                  verdict = "dedup-state-rm-from-deprecating"
                                                                  # canonical binding stays in `primary`
  if bindings reference DIFFERENT AWS IDs (DIVERGED-IDS sub-case):
                                                                  verdict = "dedup-state-rm-from-deprecating"
                                                                  # primary's binding is canonical; the deprecating
                                                                  # AWS ID becomes ORPHAN on next audit
```

For each HALT:

```
keep family:
  if r matches triage.always_import_classes
       OR r had_recent_activity (last 7d)
       OR r.observer_class is True:
                                                                  verdict = "import-to-primary-then-rm-from-deprecating"
                                                                  # two-step: write source to primary tree, terraform import,
                                                                  # then state rm from deprecating

delete family:
  if r matches triage.empty_shell_patterns AND incoming_refs is empty:
                                                                  verdict = "delete-empty-shell"
                                                                  # rare: HALT that's also dead — AWS delete + state rm

review family:
  default:                                                        verdict = "halt-defer"
                                                                  # state rm from deprecating now (Option B);
                                                                  # accept temporary un-management;
                                                                  # next audit will surface as ORPHAN with verdict=import-now
```

The default `halt-defer` exists because HALT entries usually arise from a partially-completed state-file split. Forcing `import-to-primary` in the same pass that drains the deprecating file blocks Stage 1 progress on writing source. The deferred path is safe **only if** the follow-up absorb pass is scheduled; the audit output flags any HALT entry whose source has not landed in primary within the configured grace window (`x.halt_defer_grace_days`, default 7).

#### Multi-step delete output (T3.b)

When a `delete-empty-shell` ORPHAN has non-empty `incoming_refs` (all dead), emit the dependency-ordered command sequence — *not* a single `delete` that AWS will reject. Example for SG with peer ingress:

```bash
# Two-step delete for orphan SG sg-03e0bb93ea6bd920e
# Reason: 0 ENIs, but referenced by ingress rule on out-of-scope sg-02530c9c16142e463

# Step 1: revoke the incoming reference (run against the *referencing* resource)
aws ec2 revoke-security-group-ingress \
  --group-id sg-02530c9c16142e463 \
  --protocol tcp --port 5432 --source-group sg-03e0bb93ea6bd920e

# Step 2: now safe to delete the orphan SG
aws ec2 delete-security-group --group-id sg-03e0bb93ea6bd920e
```

For IAM roles with attached policies / instance profiles: detach in dependency order (instance-profile-remove-role → detach-role-policy → delete-role) before deleting the role. The output for any `delete-empty-shell` with non-trivial `incoming_refs` must list every step.

### Phase D2 — Triage drift δ (NEW)

For each `DriftEntry`, classify by **field semantics** (which side is authoritative for that field):

```
default field-direction map:
  aws_lambda_function.last_modified     → informational  # AWS-authoritative timestamp; not real drift
  aws_lambda_function.code_sha256       → aws-wins       # deployment artifact lives in AWS
  aws_lambda_function.environment       → review         # intent unclear — could be Doppler push or console edit
  aws_rds_cluster.engine_version        → review         # could be planned upgrade or unplanned
  aws_rds_cluster.parameter_group_name  → tf-wins        # parameter groups are declared in TF
  aws_security_group.ingress            → review         # rules deleted in console (validation 2026-04-27)
  aws_security_group.egress             → review
  aws_apigatewayv2_api.routes           → review         # routes added by deploy script vs TF
  aws_apigatewayv2_api.integrations     → review

verdict resolution:
  if all drifted fields == informational  → verdict = "informational"   (no action needed)
  if any drifted field    == review       → verdict = "review"          (human chooses direction)
  elif all drifted fields == aws-wins     → verdict = "refresh-tf"      (terraform refresh + commit)
  elif all drifted fields == tf-wins      → verdict = "apply-tf"        (terraform apply to push)
  else                                    → verdict = "review"          (mixed direction → human)
```

**Why "review" is the default for ambiguous fields**: the same field can drift for opposite reasons. Lambda `environment` missing a key may mean:
- TF declared it but deploy push failed → `apply-tf` (push to AWS)
- Live Lambda has extra key set in console → `refresh-tf` (pull into TF)

`/tf-aws` cannot tell these apart from a single snapshot. CloudTrail history can disambiguate (look for `UpdateFunctionConfiguration` events with `Console` userAgent vs CI principal), but that's an enrichment beyond this phase. Today, default to `review` and let the human read CloudTrail.

**Hard-coded review patterns from `policy.exceptions` apply here too**: if a TRACKED resource also matches a `policy.exceptions[*].resource_pattern`, force `verdict = "review"` regardless of field-direction map.

#### Codebase-aware direction inference for Lambda env drift (T3.d)

Lambda `environment` is the highest-volume `review` source in this project (Doppler injects 9 keys at runtime; TF declares 25; the ~16-key diff trips Phase C2 every audit). The default `review` verdict is correct in absence of context, but the codebase contains the context: each env var either *is* read by application code or *isn't*. Use that signal to refine the verdict before kicking it to a human.

For each TRACKED Lambda with environment drift `(tf_keys, aws_keys)`:

```python
# Discover which Lambda this is and where its source lives
lambda_src_dir = locate_lambda_source(r.terraform_address)
# e.g. aws_lambda_function.telegram_api → src/api/

for key in tf_keys - aws_keys:        # TF declares, AWS missing at runtime
    used_in_code = grep_count(key, [
        f"{lambda_src_dir}/**/*.py",
        "src/types.py",                # required-vars validators
        f"{lambda_src_dir}/**/__init__.py",
    ])
    runtime_injected = key in DOPPLER_INJECTED_KEYS    # known list per Lambda

    if used_in_code > 0 and not runtime_injected:
        # TF declares it, code reads it, runtime can't inject — real bug
        verdict = "apply-tf"          # push the env var to AWS via terraform apply
        reason = f"used in code at {grep_locations(key)}; not in Doppler runtime injection set"
    elif used_in_code > 0 and runtime_injected:
        # TF declares it, code reads it, runtime DOES inject — TF is over-declaring
        verdict = "trim-spec"         # remove from TF; let Doppler own it
        reason = f"runtime-injected by Doppler; TF declaration is duplicate"
        suggested_lifecycle = 'lifecycle { ignore_changes = [environment] }'
    else:
        # TF declares it, no code reads it — dead declaration
        verdict = "trim-spec"
        reason = "declared in TF but not read anywhere in the Lambda's source tree"

for key in aws_keys - tf_keys:        # AWS has, TF lacks
    used_in_code = grep_count(key, [...])
    if used_in_code > 0:
        verdict = "refresh-tf"        # AWS-authoritative; pull into TF
        reason = "code reads the key; AWS provides it; declare it in TF"
    else:
        verdict = "review"             # extra runtime config no code reads — investigate
        reason = "AWS Lambda env has key but no code reads it; was it set manually?"
```

This converts the previous monolithic `review` verdict for env drift into per-key verdicts: `apply-tf` (real bug), `trim-spec` (over-declared), `refresh-tf` (under-declared), `review` (still ambiguous). The human only sees the residue.

The `DOPPLER_INJECTED_KEYS` set is project-specific and must be supplied by the replica config or detected via runtime probe (e.g., temporarily logging `os.environ.keys()` from the Lambda handler — Plug #2 journal **before** removing the probe). For dr-bot, today's known set per Lambda lives in:

- `src/api/app.py` and `src/telegram_lambda_handler.py` — telegram_api
- `src/handlers/line_bot_handler.py` — line_bot
- `src/report_worker_handler.py` — report_worker
- `src/handlers/ticker_scheduler.py` — ticker_scheduler

### Phase E — Verb dispatch

Switch on verb:

- **audit**: print summary table only — counts of TFM, LIVE, TRACKED, ORPHAN, GHOST, DOUBLE, HALT, DRIFTED
- **diff**: print full triage table with all δ items, including DRIFTED section with per-field tf vs aws values
- **absorb**: emit absorption artifacts (commands + `.tf` source) for `import-now` ORPHANs — see "Absorb output: hand-write vs auto-generate" below; membership only, does NOT mutate config of TRACKED resources
- **prune**: emit `terraform state rm` for `state-rm-now` GHOSTs + DOUBLEs (membership only)
- **sync**: absorb then prune in sequence (membership only)
- **DRIFTED items are NOT auto-resolved by any verb** — see "DRIFTED reconciliation" below

#### Absorb output: hand-write vs auto-generate (per-ORPHAN fork)

Two valid ways to bring an ORPHAN under TF management. The skill picks one per ORPHAN; the choice is a property of the ORPHAN, not a global flag.

| | **Approach 1 — hand-write** | **Approach 2 — auto-generate** |
|---|---|---|
| Output | `terraform import <addr> <id>` + a hand-written `.tf` stub written into `terraform/imported_orphans.tf` | An `import {}` block in `terraform/imported_orphans.tf`; the operator runs `terraform plan -generate-config-out=terraform/<resource>.tf` to materialize the source |
| Source-of-truth for fields | the team's intent — fields the stub omits will be set to AWS-current on first apply, but defaults are reified explicitly | AWS reality — every non-default attribute is captured verbatim |
| TF version | any | requires Terraform ≥ 1.5 |
| Sensitive fields | safe — the stub only declares fields the team chose | risky — auto-gen captures every attribute including possibly-sensitive ones (review required before commit) |
| Loop closure | one `terraform apply` after import | two-step: `plan -generate-config-out` → review → `apply` |

**Pick Approach 2 when ALL of the following hold**:

- ORPHAN's verdict is `import-now` AND came from `triage.always_import_classes` or `r.observer_class is True` (i.e., the team has **no opinion** about non-default fields — they want whatever AWS is doing)
- The resource type's `projection.fingerprint_fields` does not include sensitive material (no env-var maps, no secrets, no IAM policy documents likely to contain identifiers)
- Terraform CLI version available is ≥ 1.5

**Pick Approach 1 in all other cases**, including:

- ORPHAN was admitted via `had_recent_activity` heuristic (operator may want to *change* fields, not codify console drift)
- Resource type stores secrets or has fields the team intends to manage explicitly (Lambda environment, IAM policy attachments, SG rules)
- Generated config would be larger than ~50 lines (review burden swamps the convenience)

The decision is per-ORPHAN; an absorb run typically emits a mix. The output groups them into two sections so the operator reviews each batch differently:

```
ABSORB OUTPUT — replica=dr-bot
══════════════════════════════════════════════════════════════════════
Approach 2 (auto-gen, review terraform plan output before apply): <N₂>
  - aws_cloudwatch_log_group.dr-daily-report-quant-agent-dev   ← observer_class
  - aws_iam_role.scheduled_lambda                              ← always_import_classes

  → Edits required:
       terraform/imported_orphans.tf: add import {} blocks (below)
       Then run: terraform plan -generate-config-out=terraform/<resource>.tf

Approach 1 (hand-write stub + import command): <N₁>
  - aws_lambda_function.quant_agent                            ← had_recent_activity
  - aws_security_group.line-bot-ticker-report-sg               ← had_recent_activity

  → Edits required:
       terraform/imported_orphans.tf: paste the stubs (below)
       Then run: terraform import <addr> <id>  (one per ORPHAN)
```

Each ORPHAN entry in `diff` output annotates which approach the absorb verb would emit for it, so the operator can preview before running.

**Why the fork exists**: Approach 2 is mostly better for verified ORPHANs (no risk of stub-vs-AWS drift on first apply, no manual transcription errors), but it has two failure modes that Approach 1 doesn't — codifying console drift into source as if it were intent, and bulk-redacting sensitive fields the operator forgot were in the auto-gen output. The fork is a default choice between "trust AWS as source" (Approach 2) and "the operator declared intent" (Approach 1), per-ORPHAN, based on how the ORPHAN got promoted to `import-now` in the first place.

### Phase F — Confirmation gate (only on `--apply` for mutating verbs)

Display the planned changes. Wait for `y/N` from user.

#### Phase F.5 — Backend-reference sweep (PRE-APPLY GUARD)

Before any mutating verb runs, audit every entry point that initializes the Terraform backend, to ensure no CI workflow or developer recipe is still wired to a `deprecating` state file. A workflow that runs `terraform init -backend-config="key=<deprecating-path>"` will produce phantom mass-CREATE plans (the deprecating state binds a fraction of declared resources), and any auto-apply downstream is catastrophic.

```bash
# All known entry points that init the backend
sweep_paths=(
  ".github/workflows"          # CI
  "justfile"                   # local recipes
  "Justfile"                   # alternate casing
  "scripts"                    # ad-hoc shell scripts
  "terraform/envs"             # backend.hcl per env
  "Makefile"                   # legacy makefiles
)

# For each, surface every backend-key reference
for path in "${sweep_paths[@]}"; do
  grep -rEn '(backend-config=|key\s*=).*\.tfstate' "$path" 2>/dev/null
done

# Compare against state.role
# - role=primary       → OK
# - role=deprecating   → ABORT mutating verb; require explicit override flag
```

The sweep refuses `--apply` if any deprecating-keyed entry point exists. Override with `--allow-deprecating-backend` (loud flag; documents the intent in the apply log).

This phase is the institutional memory of the 2026-04-30 CI regression: `.github/workflows/terraform-test.yml` had `key="dev/terraform.tfstate"` (legacy) for months before discovery. The sweep makes that class of bug fail closed instead of fail silent.

### Phase G — Execute (only after `y`)

The destructive verb runs *bracketed* by an invariant assertion. Phase G's backup is byte-level reversibility (you can restore the file). The bracket adds **semantic** assertion: did the verb stay inside its declared scope? This catches misdirection bugs that Phase F's y/N gate cannot — for example, the verb hits the wrong state file because the working directory was initialized against the wrong backend, even though the address list looks fine.

```
G.1 Backup        → byte-level reversibility
G.2 Capture       → pre-verb invariant snapshot (computed, not narrated)
G.3 Run verb      → terraform import / state rm / stub-write
G.4 Re-fetch      → re-read state files from S3 (verb may have changed them)
G.5 Re-capture    → post-verb invariant snapshot
G.6 Assert        → declared invariant must hold; auto-restore on failure
```

**G.1 — Backup state** (unchanged):
```bash
mkdir -p .terraform-state-backups
cp /tmp/tf_state_*.json ".terraform-state-backups/$(date -u +%Y%m%dT%H%M%SZ)/"
```

**G.2 — Pre-verb invariant capture**:

The invariant declares the *verb's declared scope* in computed form. Each in-scope state file gets a managed-resource count; the verb's address list is partitioned by target file; the per-file expected change is computed as `(file_target → -N)` for prunes / `+N` for absorbs / `0` for files **not** in the verb's address list.

```python
invariants_pre = {
    file_uri: {
        "managed_count": jq_count_managed(file_uri),
        "expected_delta": +<N> | -<N> | 0,   # 0 means "must NOT change"
    }
    for file_uri in replica.x.files
}
```

For Stage 1's prune of 24 entries from deprecating: `invariants_pre = { primary: count=208 expected_delta=0; deprecating: count=24 expected_delta=-24 }`. The `expected_delta=0` on primary is what catches misdirection.

**G.3 — Run verb**: execute generated `terraform import` / `terraform state rm` / append stubs to `terraform/imported_orphans.tf`.

**G.4 — Re-fetch state**: re-download every in-scope state file from S3. Don't trust `/tmp/tf_state_*.json` from Phase A — the verb just changed those.

**G.5 — Post-verb invariant capture**:
```python
invariants_post = {
    file_uri: {"managed_count": jq_count_managed(file_uri)}
    for file_uri in replica.x.files
}
```

**G.6 — Assert**:
```python
for file_uri, inv in invariants_pre.items():
    expected = inv["managed_count"] + inv["expected_delta"]
    actual   = invariants_post[file_uri]["managed_count"]
    if actual != expected:
        ABORT(file=file_uri, expected=expected, actual=actual)

if ABORTED:
    print("⛔ INVARIANT VIOLATION — verb scope exceeded declaration")
    print("   Auto-restoring state files from .terraform-state-backups/<ts>/")
    aws s3 cp <backup>/<file>.json s3://<bucket>/<key>
    exit non-zero
```

**G.7 — Stub append** (only if G.6 passed): write `.tf` stubs to `terraform/imported_orphans.tf` (append, with date header comments). Approach 2 ORPHANs get `import {}` blocks instead — the operator's next move is `terraform plan -generate-config-out=...` per the absorb output.

**G.8 — Print**: "review and `terraform plan` before any subsequent `terraform apply`."

The point of the bracket: at every prior pass before adding G.2/G.4–G.6, the *only* thing that protected against verb-scope misdirection was operator vigilance reading Phase F's address list. The invariant turns that protection into a property the skill enforces, regardless of whether anyone is watching.

### Phase H — Verify (Layer 4 evidence per Principle #2)

Re-run Phases A through C2 (and A.5). Report residual δ on all three axes:

```
✅ δ converged
   δ_source     (Edge A):  0 UNREALIZED-INTENT, 0 UNDECLARED-IMPORT
   δ_membership (Edge B):  0 ORPHAN, 0 GHOST, 0 DOUBLE, 0 HALT
   δ_config     (Edge B):  0 DRIFTED   (out of <N> TRACKED resources fingerprinted)
```

or:

```
⚠️ Residual δ
   δ_source     (Edge A):  <U1> UNREALIZED-INTENT, <U2> UNDECLARED-IMPORT  (terraform apply or stub-write)
   δ_membership (Edge B):  <O> ORPHAN, <G> GHOST, <D> DOUBLE, <H> HALT      (membership verbs can fix; HALT may need source-write first)
   δ_config     (Edge B):  <X> DRIFTED                                       (requires human direction-of-change)
   See /tf-aws diff for details.
```

Note: a `--apply` of `absorb`/`prune`/`sync` may import an ORPHAN that itself has config drift (e.g., its current AWS config differs from any future TF declaration we synthesize). The post-apply Phase C2 catches that — newly-imported items are immediately fingerprinted against their generated `.tf` stubs.

#### Phase H self-test — coverage assertions (audit refuses to claim ✅ if any fall short)

The audit reports a number — "<N> TRACKED resources fingerprinted." A reader trusts that number to mean "every TRACKED resource of a fingerprintable type was hit." The audit refuses to size that claim if any of the following are false. This is the BS-6 plug — preventing audit-execution skew (the gap between what the audit claims to have measured and what it actually measured):

```
COVERAGE_ASSERTIONS:

  state_files_read:
    expected = len(x.primary) + len(x.legacy)            # from replica config
    actual   = number of state files successfully fetched and parsed
    fail_if  = expected != actual

  hcl_files_parsed:
    expected = count(`find terraform -name '*.tf' -not -path '*/.terraform/*'`)
    actual   = number of files Phase A.5 actually parsed
    fail_if  = expected != actual

  push_pass_executed:
    expected = "CloudTrail lookup-events returned non-zero events for the 7-day window"
    fail_if  = events == 0  AND  account is not a fresh sandbox

  observer_pass_executed:
    expected = "B2 enumerated alarms, log groups, trails, snapshots"
    fail_if  = any of these classes returned an API error AND was not handled

  fingerprintable_resources_hit:
    for each resource type T in projection.fingerprint_fields:
      expected = count(TRACKED resources of type T)
      actual   = count(TRACKED resources of type T whose live config was successfully read)
      fail_if  = expected != actual

  triage_completeness:
    expected = every UNREALIZED-INTENT, UNDECLARED-IMPORT, ORPHAN, GHOST, DOUBLE, HALT, DRIFTED has a verdict
    fail_if  = any δ entry has verdict == None

  freshness:
    expected = audit data is < 1 hour old at time of report
    fail_if  = (now - audit_start_time) > 1 hour

  invariant_bracket_executed:                       # only if --apply ran a mutating verb
    expected = Phase G.2 (pre-capture) AND G.5 (post-capture) AND G.6 (assert) all completed
    fail_if  = any of {pre_snapshot, post_snapshot, assertion_result} is missing from the apply log
    note     = absence here means the verb ran without the bracket — the audit's PASS verdict
               cannot prove the verb stayed in scope; only that residual δ is 0 *now*
```

If any assertion fails, the audit prints `⚠️ Audit incomplete — coverage assertion failed:` and refuses to print a ✅ verdict. The user must re-run with the failing condition addressed (extra credentials, longer timeout, etc.) before any verdict is rendered. The CLI exit code is non-zero in this case so CI doesn't accidentally green-light an incomplete audit.

---

## Output formats

### `audit`

```
🔍 /tf-aws audit  •  replica=dr-bot  •  <timestamp>
   Audit started: <iso8601>     ← coverage assertion: < 1h ago at report time
   Coverage:      <K> state files | <M> .tf files | <P> push events | <O> observers

  Source ↔ State (Phase A.5 — Edge A)
  ──────────────────────────────────────────────────────────────
  SRC (parsed from .tf):  S blocks across <M> files
  TFM (tracked state):    N resources in K state files
                            ├─ primary:       P resources
                            └─ deprecating:   D resources

  δ_source
    UNREALIZED-INTENT (declared in .tf, not bound):  U1
      ├─ run-apply       a  (real pending apply)
      ├─ ignore-changes  i  (lifecycle.ignore_changes — intentional)
      └─ review          v
    UNDECLARED-IMPORT (bound in state, no .tf block):  U2
      ├─ pending-stub          s  (recently imported; stub pending)
      ├─ likely-stale-state    l  (in deprecating state file)
      └─ undeclared-import     u  (loud failure)

  State ↔ AWS membership (Phase A + B + C — Edge B)
  ──────────────────────────────────────────────────────────────
  LIVE (deployed, scoped):   M resources
  TRACKED (TFM ∩ LIVE):      T resources

  δ_membership
    ORPHAN  (in AWS, not in state):     O
      ├─ keep family   (import-now):           Ok
      ├─ delete family (delete-empty-shell):   Od
      └─ review family:                         Or
    GHOST   (in state, not in AWS):     G
      ├─ state-rm-now (from primary):         Gp
      ├─ state-rm-from-deprecating:           Gd
      └─ review:                               Gr
    DOUBLE  (in multiple state files):  D
      └─ dedup-state-rm-from-deprecating:     D

  State ↔ AWS config fingerprint (Phase C2 — Edge B)
  ──────────────────────────────────────────────────────────────
  Fingerprinted (types with declared fields):  F  (out of T TRACKED)
  Skipped (no fingerprint declared):           T-F

  δ_config
    DRIFTED (TF ≠ AWS on declared fields):  X
      ├─ informational  i  (timestamps; no action)
      ├─ apply-tf       a  (TF declares value; push to AWS via terraform apply)
      ├─ refresh-tf     r  (AWS-authoritative; pull into TF via refresh)
      ├─ trim-spec      t  (over-declared in TF; remove from .tf)
      └─ review         v  (intent ambiguous; human decides)

  Last drift signal: <date>  (<event description>)

  Run `/tf-aws diff` for details.
  Source:     `terraform apply` for UNREALIZED-INTENT; write stubs for UNDECLARED-IMPORT.
  Membership: `/tf-aws absorb --apply`, `/tf-aws prune --apply`.
  Config:     see "DRIFTED reconciliation" — no auto-apply.
```

### `diff`

```
🔍 /tf-aws diff  •  replica=dr-bot
   δ_membership: <O> ORPHAN | <G> GHOST | <D> DOUBLE | <H> HALT
   δ_config:     <X> DRIFTED  (i info, a apply-tf, r refresh-tf, v review)

  ORPHANS (in AWS, not in state) — <O>
  ──────────────────────────────────────────────────────────────
  ✅ <terraform_address>
       arn: <arn>
       last activity: <date>
       verdict: import-now
       reason: <reason>

  ⚠️  <terraform_address>
       verdict: review
       reason: matches policy.exceptions

  ❓ <terraform_address>
       verdict: delete-empty-shell
       reason: <empty-shell pattern matched>

  GHOSTS (in state, not in AWS) — <G>
  ──────────────────────────────────────────────────────────────
  ✂  <terraform_address>  →  state-rm-now

  DOUBLES (in multiple state files) — <D>
  ──────────────────────────────────────────────────────────────
  ✂  <terraform_address>  →  state-rm from <legacy_state_file>

  DRIFTED (in both, but config disagrees) — <X>
  ──────────────────────────────────────────────────────────────
  🟠 <terraform_address>  (<aws_resource_type>)
       verdict: review
       fields:
         environment:  TF declares  {OPENROUTER_API_KEY: "***", PDF_STORAGE_BUCKET: "..."}
                       AWS has      {AURORA_HOST: "...", AURORA_PORT: "3306"}
                       diff: 2 keys missing in AWS, 0 extra, 0 value-mismatch
       direction-of-change: ambiguous — see CloudTrail UpdateFunctionConfiguration history

  🟢 <terraform_address>  (<aws_resource_type>)
       verdict: refresh-tf
       fields:
         code_sha256:  TF declares  abc123...
                       AWS has      def456...
       direction-of-change: aws-wins (deployment artifact lives in AWS)
       fix: terraform refresh && commit state

  🔵 <terraform_address>  (<aws_resource_type>)
       verdict: apply-tf
       fields:
         parameter_group_name:  TF declares  custom-pg-v2
                                AWS has      default.aurora-mysql8
       direction-of-change: tf-wins (parameter groups are declared in TF)
       fix: terraform apply
```

### `absorb --apply`

```
📥 /tf-aws absorb --apply  •  replica=dr-bot

  Plan:
    [import-now]      <count> resources
    [review]          <count> resources (SKIPPED — re-run with --include-review)
    [delete-shell]    <count> (use /tf-aws prune ... or console for shells)

  Generated commands:
    terraform import <addr1> <id1>
    terraform import <addr2> <id2>
    ...

  Generated .tf stubs:
    terraform/imported_orphans.tf  (will append <count> resource blocks)

  Apply? [y/N]
```

### Post-apply

```
✅ Imported <count> resources
✅ State backed up to .terraform-state-backups/<timestamp>/
✅ .tf stubs written to terraform/imported_orphans.tf

🔄 Re-running discovery to verify δ → 0 ...

✅ δ converged. ORPHAN=0, GHOST=0, DOUBLE=0, HALT=0

Next: review terraform/imported_orphans.tf, then `terraform plan` to verify no further changes.
```

---

## DRIFTED reconciliation

Once Phase C2 surfaces a DRIFTED item, the resolution forks by **which side wins** and **how**:

```
DRIFTED → TF wins  → apply-tf      (push .tf declaration to AWS)
        → AWS wins → refresh-tf    (pull AWS values into .tfstate; .tf untouched)
                   → trim-spec     (edit .tf to remove over-declared fields)
        → unclear  → review        (CloudTrail + decide direction)
        → ignore   → informational (drift acknowledged, not resolved)
```

| Phase D2 verdict | What to do | Mutates AWS? | Tooling |
|---|---|---|---|
| `informational` | Nothing | No | — |
| `apply-tf` | Push TF declaration to AWS | **YES** | `terraform apply` (outside this command) |
| `refresh-tf` | Pull AWS-authoritative value into TF state | No (state only) | `terraform refresh` then commit |
| `trim-spec` | Edit `.tf` to remove over-declared fields (AWS wins by deletion of source) | No (source only) | Manual editor + commit |
| `review` | Read CloudTrail, decide direction, then apply / refresh / trim | Maybe | Human + one of the above |

**Why `/tf-aws` does NOT auto-resolve DRIFTED**: this command's safety property is "AWS reality is read-only". An `apply-tf` resolution mutates AWS (e.g., overwrites Lambda env vars, recreates SG rules). That's a `terraform apply` — a deliberate, change-managed action — not a reconciliation we silently perform.

**Anti-pattern to avoid**: do NOT add a `/tf-aws drift --apply` verb that runs `terraform apply` for the user. Drift resolution is a directional decision (which side wins per field) and a deployment event (it changes AWS). Keep those decisions explicit and out of this command.

**Recommended workflow when DRIFTED items appear**:

1. Run `/tf-aws diff` and read the DRIFTED section.
2. For `informational` items: ignore.
3. For `refresh-tf` items: `terraform refresh && terraform plan` (should show no changes); commit the updated state.
4. For `apply-tf` items: review the planned change with `terraform plan`, then `terraform apply` if intent matches.
5. For `trim-spec` items: hand-edit the `.tf` to remove the over-declared fields. Run `terraform plan` and confirm "No changes" before committing. **Journal first** (Plug #2 — the original intent vanishes from the spec once trimmed).
6. For `review` items: read CloudTrail history for the resource (`aws cloudtrail lookup-events --lookup-attributes AttributeKey=ResourceName,AttributeValue=<id>`) to learn who changed what when. Decide direction. Apply / refresh / trim accordingly. Document the decision in `.claude/journals/`.
7. Re-run `/tf-aws audit` to verify `δ_config = 0`.

---

## End-to-end replica reconciliation

The full sequence to bring a replica's three views (`.tf` source, `.tfstate`, AWS reality) into agreement. `/tf-aws` automates only some of these; the rest are deliberate human-in-the-loop steps.

```
┌──┐ 1. /tf-aws audit
│  │    → see δ_source, δ_membership, and δ_config counts
│  │
│  │ 2. Resolve δ_source (Edge A):
│  │      UNREALIZED-INTENT → terraform apply (mutates AWS) OR add lifecycle.ignore_changes
│  │      UNDECLARED-IMPORT → write .tf stub OR investigate (loud failure for unreviewed)
│  │
│  │ 3. /tf-aws sync --apply
│  │    → close δ_membership (absorb ORPHANs, prune GHOSTs)
│  │    → leaves DRIFTED items untouched (δ_config unchanged)
│  │
│  │ 4. /tf-aws audit again
│  │    → expect δ_source = 0 AND δ_membership = 0; remaining work is δ_config
│  │
│  │ 5. For each DRIFTED item, follow § "DRIFTED reconciliation":
│  │      apply-tf      → terraform apply (TF wins; mutates AWS)
│  │      refresh-tf    → terraform refresh + commit (AWS wins, value sync)
│  │      trim-spec     → hand-edit .tf + commit (AWS wins, source narrows)
│  │      review        → CloudTrail + decide direction
│  │      informational → ignore
│  │
│  │ 6. /tf-aws audit
│  │    → expect δ_source = 0 AND δ_membership = 0 AND δ_config = 0
│  │    → AND Phase H self-test: all coverage assertions pass
│  │    → ✅ within the audit's measurement surface
│  │
│  │ 7. terraform plan          ← residual Edge A field-level check
│  │    → expect "No changes."
│  │    → non-empty diff means a non-fingerprinted field has unrealized intent
│  │      (Phase A.5 catches address-level; this catches field-level on
│  │       fields outside projection.fingerprint_fields)
│  │
│  │ 8. Apply BS-1 plug (runtime smoke)
│  │    → invoke each Lambda; check CloudWatch for errors
│  │    → config-correctness ≠ behavioral-correctness
│  ▼
   replica converged across all three views
```

**Why steps 7 and 8 are still outside `/tf-aws`**:

- Step 7 (`terraform plan`) covers field-level Edge A on fields NOT in `projection.fingerprint_fields`. Phase A.5 caught block presence; Phase C2 caught fingerprint fields; `terraform plan` catches everything else. Cheapest tool for the residual gap.
- Step 8 (runtime smoke) catches BS-1 (layer-coverage) — config-correctness without behavioral verification is the classic "passed audit, still broken" failure mode.

After step 8, "system healthy" is a defensible claim. Before step 8, ✅ means "TF source, TF state, and AWS agree on the scoped fingerprint fields, and `.tf` blocks bind cleanly to state — but you haven't verified anything actually runs."

**Three views, three edges, three plugs** (post-2026-05-01):

```
.tf source  ──edge A──►  .tfstate  ──edge B──►  AWS reality
   (intent)             (realized)                (deployment)

edge A (block-level):  measured by  /tf-aws audit Phase A.5  (steps 1, 4, 6)
edge A (field-level):  measured by  terraform plan            (step 7 — residual plug)
edge B (membership):   measured by  /tf-aws audit Phases A/B/C
edge B (fingerprint):  measured by  /tf-aws audit Phase C2
runtime (BS-1):        measured by  invoke + CloudWatch       (step 8)
audit-execution skew:  measured by  Phase H self-test          (built into every audit; BS-6)
```

---

## Blind spots and limits — what `δ = 0` does and does not prove

A passing audit (`δ_membership = 0` AND `δ_config = 0`) means: **"TF and AWS agree on the enumerated fields of in-scope resources at this moment."** It does **not** mean the system is healthy, the spec is intentional, or that nothing important is changing under the hood.

The audit measures *agreement*, not *correctness*. ✅ has a narrow technical meaning that is easy to mistake for the broad colloquial meaning. Calibrate accordingly: a complete invariant check (per Principle #25) composes `/tf-aws audit` (Levels 4 + part of 3) with **outside-the-audit** checks (Levels 0, 1, 2, full 3) and **persisted memory** (journals).

The audit has five structural blind spots. Each has a cheap mitigation that lives outside this command. Four of them (BS-1 through BS-4) are about what `/tf-aws audit` *measures imperfectly*; the fifth (BS-5) is about what `/tf-aws audit` *cannot measure at all*, because `.tf` source files are outside the audit's input scope.

### Visual framework — where each blind spot lives in the replica

The four categories below are easier to reason about as **regions** of the replica's coverage. The audit lives in one specific region; each blind spot lives in a different region — or in time. Use these visuals to decide quickly whether a concern is *inside* the audit's reach or *genuinely* a blind spot.

#### Visual A — Replica = (X, Y, projection, policy, triage)

```
                 The replica = (X, Y, projection, policy, triage)
                 ─────────────────────────────────────────────────

   ┌───────────────────────┐                  ┌───────────────────────┐
   │  X  =  TF state       │                  │  Y  =  AWS reality    │
   │       (S3 bucket,     │   ◄─────────►    │       (account+region │
   │        terraform.tf-  │     audit        │        + y.filter     │
   │        state file)    │     reads        │        for scoping)   │
   │                       │     both         │                       │
   └───────────┬───────────┘                  └───────────┬───────────┘
               │              ┌──────────────┐           │
               │              │  projection  │           │
               └──── + ──────►│  fields ◄────┼──── + ────┘
                              │  (per type)  │
                              └──────┬───────┘
                                     │
                                     ▼
              ┌─────────────────────────────────────────────┐
              │ The audit's measurement zone                 │
              │  Phase A/B → δ_membership                    │
              │    "is the resource on both sides?"          │
              │    uses: y.filter (which resources to check) │
              │                                              │
              │  Phase C2 → δ_config                         │
              │    "do the projection fields agree?"         │
              │    uses: projection.fingerprint_fields       │
              │           (which fields to diff)             │
              │                                              │
              │  policy → triage  (how to resolve found δ)   │
              └─────────────────────────────────────────────┘

   The audit can ONLY see what these parameters expose:
     which resources (y.filter)
     which fields    (projection.fingerprint_fields)
     at this moment  (snapshot, not history)
     at config layer (provisioning, not runtime)

   Every blind spot below is a thing OUTSIDE this measurement zone.
```

#### Visual B — Spatial picture (BS-1, BS-3, BS-4)

```
   ┌──────────────────────────────────────────────────────────────────────┐
   │ Universe — all AWS resources in account+region                        │
   │                                                                       │
   │     🕳️ BS-4 (scope-coverage) lives in this band                       │
   │       resources NOT matching y.filter:                                │
   │         · global IAM not name-matched                                 │
   │         · KMS keys outside dr-* / line-bot* / telegram-api*           │
   │         · log groups outside the patterns                             │
   │                                                                       │
   │   ┌──────────────────────────────────────────────────────────────┐   │
   │   │ y.filter SCOPE                                                │   │
   │   │ Phase A/B (δ_membership) catches every resource here          │   │
   │   │ that exists on one side and not the other. Includes           │   │
   │   │ resources that are their OWN TF type:                         │   │
   │   │   aws_iam_role_policy_attachment, aws_security_group_rule,    │   │
   │   │   aws_lambda_event_source_mapping, aws_route53_record, ...    │   │
   │   │                                                               │   │
   │   │   ┌─────────────────────────────────────────────────────┐     │   │
   │   │   │ projection.fingerprint_fields                        │     │   │
   │   │   │ Phase C2 (δ_config) diffs ONLY these fields:         │     │   │
   │   │   │   aws_lambda_function: last_modified, code_sha256,   │     │   │
   │   │   │                        environment                    │     │   │
   │   │   │   aws_rds_cluster:     engine_version,                │     │   │
   │   │   │                        parameter_group_name            │     │   │
   │   │   │   aws_security_group:  ingress, egress                 │     │   │
   │   │   │   aws_apigatewayv2_api: routes, integrations           │     │   │
   │   │   │                                                        │     │   │
   │   │   │   ┌─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ┐ │     │   │
   │   │   │   │ 🕳️ BS-1 (layer-coverage) — tracked but data    │ │     │   │
   │   │   │   │ flow never observed. Dashed = assumed, not    │ │     │   │
   │   │   │   │ proven. Audit reads fields; cannot invoke.    │ │     │   │
   │   │   │   └─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ┘ │     │   │
   │   │   └─────────────────────────────────────────────────────┘     │   │
   │   │                                                               │   │
   │   │   🕳️ BS-3 (field-coverage) lives in this band                 │   │
   │   │     fields on TRACKED resources, NOT in projection,           │   │
   │   │     AND NOT a separate TF resource type:                      │   │
   │   │       aws_lambda_function:  tags, timeout, memory_size,       │   │
   │   │                             layers,                           │   │
   │   │                             reserved_concurrent_executions,   │   │
   │   │                             tracing_config, dead_letter_config│   │
   │   │       aws_rds_cluster:      backup_retention_period,          │   │
   │   │                             deletion_protection               │   │
   │   │       aws_security_group:   tags, description                 │   │
   │   │       aws_apigatewayv2_api: tags, cors_configuration          │   │
   │   │                                                               │   │
   │   │     NOT BS-3 (caught by δ_membership above):                  │   │
   │   │       IAM policy attachments, SG rules, event source          │   │
   │   │       mappings — these are their own TF resource types        │   │
   │   └──────────────────────────────────────────────────────────────┘   │
   │                                                                       │
   └──────────────────────────────────────────────────────────────────────┘
```

#### Visual C — Temporal picture (BS-2)

BS-2 does not fit the spatial picture. It is about *the audit's memory of disagreement getting erased between two moments in time*. The right axis is a clock, not a region.

```
        t₀                          t₁                          t₂
   ─────────────                ──────────────              ──────────────
   PRE-RECONCILIATION          DESTRUCTIVE VERB             POST-RECONCILIATION
                                  (state rm / refresh /
                                   trim-spec)

   ┌──────────────────┐         ┌─────────────────┐        ┌──────────────────┐
   │ x:  declares X   │   ──►   │ verb collapses  │  ──►   │ x:  silent on X  │
   │ y:  lacks X      │         │ spec onto       │        │ y:  lacks X      │
   │ audit: 🔄 DRIFTED│         │ reality         │        │ audit: ✅ TRACKED│
   │ "they disagree"  │         └─────────────────┘        │ (audit cannot    │
   └──────────────────┘                                    │  see what was    │
                                                           │  once different) │
                                                           └──────────────────┘

   The diff WAS visible.       Diff erased from x.        Future audits return ✅.
   Audit could re-flag it.     Bytes preserved in state   The reason for the
                               backup; reason is not.     change is unrecoverable
                                                          from the audit alone.

   ──────────────────────────────────────────────────────────────────► time

                            🕳️ BS-2 (post-action amnesia)
                            = the difference between t₀ knowledge
                              and t₂ knowledge
                            Plug = journal AT t₀ (before t₁ fires).
                            The journal carries the reason past t₁.
```

#### Visual D — Decision tree: "will the audit catch drift on X?"

```
      ┌─────────────────────────────────────────────────────────┐
      │  Is X its own Terraform resource type?                   │
      │  (e.g. aws_iam_role_policy_attachment,                   │
      │   aws_security_group_rule, aws_route53_record)           │
      └────────────────┬────────────────────────────────────────┘
                       │
            ┌──────────┴──────────┐
           YES                    NO  (X is a FIELD on a resource)
            │                     │
            ▼                     ▼
   ┌──────────────────┐    ┌─────────────────────────────────┐
   │ Is its type      │    │ Is X listed in                  │
   │ in y.filter?     │    │ projection.fingerprint_fields   │
   │                  │    │ for its parent resource type?   │
   └────────┬─────────┘    └────────────┬────────────────────┘
            │                           │
        ┌───┴────┐                  ┌───┴────┐
       YES      NO                 YES      NO
        │       │                   │       │
        ▼       ▼                   ▼       ▼
   δ_membership 🕳️ BS-4         δ_config  🕳️ BS-3
   ✅ caught    (scope-         ✅ caught (field-
   by audit     coverage)       by audit  coverage)
                                          │
                                          ▼
                              Plug: extend
                              projection.fingerprint_fields
                              (one-line YAML edit per field).
                              Self-imposed gap, fixable.
```

This tree resolves the common confusion that *anything not surfaced by the audit* must be a blind spot. It is not. **A field that COULD be in the projection but isn't** is BS-3 (field-coverage — fixable by editing YAML). **A resource that COULD be in `y.filter` but isn't** is BS-4 (scope-coverage — a deliberate scoping choice). **A separate TF resource type within `y.filter`** (like `aws_iam_role_policy_attachment`) is **already caught by δ_membership** and is not a blind spot at all.

The tree does not cover BS-1 (layer-coverage) or BS-2 (post-action amnesia). Those are layer-of-evidence and time-axis gaps, not field-vs-resource gaps. See Visuals B and C respectively.

---

### 1. Layer-coverage — runtime/behavioral correctness is invisible

The audit operates at provisioning level. It can confirm a Lambda **exists** with the **expected config**; it cannot confirm the Lambda **runs correctly**. A correctly-shaped Lambda whose code crashes on every invocation, whose dependencies are misversioned, or whose VPC routing is broken will pass the audit unchanged.

Concretely, the audit cannot see:

- Lambda startup or invocation errors (the `Errors` CloudWatch metric)
- Whether SG ingress/egress rules actually permit the intended traffic (only that the rules exist)
- Aurora data integrity, schema validity, or row counts
- End-to-end user flows (LINE message → report; Mini App load → market data)

**Plug**: pair every audit run with per-Lambda CloudWatch error-metric checks and at least one Level-1 smoke test (e.g., LINE bot + a known-good ticker) and one Level-0 manual test for each user-facing flow under change.

### 2. Post-action amnesia — verbs that collapse spec onto reality erase intent

`state rm` (for GHOSTs), `terraform refresh` (for AWS-truthy DRIFTED items), and on-disk `.tf` edits that trim over-specified declarations all share a property: after the action, TF and AWS agree because the **spec was made smaller**, not because reality was made correct. The original disagreement is gone from the audit's view forever.

Concretely:

- After `state rm` of an Aurora SG rule deleted in console, future audits cannot distinguish "the rule was never wanted" from "the rule was deleted by mistake."
- After `trim-spec` of a Lambda env var that the validator wanted but no code consumed, future audits cannot recover the intent that the var was once declared.
- After `refresh` of a Lambda's `last_modified` field, the prior version of the state is overwritten without trace in the audit.

The TF state file is not an authoritative record of *intent*; it is a snapshot of what TF *thinks AWS looks like right now*.

**Plug**: journal the decision **before** running the destructive verb. `.claude/journals/architecture/<date>-<slug>.md` becomes the persisted memory the state file no longer carries. State backups (`.terraform-state-backups/`) preserve the *bytes* but not the *reason*; the journal preserves the reason.

### 3. Field-coverage — drift on undeclared fields is invisible

Phase C2 only compares the fields named in `projection.fingerprint_fields` (see `.claude/replicas/dr-bot.yaml`). For a TRACKED resource type with a partial fingerprint (e.g., `aws_lambda_function: [last_modified, code_sha256, environment]`), drift on **any other** field — `timeout`, `memory_size`, `vpc_config`, `tracing_config`, `dead_letter_config`, etc. — is silently invisible.

A resource type with **no** entry in `fingerprint_fields` skips Phase C2 entirely. Adding a new resource type to TF does not automatically extend the audit's reach.

**Plug**: extend `projection.fingerprint_fields` whenever a new dimension of drift surfaces. The cost is one YAML edit per dimension; the audit then catches it on every subsequent run. Treat field-coverage as a living artifact: it grows with each post-incident review.

### 4. Scope-coverage — out-of-filter resources don't exist to the audit

`y.filter` (tag-based `tag_app` plus `name_glob` fallback) defines what's "in scope" for the dr-bot replica. Resources without the right tags **and** without a matching name pattern are invisible regardless of whether they exist or what they do. A Lambda created in this AWS account by an unrelated team — or by an old experiment that didn't get tagged — is neither ORPHAN, GHOST, nor TRACKED. It is *outside the audit's universe*.

The replica's filter is a deliberate scoping decision (the Replica concept is one bot's view of one account, not the whole account). It is not a bug. But a reader who sees `δ = 0` and assumes "this account is clean" is misreading the verdict.

**Plug**: periodically run an unscoped sweep (e.g., `aws lambda list-functions` for the account/region with no tag filter) and compare against the union of all replicas' filters. Resources in the gap are either out-of-scope-for-good-reason or genuine cruft that no replica owns; both deserve review.

### 5. Source-state coverage — `.tf` ↔ `.tfstate` disagreement (now in scope as of 2026-05-01)

A replica has **three** views: `.tf` source files (intent), `.tfstate` (realized intent — written by `terraform apply` / `terraform import`), and AWS reality (deployment).

This was historically framed as a blind spot ("`/tf-aws` reads `.tfstate` and AWS, not `.tf` — run `terraform plan` separately"). That framing was wrong: it implicitly assumed every `.tf` edit is followed by an immediate `terraform apply`, which is empirically false. As of 2026-05-01, `Edge A` is a **first-class measurement** of `/tf-aws audit` (Phase A.5), not an out-of-scope concern.

Two ways disagreement appears, both surfaced by Phase A.5:

- **UNREALIZED-INTENT**: someone edits `.tf` (e.g., adds an env var, changes a timeout) and never runs `terraform apply`. Phase A.5 sees the block in `.tf` but no binding in `.tfstate`. Verdict: `run-apply` (or `ignore-changes` if `lifecycle.ignore_changes` says so).
- **UNDECLARED-IMPORT**: someone runs `terraform import` against a live AWS resource but never writes the corresponding `.tf` block. Phase A.5 sees the binding in `.tfstate` but no `resource` block. Verdict: `pending-stub` (write the block) or `undeclared-import` (loud failure for investigation).

What remains a true blind spot at this layer: structural disagreement *within* a block (e.g., the `.tf` declares `timeout = 60` but `.tfstate` shows `30`). That kind of difference is caught by `terraform plan`, not Phase A.5 — Phase A.5 is address-level only by design (field-level diff between `.tf` and `.tfstate` is what `terraform plan` already does well, and Phase C2 already handles `.tfstate` vs AWS for declared fingerprint fields). The composition is: Phase A.5 (address-level Edge A) + Phase C2 (field-level Edge B) + `terraform plan` (residual field-level Edge A on non-fingerprinted fields).

**Plug** (residual): for fields not in `projection.fingerprint_fields`, `terraform plan` remains the cheapest signal. Treat `terraform plan` as a complementary tool, not a replacement for Phase A.5 — they cover different things (block presence vs field values).

### 6. Audit-execution skew — the audit reports more coverage than it ran

The audit prints summaries: "<N> TRACKED resources fingerprinted", "<K> state files read", "<P> CloudTrail events processed". Each number is a *claim about what the audit measured*. If the underlying execution silently fell short — Phase B2 hit a permission error and skipped CloudWatch alarms; the legacy state file timed out on download; CloudTrail returned empty because the principal lacked `cloudtrail:LookupEvents`; the codebase grep in Phase D2 was run against a stale local checkout — the audit will still print a number, but the number will be smaller (or just wrong) than it should be. The reader interprets `δ = 0` as "everything checked, nothing wrong"; the underlying truth is "everything we managed to check, nothing wrong."

Concretely, this skew has appeared in past runs:

- The 2026-04-28 audit reported 1 DRIFTED Lambda. The 2026-04-30 re-audit reported 6 DRIFTED Lambdas after expanding fingerprint coverage — but the underlying delta wasn't 5 new Lambdas drifting; it was 5 Lambdas whose drift was always there but was never measured.
- The 2026-04-28 audit didn't report the 14 DOUBLE / 2 GHOST entries because it only read the primary state file and ignored `x.legacy`.
- A `policy.exceptions` regex that fails to compile would silently classify every TRACKED resource as `review` — the audit would still complete and report a count.

This is structurally distinct from BS-1/2/3/4/5: those are about *what the audit chose not to measure*. BS-6 is about *what the audit claimed to measure but didn't*. The plug is the **Phase H self-test** (introduced 2026-05-01): for every number the audit prints, the audit asserts the inputs that should have produced that number — every state file in `x.primary` + `x.legacy` was successfully fetched; every TRACKED resource of a fingerprintable type returned a live config; both Phase B passes ran without API errors; the freshness window held. If any assertion fails, the audit refuses to render a ✅ verdict and exits non-zero.

**Plug**: Phase H coverage assertions. Run them on every audit, including dry-runs. Treat any assertion failure as a hard stop, not a warning — a partial audit reported as complete is worse than no audit at all, because it manufactures false confidence.

### Summary table

| # | Blind spot | Audit signal that misleads | What ✅ does NOT prove | Plug |
|---|---|---|---|---|
| 1 | Layer-coverage | `δ_config = 0` | Runtime works, data is right, user flow succeeds | CloudWatch errors + Level-1 smoke + Level-0 e2e |
| 2 | Post-action amnesia | `δ = 0` immediately after `state rm` / `refresh` / `trim-spec` | Spec is intentional; original intent persisted | Journal **before** the destructive verb |
| 3 | Field-coverage | Phase C2 passes | All drifted fields detected | Extend `projection.fingerprint_fields` after every incident |
| 4 | Scope-coverage | Audit completes "successfully" | All AWS resources surveyed | Periodic unscoped sweep against `y.filter` complement |
| 5 | Source-state coverage | `δ_membership = 0`, `δ_config = 0` | `.tf` source matches `.tfstate` (intent matches realized intent) | Phase A.5 (HCL-parse + diff against TFM) — promoted from "out-of-scope; run terraform plan" 2026-05-01 |
| 6 | Audit-execution skew | Any of the audit's coverage numbers | Audit actually measured what it claimed to measure | Phase H coverage assertions; refuse ✅ if any assertion fails |

### Reading order for a passing audit

```
✅ /tf-aws audit  →  δ_membership = 0  AND  δ_config = 0
       │
       │  this proves AGREEMENT on SCOPED, ENUMERATED fields RIGHT NOW.
       │  it does not prove the four things in the table above.
       │
       └──►  before claiming "system healthy", also confirm:
              - CloudWatch errors flat              (Layer-coverage / BS-1)
              - journal exists for any              (Post-action amnesia / BS-2)
                state-rm / trim-spec / refresh
              - fingerprint_fields covers           (Field-coverage / BS-3)
                any field whose drift would matter
              - last unscoped sweep was             (Scope-coverage / BS-4)
                recent enough to trust
              - terraform plan shows                (Source-state coverage / BS-5)
                "No changes." (.tf == .tfstate)
```

This composes with Principle #25 (Behavioral Invariant Verification): `/tf-aws audit` covers Level 4 thoroughly and Level 3 partially. Levels 2, 1, and 0 are out-of-band and require their own evidence.

### Why this section exists

This section is load-bearing for AI agents reading `tf-aws.md` to calibrate their trust in audit outputs. Without it, the doc presents itself as a complete spec (Phases A–H, two-axis convergence) and an agent will overtrust ✅ as "system healthy" when ✅ only proves "TF and AWS agree on the slice we surveyed." The four blind spots above are the structural gaps between those two meanings; the four plugs are how a complete invariant check is composed *outside* this command.

---

## Safety checklist

- [ ] **No AWS mutations**: command writes only to TF state and local `.tf` files
- [ ] **Dry-run by default**: mutating verbs require explicit `--apply`
- [ ] **Confirmation gate**: even with `--apply`, plan is shown and user must `y/N`
- [ ] **State backup before mutate**: `.terraform-state-backups/<timestamp>/`
- [ ] **Layer 4 verification**: post-apply re-runs discovery, reports residual δ
- [ ] **Loud failures**: TF state read failure, AWS API errors, ambiguous triage all fail loudly (Principle #1)
- [ ] **Review-bound .tf stubs**: generated stubs go to `terraform/imported_orphans.tf` for human review before next `terraform apply`
- [ ] **Hard-coded review patterns**: `policy.exceptions` resources are *never* auto-imported (e.g., the deleted Aurora SG rules from validation 2026-04-27)

---

## Required IAM permissions

The invoking IAM principal needs (per validation 2026-04-27):

```
cloudfront:GetOriginAccessControl
cloudfront:GetResponseHeadersPolicy
cloudfront:GetDistribution
```

These are missing from the default `anak` IAM user. Self-grant per CLAUDE.md "AWS Permissions Philosophy" before first run, or `audit` will be incomplete for CloudFront resources.

---

## Examples

### First-time audit

```bash
/tf-aws
```

→ Prints summary across both axes (membership + config); no mutations; recommends next verb based on findings.

### Config-drift detection (Phase 2)

```bash
/tf-aws diff
```

→ Shows DRIFTED resources where TF declaration disagrees with AWS reality on declared fingerprint fields. Example real-world finding (2026-04-28):

```
DRIFTED — 1
  🟠 aws_lambda_function.telegram_api  (Lambda dr-daily-report-telegram-api-dev)
       verdict: review
       fields:
         environment:  TF declares  {OPENROUTER_API_KEY: "***", PDF_STORAGE_BUCKET: "..."}
                       AWS has      (those keys missing)
                       diff: 2 keys missing in AWS
       direction-of-change: ambiguous — Doppler push may have failed, or env was
                            edited via console; check CloudTrail UpdateFunctionConfiguration
```

This is the kind of drift Phase 1 (membership) cannot see — both sides agree the Lambda exists; they disagree on its config.

### Detailed diff before deciding

```bash
/tf-aws diff
```

→ Shows every δ item with triage verdict. Read carefully.

### Import orphans (most common workflow)

```bash
/tf-aws absorb              # dry-run; see what would be imported
/tf-aws absorb --apply      # confirm, then import
```

### Clean up after console deletions

```bash
/tf-aws prune --apply       # state rm for resources deleted from AWS
```

### Full reconciliation

```bash
/tf-aws sync --apply        # absorb + prune in one shot
```

### Edge case: include "review" items

```bash
/tf-aws absorb --apply --include-review
```

→ Imports even resources flagged for human review. Use sparingly — these typically need a human decision (e.g., the orphan API GW shadowing a tracked twin).

---

## Trade-offs (per /design)

| Decision | Why |
|---|---|
| One command, sub-verbs (not 4 separate commands) | Unified mental model; sub-verb explicit enough |
| Replica concept stays inside this command | Rule of Three: promote to kernel only when 2+ commands need it |
| AWS read-only (incl. for DRIFTED items) | Minimum blast radius; mutations go through `terraform apply` (deliberate, change-managed) |
| Dry-run default | Safe by default; opt-in for danger |
| Re-run diff after apply | Layer 4 evidence; don't claim "done" without verification |
| Backup state before mutate | Cheap insurance against bad imports |
| `audit` does both Phase 1 (membership) and Phase 2 (config) | A converged replica is one where TF and AWS agree on **what exists** AND **how it's configured** — not just one |
| `fingerprint_fields` declared in YAML, not hard-coded | Adding a new resource type to the audit is a YAML edit, not a code change |
| Per-type fingerprint (not whole-resource diff) | `terraform plan` already does whole-resource diff; this command focuses on the few fields that *signal real drift* per type — keeps signal-to-noise high |
| No auto-apply for DRIFTED | Drift resolution is a directional decision (which side wins per field) — must be explicit |

---

## Where Replica lives (and where it doesn't)

`Replica` is an **internal data structure** for `/tf-aws` only:

- **Lives in**: `.claude/replicas/dr-bot.yaml` (config), this command's algorithm (logic)
- **Does NOT live in**: CLAUDE.md principles, other command files, kernel-level type vocabulary

Promotion to kernel-level abstraction (with `/replica`, `/diff`, `/converge`) is **deferred** until 2+ other commands clearly need the same pattern. See `.claude/specifications/workflow/2026-04-28-procedural-to-algebraic-kernel-migration.md` for the deferred plan and trigger conditions.

---

## See Also

- **Replica config**: `.claude/replicas/dr-bot.yaml`
- **Replica directory README**: `.claude/replicas/README.md`
- **Discovery algorithm origins**: `.claude/specifications/workflow/2026-04-28-procedural-to-algebraic-kernel-migration.md` (deferred)
- **Drift validation**: `.claude/validations/2026-04-27-terraform-state-vs-deployed-infra.md`
- **Related principles**:
  - #1 Defensive Programming (loud failures)
  - #2 Progressive Evidence Strengthening (Layer 4 post-apply verification)
  - #25 Behavioral Invariant Verification (δ → 0 framing)
- **Related commands**:
  - `/reconcile` — kernel-level "fix" for spec↔reality (different concern)
  - `/validate` — drift detection (read-only, ad-hoc)
  - `/deploy` — one-way push of code to runtime
