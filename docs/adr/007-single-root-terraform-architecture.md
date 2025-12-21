# ADR-007: Single Root Terraform Architecture

**Status:** ✅ Accepted
**Date:** 2024-12 (Cleanup completed)
**Deciders:** Development Team

## Context

Infrastructure as Code (IaC) can be organized in various ways: monolithic single state, layered architecture (data/platform/apps), or workspace-based separation.

### Historical Background

A layered terraform architecture was initially planned:
- `01-data/` (Aurora, DynamoDB)
- `02-platform/` (VPC, networking)
- `03-apps/` (Lambdas, API Gateway)

However, these layers were never fully implemented. The directories existed with terraform code but never managed actual resources (no S3 state files were created). All resources were created and managed by root terraform from the start.

### Dec 2024 Cleanup

After confirming no S3 state files existed for layer directories, removed unused layer structure:
- Deleted `01-data/`, `02-platform/`, `03-apps/` directories
- Removed ~2GB of `.terraform` cache
- Kept `00-bootstrap/` (special case - manages state infrastructure itself)

## Decision

Use single root terraform configuration managing all infrastructure in one state file.

### Current Structure

```
terraform/
├── main.tf              # LINE bot Lambda
├── telegram_api.tf      # Telegram Lambda
├── ecr.tf               # ECR repositories
├── dynamodb.tf          # DynamoDB tables
├── aurora.tf            # Aurora database
├── frontend.tf          # CloudFront distributions
└── layers/
    └── 00-bootstrap/    # State bucket, DynamoDB locks (local state)
```

### Why Keep 00-Bootstrap Layer

Bootstrap layer uses LOCAL state (`terraform.tfstate` in its directory) to manage the S3 bucket and DynamoDB table that root terraform uses for remote state. This is the chicken-and-egg infrastructure - can't use remote state that doesn't exist yet.

## Consequences

### Positive

- ✅ **Simplicity**: Single terraform state, single apply/plan
- ✅ **No Cross-Layer Complexity**: All resources in same state, direct references
- ✅ **Faster Development**: No need to coordinate layer dependencies
- ✅ **Sufficient Scale**: ~100 resources manageable in single state
- ✅ **Easy Refactoring**: Move resources between files without state migration

### Negative

- ❌ **Blast Radius**: Failed apply affects entire infrastructure
- ❌ **State Lock Contention**: Single lock for all changes (rare issue)
- ❌ **No Partial Deploys**: Can't deploy data layer independently of apps

### Neutral

- Same backend configuration for all resources
- All team members must coordinate on terraform operations

## Alternatives Considered

### Alternative 1: Layered Architecture (01-data, 02-platform, 03-apps)

**Example:**
```
terraform/
├── 01-data/           # Aurora, DynamoDB
├── 02-platform/       # VPC, networking
└── 03-apps/           # Lambdas, API Gateway
```

**Why Rejected:**
- Adds coordination complexity between layers
- Requires data source references between layers
- Overkill for ~100 resources
- Layer directories existed but were never actually used

### Alternative 2: Terraform Workspaces

**Why Rejected:**
- Workspaces are for environments (dev/staging/prod), not logical separation
- All workspaces share same code (can't have different resource definitions)
- Not suitable for organizing infrastructure by concern

### Alternative 3: Multiple Terraform Roots

**Example:**
```
infra-data/        # Separate repo/directory
infra-platform/    # Separate repo/directory
infra-apps/        # Separate repo/directory
```

**Why Rejected:**
- Massive overhead for team size (single developer)
- Difficult to coordinate changes across repos
- State dependencies become external contracts

## References

- **Root Terraform**: `terraform/*.tf`
- **Bootstrap Layer**: `terraform/layers/00-bootstrap/`
- **Cleanup Commit**: Dec 2024 - Removed unused layer directories

## Decision Drivers

1. **Project Scale**: ~100 resources don't require layering complexity
2. **Team Size**: Single developer doesn't need coordination overhead
3. **Historical Reality**: Layers were never actually used (no state files)
4. **Simplicity**: YAGNI principle - don't build structure until needed

## Why Import Blocks Over CLI Imports

When importing existing infrastructure, use Terraform 1.5+ import blocks instead of CLI:

```hcl
# ✅ GOOD: Import blocks (version-controlled, reviewable)
import {
  to = aws_lambda_function.telegram_api
  id = "telegram-api-ticker-report"
}

# ❌ BAD: CLI imports (ephemeral, not tracked in git)
# terraform import aws_lambda_function.telegram_api telegram-api-ticker-report
```

**Rationale:**
- Import blocks are committed to git (visible in PRs)
- Can review imports before applying
- Self-documenting (shows what was imported and when)
- Idempotent (safe to re-run)

## State Lock Contention Pattern

**Historical Context:** Migrated from considering layered approach after realizing single state file doesn't cause contention issues with team of one developer.

**If team grows:**
- Consider splitting at natural boundaries (data vs apps)
- Use backend locking to prevent concurrent modifications
- Monitor state file size (becomes slow > 1000 resources)
