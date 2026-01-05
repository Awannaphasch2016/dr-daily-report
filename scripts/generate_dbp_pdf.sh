#!/bin/bash
# Generate PDF for DBP19 with Thai font support
#
# This script generates a PDF report for DBP19 ensuring:
# 1. Thai fonts (Sarabun) are embedded to prevent box characters
# 2. Latest report data is used
# 3. PDF is downloaded locally for verification
#
# Prerequisites:
# - Doppler CLI configured (ENV=dev)
# - AWS CLI with dev environment access

set -e

TICKER="DBP19"
REPORT_DATE=$(date +%Y-%m-%d)

echo "======================================================"
echo "DBP19 PDF Generation with Thai Fonts"
echo "======================================================"
echo ""
echo "Ticker: $TICKER"
echo "Date: $REPORT_DATE"
echo ""

# Step 1: Check if report exists in precomputed_reports
echo "Step 1: Checking for existing report..."
echo "------------------------------------------------------"

SYMBOL_CHECK=$(ENV=dev doppler run -- python3 -c "
from src.data.aurora.ticker_resolver import get_ticker_resolver

resolver = get_ticker_resolver()
resolved = resolver.resolve('$TICKER')

if resolved:
    print(resolved.yahoo_symbol)
else:
    print('NOT_FOUND')
" 2>/dev/null)

if [ "$SYMBOL_CHECK" == "NOT_FOUND" ]; then
    echo "❌ Error: $TICKER is not a valid ticker symbol"
    echo ""
    echo "Please check the ticker symbol and try again."
    echo "Example: DBS19, NVDA19, AAPL, etc."
    exit 1
fi

YAHOO_SYMBOL="$SYMBOL_CHECK"
echo "✅ Ticker resolved: $TICKER → $YAHOO_SYMBOL (Yahoo)"
echo ""

# Step 2: Clear pdf_url to force regeneration
echo "Step 2: Clearing pdf_url to force regeneration..."
echo "------------------------------------------------------"

ENV=dev doppler run -- python3 << 'PYTHON'
from src.data.aurora.client import AuroraClient
from datetime import date, timedelta
import sys

# Use yesterday's date for precomputed reports
# (today's report may not be generated yet)
yahoo_symbol = sys.argv[1]
report_date = date.today() - timedelta(days=1)

client = AuroraClient()

# Clear pdf_url
query = """
    UPDATE precomputed_reports
    SET pdf_url = NULL,
        pdf_s3_key = NULL,
        updated_at = NOW()
    WHERE symbol = %s
      AND report_date = %s
"""

with client.get_connection() as conn:
    cursor = conn.cursor()
    cursor.execute(query, (yahoo_symbol, report_date))
    affected = cursor.rowcount
    conn.commit()
    cursor.close()

    print(f"✅ Cleared pdf_url for {yahoo_symbol}: {affected} row(s) updated")

    if affected == 0:
        print(f"⚠️  WARNING: No report found for {yahoo_symbol} on {report_date}")
        print(f"   The report may not exist in precomputed_reports yet.")
        sys.exit(1)

# Verify
verify_query = """
    SELECT id, symbol, report_date, pdf_url, updated_at
    FROM precomputed_reports
    WHERE symbol = %s AND report_date = %s
"""

result = client.execute(verify_query, (yahoo_symbol, report_date))
if result:
    print(f"Report ID: {result[0]['id']}")
    print(f"PDF URL: {result[0]['pdf_url']}")
else:
    print("❌ Report verification failed")
    sys.exit(1)
PYTHON $YAHOO_SYMBOL

if [ $? -ne 0 ]; then
    echo ""
    echo "⚠️  Report may not exist yet. Trying to generate..."
    echo ""
fi

echo ""
echo "Step 3: Triggering PDF Workflow..."
echo "------------------------------------------------------"

# Start PDF workflow execution
EXECUTION_ARN=$(ENV=dev doppler run -- aws stepfunctions start-execution \
    --state-machine-arn arn:aws:states:ap-southeast-1:755283537543:stateMachine:dr-daily-report-pdf-workflow-dev \
    --name "${TICKER}-pdf-$(date +%s)" \
    --input "{}" \
    --query 'executionArn' \
    --output text)

echo "Started PDF workflow: $EXECUTION_ARN"
echo ""

# Monitor execution
echo "Step 4: Monitoring PDF Generation..."
echo "------------------------------------------------------"

for i in {1..30}; do
    sleep 3

    STATUS=$(ENV=dev doppler run -- aws stepfunctions describe-execution \
        --execution-arn "$EXECUTION_ARN" \
        --query 'status' \
        --output text)

    echo "[$i] Status: $STATUS"

    if [ "$STATUS" != "RUNNING" ]; then
        echo ""
        if [ "$STATUS" == "SUCCEEDED" ]; then
            echo "✅ PDF workflow completed successfully"

            # Get output
            OUTPUT=$(ENV=dev doppler run -- aws stepfunctions describe-execution \
                --execution-arn "$EXECUTION_ARN" \
                --query 'output' \
                --output text)

            echo "Output:"
            echo "$OUTPUT" | jq '.'

            # Check if PDF was generated
            TOTAL_PDFS=$(echo "$OUTPUT" | jq -r '.total_pdfs // 0')
            if [ "$TOTAL_PDFS" -gt 0 ]; then
                echo ""
                echo "✅ Generated $TOTAL_PDFS PDF(s)"
            else
                echo ""
                echo "⚠️  No PDFs generated. Check output message above."
            fi
        else
            echo "❌ PDF workflow failed with status: $STATUS"
        fi
        break
    fi
done

echo ""
echo "Step 5: Locating and Downloading $TICKER PDF..."
echo "------------------------------------------------------"

# Use yesterday's date (that's what precompute scheduler uses)
YESTERDAY=$(date -d '1 day ago' +%Y-%m-%d)

# Find the latest PDF
PDF_S3_KEY=$(ENV=dev doppler run -- aws s3 ls \
    s3://line-bot-pdf-reports-755283537543/reports/$YAHOO_SYMBOL/$YESTERDAY/ \
    | sort -k1,2 | tail -1 | awk '{print $4}')

if [ -z "$PDF_S3_KEY" ]; then
    echo "❌ No PDF found for $YAHOO_SYMBOL on $YESTERDAY"
    echo ""
    echo "Trying today's date..."

    TODAY=$(date +%Y-%m-%d)
    PDF_S3_KEY=$(ENV=dev doppler run -- aws s3 ls \
        s3://line-bot-pdf-reports-755283537543/reports/$YAHOO_SYMBOL/$TODAY/ \
        | sort -k1,2 | tail -1 | awk '{print $4}')

    if [ -z "$PDF_S3_KEY" ]; then
        echo "❌ No PDF found for $YAHOO_SYMBOL on $TODAY either"
        exit 1
    fi

    REPORT_DATE="$TODAY"
else
    REPORT_DATE="$YESTERDAY"
fi

FULL_S3_PATH="reports/$YAHOO_SYMBOL/$REPORT_DATE/$PDF_S3_KEY"
LOCAL_PATH="/tmp/${TICKER}_${REPORT_DATE}_thai_fonts.pdf"

echo "PDF S3 Key: $FULL_S3_PATH"
echo "Downloading to: $LOCAL_PATH"

ENV=dev doppler run -- aws s3 cp \
    "s3://line-bot-pdf-reports-755283537543/$FULL_S3_PATH" \
    "$LOCAL_PATH"

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ PDF downloaded successfully!"
    echo ""
    echo "Step 6: Verifying Thai Fonts..."
    echo "------------------------------------------------------"

    # Check embedded fonts
    if command -v pdffonts &> /dev/null; then
        echo "Embedded fonts:"
        pdffonts "$LOCAL_PATH"

        # Check for Sarabun (Thai font)
        if pdffonts "$LOCAL_PATH" | grep -q "Sarabun"; then
            echo ""
            echo "✅✅✅ SUCCESS! Thai fonts (Sarabun) are embedded!"
            echo "    No box characters will appear for Thai text."
        else
            echo ""
            echo "⚠️  WARNING: Thai fonts not found."
            echo "   PDF may show box characters (□) for Thai text."
        fi
    else
        echo "pdffonts not available. Install poppler-utils to verify fonts:"
        echo "  sudo apt-get install poppler-utils"
    fi

    echo ""
    echo "======================================================"
    echo "PDF Generation Complete!"
    echo "======================================================"
    echo ""
    echo "PDF Location: $LOCAL_PATH"
    echo "File size: $(ls -lh $LOCAL_PATH | awk '{print $5}')"
    echo ""
    echo "Open the PDF:"
    echo "  xdg-open $LOCAL_PATH"
    echo ""
else
    echo "❌ Failed to download PDF"
    exit 1
fi
