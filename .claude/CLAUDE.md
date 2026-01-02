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

When adding new principles requiring environment variables, update in this order:
1. Add principle to CLAUDE.md
2. Update application code to follow principle
3. **Update Terraform env vars for ALL affected Lambdas**
4. Update Doppler secrets (if sensitive)
5. Run pre-deployment validation (`scripts/validate_deployment_ready.sh`)
6. Deploy and verify env vars present

Missing step 3 causes silent failures or data inconsistencies hours after deployment.

**Multi-file synchronization pattern**:
- Application code: `src/` directory
- Infrastructure: `terraform/` directory
- Principles: `.claude/CLAUDE.md`
- Must maintain contract between all three layers

**Anti-patterns**:
- ❌ Copy-paste Lambda config without checking new requirements
- ❌ Silent fallbacks: `os.environ.get('TZ', 'UTC')` hides missing config
- ❌ No startup validation (fail on first use, not at startup)
- ❌ Infrastructure updated after deployment (reactive, not proactive)

**Startup validation pattern** (all Lambda handlers):
```python
def _validate_configuration() -> None:
    """Validate required environment variables at Lambda startup.

    Fails fast if critical configuration is missing.
    """
    required = ['AURORA_HOST', 'TZ', 'CACHE_TABLE_NAME', ...]
    missing = [var for var in required if not os.environ.get(var)]

    if missing:
        raise RuntimeError(
            f"Missing required env vars: {missing}\n"
            f"Lambda cannot start without these variables."
        )

def handler(event, context):
    _validate_configuration()  # Call FIRST
    # ... rest of handler logic
```

See [Missing Deployment Flags Pattern](.claude/abstractions/failure_mode-2026-01-02-missing-deployment-flags.md) for detailed failure mode analysis.

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

**Context**: This project is part of a four-repository ecosystem (`dr-daily-report`, `dr-daily-report_telegram`, `dr-daily-report_media`, `dr-daily-report_news`) sharing common dependencies.

**Pattern**: Use symlinked virtual environment to parent project for dependency consistency.

**Setup**:
```bash
# Symlink exists (created during initial setup)
ls -la venv  # Should show: venv -> ../dr-daily-report/venv

# Activate (works via symlink)
source venv/bin/activate

# Verify
which python  # Should show path in parent venv
```

**Why shared venv**:
- **Consistency**: All projects use identical package versions (impossible to have conflicts)
- **Disk efficiency**: 75% savings (500MB shared vs 2GB isolated)
- **Simplicity**: One venv to manage, not four
- **Development speed**: Updates immediately available across all projects

**When parent venv missing** (fallback):
```bash
# If parent project not cloned or venv broken
rm venv  # Remove broken symlink
python -m venv venv  # Create isolated venv
source venv/bin/activate
pip install -r requirements.txt
pip install -e .  # Install DR CLI
```

**Verification checklist**:
- [ ] Symlink exists: `ls -la venv` shows `-> ../parent/venv`
- [ ] Target exists: `ls -la ../dr-daily-report/venv/` shows venv structure
- [ ] Activation works: `source venv/bin/activate` succeeds
- [ ] Python path correct: `which python` points to parent venv
- [ ] DR CLI available: `dr --help` works

**Anti-patterns**:
- ❌ Creating isolated venv without understanding symlink pattern
- ❌ Installing to system Python (not activating venv)
- ❌ Assuming venv exists without verification
- ❌ Installing dependencies without activating venv first

**Related**:
- See [Principle #13: Secret Management Discipline](#13-secret-management-discipline) for Doppler config inheritance (similar "share instead of duplicate" philosophy)
- See [Shared Virtual Environment Pattern](.claude/abstractions/architecture-2026-01-02-shared-venv-pattern.md) for complete technical details

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
