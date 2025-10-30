#!/bin/bash

# Create Lambda function with environment variables from Doppler

echo "🚀 Creating Lambda function..."

# Create function
aws lambda create-function \
  --function-name line-bot-ticker-report \
  --runtime python3.11 \
  --role arn:aws:iam::755283537543:role/dev-default-lambda-execution-role \
  --handler lambda_handler.lambda_handler \
  --code S3Bucket=line-bot-ticker-deploy-20251030,S3Key=lambda_deployment.zip \
  --timeout 60 \
  --memory-size 512 \
  --environment "Variables={OPENAI_API_KEY=$OPENAI_API_KEY,LINE_CHANNEL_ACCESS_TOKEN=$LINE_CHANNEL_ACCESS_TOKEN,LINE_CHANNEL_SECRET=$LINE_CHANNEL_SECRET}" \
  --description "LINE Bot for Financial Ticker Reports in Thai"

echo ""
echo "✅ Lambda function created!"
