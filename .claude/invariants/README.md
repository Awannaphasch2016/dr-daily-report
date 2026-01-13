# Behavioral Invariants

This directory contains invariant checklists for implementations and deployments.

## Purpose

Invariant checklists make implicit assumptions explicit. Before claiming "implementation complete", verify the invariant envelope holds.

**Core Principle**: "Done" means all relevant invariants verified, not just code written.

---

## Directory Structure

```
.claude/invariants/
├── README.md                    # This file
├── TEMPLATE.md                  # Checklist template for custom invariants
│
├── system-invariants.md         # Project-wide invariants (ALWAYS verify)
│
│   # Domain-Specific Invariants
├── deployment-invariants.md     # Deploy, release, ship, promote
├── data-invariants.md           # Database, Aurora, migrations, timezone
├── api-invariants.md            # Endpoints, routes, handlers, contracts
├── langfuse-invariants.md       # LLM observability, tracing, scoring
└── frontend-invariants.md       # React, Telegram Mini App, charts, state
```

---

## Invariant Hierarchy

All invariants are organized by verification level:

| Level | Type | What to Verify | Example |
|-------|------|----------------|---------|
| **4** | Configuration | Settings are correct | Env vars set, constants defined |
| **3** | Infrastructure | Connectivity works | Lambda → Aurora, Lambda → S3 |
| **2** | Data | Data conditions hold | Schema valid, data fresh |
| **1** | Service | Service behavior correct | Lambda returns 200, API contract |
| **0** | User | User experience works | End-to-end flow succeeds |

**Verification order**: Always verify bottom-up (Level 4 → Level 0)

---

## Quick Reference: Domain → Invariant File

| If working on... | Load invariant file |
|------------------|---------------------|
| Deployment, release, CI/CD | [deployment-invariants.md](deployment-invariants.md) |
| Aurora, migrations, schema | [data-invariants.md](data-invariants.md) |
| API endpoints, handlers | [api-invariants.md](api-invariants.md) |
| Langfuse, tracing, scores | [langfuse-invariants.md](langfuse-invariants.md) |
| React, charts, Mini App | [frontend-invariants.md](frontend-invariants.md) |
| Any task | [system-invariants.md](system-invariants.md) (always) |

---

## Usage

### Using the /invariant Command

The `/invariant` command identifies relevant invariants based on your goal:

```bash
# Goal-based invariant identification
/invariant "deploy new Langfuse scoring feature"
/invariant "add new API endpoint for backtest"
/invariant "fix data migration bug"

# Domain-specific focus
/invariant deployment "release v1.2.3"
/invariant data "add new Aurora table"
/invariant langfuse "add compliance score"
```

### For New Implementations

1. Run `/invariant "{your goal}"` to identify relevant invariants
2. Review the generated checklist before implementing
3. Verify each invariant after implementing
4. Reference the completed checklist in your "done" claim

### For Deployments

1. Reference `system-invariants.md` for critical path verification
2. Load domain-specific invariants (e.g., `deployment-invariants.md`)
3. Verify bottom-up (Level 4 → Level 0)
4. Use "Claiming Done" template from invariant file

### For Custom Invariants

1. Copy `TEMPLATE.md` to `{date}-{slug}.md`
2. Fill in the invariant envelope before implementing
3. Verify each invariant after implementing
4. Reference the completed checklist in your "done" claim

---

## Claiming "Done"

Only claim "done" when ALL relevant invariants are verified:

```markdown
✅ Implementation complete: {description}

**Domain(s)**: {deployment | data | api | langfuse | frontend}

**Invariants Verified**:
- [x] Level 4: {what was verified}
- [x] Level 3: {what was verified}
- [x] Level 2: {what was verified}
- [x] Level 1: {what was verified}
- [x] Level 0: {what was verified}

**Confidence**: {HIGH | MEDIUM | LOW}
**Evidence**: {links to verification output}
```

---

## Integration with Other Tools

### The Invariant Feedback Loop

```
/invariant    →    /reconcile    →    /invariant
  (detect)          (converge)        (verify)
     ↓                  ↓                ↓
  Identify         Generate          Confirm
  invariants       fix actions       delta = 0
```

### Workflow: Plan → Invariant → Implement → Reconcile → Verify

```bash
# 1. Enter plan mode for complex task
EnterPlanMode

# 2. Identify invariants before implementing
/invariant "deploy new scoring feature"

# 3. Implement with invariants in mind

# 4. Check for violations
/invariant "deploy new scoring feature"
# → May show violations

# 5. Generate and apply fixes
/reconcile deployment
/reconcile deployment --apply

# 6. Verify invariants (delta = 0)
/invariant "deploy new scoring feature"
# → All invariants satisfied

# 7. Document if significant
/journal pattern "Invariant verification saved deployment"
```

### Workflow: Incident → Invariant → Reconcile → Verify

```bash
# 1. Incident occurs
# "Users report missing scores in Langfuse"

# 2. Identify which invariant was violated
/invariant langfuse "score submission"
# → Reveals: Level 1 invariant "flush() called" was violated

# 3. Generate fixes
/reconcile langfuse
# → Shows exactly what to fix

# 4. Apply fixes
/reconcile langfuse --apply

# 5. Verify all invariants restored
/invariant langfuse "score submission"
# → Delta = 0, all invariants satisfied
```

### Command Relationship

| Command | Direction | Question | Output |
|---------|-----------|----------|--------|
| `/invariant` | Divergent | "What must hold?" | Checklist of invariants |
| `/reconcile` | Convergent | "How to make it hold?" | Specific fix actions |
| `/validate` | Checking | "Does it hold?" | Pass/fail status |

---

## See Also

- **Commands**:
  - [/invariant](../commands/invariant.md) - Identify invariants for a goal (divergent)
  - [/reconcile](../commands/reconcile.md) - Converge violations to compliance (convergent)
- **Principle**: [CLAUDE.md - Principle #25](../CLAUDE.md) - Behavioral Invariant Verification (Tier-0)
- **Guide**: [Behavioral Invariant Guide](../../docs/guides/behavioral-invariant-verification.md) - Detailed implementation guide
- **Skills**: Domain skills that integrate invariant verification
  - [deployment skill](../skills/deployment/)
  - [testing-workflow skill](../skills/testing-workflow/)
  - [langfuse-observability skill](../skills/langfuse-observability/)

---

*Last updated: 2026-01-12*
