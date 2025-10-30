#!/usr/bin/env python3
"""
Create Lambda deployment package using Python zipfile
"""

import zipfile
import os
from pathlib import Path

def create_deployment_zip():
    """Create deployment ZIP file"""
    deployment_dir = Path("build/deployment_package")
    zip_file = "build/lambda_deployment.zip"

    if not deployment_dir.exists():
        print("❌ build/deployment_package directory not found!")
        print("   Run scripts/deploy.sh first to install dependencies")
        return False

    print(f"📦 Creating {zip_file}...")

    # Create zip file
    with zipfile.ZipFile(zip_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
        # Walk through deployment_package directory
        for root, dirs, files in os.walk(deployment_dir):
            for file in files:
                file_path = Path(root) / file
                # Calculate relative path from deployment_package
                arcname = file_path.relative_to(deployment_dir)
                zipf.write(file_path, arcname)

    # Get file size
    size_mb = os.path.getsize(zip_file) / (1024 * 1024)

    print(f"✅ Created {zip_file}")
    print(f"   Size: {size_mb:.2f} MB")
    print()

    return True

if __name__ == "__main__":
    success = create_deployment_zip()
    if success:
        print("🎉 Deployment package ready!")
        print()
        print("Next steps:")
        print("1. Upload lambda_deployment.zip to AWS Lambda")
        print("2. Set handler to: lambda_handler.lambda_handler")
        print("3. Configure environment variables")
        print("4. Set timeout to 60+ seconds")
        print("5. Set memory to 512+ MB")
    else:
        print("❌ Failed to create deployment package")
        exit(1)
