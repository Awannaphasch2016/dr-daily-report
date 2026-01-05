#!/bin/bash
# Manual DBS PDF Generation with Thai Fonts
#
# This script:
# 1. Clears pdf_url for D05.SI in Aurora
# 2. Triggers PDF workflow to regenerate with Thai fonts
# 3. Monitors execution and downloads the PDF
#
# Prerequisites:
# - Doppler CLI configured (ENV=dev)
# - AWS CLI with dev environment access
# - Aurora VPC access OR SSM session to bastion

set -e

SYMBOL="D05.SI"
REPORT_DATE="2026-01-04"

echo "======================================================"
echo "Manual DBS PDF Generation with Thai Fonts"
echo "======================================================"
echo ""
echo "Symbol: $SYMBOL"
echo "Date: $REPORT_DATE"
echo ""

# Step 1: Clear pdf_url in Aurora
echo "Step 1: Clearing pdf_url in Aurora..."
echo "------------------------------------------------------"

# Option A: Direct Aurora connection (requires VPC access)
read -p "Do you have direct VPC access to Aurora? (y/n): " HAS_VPC

if [ "$HAS_VPC" == "y" ]; then
    echo "Connecting to Aurora directly..."

    # Get Aurora credentials from Doppler
    AURORA_HOST=$(ENV=dev doppler secrets get AURORA_HOST --plain)
    AURORA_USER=$(ENV=dev doppler secrets get AURORA_USER --plain)
    AURORA_PASSWORD=$(ENV=dev doppler secrets get AURORA_MASTER_PASSWORD --plain)
    AURORA_DATABASE=$(ENV=dev doppler secrets get AURORA_DATABASE --plain)

    # Clear pdf_url
    mysql -h "$AURORA_HOST" -u "$AURORA_USER" -p"$AURORA_PASSWORD" "$AURORA_DATABASE" << SQL
UPDATE precomputed_reports
SET pdf_url = NULL,
    pdf_s3_key = NULL,
    updated_at = NOW()
WHERE symbol = '$SYMBOL'
  AND report_date = '$REPORT_DATE';

SELECT
    id,
    symbol,
    report_date,
    pdf_url,
    updated_at
FROM precomputed_reports
WHERE symbol = '$SYMBOL'
  AND report_date = '$REPORT_DATE';
SQL

    echo "✅ pdf_url cleared for $SYMBOL"
else
    # Option B: Using Python script via Lambda (has VPC access)
    echo "Using Lambda to clear pdf_url..."

    cat > /tmp/clear_pdf_url.py << 'PYTHON'
from src.data.aurora.client import AuroraClient
from datetime import date

symbol = "D05.SI"
report_date = date(2026, 1, 4)

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
    cursor.execute(query, (symbol, report_date))
    affected = cursor.rowcount
    conn.commit()
    cursor.close()

    print(f"✅ Cleared pdf_url for {symbol}: {affected} row(s) updated")

# Verify
verify_query = """
    SELECT id, symbol, report_date, pdf_url, updated_at
    FROM precomputed_reports
    WHERE symbol = %s AND report_date = %s
"""

result = client.execute(verify_query, (symbol, report_date))
if result:
    print(f"Report ID: {result[0]['id']}")
    print(f"PDF URL: {result[0]['pdf_url']}")
else:
    print("❌ Report not found")
PYTHON

    # Execute via Lambda (report_worker has Aurora access)
    echo "Invoking Lambda to clear pdf_url..."
    ENV=dev doppler run -- python3 /tmp/clear_pdf_url.py

    if [ $? -eq 0 ]; then
        echo "✅ pdf_url cleared successfully"
    else
        echo "❌ Failed to clear pdf_url"
        echo "   Trying alternative method..."

        # Alternative: Use migration_handler Lambda
        echo "   Creating Lambda payload..."
        cat > /tmp/clear_pdf_payload.json << JSON
{
  "action": "execute_sql",
  "sql": "UPDATE precomputed_reports SET pdf_url = NULL, pdf_s3_key = NULL WHERE symbol = '$SYMBOL' AND report_date = '$REPORT_DATE'",
  "database": "ticker_data"
}
JSON

        ENV=dev doppler run -- aws lambda invoke \
            --function-name dr-daily-report-migration-handler-dev \
            --payload file:///tmp/clear_pdf_payload.json \
            /tmp/clear_response.json

        echo "Response:"
        cat /tmp/clear_response.json | jq '.'
    fi
fi

echo ""
echo "Step 2: Triggering PDF Workflow..."
echo "------------------------------------------------------"

# Start PDF workflow execution
EXECUTION_ARN=$(ENV=dev doppler run -- aws stepfunctions start-execution \
    --state-machine-arn arn:aws:states:ap-southeast-1:755283537543:stateMachine:dr-daily-report-pdf-workflow-dev \
    --name "manual-dbs-pdf-$(date +%s)" \
    --input "{}" \
    --query 'executionArn' \
    --output text)

echo "Started PDF workflow: $EXECUTION_ARN"
echo ""

# Monitor execution
echo "Step 3: Monitoring PDF Generation..."
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
echo "Step 4: Locating and Downloading DBS PDF..."
echo "------------------------------------------------------"

# Find the latest PDF
PDF_S3_KEY=$(ENV=dev doppler run -- aws s3 ls \
    s3://line-bot-pdf-reports-755283537543/reports/$SYMBOL/$REPORT_DATE/ \
    | sort -k1,2 | tail -1 | awk '{print $4}')

if [ -z "$PDF_S3_KEY" ]; then
    echo "❌ No PDF found for $SYMBOL on $REPORT_DATE"
    exit 1
fi

FULL_S3_PATH="reports/$SYMBOL/$REPORT_DATE/$PDF_S3_KEY"
LOCAL_PATH="/tmp/${SYMBOL}_${REPORT_DATE}_thai_fonts.pdf"

echo "PDF S3 Key: $FULL_S3_PATH"
echo "Downloading to: $LOCAL_PATH"

ENV=dev doppler run -- aws s3 cp \
    "s3://line-bot-pdf-reports-755283537543/$FULL_S3_PATH" \
    "$LOCAL_PATH"

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ PDF downloaded successfully!"
    echo ""
    echo "Step 5: Verifying Thai Fonts..."
    echo "------------------------------------------------------"

    # Check embedded fonts
    if command -v pdffonts &> /dev/null; then
        echo "Embedded fonts:"
        pdffonts "$LOCAL_PATH"

        # Check for Sarabun
        if pdffonts "$LOCAL_PATH" | grep -q "Sarabun"; then
            echo ""
            echo "✅✅✅ SUCCESS! Thai fonts (Sarabun) are embedded!"
        else
            echo ""
            echo "⚠️  WARNING: Thai fonts not found. PDF may show black boxes."
        fi
    else
        echo "pdffonts not available. Install poppler-utils to verify fonts."
    fi

    echo ""
    echo "======================================================"
    echo "PDF Generation Complete!"
    echo "======================================================"
    echo ""
    echo "PDF Location: $LOCAL_PATH"
    echo "File size: $(ls -lh $LOCAL_PATH | awk '{print $5}')"
    echo ""
    echo "Open the PDF to verify Thai characters display correctly."
else
    echo "❌ Failed to download PDF"
    exit 1
fi
