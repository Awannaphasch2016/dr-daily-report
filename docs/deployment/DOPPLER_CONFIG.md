# Doppler Configuration Guide

## Overview

Multi-environment Doppler setup using config inheritance to share secrets while allowing environment-specific overrides.

**Environments**:
- `local` - Local development (SSM tunnel to Aurora)
- `dev` - AWS development (Lambda, Aurora)
- `stg` - AWS staging
- `prd` - AWS production

**Config Hierarchy**:
```
dev (root, inheritable)
  └─ local_dev (branch, inherits from dev)
stg (root)
prd (root)
```

---

## Doppler Constraints

### 1. Same-Environment Inheritance Forbidden

**Constraint**: Configs cannot inherit from other configs in the same environment.

**Example** (❌ Invalid):
```bash
# Both in 'dev' environment
dev_local (env: dev)
  └─ inherits from dev (env: dev)

Error: "Config cannot inherit from another config in the same environment"
```

**Solution**: Use separate `local` environment:
```bash
dev (env: dev) ← root config
local_dev (env: local) ← inherits from dev
```

**Why**: Doppler enforces environment boundaries to prevent circular dependencies.

---

### 2. Environment-Prefixed Naming Required

**Constraint**: Configs in an environment must use that environment's prefix.

**Example** (❌ Invalid):
```bash
# Config in 'local' environment
doppler configs create dev_local --environment local

Error: "Config name must start with 'local_' (ex: local_backend)"
```

**Solution**: Use environment prefix:
```bash
doppler configs create local_dev --environment local  # ✅ Valid
```

**Naming Pattern**:
- `local` environment: `local_*` (e.g., `local_dev`, `local_stg`)
- `dev` environment: `dev_*` or `dev` (root)
- No environment constraints on root config names

**Why**: Makes config-environment relationship self-documenting.

---

### 3. Validate Secrets at Startup

**Constraint**: Application must validate required secrets at startup, not on first use.

**Anti-pattern** (❌):
```python
def send_report():
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise ValueError("Missing API key")  # Fails at runtime
```

**Best practice** (✅):
```python
# At application startup
REQUIRED_SECRETS = ["AURORA_HOST", "AURORA_PASSWORD", "OPENROUTER_API_KEY"]
missing = [s for s in REQUIRED_SECRETS if not os.getenv(s)]
if missing:
    raise ValueError(f"Missing required secrets: {missing}")  # Fails immediately
```

**Why**: Fail-fast principle - catch missing secrets before processing user requests.

---

## Config Organization

### Root Config: `dev` (AWS Development)

**Purpose**: Shared development secrets for AWS Lambda deployments

**Secrets** (9 total):
```
AURORA_HOST=dev-aurora.cluster-xxx.ap-southeast-1.rds.amazonaws.com
AURORA_PORT=3306
AURORA_DATABASE=daily_report_dev
AURORA_USER=admin
AURORA_PASSWORD=<encrypted>
OPENROUTER_API_KEY=sk-or-v1-dev...
TELEGRAM_BOT_TOKEN=7573949249:...
PDF_BUCKET_NAME=dr-daily-report-pdfs-dev
REPORT_JOBS_QUEUE_URL=https://sqs.ap-southeast-1.amazonaws.com/.../dev
```

**Inheritable**: Yes (allows `local_dev` to inherit)

---

### Branch Config: `local_dev` (Local Development)

**Purpose**: Local development with SSM tunnel and mock flags

**Environment**: `local` (separate from `dev`)

**Inherits from**: `rag-chatbot-worktree.dev`

**Local Overrides** (9 secrets):
```
AURORA_HOST=localhost              # SSM tunnel endpoint
AURORA_PORT=3307                   # SSM tunnel port
AURORA_DATABASE=ticker_data        # Local database name
AURORA_USERNAME=admin
AURORA_PASSWORD=<local-password>
MOCK_AURORA=true                   # Speed up local dev (skip DB queries)
TELEGRAM_API_URL=http://localhost:8001  # Local dev server
RDS_HOST=localhost                 # Compatibility (if needed)
RDS_PORT=3307
```

**Inherited from `dev`** (9 secrets):
- `OPENROUTER_API_KEY`
- `TELEGRAM_BOT_TOKEN`
- `PDF_BUCKET_NAME`
- `REPORT_JOBS_QUEUE_URL`
- `AURORA_MASTER_PASSWORD`
- `RDS_DATABASE` (legacy, unused)
- `RDS_USER` (legacy, unused)
- `RDS_PASSWORD` (legacy, unused)
- `DOPPLER_PROJECT`, `DOPPLER_ENVIRONMENT`, `DOPPLER_CONFIG` (auto-set)

**Total**: 18 secrets (9 local + 9 inherited)

---

## Setup Workflows

### New Developer Onboarding

**Goal**: Set up local Doppler config for new developer

**Steps**:

1. **Install Doppler CLI**:
   ```bash
   # macOS
   brew install doppler

   # Linux
   curl -sLf https://cli.doppler.com/install.sh | sh
   ```

2. **Login to Doppler**:
   ```bash
   doppler login
   ```

3. **Configure project directory**:
   ```bash
   cd /path/to/dr-daily-report_telegram
   doppler setup --project rag-chatbot-worktree --config local_dev
   ```

4. **Verify secrets**:
   ```bash
   doppler run -- env | grep -E "AURORA_HOST|MOCK_AURORA"
   # Expected:
   #   AURORA_HOST=localhost
   #   MOCK_AURORA=true
   ```

5. **Start SSM tunnel** (for Aurora access):
   ```bash
   aws ssm start-session \
     --target <bastion-instance-id> \
     --document-name AWS-StartPortForwardingSessionToRemoteHost \
     --parameters '{"host":["dev-aurora.cluster-xxx..."],"portNumber":["3306"],"localPortNumber":["3307"]}'
   ```

6. **Run application**:
   ```bash
   doppler run -- python -m src.main
   ```

---

### Create New Environment

**Goal**: Add new environment (e.g., `staging2`, `prod-eu`)

**Steps**:

1. **Create Doppler environment**:
   ```bash
   doppler environments create "Staging 2" stg2 --project rag-chatbot-worktree
   ```

2. **Create root config**:
   ```bash
   doppler configs create stg2 --project rag-chatbot-worktree --environment stg2
   ```

3. **Add secrets**:
   ```bash
   doppler secrets set AURORA_HOST staging2-aurora.cluster-xxx... \
     --project rag-chatbot-worktree --config stg2

   doppler secrets set AURORA_PORT 3306 --project rag-chatbot-worktree --config stg2
   # ... (add all required secrets)
   ```

4. **Create service token for CI/CD**:
   ```bash
   doppler configs tokens create stg2-cicd \
     --project rag-chatbot-worktree \
     --config stg2 \
     --max-age 0
   ```

5. **Add token to GitHub Secrets**:
   - Go to GitHub repo → Settings → Secrets
   - Add secret: `DOPPLER_TOKEN_STG2` = <token from step 4>

6. **Update CI/CD workflows**:
   ```yaml
   # .github/workflows/deploy-stg2.yml
   jobs:
     deploy-stg2:
       steps:
         - name: Deploy with Doppler secrets
           env:
             DOPPLER_TOKEN: ${{ secrets.DOPPLER_TOKEN_STG2 }}
           run: |
             doppler run -- terraform apply -var-file=envs/stg2/terraform.tfvars
   ```

---

### Migrate Secrets Between Configs

**Goal**: Move secrets from one config to another (e.g., consolidate duplicates)

**Scenario**: Remove duplicated `OPENROUTER_API_KEY` from `local_dev`, rely on inheritance from `dev`

**Steps**:

1. **Verify secret exists in parent config**:
   ```bash
   doppler secrets get OPENROUTER_API_KEY --project rag-chatbot-worktree --config dev
   # Ensure it exists and has correct value
   ```

2. **Verify inheritance is working**:
   ```bash
   doppler configs get local_dev --project rag-chatbot-worktree --json | jq '.inherits'
   # Expected: ["rag-chatbot-worktree.dev"]
   ```

3. **Delete duplicate secret from child config**:
   ```bash
   doppler secrets delete OPENROUTER_API_KEY --project rag-chatbot-worktree --config local_dev
   ```

4. **Verify inheritance pulled secret**:
   ```bash
   doppler secrets get OPENROUTER_API_KEY --project rag-chatbot-worktree --config local_dev
   # Should return value from 'dev' config (inherited)
   ```

5. **Test application**:
   ```bash
   doppler run --config local_dev -- env | grep OPENROUTER_API_KEY
   # Ensure secret is still accessible
   ```

---

## Troubleshooting

### Issue 1: Missing Secrets

**Symptom**: Application fails with "Missing required secret: AURORA_HOST"

**Diagnosis**:
```bash
# Check if secret exists in current config
doppler secrets get AURORA_HOST --project rag-chatbot-worktree --config local_dev
```

**Solutions**:

**Case A: Secret doesn't exist in config**
```bash
# Add secret to config
doppler secrets set AURORA_HOST localhost --project rag-chatbot-worktree --config local_dev
```

**Case B: Wrong config selected**
```bash
# Check current config
doppler setup

# Expected output:
#   project: rag-chatbot-worktree
#   config: local_dev

# If wrong config, reset:
doppler setup --project rag-chatbot-worktree --config local_dev
```

**Case C: Inheritance not working**
```bash
# Check inheritance status
doppler configs get local_dev --project rag-chatbot-worktree --json | jq '.inherits'

# If empty [], inheritance not configured:
doppler configs update local_dev \
  --project rag-chatbot-worktree \
  --inherits rag-chatbot-worktree.dev
```

---

### Issue 2: Inheritance Not Working

**Symptom**: Secrets from parent config not accessible in child config

**Diagnosis**:
```bash
# Check inheritance configuration
doppler configs get local_dev --project rag-chatbot-worktree --json | jq '.inherits'

# Expected: ["rag-chatbot-worktree.dev"]
# If []: Inheritance not configured
```

**Root Causes**:

**Cause A: Same-environment inheritance**
```bash
# Both in 'dev' environment
doppler configs get dev_local --json | jq '.environment'  # Output: "dev"
doppler configs get dev --json | jq '.environment'        # Output: "dev"

# Error when trying to inherit:
doppler configs update dev_local --inherits rag-chatbot-worktree.dev
# Error: "Config cannot inherit from another config in the same environment"

# Solution: Use separate 'local' environment for local_dev
```

**Cause B: Parent not inheritable**
```bash
# Check if parent config is inheritable
doppler configs get dev --project rag-chatbot-worktree --json | jq '.inheritable'

# If false:
doppler configs update dev --project rag-chatbot-worktree --inheritable
```

**Cause C: Typo in parent config name**
```bash
# Verify parent config name
doppler configs --project rag-chatbot-worktree

# Use exact name with project prefix:
doppler configs update local_dev \
  --project rag-chatbot-worktree \
  --inherits rag-chatbot-worktree.dev
  # Note: rag-chatbot-worktree.dev (not just "dev")
```

---

### Issue 3: Environment-Prefixed Naming Error

**Symptom**: "Config name must start with 'local_' (ex: local_backend)"

**Diagnosis**: Trying to create config in `local` environment without `local_` prefix

**Example**:
```bash
doppler configs create dev_local --project rag-chatbot-worktree --environment local
# Error: Config name must start with 'local_'
```

**Solution**: Use environment prefix
```bash
doppler configs create local_dev --project rag-chatbot-worktree --environment local
```

**Why**: Doppler enforces naming convention to make config-environment relationship explicit.

---

## Migration History

### 2025-12-24 to 2025-12-25: dev_local → local_dev

**Before**:
- Config: `dev_local` (in `dev` environment, no inheritance)
- Secrets: 16 total (all defined locally, duplication)
- Issues: Secret drift, manual sync, confusing `AURORA_*` vs `RDS_*`

**After**:
- Config: `local_dev` (in `local` environment, inherits from `dev`)
- Secrets: 18 total (9 local overrides + 9 inherited)
- Benefits: Automatic sync, no duplication, clear naming

**Migration Steps**:
1. Created `local` environment
2. Created `local_dev` config with inheritance
3. Added local overrides (AURORA_HOST=localhost, MOCK_AURORA=true)
4. Verified all secrets accessible (18 total)
5. Updated local directory setup
6. Tested all workflows

**Key Decision**: Use `local_dev` name (not `dev_local`) due to Doppler constraint requiring `local_*` prefix for `local` environment.

**Evidence**: 74 `AURORA_*` references in code, 0 `RDS_*` references → Code uses `AURORA_*` exclusively.

---

## References

**Doppler Documentation**:
- [Config Inheritance](https://docs.doppler.com/docs/config-inheritance)
- [Branch Configs](https://docs.doppler.com/docs/branch-configs)
- [Environment-Based Configuration](https://docs.doppler.com/docs/environment-based-configuration)

**Project Documentation**:
- [.claude/CLAUDE.md](./.claude/CLAUDE.md) - Principle #13 (Secret Management Discipline)
- [.claude/archive/2025-12-doppler-migration/](./.claude/archive/2025-12-doppler-migration/) - Historical migration documents

**Archived Specifications** (for historical context):
- [Doppler Config Organization](./.claude/archive/2025-12-doppler-migration/2025-12-24-doppler-config-organization-for-multi-env.md)
- [dev_local vs local_dev Analysis](./.claude/archive/2025-12-doppler-migration/2025-12-25-dev-local-vs-local-dev.md)
- [Naming Convention What-If](./.claude/archive/2025-12-doppler-migration/2025-12-25-rename-local-dev-to-dev-local-with-inheritance.md)
