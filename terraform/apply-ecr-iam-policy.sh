#!/bin/bash
# Script to apply ECR IAM policy to current user

set -e

POLICY_NAME="TerraformECRAccess"
POLICY_FILE="iam-ecr-policy.json"

echo "📋 Applying ECR IAM policy..."

# Get current AWS user
CURRENT_USER=$(aws sts get-caller-identity --query 'Arn' --output text | awk -F'/' '{print $NF}')
echo "Current IAM user: $CURRENT_USER"

# Check if policy already exists
POLICY_ARN=$(aws iam list-policies --scope Local --query "Policies[?PolicyName=='$POLICY_NAME'].Arn" --output text)

if [ -z "$POLICY_ARN" ]; then
  echo "Creating new IAM policy: $POLICY_NAME"
  POLICY_ARN=$(aws iam create-policy \
    --policy-name "$POLICY_NAME" \
    --policy-document file://$POLICY_FILE \
    --description "Terraform ECR access for Lambda container deployments" \
    --query 'Policy.Arn' \
    --output text)
  echo "✅ Created policy: $POLICY_ARN"
else
  echo "Policy already exists: $POLICY_ARN"
  echo "Updating policy with new version..."

  # Get the default version
  DEFAULT_VERSION=$(aws iam get-policy --policy-arn "$POLICY_ARN" --query 'Policy.DefaultVersionId' --output text)

  # Create new policy version (AWS will set it as default automatically)
  aws iam create-policy-version \
    --policy-arn "$POLICY_ARN" \
    --policy-document file://$POLICY_FILE \
    --set-as-default

  # Delete old version if it's not v1
  if [ "$DEFAULT_VERSION" != "v1" ]; then
    aws iam delete-policy-version \
      --policy-arn "$POLICY_ARN" \
      --version-id "$DEFAULT_VERSION" || true
  fi

  echo "✅ Updated policy to latest version"
fi

# Attach policy to user
echo "Attaching policy to user: $CURRENT_USER"
aws iam attach-user-policy \
  --user-name "$CURRENT_USER" \
  --policy-arn "$POLICY_ARN" 2>/dev/null || echo "Policy already attached or attachment failed"

echo "✅ ECR IAM policy applied successfully"
echo ""
echo "Policy ARN: $POLICY_ARN"
echo "You can now create ECR repositories with Terraform"
