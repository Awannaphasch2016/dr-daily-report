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
echo "💡 Tip: Run 'aws logs tail /aws/lambda/${TELEGRAM_API_FUNCTION} --follow' to watch logs"
