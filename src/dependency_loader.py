"""
Lazy loading of heavy dependencies from S3 to /tmp
This module downloads numpy, pandas, and matplotlib from S3 on cold starts
"""
import os
import sys
import zipfile
import logging

logger = logging.getLogger(__name__)

# Configuration
S3_BUCKET = "line-bot-ticker-deploy-20251030"
S3_KEY = "python-libs/data-science-libs.zip"
TMP_DIR = "/tmp/python-libs"
ZIP_PATH = "/tmp/data-science-libs.zip"

def load_heavy_dependencies():
    """
    Download and extract heavy dependencies from S3 if not already present in /tmp
    In local environment, skip S3 download and assume dependencies are installed
    """
    try:
        # In local environment (not Lambda), skip S3 download
        # Assume numpy/pandas/matplotlib are installed locally
        if not os.environ.get('AWS_LAMBDA_FUNCTION_NAME'):
            logger.info("Local environment detected - skipping S3 dependency download")
            # Try importing to verify dependencies are available
            try:
                import numpy
                import pandas
                import matplotlib
                logger.info("Heavy dependencies available locally")
                return True
            except ImportError as e:
                logger.warning(f"Some dependencies not available locally: {e}")
                logger.warning("In Lambda, dependencies will be loaded from S3")
                return True  # Don't fail in local testing
        
        # Lambda environment - proceed with S3 download
        import boto3
        
        # Check if already loaded
        site_packages_path = os.path.join(TMP_DIR, "site-packages")
        if os.path.exists(site_packages_path) and site_packages_path in sys.path:
            logger.info("Heavy dependencies already loaded from /tmp")
            return True
        elif os.path.exists(TMP_DIR) and TMP_DIR in sys.path:
            logger.info("Heavy dependencies already loaded from /tmp")
            return True

        # Check if directory exists but not in path
        if os.path.exists(site_packages_path):
            logger.info("Adding existing /tmp/python-libs/site-packages to sys.path")
            sys.path.insert(0, site_packages_path)
            return True
        elif os.path.exists(TMP_DIR):
            logger.info("Adding existing /tmp/python-libs to sys.path")
            sys.path.insert(0, TMP_DIR)
            return True

        # Download from S3
        logger.info(f"Downloading heavy dependencies from s3://{S3_BUCKET}/{S3_KEY}")
        s3 = boto3.client('s3')
        s3.download_file(S3_BUCKET, S3_KEY, ZIP_PATH)
        logger.info(f"Downloaded {os.path.getsize(ZIP_PATH) / 1024 / 1024:.1f} MB")

        # Extract to /tmp
        logger.info(f"Extracting to {TMP_DIR}")
        os.makedirs(TMP_DIR, exist_ok=True)
        with zipfile.ZipFile(ZIP_PATH, 'r') as zip_ref:
            zip_ref.extractall(TMP_DIR)

        # Clean up ZIP file
        os.remove(ZIP_PATH)
        logger.info("Removed ZIP file to save space")

        # Add to Python path - check if site-packages exists, otherwise use TMP_DIR directly
        site_packages_path = os.path.join(TMP_DIR, "site-packages")
        if os.path.exists(site_packages_path):
            sys.path.insert(0, site_packages_path)
            logger.info(f"Added {site_packages_path} to sys.path")
        else:
            sys.path.insert(0, TMP_DIR)
            logger.info(f"Added {TMP_DIR} to sys.path")
        
        logger.info("Heavy dependencies loaded successfully")

        return True

    except Exception as e:
        logger.error(f"Failed to load heavy dependencies: {str(e)}")
        raise
