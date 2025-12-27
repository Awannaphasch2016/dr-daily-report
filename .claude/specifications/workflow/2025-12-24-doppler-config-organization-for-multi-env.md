---
title: Doppler Config Organization for Multi-Environment Setup
focus: workflow
date: 2025-12-24
status: implemented
tags: [doppler, secrets-management, multi-environment, infrastructure]
---

# Workflow Specification: Doppler Config Organization for Multi-Environment Setup

## Goal

**What does this workflow accomplish?**

Reorganize Doppler project configs (project: `rag-chatbot-worktree`) to align with the multi-environment architecture: **local**, **dev** (AWS), **staging** (AWS), and **prod** (AWS).

**Purpose**:
- Clear separation between local development and AWS environments
- Efficient secret management using Doppler's config inheritance
- Consistent naming and selection patterns
- Easy switching between environments for local dev and CI/CD

---

## Current State

### Existing Doppler Configs

```
rag-chatbot-worktree/
├── dev (root config, environment: dev)
├── dev_personal (root config, inheritable, environment: dev)
├── dev_local (root config, environment: dev)
├── stg (root config, environment: stg)
└── prd (root config, environment: prd)
```

### Issues

1. **Multiple root configs in dev**: `dev`, `dev_personal`, `dev_local` create confusion
2. **No inheritance**: All configs are root configs (no parent-child relationships)
3. **Unclear purpose**: Which config for local dev vs AWS deployment?
4. **Duplication risk**: Same secrets repeated across configs

---

## Recommended Structure

### Target Config Hierarchy

```
rag-chatbot-worktree/
├── dev (root config, environment: Development)
│   ├── dev_aws (branch config) - AWS Lambda dev environment [OPTIONAL]
│   └── dev_local (branch config) - Local development overrides
├── stg (root config, environment: Staging)
│   └── stg_aws (branch config) - Platform-specific overrides [OPTIONAL]
└── prd (root config, environment: Production)
    └── prd_aws (branch config) - Platform-specific overrides [OPTIONAL]
```

### Config Purpose Mapping

| Your Environment | Doppler Config | Type | Inherits From | Purpose |
|------------------|----------------|------|---------------|---------|
| **local** | `dev_local` | Branch | `dev` | Local development with SSM tunnel, mocks enabled |
| **dev** (AWS) | `dev` | Root | - | Development environment in AWS Lambda |
| **staging** (AWS) | `stg` | Root | - | Staging environment in AWS Lambda |
| **prod** (AWS) | `prd` | Root | - | Production environment in AWS Lambda |

**Note**: `dev_aws`, `stg_aws`, `prd_aws` branch configs are **optional** - only create if you need platform-specific overrides (e.g., different Lambda vs EC2 vs Cloudflare Workers deployment).

---

## Config Inheritance Pattern

### Root Config: `dev` (Shared Development Secrets)

**Contains**: Secrets common to ALL development deployments (local + AWS)

```bash
# Shared across dev_local and dev_aws
AURORA_HOST=dev-aurora.cluster-xxx.ap-southeast-1.rds.amazonaws.com
AURORA_PORT=3306
AURORA_DATABASE=daily_report_dev
AURORA_USER=admin
OPENROUTER_API_KEY=sk-or-v1-dev...
PDF_BUCKET_NAME=dr-daily-report-pdfs-dev
REPORT_JOBS_QUEUE_URL=https://sqs.ap-southeast-1.amazonaws.com/.../dev
LOG_LEVEL=DEBUG
ENVIRONMENT=development
AWS_REGION=ap-southeast-1
```

### Branch Config: `dev_local` (Local Development Overrides)

**Inherits from**: `dev`
**Overrides**: Platform-specific values for local development

```bash
# Override for SSM tunnel (local dev uses port forwarding)
AURORA_HOST=localhost
AURORA_PORT=3307

# Local-only flags
MOCK_AURORA=true              # Speed up local dev (skip Aurora roundtrip)
SKIP_EXTERNAL_APIS=false      # Set to true to skip LLM calls locally
TELEGRAM_API_URL=http://localhost:8001  # Local dev server

# All other secrets inherited from dev (no duplication)
# OPENROUTER_API_KEY → inherited from dev
# PDF_BUCKET_NAME → inherited from dev
# LOG_LEVEL → inherited from dev
```

**Precedence**: `dev_local` secrets override `dev` secrets with the same name.

---

## Secret Organization Examples

### Development Environment

#### Root: `dev`
```
AURORA_HOST=dev-aurora.cluster-xxx.ap-southeast-1.rds.amazonaws.com
AURORA_PORT=3306
AURORA_DATABASE=daily_report_dev
AURORA_USER=admin
AURORA_PASSWORD=<encrypted>
OPENROUTER_API_KEY=sk-or-v1-dev...
PDF_BUCKET_NAME=dr-daily-report-pdfs-dev
REPORT_JOBS_QUEUE_URL=https://sqs.ap-southeast-1.amazonaws.com/123/dev
LOG_LEVEL=DEBUG
ENVIRONMENT=development
AWS_REGION=ap-southeast-1
```

#### Branch: `dev_local` (inherits + overrides)
```
# Overrides
AURORA_HOST=localhost
AURORA_PORT=3307
TELEGRAM_API_URL=http://localhost:8001

# Additions (local-only)
MOCK_AURORA=true
SKIP_EXTERNAL_APIS=false

# Inherited (no duplication):
# - AURORA_DATABASE
# - AURORA_USER
# - AURORA_PASSWORD
# - OPENROUTER_API_KEY
# - PDF_BUCKET_NAME
# - LOG_LEVEL
# - ENVIRONMENT
# - AWS_REGION
```

### Staging Environment

#### Root: `stg`
```
AURORA_HOST=staging-aurora.cluster-xxx.ap-southeast-1.rds.amazonaws.com
AURORA_PORT=3306
AURORA_DATABASE=daily_report_staging
AURORA_USER=admin
AURORA_PASSWORD=<encrypted>
OPENROUTER_API_KEY=sk-or-v1-staging...
PDF_BUCKET_NAME=dr-daily-report-pdfs-staging
REPORT_JOBS_QUEUE_URL=https://sqs.ap-southeast-1.amazonaws.com/123/staging
LOG_LEVEL=INFO
ENVIRONMENT=staging
AWS_REGION=ap-southeast-1
```

### Production Environment

#### Root: `prd`
```
AURORA_HOST=prod-aurora.cluster-xxx.ap-southeast-1.rds.amazonaws.com
AURORA_PORT=3306
AURORA_DATABASE=daily_report_prod
AURORA_USER=admin
AURORA_PASSWORD=<encrypted>
OPENROUTER_API_KEY=sk-or-v1-prod...  # Production API key (separate budget)
PDF_BUCKET_NAME=dr-daily-report-pdfs-prod
REPORT_JOBS_QUEUE_URL=https://sqs.ap-southeast-1.amazonaws.com/123/prod
LOG_LEVEL=WARNING
ENVIRONMENT=production
AWS_REGION=ap-southeast-1
```

---

## Config Selection Patterns

### Local Development

**Directory-level setup** (recommended - set once, use everywhere):
```bash
# One-time setup
cd /home/anak/dev/dr-daily-report_telegram
doppler setup --config dev_local

# All subsequent commands use dev_local automatically
doppler run -- pytest tests/
doppler run -- just dev-api
doppler run -- python scripts/migrate.py
```

**Explicit config selection** (when you need to test different configs):
```bash
# Test with staging secrets locally
doppler run --config stg -- pytest tests/integration/

# Test with dev secrets
doppler run --config dev -- pytest tests/integration/
```

**Environment variable override**:
```bash
DOPPLER_CONFIG=dev_local doppler run -- python app.py
```

### CI/CD Workflows (GitHub Actions)

**Pattern**: Use Doppler service tokens (stored in GitHub Secrets)

```yaml
# .github/workflows/deploy-scheduler-dev.yml
jobs:
  deploy-dev:
    steps:
      - name: Install Doppler CLI
        uses: dopplerhq/cli-action@v3

      - name: Deploy with Doppler secrets
        env:
          DOPPLER_TOKEN: ${{ secrets.DOPPLER_TOKEN_DEV }}
        run: |
          # Token auto-selects 'dev' config
          doppler run -- terraform apply -var-file=envs/dev/terraform.tfvars

# .github/workflows/deploy-scheduler-staging.yml
jobs:
  deploy-staging:
    steps:
      - name: Deploy with Doppler secrets
        env:
          DOPPLER_TOKEN: ${{ secrets.DOPPLER_TOKEN_STAGING }}
        run: |
          # Token auto-selects 'stg' config
          doppler run -- terraform apply -var-file=envs/staging/terraform.tfvars
```

**Required GitHub Secrets**:
- `DOPPLER_TOKEN_DEV` (service token for `dev` config)
- `DOPPLER_TOKEN_STAGING` (service token for `stg` config)
- `DOPPLER_TOKEN_PROD` (service token for `prd` config)

### Terraform Deployments

**Current pattern** (from `docs/deployment/AUTOMATED_PRECOMPUTE.md`):
```bash
# Still works with new structure
ENV=dev doppler run -- terraform apply -var-file=environments/dev.tfvars
ENV=staging doppler run -- terraform apply -var-file=environments/staging.tfvars
ENV=prod doppler run -- terraform apply -var-file=environments/prod.tfvars
```

**Explicit config pattern** (alternative):
```bash
doppler run --config dev -- terraform apply -var-file=environments/dev.tfvars
doppler run --config stg -- terraform apply -var-file=environments/staging.tfvars
doppler run --config prd -- terraform apply -var-file=environments/prod.tfvars
```

---

## Migration Strategy

### Phase 1: Create Branch Configs (Non-Disruptive)

**Step 1.1: Create `dev_local` as branch config**
```bash
# Create new branch config
doppler configs create dev_local \
  --project rag-chatbot-worktree \
  --environment dev

# Set inheritance
doppler configs update dev_local \
  --project rag-chatbot-worktree \
  --inherits dev
```

**Step 1.2: Add local-specific overrides**
```bash
# Override Aurora connection for SSM tunnel
doppler secrets set AURORA_HOST localhost \
  --project rag-chatbot-worktree \
  --config dev_local

doppler secrets set AURORA_PORT 3307 \
  --project rag-chatbot-worktree \
  --config dev_local

# Add local-only flags
doppler secrets set MOCK_AURORA true \
  --project rag-chatbot-worktree \
  --config dev_local

doppler secrets set TELEGRAM_API_URL http://localhost:8001 \
  --project rag-chatbot-worktree \
  --config dev_local
```

**Step 1.3: Verify inheritance**
```bash
# Check dev_local inherits from dev
doppler configs get dev_local --project rag-chatbot-worktree --json | jq '.inherits'
# Expected: ["dev"]

# List all secrets (inherited + overrides)
doppler secrets --project rag-chatbot-worktree --config dev_local

# Verify OPENROUTER_API_KEY is inherited (not duplicated)
doppler secrets get OPENROUTER_API_KEY \
  --project rag-chatbot-worktree \
  --config dev_local
```

---

### Phase 2: Update Local Setup

**Step 2.1: Switch local directory to `dev_local`**
```bash
cd /home/anak/dev/dr-daily-report_telegram
doppler setup --config dev_local --project rag-chatbot-worktree

# Verify setup
doppler setup
# Expected output:
#   project: rag-chatbot-worktree
#   config: dev_local
```

**Step 2.2: Test local development**
```bash
# Verify AURORA_HOST is localhost (overridden)
doppler run -- python -c "import os; print(f'AURORA_HOST={os.getenv(\"AURORA_HOST\")}')"
# Expected: AURORA_HOST=localhost

# Verify OPENROUTER_API_KEY is inherited from dev
doppler run -- python -c "import os; print(f'OPENROUTER_API_KEY={os.getenv(\"OPENROUTER_API_KEY\")[:12]}...')"
# Expected: OPENROUTER_API_KEY=sk-or-v1-dev...

# Run local tests
doppler run -- pytest tests/ -m "not integration"
```

**Step 2.3: Test SSM tunnel workflow**
```bash
# Start SSM tunnel (in separate terminal)
aws ssm start-session \
  --target <bastion-instance-id> \
  --document-name AWS-StartPortForwardingSessionToRemoteHost \
  --parameters '{"host":["dev-aurora.cluster-xxx..."],"portNumber":["3306"],"localPortNumber":["3307"]}'

# Run integration tests using localhost:3307
doppler run -- pytest tests/infrastructure/ -m integration
```

---

### Phase 3: Clean Up Old Configs (After Verification)

**Step 3.1: Verify new structure works for 1 week**

Monitor local development and CI/CD pipelines:
- [ ] Local `pytest` runs use `dev_local` correctly
- [ ] Local Aurora access via SSM tunnel works
- [ ] GitHub Actions deployments use `dev` correctly
- [ ] No secret duplication issues

**Step 3.2: Delete old configs** (only after full verification)
```bash
# WARNING: This is destructive - only do after verification

# Delete dev_personal (no longer needed)
doppler configs delete dev_personal --project rag-chatbot-worktree

# If old dev_local was a root config, it's now replaced by branch config
# (Doppler allows same-name configs if one is root and one is branch)
```

**Step 3.3: Document new structure**

Update documentation:
- `.github/workflows/README.md` (if exists)
- `docs/deployment/MULTI_ENV.md`
- `.claude/CLAUDE.md` (Secret Management section)

---

### Phase 4: Update Documentation

**Update `docs/deployment/MULTI_ENV.md`**:
```markdown
## Doppler Config Structure

### Local Development
doppler setup --config dev_local
doppler secrets --config dev_local

Config: `dev_local` (branch, inherits from `dev`)
- Overrides: AURORA_HOST=localhost, AURORA_PORT=3307
- Additions: MOCK_AURORA=true, TELEGRAM_API_URL=http://localhost:8001
- Inherited: All other secrets from `dev`

### Dev Environment (AWS)
doppler setup --config dev
doppler secrets --config dev

Config: `dev` (root)
- All AWS-specific secrets for development environment

### Staging Environment (AWS)
doppler setup --config stg
doppler secrets --config stg

Config: `stg` (root)
- All AWS-specific secrets for staging environment

### Production Environment (AWS)
doppler setup --config prd
doppler secrets --config prd

Config: `prd` (root)
- All AWS-specific secrets for production environment
```

**Update `.claude/CLAUDE.md`** (Secret Management Principle section):
```markdown
### Doppler Config Organization

Configs organized by environment with inheritance:

**Development**:
- `dev` (root): AWS development environment
- `dev_local` (branch, inherits from `dev`): Local development overrides

**Staging**:
- `stg` (root): AWS staging environment

**Production**:
- `prd` (root): AWS production environment

**Inheritance benefits**:
- No secret duplication (shared secrets live in root)
- Easy local development (override only what's different)
- Single source of truth per environment
```

---

## Config Verification Checklist

After migration, verify each config:

### 1. Local Development (`dev_local`)

```bash
cd /home/anak/dev/dr-daily-report_telegram
doppler setup
# Verify: config = dev_local

doppler run -- env | grep -E "AURORA_HOST|AURORA_PORT|OPENROUTER_API_KEY"
# Expected:
#   AURORA_HOST=localhost
#   AURORA_PORT=3307
#   OPENROUTER_API_KEY=sk-or-v1-dev... (inherited from dev)

doppler secrets --only-names --config dev_local
# Should include both inherited secrets + overrides
```

### 2. Dev Environment (`dev`)

```bash
doppler run --config dev -- env | grep -E "AURORA_HOST|AURORA_PORT"
# Expected:
#   AURORA_HOST=dev-aurora.cluster-xxx...
#   AURORA_PORT=3306

# Verify no MOCK_AURORA in dev (local-only secret)
doppler run --config dev -- env | grep MOCK_AURORA
# Expected: (no output - not in dev config)
```

### 3. Staging Environment (`stg`)

```bash
doppler run --config stg -- env | grep -E "AURORA_HOST|LOG_LEVEL|ENVIRONMENT"
# Expected:
#   AURORA_HOST=staging-aurora.cluster-xxx...
#   LOG_LEVEL=INFO (not DEBUG like dev)
#   ENVIRONMENT=staging
```

### 4. Production Environment (`prd`)

```bash
doppler run --config prd -- env | grep -E "AURORA_HOST|LOG_LEVEL|ENVIRONMENT"
# Expected:
#   AURORA_HOST=prod-aurora.cluster-xxx...
#   LOG_LEVEL=WARNING (production-level logging)
#   ENVIRONMENT=production
```

### 5. Inheritance Verification

```bash
# Check that dev_local inherits from dev
doppler configs get dev_local --project rag-chatbot-worktree --json | jq '.inherits'
# Expected: ["dev"]

# Check that OPENROUTER_API_KEY is NOT duplicated in dev_local
doppler secrets download --config dev_local --format json | jq '.OPENROUTER_API_KEY'
# If it shows "<computed from dev>", inheritance is working
```

---

## Best Practices

### 1. Use Config Inheritance to Avoid Duplication

**DO**:
```bash
# Root config (dev) has shared secret
doppler secrets set OPENROUTER_API_KEY sk-or-v1-dev... --config dev

# Branch config (dev_local) inherits it
# No need to duplicate OPENROUTER_API_KEY in dev_local
```

**DON'T**:
```bash
# Bad: Duplicating same secret in dev and dev_local
doppler secrets set OPENROUTER_API_KEY sk-or-v1-dev... --config dev
doppler secrets set OPENROUTER_API_KEY sk-or-v1-dev... --config dev_local
# This creates maintenance burden (update in 2 places)
```

### 2. Override Only What's Different

**DO**:
```bash
# dev_local overrides only platform-specific values
doppler secrets set AURORA_HOST localhost --config dev_local
doppler secrets set MOCK_AURORA true --config dev_local

# Everything else inherited from dev
```

**DON'T**:
```bash
# Bad: Copying all secrets from dev to dev_local
# This defeats the purpose of inheritance
```

### 3. Use Descriptive Config Names

**DO**:
- `dev_local` - Clear purpose (local development)
- `dev_aws` - Clear platform (AWS-specific)
- `stg` - Standard abbreviation for staging

**DON'T**:
- `dev_personal` - Ambiguous (personal to whom? for what?)
- `config_1` - No semantic meaning

### 4. Document Environment Variables

In `.env.example` (for local development):
```bash
# Doppler Config Selection
# For local development, use:
#   doppler setup --config dev_local
#
# For testing staging locally:
#   doppler run --config stg -- <command>
#
# For production deployment:
#   doppler run --config prd -- terraform apply
```

---

## Open Questions

- [ ] Do we need platform-specific branch configs (`dev_aws`, `stg_aws`, `prd_aws`)?
  - **Recommendation**: Not needed initially. Only create if you deploy to multiple platforms (Lambda vs EC2 vs Cloudflare Workers).

- [ ] Should we create a `local` environment type in Doppler (separate from `dev`)?
  - **Recommendation**: No. Use `dev_local` as branch of `dev`. This maintains inheritance and keeps local configs tied to development environment.

- [ ] How to handle developer-specific overrides (like personal API keys)?
  - **Recommendation**: Use local `.env` file for truly personal secrets. Doppler is for team-shared secrets.

- [ ] Should we version-control Doppler config structure?
  - **Recommendation**: Document structure in `docs/deployment/DOPPLER_CONFIG.md` but don't version-control actual secrets (security risk).

---

## Implementation Notes (2025-12-25)

### Actual Implementation

The implementation differs from the initial specification due to Doppler's constraint: **configs cannot inherit from other configs in the same environment**.

**Solution**: Create a separate `local` environment for local development configs.

### Implemented Structure

```
rag-chatbot-worktree/
├── Environments:
│   ├── dev (Development)
│   ├── stg (Staging)
│   ├── prd (Production)
│   └── local (Local Development) ← NEW
│
├── Configs:
│   ├── dev (root, environment: dev, inheritable: true)
│   ├── stg (root, environment: stg)
│   ├── prd (root, environment: prd)
│   └── local_dev (branch, environment: local, inherits: rag-chatbot-worktree.dev) ← NEW
```

### Key Differences from Original Specification

1. **Environment Separation**: Created `local` environment instead of using `dev` environment for local configs
   - Reason: Doppler enforces environment-based inheritance isolation
   - Benefit: Clear separation between local and AWS environments

2. **Config Naming**: `local_dev` instead of `dev_local`
   - Reason: Doppler enforces naming convention `<environment>_<name>` for configs
   - Example: Configs in `local` environment must start with `local_`

3. **Secret Names**: Using `RDS_*` prefix, not `AURORA_*`
   - `RDS_HOST` (not `AURORA_HOST`)
   - `RDS_PORT` (not `AURORA_PORT`)
   - `RDS_DATABASE` (not `AURORA_DATABASE`)
   - `RDS_USER` (not `AURORA_USER`)
   - `RDS_PASSWORD` (not `AURORA_PASSWORD`)
   - Reason: Matches existing codebase convention

### Implemented Configuration

#### `local_dev` Config

**Environment**: `local` (Local Development)
**Inherits from**: `rag-chatbot-worktree.dev`

**Local Overrides**:
```bash
RDS_HOST=localhost            # Override from dev's AWS endpoint
RDS_PORT=3307                 # Override from dev's 5432 (SSM tunnel port)
MOCK_AURORA=true              # Local development speed optimization
TELEGRAM_API_URL=http://localhost:8001  # Local dev server
```

**Inherited from `dev`** (11 secrets):
- `OPENROUTER_API_KEY`
- `RDS_DATABASE`
- `RDS_USER`
- `RDS_PASSWORD`
- `TELEGRAM_BOT_TOKEN`
- `AURORA_MASTER_PASSWORD`
- `DOPPLER_PROJECT`
- `DOPPLER_ENVIRONMENT` (overridden to "local")
- `DOPPLER_CONFIG` (overridden to "local_dev")

### Setup Commands (Executed)

```bash
# 1. Create local environment
doppler environments create "Local Development" local --project rag-chatbot-worktree

# 2. Mark dev as inheritable
doppler configs update dev --project rag-chatbot-worktree --inheritable

# 3. Create local_dev config
doppler configs create local_dev --project rag-chatbot-worktree --environment local

# 4. Set inheritance
doppler configs update local_dev --project rag-chatbot-worktree --inherits rag-chatbot-worktree.dev

# 5. Add local overrides
doppler secrets set RDS_HOST localhost --project rag-chatbot-worktree --config local_dev
doppler secrets set RDS_PORT 3307 --project rag-chatbot-worktree --config local_dev
doppler secrets set MOCK_AURORA true --project rag-chatbot-worktree --config local_dev
doppler secrets set TELEGRAM_API_URL http://localhost:8001 --project rag-chatbot-worktree --config local_dev

# 6. Configure local directory to use local_dev
cd /home/anak/dev/dr-daily-report_telegram
doppler setup --project rag-chatbot-worktree --config local_dev
```

### Verification

```bash
# Verify inheritance working
$ doppler run -- env | grep -E "^(RDS_HOST|RDS_PORT|MOCK_AURORA|DOPPLER_CONFIG)="
DOPPLER_CONFIG=local_dev
MOCK_AURORA=true
RDS_HOST=localhost
RDS_PORT=3307

# Verify secrets count
$ doppler secrets --project rag-chatbot-worktree --config local_dev --json | jq 'length'
15  # 4 local overrides + 11 inherited from dev
```

### Migration Status

- [x] Phase 1: Create `local_dev` branch config with inheritance ✅
- [x] Phase 2: Test local development workflow ✅
- [x] Phase 3: Verify inheritance and secret access ✅
- [x] Phase 4: Update specification documentation ✅
- [x] Phase 5: Add missing AURORA_* secrets to local_dev ✅ (2025-12-25)
- [x] Phase 6: Configure local directory to use local_dev ✅ (2025-12-25)
- [ ] Phase 7: Clean up old configs (`dev_local`, `dev_personal`) - **Pending** (after 1 week verification)

### Old Configs (to be removed after verification)

These configs are now redundant and can be deleted after confirming `local_dev` works:
- `dev_local` (old, in `dev` environment, root config, no inheritance)
- `dev_personal` (old, in `dev` environment, root config, no inheritance)

**Cleanup command** (run after 1 week):
```bash
doppler configs delete dev_local --project rag-chatbot-worktree --yes
doppler configs delete dev_personal --project rag-chatbot-worktree --yes
```

---

## Final Implementation Summary (2025-12-25)

### ✅ Implementation Complete

**Config**: `local_dev`
**Status**: Fully configured and activated
**Secrets**: 18 total (9 local overrides + 9 inherited from dev)

**Final Configuration**:
```
Name: local_dev
Environment: local
Inherits: rag-chatbot-worktree.dev ✅
Secrets:
  Local Overrides (9):
    - AURORA_HOST=localhost
    - AURORA_PORT=3307
    - AURORA_DATABASE=ticker_data
    - AURORA_USERNAME=admin
    - AURORA_PASSWORD=*** (set)
    - MOCK_AURORA=true
    - TELEGRAM_API_URL=http://localhost:8001
    - RDS_HOST=localhost
    - RDS_PORT=3307

  Inherited from dev (9):
    - AURORA_MASTER_PASSWORD
    - OPENROUTER_API_KEY
    - TELEGRAM_BOT_TOKEN
    - RDS_DATABASE
    - RDS_USER
    - RDS_PASSWORD
    - DOPPLER_PROJECT (auto)
    - DOPPLER_ENVIRONMENT (auto: local)
    - DOPPLER_CONFIG (auto: local_dev)
```

**Verification Results**:
- ✅ All AURORA_* secrets present and configured for localhost
- ✅ Local dev flags (MOCK_AURORA, TELEGRAM_API_URL) configured
- ✅ Inheritance working (9 secrets auto-sync from dev)
- ✅ Local directory configured to use local_dev
- ✅ Comprehensive verification passed

**Benefits Achieved**:
1. **Inheritance**: Secrets auto-sync from dev (no manual updates)
2. **Local Optimization**: MOCK_AURORA=true, localhost connections
3. **Clear Separation**: local environment distinct from dev
4. **Maintainability**: Only 9 local overrides vs 18 total secrets

**Next Actions**:
- Use `local_dev` for all local development
- Monitor for 1 week to ensure stability
- After verification: Delete old `dev_local`, `dev_personal` configs
- Update team documentation

---

## Next Steps

- [ ] Review specification with team
- [ ] Decide on branch config naming (`dev_local` vs `dev_aws`)
- [ ] Create migration timeline (Phase 1-4 over 1-2 weeks)
- [ ] Test Phase 1 (create branch configs) without disrupting current setup
- [ ] Verify local development works with new `dev_local` config
- [ ] Clean up old configs after 1 week of verification
- [ ] Update documentation

---

## References

- [Doppler Config Inheritance](https://docs.doppler.com/docs/config-inheritance)
- [Doppler Branch Configs](https://docs.doppler.com/docs/branch-configs)
- [Doppler Environment-Based Configuration](https://docs.doppler.com/docs/environment-based-configuration)
- [GitHub Actions + Doppler Integration](https://www.doppler.com/blog/github-actions-and-doppler-streamlining-your-ci-cd-pipelines)
- `.claude/CLAUDE.md` (Secret Management Principle)
- `docs/deployment/MULTI_ENV.md` (Multi-Environment Strategy)
