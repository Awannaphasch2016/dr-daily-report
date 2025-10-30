# Lambda Deployment - Size Issue Resolution

## Problem

The deployment package unzipped size exceeds AWS Lambda's 250MB limit.

**Current situation**:
- Deployment ZIP: 88 MB
- Unzipped size: ~300+ MB (too large!)
- Limit: 250 MB unzipped

## Solutions

### Option 1: Use Docker Container Image (RECOMMENDED)

AWS Lambda supports container images up to 10GB. This is the best approach for this bot.

**Steps**:

1. **Create Dockerfile**:
```dockerfile
FROM public.ecr.aws/lambda/python:3.11

# Copy requirements
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy application code
COPY lambda_handler.py agent.py line_bot.py data_fetcher.py technical_analysis.py database.py vector_store.py config.py tickers.csv ./

# Set handler
CMD ["lambda_handler.lambda_handler"]
```

2. **Build and Push**:
```bash
# Build image
docker build -t line-bot-ticker-report .

# Tag for ECR
aws ecr create-repository --repository-name line-bot-ticker-report
docker tag line-bot-ticker-report:latest 755283537543.dkr.ecr.us-east-1.amazonaws.com/line-bot-ticker-report:latest

# Push to ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin 755283537543.dkr.ecr.us-east-1.amazonaws.com
docker push 755283537543.dkr.ecr.us-east-1.amazonaws.com/line-bot-ticker-report:latest

# Create Lambda from container
aws lambda create-function \
  --function-name line-bot-ticker-report \
  --package-type Image \
  --code ImageUri=755283537543.dkr.ecr.us-east-1.amazonaws.com/line-bot-ticker-report:latest \
  --role arn:aws:iam::755283537543:role/dev-default-lambda-execution-role \
  --timeout 60 \
  --memory-size 512
```

### Option 2: Use Lambda Layers

Split heavy dependencies into layers.

**Not recommended** for this project because:
- Still might exceed limits with all dependencies
- More complex to maintain
- Container approach is cleaner

### Option 3: Reduce Dependencies

Remove unused packages from requirements.txt:
- Remove Flask (only needed for local testing)
- Consider lighter alternatives

**Trade-offs**:
- May break local testing
- Limited savings (~10MB)

## Recommendation

**Use Option 1 (Docker Container)**

This is the modern, recommended approach for Lambda functions with large dependencies.

### Quick Start with Docker

Run this script to deploy:

```bash
# File: deploy_container.sh

#!/bin/bash

echo "🐳 Building Docker container for Lambda..."

# Create Dockerfile
cat > Dockerfile <<'EOF'
FROM public.ecr.aws/lambda/python:3.11

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY lambda_handler.py agent.py line_bot.py data_fetcher.py \
     technical_analysis.py database.py vector_store.py config.py \
     tickers.csv ./

# Set handler
CMD ["lambda_handler.lambda_handler"]
EOF

# Build
docker build -t line-bot-ticker-report .

# Create ECR repository
aws ecr create-repository --repository-name line-bot-ticker-report 2>/dev/null || true

# Get account ID and region
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
REGION=us-east-1

# Login to ECR
aws ecr get-login-password --region $REGION | \
  docker login --username AWS --password-stdin \
  $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com

# Tag and push
docker tag line-bot-ticker-report:latest \
  $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/line-bot-ticker-report:latest

docker push $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/line-bot-ticker-report:latest

# Create or update Lambda function
aws lambda create-function \
  --function-name line-bot-ticker-report \
  --package-type Image \
  --code ImageUri=$ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/line-bot-ticker-report:latest \
  --role arn:aws:iam::$ACCOUNT_ID:role/dev-default-lambda-execution-role \
  --timeout 60 \
  --memory-size 512 \
  --environment "Variables={OPENAI_API_KEY=$OPENAI_API_KEY,LINE_CHANNEL_ACCESS_TOKEN=$LINE_CHANNEL_ACCESS_TOKEN,LINE_CHANNEL_SECRET=$LINE_CHANNEL_SECRET}" \
  2>/dev/null || \
aws lambda update-function-code \
  --function-name line-bot-ticker-report \
  --image-uri $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/line-bot-ticker-report:latest

echo "✅ Deployment complete!"
```

## Current Status

✅ Deployment package created (88 MB)
✅ Uploaded to S3
❌ Direct Lambda deployment failed (size limit)
⏳ Next: Deploy using Docker container

## Do you want me to create the Docker deployment?

Just say "yes" and I'll create the Dockerfile and deployment script for you!
