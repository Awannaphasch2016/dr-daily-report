#!/bin/bash
#
# IAM AssumeRole Setup Script - Phase 2 (Long-term Fix)
# Configures user with minimal AssumeRole permissions
#
# Usage: ./scripts/iam_setup_assume_role.sh [role-arn]
#
# Prerequisites:
#   1. TerraformDeployRole must exist (created via terraform/iam_terraform_role.tf)
#   2. Run this script AFTER applying terraform/iam_terraform_role.tf
#

set -euo pipefail

USER_NAME="anak"

# Get role ARN from argument or Terraform output
if [ $# -ge 1 ]; then
    ROLE_ARN="$1"
else
    echo "📋 Getting role ARN from Terraform output..."
    cd terraform
    ROLE_ARN=$(terraform output -raw terraform_role_arn 2>/dev/null || {
        echo "❌ Failed to get role ARN from Terraform"
        echo "   Make sure terraform/iam_terraform_role.tf has been applied"
        echo "   Or provide role ARN as argument: $0 <role-arn>"
        exit 1
    })
    cd ..
fi

echo "=========================================="
echo "IAM AssumeRole Setup (Phase 2)"
echo "=========================================="
echo ""
echo "Goal: Configure user with minimal AssumeRole permissions"
echo "Role ARN: $ROLE_ARN"
echo ""

# Verify role exists
echo "Step 1: Verifying role exists..."
if aws iam get-role --role-name "$(echo "$ROLE_ARN" | awk -F'/' '{print $NF}')" &>/dev/null; then
    echo "   ✅ Role exists"
else
    echo "   ❌ Role not found: $ROLE_ARN"
    echo "   Create it first: terraform apply -target=aws_iam_role.terraform_deploy"
    exit 1
fi
echo ""

# Step 2: Detach all policies from user (except AssumeRole policy we'll create)
echo "Step 2: Detaching existing policies from user..."
echo "   ⚠️  This will remove all policies from user!"
read -p "   Continue? (y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Setup cancelled"
    exit 0
fi

USER_POLICIES=$(aws iam list-attached-user-policies --user-name "$USER_NAME" --query 'AttachedPolicies[*].PolicyArn' --output text)
if [ -n "$USER_POLICIES" ]; then
    for policy_arn in $USER_POLICIES; do
        policy_name=$(echo "$policy_arn" | awk -F'/' '{print $NF}')
        echo "   Detaching: $policy_name"
        aws iam detach-user-policy --user-name "$USER_NAME" --policy-arn "$policy_arn" || {
            echo "      ⚠️  Failed to detach (may already be detached)"
        }
    done
    echo "   ✅ All policies detached"
else
    echo "   No policies to detach"
fi
echo ""

# Step 3: Create inline AssumeRole policy
echo "Step 3: Creating inline AssumeRole policy..."
ASSUME_ROLE_POLICY=$(cat <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "sts:AssumeRole",
        "iam:GetRole"
      ],
      "Resource": "$ROLE_ARN"
    }
  ]
}
EOF
)

# Check if inline policy already exists
if aws iam get-user-policy --user-name "$USER_NAME" --policy-name "AssumeTerraformRole" &>/dev/null; then
    echo "   Updating existing inline policy..."
    aws iam put-user-policy \
        --user-name "$USER_NAME" \
        --policy-name "AssumeTerraformRole" \
        --policy-document "$ASSUME_ROLE_POLICY"
    echo "   ✅ Policy updated"
else
    echo "   Creating new inline policy..."
    aws iam put-user-policy \
        --user-name "$USER_NAME" \
        --policy-name "AssumeTerraformRole" \
        --policy-document "$ASSUME_ROLE_POLICY"
    echo "   ✅ Policy created"
fi
echo ""

# Step 4: Verify configuration
echo "Step 4: Verifying configuration..."
echo ""

echo "   User policies (should only have inline AssumeRole policy):"
USER_POLICIES_AFTER=$(aws iam list-attached-user-policies --user-name "$USER_NAME" --query 'AttachedPolicies[*].PolicyArn' --output text)
if [ -z "$USER_POLICIES_AFTER" ]; then
    echo "   ✅ No attached policies"
else
    echo "   ⚠️  Still has attached policies:"
    for policy in $USER_POLICIES_AFTER; do
        echo "   - $policy"
    done
fi

INLINE_POLICIES=$(aws iam list-user-policies --user-name "$USER_NAME" --query 'PolicyNames' --output text)
if echo "$INLINE_POLICIES" | grep -q "AssumeTerraformRole"; then
    echo "   ✅ Inline policy 'AssumeTerraformRole' exists"
else
    echo "   ❌ Inline policy not found"
fi
echo ""

# Step 5: Test AssumeRole
echo "Step 5: Testing AssumeRole..."
echo "   Attempting to assume role..."
ASSUMED_CREDENTIALS=$(aws sts assume-role \
    --role-arn "$ROLE_ARN" \
    --role-session-name "terraform-test-$(date +%s)" \
    --query 'Credentials' \
    --output json 2>&1) || {
    echo "   ❌ Failed to assume role"
    echo "   Error: $ASSUMED_CREDENTIALS"
    echo ""
    echo "   Troubleshooting:"
    echo "   1. Check trust policy allows user: $USER_NAME"
    echo "   2. Check inline policy allows sts:AssumeRole"
    echo "   3. Wait 10-15 seconds for IAM propagation"
    exit 1
}

echo "   ✅ Successfully assumed role!"
ACCESS_KEY=$(echo "$ASSUMED_CREDENTIALS" | jq -r '.AccessKeyId')
echo "   Temporary Access Key: ${ACCESS_KEY:0:10}..."
echo ""

echo "=========================================="
echo "✅ AssumeRole Setup Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "  1. Configure AWS profile: ./scripts/setup_aws_profile_assume_role.sh"
echo "  2. Test Terraform: AWS_PROFILE=terraform terraform plan"
echo "  3. Validate: ./scripts/validate_assume_role.sh"
echo ""
echo "Role ARN: $ROLE_ARN"
echo ""
