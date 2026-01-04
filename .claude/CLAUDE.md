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

**Rollback triggers** (when to revert deployment):
- Post-deployment smoke test fails (Lambda returns 500, import errors)
- CloudWatch shows only START/END logs (no application logs = startup crash)
- Error rate exceeds baseline (>5% errors in first 5 minutes)
- Ground truth verification fails (database state doesn't match expectations)

**Rollback execution**:
- Use previous known-good artifact (commit SHA or image digest)
- Apply same deployment process (waiters, verification, smoke tests)
- Document rollback reason and create incident report
- Don't delete failed deployment (preserve for investigation)

**Anti-pattern**: Assuming deployment succeeded because process exit code = 0. Exit code is weakest evidence - verify through smoke tests and ground truth.

### 7. Loud Mock Pattern
Mock/stub data in production code must be centralized, explicit, and loud. Register ALL mocks in centralized registry (`src/mocks/__init__.py`), log loudly at startup (WARNING level), gate behind environment variables (fail in production if unexpected mocks active), document why each mock exists (owner, date, reason). Valid: speeding local dev. Invalid: hiding implementation gaps, bypassing security.

### 8. Error Handling Duality
Workflow nodes use state-based error propagation (collect all errors, enable resumable workflows). Utility functions raise descriptive exceptions (fail fast). Never mix patterns. Functions returning `None` on failure create cascading silent failures—prefer explicit exceptions. See [Code Style Guide](docs/CODE_STYLE.md#error-handling-patterns).

### 9. Feedback Loop Awareness
When failures persist, use `/reflect` to identify which loop type you're using: retrying (fix execution), initial-sensitive (change assumptions), branching (try different path), synchronize (align knowledge), or meta-loop (change loop type itself). Thinking tools reveal progress patterns without explicit metrics—use `/trace` for root cause, `/hypothesis` for new assumptions, `/compare` for path evaluation. See [Thinking Process Architecture - Feedback Loops](.claude/diagrams/thinking-process-architecture.md#11-feedback-loop-types-self-healing-properties) and [Metacognitive Commands](.claude/diagrams/thinking-process-architecture.md#metacognitive-commands-thinking-about-thinking).

### 10. Testing Anti-Patterns Awareness

Test outcomes, not execution. Verify results, not just that functions were called. MagicMock defaults are truthy—explicitly mock failure states. Round-trip tests for persistence. Database operations fail without exceptions—check rowcount. After writing test, break code to verify test catches it.

**Deployment fidelity testing**: Test deployment artifacts (Docker images with Lambda base image), not just source code. Validates imports work in `/var/task`, catches environment mismatches before deployment.

**Common anti-patterns**: Testing imports locally only (local ≠ Lambda), mocking all environment (hides missing config), only testing deployed systems (doesn't catch fresh deployment gaps), assuming local tests pass = Lambda works.

See [testing-workflow skill](.claude/skills/testing-workflow/) for test patterns, anti-patterns, and comprehensive checklists. Extends Principle #19 (Cross-Boundary Contract Testing) with deployment-specific patterns. Real incidents: LINE bot 7-day outage (ImportError in Lambda, not local), query_tool_handler deployment blocker.

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

### 14. Table Name Centralization
All Aurora table names are defined in `src/data/aurora/table_names.py` as constants. This provides a single modification point if table schema evolves.

**Pattern**:
```python
from src.data.aurora.table_names import DAILY_PRICES

query = f"SELECT * FROM {DAILY_PRICES} WHERE symbol = %s"
```

**Rationale**:
- Table names are stable but treating them as configuration enables future flexibility
- Centralized constants (not environment variables) since names don't vary per environment
- f-string interpolation for table names, parameterized queries for user data (SQL injection safety)

**If renaming a table**:
1. Update constant in `table_names.py`
2. Create migration SQL file
3. Run tests to verify
4. Deploy (constants propagate automatically via imports)

**Removed tables**:
- `ticker_info` - Dropped in migration 018 (empty table, replaced by ticker_master)

### 15. Infrastructure-Application Contract

Maintain contract between application code (`src/`), infrastructure (`terraform/`), and principles (`.claude/CLAUDE.md`). Code deployed without matching infrastructure causes silent failures hours after deployment.

**Deployment order**: (1) Update code, (2) **Create schema migration**, (3) **Update Terraform env vars**, (4) Update Doppler secrets, (5) **Deploy migration FIRST**, (6) Then deploy code, (7) Verify ground truth.

**Startup validation**: Validate required env vars at Lambda startup (fail fast). No silent fallbacks (`os.environ.get('TZ', 'UTC')` hides missing config).

**Common failures**: Missing env var, schema not migrated before code, timezone date boundary bug (no TZ env var), copy-paste inheritance (old config missing new requirements).

See [Infrastructure-Application Contract Guide](docs/guides/infrastructure-application-contract.md) for deployment order, schema migration checklist, startup validation patterns, pre-deployment validation script, and 4 real failure instances. Integrates with Principle #1 (Defensive Programming), #2 (Progressive Evidence Strengthening), #5 (Database Migrations), #20 (Execution Boundary Discipline).

### 16. Timezone Discipline

Use Bangkok timezone (Asia/Bangkok, UTC+7) consistently across all system components. For Bangkok-based users with no UTC requirements, single-timezone standardization eliminates mental conversion overhead and prevents date boundary bugs.

**Infrastructure configuration**:
- Aurora MySQL: `time_zone = "Asia/Bangkok"` (RDS parameter group)
- Lambda functions: `TZ = "Asia/Bangkok"` (environment variable)
- EventBridge Scheduler: UTC cron (platform limitation) but executes at Bangkok time equivalent

**Code pattern** (explicit timezone):
```python
from zoneinfo import ZoneInfo

# Explicit Bangkok timezone for business dates
bangkok_tz = ZoneInfo("Asia/Bangkok")
today = datetime.now(bangkok_tz).date()
```

**Anti-patterns**:
- ❌ Using `datetime.utcnow()` (implicit UTC, wrong for Bangkok business dates)
- ❌ Using `datetime.now()` without explicit timezone (ambiguous, depends on env var)
- ❌ Missing TZ env var in Lambda (defaults to UTC, causes date boundary bugs)

**Rationale**:
- Bangkok users + Bangkok scheduler = Bangkok dates everywhere
- Prevents cache misses (21:00 UTC Dec 30 ≠ 04:00 Bangkok Dec 31)
- Single timezone = no mental conversion overhead

See [Timezone Implementation](.claude/validations/2025-12-30-etl-bangkok-timezone-verification.md) for validation.

### 17. Shared Virtual Environment Pattern

Four-repository ecosystem shares single Python virtual environment via symlink (`venv -> ../dr-daily-report/venv`). Eliminates version conflicts between related projects, saves 75% disk space (500MB shared vs 2GB isolated), simplifies management (update once affects all).

**Setup**: `source venv/bin/activate` (works via symlink). Verify: `which python` shows parent venv path.

**Fallback** (if parent missing): `rm venv && python -m venv venv && pip install -r requirements.txt`

**Benefits**: Consistency (identical versions), disk efficiency, development speed (updates immediate), simplicity (one venv).

See [Shared Virtual Environment Guide](docs/guides/shared-virtual-environment.md) for setup workflow, verification checklist, common scenarios (installing packages, broken symlinks), CI/CD integration, and relationship to Doppler config inheritance (Principle #13).

### 18. Logging Discipline (Storytelling Pattern)

Log for narrative reconstruction, not just event recording. Each log level tells a story: ERROR (what failed), WARNING (what's unexpected), INFO (what happened), DEBUG (how it happened). Reading logs should explain what was executed or failed without needing to inspect traces directly. Logs serve as "weaker ground truth"—faster to inspect than traces, more reliable than status codes.

**Narrative structure**:
- **Beginning**: What we're doing (context, inputs)
- **Middle**: Key steps (transformations, milestones with breadcrumbs)
- **End**: Outcome (✅ success / ❌ failure with details)

**Visual scanability**:
- **Symbols**: ✅ (success), ⚠️ (degraded), ❌ (failure)
- **Chapters**: `====` separators, 📄 phase emojis
- **Correlation**: `[job_id]` prefix for distributed threads

**Verification logging** (defensive storytelling):
```python
result = client.execute(query)
if result.rowcount == 0:
    logger.error("❌ Operation failed - 0 rows affected")  # Explicit
else:
    logger.info(f"✅ Affected {result.rowcount} rows")     # Verified
```

**Anti-patterns**:
- ❌ Logging errors at WARNING level (invisible to monitoring)
- ❌ Missing narrative phases (can't reconstruct execution from logs)
- ❌ Silent success (only logging failures hides what happened)

See [Logging as Storytelling](.claude/abstractions/architecture-2026-01-03-logging-as-storytelling.md) for comprehensive templates and examples. Integrates with Principle #2 (Progressive Evidence Strengthening - logs as Layer 3) and Principle #1 (Defensive Programming - verification logging).

### 19. Cross-Boundary Contract Testing

Test transitions between execution phases, service components, data domains, and temporal states—not just behavior within a single boundary. Integration tests against deployed systems miss contract violations at **boundary crossings** where assumptions, configurations, or type systems change (missing env vars at deployment → first invocation, event structure at API Gateway → Lambda, type conversion at Python → MySQL).

**Boundary types**: Phase (Build → Runtime), Service (Lambda → Aurora), Data (Python → JSON), Time (23:59 → 00:00 date change).

**When to apply**: Before deployment (phase boundaries), when integrating services (service boundaries), when handling user input (data boundaries), when dealing with time-sensitive operations (time boundaries).

See [Cross-Boundary Contract Testing Guide](docs/guides/cross-boundary-contract-testing.md) for boundary taxonomy, test pattern templates, comprehensive examples, identification heuristics, and real-world incident analysis. Integrates with Principle #1 (Defensive Programming), #2 (Progressive Evidence Strengthening), #4 (Type System Integration), #15 (Infrastructure-Application Contract), #16 (Timezone Discipline).

### 20. Execution Boundary Discipline

**Reading code ≠ Verifying code works.** In distributed systems, code correctness depends on WHERE it executes and WHAT initial conditions hold. Before concluding "code is correct", systematically identify execution boundaries (code → runtime, code → database, service → service) and verify contracts at each boundary match reality.

**Five verification questions**: WHERE does code run? WHAT environment required? WHAT systems called? WHAT entity properties? HOW verify contract?

**Five layers of correctness**: Syntactic (code compiles) → Semantic (logic correct) → Boundary (can reach dependencies) → Configuration (entity config matches) → Intentional (usage matches design).

**Common failures**: Missing env var, schema mismatch, permission denied, network blocked, timeout insufficient, sync Lambda for async work.

See [Execution Boundary Discipline Guide](docs/guides/execution-boundary-discipline.md) for verification questions, concrete methods (Docker testing, Terraform verification, Aurora schema validation), boundary checklist, anti-patterns, and real-world impact analysis. Integrates with Principle #1 (validate at startup), #2 (evidence strengthening), #4 (type boundaries), #15 (infra-app contract), #19 (boundary testing).

### 21. Deployment Blocker Resolution

When deployment blocked by validation failures or pipeline issues, apply systematic heuristic to choose resolution path. Not all blockers require fixing—some can be safely bypassed when evidence supports safety.

**Choose LEAST RESISTANCE (bypass)** when: (1) Change validated independently, (2) Blocker unrelated to change, (3) Change backward compatible, (4) Manual bypass auditable (artifact promotion), (5) Alternative paths high cost.

**Choose FIX BLOCKER FIRST** when: Security-related, change depends on fix, systemic issue, manual bypass risky, or root cause quick to fix.

**Manual deployment discipline**: Artifact promotion (not rebuild), traceable to commit SHA, document why/what/follow-up, use same validation as CI/CD (waiters, smoke tests), create issue to fix blocker separately.

See [Deployment Blocker Resolution Guide](docs/guides/deployment-blocker-resolution.md) for decision heuristic, step-by-step template, manual Lambda deployment workflow, circular dependency patterns, and real-world examples. Integrates with Principle #2 (Progressive Evidence Strengthening), #11 (Artifact Promotion), #19 (Cross-Boundary Contract Testing).

---

## Extension Points

1. **Adding Scoring Metrics**: Create scorer class in `src/scoring/` → integrate into `src/workflow/workflow_nodes.py` → extend `AgentState` TypedDict in `src/types.py`. See [Project Conventions](docs/PROJECT_CONVENTIONS.md#extension-points).

2. **Adding CLI Commands**: Create command in `dr_cli/commands/<group>.py` with Click decorators → add Justfile recipe for intent layer. Two-layer design: Justfile (WHEN/WHY), dr CLI (HOW).

3. **Extending State**: Update `AgentState` TypedDict in `src/types.py` → add workflow node that populates field. All state fields must be JSON-serializable for Lambda responses.

4. **Adding API Endpoints**: Create service singleton → define Pydantic models → add FastAPI route → write integration tests. Follow async/sync dual method pattern for LangGraph compatibility.

---

## References

- **Project Conventions**: [docs/PROJECT_CONVENTIONS.md](docs/PROJECT_CONVENTIONS.md) - Directory structure, naming patterns, CLI commands, extension points
- **Implementation Guides**: [docs/guides/README.md](docs/guides/README.md) - Comprehensive how-to guides for implementing principles (boundary testing, execution boundaries, deployment blockers, infrastructure contracts, shared venv)
- **Skills**: [.claude/skills/README.md](.claude/skills/README.md) - Executable workflows and checklists
- **Documentation**: [docs/README.md](docs/README.md) - Complete documentation index
- **Architecture Decisions**: [docs/adr/README.md](docs/adr/README.md) - ADRs for major technology choices
- **Deployment**: [docs/deployment/](docs/deployment/) - Complete deployment guides and runbooks
- **Code Style**: [docs/CODE_STYLE.md](docs/CODE_STYLE.md) - Detailed coding patterns and conventions
