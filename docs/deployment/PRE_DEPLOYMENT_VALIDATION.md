# Pre-Deployment Validation

**Purpose**: Prevent deployment failures caused by missing or empty secrets.

**Context**: After the 2026-01-09 LINE bot incident (see `.claude/bug-hunts/2026-01-09-linebot-no-response.md`), we implemented pre-deployment validation to catch configuration issues before they break production.

---

## Quick Start

**Before every Terraform apply**, run the validation script:

```bash
# Validate dev environment
./scripts/validate-doppler-secrets.sh dev

# Validate staging
./scripts/validate-doppler-secrets.sh stg

# Validate production
./scripts/validate-doppler-secrets.sh prd
```

**If validation passes** (exit code 0):
```
✅ All required secrets present and valid!
ℹ️  Safe to proceed with Terraform apply
```

**If validation fails** (exit code 1):
```
❌ Validation failed: 2 required secret(s) missing

Missing or empty secrets:
  - LINE_CHANNEL_ACCESS_TOKEN
  - LINE_CHANNEL_SECRET

Cannot proceed with Terraform apply
```

---

## Integration with Terraform Workflow

### Manual Deployment

```bash
# 1. Validate secrets FIRST
./scripts/validate-doppler-secrets.sh dev

# 2. If validation passes, proceed with Terraform
cd terraform
doppler run --config dev -- terraform plan -var-file=terraform.dev.tfvars
doppler run --config dev -- terraform apply -var-file=terraform.dev.tfvars -auto-approve
```

### CI/CD Integration (GitHub Actions)

Add validation step before Terraform apply:

```yaml
- name: Validate Doppler Secrets
  run: |
    ./scripts/validate-doppler-secrets.sh ${{ env.ENVIRONMENT }}
  env:
    DOPPLER_TOKEN: ${{ secrets.DOPPLER_TOKEN }}

- name: Terraform Apply
  if: success()  # Only run if validation passed
  run: |
    cd terraform
    doppler run --config ${{ env.ENVIRONMENT }} -- terraform apply -auto-approve
```

---

## What Gets Validated

### Required Secrets (Must Exist and Be Non-Empty)

| Secret Name | Description | Used By |
|-------------|-------------|---------|
| `OPENROUTER_API_KEY` | OpenRouter API key for LLM access | All Lambdas with LLM |
| `TF_VAR_OPENROUTER_API_KEY` | Terraform variable version | Terraform |
| `AURORA_MASTER_PASSWORD` | Aurora MySQL password | All Lambdas with database |
| `TF_VAR_AURORA_MASTER_PASSWORD` | Terraform variable version | Terraform |
| `LINE_CHANNEL_ACCESS_TOKEN` | LINE Bot access token | LINE bot Lambda |
| `TF_VAR_LINE_CHANNEL_ACCESS_TOKEN` | Terraform variable version | Terraform |
| `LINE_CHANNEL_SECRET` | LINE Bot channel secret | LINE bot Lambda |
| `TF_VAR_LINE_CHANNEL_SECRET` | Terraform variable version | Terraform |
| `telegram_bot_token` | Telegram bot token | Telegram Mini App |
| `telegram_app_id` | Telegram app ID | Telegram Mini App |
| `telegram_app_hash` | Telegram app hash | Telegram Mini App |

### Optional Secrets (Warning If Missing)

| Secret Name | Description | Impact If Missing |
|-------------|-------------|-------------------|
| `LANGFUSE_PUBLIC_KEY` | Langfuse observability | No tracing/monitoring |
| `LANGFUSE_SECRET_KEY` | Langfuse API secret | No tracing/monitoring |
| `LANGFUSE_HOST` | Langfuse host URL | No tracing/monitoring |

---

## Validation Layers

This validation is **Layer 1** of a multi-layer defense strategy:

### Layer 1: Pre-Deployment Script Validation ✅ (This)
- **When**: Before Terraform apply
- **What**: Checks Doppler config has all required secrets
- **Catches**: Missing secrets before deployment
- **Exit code**: Non-zero prevents deployment

### Layer 2: Terraform Variable Validation ✅
- **When**: During Terraform plan/apply
- **What**: Terraform validates variable constraints
- **Catches**: Empty strings, invalid values
- **Example**:
  ```hcl
  variable "LINE_CHANNEL_ACCESS_TOKEN" {
    validation {
      condition     = length(var.LINE_CHANNEL_ACCESS_TOKEN) > 0
      error_message = "LINE_CHANNEL_ACCESS_TOKEN must not be empty."
    }
  }
  ```

### Layer 3: Application Startup Validation (Existing)
- **When**: Lambda cold start
- **What**: Application code checks required env vars
- **Catches**: Missing env vars at runtime
- **Example** (Python):
  ```python
  required_vars = ["LINE_CHANNEL_ACCESS_TOKEN", "LINE_CHANNEL_SECRET"]
  missing = [v for v in required_vars if not os.getenv(v)]
  if missing:
      raise ValueError(f"Missing env vars: {missing}")
  ```

---

## How to Fix Missing Secrets

### Option 1: Copy from Another Environment

```bash
# Copy LINE credentials from staging to dev
TOKEN=$(doppler secrets get LINE_CHANNEL_ACCESS_TOKEN --config stg --plain)
SECRET=$(doppler secrets get LINE_CHANNEL_SECRET --config stg --plain)

doppler secrets set LINE_CHANNEL_ACCESS_TOKEN="$TOKEN" --config dev
doppler secrets set LINE_CHANNEL_SECRET="$SECRET" --config dev
doppler secrets set TF_VAR_LINE_CHANNEL_ACCESS_TOKEN="$TOKEN" --config dev
doppler secrets set TF_VAR_LINE_CHANNEL_SECRET="$SECRET" --config dev
```

### Option 2: Set New Value

```bash
# Set a new secret value
doppler secrets set LINE_CHANNEL_ACCESS_TOKEN='your-token-here' --config dev
doppler secrets set TF_VAR_LINE_CHANNEL_ACCESS_TOKEN='your-token-here' --config dev
```

### Option 3: Import from File

```bash
# Import from .env file (if you have one)
doppler import .env --config dev
```

---

## Troubleshooting

### Validation Script Not Found

```bash
❌ bash: ./scripts/validate-doppler-secrets.sh: No such file or directory
```

**Solution**: Make sure you're in the project root:
```bash
cd /path/to/dr-daily-report_telegram
chmod +x scripts/validate-doppler-secrets.sh
./scripts/validate-doppler-secrets.sh dev
```

### Doppler CLI Not Installed

```bash
❌ ERROR: Doppler CLI is not installed
```

**Solution**: Install Doppler CLI:
```bash
# macOS
brew install dopplerhq/cli/doppler

# Linux
curl -Ls https://cli.doppler.com/install.sh | sh
```

### Config Not Found

```bash
❌ ERROR: Doppler config 'dev' not found
```

**Solution**: Check available configs:
```bash
doppler configs
```

Then use the correct config name.

### Secret Exists But Validation Fails

```bash
❌ LINE_CHANNEL_ACCESS_TOKEN - MISSING or EMPTY
```

But `doppler secrets` shows it exists?

**Possible causes**:
1. **Value is empty string**: Check with `doppler secrets get LINE_CHANNEL_ACCESS_TOKEN --config dev --plain`
2. **Wrong config**: Make sure you're checking the right environment
3. **Permissions**: Ensure you have read access to the config

---

## Related Documentation

- **Incident Report**: `.claude/bug-hunts/2026-01-09-linebot-no-response.md`
- **Principle #15**: Infrastructure-Application Contract (`docs/guides/infrastructure-application-contract.md`)
- **Principle #13**: Secret Management Discipline (`docs/deployment/DOPPLER_CONFIG.md`)
- **Deployment Guide**: `docs/deployment/DEPLOYMENT.md`

---

## Script Source

**Location**: `scripts/validate-doppler-secrets.sh`

**Exit Codes**:
- `0` - All required secrets present and valid
- `1` - Missing or empty secrets detected
- `2` - Invalid arguments or configuration

**Usage**:
```bash
./scripts/validate-doppler-secrets.sh <environment>
```

**Example Output** (Success):
```
ℹ️  Validating Doppler secrets for environment: dev
ℹ️  Doppler config: dev

ℹ️  Checking required secrets...
✅ OPENROUTER_API_KEY - Present
✅ LINE_CHANNEL_ACCESS_TOKEN - Present
✅ LINE_CHANNEL_SECRET - Present
✅ telegram_bot_token - Present
✅ telegram_app_id - Present
✅ telegram_app_hash - Present

ℹ️  Checking Terraform-specific secrets (TF_VAR_*)...
✅ TF_VAR_OPENROUTER_API_KEY - Present
✅ TF_VAR_AURORA_MASTER_PASSWORD - Present
✅ TF_VAR_LINE_CHANNEL_ACCESS_TOKEN - Present
✅ TF_VAR_LINE_CHANNEL_SECRET - Present

ℹ️  Checking optional secrets...
✅ LANGFUSE_PUBLIC_KEY - Present
✅ LANGFUSE_SECRET_KEY - Present
✅ LANGFUSE_HOST - Present

================================================================
✅ All required secrets present and valid!

ℹ️  Safe to proceed with Terraform apply
```

**Example Output** (Failure):
```
ℹ️  Validating Doppler secrets for environment: dev
ℹ️  Doppler config: dev

ℹ️  Checking required secrets...
✅ OPENROUTER_API_KEY - Present
❌ LINE_CHANNEL_ACCESS_TOKEN - MISSING or EMPTY
❌   Description: LINE Bot channel access token
❌ LINE_CHANNEL_SECRET - MISSING or EMPTY
❌   Description: LINE Bot channel secret

================================================================
❌ Validation failed: 2 required secret(s) missing

Missing or empty secrets:
  - LINE_CHANNEL_ACCESS_TOKEN
  - LINE_CHANNEL_SECRET

❌ Cannot proceed with Terraform apply
ℹ️  Add missing secrets with: doppler secrets set <SECRET_NAME>='<value>' --config dev
```

---

## Prevention Checklist

Before every deployment, ensure:

- [ ] Run `./scripts/validate-doppler-secrets.sh <env>` and verify exit code 0
- [ ] All required secrets present in Doppler config
- [ ] Terraform variable validations pass
- [ ] Application code has startup validation (defensive programming)
- [ ] Post-deployment smoke test planned

This multi-layer approach (script + Terraform + application) ensures configuration issues are caught early and never reach production.
