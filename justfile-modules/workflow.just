# Workflow Module
# Development workflow commands

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
