#!/bin/bash
# Quick test script for peer comparison feature

echo "🔍 Testing Peer Comparison Feature"
echo "===================================="
echo ""
echo "⚠️  This will take 30-60 seconds to generate a report..."
echo ""

TICKER="${1:-NVDA19}"
URL="http://localhost:8001/api/v1/report/${TICKER}"

echo "📊 Fetching report for ${TICKER}..."
echo ""

RESPONSE=$(curl -s "$URL")

if [ $? -ne 0 ]; then
    echo "❌ Failed to fetch report"
    exit 1
fi

# Check if jq is available
if command -v jq &> /dev/null; then
    echo "✅ Report generated successfully"
    echo ""
    echo "📋 Peers found:"
    echo "$RESPONSE" | jq -r '.peers[] | "  • \(.ticker) - \(.company_name)\n    Stance: \(.stance), Valuation: \(.valuation_label)"'
    echo ""
    echo "Total peers: $(echo "$RESPONSE" | jq '.peers | length')"
else
    # Fallback if jq not available
    echo "$RESPONSE"
fi

echo ""
echo "✅ Test completed"
