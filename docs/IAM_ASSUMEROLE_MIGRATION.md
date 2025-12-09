# IAM AssumeRole Migration Guide

This guide documents the migration from direct IAM user policies to the AssumeRole pattern for Terraform operations.

## Problem: IAM Policy Limit

AWS IAM users have a limit of **10 attached policies**. When this limit is reached, you cannot attach additional policies (e.g., SQS permissions), blocking infrastructure deployments.

## Solution: AssumeRole Pattern

Instead of attaching all policies directly to the user, we:
1. Create an IAM role (`TerraformDeployRole`) with all necessary policies attached (no limit)
2. Configure the user with minimal permissions to assume this role
3. Use AssumeRole for all Terraform operations

**Benefits:**
- ✅ No policy limit (roles can have unlimited policies)
- ✅ AWS-recommended pattern for elevated permissions
- ✅ Better audit trail (CloudTrail shows AssumeRole events)
- ✅ Temporary credentials (expire after session)

## Phase 1: Immediate Fix (IAM Groups)

**Status:** ✅ Implemented

Move custom policies from user to IAM group to immediately unblock SQS permissions.

```bash
# Run migration
./scripts/iam_migrate_to_groups.sh

# Verify
aws iam list-attached-user-policies --user-name anak
aws iam list-groups-for-user --user-name anak
aws sqs list-queues  # Should work now

# Rollback if needed
./scripts/iam_rollback_to_user.sh
```

**Result:** User has ≤3 policies directly, rest inherited via `TerraformOperators` group.

## Phase 2: Long-term Fix (AssumeRole)

**Status:** ✅ Implemented (ready for migration)

### Step 1: Create Terraform Role

Apply Terraform configuration to create the role:

```bash
cd terraform
terraform init
terraform apply -target=aws_iam_role.terraform_deploy
terraform apply  # Apply remaining resources
terraform output terraform_role_arn  # Save this ARN
```

### Step 2: Configure User Permissions

Run setup script to configure user with minimal AssumeRole permissions:

```bash
# Option 1: Get role ARN from Terraform output
./scripts/iam_setup_assume_role.sh

# Option 2: Provide role ARN directly
./scripts/iam_setup_assume_role.sh arn:aws:iam::ACCOUNT_ID:role/TerraformDeployRole
```

This script:
- Detaches all policies from user
- Creates inline policy: `sts:AssumeRole` + `iam:GetRole` for the role

### Step 3: Configure AWS Profile

Set up AWS profile for easy AssumeRole usage:

```bash
# Option 1: Get role ARN from Terraform output
./scripts/setup_aws_profile_assume_role.sh

# Option 2: Provide role ARN directly
./scripts/setup_aws_profile_assume_role.sh arn:aws:iam::ACCOUNT_ID:role/TerraformDeployRole
```

This creates `[profile terraform]` in `~/.aws/config`.

### Step 4: Validate Configuration

Test AssumeRole configuration:

```bash
./scripts/validate_assume_role.sh
```

This verifies:
- ✅ User can assume role directly
- ✅ AWS profile works
- ✅ Assumed role has required permissions
- ✅ Terraform works with AssumeRole
- ✅ CloudTrail shows AssumeRole events

### Step 5: Use AssumeRole for Terraform

```bash
# Method 1: Use AWS_PROFILE environment variable
export AWS_PROFILE=terraform
terraform plan
terraform apply

# Method 2: Inline for single command
AWS_PROFILE=terraform terraform plan

# Method 3: Update Terraform provider (automatic)
# Set in terraform/variables.tf:
# use_assume_role = true
# terraform_role_arn = "arn:aws:iam::ACCOUNT_ID:role/TerraformDeployRole"
terraform plan  # Automatically uses AssumeRole
```

### Step 6: Migrate CI/CD (Optional)

Update `.github/workflows/deploy.yml` to use AssumeRole:

```yaml
- name: Configure AWS credentials (AssumeRole)
  uses: aws-actions/configure-aws-credentials@v4
  with:
    role-to-assume: ${{ secrets.AWS_ROLE_ARN }}
    aws-region: ${{ env.AWS_REGION }}
```

**Note:** Requires `AWS_ROLE_ARN` secret in GitHub.

**Current Status:** CI/CD still uses direct credentials (for gradual migration).

## Rollback Plan

If AssumeRole fails, rollback to IAM Groups:

```bash
# 1. Re-attach policies to user
./scripts/iam_rollback_to_user.sh

# 2. Remove assume_role from Terraform provider
# Edit terraform/main.tf: Remove assume_role block

# 3. Continue with IAM Groups solution
./scripts/iam_migrate_to_groups.sh
```

## Troubleshooting

### Cannot Assume Role

**Error:** `AccessDenied: User is not authorized to perform: sts:AssumeRole`

**Solutions:**
1. Check user has inline policy: `AssumeTerraformRole`
2. Check role trust policy allows user: `anak`
3. Wait 10-15 seconds for IAM propagation
4. Verify role ARN is correct

### Terraform Fails with AssumeRole

**Error:** `Error: error configuring Terraform AWS Provider`

**Solutions:**
1. Check `terraform_role_arn` variable is set correctly
2. Verify `use_assume_role = true` in variables
3. Test AssumeRole manually: `aws sts assume-role --role-arn ...`
4. Check CloudTrail for AssumeRole events

### Profile Not Found

**Error:** `The config profile (terraform) could not be found`

**Solutions:**
1. Run: `./scripts/setup_aws_profile_assume_role.sh`
2. Check `~/.aws/config` exists and has `[profile terraform]`
3. Verify role ARN in profile matches actual role

## Success Criteria

**Phase 1 (Groups):**
- ✅ User has ≤3 policies directly attached
- ✅ User is member of `TerraformOperators` group
- ✅ Group has 7+ policies attached
- ✅ `aws sqs list-queues` works

**Phase 2 (AssumeRole):**
- ✅ `TerraformDeployRole` exists and has all policies
- ✅ User can assume role: `aws sts assume-role --role-arn ...`
- ✅ Terraform works with `AWS_PROFILE=terraform`
- ✅ CI/CD uses AssumeRole automatically (optional)
- ✅ CloudTrail shows AssumeRole events
- ✅ User has only minimal AssumeRole permissions

## References

- [AWS IAM Best Practices: Use Roles](https://docs.aws.amazon.com/IAM/latest/UserGuide/best-practices.html#use-roles)
- [Terraform AWS Provider: AssumeRole](https://registry.terraform.io/providers/hashicorp/aws/latest/docs#assume-role)
- [IAM Policy Limits](https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_iam-quotas.html)
