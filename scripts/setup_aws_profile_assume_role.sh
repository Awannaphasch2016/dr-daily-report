#!/bin/bash
#
# AWS Profile Setup for AssumeRole Pattern
# Creates [profile terraform] in ~/.aws/config
#
# Usage: ./scripts/setup_aws_profile_assume_role.sh [role-arn]
#

set -euo pipefail

AWS_CONFIG_FILE="${HOME}/.aws/config"
PROFILE_NAME="terraform"

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

# Get current AWS profile (default or from AWS_PROFILE)
SOURCE_PROFILE="${AWS_PROFILE:-default}"
if [ "$SOURCE_PROFILE" = "default" ]; then
    # Check if default profile exists
    if ! grep -q "\[profile default\]" "$AWS_CONFIG_FILE" 2>/dev/null && \
       ! grep -q "\[default\]" "$AWS_CONFIG_FILE" 2>/dev/null; then
        echo "⚠️  No default profile found. Using 'default' as source_profile."
        echo "   Make sure your AWS credentials are configured:"
        echo "   - Run: aws configure"
        echo "   - Or set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY"
    fi
fi

echo "=========================================="
echo "AWS Profile Setup for AssumeRole"
echo "=========================================="
echo ""
echo "Profile name: $PROFILE_NAME"
echo "Role ARN: $ROLE_ARN"
echo "Source profile: $SOURCE_PROFILE"
echo ""

# Create .aws directory if it doesn't exist
mkdir -p "$(dirname "$AWS_CONFIG_FILE")"

# Create config file if it doesn't exist
if [ ! -f "$AWS_CONFIG_FILE" ]; then
    touch "$AWS_CONFIG_FILE"
    chmod 600 "$AWS_CONFIG_FILE"
    echo "📝 Created $AWS_CONFIG_FILE"
fi

# Check if profile already exists
if grep -q "\[profile $PROFILE_NAME\]" "$AWS_CONFIG_FILE"; then
    echo "⚠️  Profile '$PROFILE_NAME' already exists in $AWS_CONFIG_FILE"
    read -p "   Overwrite? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Setup cancelled"
        exit 0
    fi
    
    # Remove existing profile block
    sed -i "/\[profile $PROFILE_NAME\]/,/^$/d" "$AWS_CONFIG_FILE"
    echo "   Removed existing profile"
fi

# Add profile configuration
echo "" >> "$AWS_CONFIG_FILE"
echo "[profile $PROFILE_NAME]" >> "$AWS_CONFIG_FILE"
echo "role_arn = $ROLE_ARN" >> "$AWS_CONFIG_FILE"
echo "source_profile = $SOURCE_PROFILE" >> "$AWS_CONFIG_FILE"
echo "region = ap-southeast-1" >> "$AWS_CONFIG_FILE"

echo "✅ Profile configured in $AWS_CONFIG_FILE"
echo ""

# Verify configuration
echo "Verifying configuration..."
if aws sts get-caller-identity --profile "$PROFILE_NAME" &>/dev/null; then
    echo "✅ Profile works! Current identity:"
    aws sts get-caller-identity --profile "$PROFILE_NAME"
else
    echo "⚠️  Profile test failed (may need to wait for IAM propagation)"
    echo "   Try again in 10-15 seconds:"
    echo "   aws sts get-caller-identity --profile $PROFILE_NAME"
fi
echo ""

echo "=========================================="
echo "✅ Setup Complete!"
echo "=========================================="
echo ""
echo "Usage:"
echo "  # Use AssumeRole for Terraform"
echo "  AWS_PROFILE=$PROFILE_NAME terraform plan"
echo "  AWS_PROFILE=$PROFILE_NAME terraform apply"
echo ""
echo "  # Or export for all commands"
echo "  export AWS_PROFILE=$PROFILE_NAME"
echo "  terraform plan"
echo ""
echo "Profile configuration:"
echo "  Role ARN: $ROLE_ARN"
echo "  Source: $SOURCE_PROFILE"
echo "  Region: ap-southeast-1"
echo ""
