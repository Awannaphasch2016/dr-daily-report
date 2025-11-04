# Deployment commands
# Note: Recipes run from justfile-modules/, so paths use ../

# Create Lambda deployment package
build:
    @cd .. && bash scripts/deploy.sh

# Create minimal Lambda deployment package
build-minimal:
    @cd .. && bash scripts/create_lambda_minimal.sh

# Create Lambda deployment package (alternative script)
build-lambda:
    @cd .. && bash scripts/create_lambda.sh

# Deploy to AWS Lambda (requires AWS CLI configured)
deploy-lambda:
    @cd .. && bash scripts/create_lambda.sh

# Setup LINE webhook configuration helper
setup-webhook:
    @cd .. && bash scripts/setup_line_webhook.sh

# Clean build artifacts
clean-build:
    @cd .. && rm -rf build/
    @cd .. && rm -f *.zip
    @echo "? Build artifacts cleaned"

# Clean Python cache files
clean-pycache:
    @cd .. && find . -type d -name "__pycache__" -exec rm -r {} + 2>/dev/null || true
    @cd .. && find . -type f -name "*.pyc" -delete 2>/dev/null || true
    @echo "? Python cache cleaned"

# Clean all: pycache, build artifacts, test artifacts
clean-all:
    @cd .. && rm -rf build/
    @cd .. && rm -f *.zip
    @cd .. && find . -type d -name "__pycache__" -exec rm -r {} + 2>/dev/null || true
    @cd .. && find . -type f -name "*.pyc" -delete 2>/dev/null || true
    @cd .. && rm -rf .pytest_cache/
    @cd .. && rm -rf .coverage htmlcov/
    @echo "? All cleaned"