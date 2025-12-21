# ADR-008: Directory Structure Over Terraform Workspaces

**Status:** ✅ Accepted
**Date:** 2024-01
**Deciders:** Development Team

## Context

Terraform supports multiple environments through two primary mechanisms:
1. **Workspaces**: `terraform workspace select prod`
2. **Directory Structure**: `envs/dev/`, `envs/staging/`, `envs/prod/`

Both approaches aim to manage multiple environments (dev, staging, prod) with the same infrastructure code but different state and variable values.

### Requirements

- Prevent accidental destruction of production
- Enable different configurations per environment (instance sizes, retention policies)
- Support environment-specific code review workflows
- Isolate state between environments

## Decision

Use environment directories (`envs/dev/`, `envs/staging/`, `envs/prod/`) instead of Terraform workspaces.

### Directory Structure

```
terraform/
├── modules/               # Shared modules
│   ├── telegram-api/
│   ├── line-bot/
│   └── data-lake/
└── envs/
    ├── dev/
    │   ├── main.tf
    │   ├── variables.tf
    │   └── backend.tf     # S3 key: terraform/dev/state
    ├── staging/
    │   ├── main.tf
    │   ├── variables.tf
    │   └── backend.tf     # S3 key: terraform/staging/state
    └── prod/
        ├── main.tf
        ├── variables.tf
        └── backend.tf     # S3 key: terraform/prod/state
```

### Usage Pattern

```bash
# Development
cd terraform/envs/dev
terraform plan
terraform apply

# Production (different directory - impossible to confuse)
cd terraform/envs/prod
terraform plan
terraform apply
```

## Consequences

### Positive

- ✅ **Safety**: Can't accidentally `terraform destroy` prod from dev terminal
- ✅ **Code Review**: prod changes get separate PRs with different reviewers
- ✅ **Flexibility**: Each env can have different resource sizes, retention policies
- ✅ **State Isolation**: Separate S3 keys prevent cross-env state corruption
- ✅ **Explicit Context**: Always visible which env you're operating in (`pwd` shows it)
- ✅ **Environment-Specific Config**: Can add prod-only resources without affecting dev

### Negative

- ❌ **More Files**: 3x directory duplication (one per environment)
- ❌ **Module Updates**: Must update all envs when changing shared modules
- ❌ **DRY Violation**: Some duplication between env configs (mitigated by modules)

### Mitigation

- Use shared modules in `terraform/modules/` for common infrastructure
- Module updates propagate to all environments automatically
- Environment-specific variables kept in `variables.tf` per env

## Alternatives Considered

### Alternative 1: Terraform Workspaces

**Example:**
```bash
terraform workspace select dev
terraform apply

terraform workspace select prod
terraform apply  # Easy to run in wrong workspace!
```

**Comparison Table:**

| Workspaces | Directory Structure |
|------------|---------------------|
| `terraform workspace select prod` accidents | Explicit `cd envs/prod` |
| Same backend, easy cross-contamination | Separate backends per env |
| Can't require PR for prod only | Different directories = different PRs |
| Must share provider versions | Can differ per env |
| Good for: ephemeral/identical envs | Good for: long-lived envs with different configs |

**Why Rejected:**
- Easy to accidentally operate on wrong workspace
- All workspaces share same backend configuration
- Can't enforce different approval workflows per environment
- Workspace state is less visible than directory structure

### Alternative 2: Separate Repositories Per Environment

**Why Rejected:**
- Massive overhead: 3 repos to maintain
- Module sharing becomes difficult
- Can't see cross-env changes in single PR
- Overkill for project scale

### Alternative 3: Branch-Based Environments

**Example:**
```bash
git checkout dev
terraform apply

git checkout prod
terraform apply
```

**Why Rejected:**
- Git branches are for code versions, not environment separation
- Merging becomes nightmare (dev changes auto-merge to prod)
- Can't have environment-specific files
- Confuses version control with infrastructure separation

## References

- **Environment Configs**: `terraform/envs/{dev,staging,prod}/`
- **Shared Modules**: `terraform/modules/`
- **Backend Configuration**: Each env has separate S3 state key

## Decision Drivers

1. **Safety**: Prevent accidental prod destruction (workspace accidents in other projects)
2. **Visibility**: Always clear which environment you're operating in
3. **Flexibility**: Different instance sizes, retention policies per env
4. **Code Review**: Prod changes require separate PR with stricter review

## Historical Context

Chose directories after evaluating workspace accidents in other projects where `terraform destroy` in wrong workspace deleted production resources. The extra files are acceptable cost for the safety guarantee.

## Production-Only Resources Pattern

With directory structure, can add prod-only resources without affecting dev:

```hcl
# terraform/envs/prod/main.tf only
module "backup" {
  source = "../../modules/backup"
  # Only exists in prod
}

# terraform/envs/dev/main.tf
# No backup module - not needed in dev
```

This pattern is impossible with workspaces (all workspaces share same code).
