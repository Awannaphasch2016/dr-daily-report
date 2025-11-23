#!/usr/bin/env python3
"""Generate presigned URL for the DBS19 PDF"""

import os
import subprocess
from src.pdf_storage import PDFStorage

# Load Doppler env
print("📡 Loading environment variables from Doppler...")
result = subprocess.run(
    ['doppler', '--project', 'rag-chatbot-worktree', '--config', 'dev_personal', 'run', '--', 'env'],
    capture_output=True,
    text=True,
    check=True
)

for line in result.stdout.split('\n'):
    if '=' in line and not line.startswith('#'):
        key, value = line.split('=', 1)
        os.environ[key] = value

# Get bucket from Terraform
print("📦 Getting bucket name from Terraform...")
tf_result = subprocess.run(
    ['terraform', 'output', '-raw', 'pdf_storage_bucket'],
    cwd='terraform',
    capture_output=True,
    text=True,
    check=True
)
os.environ['PDF_STORAGE_BUCKET'] = tf_result.stdout.strip().strip('"')

# Generate presigned URL
storage = PDFStorage()
object_key = 'reports/DBS19/20251110/DBS19_report_20251110_095023.pdf'

print(f"\n🔗 Generating presigned URL for: {object_key}")
print(f"   Bucket: {storage.bucket_name}\n")

url = storage.get_presigned_url(object_key)

print("\n" + "="*80)
print("PRESIGNED URL (copy and paste into browser):")
print("="*80)
print(url)
print("="*80)
print("\n✅ This URL is valid for 24 hours.")
print("   You can click this link or copy-paste it into your browser to view the PDF.\n")
