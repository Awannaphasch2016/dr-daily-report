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
- **Network/Infrastructure**: Execution time → Error message → Stack trace → Network path analysis
  - Layer 1 (Surface): Lambda timeout (600s execution time)
  - Layer 2 (Content): Error message ("ConnectTimeoutError")
  - Layer 3 (Observability): Stack trace (botocore.exceptions at line 84)
  - Layer 4 (Ground truth): Network analysis (NAT Gateway saturation, no VPC endpoint)
  - **Critical insight**: Execution time shows WHAT system waits for (10min S3 timeout), not WHERE code hangs (ReportLab)

See [error-investigation skill](.claude/skills/error-investigation/) for AWS-specific application.

### 3. Aurora-First Data Architecture
Aurora is the source of truth. Data precomputed nightly via scheduler (46 tickers). Report APIs are read-only and query Aurora directly. If data missing, APIs return error (fail-fast) instead of falling back to external APIs. Ensures consistent performance and prevents unpredictable latency.

### 4. Type System Integration Research
Research type compatibility BEFORE integrating heterogeneous systems (APIs, databases, message queues). Type mismatches cause silent failures. Answer: (1) What types does target accept? (2) What types does source produce? (3) How does target handle invalid types? Convert types → handle special values → validate schema → verify outcome. See [Type System Integration Guide](docs/TYPE_SYSTEM_INTEGRATION.md).

### 5. Database Migrations Immutability
Migration files are immutable once committed—never edit them. Always create new migrations for schema changes. Use reconciliation migrations (idempotent operations: CREATE TABLE IF NOT EXISTS) when database state is unknown. Prevents migration conflicts and unclear execution states. Verify with `DESCRIBE table_name` after applying. See [database-migration skill](.claude/skills/database-migration/).

### 6. Deployment Monitoring Discipline
Use AWS CLI waiters (`aws lambda wait function-updated`), never `sleep X`. Use GitHub Actions `gh run watch --exit-status` for proper exit codes. Apply Progressive Evidence Strengthening (Principle #2): verify status code + payload + logs + actual behavior. Validate infrastructure-deployment contract before deploying.

**Rollback triggers**: Post-deployment smoke test fails, CloudWatch shows only START/END logs (startup crash), error rate exceeds baseline (>5% in first 5 minutes), ground truth verification fails.

**Anti-pattern**: Assuming deployment succeeded because process exit code = 0. Exit code is weakest evidence.

See [deployment skill](.claude/skills/deployment/) for rollback execution workflow, verification checklists, and manual deployment procedures.

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
Use Doppler for centralized secret management with config inheritance. Cross-environment inheritance (dev → local_dev) syncs shared secrets while allowing local overrides. Validate secrets at application startup (fail-fast).

**Config organization**: `dev` (root) → `local_dev` (inherits), `stg` (root), `prd` (root).

**Doppler constraints**: Same-environment inheritance forbidden, environment-prefixed naming required, cross-environment inheritance allowed.

**Anti-patterns**: Duplicating secrets across configs, manual secret sync, same-environment inheritance.

See [Doppler Config Guide](docs/deployment/DOPPLER_CONFIG.md) for setup workflows, inheritance patterns, and troubleshooting.

### 14. Table Name Centralization
All Aurora table names defined in `src/data/aurora/table_names.py` as constants. Centralized constants (not env vars) since names don't vary per environment. Use f-string interpolation for table names, parameterized queries for user data (SQL injection safety).

**Renaming workflow**: Update constant → create migration → run tests → deploy.

See [Code Style Guide](docs/CODE_STYLE.md#database-patterns) for usage patterns and examples.

### 15. Infrastructure-Application Contract

Maintain contract between application code (`src/`), infrastructure (`terraform/`), and principles. Code deployed without matching infrastructure causes silent failures hours after deployment.

**Deployment order**: Update code → Create migration → Update Terraform → Update Doppler → Deploy migration FIRST → Deploy code → Verify ground truth.

**Startup validation**: Validate required env vars at Lambda startup (fail fast). No silent fallbacks.

**Common failures**: Missing env var, schema not migrated before code, copy-paste inheritance.

See [Infrastructure-Application Contract Guide](docs/guides/infrastructure-application-contract.md) for deployment order, schema migration checklist, startup validation patterns, VPC endpoint verification, NAT Gateway saturation patterns, and real failure instances.

### 16. Timezone Discipline

Use Bangkok timezone (Asia/Bangkok, UTC+7) consistently across all system components. Single-timezone standardization eliminates mental conversion overhead and prevents date boundary bugs.

**Infrastructure**: Aurora (`time_zone = "Asia/Bangkok"`), Lambda (`TZ = "Asia/Bangkok"`), EventBridge (UTC cron → Bangkok equivalent).

**Code pattern**: Always use explicit `datetime.now(ZoneInfo("Asia/Bangkok"))` for business dates.

**Anti-patterns**: Using `datetime.utcnow()`, using `datetime.now()` without explicit timezone, missing TZ env var.

See [Timezone Discipline Guide](docs/guides/timezone-discipline.md) for infrastructure configuration, code patterns, date boundary handling, and real incident analysis.

### 17. Shared Virtual Environment Pattern

Four-repository ecosystem shares single Python virtual environment via symlink (`venv -> ../dr-daily-report/venv`). Eliminates version conflicts between related projects, saves 75% disk space (500MB shared vs 2GB isolated), simplifies management (update once affects all).

**Setup**: `source venv/bin/activate` (works via symlink). Verify: `which python` shows parent venv path.

**Fallback** (if parent missing): `rm venv && python -m venv venv && pip install -r requirements.txt`

**Benefits**: Consistency (identical versions), disk efficiency, development speed (updates immediate), simplicity (one venv).

See [Shared Virtual Environment Guide](docs/guides/shared-virtual-environment.md) for setup workflow, verification checklist, common scenarios (installing packages, broken symlinks), CI/CD integration, and relationship to Doppler config inheritance (Principle #13).

### 18. Logging Discipline (Storytelling Pattern)

Log for narrative reconstruction, not just event recording. Each log level tells a story: ERROR (what failed), WARNING (what's unexpected), INFO (what happened), DEBUG (how it happened). Logs serve as Layer 3 evidence (Principle #2)—faster than traces, more reliable than status codes.

**Narrative structure**: Beginning (context) → Middle (milestones) → End (✅ success / ❌ failure).

**Visual scanability**: Status symbols (✅⚠️❌), chapter separators, correlation IDs for distributed threads.

**Boundary logging**: WHERE you log determines WHAT survives Lambda failures. Log at handler boundaries, not deep in call stack.

**Critical insight**: Execution time shows WHAT system waits for, not WHERE code hangs. Use stack traces (Layer 3) to find actual hang point.

See [Logging Discipline Guide](docs/guides/logging-discipline.md) for narrative structure, boundary logging strategy, verification logging patterns, and anti-patterns.

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

### 22. LLM Observability Discipline

Use Langfuse for LLM tracing, scoring, and prompt management. Every user-facing LLM operation must be traced. Quality scores enable trend analysis and regression detection. Langfuse provides Layer 3 evidence (Principle #2) for LLM operations.

**Tracing**: Entry points decorated with `@observe()`, Lambda handlers call `flush()` before returning (critical for serverless).

**Scoring**: Score high-value outputs (reports, responses), not infrastructure. 5 quality scores per report.

**Graceful degradation**: All Langfuse operations non-blocking. Core functionality works without Langfuse.

**Versioning**: Format `{env}-{version|branch}-{short_sha}`, set automatically by CI/CD via `LANGFUSE_RELEASE`.

See [Langfuse Integration Guide](docs/guides/langfuse-integration.md) and [langfuse-observability skill](.claude/skills/langfuse-observability/) for tracing patterns, scoring criteria, and versioning standard.

### 23. Configuration Variation Axis

Choose configuration mechanism based on WHAT varies and WHEN it varies. Eliminates ad-hoc decisions about env vars vs constants vs config files.

**Decision tree**: Secret? → Doppler | Environment-specific? → Doppler | Per-deployment? → CI/CD | Complex structure? → JSON | Static? → Python constant.

**Doppler as isolation container**: Each environment (local/dev/stg/prd) is an isolated container with complete configuration set. Doppler → Terraform via `TF_VAR_` prefix.

**One-path execution**: Read env vars ONCE at startup (singleton pattern), not per-request.

**Anti-patterns**: Hardcoding secrets, duplicating config across environments, reading env vars per request.

See [Configuration Variation Guide](docs/guides/configuration-variation.md) for decision heuristic, flow patterns, migration checklist, and comprehensive examples.

### 24. External Service Credential Isolation

External services with **webhook-based integrations** require **per-environment credentials**. Copying credentials across environments creates silent routing failures where operations succeed technically but fail functionally.

**Why webhooks require isolation**: LINE, Telegram, Slack webhooks are per-channel/per-bot. Using dev credentials in staging means staging Lambda replies via dev channel—user receives nothing, but Lambda returns 200.

**Isolation checklist for new environments**:
1. Create new channel/bot/app in external service
2. Generate new credentials for that channel
3. Configure webhook URL to point to new environment
4. Store credentials in Doppler under environment-specific config
5. Verify end-to-end: user action → webhook → Lambda → reply → **user receives**

**Services requiring isolation**: LINE, Telegram, Slack, Discord, Stripe webhooks, GitHub Apps, OAuth providers.

**Verification**: HTTP 200 is Layer 1 evidence (weakest). External services require **Layer 4 ground truth**—user actually receives the message. See Principle #2.

**Anti-patterns**:
- ❌ Copying dev credentials to staging "to test quickly"
- ❌ Sharing webhook channels across environments
- ❌ Assuming HTTP 200 from SDK = message delivered

See [External Service Credential Isolation Guide](docs/guides/external-service-credential-isolation.md) for isolation checklist, verification patterns, and real incident analysis. Integrates with Principle #2 (Progressive Evidence), #13 (Secret Management), #15 (Infrastructure Contract).

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
