# Development commands
# Note: Recipes run from justfile-modules/, so paths use ../

# Run the Flask server locally
run-server:
    @cd .. && python scripts/run_server.py

# Run tests with pytest
test:
    @cd .. && python -m pytest tests/ -v

# Run a specific test file
test-file test_file:
    @cd .. && python -m pytest tests/{{test_file}} -v

# Run LINE bot follow event test
test-follow:
    @cd .. && PYTHONPATH=$(pwd) python tests/test_line_follow.py

# Run LINE bot help command test
test-help:
    @cd .. && PYTHONPATH=$(pwd) python tests/test_line_help.py

# Run LINE bot error handling test
test-error-handling:
    @cd .. && PYTHONPATH=$(pwd) python tests/test_line_error_handling.py

# Run LINE bot fuzzy matching test
test-fuzzy-matching:
    @cd .. && PYTHONPATH=$(pwd) python tests/test_fuzzy_matching.py

# Run LINE bot caching test
test-caching:
    @cd .. && PYTHONPATH=$(pwd) python tests/test_caching.py

# Run LINE bot message test
test-message ticker:
    @cd .. && PYTHONPATH=.. python tests/test_line_message.py {{ticker}}

# Run LINE bot integration test
test-integration ticker:
    @cd .. && PYTHONPATH=.. python tests/test_line_integration.py {{ticker}}

# Run all tests in tests directory
test-all:
    @cd .. && python -m pytest tests/ -v --tb=short

# Install dependencies
install:
    @cd .. && pip install -r requirements.txt

# Install development dependencies
install-dev:
    @cd .. && pip install -r requirements.txt -r requirements.txt

# Run Python script with PYTHONPATH set
run script:
    @cd .. && PYTHONPATH=.. python {{script}}

# Start interactive Python shell with project imports
shell:
    @cd .. && PYTHONPATH=.. python -i