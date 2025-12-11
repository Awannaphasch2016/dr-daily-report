#!/bin/bash
# Quick script to run DBS19 report generation

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_ROOT"

echo "=========================================="
echo "📊 Generating Report for DBS19"
echo "=========================================="
echo ""

# Try Doppler first
if command -v doppler > /dev/null 2>&1; then
    echo "🔍 Attempting to use Doppler..."
    
    # Try common project names
    for PROJECT in "dr-daily-report" "dr-daily-report-telegram" "dr-daily-report_report_generation"; do
        echo "  Trying project: $PROJECT"
        if doppler run --project "$PROJECT" --config dev --command "test -n \"\$OPENROUTER_API_KEY\"" 2>/dev/null; then
            echo "✅ Found Doppler project: $PROJECT"
            echo ""
            echo "📝 Generating report with Doppler..."
            doppler run --project "$PROJECT" --config dev --command "PYTHONPATH=$PROJECT_ROOT:\$PYTHONPATH python3 scripts/generate_report_output.py DBS19"
            exit 0
        fi
    done
    
    echo "⚠️  Doppler project not found. Trying direct API key..."
fi

# Fallback: Check for direct API key
if [ -z "${OPENROUTER_API_KEY:-}" ]; then
    echo "❌ ERROR: OPENROUTER_API_KEY not set"
    echo ""
    echo "Please either:"
    echo "  1. Configure Doppler:"
    echo "     doppler configure set project <project-name>"
    echo "     doppler configure set config dev"
    echo ""
    echo "  2. Or set API key directly:"
    echo "     export OPENROUTER_API_KEY='your-key-here'"
    echo "     $0"
    exit 1
fi

echo "📝 Generating report with direct API key..."
PYTHONPATH="$PROJECT_ROOT:$PYTHONPATH" python3 scripts/generate_report_output.py DBS19
