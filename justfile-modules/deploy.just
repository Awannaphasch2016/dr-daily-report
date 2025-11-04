# Deployment Module
# Commands for deployment operations

# Create Lambda deployment package
deploy-lambda:
    @echo "📦 Creating Lambda deployment package..."
    ./scripts/create_lambda.sh

# Create minimal Lambda deployment
deploy-lambda-minimal:
    @echo "📦 Creating minimal Lambda deployment..."
    ./scripts/create_lambda_minimal.sh

# Deploy to Lambda
deploy:
    @echo "🚀 Deploying..."
    ./scripts/deploy.sh
