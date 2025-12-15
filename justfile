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

# Deployment gate tests (must pass before deploying Telegram Mini App)
test-deploy:
    @echo "🧪 Running deployment gate tests..."
    @echo "   These tests must pass before deploying to production."
    pytest tests/telegram tests/shared -m "not integration and not e2e and not smoke" -v --tb=short
    @echo "✅ Deployment gate tests passed!"

# LINE Bot test suite (for LINE Bot development)
test-line-all:
    @echo "🧪 Running LINE Bot tests..."
    pytest tests/line_bot tests/shared -m "not integration and not e2e" -v --tb=short
    @echo "✅ LINE Bot tests passed!"

# === TIER-BASED TESTING ===
# Tiers are compositions of markers (see conftest.py for details)
# Tier 0: Unit tests only
# Tier 1: Unit + mocked (default, same as 'pytest')
# Tier 2: + integration (requires API keys)
# Tier 3: + smoke (requires running server)
# Tier 4: + e2e (requires browser)

# Fastest possible test run (unit tests only)
test-tier0:
    @echo "🧪 Running tier 0 (unit tests only)..."
    pytest --tier=0 tests/shared tests/telegram -v --tb=short
    @echo "✅ Tier 0 tests passed!"

# Default test tier (unit + mocked, equivalent to just 'pytest')
test-tier1:
    @echo "🧪 Running tier 1 (unit + mocked)..."
    pytest --tier=1 tests/shared tests/telegram -v --tb=short
    @echo "✅ Tier 1 tests passed!"

# Integration tests (requires OPENROUTER_API_KEY)
test-tier2:
    @echo "🧪 Running tier 2 (+ integration tests)..."
    @echo "   ℹ️  Requires OPENROUTER_API_KEY"
    doppler run -- pytest --tier=2 tests/shared tests/telegram -v --tb=short
    @echo "✅ Tier 2 tests passed!"

# Smoke tests (requires running API server)
test-tier3:
    @echo "🧪 Running tier 3 (+ smoke tests)..."
    @echo "   ℹ️  Requires running API server (just dev-api)"
    pytest --tier=3 tests/telegram/test_smoke.py -v --tb=short
    @echo "✅ Tier 3 tests passed!"

# E2E tests (requires browser)
test-tier4:
    @echo "🧪 Running tier 4 (+ e2e browser tests)..."
    @echo "   ℹ️  Requires Playwright: playwright install chromium"
    pytest --tier=4 tests/e2e -v --tb=short
    @echo "✅ Tier 4 tests passed!"

# === LAMBDA RIE TESTING (Pre-Deployment Validation) ===
# Test Lambda handlers in actual Lambda container using Runtime Interface Emulator
# This catches import errors BEFORE deployment to AWS

# Start Lambda containers locally with RIE (for testing handlers)
lambda-up:
    @echo "🚀 Starting Lambda RIE containers..."
    @echo "   report-worker: http://localhost:9001"
    @echo "   telegram-api:  http://localhost:9002"
    @echo "   line-bot:      http://localhost:9003"
    docker-compose -f docker-compose.lambda.yml up -d report-worker telegram-api line-bot
    @echo "⏳ Waiting for containers to be ready..."
    @sleep 5
    @echo "✅ Lambda containers ready for testing!"

# Stop Lambda RIE containers
lambda-down:
    @echo "🛑 Stopping Lambda RIE containers..."
    docker-compose -f docker-compose.lambda.yml down
    @echo "✅ Containers stopped"

# Test Lambda handlers using RIE (catches import errors before deployment)
test-lambda:
    @echo "🧪 Testing Lambda handlers in RIE containers..."
    @echo "   This validates handlers import correctly in Lambda environment"
    @echo ""
    @if ! docker ps | grep -q report-worker; then \
        echo "⚠️  Containers not running. Starting them..."; \
        just lambda-up; \
    fi
    pytest tests/lambda_rie/ -v --tier=2
    @echo ""
    @echo "✅ Lambda RIE tests passed!"

# Full Lambda validation workflow: build → test → cleanup
test-lambda-full:
    @echo "🔍 Full Lambda validation workflow..."
    @echo ""
    @echo "1️⃣  Building Lambda container image..."
    docker build -f Dockerfile.lambda.container -t lambda-local-test .
    @echo ""
    @echo "2️⃣  Starting RIE containers..."
    just lambda-up
    @echo ""
    @echo "3️⃣  Running import validation tests..."
    pytest tests/lambda_rie/ -v --tier=2
    @echo ""
    @echo "4️⃣  Cleaning up..."
    just lambda-down
    @echo ""
    @echo "✅ Full Lambda validation passed!"

# Quick check: Verify handlers can import in Lambda container
lambda-check:
    @echo "⚡ Quick Lambda import check..."
    @docker build -q -f Dockerfile.lambda.container -t lambda-quick-test . > /dev/null
    @docker run --rm -e PYTHONPATH=/var/task --entrypoint sh lambda-quick-test -c "python3 scripts/test_lambda_imports.py"

# === AURORA DATABASE INTERACTION ===

# Start SSM port forwarding to Aurora (run in background, keep terminal open)
aurora-tunnel:
    @echo "🔌 Starting SSM tunnel to Aurora..."
    @echo "   Local port: 3307"
    @echo "   Remote: dr-daily-report-aurora-dev"
    @echo ""
    @echo "⚠️  Keep this terminal open while using Aurora"
    @echo "   Press Ctrl+C to stop the tunnel"
    @echo ""
    aws ssm start-session \
      --target i-0dab21bdf83ce9aaf \
      --document-name AWS-StartPortForwardingSessionToRemoteHost \
      --parameters '{"host":["dr-daily-report-aurora-dev.cluster-c9a0288e4hqm.ap-southeast-1.rds.amazonaws.com"],"portNumber":["3306"],"localPortNumber":["3307"]}' \
      --region ap-southeast-1

# Explore Aurora database with VisiData (requires aurora-tunnel running in another terminal)
aurora-vd *ARGS:
    @echo "⚠️  DEPRECATED: Use 'just aurora-query \"SELECT ...\" --output vd' instead"
    @echo ""
    @echo "Example:"
    @echo "   just aurora-query \"SELECT * FROM ticker_master\" --output vd"
    @echo ""
    @exit 1

# Run SQL query against Aurora (requires aurora-tunnel running in another terminal)
aurora-query QUERY *FLAGS:
    #!/usr/bin/env bash
    set -euo pipefail

    # Check tunnel
    if ! nc -z 127.0.0.1 3307 2>/dev/null; then
        echo "❌ SSM tunnel not running. Run: just aurora-tunnel"
        exit 1
    fi

    # Parse output flag
    output="table"
    if echo "{{FLAGS}}" | grep -q "\--output"; then
        output=$(echo "{{FLAGS}}" | sed -n 's/.*--output[= ]\([^ ]*\).*/\1/p')
    fi

    # Execute query with selected output format
    if [ "$output" = "vd" ]; then
        echo "📊 Opening in VisiData..." >&2
        mysql -h 127.0.0.1 -P 3307 -u admin -pAuroraDevDb2025SecureX1 \
            ticker_data --batch -e "{{QUERY}}" 2>/dev/null | vd -f tsv
    else
        echo "📝 Query: {{QUERY}}"
        echo ""
        mysql -h 127.0.0.1 -P 3307 -u admin -pAuroraDevDb2025SecureX1 \
            ticker_data -e "{{QUERY}}"
    fi

# === PROMOTION PIPELINE ===
# Validates tests pass in order: local → dev → staging → prod
# Each stage must pass before promoting to the next environment

# Full promotion validation pipeline (all 4 stages)
promote:
    @echo "🚀 Running full promotion validation pipeline..."
    @echo "   local → dev → staging → prod"
    @echo ""
    just promote-local
    just promote-dev
    just promote-staging
    just promote-prod
    @echo ""
    @echo "✅ All promotion gates passed! Ready to deploy."

# Stage 1: Local (no external resources, fastest)
promote-local:
    @echo "📍 Stage 1: Local validation (tier 1)..."
    pytest --tier=1 tests/shared tests/telegram -v --tb=short
    @echo "✅ Local tests passed!"

# Stage 2: Dev (requires API keys from Doppler dev_personal)
promote-dev:
    @echo "📍 Stage 2: Dev validation (tier 2 + integration)..."
    @echo "   Using Doppler config: dev_personal"
    doppler run -c dev_personal -- pytest --tier=2 tests/shared tests/telegram -v --tb=short
    @echo "✅ Dev integration tests passed!"

# Stage 3: Staging (smoke tests against staging API)
promote-staging:
    @echo "📍 Stage 3: Staging validation (tier 3 + smoke)..."
    @echo "   Using Doppler config: stg"
    doppler run -c stg -- pytest --tier=3 tests/telegram/test_smoke.py -v
    @echo "✅ Staging smoke tests passed!"

# Stage 4: Prod (read-only smoke tests against prod API)
promote-prod:
    @echo "📍 Stage 4: Production validation (read-only smoke)..."
    @echo "   Using Doppler config: prd"
    @echo "   ⚠️  Running only read-only tests (health, search, rankings)"
    doppler run -c prd -- pytest --tier=3 tests/telegram/test_smoke.py -v -m "readonly"
    @echo "✅ Production smoke tests passed!"

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

# === TERRAFORM MULTI-ENVIRONMENT ===
# Uses directory structure for environment separation (not workspaces)
# See: terraform/envs/{dev,staging,prod}/backend.hcl and terraform.tfvars
#
# Usage:
#   just tf-init dev       # Initialize with dev backend config
#   just tf-plan dev       # Plan changes for dev
#   just tf-apply dev      # Apply changes to dev
#   just tf-destroy staging # Destroy staging (with confirmation)

# Initialize Terraform for a specific environment
tf-init ENV:
    @echo "🔧 Initializing Terraform for {{ENV}}..."
    cd terraform && terraform init -backend-config=envs/{{ENV}}/backend.hcl -reconfigure
    @echo "✅ Terraform initialized for {{ENV}}"

# Helper to map environment name to Doppler config
# dev → dev_personal, staging → stg, prod → prd
_doppler-config ENV:
    #!/bin/bash
    case "{{ENV}}" in
        dev) echo "dev_personal" ;;
        staging) echo "stg" ;;
        prod) echo "prd" ;;
        *) echo "{{ENV}}" ;;
    esac

# Run Terraform plan for a specific environment (with Doppler secrets)
tf-plan ENV:
    #!/bin/bash
    set -e
    DOPPLER_CONFIG=$(just _doppler-config {{ENV}})
    echo "📋 Running Terraform plan for {{ENV}}..."
    echo "   Backend: envs/{{ENV}}/backend.hcl"
    echo "   Vars:    envs/{{ENV}}/terraform.tfvars"
    echo "   Doppler: $DOPPLER_CONFIG"
    cd terraform && doppler run -c $DOPPLER_CONFIG -- terraform plan -var-file=envs/{{ENV}}/terraform.tfvars -out=tfplan-{{ENV}}
    echo "✅ Plan saved to terraform/tfplan-{{ENV}}. Review and run 'just tf-apply {{ENV}}' to apply."

# Apply Terraform changes for a specific environment
tf-apply ENV:
    #!/bin/bash
    set -e
    if [ ! -f terraform/tfplan-{{ENV}} ]; then
        echo "❌ Run 'just tf-plan {{ENV}}' first to create a plan"
        exit 1
    fi
    DOPPLER_CONFIG=$(just _doppler-config {{ENV}})
    echo "🔧 Applying Terraform plan for {{ENV}}..."
    cd terraform && doppler run -c $DOPPLER_CONFIG -- terraform apply tfplan-{{ENV}}
    rm -f terraform/tfplan-{{ENV}}
    echo "✅ Terraform applied to {{ENV}} successfully!"

# Destroy infrastructure for a specific environment (with confirmation)
tf-destroy ENV:
    #!/bin/bash
    set -e
    echo "⚠️  WARNING: This will destroy all resources in {{ENV}}!"
    echo "   Press Ctrl+C to abort, or Enter to continue..."
    read -r _
    DOPPLER_CONFIG=$(just _doppler-config {{ENV}})
    echo "🗑️  Destroying {{ENV}} infrastructure..."
    cd terraform && doppler run -c $DOPPLER_CONFIG -- terraform destroy -var-file=envs/{{ENV}}/terraform.tfvars
    echo "✅ {{ENV}} infrastructure destroyed"

# Show current Terraform state for an environment
tf-state ENV:
    @echo "📊 Terraform state for {{ENV}}..."
    cd terraform && terraform state list

# Verify Lambda has no placeholder values after deployment
tf-verify-lambda FUNCTION="dr-daily-report-telegram-api-dev":
    @echo "🔍 Verifying Lambda environment variables..."
    @aws lambda get-function-configuration --function-name {{FUNCTION}} \
        --query 'Environment.Variables' | grep -q "placeholder" && \
        (echo "❌ ERROR: Placeholder found in Lambda!" && exit 1) || \
        echo "✅ No placeholders found in Lambda"

# Legacy single-env terraform commands (for backwards compatibility)
# These use dev environment by default
terraform-plan:
    @just tf-plan dev

terraform-apply:
    @just tf-apply dev

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

# === CLEANUP ===

# Quick cleanup (remove build artifacts only)
clean:
    dr clean build

# Deep cleanup (remove all generated files including cache)
deep-clean:
    @echo "🧹 Deep cleaning..."
    dr clean all
    @echo "✅ All artifacts removed"

# Clean Terraform caches and artifacts (~1.9GB)
clean-terraform:
    @echo "🧹 Cleaning Terraform artifacts..."
    rm -rf terraform/.terraform/
    rm -rf terraform/layers/*/.terraform/
    rm -f terraform/*.tfplan
    rm -f terraform/*.backup
    @echo "✓ Cleaned Terraform caches"

# Clean Python cache files
clean-python:
    @echo "🧹 Cleaning Python cache..."
    find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    find . -type f -name "*.pyc" -delete 2>/dev/null || true
    @echo "✓ Cleaned Python cache"

# Clean test outputs
clean-tests:
    @echo "🧹 Cleaning test outputs..."
    rm -rf tests/output/
    rm -rf tests/artifacts/
    @echo "✓ Cleaned test outputs"

# Clean all caches and artifacts (Terraform + Python + tests)
clean-all-caches: clean-terraform clean-python clean-tests
    @echo "✅ Cleaned all caches and artifacts (~1.9GB freed)"

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

# === MCP SETUP ===

# Setup AWS MCP tools for Cursor IDE (run once to enable AWS integration)
setup-mcp:
    @echo "🔧 Setting up AWS MCP for Cursor IDE..."
    @if [ "$(OS)" = "Windows_NT" ]; then \
        powershell -ExecutionPolicy Bypass -File scripts/setup-mcp.ps1; \
    else \
        bash scripts/setup-mcp.sh; \
    fi
    @echo ""
    @echo "✅ MCP setup complete! Restart Cursor IDE to activate."

# Test AWS MCP server handshake (verify MCP server is working correctly)
test-mcp:
    @echo "🧪 Testing AWS MCP Server Handshake..."
    python scripts/test_mcp_handshake.py

# Verify MCP configuration uses Doppler (project standard)
verify-mcp:
    @echo "🔍 Verifying MCP Configuration (Doppler-based)..."
    python scripts/test_mcp_doppler.py

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

# === INFRASTRUCTURE TDD ===
# OPA policy validation (pre-apply) + Terratest integration tests (post-apply)
# Flow: terraform plan → OPA validation → terraform apply → Terratest
#
# Usage:
#   just opa-validate dev    # Validate Terraform plan against OPA policies
#   just terratest           # Run Terratest integration tests
#   just infra-tdd dev       # Full TDD cycle: OPA → apply → Terratest

# Install OPA/Conftest for policy validation
opa-install:
    @echo "📦 Installing Conftest (OPA for Terraform)..."
    @if command -v conftest &> /dev/null; then \
        echo "✅ Conftest already installed: $(conftest --version)"; \
    else \
        echo "Installing Conftest..."; \
        curl -L https://github.com/open-policy-agent/conftest/releases/download/v0.46.2/conftest_0.46.2_Linux_x86_64.tar.gz | tar xz; \
        sudo mv conftest /usr/local/bin/; \
        echo "✅ Conftest installed: $(conftest --version)"; \
    fi

# Run OPA policy validation on Terraform plan (pre-apply check)
opa-validate ENV="dev":
    #!/bin/bash
    set -e
    echo "🔍 Running OPA policy validation for {{ENV}}..."
    DOPPLER_CONFIG=$(just _doppler-config {{ENV}})

    # Generate Terraform plan JSON
    echo "   Generating Terraform plan..."
    cd terraform && doppler run -c $DOPPLER_CONFIG -- terraform plan \
        -var-file=envs/{{ENV}}/terraform.tfvars \
        -out=tfplan.binary \
        -no-color
    terraform show -json tfplan.binary > tfplan.json

    # Run OPA policies
    echo "   Running OPA policies..."
    conftest test tfplan.json --policy policies/ --all-namespaces --output table

    # Cleanup
    rm -f tfplan.binary tfplan.json
    echo "✅ OPA validation passed for {{ENV}}!"

# Run OPA validation with warnings only (non-blocking)
opa-check ENV="dev":
    #!/bin/bash
    set -e
    echo "🔍 Running OPA policy check (non-blocking) for {{ENV}}..."
    DOPPLER_CONFIG=$(just _doppler-config {{ENV}})

    cd terraform && doppler run -c $DOPPLER_CONFIG -- terraform plan \
        -var-file=envs/{{ENV}}/terraform.tfvars \
        -out=tfplan.binary \
        -no-color 2>&1 | tail -5
    terraform show -json tfplan.binary > tfplan.json

    # Run policies but don't fail on denies
    conftest test tfplan.json --policy policies/ --all-namespaces --no-fail --output stdout

    rm -f tfplan.binary tfplan.json
    echo "✅ OPA check complete!"

# Run Terratest integration tests (post-apply verification)
terratest:
    @echo "🧪 Running Terratest integration tests..."
    @if ! command -v go &> /dev/null; then \
        echo "❌ Go is not installed. Install Go 1.21+ first."; \
        exit 1; \
    fi
    cd terraform/tests && go test -v -timeout 15m ./... -parallel 4
    @echo "✅ Terratest integration tests passed!"

# Run specific Terratest test
terratest-run TEST:
    @echo "🧪 Running Terratest: {{TEST}}..."
    cd terraform/tests && go test -v -timeout 10m -run {{TEST}}

# Full Infrastructure TDD cycle: OPA validate → apply → Terratest
infra-tdd ENV="dev":
    @echo "🔄 Running full Infrastructure TDD cycle for {{ENV}}..."
    @echo ""
    @echo "Step 1: OPA Policy Validation (pre-apply)"
    just opa-validate {{ENV}}
    @echo ""
    @echo "Step 2: Terraform Apply"
    just tf-plan {{ENV}}
    just tf-apply {{ENV}}
    @echo ""
    @echo "Step 3: Terratest Integration Tests (post-apply)"
    just terratest
    @echo ""
    @echo "✅ Infrastructure TDD cycle complete for {{ENV}}!"

# List available OPA policies
opa-list:
    @echo "📋 Available OPA policies:"
    @find terraform/policies -name "*.rego" -type f | sort

# Test OPA policies against sample plan (offline)
opa-test:
    @echo "🧪 Testing OPA policies..."
    cd terraform && conftest verify --policy policies/
