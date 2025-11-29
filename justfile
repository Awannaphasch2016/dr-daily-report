# DR Daily Report - Intent-Based Justfile
#
# This justfile provides intent-based recipes that describe WHEN and WHY
# you should run commands. Each recipe calls the `dr` CLI which provides
# the clean syntax and implementation details.
#
# Architecture:
#   Justfile (this file) = Descriptive layer (INTENT)
#   dr CLI              = Implementation layer (SYNTAX)
#
# For detailed CLI help: dr --help
# For command-specific help: dr <command> --help

# Show all available recipes
default:
    @just --list

# === DEVELOPMENT WORKFLOWS ===

# Start local development server (use when developing locally)
dev:
    @echo "🚀 Starting development server..."
    dr --doppler dev server

# Quick development setup (first time or after pulling changes)
setup:
    @echo "📦 Installing dependencies..."
    dr dev install
    @echo "✅ Setup complete! Run 'just dev' to start the server."

# Run interactive Python shell (when you need to test code interactively)
shell:
    dr --doppler dev shell

# Verify development environment (run when setting up or debugging issues)
verify:
    @echo "🔍 Verifying development environment..."
    dr dev verify

# === TELEGRAM MINI APP DEVELOPMENT ===

# Verify Telegram Mini App development setup
verify-telegram:
    @echo "🔍 Verifying Telegram Mini App setup..."
    dr dev verify telegram

# Start FastAPI server with local DynamoDB (for Telegram Mini App development)
dev-api:
    @echo "🚀 Starting FastAPI with local DynamoDB..."
    ./scripts/start_local_api.sh

# Create DynamoDB tables in local DynamoDB (run once before dev-api)
setup-local-db:
    @echo "🔧 Creating local DynamoDB tables..."
    @echo "Checking if Docker is running..."
    @if ! docker ps > /dev/null 2>&1; then \
        echo "❌ Docker is not running. Please start Docker first."; \
        exit 1; \
    fi
    @echo "Checking if DynamoDB Local container exists..."
    @if ! docker ps -a | grep -q dynamodb-local; then \
        echo "📦 Starting DynamoDB Local container..."; \
        docker run -d -p 8000:8000 --name dynamodb-local amazon/dynamodb-local; \
    elif ! docker ps | grep -q dynamodb-local; then \
        echo "▶️  Starting existing DynamoDB Local container..."; \
        docker start dynamodb-local; \
    else \
        echo "✅ DynamoDB Local is already running"; \
    fi
    @sleep 2
    @echo "Creating tables (using doppler for consistent credentials)..."
    doppler run -- python scripts/create_local_dynamodb_tables.py
    @echo ""
    @echo "Verifying tables..."
    @doppler run -- aws dynamodb list-tables --endpoint-url http://localhost:8000 --region ap-southeast-1 | jq -r '.TableNames[]'

# Test watchlist endpoints (requires dev-api running in another terminal)
test-watchlist:
    @echo "🧪 Testing watchlist endpoints..."
    ./scripts/test_watchlist.sh

# Test rankings endpoints (requires dev-api running in another terminal)
test-rankings:
    @echo "🧪 Testing rankings endpoints..."
    ./scripts/test_rankings.sh

# Alias for setup-local-db (clearer naming)
setup-local-dynamodb: setup-local-db

# Stop local DynamoDB container
stop-local-db:
    @echo "🛑 Stopping DynamoDB Local..."
    docker stop dynamodb-local || true

# === TESTING WORKFLOWS ===

# Run this when you want to test your recent changes
test-changes:
    @echo "🧪 Running tests..."
    dr test

# Run this before committing to ensure nothing is broken
pre-commit:
    @echo "🔍 Pre-commit checks..."
    dr check syntax
    dr test
    @echo "✅ All checks passed! Safe to commit."

# Test specific functionality by file name
test-file FILE:
    dr test file {{FILE}}

# Test LINE bot specific features (follow, help, error, fuzzy, cache)
test-line TYPE:
    dr test line {{TYPE}}

# Test with a real ticker symbol (for integration testing)
test-ticker TICKER:
    dr test integration {{TICKER}}

# === BUILD & DEPLOYMENT ===

# Build deployment package (when preparing to deploy)
build:
    @echo "📦 Building deployment package..."
    dr build

# Build minimal package (for faster Lambda cold starts)
build-minimal:
    @echo "📦 Building minimal package..."
    dr build --minimal

# Deploy to production (requires AWS credentials configured)
deploy-prod:
    @echo "🚀 Deploying to AWS Lambda..."
    @echo "⚠️  Make sure you have AWS credentials configured!"
    dr --doppler deploy lambda-deploy

# Complete deploy workflow (build + deploy)
ship-it:
    @echo "🚢 Building and deploying..."
    just build
    just deploy-prod
    @echo "✅ Deployment complete!"

# Setup LINE webhook (run after deploying Lambda function)
setup-webhook:
    @echo "🔗 Setting up LINE webhook..."
    dr --doppler deploy webhook

# === TELEGRAM MINI APP DEPLOYMENT ===

# Deploy Telegram backend Lambda functions
deploy-telegram-backend ENV="dev":
    @echo "🚀 Deploying Telegram backend to {{ENV}}..."
    ./scripts/deploy-backend.sh {{ENV}}

# Deploy Telegram frontend to S3/CloudFront
deploy-telegram-frontend ENV="dev":
    @echo "🚀 Deploying Telegram frontend to {{ENV}}..."
    ./scripts/deploy-frontend.sh {{ENV}}

# Deploy full Telegram Mini App (backend + frontend)
deploy-telegram ENV="dev":
    @echo "🚀 Deploying full Telegram Mini App to {{ENV}}..."
    just deploy-telegram-backend {{ENV}}
    just deploy-telegram-frontend {{ENV}}
    @echo "✅ Telegram Mini App deployed!"

# Run Terraform plan for Telegram infrastructure (with Doppler secrets)
# Validates that placeholder values are overridden by Doppler TF_VAR_* env vars
tf-plan:
    @echo "📋 Running Terraform plan with Doppler..."
    cd terraform && doppler run -- terraform plan -var-file=terraform.tfvars -out=tfplan
    @echo "✅ Plan saved to terraform/tfplan. Review and run 'just tf-apply' to apply."

# Apply Terraform changes (requires tf-plan to be run first)
tf-apply:
    @test -f terraform/tfplan || (echo "❌ Run 'just tf-plan' first to create a plan" && exit 1)
    @echo "🔧 Applying Terraform plan..."
    cd terraform && doppler run -- terraform apply tfplan
    @rm -f terraform/tfplan
    @echo "✅ Terraform applied successfully!"

# Verify Lambda has no placeholder values after deployment
tf-verify-lambda FUNCTION="dr-daily-report-telegram-api-dev":
    @echo "🔍 Verifying Lambda environment variables..."
    @aws lambda get-function-configuration --function-name {{FUNCTION}} \
        --query 'Environment.Variables' | grep -q "placeholder" && \
        (echo "❌ ERROR: Placeholder found in Lambda!" && exit 1) || \
        echo "✅ No placeholders found in Lambda"

# === GITHUB ACTIONS LOCAL TESTING (TDD) ===

# Validate GitHub Actions workflows (static analysis - fast)
ci-lint:
    @echo "🔍 Running actionlint on workflows..."
    ~/.local/bin/actionlint .github/workflows/deploy.yml
    ~/.local/bin/actionlint .github/workflows/pr-check.yml
    @echo "✅ All workflows pass actionlint"

# Dry-run GitHub Actions locally (test without executing)
ci-dryrun JOB="environment":
    @echo "🔄 Dry-running job: {{JOB}}..."
    ~/.local/bin/act push -j {{JOB}} --dryrun

# Run GitHub Actions job locally (requires Docker)
ci-run JOB="test":
    @echo "🚀 Running job: {{JOB}} locally..."
    ~/.local/bin/act push -j {{JOB}}

# List all jobs in workflows
ci-list:
    @~/.local/bin/act --list

# Full CI/CD TDD workflow (lint → dryrun → run test job)
ci-test:
    @echo "🧪 Running CI/CD TDD workflow..."
    just ci-lint
    just ci-dryrun environment
    just ci-dryrun test
    @echo "✅ CI/CD validation complete!"

# Legacy aliases (for backwards compatibility)
terraform-plan: tf-plan
terraform-apply: tf-apply

# === CLEANUP ===

# Quick cleanup (remove build artifacts only)
clean:
    dr clean build

# Deep cleanup (remove all generated files including cache)
deep-clean:
    @echo "🧹 Deep cleaning..."
    dr clean all
    @echo "✅ All artifacts removed"

# === CODE QUALITY ===

# Check if your code has syntax errors
check:
    dr check syntax

# Format code with black (before committing)
format:
    @echo "✨ Formatting code..."
    dr check format

# Lint code for potential issues
lint:
    dr check lint

# Check if environment variables are properly set
check-env:
    dr check env

# === UTILITIES ===

# Show project structure
tree:
    dr util tree

# Show code statistics
stats:
    dr util stats

# Generate report for a specific ticker
report TICKER:
    @echo "📊 Generating report for {{TICKER}}..."
    dr --doppler util report {{TICKER}}

# Show quick reference info
info:
    dr util info

# === LANGSMITH ===

# List recent LangSmith traces
langsmith-runs:
    @echo "📊 Fetching recent LangSmith traces..."
    dr --doppler langsmith list-runs

# Show detailed information for a specific trace
langsmith-run RUN_ID:
    @echo "📊 Fetching trace details for {{RUN_ID}}..."
    dr --doppler langsmith show-run {{RUN_ID}}

# Show feedback for a specific trace
langsmith-feedback RUN_ID:
    @echo "📊 Fetching feedback for trace {{RUN_ID}}..."
    dr --doppler langsmith show-feedback {{RUN_ID}}

# Show LangSmith statistics
langsmith-stats:
    @echo "📈 Calculating LangSmith statistics..."
    dr --doppler langsmith stats

# List available LangSmith projects
langsmith-projects:
    @echo "📂 Listing LangSmith projects..."
    dr --doppler langsmith projects

# === COMMON WORKFLOWS ===

# Daily development routine (pull, setup, test)
daily:
    @echo "📅 Running daily routine..."
    git pull
    just setup
    just test-changes
    @echo "✅ Ready to code!"

# Pre-deployment checklist (test, build, verify)
pre-deploy:
    @echo "📋 Running pre-deployment checks..."
    just test-changes
    just check
    just build
    @echo "✅ Ready to deploy! Run 'just deploy-prod' when ready."

# Quick reset (clean and reinstall)
reset:
    @echo "🔄 Resetting environment..."
    just deep-clean
    just setup
    @echo "✅ Environment reset complete"
