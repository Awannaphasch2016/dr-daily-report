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
