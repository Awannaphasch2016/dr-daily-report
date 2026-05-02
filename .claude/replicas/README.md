# Replicas (internal scope)

This directory holds **declarations of paired representations** — two artifacts that should describe the same entity but evolve under independent update cycles. The canonical example is Terraform state ↔ deployed AWS reality.

## Important: this is INTERNAL to specific commands

The `Replica` concept is **not** a kernel-level abstraction at this time. It is internal scaffolding used by individual commands that need paired-state reconciliation. Today, only `/tf-aws` consumes the declarations in this directory.

The kernel does not know about replicas. Don't `Read` files here from other contexts expecting a stable interface — the schema may evolve as more commands need it.

## Why internal-only (Rule of Three)

The decision to keep `Replica` internal rather than promoting it to a Tier-0 kernel type is documented in:

- `.claude/specifications/workflow/2026-04-28-procedural-to-algebraic-kernel-migration.md` — the deferred plan for kernel-level promotion
- The trigger conditions for promotion: when 2+ other commands clearly need the same pattern (e.g., a future `/spec-vs-code`, `/migration-vs-schema`, or `/cache-vs-source`), extract `Replica` into a shared module and update CLAUDE.md.

Until that threshold is reached, leaving the abstraction local prevents premature generalization.

## Schema (subject to change)

Each `<name>.yaml` file declares one replica pair:

```yaml
name: <unique_name>
description: <human readable purpose>

x:
  type: <substrate type>     # tfstate, file, doppler-config, ...
  primary: <pointer>
  legacy: [<pointer>, ...]   # optional secondary sources
  region: <if applicable>

y:
  type: <substrate type>     # aws_account, db, source-of-truth, ...
  account / connection / scope identifiers
  filter: <how to scope which Y resources are in this replica>

projection:
  kind: <how to compare X and Y>
  fingerprint_fields: <per-resource-type fields to compare>

policy:
  default: <reconciliation strategy>  # absorb-reality, conform-to-spec, merge, ...
  exceptions:
    - resource_pattern: <glob>
      override: <strategy>
      reason: <why>

triage:
  empty_shell_patterns: <when to recommend deletion vs import>
  always_import_classes: <observer-class resources always managed>
  recent_activity_window: <activity threshold>

backup:
  enabled: <bool>
  directory: <path>
  retention_days: <int>
```

## Current declarations

| File | Consumer | Purpose |
|---|---|---|
| `dr-bot.yaml` | `/tf-aws` | TF state ↔ AWS reality for the dr daily report bot |

## Adding a new replica

If you have a new pair to reconcile, ask:

1. **Does `/tf-aws` already cover it?** If yes, just extend `dr-bot.yaml` (or branch a new replica file consumed by the same command).
2. **Is this a new domain (not TF↔AWS)?** Build the new command first; declare its replica YAML inside `.claude/replicas/`.
3. **Are 2+ commands now using replicas?** Time to revisit `.claude/specifications/workflow/2026-04-28-procedural-to-algebraic-kernel-migration.md` and consider promoting `Replica` to a kernel-level type with `/replica`, `/diff`, `/converge` commands.

## Why this directory exists at the kernel level (`.claude/`) rather than per-command

Even though `Replica` is currently internal-only, the declarations live at `.claude/replicas/` rather than buried inside `/tf-aws`-specific paths because:

- Configs are user-facing (humans edit them)
- Future kernel-level promotion is anticipated; placing them here now avoids a later move
- Discovery: anyone exploring the project can see "what paired-state systems are tracked"

This is a small concession to future generalization. The promise is: until the Rule of Three triggers, **other commands MUST NOT consume these files**.
