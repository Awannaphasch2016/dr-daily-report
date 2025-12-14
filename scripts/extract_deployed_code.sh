#!/bin/bash
# scripts/extract_deployed_code.sh
#
# Purpose: Extract entire codebase from deployed Lambda Docker image
# Usage: ./scripts/extract_deployed_code.sh [function-name] [output-dir]

set -e  # Exit on error

# Configuration
FUNCTION_NAME="${1:-dr-daily-report-ticker-fetcher-dev}"
OUTPUT_DIR="${2:-/tmp/deployed-code}"
AWS_REGION="ap-southeast-1"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo "=========================================="
echo "  Extract Deployed Lambda Code"
echo "=========================================="
echo ""

# Step 1: Get deployed image URI
echo "📋 Function: $FUNCTION_NAME"
echo "📂 Output:   $OUTPUT_DIR"
echo ""

echo -n "🔍 Getting deployed image URI... "
DEPLOYED_IMAGE=$(aws lambda get-function \
  --function-name "$FUNCTION_NAME" \
  --region "$AWS_REGION" \
  --query 'Code.ImageUri' \
  --output text 2>/dev/null)

if [ -z "$DEPLOYED_IMAGE" ]; then
  echo -e "${RED}ERROR${NC}"
  echo "Could not find Lambda function: $FUNCTION_NAME"
  exit 1
fi

echo -e "${GREEN}OK${NC}"
echo "   Image: $DEPLOYED_IMAGE"
echo ""

# Step 2: Login to ECR
echo -n "🔐 Logging in to ECR... "
aws ecr get-login-password --region "$AWS_REGION" | \
  docker login --username AWS --password-stdin \
  $(echo "$DEPLOYED_IMAGE" | cut -d'/' -f1) >/dev/null 2>&1

if [ $? -eq 0 ]; then
  echo -e "${GREEN}OK${NC}"
else
  echo -e "${RED}FAILED${NC}"
  exit 1
fi
echo ""

# Step 3: Pull image
echo "📥 Pulling Docker image..."
docker pull "$DEPLOYED_IMAGE"
echo ""

# Step 4: Clean output directory
if [ -d "$OUTPUT_DIR" ]; then
  echo -n "🗑️  Cleaning existing output directory... "
  rm -rf "$OUTPUT_DIR"
  echo -e "${GREEN}OK${NC}"
fi

mkdir -p "$OUTPUT_DIR"
echo ""

# Step 5: Extract code
echo "📦 Extracting codebase from image..."
docker run --rm \
  -v "$OUTPUT_DIR:/output" \
  "$DEPLOYED_IMAGE" \
  sh -c "cp -r /var/task/* /output/"

if [ $? -eq 0 ]; then
  echo -e "${GREEN}✅ Extraction complete!${NC}"
else
  echo -e "${RED}❌ Extraction failed${NC}"
  exit 1
fi
echo ""

# Step 6: Show summary
echo "=========================================="
echo "  Summary"
echo "=========================================="
echo ""
echo "📂 Deployed code extracted to:"
echo "   $OUTPUT_DIR"
echo ""

# Count files
TOTAL_FILES=$(find "$OUTPUT_DIR" -type f | wc -l)
PYTHON_FILES=$(find "$OUTPUT_DIR" -name "*.py" | wc -l)

echo "📊 Statistics:"
echo "   Total files:  $TOTAL_FILES"
echo "   Python files: $PYTHON_FILES"
echo ""

# List handler files
echo "🔧 Handler files found:"
for handler in $(find "$OUTPUT_DIR/src/scheduler" -name "*_handler.py" 2>/dev/null); do
  HANDLER_NAME=$(basename "$handler")
  LINE_COUNT=$(wc -l < "$handler")
  echo "   ├─ $HANDLER_NAME ($LINE_COUNT lines)"
done
echo ""

# Show directory structure
echo "📁 Directory structure:"
cd "$OUTPUT_DIR"
if command -v tree >/dev/null 2>&1; then
  tree -L 2 -d --dirsfirst | head -20
else
  find . -maxdepth 2 -type d | grep -v "^\.$" | sed 's|^\./|   |' | sort
fi
echo ""

# Helpful commands
echo "=========================================="
echo "  Next Steps"
echo "=========================================="
echo ""
echo "Browse code:"
echo "  cd $OUTPUT_DIR"
echo ""
echo "Open in editor:"
echo "  code $OUTPUT_DIR"
echo "  vim $OUTPUT_DIR/src/scheduler/ticker_fetcher_handler.py"
echo ""
echo "Compare with local:"
echo "  diff -r $OUTPUT_DIR/src src/"
echo ""
echo "Search for specific code:"
echo "  grep -r 'yfinance' $OUTPUT_DIR/src"
echo ""
