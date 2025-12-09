#!/bin/bash
#
# IAM Group Migration Script - Phase 1 (Immediate Fix)
# Moves custom policies from user to IAM group to unblock SQS permissions
#
# Usage: ./scripts/iam_migrate_to_groups.sh
#

set -euo pipefail

GROUP_NAME="TerraformOperators"
USER_NAME="anak"  # Hardcoded as per plan

echo "=========================================="
echo "IAM Group Migration (Phase 1)"
echo "=========================================="
echo ""
echo "Goal: Move custom policies from user to group"
echo "Result: User has ≤3 policies directly, rest inherited via group"
echo ""

# Get current user to verify
CURRENT_USER=$(aws sts get-caller-identity --query 'Arn' --output text | sed 's/.*\///')
if [ "$CURRENT_USER" != "$USER_NAME" ]; then
    echo "⚠️  Warning: Current user ($CURRENT_USER) doesn't match expected ($USER_NAME)"
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

echo "📋 Current user: $CURRENT_USER"
echo ""

# Step 1: List all policies attached to user
echo "Step 1: Listing current user policies..."
USER_POLICIES=$(aws iam list-attached-user-policies --user-name "$USER_NAME" --query 'AttachedPolicies[*].PolicyArn' --output text)
echo "   Found policies attached to user:"
if [ -z "$USER_POLICIES" ]; then
    echo "   (none)"
else
    for policy in $USER_POLICIES; do
        echo "   - $policy"
    done
fi
echo ""

# Step 2: Identify AWS-managed vs custom policies
echo "Step 2: Identifying policy types..."
AWS_MANAGED_POLICIES=()
CUSTOM_POLICIES=()

for policy_arn in $USER_POLICIES; do
    if [[ "$policy_arn" == arn:aws:iam::aws:* ]]; then
        AWS_MANAGED_POLICIES+=("$policy_arn")
        echo "   AWS-managed: $policy_arn"
    else
        CUSTOM_POLICIES+=("$policy_arn")
        echo "   Custom: $policy_arn"
    fi
done

echo ""
echo "   Summary:"
echo "   - AWS-managed policies: ${#AWS_MANAGED_POLICIES[@]} (will keep on user)"
echo "   - Custom policies: ${#CUSTOM_POLICIES[@]} (will move to group)"
echo ""

if [ ${#CUSTOM_POLICIES[@]} -eq 0 ]; then
    echo "✅ No custom policies to migrate. User already optimized."
    exit 0
fi

# Step 3: Create IAM group (if not exists)
echo "Step 3: Creating IAM group '$GROUP_NAME'..."
if aws iam get-group --group-name "$GROUP_NAME" &>/dev/null; then
    echo "   Group already exists: $GROUP_NAME"
else
    aws iam create-group --group-name "$GROUP_NAME"
    echo "   ✅ Created group: $GROUP_NAME"
fi
echo ""

# Step 4: Detach custom policies from user and attach to group
echo "Step 4: Moving custom policies to group..."
for policy_arn in "${CUSTOM_POLICIES[@]}"; do
    policy_name=$(echo "$policy_arn" | awk -F'/' '{print $NF}')
    echo "   Processing: $policy_name"
    
    # Detach from user
    echo "      Detaching from user..."
    aws iam detach-user-policy --user-name "$USER_NAME" --policy-arn "$policy_arn" || {
        echo "      ⚠️  Failed to detach (may already be detached)"
    }
    
    # Attach to group
    echo "      Attaching to group..."
    aws iam attach-group-policy --group-name "$GROUP_NAME" --policy-arn "$policy_arn" || {
        echo "      ⚠️  Failed to attach (may already be attached)"
    }
    
    echo "      ✅ Moved: $policy_name"
done
echo ""

# Step 5: Ensure SQS policy is attached to group
echo "Step 5: Ensuring SQS policy is attached to group..."
SQS_POLICY_NAME="dr-daily-report-sqs-access"
SQS_POLICY_ARN=$(aws iam list-policies --scope Local --query "Policies[?PolicyName=='${SQS_POLICY_NAME}'].Arn" --output text 2>/dev/null || true)

if [ -z "$SQS_POLICY_ARN" ]; then
    echo "   ⚠️  SQS policy not found. Creating it..."
    cd terraform
    SQS_POLICY_ARN=$(aws iam create-policy \
        --policy-name "$SQS_POLICY_NAME" \
        --policy-document file://iam-sqs-policy.json \
        --description "SQS permissions for dr-daily-report async infrastructure" \
        --query 'Policy.Arn' \
        --output text)
    cd ..
    echo "   ✅ Created SQS policy: $SQS_POLICY_ARN"
else
    echo "   SQS policy exists: $SQS_POLICY_ARN"
fi

# Attach SQS policy to group
aws iam attach-group-policy --group-name "$GROUP_NAME" --policy-arn "$SQS_POLICY_ARN" 2>/dev/null || {
    echo "   ⚠️  SQS policy already attached to group (or attachment failed)"
}
echo "   ✅ SQS policy attached to group"
echo ""

# Step 6: Add user to group
echo "Step 6: Adding user to group..."
if aws iam get-group --group-name "$GROUP_NAME" --query "Users[?UserName=='$USER_NAME']" --output text | grep -q "$USER_NAME"; then
    echo "   User already in group"
else
    aws iam add-user-to-group --group-name "$GROUP_NAME" --user-name "$USER_NAME"
    echo "   ✅ Added user to group"
fi
echo ""

# Step 7: Verify configuration
echo "Step 7: Verifying configuration..."
echo ""

echo "   User policies (should be ≤3 AWS-managed):"
USER_POLICIES_AFTER=$(aws iam list-attached-user-policies --user-name "$USER_NAME" --query 'AttachedPolicies[*].PolicyArn' --output text)
if [ -z "$USER_POLICIES_AFTER" ]; then
    echo "   (none) ✅"
else
    for policy in $USER_POLICIES_AFTER; do
        echo "   - $policy"
    done
    USER_POLICY_COUNT=$(echo "$USER_POLICIES_AFTER" | wc -w)
    if [ "$USER_POLICY_COUNT" -le 3 ]; then
        echo "   ✅ User has $USER_POLICY_COUNT policies (≤3 limit)"
    else
        echo "   ⚠️  User still has $USER_POLICY_COUNT policies (may exceed limit)"
    fi
fi
echo ""

echo "   Group policies (should include all custom policies + SQS):"
GROUP_POLICIES=$(aws iam list-attached-group-policies --group-name "$GROUP_NAME" --query 'AttachedPolicies[*].PolicyArn' --output text)
if [ -z "$GROUP_POLICIES" ]; then
    echo "   (none) ❌"
else
    for policy in $GROUP_POLICIES; do
        policy_name=$(echo "$policy" | awk -F'/' '{print $NF}')
        echo "   - $policy_name"
    done
    GROUP_POLICY_COUNT=$(echo "$GROUP_POLICIES" | wc -w)
    echo "   ✅ Group has $GROUP_POLICY_COUNT policies"
fi
echo ""

echo "   User group membership:"
USER_GROUPS=$(aws iam list-groups-for-user --user-name "$USER_NAME" --query 'Groups[*].GroupName' --output text)
if echo "$USER_GROUPS" | grep -q "$GROUP_NAME"; then
    echo "   ✅ User is member of $GROUP_NAME"
else
    echo "   ❌ User is NOT member of $GROUP_NAME"
fi
echo ""

# Step 8: Test SQS access
echo "Step 8: Testing SQS access..."
if aws sqs list-queues &>/dev/null; then
    echo "   ✅ SQS access works!"
else
    echo "   ⚠️  SQS access test failed (may need to wait for IAM propagation)"
    echo "   Wait 10-15 seconds and run: aws sqs list-queues"
fi
echo ""

echo "=========================================="
echo "✅ Migration Complete!"
echo "=========================================="
echo ""
echo "Summary:"
echo "  - User policies: $(aws iam list-attached-user-policies --user-name "$USER_NAME" --query 'length(AttachedPolicies)' --output text)"
echo "  - Group policies: $(aws iam list-attached-group-policies --group-name "$GROUP_NAME" --query 'length(AttachedPolicies)' --output text)"
echo "  - User is member of: $GROUP_NAME"
echo ""
echo "Next steps:"
echo "  1. Test SQS access: aws sqs list-queues"
echo "  2. Test Terraform: terraform plan"
echo "  3. If issues, rollback: ./scripts/iam_rollback_to_user.sh"
echo ""
