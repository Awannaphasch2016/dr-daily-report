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

# Get ECR repository URL from Terraform
cd terraform
ECR_REPO=$(terraform output -raw ecr_repository_url 2>/dev/null) || {
    echo "❌ Failed to get ECR repository URL from Terraform"
    echo "Make sure terraform has been applied first"
    exit 1
}
TELEGRAM_API_FUNCTION=$(terraform output -raw telegram_api_function_name 2>/dev/null) || {
    echo "❌ Failed to get Telegram API function name from Terraform"
    exit 1
}
REPORT_WORKER_FUNCTION=$(terraform output -raw report_worker_function_name 2>/dev/null) || {
    echo "❌ Failed to get Report Worker function name from Terraform"
    exit 1
}
cd ..

echo "📦 ECR Repository: ${ECR_REPO}"
echo "🔧 Telegram API Function: ${TELEGRAM_API_FUNCTION}"
echo "🔧 Report Worker Function: ${REPORT_WORKER_FUNCTION}"

# Login to ECR
echo "🔐 Logging in to ECR..."
aws ecr get-login-password --region ${AWS_REGION} | \
    docker login --username AWS --password-stdin ${ECR_REPO%%/*}

# Build Docker image
echo "🔨 Building Docker image..."
IMAGE_TAG="${ECR_REPO}:latest"
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

# ============================================================================
# SMOKE TESTS - Test $LATEST before promoting to live
# ============================================================================
echo ""
echo "🧪 Running smoke tests on \$LATEST..."

# Test Telegram API health endpoint
echo "  Testing Telegram API health..."
HEALTH_RESPONSE=$(aws lambda invoke \
    --function-name ${TELEGRAM_API_FUNCTION} \
    --payload '{"rawPath": "/api/v1/health", "requestContext": {"http": {"method": "GET"}}}' \
    --region ${AWS_REGION} \
    /tmp/health_response.json \
    --query 'StatusCode' \
    --output text 2>/dev/null)

if [ "$HEALTH_RESPONSE" != "200" ]; then
    echo "  ❌ Health check failed (status: $HEALTH_RESPONSE)"
    echo "  Response: $(cat /tmp/health_response.json)"
    echo ""
    echo "⚠️  Deployment stopped. $LATEST updated but alias NOT moved."
    echo "   Users still see previous version."
    exit 1
fi

# Check response body
HEALTH_BODY=$(cat /tmp/health_response.json | jq -r '.body' 2>/dev/null | jq -r '.status' 2>/dev/null)
if [ "$HEALTH_BODY" != "healthy" ]; then
    echo "  ❌ Health check returned unexpected status: $HEALTH_BODY"
    echo "  Response: $(cat /tmp/health_response.json)"
    echo ""
    echo "⚠️  Deployment stopped. $LATEST updated but alias NOT moved."
    exit 1
fi

echo "  ✅ Telegram API health check passed"

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

echo ""
echo "🎉 Backend deployed successfully!"
echo ""
echo "📊 Lambda Functions Updated:"
echo "   - ${TELEGRAM_API_FUNCTION}"
echo "   - ${REPORT_WORKER_FUNCTION}"

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
echo ""
echo "💡 Tips:"
echo "   Watch logs: aws logs tail /aws/lambda/${TELEGRAM_API_FUNCTION} --follow"
echo ""
echo "   Rollback:   aws lambda update-alias --function-name ${TELEGRAM_API_FUNCTION} --name live --function-version <prev>"
echo "               aws lambda update-alias --function-name ${REPORT_WORKER_FUNCTION} --name live --function-version <prev>"
