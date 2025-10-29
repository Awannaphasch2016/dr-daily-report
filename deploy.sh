#!/bin/bash

# Deployment script for LINE Bot Lambda Function

echo "🚀 Starting deployment process..."

# Create deployment package directory
echo "📦 Creating deployment package..."
rm -rf deployment_package
mkdir -p deployment_package

# Install dependencies
echo "📥 Installing dependencies..."
pip install -r requirements.txt -t deployment_package/

# Copy application files
echo "📋 Copying application files..."
cp lambda_handler.py deployment_package/
cp line_bot.py deployment_package/
cp agent.py deployment_package/
cp data_fetcher.py deployment_package/
cp technical_analysis.py deployment_package/
cp database.py deployment_package/
cp vector_store.py deployment_package/
cp config.py deployment_package/
cp tickers.csv deployment_package/

# Create deployment package
echo "📦 Creating ZIP file..."
cd deployment_package
zip -r ../lambda_deployment.zip . -q
cd ..

echo "✅ Deployment package created: lambda_deployment.zip"
echo ""
echo "📝 Next steps:"
echo "1. Upload lambda_deployment.zip to AWS Lambda"
echo "2. Set handler to: lambda_handler.lambda_handler"
echo "3. Configure environment variables:"
echo "   - OPENAI_API_KEY"
echo "   - LINE_CHANNEL_ACCESS_TOKEN"
echo "   - LINE_CHANNEL_SECRET"
echo "4. Set timeout to at least 60 seconds"
echo "5. Set memory to at least 512 MB"
echo "6. Configure API Gateway as trigger"
echo ""
echo "🎉 Done!"
