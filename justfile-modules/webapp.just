# Web Application Module
# Commands for running and managing the Flask webapp

# Start Flask webapp
webapp:
    @echo "🚀 Starting Flask webapp..."
    python ../webapp/app.py

# Start webapp with auto-reload
webapp-dev:
    @echo "🚀 Starting Flask webapp (development mode)..."
    FLASK_ENV=development FLASK_DEBUG=1 python ../webapp/app.py

# Run webapp server (alternative)
server:
    @echo "🚀 Starting server..."
    python ../scripts/run_server.py

# Check if Flask app is running
check-webapp:
    @echo "🔍 Checking if Flask app is running..."
    @curl -s http://127.0.0.1:5000/tiles > /dev/null && echo "✅ Flask app is running!" || echo "❌ Flask app is not running"

# Open tiles page in browser
open-tiles:
    @echo "🌐 Opening tiles page..."
    @xdg-open http://127.0.0.1:5000/tiles 2>/dev/null || open http://127.0.0.1:5000/tiles 2>/dev/null || echo "Please open http://127.0.0.1:5000/tiles in your browser"
