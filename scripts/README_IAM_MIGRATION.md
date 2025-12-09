# IAM Migration Scripts

Scripts for migrating from direct IAM user policies to IAM Groups (Phase 1) and AssumeRole pattern (Phase 2).

## Quick Start

### Phase 1: Immediate Fix (IAM Groups) - 5 minutes

Unblock SQS permissions by moving policies from user to group:

```bash
# Run migration
./scripts/iam_migrate_to_groups.sh

# Verify it worked
aws sqs list-queues
aws iam list-attached-user-policies --user-name anak
aws iam list-groups-for-user --user-name anak

# Rollback if needed
./scripts/iam_rollback_to_user.sh
```

### Phase 2: Long-term Fix (AssumeRole) - 1-2 hours

Eliminate policy limits entirely with AWS-recommended AssumeRole pattern:

```bash
# Step 1: Create Terraform role
cd terraform
terraform apply -target=aws_iam_role.terraform_deploy
terraform output terraform_role_arn  # Save this ARN

# Step 2: Configure user permissions
cd ..
./scripts/iam_setup_assume_role.sh

# Step 3: Configure AWS profile
./scripts/setup_aws_profile_assume_role.sh

# Step 4: Validate
./scripts/validate_assume_role.sh

# Step 5: Use AssumeRole
AWS_PROFILE=terraform terraform plan
```

## Scripts Overview

| Script | Purpose | When to Use |
|--------|---------|-------------|
| `iam_migrate_to_groups.sh` | Move policies from user to group | Phase 1: Immediate fix |
| `iam_rollback_to_user.sh` | Revert group migration | Troubleshooting Phase 1 |
| `iam_setup_assume_role.sh` | Configure user for AssumeRole | Phase 2: After role created |
| `setup_aws_profile_assume_role.sh` | Create AWS profile | Phase 2: After user setup |
| `validate_assume_role.sh` | Test AssumeRole configuration | Phase 2: Validation |

## Files Created

### Phase 1 (Immediate)
- ✅ `scripts/iam_migrate_to_groups.sh` - Group migration script
- ✅ `scripts/iam_rollback_to_user.sh` - Rollback script

### Phase 2 (Long-term)
- ✅ `terraform/iam_terraform_role.tf` - Terraform role definition
- ✅ `scripts/iam_setup_assume_role.sh` - User setup script
- ✅ `scripts/setup_aws_profile_assume_role.sh` - AWS profile setup
- ✅ `scripts/validate_assume_role.sh` - Validation script
- ✅ `docs/IAM_ASSUMEROLE_MIGRATION.md` - Complete migration guide

### Terraform Updates
- ✅ `terraform/main.tf` - Added `assume_role` provider block
- ✅ `terraform/variables.tf` - Added AssumeRole variables

## Implementation Status

- ✅ Phase 1: IAM Groups migration (ready to run)
- ✅ Phase 2: AssumeRole pattern (ready for migration)
- ✅ Documentation: Complete migration guide
- ⏳ CI/CD: Documented but not migrated (gradual migration)

## Next Steps

1. **TODAY**: Run Phase 1 migration → unblocks SQS
   ```bash
   ./scripts/iam_migrate_to_groups.sh
   ```

2. **THIS WEEK**: Implement Phase 2 AssumeRole pattern
   ```bash
   # Create role
   cd terraform && terraform apply -target=aws_iam_role.terraform_deploy
   
   # Setup user
   ./scripts/iam_setup_assume_role.sh
   ./scripts/setup_aws_profile_assume_role.sh
   ./scripts/validate_assume_role.sh
   ```

3. **NEXT WEEK**: Migrate CI/CD to AssumeRole (optional)
   - Add `AWS_ROLE_ARN` secret to GitHub
   - Update `.github/workflows/deploy.yml` to use `role-to-assume`

## See Also

- [Complete Migration Guide](docs/IAM_ASSUMEROLE_MIGRATION.md)
- [Terraform Role Configuration](terraform/iam_terraform_role.tf)
