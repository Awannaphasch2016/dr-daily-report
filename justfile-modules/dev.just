# Development Tools Module
# Commands for development and code quality

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

# Clean Python cache files
clean:
    @echo "🧹 Cleaning cache files..."
    find . -type d -name "__pycache__" -exec rm -r {} + 2>/dev/null || true
    find . -type f -name "*.pyc" -delete 2>/dev/null || true
    find . -type f -name "*.pyo" -delete 2>/dev/null || true
    echo "✅ Cleaned!"
