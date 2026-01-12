# Configuration Variation Axis Guide

**Principle #23** | Choose configuration mechanism based on WHAT varies and WHEN it varies.

---

## Overview

### Core Problem
Ad-hoc decisions about configuration mechanisms (env vars vs constants vs config files) lead to inconsistency, duplication, and environment contamination.

### Key Insight
Configuration has a "variation axis"—understanding WHAT varies (secret, environment, deployment, structure) determines WHERE it belongs (Doppler, CI/CD, code, JSON).

---

## Decision Heuristic

### Quick Reference Table

| Varies By | Mechanism | Location | Examples |
|-----------|-----------|----------|----------|
| Per environment | Doppler → env var | `os.environ.get()` | `AURORA_HOST`, `LANGFUSE_TRACING_ENVIRONMENT` |
| Secret (any env) | Doppler → env var | `os.environ.get()` | API keys, passwords, tokens |
| Per deployment | CI/CD → env var | GitHub Actions | `LANGFUSE_RELEASE` (commit-specific) |
| Never | Python constant | Domain modules | Table names, score names |
| Complex structure | JSON file | `config/*.json` | Tag taxonomies, prompt templates |

### Decision Tree

```
Is it a secret?
  └─ YES → Doppler (regardless of sensitivity level)
  └─ NO ↓
     Does it differ by environment (local/dev/stg/prd)?
       └─ YES → Doppler
       └─ NO ↓
          Does it change per deployment (commit SHA, version)?
            └─ YES → CI/CD direct update
            └─ NO ↓
               Is it a complex nested structure?
                 └─ YES → JSON file
                 └─ NO → Python constant
```

---

## Doppler as Environment Isolation Container

### Philosophy

Doppler holds ALL environment-specific configuration, not just secrets. Each environment (local/dev/stg/prd) is an isolated container with its complete configuration set.

```
┌─────────────────────────────────────────────────────────────┐
│                    Doppler Organization                     │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  local_dev (isolated)     dev (isolated)                    │
│  ├─ AURORA_HOST=localhost ├─ AURORA_HOST=dev.aurora.aws     │
│  ├─ OPENROUTER_KEY=xxx    ├─ OPENROUTER_KEY=xxx             │
│  └─ TZ=Asia/Bangkok       └─ TZ=Asia/Bangkok                │
│                                                             │
│  stg (isolated)           prd (isolated)                    │
│  ├─ AURORA_HOST=stg.aws   ├─ AURORA_HOST=prd.aws            │
│  ├─ OPENROUTER_KEY=xxx    ├─ OPENROUTER_KEY=xxx             │
│  └─ TZ=Asia/Bangkok       └─ TZ=Asia/Bangkok                │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Benefits

1. **Environment isolation**: No cross-environment contamination
2. **Single source of truth**: All env config in one place
3. **Inheritance**: Reduce duplication via config inheritance
4. **Audit trail**: Doppler tracks who changed what

---

## Configuration Flow Patterns

### Pattern 1: Doppler → Lambda (via Terraform)

```
Doppler (dev)                    Terraform                    Lambda
├─ AURORA_HOST          →        environment {               →  os.environ.get("AURORA_HOST")
├─ OPENROUTER_KEY       →          AURORA_HOST = var.xxx     →  os.environ.get("OPENROUTER_KEY")
└─ TF_VAR_xxx (prefix)  →        }                           →
```

**Doppler secrets with `TF_VAR_` prefix** are automatically passed to Terraform variables.

### Pattern 2: CI/CD → Lambda (direct update)

```
GitHub Actions                   Lambda
├─ LANGFUSE_RELEASE      →       os.environ.get("LANGFUSE_RELEASE")
│   (computed: env-branch-sha)
└─ Computed at deploy time
```

For deployment-specific values that change every commit but aren't environment secrets.

### Pattern 3: Python Constants (code)

```python
# src/data/aurora/table_names.py
DAILY_PRICES = "daily_prices"
TICKER_MASTER = "ticker_master"

# src/scoring/score_names.py
FAITHFULNESS = "faithfulness"
COMPLETENESS = "completeness"
```

For values that are identical across ALL environments and deployments.

### Pattern 4: JSON Files (complex structures)

```json
// config/tag_taxonomy.json
{
  "categories": {
    "tech": ["AI", "Cloud", "Security"],
    "finance": ["Banking", "Insurance", "Investment"]
  }
}
```

For complex nested structures that would be unwieldy as env vars or constants.

---

## One-Path Execution Pattern

### Problem
Reading env vars on every request causes non-deterministic behavior if env changes mid-execution.

### Solution
Read values ONCE at startup (singleton pattern):

```python
# CORRECT: Read once at module load
from functools import lru_cache

@lru_cache(maxsize=1)
def get_config():
    return {
        "aurora_host": os.environ.get("AURORA_HOST"),
        "tz": os.environ.get("TZ"),
    }

# Usage
config = get_config()
host = config["aurora_host"]  # Always same value
```

```python
# WRONG: Read on every call
def get_aurora_host():
    return os.environ.get("AURORA_HOST")  # Could change mid-execution
```

---

## Startup Validation

### Pattern

Validate ALL required env vars at Lambda startup:

```python
# src/config.py
import os

REQUIRED_ENV_VARS = [
    "AURORA_HOST",
    "AURORA_PORT",
    "TZ",
    "OPENROUTER_API_KEY",
]

def validate_config():
    """Fail fast if required config missing."""
    missing = [var for var in REQUIRED_ENV_VARS if not os.environ.get(var)]
    if missing:
        raise RuntimeError(f"Missing required env vars: {missing}")

# Call at module load (Lambda cold start)
validate_config()
```

### Anti-Pattern

```python
# WRONG: Silent default hides missing config
tz = os.environ.get("TZ", "UTC")  # Silently uses UTC if TZ missing
```

---

## Common Configuration Types

### Secrets (Always Doppler)

```
AURORA_PASSWORD
OPENROUTER_API_KEY
LINE_CHANNEL_SECRET
TELEGRAM_BOT_TOKEN
LANGFUSE_SECRET_KEY
```

### Environment-Specific (Doppler)

```
AURORA_HOST           # localhost vs dev.aurora.aws vs prd.aurora.aws
AURORA_PORT           # 3306 (direct) vs 3307 (tunnel)
LANGFUSE_PUBLIC_KEY   # Different per environment
LANGFUSE_TRACING_ENVIRONMENT  # local/dev/stg/prd
```

### Deployment-Specific (CI/CD)

```
LANGFUSE_RELEASE      # dev-dev-abc1234 (computed at deploy time)
DEPLOYED_AT           # ISO timestamp of deployment
COMMIT_SHA            # Full commit hash
```

### Constants (Code)

```python
# Table names
DAILY_PRICES = "daily_prices"

# Score names
FAITHFULNESS = "faithfulness"

# Trace names
REPORT_GENERATION = "report_generation"

# API paths
HEALTH_CHECK = "/health"
```

### Complex Structures (JSON)

```json
// Prompt templates
{
  "system_prompt": "You are...",
  "user_template": "Analyze {symbol}..."
}

// Tag taxonomies
{
  "categories": { ... }
}
```

---

## Anti-Patterns

### 1. Hardcoding Secrets

```python
# WRONG: Security risk
OPENROUTER_KEY = "sk-or-v1-xxx..."

# CORRECT: From environment
OPENROUTER_KEY = os.environ.get("OPENROUTER_API_KEY")
```

### 2. Duplicating Config Across Environments

```
# WRONG: Same secret in multiple Doppler configs
dev:  OPENROUTER_KEY=xxx
stg:  OPENROUTER_KEY=xxx  # Duplicated!
prd:  OPENROUTER_KEY=xxx  # Duplicated!

# CORRECT: Use inheritance or shared config
```

### 3. Using tfvars for Doppler-Managed Values

```hcl
# WRONG: Duplicates what Doppler has
variable "aurora_host" {
  default = "dev.aurora.aws"  # Already in Doppler!
}

# CORRECT: Pass through from Doppler via TF_VAR_ prefix
```

### 4. JSON for Simple Key-Value

```json
// WRONG: Overkill
{
  "table_name": "daily_prices"
}

// CORRECT: Python constant
DAILY_PRICES = "daily_prices"
```

### 5. Scattered Constants

```python
# WRONG: Constants in multiple files
# src/api/routes.py
TABLE = "daily_prices"

# src/data/queries.py
TABLE = "daily_prices"  # Duplicated!

# CORRECT: Centralized
# src/data/aurora/table_names.py
DAILY_PRICES = "daily_prices"
```

### 6. Reading Env Vars Per Request

```python
# WRONG: Non-deterministic
def handle_request():
    host = os.environ.get("AURORA_HOST")  # Could change!
    ...

# CORRECT: Read once at startup
CONFIG = {"host": os.environ.get("AURORA_HOST")}

def handle_request():
    host = CONFIG["host"]  # Always consistent
```

---

## Migration Checklist

When adding new configuration:

1. **Classify the variation axis**
   - [ ] Secret? → Doppler
   - [ ] Environment-specific? → Doppler
   - [ ] Deployment-specific? → CI/CD
   - [ ] Complex structure? → JSON
   - [ ] Static? → Python constant

2. **Add to appropriate location**
   - [ ] Doppler: Add to ALL relevant environment configs
   - [ ] CI/CD: Add to workflow file
   - [ ] Code: Add to centralized module
   - [ ] JSON: Add to config/ directory

3. **Update validation**
   - [ ] Add to `REQUIRED_ENV_VARS` if required
   - [ ] Add startup validation if critical

4. **Document**
   - [ ] Update relevant guide if new pattern
   - [ ] Add to environment setup docs

---

## Integration with Principles

| Principle | Integration |
|-----------|-------------|
| #1 Defensive Programming | Startup validation (fail-fast) |
| #13 Secret Management | Doppler for all secrets |
| #14 Table Names | Constants for static values |
| #15 Infrastructure Contract | Env vars as contract between infra and code |

---

## See Also

- [CLAUDE.md Principle #23](../../.claude/CLAUDE.md) - Core principle
- [Doppler Config Guide](../deployment/DOPPLER_CONFIG.md) - Secret management setup
- [Infrastructure-Application Contract Guide](infrastructure-application-contract.md) - Deployment order

---

*Guide version: 2026-01-12*
*Principle: #23 Configuration Variation Axis*
*Status: Active - extracted from CLAUDE.md for right abstraction level*
