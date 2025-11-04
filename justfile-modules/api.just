# API Testing Module
# Commands for testing API endpoints

# Test API endpoint
api-test:
    @echo "🌐 Testing API..."
    python webapp/test_api.py

# Test tiles API
api-tiles:
    @echo "🌐 Testing tiles API..."
    curl -s http://127.0.0.1:5000/api/tiles-data | python -m json.tool | head -50
