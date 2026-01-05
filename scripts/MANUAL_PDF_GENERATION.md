# Manual DBS PDF Generation with Thai Fonts

## Overview

These scripts manually generate a DBS (D05.SI) PDF with Thai font support by:
1. Clearing the existing pdf_url in Aurora
2. Triggering the PDF workflow
3. Downloading and verifying the PDF

## Prerequisites

- Doppler CLI configured with ENV=dev
- AWS CLI with dev environment credentials
- **Aurora VPC access** (required to update database)
- Python 3.11+ with project dependencies installed

## Quick Start

### Option 1: Python Script (Recommended)

```bash
# Activate virtual environment
source venv/bin/activate

# Run with Doppler
ENV=dev doppler run -- python3 scripts/generate_dbs_pdf.py
```

### Option 2: Bash Script

```bash
# Run with Doppler
ENV=dev doppler run -- ./scripts/manual_dbs_pdf_generation.sh
```

## What the Scripts Do

### Step 1: Clear pdf_url in Aurora

Connects to Aurora and runs:
```sql
UPDATE precomputed_reports
SET pdf_url = NULL,
    pdf_s3_key = NULL
WHERE symbol = 'D05.SI'
  AND report_date = '2026-01-04';
```

### Step 2: Trigger PDF Workflow

Starts the Step Functions PDF workflow:
```bash
aws stepfunctions start-execution \
  --state-machine-arn arn:aws:states:...:stateMachine:dr-daily-report-pdf-workflow-dev
```

### Step 3: Monitor Execution

Polls the Step Functions execution every 3 seconds until completion.

### Step 4: Download PDF

Downloads the generated PDF from S3 to `/tmp/D05.SI_2026-01-04_thai_fonts.pdf`

### Step 5: Verify Thai Fonts

Checks embedded fonts using `pdffonts` to confirm Sarabun fonts are present.

## Expected Output

```
======================================================
Manual DBS PDF Generation with Thai Fonts
======================================================

Symbol: D05.SI
Date: 2026-01-04

Step 1: Clearing pdf_url in Aurora...
------------------------------------------------------
✅ Cleared pdf_url for D05.SI: 1 row(s) updated
   Report ID: 2134
   PDF URL: NULL (ready for regeneration)

Step 2: Triggering PDF Workflow...
------------------------------------------------------
Started: arn:aws:states:...:execution:dr-daily-report-pdf-workflow-dev:manual-dbs-pdf-...

Step 3: Monitoring PDF Generation...
------------------------------------------------------
[1] Status: RUNNING
[2] Status: RUNNING
[3] Status: SUCCEEDED

✅ PDF workflow completed successfully
   Generated 1 PDF(s)

Step 4: Downloading PDF with Thai Fonts...
------------------------------------------------------
S3 Key: reports/D05.SI/2026-01-04/D05.SI_report_2026-01-04_182530.pdf
Downloading to: /tmp/D05.SI_2026-01-04_thai_fonts.pdf
✅ Downloaded: /tmp/D05.SI_2026-01-04_thai_fonts.pdf

Step 5: Verifying Thai Fonts...
------------------------------------------------------
Embedded fonts:
name                    type      encoding   emb sub uni
AAAAAA+Sarabun-Bold     TrueType  WinAnsi    yes yes yes
AAAAAA+Sarabun-Regular  TrueType  WinAnsi    yes yes yes
Helvetica               Type 1    WinAnsi    no  no  no

✅✅✅ SUCCESS! Thai fonts (Sarabun) are embedded!

======================================================
PDF Generation Complete!
======================================================

PDF Location: /tmp/D05.SI_2026-01-04_thai_fonts.pdf

Open the PDF to verify Thai characters display correctly.
```

## Troubleshooting

### Error: Can't connect to Aurora

**Problem**: No VPC access to Aurora database

**Solution**:
- Run from within the VPC (bastion host)
- Or use SSM port forwarding:
  ```bash
  aws ssm start-session \
    --target i-XXXXXXXXX \
    --document-name AWS-StartPortForwardingSessionToRemoteHost \
    --parameters '{"host":["aurora-endpoint"],"portNumber":["3306"],"localPortNumber":["3307"]}'
  ```

### Error: pdf_url already NULL

**Problem**: pdf_url was already cleared, but no PDF generated

**Solution**: The workflow might have already run. Check S3:
```bash
ENV=dev doppler run -- aws s3 ls s3://line-bot-pdf-reports-755283537543/reports/D05.SI/2026-01-04/
```

### Error: No PDFs generated (total_pdfs: 0)

**Problem**: PDF workflow found no reports needing PDFs

**Causes**:
1. pdf_url not properly cleared
2. Report doesn't exist for this date
3. Report already has pdf_url set again

**Solution**: Verify the report exists and pdf_url is NULL:
```sql
SELECT id, symbol, report_date, pdf_url, pdf_s3_key
FROM precomputed_reports
WHERE symbol = 'D05.SI' AND report_date = '2026-01-04';
```

### PDF downloaded but no Thai fonts

**Problem**: Sarabun fonts not embedded in PDF

**Causes**:
1. Lambda not using updated Docker image with fonts
2. Font registration failed

**Solution**: Verify Lambda is using correct image:
```bash
ENV=dev doppler run -- aws lambda get-function-configuration \
  --function-name dr-daily-report-pdf-worker-dev \
  --query 'CodeSha256' \
  --output text
```

Should be: `9dbd1772cedc445a77818c86c8abe540de8e1b2f8d8f92a5b338b9337aabed95`

## Alternative: Wait for Tomorrow

Instead of manually generating, you can wait for tomorrow's automatic run:
- **Scheduled**: 8 AM Bangkok time
- **Process**: Automatic (precompute → EventBridge → PDF)
- **Result**: All 46 PDFs regenerated with Thai fonts

## Files Created

- `scripts/manual_dbs_pdf_generation.sh` - Bash version (interactive)
- `scripts/generate_dbs_pdf.py` - Python version (simpler)
- `scripts/MANUAL_PDF_GENERATION.md` - This file

## Related

- EventBridge validation: `.claude/validations/2026-01-04-pdf-workflow-eventbridge-trigger.md`
- Thai font fix: Commit `e4323fd`
- Deployment: Lambda image `thai-fonts-e4323fd-20260104175500`
