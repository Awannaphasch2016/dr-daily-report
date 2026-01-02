---
pattern_type: failure_mode
confidence: high
created: 2026-01-02
instances: 4
tags: [deployment, configuration, environment-variables, defensive-programming]
---

# Failure Pattern: Missing Deployment Flags/Environment Variables

## Abstracted From

**Instances analyzed**: 4

1. **Scheduler Lambda - Missing CACHE_TABLE_NAME** (Dec 2025)
   - Source: git:b21c887 "feat: Add startup configuration validation to scheduler Lambda"
   - Impact: Jobs marked "completed" but cache never written (silent failure for 2+ hours)
   - Detection: Added startup validation to fail fast

2. **Lambda TZ Environment Variable** (Dec 2025)
   - Source: git:e22089a "fix: Use Bangkok timezone for Aurora date queries"
   - Impact: Cache misses due to UTC/Bangkok date boundary mismatch
   - Root cause: TZ env var not set on Lambdas despite Principle #14 requiring it
   - Files affected: 3 Python files using implicit timezone

3. **Langfuse Observability Flags** (Dec 2025)
   - Source: git:f9dc132 "feat: Add Langfuse observability integration"
   - Missing: LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY, LANGFUSE_HOST
   - Impact: Observability decorators deployed but not active (graceful degradation saved)
   - Required: Manual Doppler update after Terraform deployment

4. **Async Report Worker - Missing TZ** (Jan 2026)
   - Source: terraform/async_report.tf:194-213
   - Status: **CURRENT - NOT YET FIXED**
   - Missing: `TZ = "Asia/Bangkok"` in environment variables
   - Impact: Will use UTC by default, causing same date boundary bug as #2
   - Comparison: fund_data_sync.tf:111 has `TZ = "Asia/Bangkok"` but async_report doesn't

---

## Pattern Description

### What It Is

**Infrastructure-Application Contract Violation**: When new application-level requirements (principles, features, configurations) are added to the codebase, but infrastructure deployment configurations (Terraform, GitHub Actions) are not updated to satisfy those requirements.

### When It Occurs

**Trigger conditions**:
1. New CLAUDE.md principle requires environment variable (e.g., TZ for Principle #14)
2. New feature requires API keys/secrets (e.g., Langfuse, OpenRouter)
3. New dependency requires configuration (e.g., Aurora table names)
4. Code uses `os.environ.get()` without validation at startup

**Common scenarios**:
- Adding new Lambda function (copy-paste env vars from existing, miss new ones)
- Updating principle (add to CLAUDE.md, forget to update Terraform)
- Adding observability (code deployed before secrets configured)
- Cross-environment drift (dev has flag, staging/prod missing)

### Why It Happens

**Root causes**:

1. **Multi-file synchronization gap**:
   - Application code in `src/` directory
   - Infrastructure in `terraform/` directory
   - Principles in `.claude/CLAUDE.md`
   - No automated contract validation between these layers

2. **Principle → Infrastructure lag**:
   - Principle added to CLAUDE.md (e.g., Timezone Discipline)
   - Python code follows principle (uses `datetime.now(bangkok_tz)`)
   - Terraform not updated (Lambda still uses UTC via missing TZ env var)
   - **Time gap**: Can be days/weeks between principle and infrastructure update

3. **Silent degradation**:
   - Python: `os.environ.get('TZ', 'UTC')` - Silent fallback hides missing config
   - Langfuse: Graceful degradation - Works without env vars (no errors)
   - Result: Tests pass, deployment succeeds, but feature not active

4. **Copy-paste inheritance**:
   - New Lambda created by copying existing Lambda config
   - Copy includes old env vars but misses new requirements
   - Example: fund_data_sync.tf has TZ, async_report.tf doesn't (copied before TZ added)

---

## Concrete Instances

### Instance 1: Scheduler Lambda - Missing CACHE_TABLE_NAME (High Impact)

**From**: git:b21c887 (Dec 8, 2025)

**Context**: Scheduler Lambda deployed to write precomputed reports to cache table

**Manifestation**:
```python
# src/scheduler/handler.py (before fix)
cache_table = os.environ.get('CACHE_TABLE_NAME')  # Returns None
# ... later ...
cache_table.put_item(...)  # AttributeError: NoneType has no attribute 'put_item'
```

**Impact**:
- Jobs marked "completed" in DynamoDB
- Cache writes silently failed (no error raised)
- Users saw "รายงานยังไม่พร้อม" errors despite jobs completed
- Took 2+ hours to debug (silent failure)

**Fix**:
```python
# Added startup validation
def _validate_configuration():
    required = ['CACHE_TABLE_NAME', 'AURORA_HOST', ...]
    missing = [v for v in required if not os.environ.get(v)]
    if missing:
        raise RuntimeError(f"Missing env vars: {missing}")
```

**Lesson**: "Validate configuration at startup, not on first use" (Defensive Programming)

---

### Instance 2: Lambda TZ Environment Variable (Medium Impact)

**From**: git:e22089a (Dec 31, 2025)

**Context**: CLAUDE.md Principle #14 (Timezone Discipline) added, requiring Bangkok timezone

**Manifestation**:
```python
# Python code followed principle
from zoneinfo import ZoneInfo
bangkok_tz = ZoneInfo("Asia/Bangkok")
today = datetime.now(bangkok_tz).date()  # 2025-12-31 04:00 Bangkok

# But Terraform missing TZ env var
# Lambda defaults to UTC
datetime.now().date()  # 2025-12-30 21:00 UTC (implicit)
```

**Impact**:
- Scheduler stores reports with date=2025-12-31 (Bangkok)
- LINE bot queries with date=2025-12-30 (UTC default)
- Cache miss! Reports exist but wrong date
- User-facing error despite data populated

**Fix**:
1. Short-term: Explicit `ZoneInfo("Asia/Bangkok")` in Python code
2. Long-term: Add `TZ = "Asia/Bangkok"` to all Lambda env vars in Terraform

**Lesson**: Principle → Code → Infrastructure (all 3 must align)

---

### Instance 3: Langfuse Observability Flags (Low Impact - Graceful Degradation)

**From**: git:f9dc132 (Dec 19, 2025)

**Context**: Added Langfuse observability to replace LangSmith ($99/mo → $0)

**Manifestation**:
```python
# src/integrations/langfuse_client.py deployed
@observe(name="generate_report")  # Decorator active
def generate_report():
    ...

# But Terraform missing Langfuse env vars
LANGFUSE_PUBLIC_KEY = None
LANGFUSE_SECRET_KEY = None
LANGFUSE_HOST = None

# Graceful degradation - no errors, but no traces sent
```

**Impact**:
- Code deployed successfully
- Tests passed (graceful fallback)
- **Feature not active** (no traces in Langfuse dashboard)
- Required manual Doppler secret update after deployment

**Fix**:
1. Add env vars to Terraform (git:f9dc132)
2. Update Doppler with actual keys
3. Redeploy Lambda

**Why low impact**: Graceful degradation prevented production failures

**Lesson**: "Fail fast" better than "graceful degradation" for missing config

---

### Instance 4: Async Report Worker - Missing TZ (CURRENT - Not Fixed)

**From**: terraform/async_report.tf:194-213 (Jan 2, 2026)

**Context**: Timezone Principle #14 exists, fund_data_sync has TZ, async_report doesn't

**Manifestation**:
```hcl
# terraform/fund_data_sync.tf:111 (CORRECT)
environment {
  variables = {
    TZ = "Asia/Bangkok"
    ...
  }
}

# terraform/async_report.tf:194 (MISSING TZ)
environment {
  variables = {
    OPENROUTER_API_KEY = var.OPENROUTER_API_KEY
    JOBS_TABLE_NAME    = aws_dynamodb_table.report_jobs.name
    # ❌ Missing: TZ = "Asia/Bangkok"
    ...
  }
}
```

**Impact** (predicted):
- Same date boundary bug as Instance #2
- Telegram report generation will use UTC dates
- Cache misses when querying Aurora (Bangkok dates)
- User-facing errors despite cached data

**Status**: **Detected via /abstract command** - Not yet deployed to production

**Fix needed**:
```hcl
environment {
  variables = {
    TZ                 = "Asia/Bangkok"  # ADD THIS
    OPENROUTER_API_KEY = var.OPENROUTER_API_KEY
    ...
  }
}
```

---

## Generalized Pattern

### Signature (How to Recognize It)

**Observable characteristics**:

1. **New principle in CLAUDE.md** → Code updated → Infrastructure not updated
   - grep ".claude/CLAUDE.md" for new principles
   - Check if Terraform has corresponding env vars

2. **Feature works in local dev** → Fails in deployed Lambda
   - Local: Has .env file or shell exports
   - Lambda: Missing Terraform env vars

3. **Copy-paste Lambda creation** → Missing new requirements
   - Old Lambda configs used as template
   - New requirements added after template creation

4. **Silent failures or graceful degradation**
   - Tests pass but feature not active
   - No errors but data inconsistent (date boundaries, cache misses)

5. **"Works on my machine"** syndrome
   - Developer has secrets in shell environment
   - Lambda doesn't have same environment

### Preconditions (What Enables It)

**Conditions that must hold**:

1. **Multi-layer architecture**:
   - Application code (`src/`)
   - Infrastructure (`terraform/`)
   - Principles (`.claude/CLAUDE.md`)
   - No automated contract validation

2. **Environment-dependent configuration**:
   - Code uses `os.environ.get()` or environment variables
   - No startup validation (fails on first use, not at startup)

3. **Time lag between layers**:
   - Principle added first
   - Code follows principle
   - Infrastructure updated last (or forgotten)

4. **Copy-paste reuse**:
   - New resources created from old templates
   - Templates predate new requirements

### Components (What's Involved)

**Entities**:

1. **CLAUDE.md** - Source of truth for principles
2. **Python code** (`src/`) - Application logic following principles
3. **Terraform** (`terraform/*.tf`) - Infrastructure configuration
4. **Doppler** - Secret management (external dependency)
5. **CI/CD** (GitHub Actions) - Deployment pipeline
6. **Lambda runtime** - Execution environment

**Dependency chain**:
```
CLAUDE.md Principle
    ↓ (informs)
Python Code (follows principle)
    ↓ (requires)
Terraform Env Vars (provides config)
    ↓ (references)
Doppler Secrets (stores sensitive values)
    ↓ (deployed by)
GitHub Actions (runs terraform apply)
    ↓ (creates)
Lambda Function (runtime environment)
```

**Failure point**: Arrow between "Python Code" and "Terraform Env Vars" breaks

### Mechanism (How It Works/Fails)

**Failure flow**:

```
Step 1: New Principle Added to CLAUDE.md
├─ Example: "Principle #14: Timezone Discipline - Use Bangkok timezone"
└─ Why: Standardize timezone for Bangkok users

Step 2: Python Code Updated to Follow Principle
├─ Code: datetime.now(ZoneInfo("Asia/Bangkok"))
├─ Tests: Pass (local dev has TZ env var or explicit timezone)
└─ Deployed: Code in Lambda image

Step 3: Infrastructure NOT Updated (GAP!)
├─ Terraform: Missing TZ env var in Lambda configuration
├─ Deployed Lambda: Falls back to UTC (Linux default)
└─ Result: Code expects Bangkok, runtime provides UTC

Step 4: Silent Failure or Data Inconsistency
├─ Symptom: Date boundary bugs (2025-12-30 vs 2025-12-31)
├─ Symptom: Cache misses (scheduler writes Bangkok date, API reads UTC date)
└─ Detection: Hours later when users report errors

Step 5: Debugging
├─ Check CloudWatch logs
├─ Notice date mismatch
├─ Trace back to missing TZ env var
└─ Fix: Add TZ to Terraform, redeploy
```

**Why it's hard to detect**:
- Tests pass (local env has config)
- Deployment succeeds (no build errors)
- Runtime errors are indirect (cache miss, not "missing TZ")
- No compile-time contract validation

---

## Pattern Template

### Failure Mode Template: Missing Deployment Flags

**Pattern Name**: Infrastructure-Application Contract Violation

**Category**: Configuration management, deployment

**Symptoms**:

1. **Error signature**:
   - `AttributeError: 'NoneType' has no attribute '...'` (missing env var)
   - Date boundary bugs (UTC vs local timezone)
   - Cache misses despite data present
   - Feature not active (graceful degradation)

2. **Timing**:
   - Appears after deployment
   - Not caught by tests or CI/CD
   - Hours/days after code changes

3. **Frequency**:
   - Every new principle requiring env var
   - Every new Lambda creation (copy-paste)
   - Every new feature requiring secrets

**Root Cause**:

**What actually causes this**:
- Multi-file synchronization gap (CLAUDE.md → Code → Terraform)
- No automated contract validation between application and infrastructure
- Time lag between principle addition and infrastructure update

**Detection**:

1. **Pre-deployment checks**:
   ```bash
   # Check if CLAUDE.md principles match Terraform env vars
   grep -r "Principle.*TZ\|timezone" .claude/CLAUDE.md
   grep -r "TZ.*=" terraform/*.tf

   # Compare env vars across Lambdas
   grep -A 20 "environment {" terraform/fund_data_sync.tf
   grep -A 20 "environment {" terraform/async_report.tf
   ```

2. **Runtime checks** (startup validation):
   ```python
   # src/scheduler/handler.py
   def _validate_configuration():
       required = ['TZ', 'AURORA_HOST', 'CACHE_TABLE_NAME', ...]
       missing = [v for v in required if not os.environ.get(v)]
       if missing:
           raise RuntimeError(f"Missing required env vars: {missing}")
   ```

3. **Post-deployment checks**:
   ```bash
   # Verify Lambda env vars
   aws lambda get-function-configuration \
     --function-name dr-daily-report-report-worker-dev \
     | jq '.Environment.Variables | keys'
   ```

**Prevention**:

1. **Pre-deployment validation**:
   - Run infrastructure tests (git:b565398)
   - Checklist: CLAUDE.md principles → Terraform env vars mapping
   - Automated: `scripts/validate_deployment_ready.sh`

2. **Startup validation** (Defensive Programming Principle #1):
   ```python
   # At Lambda handler entry point
   _validate_configuration()  # Fail fast if env vars missing
   ```

3. **Infrastructure templates**:
   - Create canonical Lambda env var template
   - New Lambdas use template (not copy-paste)
   - Template updated when principles added

4. **Contract testing**:
   - Test that verifies CLAUDE.md principles → Terraform alignment
   - Example: "If Principle #14 exists, all Lambdas must have TZ env var"

5. **Documentation**:
   - When adding principle, add checklist item:
     - [ ] Update CLAUDE.md
     - [ ] Update application code
     - [ ] Update Terraform env vars
     - [ ] Update Doppler secrets (if sensitive)
     - [ ] Run pre-deployment validation

**Resolution**:

**Short-term** (fix current deployment):
```bash
# 1. Identify missing env var
grep "missing\|error" cloudwatch-logs

# 2. Add to Terraform
vim terraform/async_report.tf
# Add: TZ = "Asia/Bangkok"

# 3. Apply infrastructure change
cd terraform/envs/dev
terraform apply

# 4. Wait for Lambda update
aws lambda wait function-updated \
  --function-name dr-daily-report-report-worker-dev

# 5. Verify env var present
aws lambda get-function-configuration \
  --function-name dr-daily-report-report-worker-dev \
  | jq '.Environment.Variables.TZ'
```

**Long-term** (prevent recurrence):
```bash
# 1. Add startup validation to all Lambdas
# See Instance #1 fix (b21c887)

# 2. Create pre-deployment validation script
# See git:b565398

# 3. Add to CI/CD pipeline
# .github/workflows/deploy.yml:
#   - name: Validate deployment readiness
#     run: ./scripts/validate_deployment_ready.sh

# 4. Create Lambda env var template
# terraform/templates/lambda_env_vars.tf

# 5. Document in CLAUDE.md
# Update Principle #1 (Defensive Programming) with:
# "All Lambdas must validate required env vars at startup"
```

---

## Variations

**Observed variations** across instances:

### Variation 1: Secret vs Non-Secret Configuration

**Secret** (Langfuse keys):
- Stored in Doppler
- Referenced in Terraform as `var.LANGFUSE_PUBLIC_KEY`
- Requires 2-step fix: (1) Add to Doppler, (2) Update Terraform

**Non-secret** (TZ, table names):
- Hardcoded in Terraform or computed from resources
- Single-step fix: Update Terraform

**Implication**: Secrets have higher deployment friction

### Variation 2: Impact Severity

**High impact** (CACHE_TABLE_NAME):
- Silent failure, data loss
- User-facing errors
- Requires immediate fix

**Medium impact** (TZ):
- Data inconsistency (date boundaries)
- Cache misses
- Can workaround with explicit timezone in code

**Low impact** (Langfuse):
- Graceful degradation
- Feature not active but no errors
- Non-critical observability feature

**Implication**: Prioritize startup validation for high-impact configs

### Variation 3: Detection Time

**Immediate** (startup validation):
- Lambda fails to start
- CloudWatch shows configuration error
- Fix before user impact

**Delayed** (first use):
- Lambda starts successfully
- Fails on first feature usage
- Silent failures accumulate

**Implication**: Startup validation critical for early detection

---

## When to Deviate

**Scenarios where standard pattern doesn't apply**:

1. **Intentional feature flags**:
   - Flag: `ENABLE_FEATURE_X = true/false`
   - Purpose: Gradual rollout, A/B testing
   - Expected: Missing flag = feature disabled
   - **Don't apply**: Startup validation would prevent deployment

2. **Optional observability**:
   - Example: Langfuse, DataDog, Sentry
   - Purpose: Non-critical monitoring
   - Expected: Graceful degradation if missing
   - **Don't apply**: Fail-fast would break deployments

3. **Environment-specific config**:
   - Dev: `DEBUG_MODE = true`
   - Prod: `DEBUG_MODE = false`
   - Expected: Different values per environment
   - **Don't apply**: Validation must account for env differences

**Modification needed**:
```python
# Flexible validation for optional configs
def _validate_configuration():
    # Required (fail-fast)
    required = ['AURORA_HOST', 'CACHE_TABLE_NAME']
    missing_required = [v for v in required if not os.environ.get(v)]
    if missing_required:
        raise RuntimeError(f"Missing REQUIRED env vars: {missing_required}")

    # Optional (warn only)
    optional = ['LANGFUSE_PUBLIC_KEY', 'DEBUG_MODE']
    missing_optional = [v for v in optional if not os.environ.get(v)]
    if missing_optional:
        logger.warning(f"Missing OPTIONAL env vars: {missing_optional} (features disabled)")
```

---

## Graduation Path

### Pattern Confidence: **HIGH** (4 instances with consistent signature)

**Graduation steps**:

#### 1. Update CLAUDE.md Principle #1 (Defensive Programming)

**Current**:
> Validate configuration at startup, not on first use.

**Proposed addition**:
> **Infrastructure-Application Contract**: When adding new principles requiring environment variables, update in this order:
> 1. Add principle to CLAUDE.md
> 2. Update application code to follow principle
> 3. **Update Terraform env vars for ALL affected Lambdas**
> 4. Update Doppler secrets (if sensitive)
> 5. Run pre-deployment validation (`scripts/validate_deployment_ready.sh`)
> 6. Deploy and verify env vars present
>
> Missing step 3 causes silent failures or data inconsistencies hours after deployment.

#### 2. Create Deployment Checklist

File: `.claude/checklists/adding-lambda-env-var.md`

```markdown
# Checklist: Adding Lambda Environment Variable

Use when: New principle or feature requires Lambda environment variable

## Pre-Change

- [ ] Identify which Lambdas need the env var
  - Check: Does Lambda use feature requiring config?
  - List: `grep -r "FEATURE_NAME" src/`

## Infrastructure Changes

- [ ] Add env var to Terraform
  - File: `terraform/{lambda_name}.tf`
  - Section: `environment { variables = { ... } }`
  - Value: Hardcoded, computed, or `var.VARIABLE_NAME`

- [ ] If secret: Add to Doppler
  - Config: `dev`, `staging`, `prod`
  - Terraform var: `TF_VAR_{VARIABLE_NAME}`

- [ ] Add to ALL affected Lambdas (check list from Pre-Change)
  - async_report.tf
  - telegram_api.tf
  - scheduler.tf
  - fund_data_sync.tf
  - etc.

## Validation

- [ ] Run pre-deployment validation
  ```bash
  ./scripts/validate_deployment_ready.sh
  ```

- [ ] Add startup validation to Lambda handler
  ```python
  def _validate_configuration():
      required = [' VARIABLE_NAME', ...]
      missing = [v for v in required if not os.environ.get(v)]
      if missing:
          raise RuntimeError(f"Missing: {missing}")
  ```

## Deployment

- [ ] Apply Terraform changes
  ```bash
  cd terraform/envs/dev
  terraform plan
  terraform apply
  ```

- [ ] Wait for Lambda update
  ```bash
  aws lambda wait function-updated \
    --function-name {lambda-name}
  ```

- [ ] Verify env var present
  ```bash
  aws lambda get-function-configuration \
    --function-name {lambda-name} \
    | jq '.Environment.Variables.VARIABLE_NAME'
  ```

## Post-Deployment

- [ ] Test feature in dev environment
- [ ] Check CloudWatch logs for startup validation success
- [ ] Verify no errors related to missing config
- [ ] Repeat for staging/prod environments

## Rollback Plan

If deployment fails due to missing config:

```bash
# Revert Terraform
git revert {commit-hash}
cd terraform/envs/dev
terraform apply

# Or: Add missing config and redeploy
doppler secrets set TF_VAR_VARIABLE_NAME="value"
terraform apply
```
```

#### 3. Create Infrastructure Template

File: `terraform/templates/lambda_common_env_vars.tf`

```hcl
# Common environment variables for all Lambdas
# Include via: merge(local.common_lambda_env_vars, { lambda-specific vars })

locals {
  common_lambda_env_vars = {
    # Timezone (Principle #14: Timezone Discipline)
    TZ = "Asia/Bangkok"

    # Environment identifier
    ENVIRONMENT = var.environment

    # Aurora connection (if Lambda needs database)
    AURORA_HOST     = aws_rds_cluster.aurora.endpoint
    AURORA_PORT     = "3306"
    AURORA_DATABASE = var.aurora_database_name
    AURORA_USER     = var.aurora_master_username
    AURORA_PASSWORD = var.AURORA_MASTER_PASSWORD

    # Observability (Principle #?: Langfuse Integration)
    LANGFUSE_PUBLIC_KEY = var.LANGFUSE_PUBLIC_KEY
    LANGFUSE_SECRET_KEY = var.LANGFUSE_SECRET_KEY
    LANGFUSE_HOST       = var.LANGFUSE_HOST
  }
}

# Usage in Lambda definitions:
# environment {
#   variables = merge(local.common_lambda_env_vars, {
#     # Lambda-specific vars
#     JOBS_TABLE_NAME = aws_dynamodb_table.report_jobs.name
#   })
# }
```

#### 4. Add Contract Test

File: `tests/infrastructure/test_lambda_env_vars.py`

```python
"""
Test that CLAUDE.md principles → Terraform env vars contract is maintained
"""
import pytest
import subprocess
import json
from typing import Dict, List

# Map CLAUDE.md principles to required env vars
PRINCIPLE_ENV_VAR_CONTRACT = {
    "Principle #14: Timezone Discipline": ["TZ"],
    "Langfuse Observability Integration": [
        "LANGFUSE_PUBLIC_KEY",
        "LANGFUSE_SECRET_KEY",
        "LANGFUSE_HOST"
    ],
    "Aurora-First Data Architecture": [
        "AURORA_HOST",
        "AURORA_PORT",
        "AURORA_DATABASE",
        "AURORA_USER",
        "AURORA_PASSWORD"
    ],
}

# Lambdas that should have env vars
LAMBDAS_TO_CHECK = [
    "dr-daily-report-report-worker-dev",
    "dr-daily-report-telegram-api-dev",
    "dr-daily-report-scheduler-dev",
]


def get_lambda_env_vars(function_name: str) -> Dict[str, str]:
    """Get environment variables from deployed Lambda"""
    result = subprocess.run(
        [
            "aws", "lambda", "get-function-configuration",
            "--function-name", function_name
        ],
        capture_output=True,
        text=True
    )
    config = json.loads(result.stdout)
    return config.get("Environment", {}).get("Variables", {})


@pytest.mark.integration
@pytest.mark.parametrize("lambda_name", LAMBDAS_TO_CHECK)
def test_lambda_has_required_env_vars_per_principles(lambda_name: str):
    """
    Verify deployed Lambda has env vars required by CLAUDE.md principles

    This test enforces Infrastructure-Application Contract:
    - If principle exists → Lambda must have corresponding env vars
    - Prevents "missing deployment flags" failure mode
    """
    env_vars = get_lambda_env_vars(lambda_name)

    # Check each principle's required env vars
    for principle, required_vars in PRINCIPLE_ENV_VAR_CONTRACT.items():
        missing = [var for var in required_vars if var not in env_vars]

        assert not missing, (
            f"Lambda {lambda_name} violates '{principle}'\n"
            f"Missing required env vars: {missing}\n"
            f"Fix: Add to terraform/{lambda_name.split('-')[-2]}.tf environment block"
        )


@pytest.mark.integration
def test_all_lambdas_have_consistent_common_env_vars():
    """
    Verify all Lambdas have same common env vars (TZ, LANGFUSE_*, etc.)

    Prevents copy-paste inheritance issues where new Lambda
    misses env vars that were added after template creation
    """
    common_vars = ["TZ", "ENVIRONMENT"]

    lambda_env_vars = {
        lambda_name: get_lambda_env_vars(lambda_name)
        for lambda_name in LAMBDAS_TO_CHECK
    }

    for lambda_name, env_vars in lambda_env_vars.items():
        missing = [var for var in common_vars if var not in env_vars]

        assert not missing, (
            f"Lambda {lambda_name} missing common env vars: {missing}\n"
            f"All Lambdas should use: terraform/templates/lambda_common_env_vars.tf"
        )
```

#### 5. Update Deployment Workflow

File: `.github/workflows/deploy.yml` (add step)

```yaml
- name: Validate Deployment Readiness
  run: |
    chmod +x scripts/validate_deployment_ready.sh
    ENV=${{ env.ENVIRONMENT }} ./scripts/validate_deployment_ready.sh

- name: Run Infrastructure Contract Tests
  run: |
    ENV=${{ env.ENVIRONMENT }} doppler run -- pytest \
      tests/infrastructure/test_lambda_env_vars.py \
      -m integration \
      -v
```

---

## Action Items

- [x] Pattern extracted from 4 instances
- [x] Template created for failure mode
- [ ] Update CLAUDE.md Principle #1 (Infrastructure-Application Contract)
- [ ] Create `.claude/checklists/adding-lambda-env-var.md`
- [ ] Create `terraform/templates/lambda_common_env_vars.tf`
- [ ] Create `tests/infrastructure/test_lambda_env_vars.py` (contract test)
- [ ] Fix Instance #4: Add `TZ = "Asia/Bangkok"` to async_report.tf
- [ ] Add pre-deployment validation to GitHub Actions workflow
- [ ] Update deployment skill with this pattern

---

## References

### Code Files

- Startup validation: `src/scheduler/handler.py:608-688` (git:b21c887)
- Pre-deployment script: `scripts/validate_deployment_ready.sh` (git:b565398)
- Terraform configs: `terraform/async_report.tf`, `terraform/fund_data_sync.tf`

### Git Commits

- b21c887: "feat: Add startup configuration validation to scheduler Lambda"
- e22089a: "fix: Use Bangkok timezone for Aurora date queries"
- f9dc132: "feat: Add Langfuse observability integration"
- b565398: "feat: Add pre-deployment configuration validation script"

### Principles

- CLAUDE.md Principle #1: Defensive Programming
- CLAUDE.md Principle #14: Timezone Discipline (missing from Lambdas)

### Related Patterns

- Progressive Evidence Strengthening (Principle #2) - Verify env vars at multiple layers
- Single Execution Path Principle (Principle #12) - No silent fallbacks

---

## Metadata

**Pattern Type**: failure_mode

**Confidence**: High (4 instances, consistent signature, clear fix pattern)

**Created**: 2026-01-02

**Instances**: 4 (3 historical + 1 current)

**Last Updated**: 2026-01-02

**Graduation Status**: Ready for CLAUDE.md integration

**Impact**: High (prevents hours of debugging silent failures)
