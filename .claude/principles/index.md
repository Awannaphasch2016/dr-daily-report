# Principle Routing Index

**Purpose**: Quick lookup to find which principle cluster to load based on current task.

---

## Routing Table

| If you're doing... | Load this cluster | Principles |
|--------------------|-------------------|------------|
| **Deploying** to any environment | [deployment-principles.md](deployment-principles.md) | #6, #11, #15, #19, #21 |
| **Writing tests** or fixing test failures | [testing-principles.md](testing-principles.md) | #10, #19 |
| **Aurora queries**, migrations, ETL | [data-principles.md](data-principles.md) | #3, #5, #14, #16 |
| **Secrets**, env vars, external services | [configuration-principles.md](configuration-principles.md) | #13, #24 |
| **API integration**, error handling | [integration-principles.md](integration-principles.md) | #4, #7, #8 |
| **Debugging loops**, concept analysis | [meta-principles.md](meta-principles.md) | #9, #12, #17 |
| **LLM operations**, tracing | [integration-principles.md](integration-principles.md) | #22 |

---

## Keyword Triggers

### Deployment Cluster
**Keywords**: deploy, CI/CD, release, rollback, Lambda update, staging, production, artifact, promotion

**Load**: `deployment-principles.md`

### Testing Cluster
**Keywords**: test, pytest, mock, fixture, assertion, coverage, tier, anti-pattern

**Load**: `testing-principles.md`

### Data Cluster
**Keywords**: Aurora, MySQL, query, migration, schema, table, timezone, date, precompute

**Load**: `data-principles.md`

### Configuration Cluster
**Keywords**: secret, Doppler, env var, credential, webhook, LINE, Telegram, external service

**Load**: `configuration-principles.md`

### Integration Cluster
**Keywords**: API, type, JSON, serialize, error, exception, LLM, Langfuse, trace

**Load**: `integration-principles.md`

### Meta Cluster
**Keywords**: debug, stuck, loop, retry, feedback, analysis, OWL, relationship, venv, local

**Load**: `meta-principles.md`

---

## Multi-Cluster Scenarios

Some tasks require multiple clusters:

| Task | Clusters Needed |
|------|-----------------|
| Deploy with new secrets | deployment + configuration |
| Migration + deployment | data + deployment |
| Test external API integration | testing + integration |
| Debug deployment failure | deployment + meta |

---

## Core Principles (Always Loaded)

These are in CLAUDE.md and always apply:

| # | Principle | One-liner |
|---|-----------|-----------|
| 1 | Defensive Programming | Fail fast, no silent failures |
| 2 | Progressive Evidence | Verify weak → strong evidence |
| 18 | Logging Discipline | Log for narrative reconstruction |
| 20 | Execution Boundary | Reading code ≠ verifying it works |
| 23 | Configuration Variation | Choose config mechanism by what varies |
| 25 | Behavioral Invariant | State invariants before claiming done |

---

## Quick Reference

```bash
# Deploying?
Read: .claude/principles/deployment-principles.md

# Testing?
Read: .claude/principles/testing-principles.md

# Data/Aurora?
Read: .claude/principles/data-principles.md

# Secrets/Config?
Read: .claude/principles/configuration-principles.md

# API/Errors?
Read: .claude/principles/integration-principles.md

# Stuck/Debugging?
Read: .claude/principles/meta-principles.md
```

---

*Last updated: 2026-01-12*
