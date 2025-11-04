# Dependencies Module
# Commands for managing dependencies

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
