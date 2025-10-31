#!/bin/bash

# Deployment script for LINE Bot Lambda Function

echo "🚀 Starting deployment process..."

# Create deployment package directory
echo "📦 Creating deployment package..."
rm -rf build/deployment_package
mkdir -p build/deployment_package

# Install dependencies
echo "📥 Installing dependencies..."
pip install -r requirements.txt -t build/deployment_package/

# Copy application files
echo "📋 Copying application files..."
cp -r src/* build/deployment_package/
cp data/tickers.csv build/deployment_package/

# Create deployment package
echo "📦 Creating ZIP file..."
cd build/deployment_package
zip -r ../lambda_deployment.zip . -q
cd ../..

echo "✅ Deployment package created: lambda_deployment.zip"
echo ""
echo "📝 Next steps:"
echo ""
echo "For LINE Bot handler:"
echo "1. Upload lambda_deployment.zip to AWS Lambda"
echo "2. Set handler to: lambda_handler.lambda_handler"
echo "3. Configure environment variables:"
echo "   - OPENAI_API_KEY"
echo "   - LINE_CHANNEL_ACCESS_TOKEN"
echo "   - LINE_CHANNEL_SECRET"
echo "4. Set timeout to at least 60 seconds"
echo "5. Set memory to at least 512 MB"
echo "6. Configure API Gateway as trigger for /webhook (POST)"
echo ""
echo "For REST API handler:"
echo "1. Upload lambda_deployment.zip to AWS Lambda (or create new function)"
echo "2. Set handler to: api_handler.api_handler"
echo "3. Configure environment variables:"
echo "   - OPENAI_API_KEY (only)"
echo "4. Set timeout to at least 60 seconds"
echo "5. Set memory to at least 512 MB"
echo "6. Configure API Gateway REST API with /analyze (GET) route"
echo ""
echo "🎉 Done!"
