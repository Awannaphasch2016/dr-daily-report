#!/bin/bash
#
# IAM Rollback Script - Revert Group Migration
# Moves policies back from group to user (for troubleshooting)
#
# Usage: ./scripts/iam_rollback_to_user.sh
#

set -euo pipefail

GROUP_NAME="TerraformOperators"
USER_NAME="anak"

echo "=========================================="
echo "IAM Rollback - Reverting Group Migration"
echo "=========================================="
echo ""
echo "⚠️  WARNING: This will move policies back to user"
echo "   This may hit the 10-policy limit again!"
echo ""

read -p "Continue with rollback? (y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Rollback cancelled"
    exit 0
fi

echo ""
echo "📋 Current user: $USER_NAME"
echo ""

# Step 1: List group policies
echo "Step 1: Listing group policies..."
GROUP_POLICIES=$(aws iam list-attached-group-policies --group-name "$GROUP_NAME" --query 'AttachedPolicies[*].PolicyArn' --output text)
if [ -z "$GROUP_POLICIES" ]; then
    echo "   No policies in group. Nothing to rollback."
    exit 0
fi

echo "   Found policies in group:"
for policy in $GROUP_POLICIES; do
    echo "   - $policy"
done
echo ""

# Step 2: Move policies back to user
echo "Step 2: Moving policies back to user..."
for policy_arn in $GROUP_POLICIES; do
    policy_name=$(echo "$policy_arn" | awk -F'/' '{print $NF}')
    echo "   Processing: $policy_name"
    
    # Detach from group
    echo "      Detaching from group..."
    aws iam detach-group-policy --group-name "$GROUP_NAME" --policy-arn "$policy_arn" || {
        echo "      ⚠️  Failed to detach from group"
    }
    
    # Attach to user
    echo "      Attaching to user..."
    aws iam attach-user-policy --user-name "$USER_NAME" --policy-arn "$policy_arn" || {
        echo "      ⚠️  Failed to attach to user (may already be attached)"
    }
    
    echo "      ✅ Moved: $policy_name"
done
echo ""

# Step 3: Remove user from group (optional - keep group for future use)
echo "Step 3: Removing user from group..."
read -p "Remove user from group? (y/N) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    aws iam remove-user-from-group --group-name "$GROUP_NAME" --user-name "$USER_NAME" || {
        echo "   ⚠️  Failed to remove user from group (may not be member)"
    }
    echo "   ✅ Removed user from group"
else
    echo "   Keeping user in group (for future use)"
fi
echo ""

# Step 4: Verify configuration
echo "Step 4: Verifying configuration..."
echo ""

echo "   User policies (after rollback):"
USER_POLICIES_AFTER=$(aws iam list-attached-user-policies --user-name "$USER_NAME" --query 'AttachedPolicies[*].PolicyArn' --output text)
if [ -z "$USER_POLICIES_AFTER" ]; then
    echo "   (none)"
else
    for policy in $USER_POLICIES_AFTER; do
        echo "   - $policy"
    done
    USER_POLICY_COUNT=$(echo "$USER_POLICIES_AFTER" | wc -w)
    echo "   Total: $USER_POLICY_COUNT policies"
    if [ "$USER_POLICY_COUNT" -gt 10 ]; then
        echo "   ⚠️  WARNING: User has more than 10 policies (AWS limit)"
    fi
fi
echo ""

echo "=========================================="
echo "✅ Rollback Complete!"
echo "=========================================="
echo ""
echo "Note: Group '$GROUP_NAME' still exists but is empty"
echo "You can delete it with: aws iam delete-group --group-name $GROUP_NAME"
echo ""
