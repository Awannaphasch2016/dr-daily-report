#!/bin/bash
# Deploy MCP Server Lambda Functions
# Usage: ./scripts/deploy-mcp-server.sh [dev|staging|prod] [sec-edgar|all]

set -e

ENV=${1:-dev}
SERVER=${2:-all}
PROJECT_NAME="dr-daily-report"
AWS_REGION="ap-southeast-1"

echo "🚀 Deploying MCP server(s) to ${ENV}..."

# Validate environment
if [[ ! "$ENV" =~ ^(dev|staging|prod)$ ]]; then
    echo "❌ Invalid environment: $ENV"
    echo "Usage: $0 [dev|staging|prod] [sec-edgar|all]"
    exit 1
fi

# Select tfvars file based on environment
TFVARS_FILE="terraform.${ENV}.tfvars"
if [ ! -f "terraform/${TFVARS_FILE}" ]; then
    echo "❌ tfvars file not found: terraform/${TFVARS_FILE}"
    exit 1
fi
echo "📋 Using tfvars: ${TFVARS_FILE}"

# Get ECR repository URL and Lambda function names from Terraform
cd terraform
ECR_REPO=$(terraform output -raw ecr_repository_url 2>/dev/null) || {
    echo "❌ Failed to get ECR repository URL from Terraform"
    echo "Make sure terraform has been applied with -var-file=${TFVARS_FILE}"
    exit 1
}

# Get MCP server function names
SEC_EDGAR_FUNCTION=$(terraform output -raw sec_edgar_mcp_function_name 2>/dev/null) || {
    echo "⚠️ SEC EDGAR MCP function not found in Terraform outputs"
    SEC_EDGAR_FUNCTION=""
}
cd ..

echo "📦 ECR Repository: ${ECR_REPO}"

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

# Update Lambda functions
echo "🔄 Updating MCP server Lambda functions..."

# Update SEC EDGAR MCP Server Lambda
if [[ "$SERVER" == "sec-edgar" || "$SERVER" == "all" ]]; then
    if [ -n "$SEC_EDGAR_FUNCTION" ]; then
        echo "  Updating ${SEC_EDGAR_FUNCTION}..."
        aws lambda update-function-code \
            --function-name ${SEC_EDGAR_FUNCTION} \
            --image-uri ${IMAGE_TAG} \
            --region ${AWS_REGION} \
            --output text > /dev/null

        # Wait for update to complete
        echo "  ⏳ Waiting for Lambda update to complete..."
        aws lambda wait function-updated \
            --function-name ${SEC_EDGAR_FUNCTION} \
            --region ${AWS_REGION}

        # Get Function URL
        FUNCTION_URL=$(aws lambda get-function-url-config \
            --function-name ${SEC_EDGAR_FUNCTION} \
            --region ${AWS_REGION} \
            --query 'FunctionUrl' \
            --output text 2>/dev/null || echo "")

        if [ -n "$FUNCTION_URL" ]; then
            echo "  ✅ SEC EDGAR MCP Server updated"
            echo "  📍 Function URL: ${FUNCTION_URL}"
            echo ""
            echo "  💡 Set environment variable:"
            echo "     SEC_EDGAR_MCP_URL=${FUNCTION_URL}/mcp"
        else
            echo "  ⚠️ Function URL not found (may need to be created via Terraform)"
        fi
    else
        echo "  ⚠️ SEC EDGAR MCP function not found, skipping"
    fi
fi

echo ""
echo "✅ MCP server deployment complete!"
echo ""
echo "📝 Next steps:"
echo "   1. Update environment variables (Doppler) with MCP server URLs"
echo "   2. Test MCP server connectivity"
echo "   3. Verify integration with LangGraph workflow"
