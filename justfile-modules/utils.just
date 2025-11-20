# Utility commands
# Note: Recipes run from justfile-modules/, so paths use ../

# Show project structure
tree:
    @cd .. && tree -L 2 -I 'venv|__pycache__|*.pyc|.git|build' || find . -maxdepth 2 -not -path '*/\.*' -not -path '*/venv/*' -not -path '*/build/*' | head -30

# List Python files
list-python:
    @cd .. && find . -name "*.py" -not -path "./venv/*" -not -path "./build/*" -not -path "./.git/*" | head -50

# Count lines of code
loc:
    @cd .. && find . -name "*.py" -not -path "./venv/*" -not -path "./build/*" -not -path "./.git/*" | xargs wc -l | tail -1

# Check Python syntax
check-syntax:
    @cd .. && python -m py_compile src/**/*.py 2>&1 | head -20 || echo "? Syntax check passed"

# Format code with black (if installed)
format:
    @cd .. && black src/ tests/ --line-length 100 2>/dev/null || echo "??  black not installed, skipping"

# Lint code with pylint (if installed)
lint:
    @cd .. && pylint src/ --disable=C,R,W 2>/dev/null || echo "??  pylint not installed, skipping"

# Generate report for a ticker
generate-report ticker:
    @cd .. && PYTHONPATH=.. python -c "from src.agent import TickerAnalysisAgent; agent = TickerAnalysisAgent(); print(agent.analyze_ticker('{{ticker}}'))"

# Generate all reports (uses generate_all_reports.py if exists)
generate-all:
    @cd .. && python generate_all_reports.py 2>/dev/null || echo "??  generate_all_reports.py not found"

# Show environment variables status
check-env:
    @echo "Checking environment variables..."
    @cd .. && [ -n "$$OPENAI_API_KEY" ] && echo "? OPENAI_API_KEY: Set" || echo "? OPENAI_API_KEY: Not set"
    @cd .. && [ -n "$$LINE_CHANNEL_ACCESS_TOKEN" ] && echo "? LINE_CHANNEL_ACCESS_TOKEN: Set" || echo "? LINE_CHANNEL_ACCESS_TOKEN: Not set"
    @cd .. && [ -n "$$LINE_CHANNEL_SECRET" ] && echo "? LINE_CHANNEL_SECRET: Set" || echo "? LINE_CHANNEL_SECRET: Not set"

# Show help/info
info:
    @echo "?? Daily Report LINE Bot"
    @echo ""
    @echo "Common commands:"
    @echo "  just run-server      - Run Flask server locally"
    @echo "  just test            - Run all tests"
    @echo "  just build           - Create Lambda deployment package"
    @echo "  just clean-all       - Clean all build artifacts"
    @echo ""
    @echo "For more commands, run: just --list"
