#!/bin/bash
# Deploy Backend Lambda Functions
# Usage: ./scripts/deploy-backend.sh [dev|staging|prod]

set -e

ENV=${1:-dev}
PROJECT_NAME="dr-daily-report"
AWS_REGION="ap-southeast-1"

echo "🚀 Deploying backend to ${ENV}..."

# Validate environment
if [[ ! "$ENV" =~ ^(dev|staging|prod)$ ]]; then
    echo "❌ Invalid environment: $ENV"
    echo "Usage: $0 [dev|staging|prod]"
    exit 1
fi

# Select tfvars file based on environment
TFVARS_FILE="terraform.${ENV}.tfvars"
if [ ! -f "terraform/${TFVARS_FILE}" ]; then
    echo "❌ tfvars file not found: terraform/${TFVARS_FILE}"
    exit 1
fi
echo "📋 Using tfvars: ${TFVARS_FILE}"

# Get ECR repository URL from Terraform
cd terraform
ECR_REPO=$(terraform output -raw ecr_repository_url 2>/dev/null) || {
    echo "❌ Failed to get ECR repository URL from Terraform"
    echo "Make sure terraform has been applied with -var-file=${TFVARS_FILE}"
    exit 1
}
TELEGRAM_API_FUNCTION=$(terraform output -raw telegram_lambda_function_name 2>/dev/null) || {
    echo "❌ Failed to get Telegram API function name from Terraform"
    exit 1
}
REPORT_WORKER_FUNCTION=$(terraform output -raw report_worker_function_name 2>/dev/null) || {
    echo "❌ Failed to get Report Worker function name from Terraform"
    exit 1
}
SCHEDULER_FUNCTION=$(terraform output -raw ticker_scheduler_function_name 2>/dev/null) || {
    echo "⚠️ Scheduler function not found in Terraform outputs, skipping scheduler deployment"
    SCHEDULER_FUNCTION=""
}
cd ..

echo "📦 ECR Repository: ${ECR_REPO}"
echo "🔧 Telegram API Function: ${TELEGRAM_API_FUNCTION}"
echo "🔧 Report Worker Function: ${REPORT_WORKER_FUNCTION}"
if [ -n "$SCHEDULER_FUNCTION" ]; then
    echo "🔧 Scheduler Function: ${SCHEDULER_FUNCTION}"
fi

# Login to ECR
echo "🔐 Logging in to ECR..."
aws ecr get-login-password --region ${AWS_REGION} | \
    docker login --username AWS --password-stdin ${ECR_REPO%%/*}

# Build Docker image with versioned tag
VERSION_TAG="v$(date +%Y%m%d%H%M%S)"
echo "🔨 Building Docker image (${VERSION_TAG})..."
IMAGE_TAG="${ECR_REPO}:${VERSION_TAG}"
docker build -t ${IMAGE_TAG} -f Dockerfile.lambda.container .

# Push to ECR
echo "📤 Pushing image to ECR..."
docker push ${IMAGE_TAG}

# Update Lambda functions to use new image
echo "🔄 Updating Lambda functions..."

# Update Telegram API Lambda
echo "  Updating ${TELEGRAM_API_FUNCTION}..."
aws lambda update-function-code \
    --function-name ${TELEGRAM_API_FUNCTION} \
    --image-uri ${IMAGE_TAG} \
    --region ${AWS_REGION} \
    --output text > /dev/null

# Wait for update to complete
aws lambda wait function-updated \
    --function-name ${TELEGRAM_API_FUNCTION} \
    --region ${AWS_REGION}

# Update Report Worker Lambda
echo "  Updating ${REPORT_WORKER_FUNCTION}..."
aws lambda update-function-code \
    --function-name ${REPORT_WORKER_FUNCTION} \
    --image-uri ${IMAGE_TAG} \
    --region ${AWS_REGION} \
    --output text > /dev/null

# Wait for update to complete
aws lambda wait function-updated \
    --function-name ${REPORT_WORKER_FUNCTION} \
    --region ${AWS_REGION}

# Update Scheduler Lambda (if exists)
if [ -n "$SCHEDULER_FUNCTION" ]; then
    echo "  Updating ${SCHEDULER_FUNCTION}..."
    aws lambda update-function-code \
        --function-name ${SCHEDULER_FUNCTION} \
        --image-uri ${IMAGE_TAG} \
        --region ${AWS_REGION} \
        --output text > /dev/null
    
    # Wait for update to complete
    aws lambda wait function-updated \
        --function-name ${SCHEDULER_FUNCTION} \
        --region ${AWS_REGION}
    echo "  ✅ Scheduler updated"
fi

# ============================================================================
# SMOKE TESTS - Test via API Gateway before promoting to live
# ============================================================================
echo ""
echo "🧪 Running smoke tests via API Gateway..."

# Get API URL from Terraform (need to stay in terraform dir from earlier)
cd terraform
API_URL=$(terraform output -raw telegram_api_invoke_url 2>/dev/null) || {
    echo "  ⚠️ Could not get API URL from Terraform, skipping smoke tests"
    API_URL=""
}
cd ..

if [ -n "$API_URL" ]; then
    # Test health endpoint via API Gateway (tests the live alias)
    echo "  Testing health endpoint: ${API_URL}/health"
    HEALTH_RESPONSE=$(curl -s -w "\n%{http_code}" "${API_URL}/health" 2>/dev/null)
    HEALTH_CODE=$(echo "$HEALTH_RESPONSE" | tail -n1)
    HEALTH_BODY=$(echo "$HEALTH_RESPONSE" | head -n-1)

    if [ "$HEALTH_CODE" != "200" ]; then
        echo "  ❌ Health check failed (HTTP $HEALTH_CODE)"
        echo "  Response: $HEALTH_BODY"
        echo ""
        echo "⚠️  Deployment stopped. Lambda updated but alias NOT moved."
        echo "   Users still see previous version."
        exit 1
    fi

    # Verify response contains status: ok
    HEALTH_STATUS=$(echo "$HEALTH_BODY" | jq -r '.status' 2>/dev/null)
    if [ "$HEALTH_STATUS" != "ok" ]; then
        echo "  ❌ Health check returned unexpected status: $HEALTH_STATUS"
        echo "  Response: $HEALTH_BODY"
        echo ""
        echo "⚠️  Deployment stopped. Lambda updated but alias NOT moved."
        exit 1
    fi

    echo "  ✅ Health check passed (status: ok)"
else
    echo "  ⏭️  Skipping smoke tests (API URL not available)"
fi

# ============================================================================
# PUBLISH & PROMOTE - Only after smoke tests pass
# ============================================================================
echo ""
echo "📸 Publishing new versions..."

# Publish Telegram API version
TELEGRAM_VERSION=$(aws lambda publish-version \
    --function-name ${TELEGRAM_API_FUNCTION} \
    --description "Deployed $(date +%Y-%m-%d\ %H:%M:%S)" \
    --region ${AWS_REGION} \
    --query 'Version' \
    --output text)
echo "  Telegram API: Version ${TELEGRAM_VERSION}"

# Publish Report Worker version
WORKER_VERSION=$(aws lambda publish-version \
    --function-name ${REPORT_WORKER_FUNCTION} \
    --description "Deployed $(date +%Y-%m-%d\ %H:%M:%S)" \
    --region ${AWS_REGION} \
    --query 'Version' \
    --output text)
echo "  Report Worker: Version ${WORKER_VERSION}"

# Publish Scheduler version (if exists)
if [ -n "$SCHEDULER_FUNCTION" ]; then
    SCHEDULER_VERSION=$(aws lambda publish-version \
        --function-name ${SCHEDULER_FUNCTION} \
        --description "Deployed $(date +%Y-%m-%d\ %H:%M:%S)" \
        --region ${AWS_REGION} \
        --query 'Version' \
        --output text)
    echo "  Scheduler: Version ${SCHEDULER_VERSION}"
fi

# Update aliases to point to new versions
echo ""
echo "🔄 Updating 'live' aliases..."

aws lambda update-alias \
    --function-name ${TELEGRAM_API_FUNCTION} \
    --name live \
    --function-version ${TELEGRAM_VERSION} \
    --region ${AWS_REGION} \
    --output text > /dev/null
echo "  Telegram API: live → v${TELEGRAM_VERSION}"

aws lambda update-alias \
    --function-name ${REPORT_WORKER_FUNCTION} \
    --name live \
    --function-version ${WORKER_VERSION} \
    --region ${AWS_REGION} \
    --output text > /dev/null
echo "  Report Worker: live → v${WORKER_VERSION}"

if [ -n "$SCHEDULER_FUNCTION" ]; then
    aws lambda update-alias \
        --function-name ${SCHEDULER_FUNCTION} \
        --name live \
        --function-version ${SCHEDULER_VERSION} \
        --region ${AWS_REGION} \
        --output text > /dev/null
    echo "  Scheduler: live → v${SCHEDULER_VERSION}"
fi

echo ""
echo "🎉 Backend deployed successfully!"
echo ""
echo "📊 Lambda Functions Updated:"
echo "   - ${TELEGRAM_API_FUNCTION}"
echo "   - ${REPORT_WORKER_FUNCTION}"
if [ -n "$SCHEDULER_FUNCTION" ]; then
    echo "   - ${SCHEDULER_FUNCTION}"
fi

# Get API URL
cd terraform
API_URL=$(terraform output -raw telegram_api_invoke_url 2>/dev/null) || API_URL="Unknown"
cd ..

echo ""
echo "🔗 API URL: ${API_URL}"
echo ""
echo "📊 Versions deployed:"
echo "   Telegram API: v${TELEGRAM_VERSION}"
echo "   Report Worker: v${WORKER_VERSION}"
if [ -n "$SCHEDULER_FUNCTION" ]; then
    echo "   Scheduler: v${SCHEDULER_VERSION}"
fi
echo ""
echo "💡 Tips:"
echo "   Watch logs: aws logs tail /aws/lambda/${TELEGRAM_API_FUNCTION} --follow"
if [ -n "$SCHEDULER_FUNCTION" ]; then
    echo "   Scheduler logs: aws logs tail /aws/lambda/${SCHEDULER_FUNCTION} --follow"
fi
echo ""
echo "   Rollback:   aws lambda update-alias --function-name ${TELEGRAM_API_FUNCTION} --name live --function-version <prev>"
echo "               aws lambda update-alias --function-name ${REPORT_WORKER_FUNCTION} --name live --function-version <prev>"
if [ -n "$SCHEDULER_FUNCTION" ]; then
    echo "               aws lambda update-alias --function-name ${SCHEDULER_FUNCTION} --name live --function-version <prev>"
fi
