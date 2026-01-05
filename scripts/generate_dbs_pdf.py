#!/usr/bin/env python3
"""
Manual DBS PDF Generation with Thai Fonts

Simpler Python-only alternative to the bash script.
Requires: Python 3.11+, Aurora VPC access
"""

from src.data.aurora.client import AuroraClient
from datetime import date
import subprocess
import time
import json
import os

SYMBOL = "D05.SI"
REPORT_DATE = date(2026, 1, 4)
AWS_REGION = "ap-southeast-1"
PDF_WORKFLOW_ARN = "arn:aws:states:ap-southeast-1:755283537543:stateMachine:dr-daily-report-pdf-workflow-dev"
S3_BUCKET = "line-bot-pdf-reports-755283537543"

print("=" * 60)
print("Manual DBS PDF Generation with Thai Fonts")
print("=" * 60)
print(f"\nSymbol: {SYMBOL}")
print(f"Date: {REPORT_DATE}")
print()

# Step 1: Clear pdf_url in Aurora
print("Step 1: Clearing pdf_url in Aurora...")
print("-" * 60)

try:
    client = AuroraClient()

    # Clear pdf_url
    update_query = """
        UPDATE precomputed_reports
        SET pdf_url = NULL,
            pdf_s3_key = NULL,
            updated_at = NOW()
        WHERE symbol = %s
          AND report_date = %s
    """

    with client.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(update_query, (SYMBOL, REPORT_DATE))
        affected = cursor.rowcount
        conn.commit()
        cursor.close()

    print(f"✅ Cleared pdf_url for {SYMBOL}: {affected} row(s) updated")

    # Verify
    verify_query = """
        SELECT id, symbol, report_date, pdf_url, updated_at
        FROM precomputed_reports
        WHERE symbol = %s AND report_date = %s
    """

    result = client.execute(verify_query, (SYMBOL, REPORT_DATE))
    if result:
        report = result[0]
        print(f"   Report ID: {report['id']}")
        print(f"   PDF URL: {report['pdf_url'] or 'NULL (ready for regeneration)'}")
    else:
        print("❌ Report not found!")
        exit(1)

except Exception as e:
    print(f"❌ Failed to clear pdf_url: {e}")
    print("\nAlternative: Run this SQL manually in Aurora:")
    print(f"""
    UPDATE precomputed_reports
    SET pdf_url = NULL, pdf_s3_key = NULL
    WHERE symbol = '{SYMBOL}' AND report_date = '{REPORT_DATE}';
    """)
    exit(1)

# Step 2: Trigger PDF workflow
print("\nStep 2: Triggering PDF Workflow...")
print("-" * 60)

execution_name = f"manual-dbs-pdf-{int(time.time())}"

result = subprocess.run([
    "aws", "stepfunctions", "start-execution",
    "--state-machine-arn", PDF_WORKFLOW_ARN,
    "--name", execution_name,
    "--input", "{}",
    "--region", AWS_REGION
], capture_output=True, text=True, env=os.environ)

if result.returncode != 0:
    print(f"❌ Failed to start PDF workflow: {result.stderr}")
    exit(1)

response = json.loads(result.stdout)
execution_arn = response['executionArn']
print(f"Started: {execution_arn}")

# Step 3: Monitor execution
print("\nStep 3: Monitoring PDF Generation...")
print("-" * 60)

for i in range(30):
    time.sleep(3)

    result = subprocess.run([
        "aws", "stepfunctions", "describe-execution",
        "--execution-arn", execution_arn,
        "--region", AWS_REGION
    ], capture_output=True, text=True, env=os.environ)

    if result.returncode == 0:
        execution = json.loads(result.stdout)
        status = execution['status']
        print(f"[{i+1}] Status: {status}")

        if status != "RUNNING":
            print()
            if status == "SUCCEEDED":
                print("✅ PDF workflow completed successfully")

                output = json.loads(execution.get('output', '{}'))
                total_pdfs = output.get('total_pdfs', 0)

                if total_pdfs > 0:
                    print(f"   Generated {total_pdfs} PDF(s)")
                else:
                    print(f"   Message: {output.get('message', 'Unknown')}")
            else:
                print(f"❌ Workflow failed: {status}")
            break
    else:
        print(f"   Error checking status: {result.stderr}")

# Step 4: Download PDF
print("\nStep 4: Downloading PDF with Thai Fonts...")
print("-" * 60)

# List PDFs for this symbol/date
result = subprocess.run([
    "aws", "s3", "ls",
    f"s3://{S3_BUCKET}/reports/{SYMBOL}/{REPORT_DATE.strftime('%Y-%m-%d')}/",
    "--region", AWS_REGION
], capture_output=True, text=True, env=os.environ)

if result.returncode == 0 and result.stdout:
    # Get the latest PDF (last line)
    lines = [line for line in result.stdout.strip().split('\n') if line]
    if lines:
        latest = lines[-1]
        pdf_filename = latest.split()[-1]
        s3_key = f"reports/{SYMBOL}/{REPORT_DATE.strftime('%Y-%m-%d')}/{pdf_filename}"
        local_path = f"/tmp/{SYMBOL}_{REPORT_DATE.strftime('%Y-%m-%d')}_thai_fonts.pdf"

        print(f"S3 Key: {s3_key}")
        print(f"Downloading to: {local_path}")

        result = subprocess.run([
            "aws", "s3", "cp",
            f"s3://{S3_BUCKET}/{s3_key}",
            local_path,
            "--region", AWS_REGION
        ], env=os.environ)

        if result.returncode == 0:
            print(f"✅ Downloaded: {local_path}")

            # Verify Thai fonts
            print("\nStep 5: Verifying Thai Fonts...")
            print("-" * 60)

            result = subprocess.run(["pdffonts", local_path],
                                   capture_output=True, text=True)

            if result.returncode == 0:
                print("Embedded fonts:")
                print(result.stdout)

                if "Sarabun" in result.stdout:
                    print("\n✅✅✅ SUCCESS! Thai fonts (Sarabun) are embedded!")
                else:
                    print("\n⚠️  WARNING: Sarabun fonts not found")
            else:
                print("pdffonts not available (install poppler-utils)")

            print("\n" + "=" * 60)
            print("PDF Generation Complete!")
            print("=" * 60)
            print(f"\nPDF Location: {local_path}")
            print("\nOpen the PDF to verify Thai characters display correctly.")

        else:
            print("❌ Failed to download PDF")
    else:
        print("❌ No PDF files found")
else:
    print(f"❌ Failed to list S3 files: {result.stderr}")
