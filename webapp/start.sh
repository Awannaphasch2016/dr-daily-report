#!/bin/bash
# Start Flask webapp
cd "$(dirname "$0")"
export FLASK_APP=app.py
export FLASK_ENV=development
python app.py
