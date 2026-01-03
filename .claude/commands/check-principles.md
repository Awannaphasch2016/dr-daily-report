---
name: check-principles
description: Systematic CLAUDE.md compliance audit - verify adherence to core principles before deployment or after incidents
accepts_args: false
composition:
  - skill: research
---

# Check-Principles Command

**Purpose**: Systematic compliance audit for CLAUDE.md principles

**Core Principle**: Proactive principle verification prevents production issues. Check compliance BEFORE deployment, not after failure.

**When to use**:
- Before deploying significant changes (prevent issues)
- After production incidents (identify root cause)
- During code review (verify PR compliance)
- When refactoring (ensure principles maintained)
- Weekly health check (systematic audit)

**Output**: Compliance status, gaps identified, specific recommendations

---

## Quick Reference

```bash
# Before deployment
/check-principles
→ Verify Principles #6, #11, #15 (deployment-related)
→ Identify gaps in infrastructure-application contract
→ Recommendation: Update Terraform before deploying

# After incident
/check-principles
→ Verify Principles #1, #2, #20 (defensive programming, evidence, boundaries)
→ Identify which principles were violated
→ Root cause: Principle #20 violated (didn't verify execution boundaries)

# During code review
/check-principles
→ Verify Principles #1, #4, #10 (defensive, type system, testing)
→ Check if new code follows established patterns
→ Flag: Missing error handling (Principle #1 violation)

# Health check
/check-principles
→ Audit all 20 principles
→ Identify systematic compliance gaps
→ Prioritize improvements
```

---

## Check-Principles vs Other Commands

| Command | Purpose | Focus | Timing |
|---------|---------|-------|--------|
| **`/reflect`** | Metacognitive analysis | Past actions (what happened) | After work |
| **`/check-principles`** | Compliance audit | Current state (what's missing) | Before/After |
| **`/validate`** | Hypothesis testing | Specific claim (is X true?) | During investigation |
| **`/proof`** | Evidence verification | Claim validity (prove X works) | During implementation |

**Key difference**: `/check-principles` is proactive (prevent issues) vs `/reflect` is reactive (learn from issues)

---

## Execution Flow

### Step 1: Determine Audit Scope

**Context-based scope selection**:

```
BEFORE deployment:
→ Focus: Deployment-related principles (#6, #11, #15, #16)
→ Critical: Infrastructure-application contract, artifact promotion
→ Depth: Deep verification (check Terraform, Docker, env vars)

AFTER incident:
→ Focus: Incident-related principles (depends on error type)
→ Error type → Principle mapping (see Error-to-Principle Matrix)
→ Depth: Root cause analysis (which principle violation caused issue?)

DURING code review:
→ Focus: Code quality principles (#1, #4, #8, #10, #19, #20)
→ Critical: Defensive programming, type system, error handling, testing
→ Depth: Code-specific verification (does PR follow patterns?)

HEALTH check (weekly):
→ Focus: All 20 principles
→ Critical: Identify systematic gaps across project
→ Depth: Systematic audit (pattern detection, not single-file)
```

**Scope output**:
```
Audit scope: [DEPLOYMENT | INCIDENT | CODE_REVIEW | HEALTH_CHECK]
Principles selected: [List of principle numbers]
Depth: [QUICK | DEEP | SYSTEMATIC]
```

---

### Step 2: Execute Compliance Checks

**For each selected principle**:

```
Principle #X: [Principle Name]

Compliance Question:
[Specific yes/no question based on current context]

Verification Method:
[How to check - file inspection, AWS CLI command, git log, etc.]

Evidence:
[Actual data collected - file contents, command output, etc.]

Status: [✅ COMPLIANT | ⚠️ PARTIAL | ❌ VIOLATION]

Gap (if not compliant):
[What's missing or wrong]

Impact (if violation):
[How this affects system/deployment]
```

---

### Step 3: Generate Recommendations

**Prioritization**:

```
CRITICAL (blocking):
- Principle violations that will cause deployment failure
- Example: Missing env vars (Principle #15), No startup validation (Principle #1)
- Action: MUST fix before proceeding

HIGH (risky):
- Principle violations that might cause production issues
- Example: No boundary verification (Principle #20), Silent failures (Principle #1)
- Action: SHOULD fix before deployment

MEDIUM (debt):
- Principle violations that reduce code quality
- Example: Magic numbers, no docstrings, missing tests
- Action: Schedule for next sprint

LOW (nice-to-have):
- Minor style/convention issues
- Action: Optional improvement
```

**Recommendation format**:
```
Priority: [CRITICAL | HIGH | MEDIUM | LOW]
Principle: #X
Gap: [Specific violation]
Fix: [Concrete action to take]
Verification: [How to verify fix applied]
```

---

## Top 20 Principles Checklist

### Deployment Principles (6 principles)

#### Principle #6: Deployment Monitoring Discipline

**Compliance question**: Are you using AWS CLI waiters instead of `sleep`?

**Verification**:
```bash
# Check for sleep usage in deployment scripts
rg "sleep \d+" scripts/ .github/workflows/ --type sh

# Should use waiters instead
rg "aws.*wait" scripts/ .github/workflows/ --type sh
```

**Status**: [✅ | ⚠️ | ❌]

**Gap**: [If violations found, list files with `sleep` usage]

**Recommendation**: Replace `sleep X` with `aws <service> wait <condition>`

---

#### Principle #11: Artifact Promotion Principle

**Compliance question**: Are you promoting the same Docker image digest across environments?

**Verification**:
```bash
# Check if Terraform uses image digests (not tags)
rg "image.*:latest" terraform/ --type tf
# Should use: image = "${data.aws_ecr_image.worker.image_uri}@${data.aws_ecr_image.worker.image_digest}"

# Verify all environments use same digest
grep "image_digest" terraform/environments/*/terraform.tfvars
```

**Status**: [✅ | ⚠️ | ❌]

**Gap**: [If using tags instead of digests, list resources]

**Recommendation**: Use `data.aws_ecr_image` to reference immutable digests

---

#### Principle #15: Infrastructure-Application Contract

**Compliance question**: Are Terraform environment variables in sync with application requirements?

**Verification**:
```bash
# Step 1: Extract env vars from application code
rg "os\.environ\[" src/ --type py | cut -d"'" -f2 | sort -u > /tmp/app_envs.txt

# Step 2: Extract env vars from Terraform
rg "environment\s*=\s*\{" terraform/ --type tf -A 50 | \
  grep -E '^\s+[A-Z_]+\s*=' | cut -d'=' -f1 | tr -d ' ' | sort -u > /tmp/tf_envs.txt

# Step 3: Find missing env vars
comm -23 /tmp/app_envs.txt /tmp/tf_envs.txt
```

**Status**: [✅ | ⚠️ | ❌]

**Gap**: [List env vars required by code but missing in Terraform]

**Recommendation**: Add missing env vars to Terraform Lambda configurations

---

#### Principle #16: Timezone Discipline

**Compliance question**: Are all components using Bangkok timezone consistently?

**Verification**:
```bash
# Check Lambda env vars
rg 'TZ.*=.*"Asia/Bangkok"' terraform/ --type tf

# Check Aurora timezone
aws rds describe-db-cluster-parameters \
  --db-cluster-parameter-group-name dr-daily-report-aurora-params \
  --query 'Parameters[?ParameterName==`time_zone`].ParameterValue' \
  --output text

# Check code uses explicit timezone
rg 'ZoneInfo\("Asia/Bangkok"\)' src/ --type py

# Anti-pattern check
rg 'datetime\.utcnow\(\)' src/ --type py
```

**Status**: [✅ | ⚠️ | ❌]

**Gap**: [List components not using Bangkok timezone]

**Recommendation**: Set TZ env var, use ZoneInfo("Asia/Bangkok"), avoid utcnow()

---

#### Principle #13: Secret Management Discipline

**Compliance question**: Are secrets in Doppler and validated at startup?

**Verification**:
```bash
# Check if secrets referenced in code exist in Doppler
ENV=dev doppler secrets get --json | jq -r 'keys[]' > /tmp/doppler_secrets.txt

# Extract secret references from code
rg 'os\.environ\["[A-Z_]+"\]' src/ --type py -o | \
  cut -d'"' -f2 | sort -u > /tmp/code_secrets.txt

# Find missing secrets
comm -23 /tmp/code_secrets.txt /tmp/doppler_secrets.txt

# Check for startup validation
rg "def _validate_configuration" src/ --type py
```

**Status**: [✅ | ⚠️ | ❌]

**Gap**: [List secrets missing from Doppler, Lambdas without startup validation]

**Recommendation**: Add secrets to Doppler, implement _validate_configuration()

---

#### Principle #17: Shared Virtual Environment Pattern

**Compliance question**: Is venv symlinked to parent project?

**Verification**:
```bash
# Check symlink exists
ls -la venv | grep '\->'

# Verify points to parent
readlink venv

# Check activation works
source venv/bin/activate && which python && dr --help
```

**Status**: [✅ | ⚠️ | ❌]

**Gap**: [If venv is isolated instead of symlinked]

**Recommendation**: Remove isolated venv, create symlink: `ln -s ../dr-daily-report/venv venv`

---

### Code Quality Principles (8 principles)

#### Principle #1: Defensive Programming

**Compliance question**: Does code validate prerequisites and fail fast?

**Verification**:
```bash
# Check for validation patterns
rg "if not.*or len\(.*\) == 0:" src/ --type py
rg "if rowcount == 0:" src/ --type py

# Check for anti-pattern: silent failures
rg "except.*:\s*pass" src/ --type py
rg "return True\s*#.*failed" src/ --type py

# Check startup validation
rg "def _validate_configuration" src/*handler.py --type py
```

**Status**: [✅ | ⚠️ | ❌]

**Gap**: [List files with silent failures, missing validation]

**Recommendation**: Add explicit validation, remove silent fallbacks, implement startup checks

---

#### Principle #2: Progressive Evidence Strengthening

**Compliance question**: Are operations verified through ground truth, not just status codes?

**Verification**:
```bash
# Check for weak evidence (status code only)
rg "if response\.status_code == 200:" src/ --type py

# Check for strong evidence (content + rowcount + logs)
rg "if rowcount > 0:" src/ --type py
rg "logger\.info.*✅" src/ --type py
```

**Status**: [✅ | ⚠️ | ❌]

**Gap**: [List operations verified only by status code]

**Recommendation**: Add content validation, rowcount checks, log verification

---

#### Principle #4: Type System Integration Research

**Compliance question**: Are type conversions explicit when crossing system boundaries?

**Verification**:
```bash
# Check for JSON serialization at boundaries
rg "json\.dumps\(" src/ --type py

# Check for anti-pattern: passing dict to PyMySQL JSON column
rg "execute\(.*VALUES.*%s.*\)" src/data/aurora/ --type py -A 2 | \
  rg -v "json\.dumps"

# Check for NaN handling
rg "float\('nan'\)" src/ --type py
```

**Status**: [✅ | ⚠️ | ❌]

**Gap**: [List boundary crossings without explicit type conversion]

**Recommendation**: Use json.dumps() for JSON columns, handle NaN explicitly

---

#### Principle #8: Error Handling Duality

**Compliance question**: Do workflow nodes use state-based errors and utilities raise exceptions?

**Verification**:
```bash
# Check workflow nodes use state['error']
rg "state\['error'\] =" src/workflow/ --type py

# Check utilities raise exceptions
rg "raise [A-Za-z]+Error" src/data/ src/services/ --type py

# Anti-pattern: mixing patterns
rg "raise.*Error" src/workflow/workflow_nodes.py --type py
rg "state\['error'\]" src/data/ src/services/ --type py
```

**Status**: [✅ | ⚠️ | ❌]

**Gap**: [List files mixing error handling patterns]

**Recommendation**: Workflow nodes: state-based, Utilities: exceptions

---

#### Principle #10: Testing Anti-Patterns Awareness

**Compliance question**: Do tests verify outcomes, not just execution?

**Verification**:
```bash
# Check for "The Liar" pattern
rg "assert_called\(\)" tests/ --type py
rg "assert.*is not None" tests/ --type py

# Check for proper outcome verification
rg "assert.*rowcount.*>" tests/ --type py
rg "assert result == expected" tests/ --type py

# Check tests can fail
rg "def test_.*_failure" tests/ --type py
```

**Status**: [✅ | ⚠️ | ❌]

**Gap**: [List tests that only check execution, not outcomes]

**Recommendation**: Verify results, test failure paths, break code to verify test catches it

---

#### Principle #18: Logging Discipline (Storytelling Pattern)

**Compliance question**: Do logs tell a narrative with beginning, middle, and end?

**Verification**:
```bash
# Check for narrative structure
rg "logger\.info.*====.*" src/ --type py  # Chapter separators
rg "logger\.info.*✅" src/ --type py      # Success markers
rg "logger\.error.*❌" src/ --type py     # Failure markers

# Check for verification logging
rg "if rowcount == 0:.*logger\.error" src/ --type py -A 1

# Anti-pattern: errors at WARNING level
rg "logger\.warning.*failed" src/ --type py
```

**Status**: [✅ | ⚠️ | ❌]

**Gap**: [List modules missing narrative structure, logging errors at WARNING]

**Recommendation**: Add chapter separators, use symbols (✅/❌), log errors at ERROR level

---

#### Principle #19: Cross-Boundary Contract Testing

**Compliance question**: Are boundary transitions tested (not just logic within boundaries)?

**Verification**:
```bash
# Check for boundary tests
rg "def test_.*_boundary" tests/ --type py
rg "def test_handler_startup_without" tests/ --type py

# Check for phase boundary tests (deployment → runtime)
rg "os\.environ\.pop" tests/ --type py

# Check for data boundary tests (Python → JSON → MySQL)
rg "json\.dumps.*json\.loads" tests/ --type py
```

**Status**: [✅ | ⚠️ | ❌]

**Gap**: [List missing boundary tests: phase, service, data, time]

**Recommendation**: Add boundary tests for transitions, not just internal logic

---

#### Principle #20: Execution Boundary Discipline

**Compliance question**: Are execution boundaries verified (WHERE code runs, WHAT it needs)?

**Verification**:
```bash
# Check if code verifies WHERE it runs
rg "aws lambda get-function-configuration" scripts/ .github/workflows/ --type sh

# Check environment variable verification
rg "os\.environ\[" src/ --type py | cut -d"'" -f2 | sort -u
# Compare with Terraform (see Principle #15)

# Check schema verification
rg "SHOW COLUMNS" scripts/ docs/ --type md

# Anti-pattern: assuming without verifying
rg "# Assumes.*" src/ --type py
```

**Status**: [✅ | ⚠️ | ❌]

**Gap**: [List unverified boundaries: Lambda config, env vars, Aurora schema, IAM permissions]

**Recommendation**: Use execution-boundaries.md checklist, verify through ground truth

---

### Architecture Principles (6 principles)

#### Principle #3: Aurora-First Data Architecture

**Compliance question**: Is Aurora the source of truth? Are APIs read-only?

**Verification**:
```bash
# Check APIs query Aurora (not external APIs)
rg "yf\.download" src/telegram/api/ src/telegram/services/ --type py
# Should be empty (external APIs only in ETL)

# Check for fallback pattern (anti-pattern)
rg "if.*not found.*fetch" src/telegram/ --type py

# Verify precompute schedule active
aws events list-rules --name-prefix dr-daily-report-precompute
```

**Status**: [✅ | ⚠️ | ❌]

**Gap**: [If APIs call external services instead of Aurora]

**Recommendation**: APIs must query Aurora only, ETL populates Aurora nightly

---

#### Principle #5: Database Migrations Immutability

**Compliance question**: Are migrations immutable once committed?

**Verification**:
```bash
# Check if committed migrations were modified
git log --oneline migrations/ | head -20

# Look for edited migrations (should be none)
git log --all --oneline -- migrations/*.sql | \
  awk '{print $NF}' | sort | uniq -c | awk '$1>1'

# Check for reconciliation pattern
rg "CREATE TABLE IF NOT EXISTS" migrations/ --type sql
```

**Status**: [✅ | ⚠️ | ❌]

**Gap**: [If migrations were edited after commit]

**Recommendation**: Never edit committed migrations, create new migration files

---

#### Principle #14: Table Name Centralization

**Compliance question**: Are all table names defined in table_names.py?

**Verification**:
```bash
# Check table references use constants
rg "from.*table_names import" src/ --type py

# Anti-pattern: hardcoded table names
rg 'SELECT.*FROM "?[a-z_]+"?' src/ --type py | \
  rg -v 'FROM \{' | \
  rg -v 'table_names\.'

# Verify all tables defined
cat src/data/aurora/table_names.py
```

**Status**: [✅ | ⚠️ | ❌]

**Gap**: [List queries with hardcoded table names]

**Recommendation**: Add constants to table_names.py, use f-strings with constants

---

#### Principle #7: Loud Mock Pattern

**Compliance question**: Are mocks centralized, explicit, and loud?

**Verification**:
```bash
# Check mock registry exists
cat src/mocks/__init__.py

# Check mocks log loudly at startup
rg "logger\.warning.*MOCK" src/mocks/ --type py

# Check mocks gated by env vars
rg "if.*MOCK.*enabled" src/mocks/ --type py

# Anti-pattern: scattered mocks
rg "Mock\(\)" src/ --type py | rg -v "tests/"
```

**Status**: [✅ | ⚠️ | ❌]

**Gap**: [List scattered mocks not in registry]

**Recommendation**: Move mocks to src/mocks/, register in __init__.py, log loudly

---

#### Principle #12: OWL-Based Relationship Analysis

**Compliance question**: Are "X vs Y" decisions analyzed with formal relationships?

**Verification**:
```bash
# Check ADRs use relationship analysis
rg "Part-Whole|Complement|Substitution|Composition" docs/adr/ --type md

# Check for vague "it depends" (anti-pattern)
rg "it depends" docs/adr/ docs/*.md --type md
```

**Status**: [✅ | ⚠️ | ❌]

**Gap**: [If ADRs lack relationship analysis]

**Recommendation**: Use docs/RELATIONSHIP_ANALYSIS.md framework for decisions

---

#### Principle #9: Feedback Loop Awareness

**Compliance question**: Are you using metacognitive commands when stuck?

**Verification**:
```bash
# This is a process principle, verified during /reflect
# Check if /reflect was used when stuck (manual review)

# Check if thinking commands documented in evolution/
ls -la .claude/evolution/*reflect*.md
ls -la .claude/evolution/*hypothesis*.md
```

**Status**: [✅ | ⚠️ | ❌] (Process audit, not code audit)

**Gap**: [If stuck patterns persist without using /reflect]

**Recommendation**: Use /reflect after 3+ attempts, /hypothesis for assumptions

---

## Error-to-Principle Matrix

**Map production errors to likely principle violations**:

| Error Pattern | Likely Violation | Principles to Check |
|---------------|------------------|---------------------|
| **Lambda timeout** | Didn't verify timeout config | #20 (Execution Boundaries), #6 (Deployment Monitoring) |
| **Missing env var** | Infra-app contract broken | #15 (Infra-App Contract), #1 (Defensive Programming) |
| **Schema mismatch** | Didn't verify schema | #20 (Execution Boundaries), #5 (Migrations), #4 (Type System) |
| **Permission denied** | Didn't verify IAM | #20 (Execution Boundaries), #15 (Infra-App Contract) |
| **Silent failure** | No validation, weak evidence | #1 (Defensive Programming), #2 (Progressive Evidence) |
| **Date boundary bug** | Timezone inconsistency | #16 (Timezone Discipline), #19 (Cross-Boundary Testing) |
| **Cache miss** | Wrong business date | #16 (Timezone Discipline), #3 (Aurora-First) |
| **Deployment failed** | Config mismatch | #15 (Infra-App Contract), #6 (Deployment Monitoring) |
| **Test passed but prod failed** | Boundary not tested | #19 (Cross-Boundary Testing), #20 (Execution Boundaries) |
| **Type error** | No type conversion | #4 (Type System Integration), #1 (Defensive Programming) |

**Usage**: After incident, use error pattern to select principles to audit

---

## Output Format

```markdown
# Principle Compliance Audit

**Audit Date**: [YYYY-MM-DD HH:MM]
**Scope**: [DEPLOYMENT | INCIDENT | CODE_REVIEW | HEALTH_CHECK]
**Context**: [Brief description of what triggered audit]

---

## Audit Summary

**Principles audited**: [N]
**Status**:
- ✅ Compliant: [N]
- ⚠️ Partial: [N]
- ❌ Violations: [N]

**Overall compliance**: [XX%]

---

## Compliance Results

### Principle #X: [Principle Name]

**Compliance question**: [Specific question]

**Verification method**: [How checked]

**Evidence**:
```
[Actual data - command output, file contents, etc.]
```

**Status**: [✅ COMPLIANT | ⚠️ PARTIAL | ❌ VIOLATION]

**Gap** (if not compliant): [What's missing]

**Impact**: [How this affects system]

---

[Repeat for each principle]

---

## Recommendations

### Critical (Blocking)

**Priority**: CRITICAL
**Principle**: #X
**Gap**: [Specific violation]
**Fix**: [Concrete action]
**Verification**: [How to verify fix]
**Blocker**: [What this blocks - deployment, merge, etc.]

---

### High (Risky)

[Repeat format]

---

### Medium (Debt)

[Repeat format]

---

### Low (Nice-to-have)

[Repeat format]

---

## Action Items

1. **[CRITICAL]** [Action description] (Principle #X)
   - Command: `[command to run]`
   - Verify: `[verification command]`
   - Estimated time: [X minutes]

2. **[HIGH]** [Action description] (Principle #Y)
   - [Details]

---

## Next Audit

**Recommended timing**: [Date/trigger]
**Focus areas**: [Based on gaps found]
```

---

## Examples

### Example 1: Pre-Deployment Audit

```bash
/check-principles

# Context: About to deploy Lambda timeout increase

## Audit Summary
Principles audited: 6 (deployment-related)
Status:
- ✅ Compliant: 4
- ⚠️ Partial: 1
- ❌ Violations: 1

Overall compliance: 67%

## Compliance Results

### Principle #15: Infrastructure-Application Contract

Compliance question: Are Terraform env vars in sync with application?

Verification:
```bash
comm -23 /tmp/app_envs.txt /tmp/tf_envs.txt
```

Evidence:
```
CACHE_TTL
LOG_LEVEL
```

Status: ❌ VIOLATION

Gap: Lambda code expects CACHE_TTL and LOG_LEVEL, but Terraform doesn't provide them

Impact: Lambda will fail at startup with KeyError

---

### Principle #20: Execution Boundary Discipline

Compliance question: Did we verify Lambda timeout matches code requirements?

Verification:
```bash
aws lambda get-function-configuration \
  --function-name dr-daily-report-worker-dev \
  --query 'Timeout'
```

Evidence:
```
30
```

Status: ⚠️ PARTIAL

Gap: Current timeout is 30s, about to change to 120s, but didn't verify code actually needs 120s

Impact: Might be over-provisioning (cost) or under-provisioning (still timeout)

Recommendation: Profile code to determine actual execution time needed

---

## Recommendations

### Critical (Blocking)

Priority: CRITICAL
Principle: #15
Gap: Missing env vars CACHE_TTL and LOG_LEVEL
Fix: Add to Terraform Lambda configuration
Verification: `rg "CACHE_TTL|LOG_LEVEL" terraform/lambda.tf`
Blocker: Deployment will fail

### High (Risky)

Priority: HIGH
Principle: #20
Gap: Didn't profile code to verify 120s timeout needed
Fix: Add CloudWatch timer, analyze execution times over 1 week
Verification: Check CloudWatch metrics for Duration
Blocker: Might waste money if over-provisioned

---

## Action Items

1. **[CRITICAL]** Add missing env vars to Terraform (Principle #15)
   - File: `terraform/lambda.tf`
   - Add: `CACHE_TTL = "3600"` and `LOG_LEVEL = "INFO"`
   - Verify: `terraform plan | grep CACHE_TTL`
   - Time: 5 minutes

2. **[HIGH]** Profile Lambda execution time (Principle #20)
   - Command: Check CloudWatch Duration metric
   - Analyze: P99 duration over 1 week
   - Decide: Set timeout = P99 * 1.5 (safety margin)
   - Time: 30 minutes

## Next Audit
Timing: After deployment, verify env vars present in runtime
Command: `aws lambda get-function-configuration --function-name X --query 'Environment.Variables'`
```

---

### Example 2: Post-Incident Audit

```bash
/check-principles

# Context: Production incident - Lambda timeout despite recent optimization

## Error Pattern
Error: Task timed out after 30.00 seconds
Map to principles: #20 (Execution Boundaries), #6 (Deployment Monitoring)

## Audit Summary
Principles audited: 3 (incident-related)
Violations: 2

## Compliance Results

### Principle #20: Execution Boundary Discipline

Compliance question: Did we verify Lambda timeout configuration?

Verification: Check deployment history
```bash
git log --oneline -10 -- terraform/lambda.tf
```

Evidence:
```
No recent changes to timeout configuration
Timeout still 30s from initial setup 6 months ago
Code execution time increased from 15s → 45s over time
```

Status: ❌ VIOLATION

Gap: Never verified timeout matches current code requirements

Impact: Production outage (Lambda timeouts)

Root cause: Assumed 30s was enough, never re-verified as code evolved

---

### Principle #2: Progressive Evidence Strengthening

Compliance question: Did we verify beyond status code when optimizing?

Evidence:
```
Deployment 1: Added caching → Status 200 → Assumed fixed
Deployment 2: Optimized query → Status 200 → Assumed fixed
Deployment 3: Increased memory → Status 200 → Assumed fixed
All deployments: Still timing out in production
```

Status: ❌ VIOLATION

Gap: Stopped verification at Layer 1 (status code), didn't check Layer 4 (actual execution time)

Impact: 3 failed deployments, wasted 90 minutes

---

## Root Cause

Principle #20 violation (didn't verify execution boundaries)
→ Assumed 30s timeout was correct
→ Never checked aws lambda get-function-configuration
→ Code execution time grew beyond timeout constraint
→ Production outages

## Recommendations

Priority: CRITICAL
Fix: Verify timeout config, increase to match code requirements
Action:
1. Check current code execution time (CloudWatch)
2. Increase timeout to P99 * 1.5
3. Add monitoring alert if Duration > Timeout * 0.8
4. Add principle #20 to pre-deployment checklist

Verification:
```bash
aws lambda get-function-configuration --query 'Timeout'
aws cloudwatch get-metric-statistics --metric-name Duration ...
```
```

---

## Best Practices

### Do
- **Run before every deployment** (prevent issues)
- **Run after every incident** (root cause analysis)
- **Select context-appropriate scope** (deployment, incident, code review, health check)
- **Verify through evidence** (commands, not assumptions)
- **Prioritize recommendations** (CRITICAL blocks, HIGH warns, MEDIUM/LOW defer)
- **Create action items** with specific commands

### Don't
- **Don't skip pre-deployment audits** (catches issues before production)
- **Don't audit all 20 principles every time** (scope based on context)
- **Don't assume compliance** (verify through evidence)
- **Don't defer CRITICAL fixes** (blocks deployment)
- **Don't audit without action** (create concrete action items)

---

## Integration with Other Commands

**`/check-principles` → `/reflect`**:
- After incident, `/check-principles` identifies which principles violated
- Then `/reflect` analyzes why those principles weren't followed
- Result: Root cause + metacognitive learning

**`/check-principles` → `/validate`**:
- `/check-principles` identifies gaps (e.g., missing env var)
- Then `/validate` verifies fix applied correctly
- Result: Compliance verification

**`/check-principles` → deployment**:
- Pre-deployment `/check-principles` catches config mismatches
- Blocks deployment until CRITICAL issues fixed
- Result: Prevented production incident

---

## See Also

- **Principles**: [CLAUDE.md](../../CLAUDE.md) - All 20 principles
- **Execution Boundaries**: [execution-boundaries.md](../../checklists/execution-boundaries.md) - Principle #20 checklist
- **Commands**:
  - `/reflect` - Metacognitive analysis (after work)
  - `/validate` - Hypothesis verification (during work)
  - `/proof` - Evidence verification (during work)
- **Skills**:
  - [code-review](../../skills/code-review/) - PR compliance checking
  - [deployment](../../skills/deployment/) - Deployment verification
  - [error-investigation](../../skills/error-investigation/) - Incident analysis

---

## Prompt Template

When you invoke `/check-principles`, analyze:

**Context**: What triggered this audit? (deployment, incident, code review, health check)

**Scope**: Which principles are most relevant? (deployment, incident-related, code quality, architecture)

**Depth**: How deep to verify? (quick check, deep verification, systematic audit)

**For each principle**:
1. Compliance question (yes/no)
2. Verification method (how to check)
3. Evidence (actual data)
4. Status (compliant, partial, violation)
5. Gap (what's missing)
6. Impact (how it affects system)

**Recommendations**: Prioritize by severity (CRITICAL → LOW)

**Action items**: Concrete commands with verification steps

**Output**: Structured compliance audit following the format above.
