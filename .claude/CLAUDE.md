# Daily Report - Development Guide

**CLAUDE.md is the ground truth contract for how we work.**

---

## About This Document

Maintain the **"Goldilocks Zone" of abstraction** - principles that guide behavior and explain WHY, not implementation details that change frequently. A principle belongs here if it guides behavior, explains rationale, and would cause bugs/confusion if not followed.

---

## Project Context

**Multi-App Architecture:** LINE Bot (chat-based) + Telegram Mini App (web dashboard) share identical core backend. Resources separated via AWS tags (`App = line-bot | telegram-api | shared`).

**Branch Strategy:** `dev` → dev environment (~8 min) | `main` → staging environment (~10 min) | Tags `v*.*.*` → production (~12 min)

**AWS Permissions Philosophy:** Full IAM permissions available. When encountering permission errors, create necessary IAM policy and attach—don't ask for permission. See [AWS Setup](docs/AWS_SETUP.md).

For complete component inventory, technology stack, and directory structure, see [Documentation Index](docs/README.md) and [Project Conventions](docs/PROJECT_CONVENTIONS.md).

---

## Core Principles

### 1. Defensive Programming
Fail fast and visibly when something is wrong. Silent failures hide bugs. Validate configuration at startup, not on first use. Explicitly detect operation failures (rowcount, status codes). No silent fallbacks or default values that hide error recovery. **Never assume data exists** without validating first. See [code-review skill](.claude/skills/code-review/).

### 2. Progressive Evidence Strengthening
Execution completion ≠ Operational success. Trust but verify through increasingly strong evidence sources. **Surface signals** (status codes, exit codes) are weakest—they confirm execution finished but not correctness. **Content signals** (payloads, data structures) are stronger—they validate schema and presence. **Observability signals** (execution traces, logs) are stronger still—they reveal what actually happened. **Ground truth** (actual state changes, side effects) is strongest—it confirms intent matched reality. Never stop verification at weak evidence—progress until ground truth is verified.

**Domain applications**:
- **HTTP APIs**: Status code → Response payload → Application logs → Database state
- **File operations**: Exit code → File content → System logs → Disk state
- **Database ops**: Rowcount → Query result → DB logs → Table inspection
- **Deployments**: Process exit → Service health → CloudWatch logs → Traffic metrics
- **Testing**: Test passed → Output correct → No errors logged → Side effects verified

See [error-investigation skill](.claude/skills/error-investigation/) for AWS-specific application.

### 3. Aurora-First Data Architecture
Aurora is the source of truth. Data precomputed nightly via scheduler (46 tickers). Report APIs are read-only and query Aurora directly. If data missing, APIs return error (fail-fast) instead of falling back to external APIs. Ensures consistent performance and prevents unpredictable latency.

### 4. Type System Integration Research
Research type compatibility BEFORE integrating heterogeneous systems (APIs, databases, message queues). Type mismatches cause silent failures. Answer: (1) What types does target accept? (2) What types does source produce? (3) How does target handle invalid types? Convert types → handle special values → validate schema → verify outcome. See [Type System Integration Guide](docs/TYPE_SYSTEM_INTEGRATION.md).

### 5. Database Migrations Immutability
Migration files are immutable once committed—never edit them. Always create new migrations for schema changes. Use reconciliation migrations (idempotent operations: CREATE TABLE IF NOT EXISTS) when database state is unknown. Prevents migration conflicts and unclear execution states. Verify with `DESCRIBE table_name` after applying. See [database-migration skill](.claude/skills/database-migration/).

### 6. Deployment Monitoring Discipline
Use AWS CLI waiters (`aws lambda wait function-updated`), never `sleep X`. Use GitHub Actions `gh run watch --exit-status` for proper exit codes. Apply Progressive Evidence Strengthening (Principle #2): verify status code + payload + logs + actual behavior. Validate infrastructure-deployment contract before deploying (GitHub secrets match AWS reality). See [deployment skill](.claude/skills/deployment/).

### 7. Loud Mock Pattern
Mock/stub data in production code must be centralized, explicit, and loud. Register ALL mocks in centralized registry (`src/mocks/__init__.py`), log loudly at startup (WARNING level), gate behind environment variables (fail in production if unexpected mocks active), document why each mock exists (owner, date, reason). Valid: speeding local dev. Invalid: hiding implementation gaps, bypassing security.

### 8. Error Handling Duality
Workflow nodes use state-based error propagation (collect all errors, enable resumable workflows). Utility functions raise descriptive exceptions (fail fast). Never mix patterns. Functions returning `None` on failure create cascading silent failures—prefer explicit exceptions. See [Code Style Guide](docs/CODE_STYLE.md#error-handling-patterns).

### 9. Feedback Loop Awareness
When failures persist, use `/reflect` to identify which loop type you're using: retrying (fix execution), initial-sensitive (change assumptions), branching (try different path), synchronize (align knowledge), or meta-loop (change loop type itself). Thinking tools reveal progress patterns without explicit metrics—use `/trace` for root cause, `/hypothesis` for new assumptions, `/compare` for path evaluation. See [Thinking Process Architecture - Feedback Loops](.claude/diagrams/thinking-process-architecture.md#11-feedback-loop-types-self-healing-properties) and [Metacognitive Commands](.claude/diagrams/thinking-process-architecture.md#metacognitive-commands-thinking-about-thinking).

### 10. Testing Anti-Patterns Awareness
Test outcomes, not execution. Verify results, not just that functions were called. MagicMock defaults are truthy—explicitly mock failure states. Round-trip tests for persistence. Schema testing at boundaries. Database operations fail without exceptions—check rowcount. After writing test, break code to verify test catches it. See [testing-workflow skill](.claude/skills/testing-workflow/).

### 11. Artifact Promotion Principle
Build once, promote same immutable Docker image through all environments (dev → staging → prod). What you test in staging is exactly what deploys to production. Use immutable image digests, not tags. Verify all environments use identical digest. See [deployment skill](.claude/skills/deployment/MULTI_ENV.md) and [docs/deployment/MULTI_ENV.md](docs/deployment/MULTI_ENV.md).

### 12. OWL-Based Relationship Analysis
Use formal ontology relationships (OWL, RDF) for structured concept comparison. Eliminates "it depends" answers by applying 4 fundamental relationship types: part-whole, complement, substitution, composition. Transforms vague "X vs Y" questions into precise analytical frameworks with concrete examples. See [Relationship Analysis Guide](docs/RELATIONSHIP_ANALYSIS.md).

### 13. Secret Management Discipline
Use Doppler for centralized secret management with config inheritance to prevent duplication. Cross-environment inheritance (dev → local_dev in `local` environment) automatically syncs shared secrets while allowing local overrides. Validate secrets at application startup, not on first use (fail-fast principle).

**Doppler Constraints** (platform limitations):
1. **Same-environment inheritance forbidden**: Configs in same environment cannot inherit from each other
2. **Environment-prefixed naming required**: Configs must use environment prefix (e.g., `local_*` for `local` environment)
3. **Cross-environment inheritance allowed**: `local_dev` (in `local` env) can inherit from `dev` (in `dev` env)

**Config Organization**:
- `dev` (root, AWS): Shared development secrets
- `local_dev` (branch, inherits from dev): Local overrides only (localhost, mock flags)
- `stg` (root, AWS): Staging secrets
- `prd` (root, AWS): Production secrets

**Benefits**:
- No secret duplication (9 local overrides + 9 inherited = 18 total)
- Automatic propagation when dev secrets updated
- Clear separation between environments

**Anti-patterns**:
- ❌ Duplicating secrets across configs (breaks single source of truth)
- ❌ Same-environment inheritance (violates Doppler constraint)
- ❌ Manual secret sync (error-prone, causes drift)

See [Doppler Config Guide](docs/deployment/DOPPLER_CONFIG.md) for setup workflows and troubleshooting.

---

## Extension Points

1. **Adding Scoring Metrics**: Create scorer class in `src/scoring/` → integrate into `src/workflow/workflow_nodes.py` → extend `AgentState` TypedDict in `src/types.py`. See [Project Conventions](docs/PROJECT_CONVENTIONS.md#extension-points).

2. **Adding CLI Commands**: Create command in `dr_cli/commands/<group>.py` with Click decorators → add Justfile recipe for intent layer. Two-layer design: Justfile (WHEN/WHY), dr CLI (HOW).

3. **Extending State**: Update `AgentState` TypedDict in `src/types.py` → add workflow node that populates field. All state fields must be JSON-serializable for Lambda responses.

4. **Adding API Endpoints**: Create service singleton → define Pydantic models → add FastAPI route → write integration tests. Follow async/sync dual method pattern for LangGraph compatibility.

---

## References

- **Project Conventions**: [docs/PROJECT_CONVENTIONS.md](docs/PROJECT_CONVENTIONS.md) - Directory structure, naming patterns, CLI commands, extension points
- **Skills**: [.claude/skills/README.md](.claude/skills/README.md) - Executable workflows and checklists
- **Documentation**: [docs/README.md](docs/README.md) - Complete documentation index
- **Architecture Decisions**: [docs/adr/README.md](docs/adr/README.md) - ADRs for major technology choices
- **Deployment**: [docs/deployment/](docs/deployment/) - Complete deployment guides and runbooks
- **Code Style**: [docs/CODE_STYLE.md](docs/CODE_STYLE.md) - Detailed coding patterns and conventions
