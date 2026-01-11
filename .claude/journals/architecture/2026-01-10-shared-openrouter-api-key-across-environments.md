---
title: Shared OpenRouter API Key Across Environments
category: architecture
date: 2026-01-10
status: decided
related_adrs: []
tags: [secrets, doppler, openrouter, multi-env]
---

# Shared OpenRouter API Key Across Environments

## Context

**What problem are we solving?**

Staging environment report generation failing with 401 error because `OPENROUTER_API_KEY` is not configured in the `stg` Doppler config.

**Constraints**:
- OpenRouter bills per API call, not per key
- No need for environment-specific rate limits
- Simplicity preferred over isolation

## Options Considered

### Option 1: Separate API Keys Per Environment
**Pros**:
- Environment isolation (dev mistakes don't affect prod billing)
- Easier to revoke single environment

**Cons**:
- More keys to manage
- No practical benefit for this use case
- Extra complexity

### Option 2: Shared API Key Across All Environments
**Pros**:
- Single key to manage
- Automatic inheritance via Doppler config hierarchy
- Consistent behavior across environments

**Cons**:
- No billing isolation per environment
- Revoking key affects all environments

## Decision

**Shared API Key**: Use the same `OPENROUTER_API_KEY` for dev, staging, and prod.

**Why?**
- OpenRouter tracks usage per account, not per key
- Simplicity > theoretical isolation benefits
- Doppler inheritance makes this automatic (`stg` inherits from `dev`)

## Implementation

Doppler config setup:
```
dev (root)           → OPENROUTER_API_KEY = sk-or-...
  └── local_dev      → (inherits)
stg (root)           → OPENROUTER_API_KEY = sk-or-...  (same key)
prd (root)           → OPENROUTER_API_KEY = sk-or-...  (same key)
```

**Note**: `stg` and `prd` are root configs (not branches), so they need the key set explicitly.

## Action Items

- [x] Confirm OPENROUTER_API_KEY exists in `dev` config
- [ ] Set same key in `stg` config: `doppler secrets set OPENROUTER_API_KEY --config stg`
- [ ] Set same key in `prd` config: `doppler secrets set OPENROUTER_API_KEY --config prd`
- [ ] Verify staging report generation works

## Consequences

**Positive**:
- Staging will work immediately after key is set
- Simple secret management

**Negative**:
- Cannot isolate billing per environment (acceptable)
