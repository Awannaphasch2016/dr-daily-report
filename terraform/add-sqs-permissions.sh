#!/bin/bash
#
# Add SQS permissions to IAM user for async report infrastructure
#
# Usage: ./add-sqs-permissions.sh
#

set -e

POLICY_NAME="dr-daily-report-sqs-access"
POLICY_FILE="iam-sqs-policy.json"

echo "🔐 Adding SQS permissions to IAM user..."

# Check if policy already exists
EXISTING_POLICY=$(aws iam list-policies --query "Policies[?PolicyName=='${POLICY_NAME}'].Arn" --output text 2>/dev/null || true)

if [ -n "$EXISTING_POLICY" ]; then
    echo "📋 Policy already exists: ${EXISTING_POLICY}"
    echo "   Updating policy..."

    # Create new policy version
    aws iam create-policy-version \
        --policy-arn "$EXISTING_POLICY" \
        --policy-document "file://${POLICY_FILE}" \
        --set-as-default

    echo "✅ Policy updated successfully"
else
    echo "📋 Creating new policy: ${POLICY_NAME}"

    POLICY_ARN=$(aws iam create-policy \
        --policy-name "$POLICY_NAME" \
        --policy-document "file://${POLICY_FILE}" \
        --description "SQS permissions for dr-daily-report async infrastructure" \
        --query 'Policy.Arn' \
        --output text)

    echo "✅ Policy created: ${POLICY_ARN}"

    # Get current user
    CURRENT_USER=$(aws sts get-caller-identity --query 'Arn' --output text | sed 's/.*\///')

    echo "📎 Attaching policy to user: ${CURRENT_USER}"
    aws iam attach-user-policy \
        --user-name "$CURRENT_USER" \
        --policy-arn "$POLICY_ARN"

    echo "✅ Policy attached successfully"
fi

echo ""
echo "🎉 Done! You can now run: terraform apply"
