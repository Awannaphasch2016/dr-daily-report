---
name: feature
description: Create or update feature specification in .claude/specs/ following structured contract format (spec.yaml, invariants.md, constraints.md, acceptance.md)
accepts_args: true
arg_schema:
  - name: feature_name
    required: true
    description: "Feature name (lowercase, kebab-case, e.g., 'stock-backtester')"
  - name: focus
    required: false
    description: "Optional focus: spec, invariants, constraints, acceptance, or all (default)"
composition:
  - skill: research
---

# Feature Command

**Purpose**: Create or update a **contractual** feature specification that integrates with the Thinking Tuple kernel

**Core Principle**: Features have contracts. A `/feature` spec defines what MUST hold (invariants), what we've learned (constraints), and how to verify "done" (acceptance criteria).

**When to use**:
- Starting a new feature -> Create spec before coding
- Committing to build something explored with `/specify`
- Need `/invariant` and `/reconcile` to verify against a contract
- Long-running feature work -> Need checkpoint/recovery

**When NOT to use**:
- Exploring ideas -> Use `/specify` (exploratory, disposable)
- Quick one-off changes -> No spec needed
- Spike/proof-of-concept -> Use `/specify spike`

---

## Tuple Effects (Universal Kernel Integration)

**Mode Type**: `define`

When `/feature` executes, it creates artifacts that directly populate tuple components:

| Tuple Component | Effect |
|-----------------|--------|
| **Constraints** | **POPULATE**: Loads from `constraints.md` + `spec.yaml` dependencies |
| **Invariant** | **POPULATE**: Loads from `invariants.md` (5 levels) |
| **Principles** | **ADD**: Feature-specific principles in constraints |
| **Strategy** | Enables `/invariant` -> `/reconcile` loop |
| **Check** | **POPULATE**: Loads from `acceptance.md` |

**Tuple Loading Example**:
```yaml
# When working on "stock-backtester" feature:
tuple:
  constraints:
    dependencies:
      - shared/aurora      # From spec.yaml
      - shared/langfuse
    learned:
      - "yfinance API unreliable > 5s"  # From constraints.md
  invariant:
    level_4: ["BACKTEST_TIMEOUT configured"]
    level_3: ["Lambda -> Aurora connectivity"]
    level_2: ["Historical prices available"]
    level_1: ["POST /backtest returns valid JSON"]
    level_0: ["User can run backtest and see results"]
  check:
    acceptance:
      - "All invariant levels verified"
      - "Performance SLA met: < 30s per backtest"
```

---

## Local Check (Mode Completion Criteria)

The `/feature` mode is complete when ALL of the following hold:

| Criterion | Verification |
|-----------|--------------|
| **Directory Created** | `.claude/specs/{feature}/` exists |
| **spec.yaml Valid** | Contains objective, dependencies, resources |
| **invariants.md Complete** | All 5 levels defined with verification commands |
| **constraints.md Exists** | At least empty template ready for learning |
| **acceptance.md Defined** | Clear "done" criteria specified |
| **Registered** | Added to specs README if new feature |

**Check Result Mapping**:
- **PASS**: All files created/updated, ready for `/invariant` verification
- **PARTIAL**: Some sections incomplete -> prompt for missing info
- **FAIL**: Invalid structure -> show template and retry

---

## Quick Reference

```bash
# Create new feature spec
/feature "stock-backtester"
# Creates: .claude/specs/stock-backtester/
#   spec.yaml, invariants.md, constraints.md, acceptance.md

# Update specific section
/feature "telegram" invariants
/feature "linebot" constraints

# View existing feature
/feature "telegram" spec
```

---

## Output Structure

```
.claude/specs/{feature}/
  spec.yaml          # Metadata, dependencies, resources, flows
  invariants.md      # 5-level behavioral contracts (Level 4->0)
  constraints.md     # Learned restrictions (grows over time)
  acceptance.md      # "Done" criteria for verification
```

---

## Templates

### spec.yaml Template

```yaml
# {Feature Name} Specification
# {Brief description}

objective: {feature-name}
description: "{What this feature does}"
owner: "{Primary code location}"
created: {YYYY-MM-DD}

# Deployment targets
environments:
  - dev   # Development
  - stg   # Staging
  - prd   # Production

# Dependencies on other specifications
dependencies:
  - shared/aurora      # Data layer
  - shared/langfuse    # Observability
  - shared/deployment  # CI/CD pipeline

# AWS Resources
resources:
  lambda:
    name_pattern: "dr-{feature}-{env}"
    runtime: python3.11
    timeout: 30
    memory: 512

# User flows
flows:
  - name: "{Primary Flow}"
    trigger: "{What initiates}"
    output: "{What user sees}"
    latency_sla: "< Xs"

# Specification components
components:
  invariants: invariants.md
  constraints: constraints.md
  acceptance: acceptance.md
```

---

### invariants.md Template

```markdown
# {Feature Name} Invariants

**Objective**: {Brief description}
**Last Updated**: {YYYY-MM-DD}

---

## Level 4: Configuration Invariants
- [ ] `{SECRET_NAME}` set in Doppler
- [ ] Lambda timeout >= {X}s, memory >= {Y}MB

## Level 3: Infrastructure Invariants
- [ ] Lambda -> Aurora connectivity
- [ ] Lambda -> External APIs via NAT Gateway

## Level 2: Data Invariants
- [ ] {Data source} updated within {time window}
- [ ] Required data exists for {scope}

## Level 1: Service Invariants
- [ ] `{endpoint}` returns {expected response}
- [ ] Errors logged to CloudWatch

## Level 0: User Invariants
- [ ] User can {primary action}
- [ ] {Action} completes within {SLA}
```

---

### constraints.md Template

```markdown
# {Feature Name} Constraints

**Objective**: {Brief description}
**Last Updated**: {YYYY-MM-DD}

---

## Technical Constraints
- {Constraint 1}: {What we learned}

## Business Constraints
- {Constraint}: {Business rule}

## Lessons Learned
- **{Date}**: {What happened, what we learned}

## Anti-Patterns to Avoid
- {Anti-pattern}: {Why it's problematic}
```

---

### acceptance.md Template

```markdown
# {Feature Name} Acceptance Criteria

**Objective**: {Brief description}
**Last Updated**: {YYYY-MM-DD}

---

## Definition of Done

### Functional Requirements
- [ ] {Requirement 1}
- [ ] {Requirement 2}

### Performance Requirements
- [ ] {Performance metric}: {Target}

### Quality Requirements
- [ ] Tests written and passing
- [ ] Code reviewed and approved

### Operational Requirements
- [ ] Deployed to {target environment}
- [ ] Monitoring configured
```

---

## Relationship to Other Commands

| Command | Purpose | Output Location |
|---------|---------|-----------------|
| `/specify` | Exploratory design sketch | `.claude/specifications/` (disposable) |
| `/feature` | Contractual feature spec | `.claude/specs/{feature}/` (persistent) |
| `/invariant` | Verify against feature spec | Uses `.claude/specs/{feature}/invariants.md` |
| `/reconcile` | Fix violations | Uses feature spec as target state |

**Workflow**:
```bash
# Explore (optional)
/specify "backtester API" api
# Ready to commit?

# Commit to feature
/feature "stock-backtester"

# Develop with verification
/invariant "stock-backtester" dev
/reconcile "stock-backtester"
# delta = 0? Done!
```

---

## Examples

### Example 1: Create New Feature

```bash
/feature "stock-backtester"
```

**Output**:
```
Creating feature specification: stock-backtester

Generated:
  .claude/specs/stock-backtester/
    spec.yaml
    invariants.md
    constraints.md
    acceptance.md

Next steps:
1. Review spec.yaml - verify dependencies and resources
2. Fill in invariants.md - define what must hold
3. Fill in acceptance.md - define "done"
4. Start development
5. Use /invariant "stock-backtester" to verify
```

---

### Example 2: Update Existing Feature

```bash
/feature "telegram" invariants
```

**Output**:
```
Loading existing feature: telegram

Current invariants.md summary:
- Level 4: 8 config invariants
- Level 3: 5 infra invariants
- Level 2: 6 data invariants
- Level 1: 8 service invariants
- Level 0: 6 user invariants

What would you like to update?
```

---

## Best Practices

### Do
- Create spec before coding (spec-first development)
- Keep invariants verifiable (include verification commands)
- Update constraints as you learn (living document)
- Run `/invariant` frequently (catch drift early)

### Don't
- Don't skip invariant levels (all 5 levels matter)
- Don't make invariants aspirational (must be testable)
- Don't forget environment overrides (local != prod)

---

## See Also

- `.claude/specs/README.md` - Spec-driven development overview
- `.claude/commands/specify.md` - Exploratory design sketches
- `.claude/commands/invariant.md` - Verify against spec
- `.claude/commands/reconcile.md` - Fix violations
