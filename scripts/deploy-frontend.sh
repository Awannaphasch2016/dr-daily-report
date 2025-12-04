#!/bin/bash
# Deploy Frontend to S3 + CloudFront
#
# Two-CloudFront Pattern for Zero-Risk Frontend Deployment:
# - TEST CloudFront: Invalidated immediately, E2E tests run against this
# - APP CloudFront: Invalidated only after E2E tests pass, users see this
#
# Usage:
#   ./scripts/deploy-frontend.sh dev              # Full deploy (S3 + both invalidations)
#   ./scripts/deploy-frontend.sh dev --test-only  # S3 + TEST CloudFront only (for CI/CD)
#   ./scripts/deploy-frontend.sh dev --app-only   # APP CloudFront invalidation only (after E2E pass)

set -e

ENV=${1:-dev}
MODE=${2:-full}  # full, --test-only, --app-only
PROJECT_NAME="dr-daily-report"
TWINBAR_DIR="frontend/twinbar"

# Show usage
show_usage() {
    echo "Usage: $0 [dev|staging|prod] [--test-only|--app-only]"
    echo ""
    echo "Modes:"
    echo "  (default)    Full deploy: S3 sync + invalidate TEST + invalidate APP"
    echo "  --test-only  S3 sync + invalidate TEST CloudFront only (for E2E testing)"
    echo "  --app-only   Invalidate APP CloudFront only (after E2E tests pass)"
    echo ""
    echo "Two-CloudFront Pattern:"
    echo "  TEST CloudFront → E2E tests hit this (invalidated first)"
    echo "  APP CloudFront  → Users hit this (invalidated after E2E pass)"
}

# Validate environment
if [[ ! "$ENV" =~ ^(dev|staging|prod)$ ]]; then
    echo "❌ Invalid environment: $ENV"
    show_usage
    exit 1
fi

# Validate mode
if [[ ! "$MODE" =~ ^(full|--test-only|--app-only)$ ]]; then
    echo "❌ Invalid mode: $MODE"
    show_usage
    exit 1
fi

echo "🚀 Deploying frontend to ${ENV} (mode: ${MODE})..."

# Get Terraform outputs
cd terraform

# Get distribution IDs
APP_DIST_ID=$(terraform output -raw cloudfront_distribution_id 2>/dev/null) || {
    echo "⚠️ APP CloudFront distribution ID not found"
    APP_DIST_ID=""
}

TEST_DIST_ID=$(terraform output -raw cloudfront_test_distribution_id 2>/dev/null) || {
    echo "⚠️ TEST CloudFront distribution ID not found"
    TEST_DIST_ID=""
}

# For --app-only mode, we only need to invalidate
if [[ "$MODE" == "--app-only" ]]; then
    if [[ -n "$APP_DIST_ID" ]]; then
        echo "🔄 Invalidating APP CloudFront cache (users will see new frontend)..."
        aws cloudfront create-invalidation \
            --distribution-id ${APP_DIST_ID} \
            --paths "/*" \
            --output text > /dev/null

        WEBAPP_URL=$(terraform output -raw webapp_url 2>/dev/null) || WEBAPP_URL="unknown"
        echo "✅ APP CloudFront cache invalidated"
        echo "🌐 Users now see: ${WEBAPP_URL}"
    else
        echo "❌ APP CloudFront distribution ID not found"
        exit 1
    fi
    cd ..
    exit 0
fi

# For full and --test-only modes, we need to sync files first
BUCKET=$(terraform output -raw webapp_bucket_name 2>/dev/null) || {
    echo "❌ Failed to get S3 bucket name from Terraform"
    echo "Make sure terraform has been applied first"
    exit 1
}
API_URL=$(terraform output -raw telegram_api_invoke_url 2>/dev/null) || {
    echo "❌ Failed to get API URL from Terraform"
    exit 1
}
cd ..

echo "📦 S3 Bucket: ${BUCKET}"
echo "🔗 API URL: ${API_URL}"

# Check if twinbar directory exists
if [[ ! -d "$TWINBAR_DIR" ]]; then
    echo "❌ Twinbar directory not found: $TWINBAR_DIR"
    exit 1
fi

# Build the React app
echo "🔨 Building Twinbar React app..."
cd ${TWINBAR_DIR}

# Install dependencies if node_modules doesn't exist
if [[ ! -d "node_modules" ]]; then
    echo "📦 Installing dependencies..."
    npm install
fi

# Build the app
npm run build

# Set BUILD_DIR to the dist output
BUILD_DIR="$(pwd)/dist"
cd ../..

# Inject API URL into the built index.html
echo "🔧 Injecting API URL into built index.html..."
# Add API URL as a global variable before the closing </head> tag
sed -i "s|</head>|<script>window.TELEGRAM_API_URL = '${API_URL}';</script></head>|g" ${BUILD_DIR}/index.html

echo "✅ Build complete: ${BUILD_DIR}"

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

# Invalidate TEST CloudFront (always for full and --test-only modes)
if [[ -n "$TEST_DIST_ID" ]]; then
    echo "🔄 Invalidating TEST CloudFront cache (for E2E testing)..."
    aws cloudfront create-invalidation \
        --distribution-id ${TEST_DIST_ID} \
        --paths "/*" \
        --output text > /dev/null

    cd terraform
    TEST_URL=$(terraform output -raw webapp_test_url 2>/dev/null) || TEST_URL="unknown"
    cd ..
    echo "✅ TEST CloudFront cache invalidated"
    echo "🧪 E2E test URL: ${TEST_URL}"
fi

# For --test-only mode, stop here (don't invalidate APP)
if [[ "$MODE" == "--test-only" ]]; then
    echo ""
    echo "⏸️  Paused before APP invalidation (--test-only mode)"
    echo "   Run E2E tests against TEST URL, then run:"
    echo "   $0 $ENV --app-only"
    exit 0
fi

# For full mode, also invalidate APP CloudFront
if [[ -n "$APP_DIST_ID" ]]; then
    echo "🔄 Invalidating APP CloudFront cache (users will see new frontend)..."
    aws cloudfront create-invalidation \
        --distribution-id ${APP_DIST_ID} \
        --paths "/*" \
        --output text > /dev/null

    cd terraform
    WEBAPP_URL=$(terraform output -raw webapp_url 2>/dev/null) || WEBAPP_URL="unknown"
    cd ..
    echo "✅ APP CloudFront cache invalidated"
fi

echo ""
echo "🎉 Frontend deployed successfully!"
echo "🧪 TEST URL (E2E): ${TEST_URL:-N/A}"
echo "🌐 APP URL (Users): ${WEBAPP_URL:-N/A}"
