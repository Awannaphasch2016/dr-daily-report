---
title: Configurable Beta User Limit
focus: general
date: 2026-01-17
status: draft
tags: [line-bot, beta, configuration]
---

# Specification: Configurable Beta User Limit

## Goal

**What problem does this solve?**

Allow the operator to easily adjust the beta user limit (N) as the LINE Bot gains stability, without requiring code changes or redeployment.

**Current state**:
- `BETA_USER_LIMIT = 20` is hardcoded in `src/integrations/line_bot.py`
- Changing requires code change + deployment

**Desired state**:
- Limit configurable via environment variable
- Can adjust limit without code change
- S3 state also stores the limit for visibility

---

## Design Options

### Option A: Environment Variable Only (Recommended)

**Mechanism**: Read limit from `BETA_USER_LIMIT` env var

```python
# Current (hardcoded)
BETA_USER_LIMIT = 20

# New (configurable)
BETA_USER_LIMIT = int(os.getenv("BETA_USER_LIMIT", "20"))
```

**Pros**:
- Simplest change (1 line)
- Follows Principle #23 (Configuration Variation Axis: environment-specific → env var)
- Consistent with other config patterns in codebase
- Change via Terraform → Lambda env vars → deploy

**Cons**:
- Requires Lambda update to change (not instant)
- Must redeploy to apply new limit

**How to adjust limit**:
1. Update `terraform/main.tf` → `BETA_USER_LIMIT` env var
2. `terraform apply` (or merge to dev branch)
3. Lambda picks up new value on next cold start

---

### Option B: S3 Configuration File

**Mechanism**: Store limit in S3 alongside user list

```json
// beta-users.json (updated structure)
{
  "limit": 20,
  "users": ["U_user1", "U_user2", ...]
}
```

**Pros**:
- Change limit instantly (no redeploy)
- Limit and users in same place (visibility)

**Cons**:
- More complex code changes
- S3 read on every request (or cache with TTL)
- Over-engineering for this use case

---

### Option C: Hybrid (Env var default, S3 override)

**Mechanism**:
- Default from env var
- S3 can override if `limit` field present

**Pros**:
- Best of both worlds
- Instant override possible

**Cons**:
- Most complex
- Confusing which value is in effect

---

## Recommendation: Option A (Environment Variable)

**Rationale**:
1. **Simplicity**: 1-line code change
2. **Consistency**: Follows existing config patterns
3. **Deployment frequency**: You're already deploying frequently
4. **Audit trail**: Terraform tracks changes

---

## Implementation Spec (Option A)

### Code Change

**File**: `src/integrations/line_bot.py:19-21`

```python
# Before
BETA_USER_LIMIT = 20
BETA_USERS_S3_KEY = "beta-users.json"

# After
BETA_USER_LIMIT = int(os.getenv("BETA_USER_LIMIT", "0"))  # 0 = unlimited
BETA_USERS_S3_KEY = "beta-users.json"
```

**Behavior**:
- `BETA_USER_LIMIT=0` → No limit (unlimited users)
- `BETA_USER_LIMIT=20` → First 20 users only
- `BETA_USER_LIMIT=50` → First 50 users only
- Not set → Default to 0 (unlimited) or 20 (your choice)

### Logic Change

**File**: `src/integrations/line_bot.py` → `_try_add_beta_user()`

```python
def _try_add_beta_user(self, user_id: str) -> bool:
    """Try to add user to beta. Returns True if added/exists, False if full."""
    if not self.beta_enabled:
        return True  # Beta management disabled = allow all
    if user_id in self.beta_users:
        return True  # Already a beta user

    # Check limit (0 = unlimited)
    if BETA_USER_LIMIT > 0 and len(self.beta_users) >= BETA_USER_LIMIT:
        logger.info(f"❌ Beta full ({len(self.beta_users)}/{BETA_USER_LIMIT}), rejecting: {user_id[:10]}...")
        return False

    self.beta_users.add(user_id)
    self._save_beta_users()
    limit_str = f"/{BETA_USER_LIMIT}" if BETA_USER_LIMIT > 0 else " (unlimited)"
    logger.info(f"✅ Beta user added: {user_id[:10]}... ({len(self.beta_users)}{limit_str})")
    return True
```

### Terraform Change

**File**: `terraform/main.tf` → LINE Bot Lambda environment

```hcl
environment {
  variables = {
    # ... existing vars ...
    BETA_USER_LIMIT = var.beta_user_limit  # New
  }
}
```

**File**: `terraform/variables.tf`

```hcl
variable "beta_user_limit" {
  description = "Maximum number of beta users for LINE Bot (0 = unlimited)"
  type        = number
  default     = 20
}
```

**File**: `terraform/terraform.dev.tfvars`

```hcl
beta_user_limit = 20  # Start with 20, increase as needed
```

---

## Operational Workflow

### To increase limit from 20 to 50:

```bash
# Option 1: Via Terraform (recommended)
# 1. Edit terraform/terraform.dev.tfvars
beta_user_limit = 50

# 2. Apply
cd terraform && terraform apply -var-file=terraform.dev.tfvars

# Option 2: Via AWS Console (quick test)
# 1. Go to Lambda → dr-daily-report-line-bot-dev → Configuration → Environment
# 2. Edit BETA_USER_LIMIT → 50
# 3. Save (triggers new deployment)
```

### To remove limit entirely:

```hcl
beta_user_limit = 0  # 0 = unlimited
```

---

## Migration: Seed Existing Users (Optional)

If you want to count existing users toward the limit, you need to seed them:

### Get Existing Users from LINE

```bash
# LINE doesn't provide "list all followers" API
# Options:
# 1. Check LINE Official Account Manager web UI
# 2. Query from your own database (if you logged user IDs before)
# 3. Accept that existing users are "grandfathered"
```

### Seed Users Manually

```bash
# Download current beta-users.json
aws s3 cp s3://line-bot-pdf-reports-755283537543/beta-users.json /tmp/beta-users.json

# Edit to add existing user IDs
cat /tmp/beta-users.json
# {"users": ["U_test_beta_user_1"]}

# Add known users
cat > /tmp/beta-users.json <<'EOF'
{
  "users": [
    "U_existing_user_1",
    "U_existing_user_2",
    "U_test_beta_user_1"
  ]
}
EOF

# Upload
aws s3 cp /tmp/beta-users.json s3://line-bot-pdf-reports-755283537543/beta-users.json
```

---

## Open Questions

- [x] **Default when not set**: 0 (unlimited) or 20 (safe default)?
  - **Decision needed**: What's safer for your use case?

- [ ] **Grandfathered users**: Accept existing users aren't counted, or seed them?

---

## Summary

| Aspect | Specification |
|--------|---------------|
| **Approach** | Option A: Environment variable |
| **Config var** | `BETA_USER_LIMIT` |
| **Default** | TBD (0 or 20) |
| **Behavior** | 0 = unlimited, N = limit to N users |
| **Change method** | Terraform → deploy |
| **Code changes** | 2 files: line_bot.py, variables.tf |

---

## Next Steps

- [ ] Decide default value (0 or 20)
- [ ] Decide if seeding existing users is needed
- [ ] If ready, implement with `/step`
