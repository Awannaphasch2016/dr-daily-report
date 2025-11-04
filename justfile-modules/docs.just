# Documentation Module
# Commands for viewing documentation

# View API documentation
docs-api:
    @echo "📚 Opening API documentation..."
    @cat ../docs/API_USAGE.md | head -100

# View quickstart guide
docs-quickstart:
    @echo "📚 Opening quickstart guide..."
    @cat ../docs/QUICKSTART.md | head -100
