#!/usr/bin/env python3
"""
Quick start script for Flask webapp
Run this to start the web server
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from webapp.app import app

if __name__ == '__main__':
    print("=" * 80)
    print("Starting Ticker Reports Web Application")
    print("=" * 80)
    print()
    print("🌐 Web interface: http://localhost:5000")
    print("📊 API endpoint: http://localhost:5000/api/reports")
    print()
    print("Press Ctrl+C to stop")
    print("=" * 80)
    print()
    
    app.run(debug=True, host='0.0.0.0', port=5000)
