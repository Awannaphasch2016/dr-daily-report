# Justfile for Daily Report Media Project
# Common commands for development and operations

# Default recipe - show available commands
default:
    @just --list

# ============================================================================
# Web Application
# ============================================================================

# Start Flask webapp
webapp:
    @echo "🚀 Starting Flask webapp..."
    cd webapp && python app.py

# Start webapp with auto-reload
webapp-dev:
    @echo "🚀 Starting Flask webapp (development mode)..."
    cd webapp && FLASK_ENV=development FLASK_DEBUG=1 python app.py

# Run webapp server (alternative)
server:
    @echo "🚀 Starting server..."
    python scripts/run_server.py

# ============================================================================
# Testing
# ============================================================================

# Run all tests
test:
    @echo "🧪 Running all tests..."
    pytest tests/ -v

# Run unit tests only
test-unit:
    @echo "🧪 Running unit tests..."
    pytest tests/ -v -k "not e2e"

# Run E2E tests (requires Flask app running)
test-e2e:
    @echo "🧪 Running E2E tests..."
    @./tests/run_e2e_tests.sh

# Run E2E tests with UI
test-e2e-headed:
    @echo "🧪 Running E2E tests (headed mode)..."
    pytest tests/test_tiles_e2e.py --browser chromium --headed -v

# Run specific test file
test-file FILE:
    @echo "🧪 Running {{FILE}}..."
    pytest {{FILE}} -v

# Run tests with coverage
test-cov:
    @echo "🧪 Running tests with coverage..."
    pytest tests/ --cov=src --cov=webapp --cov-report=html

# ============================================================================
# Dependencies
# ============================================================================

# Install all dependencies
install:
    @echo "📦 Installing dependencies..."
    pip install -r requirements.txt

# Install minimal dependencies
install-minimal:
    @echo "📦 Installing minimal dependencies..."
    pip install -r requirements_minimal.txt

# Install Playwright browsers
install-playwright:
    @echo "📦 Installing Playwright browsers..."
    playwright install chromium

# Update dependencies
update:
    @echo "📦 Updating dependencies..."
    pip install --upgrade -r requirements.txt

# ============================================================================
# Database Operations
# ============================================================================

# Initialize database
db-init:
    @echo "💾 Initializing database..."
    cd webapp && python -c "from app import init_db; init_db()"

# Index existing PDFs
db-index-pdfs:
    @echo "💾 Indexing PDFs..."
    cd webapp && python index_existing_pdfs.py

# Check database contents
db-check:
    @echo "💾 Checking database..."
    python webapp/check_db.py

# ============================================================================
# Report Generation
# ============================================================================

# Generate report for a single ticker
report TICKER:
    @echo "📄 Generating report for {{TICKER}}..."
    python webapp/save_report_to_db.py {{TICKER}}

# Generate all reports
reports-all:
    @echo "📄 Generating all reports..."
    python generate_all_reports.py

# Generate reports with faithfulness scoring
reports-faithful:
    @echo "📄 Generating reports with faithfulness scoring..."
    python generate_report_with_faithfulness.py

# ============================================================================
# Development Tools
# ============================================================================

# Run linting
lint:
    @echo "🔍 Running linter..."
    @echo "Checking Python files..."
    @find . -name "*.py" -not -path "./venv/*" -not -path "./.venv/*" -exec python -m py_compile {} \; || true

# Format code (if black is installed)
format:
    @echo "✨ Formatting code..."
    @black . --check || echo "Black not installed, skipping..."

# Check code complexity
complexity:
    @echo "📊 Analyzing code complexity..."
    python scripts/analyze_complexity.py

# ============================================================================
# API Testing
# ============================================================================

# Test API endpoint
api-test:
    @echo "🌐 Testing API..."
    python webapp/test_api.py

# Test tiles API
api-tiles:
    @echo "🌐 Testing tiles API..."
    curl -s http://127.0.0.1:5000/api/tiles-data | python -m json.tool | head -50

# ============================================================================
# Deployment
# ============================================================================

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

# ============================================================================
# Quick Development Tasks
# ============================================================================

# Quick test for a ticker
quick-test TICKER:
    @echo "⚡ Quick test for {{TICKER}}..."
    python test_direct.py {{TICKER}}

# Test audio generation
test-audio:
    @echo "🔊 Testing audio generation..."
    python test_audio.py

# Test botnoi integration
test-botnoi:
    @echo "🤖 Testing Botnoi integration..."
    python test_botnoi.py

# Show scores
scores:
    @echo "📊 Showing scores..."
    python show_scores.py

# ============================================================================
# Utilities
# ============================================================================

# Clean Python cache files
clean:
    @echo "🧹 Cleaning cache files..."
    find . -type d -name "__pycache__" -exec rm -r {} + 2>/dev/null || true
    find . -type f -name "*.pyc" -delete 2>/dev/null || true
    find . -type f -name "*.pyo" -delete 2>/dev/null || true
    echo "✅ Cleaned!"

# Check if Flask app is running
check-webapp:
    @echo "🔍 Checking if Flask app is running..."
    @curl -s http://127.0.0.1:5000/tiles > /dev/null && echo "✅ Flask app is running!" || echo "❌ Flask app is not running"

# Open tiles page in browser
open-tiles:
    @echo "🌐 Opening tiles page..."
    @xdg-open http://127.0.0.1:5000/tiles 2>/dev/null || open http://127.0.0.1:5000/tiles 2>/dev/null || echo "Please open http://127.0.0.1:5000/tiles in your browser"

# View database
db-view:
    @echo "💾 Opening database..."
    @sqlite3 webapp/data/ticker_reports.db ".tables" || sqlite3 data/ticker_reports.db ".tables"

# ============================================================================
# Development Workflow
# ============================================================================

# Start full development environment
dev-start:
    @echo "🚀 Starting development environment..."
    @just check-webapp || (echo "Starting Flask app..." && just webapp-dev &)
    @sleep 2
    @just check-webapp
    @echo "✅ Development environment ready!"
    @echo "   Webapp: http://127.0.0.1:5000"
    @echo "   Tiles: http://127.0.0.1:5000/tiles"

# Stop development environment
dev-stop:
    @echo "🛑 Stopping development environment..."
    @pkill -f "python.*app.py" || echo "No Flask processes found"

# Reset database and reindex
reset-db:
    @echo "🔄 Resetting database..."
    @rm -f webapp/data/ticker_reports.db data/ticker_reports.db
    @just db-init
    @just db-index-pdfs
    @echo "✅ Database reset complete!"

# ============================================================================
# Documentation
# ============================================================================

# View API documentation
docs-api:
    @echo "📚 Opening API documentation..."
    @cat docs/API_USAGE.md | head -100

# View quickstart guide
docs-quickstart:
    @echo "📚 Opening quickstart guide..."
    @cat docs/QUICKSTART.md | head -100

# ============================================================================
# Help
# ============================================================================

# Show help
help:
    @echo "Daily Report Media - Common Commands"
    @echo ""
    @echo "Web Application:"
    @echo "  just webapp          - Start Flask webapp"
    @echo "  just webapp-dev      - Start Flask webapp (development mode)"
    @echo ""
    @echo "Testing:"
    @echo "  just test            - Run all tests"
    @echo "  just test-unit       - Run unit tests only"
    @echo "  just test-e2e        - Run E2E tests"
    @echo ""
    @echo "Development:"
    @echo "  just dev-start       - Start full dev environment"
    @echo "  just clean           - Clean cache files"
    @echo ""
    @echo "Report Generation:"
    @echo "  just report TICKER   - Generate report for ticker"
    @echo "  just reports-all     - Generate all reports"
    @echo ""
    @echo "See 'just --list' for all available commands"
