#!/bin/bash
# Deploy Frontend to S3 + CloudFront
# Usage: ./scripts/deploy-frontend.sh [dev|staging|prod]

set -e

ENV=${1:-dev}
PROJECT_NAME="dr-daily-report"
WEBAPP_DIR="frontend/telegram-webapp"

echo "🚀 Deploying frontend to ${ENV}..."

# Validate environment
if [[ ! "$ENV" =~ ^(dev|staging|prod)$ ]]; then
    echo "❌ Invalid environment: $ENV"
    echo "Usage: $0 [dev|staging|prod]"
    exit 1
fi

# Check if webapp directory exists
if [[ ! -d "$WEBAPP_DIR" ]]; then
    echo "❌ Webapp directory not found: $WEBAPP_DIR"
    exit 1
fi

# Select tfvars file based on environment
TFVARS_FILE="terraform.${ENV}.tfvars"
if [ ! -f "terraform/${TFVARS_FILE}" ]; then
    echo "❌ tfvars file not found: terraform/${TFVARS_FILE}"
    exit 1
fi
echo "📋 Using tfvars: ${TFVARS_FILE}"

# Get bucket name and API URL from Terraform outputs
cd terraform
BUCKET=$(terraform output -raw webapp_bucket_name 2>/dev/null) || {
    echo "❌ Failed to get S3 bucket name from Terraform"
    echo "Make sure terraform has been applied first"
    exit 1
}
API_URL=$(terraform output -raw telegram_api_invoke_url 2>/dev/null) || {
    echo "❌ Failed to get API URL from Terraform"
    exit 1
}
DIST_ID=$(terraform output -raw cloudfront_distribution_id 2>/dev/null) || {
    echo "⚠️ CloudFront distribution ID not found, skipping cache invalidation"
    DIST_ID=""
}
cd ..

echo "📦 S3 Bucket: ${BUCKET}"
echo "🔗 API URL: ${API_URL}"

# Create temp directory for build
BUILD_DIR=$(mktemp -d)
trap "rm -rf $BUILD_DIR" EXIT

# Copy webapp files to build directory
cp -r ${WEBAPP_DIR}/* ${BUILD_DIR}/

# Replace API URL placeholder in index.html
echo "🔧 Injecting API URL into index.html..."
sed -i "s|window.TELEGRAM_API_URL = '{{API_URL}}'|window.TELEGRAM_API_URL = '${API_URL}'|g" ${BUILD_DIR}/index.html

# Verify replacement
if grep -q "{{API_URL}}" ${BUILD_DIR}/index.html; then
    echo "⚠️ Warning: API_URL placeholder still found in index.html"
fi

# Sync to S3
echo "📤 Uploading to S3..."
aws s3 sync ${BUILD_DIR}/ s3://${BUCKET}/ \
    --delete \
    --cache-control "max-age=3600" \
    --exclude "*.html" \
    --exclude "*.json"

# Upload HTML files with shorter cache
aws s3 sync ${BUILD_DIR}/ s3://${BUCKET}/ \
    --exclude "*" \
    --include "*.html" \
    --cache-control "max-age=300"

# Upload JSON files (manifest, etc.) with shorter cache
aws s3 sync ${BUILD_DIR}/ s3://${BUCKET}/ \
    --exclude "*" \
    --include "*.json" \
    --cache-control "max-age=300"

echo "✅ Files uploaded to S3"

# Invalidate CloudFront cache
if [[ -n "$DIST_ID" ]]; then
    echo "🔄 Invalidating CloudFront cache..."
    aws cloudfront create-invalidation \
        --distribution-id ${DIST_ID} \
        --paths "/*" \
        --output text > /dev/null

    echo "✅ CloudFront cache invalidation initiated"
fi

# Get CloudFront URL
if [[ -n "$DIST_ID" ]]; then
    cd terraform
    WEBAPP_URL=$(terraform output -raw webapp_url 2>/dev/null) || WEBAPP_URL="https://${DIST_ID}.cloudfront.net"
    cd ..
    echo ""
    echo "🎉 Frontend deployed successfully!"
    echo "🌐 URL: ${WEBAPP_URL}"
else
    echo ""
    echo "🎉 Frontend deployed to S3 successfully!"
    echo "🌐 S3 URL: http://${BUCKET}.s3-website-ap-southeast-1.amazonaws.com"
fi
