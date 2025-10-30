#!/usr/bin/env python3
"""Create minimal deployment ZIP"""

import zipfile
import os
from pathlib import Path

deployment_dir = Path("deployment_package_minimal")
zip_file = "lambda_deployment_minimal.zip"

print(f"📦 Creating minimal deployment package...")

with zipfile.ZipFile(zip_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
    for root, dirs, files in os.walk(deployment_dir):
        for file in files:
            file_path = Path(root) / file
            arcname = file_path.relative_to(deployment_dir)
            zipf.write(file_path, arcname)

size_mb = os.path.getsize(zip_file) / (1024 * 1024)
print(f"✅ Created {zip_file}")
print(f"   Size: {size_mb:.2f} MB")

# Estimate unzipped size
unzipped_mb = sum(f.stat().st_size for f in deployment_dir.rglob('*') if f.is_file()) / (1024 * 1024)
print(f"   Unzipped: ~{unzipped_mb:.2f} MB")

if unzipped_mb > 250:
    print(f"   ⚠️  Still over 250MB limit!")
else:
    print(f"   ✅ Under 250MB limit!")
