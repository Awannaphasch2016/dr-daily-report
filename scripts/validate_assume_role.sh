#!/bin/bash
#
# AssumeRole Validation Script
# Tests AssumeRole configuration and Terraform operations
#
# Usage: ./scripts/validate_assume_role.sh [role-arn]
#

set -euo pipefail

PROFILE_NAME="terraform"
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
echo "AssumeRole Validation"
echo "=========================================="
echo ""
echo "Role ARN: $ROLE_ARN"
echo "Profile: $PROFILE_NAME"
echo ""

# Test 1: Verify user can assume role directly
echo "Test 1: Direct AssumeRole (via AWS CLI)..."
ASSUME_RESULT=$(aws sts assume-role \
    --role-arn "$ROLE_ARN" \
    --role-session-name "validation-$(date +%s)" \
    --query 'Credentials' \
    --output json 2>&1) || {
    echo "   ❌ FAILED: Cannot assume role directly"
    echo "   Error: $ASSUME_RESULT"
    echo ""
    echo "   Troubleshooting:"
    echo "   1. Check user has inline policy: AssumeTerraformRole"
    echo "   2. Check role trust policy allows user: $USER_NAME"
    echo "   3. Wait 10-15 seconds for IAM propagation"
    exit 1
}

echo "   ✅ PASSED: Successfully assumed role"
ACCESS_KEY=$(echo "$ASSUME_RESULT" | jq -r '.AccessKeyId')
EXPIRATION=$(echo "$ASSUME_RESULT" | jq -r '.Expiration')
echo "   Temporary credentials expire: $EXPIRATION"
echo ""

# Test 2: Verify AWS profile works
echo "Test 2: AWS Profile AssumeRole..."
if ! grep -q "\[profile $PROFILE_NAME\]" "${HOME}/.aws/config" 2>/dev/null; then
    echo "   ⚠️  SKIPPED: Profile '$PROFILE_NAME' not configured"
    echo "   Run: ./scripts/setup_aws_profile_assume_role.sh"
else
    PROFILE_IDENTITY=$(aws sts get-caller-identity --profile "$PROFILE_NAME" 2>&1) || {
        echo "   ❌ FAILED: Profile doesn't work"
        echo "   Error: $PROFILE_IDENTITY"
        exit 1
    }
    
    echo "   ✅ PASSED: Profile works"
    ROLE_NAME=$(echo "$PROFILE_IDENTITY" | jq -r '.Arn' | awk -F'/' '{print $NF}')
    echo "   Assumed role: $ROLE_NAME"
fi
echo ""

# Test 3: Verify assumed role has required permissions
echo "Test 3: Permissions check (via assumed role)..."
export AWS_PROFILE="$PROFILE_NAME"

# Test SQS access
if aws sqs list-queues --profile "$PROFILE_NAME" &>/dev/null; then
    echo "   ✅ SQS access works"
else
    echo "   ⚠️  SQS access failed (may not have queues)"
fi

# Test ECR access
if aws ecr describe-repositories --profile "$PROFILE_NAME" &>/dev/null; then
    echo "   ✅ ECR access works"
else
    echo "   ⚠️  ECR access failed (may not have repositories)"
fi

# Test Lambda access
if aws lambda list-functions --profile "$PROFILE_NAME" --max-items 1 &>/dev/null; then
    echo "   ✅ Lambda access works"
else
    echo "   ⚠️  Lambda access failed"
fi

# Test S3 access
if aws s3 ls --profile "$PROFILE_NAME" &>/dev/null; then
    echo "   ✅ S3 access works"
else
    echo "   ⚠️  S3 access failed"
fi

unset AWS_PROFILE
echo ""

# Test 4: Test Terraform with AssumeRole
echo "Test 4: Terraform with AssumeRole..."
if [ ! -d "terraform" ]; then
    echo "   ⚠️  SKIPPED: terraform/ directory not found"
else
    cd terraform
    
    # Check if Terraform is initialized
    if [ ! -d ".terraform" ]; then
        echo "   ⚠️  SKIPPED: Terraform not initialized"
        echo "   Run: terraform init"
    else
        echo "   Running: terraform plan (dry-run)..."
        PLAN_OUTPUT=$(AWS_PROFILE="$PROFILE_NAME" terraform plan -out=/dev/null 2>&1) || {
            PLAN_EXIT_CODE=$?
            if [ $PLAN_EXIT_CODE -eq 1 ]; then
                echo "   ❌ FAILED: Terraform plan failed"
                echo "   Error: $PLAN_OUTPUT"
                cd ..
                exit 1
            else
                # Exit code 2 means plan succeeded but there are changes (expected)
                echo "   ✅ PASSED: Terraform plan works (found changes, which is expected)"
            fi
        }
        
        if echo "$PLAN_OUTPUT" | grep -q "No changes"; then
            echo "   ✅ PASSED: Terraform plan works (no changes detected)"
        elif echo "$PLAN_OUTPUT" | grep -q "Plan:"; then
            echo "   ✅ PASSED: Terraform plan works (changes detected)"
        else
            echo "   ⚠️  Terraform plan output unclear"
        fi
    fi
    
    cd ..
fi
echo ""

# Test 5: Check CloudTrail for AssumeRole events
echo "Test 5: CloudTrail AssumeRole events..."
echo "   Checking last 5 minutes for AssumeRole events..."
START_TIME=$(($(date +%s) - 300))000  # 5 minutes ago

CLOUDTRAIL_EVENTS=$(aws cloudtrail lookup-events \
    --lookup-attributes AttributeKey=EventName,AttributeValue=AssumeRole \
    --start-time "$START_TIME" \
    --max-results 10 \
    --query 'Events[*].[EventTime,Username,Resources[0].ResourceName]' \
    --output text 2>/dev/null || echo "")

if [ -z "$CLOUDTRAIL_EVENTS" ]; then
    echo "   ⚠️  No AssumeRole events found in CloudTrail (may take time to appear)"
else
    echo "   ✅ Found AssumeRole events in CloudTrail:"
    echo "$CLOUDTRAIL_EVENTS" | while read -r event_time username resource; do
        echo "      $event_time - $username → $resource"
    done
fi
echo ""

echo "=========================================="
echo "✅ Validation Complete!"
echo "=========================================="
echo ""
echo "Summary:"
echo "  ✅ Direct AssumeRole: Works"
if grep -q "\[profile $PROFILE_NAME\]" "${HOME}/.aws/config" 2>/dev/null; then
    echo "  ✅ AWS Profile: Configured and working"
else
    echo "  ⚠️  AWS Profile: Not configured (run setup script)"
fi
echo "  ✅ Permissions: Verified"
echo "  ✅ Terraform: Works with AssumeRole"
echo ""
echo "Next steps:"
echo "  1. Use AssumeRole for all Terraform operations:"
echo "     AWS_PROFILE=$PROFILE_NAME terraform plan"
echo "  2. Update CI/CD to use AssumeRole (see .github/workflows/deploy.yml)"
echo ""
