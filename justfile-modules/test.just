# Testing Module
# Commands for running tests

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
