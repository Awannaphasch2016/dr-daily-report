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
Test outcomes, not execution. Verify results, not just that functions were called. MagicMock defaults are truthy—explicitly mock failure states. Round-trip tests for persistence. Schema testing at boundaries. Database operations fail without exceptions—check rowcount. After writing test, break code to verify test catches it. See [testing-workflow skill](.claude/skills/testing-workflow/).

**Deployment fidelity testing** (Docker container validation):
- Test deployment artifacts (Docker images), not just source code
- Use runtime-matching environments (Docker with Lambda base image)
- Validate filesystem layout (imports work in `/var/task`)
- Test failure modes (missing env vars, schema mismatches, import errors)
- Run before merge (PR workflow), not after deployment

**Primary example** (Docker import validation):
```python
def test_handler_imports_in_docker():
    """Phase boundary: Development → Lambda Runtime

    Tests Lambda handler imports in actual container environment.
    Simulates: Fresh deployment to Lambda.
    """
    import_script = "import src.scheduler.query_tool_handler"

    # Run import test inside Lambda container
    result = subprocess.run(
        ["docker", "run", "--rm", "--entrypoint", "python3",
         "dr-lambda-test", "-c", import_script],
        capture_output=True
    )

    assert result.returncode == 0, (
        f"Import failed in Lambda container: {result.stderr}\n"
        f"This would cause production failure if deployed."
    )
```

**When to use Docker tests**:
- Before every PR merge (automated in workflow)
- After Dockerfile changes
- After adding new Lambda handlers
- When import errors appear in deployment

**Evidence**: Dec 2025 LINE bot 7-day outage (ImportError in production), Jan 2026 query_tool_handler import error (deployment blocker). Both caught by local tests but failed in Lambda container.

**Anti-patterns**:
- ❌ Testing imports locally only (import ≠ works in Lambda)
- ❌ Mocking all environment (hides missing configuration)
- ❌ Only testing deployed systems (doesn't catch fresh deployment gaps)
- ❌ Assuming local tests pass = Lambda works (environment ≠ runtime)

**Integration**: Extends Principle #19 (Cross-Boundary Contract Testing - phase boundaries) with deployment-specific testing patterns. See [lambda-deployment checklist](.claude/checklists/lambda-deployment.md) for complete verification workflow.

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

When adding new features requiring infrastructure changes, update in this order:
1. Add principle to CLAUDE.md (if applicable)
2. Update application code to follow principle
3. **Update database schema for ALL affected tables (create migration)**
4. **Update Terraform env vars for ALL affected Lambdas**
5. Update Doppler secrets (if sensitive)
6. Run pre-deployment validation (`scripts/validate_deployment_ready.sh`)
7. Deploy schema migration FIRST, then code changes
8. Verify infrastructure matches code expectations

**Schema Migration Checklist**:
- [ ] Created migration file (`db/migrations/0XX_*.sql`)
- [ ] Tested migration locally (rollback tested)
- [ ] Ran schema validation tests (`test_aurora_schema_comprehensive.py`)
- [ ] Deployed migration to dev environment
- [ ] Verified migration applied (`DESCRIBE table_name`)
- [ ] THEN deploy code changes (handler updates)
- [ ] Verify ground truth (actual Aurora state matches code expectations)

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

Test transitions between execution phases, service components, data domains, and temporal states—not just behavior within a single boundary. Tests that verify logic in isolation (unit tests) or deployed systems (integration tests) miss contract violations that appear at **boundary crossings** where assumptions, configurations, or type systems change.

**Boundary types**:
- **Phase**: Build → Runtime, Development → Production, Container Startup → Running
- **Service**: API Gateway → Lambda, Lambda → Aurora, Lambda → SQS
- **Data**: Python types → JSON, NumPy → MySQL, User input → Database
- **Time**: Date boundaries (23:59 → 00:00), Timezone transitions (UTC → Bangkok), Cache TTL expiration

**Test pattern** (tests the transition itself):
```python
def test_<source>_to_<target>_boundary():
    """<Boundary type>: <Source> → <Target>

    Tests that <contract> is upheld when crossing boundary.
    Simulates: <Real scenario exposing this boundary>
    """
    # 1. Set up boundary conditions (remove mocks, use real constraints)
    # 2. Invoke the transition (call handler, serialize data, etc.)
    # 3. Verify contract upheld (or exception raised if broken)
    # 4. Clean up (restore environment)
```

**Primary example - Phase boundary** (Docker Container Import Validation):
```python
def test_handler_imports_in_docker():
    """Phase boundary: Development → Lambda Runtime

    Tests Lambda handler imports in actual Lambda container environment.
    Simulates: Fresh Lambda deployment with new code.
    """
    import_script = "import src.scheduler.query_tool_handler"

    # Run import test inside Lambda Python 3.11 container
    result = subprocess.run(
        ["docker", "run", "--rm", "--entrypoint", "python3",
         "dr-lambda-test", "-c", import_script],
        capture_output=True
    )

    assert result.returncode == 0, (
        f"Import failed in Lambda container: {result.stderr}\n"
        f"Local import passed but Lambda import failed.\n"
        f"This is a phase boundary violation."
    )
```

**Secondary example - Phase boundary** (Lambda Startup Validation):
```python
def test_handler_startup_without_environment():
    """Phase boundary: Deployment → First Invocation

    Tests Lambda fails fast when environment variables missing.
    Simulates: Fresh deployment where Terraform forgot env vars.
    """
    original_tz = os.environ.pop('TZ', None)
    try:
        from src.scheduler.handler import lambda_handler
        with pytest.raises(RuntimeError) as exc:
            lambda_handler({}, MagicMock())
        assert 'TZ' in str(exc.value)
    finally:
        if original_tz: os.environ['TZ'] = original_tz
```

**Other boundary examples**:
- **Service**: Test Lambda with actual API Gateway event structure (not mocked dict)
- **Data**: Test Python `float('nan')` → MySQL JSON (MySQL rejects NaN per RFC 8259)
- **Time**: Test cache key consistency across date boundary (23:59 Bangkok → 00:01)

**Boundary identification heuristic**:
1. Map system components and their interactions (each arrow = service boundary)
2. List lifecycle phases for each component (each transition = phase boundary)
3. Trace data transformations through system (each conversion = data boundary)
4. Identify time-sensitive operations (each state change = time boundary)
5. For each boundary, ask: "What assumptions does each side make? Do tests verify this contract?"

**Anti-patterns**:
- ❌ Testing only within boundaries (mocked environment, isolated logic)
- ❌ Testing deployed systems only (doesn't catch fresh deployment gaps)
- ❌ Assuming mocks match reality (real API Gateway sends body as string, not dict)
- ❌ No negative boundary tests (only testing success paths)

**Rationale**: Integration tests against deployed systems pass because those systems already have correct configuration. Gap appears when crossing boundaries—deploying to NEW environment, integrating with DIFFERENT service, handling UNEXPECTED data, or crossing TIME-based state changes. Boundary tests explicitly verify these transitions.

See [Cross-Boundary Contract Testing](.claude/abstractions/architecture-2026-01-03-cross-boundary-contract-testing.md) for comprehensive boundary taxonomy, testing templates, and real-world examples. Integrates with Principle #1 (Defensive Programming - validation at boundaries), Principle #2 (Progressive Evidence Strengthening - verify transitions), Principle #4 (Type System Integration - data boundaries), Principle #15 (Infrastructure-Application Contract - phase boundaries), and Principle #16 (Timezone Discipline - time boundaries).

### 20. Execution Boundary Discipline

**Reading code ≠ Verifying code works.** In distributed systems, code correctness depends on WHERE it executes and WHAT initial conditions hold. Before concluding "code is correct", systematically identify execution boundaries (code → runtime, code → database, service → service) and verify contracts at each boundary match reality.

**Verification questions**:
- WHERE does this code run? (Lambda, EC2, local?)
- WHAT environment does it require? (env vars, network, permissions?)
- WHAT external systems does it call? (Aurora schema, S3 bucket, API format?)
- WHAT are entity properties? (Lambda timeout/memory, Aurora connection limits, intended usage)
- HOW do I verify the contract? (Terraform config, SHOW COLUMNS, test access?)

**Concrete verification methods**:

**1. Docker container testing** (Development → Lambda Runtime):
```bash
# Build Lambda container
docker build -t dr-lambda-test -f Dockerfile .

# Test imports in container
docker run --rm --entrypoint python3 dr-lambda-test \
  -c "import src.scheduler.query_tool_handler"

# Interactive debugging
docker run -it --entrypoint bash dr-lambda-test
```

**2. Terraform environment verification** (Code → Infrastructure):
```bash
# Extract required vars from code
grep "required_vars\|REQUIRED_VARS" src/handler.py

# Check Terraform has all vars
grep -A 20 "environment" terraform/lambda_config.tf

# Verify deployed Lambda has vars
aws lambda get-function-configuration \
  --function-name LAMBDA_NAME \
  --query 'Environment.Variables'
```

**3. Aurora schema verification** (Code → Database):
```bash
# Run schema validation tests
pytest tests/infrastructure/test_aurora_schema_comprehensive.py -v

# Manual verification
mysql -h $AURORA_HOST -u $AURORA_USER -p$AURORA_PASSWORD \
  -e "DESCRIBE table_name"
```

**Anti-patterns**:
- ❌ Assuming code works because Python syntax is valid
- ❌ Assuming environment variables exist (verify Terraform/Doppler)
- ❌ Assuming database schema matches code (verify with SHOW COLUMNS)
- ❌ Stopping at code inspection (verify through deployment config → actual runtime)
- ❌ Testing locally only (local ≠ Lambda container environment)

**Common boundary failures**: Missing env var (Lambda vs local), schema mismatch (code INSERT vs Aurora columns), permission denied (IAM role vs resource policy), network blocked (VPC vs internet).

**Progressive verification** (Principle #2): Code syntax (Layer 1) → Infrastructure config (Layer 2) → Runtime inspection (Layer 3) → Execution test (Layer 4). Never stop at Layer 1.

**Rationale**: Code can be syntactically correct but fail in production because execution boundaries aren't verified. Missing environment variable causes runtime error. Schema mismatch causes silent data loss. Permission denied blocks service access. Network misconfiguration prevents connectivity. These failures are invisible from code inspection alone—must verify WHERE code runs and WHAT it needs.

**Related**: Principle #1 (validate at startup), #2 (evidence strengthening), #4 (type boundaries), #15 (infra-app contract), #19 (boundary testing). See [execution boundary checklist](.claude/checklists/execution-boundaries.md) for systematic verification workflow.

### 21. Deployment Blocker Resolution

When deployment is blocked by validation failures or pipeline issues, apply systematic decision heuristic to choose resolution path. Not all blockers require fixing - some can be safely bypassed when evidence supports safety.

**Decision heuristic**:

**Choose LEAST RESISTANCE (bypass blocker) when**:
1. **Change is isolated and validated independently**
   - Handler tests passed, Docker image built successfully, Quality Gates green
2. **Blocker is unrelated to current change**
   - Schema validation tests different Lambda, pre-existing failure not caused by your changes
3. **Change is backward compatible**
   - New mode added, existing modes still work (SQS mode unaffected)
4. **Manual bypass is safe and auditable**
   - Use artifact built by CI/CD (promotion, not rebuild)
   - Traceable to commit SHA, same image that passed Quality Gates
5. **Alternative paths have high cost**
   - Fixing blocker: Hours of investigation | Waiting: Blocks critical migration indefinitely

**Choose FIX BLOCKER FIRST when**:
1. Blocker is security-related (can't bypass safely)
2. Change depends on blocker being fixed
3. Blocker indicates systemic issue affecting your change
4. Manual bypass introduces risk > cost of fixing
5. Root cause is simple and quick to fix

**Manual deployment discipline** (when bypassing pipeline):
- Only use artifacts built by validated pipeline (artifact promotion, not rebuild)
- Trace artifact to specific commit SHA or image digest
- Document: Why blocked, why bypass safe, what artifact used, follow-up issue
- Use same validation commands as CI/CD (waiters, smoke tests, verification)
- Create issue to fix blocker separately (don't forget systemic improvement)

**Anti-patterns**:
- ❌ Treating all validation gates as equally important
- ❌ Blocking all work until perfect pipeline
- ❌ Ad-hoc rebuilds bypassing quality gates
- ❌ Manual deployments without traceability
- ❌ Ignoring blocker after bypass (creates technical debt)

**Related**: Principle #2 (Progressive Evidence Strengthening - use highest available evidence when ground truth blocked), Principle #11 (Artifact Promotion - manual deployment is still promotion), Principle #19 (Cross-Boundary Contract Testing - validate independently before bypassing).

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
