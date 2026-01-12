# Principle Clusters

**Purpose**: Context-specific principles organized by task/domain for efficient loading.

**Design Philosophy**: Principles have different applicability levels. Core principles (Tier-0) apply to EVERY task and live in CLAUDE.md. Domain and task-specific principles live here, loaded only when relevant.

---

## Architecture

```
CLAUDE.md (~80 lines)
├── Project Context (always loaded)
├── Tier-0: Core Principles (ALWAYS apply)
│   └── 6 principles that guide ALL work
└── Routing Index → points here

.claude/principles/
├── index.md (routing table with triggers)
├── deployment-principles.md (deployment lifecycle)
├── data-principles.md (Aurora, migrations, timezone)
├── configuration-principles.md (secrets, env vars)
├── testing-principles.md (test patterns)
├── integration-principles.md (APIs, error handling)
└── meta-principles.md (debugging, analysis)
```

---

## Tier Classification

### Tier-0: Core (ALWAYS Apply)
These principles guide every task. They live in CLAUDE.md.

| # | Principle | Why Always |
|---|-----------|-----------|
| 1 | Defensive Programming | Every code change |
| 2 | Progressive Evidence | Every verification |
| 18 | Logging Discipline | Any logging |
| 20 | Execution Boundary | Before claiming "works" |
| 23 | Configuration Variation | Any config decision |
| 25 | Behavioral Invariant | Before claiming "done" |

### Tier-1: Domain (Load by Context)
These principles apply to specific domains.

| Cluster | Principles | Load When |
|---------|-----------|-----------|
| Data | #3, #5, #14, #16 | Aurora queries, migrations |
| LLM | #22 | LLM operations |

### Tier-2: Task (Load by Task)
These principles apply to specific tasks.

| Cluster | Principles | Load When |
|---------|-----------|-----------|
| Deployment | #6, #11, #15, #19, #21 | Deploying |
| Testing | #10, #19 | Writing tests |
| Configuration | #13, #24 | Secrets, external services |
| Integration | #4, #7, #8 | API integration |

### Tier-3: Meta/Environment
These principles apply to specific situations.

| Cluster | Principles | Load When |
|---------|-----------|-----------|
| Meta | #9, #12 | Debugging loops, analysis |
| Environment | #17 | Local dev setup |

---

## Token Efficiency

| Scenario | Before | After | Savings |
|----------|--------|-------|---------|
| Any task | 301 lines | 80 (core) | 73% |
| + 1 cluster | 301 lines | 130 lines | 57% |
| + 2 clusters | 301 lines | 180 lines | 40% |

---

## How to Use

### For Claude (Agent)
1. CLAUDE.md is always loaded (Tier-0 principles)
2. Check routing index for task-specific clusters
3. Load relevant cluster(s) based on current task
4. Apply all loaded principles

### For Humans
1. Read CLAUDE.md for core principles
2. Browse clusters for domain-specific guidance
3. Each cluster is self-contained with full principle text

---

## Cluster Files

- **[index.md](index.md)** - Routing table with triggers
- **[deployment-principles.md](deployment-principles.md)** - Deployment lifecycle
- **[data-principles.md](data-principles.md)** - Aurora, migrations, timezone
- **[configuration-principles.md](configuration-principles.md)** - Secrets, credentials
- **[testing-principles.md](testing-principles.md)** - Test patterns
- **[integration-principles.md](integration-principles.md)** - APIs, errors
- **[meta-principles.md](meta-principles.md)** - Debugging, analysis

---

## Maintenance

When adding a new principle:
1. Determine tier (0=always, 1=domain, 2=task, 3=meta)
2. If Tier-0: Add to CLAUDE.md
3. If Tier-1/2/3: Add to appropriate cluster
4. Update index.md routing table

When updating a principle:
1. Update in its home location (CLAUDE.md or cluster file)
2. Keep cross-references consistent

---

*Created: 2026-01-12*
*Architecture: Tier-based classification with connascent clustering*
