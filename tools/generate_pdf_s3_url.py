#!/usr/bin/env python3
"""
Generate PDF report with Thai fonts and upload to S3, then get presigned URL.
"""

import os
import sys
import logging
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def load_env_from_doppler():
    """Try to load environment variables from Doppler"""
    try:
        import subprocess
        logger.info("📡 Attempting to load environment from Doppler...")
        result = subprocess.run(
            ['doppler', '--project', 'rag-chatbot-worktree', '--config', 'dev_personal', 'run', '--', 'env'],
            capture_output=True,
            text=True,
            check=True
        )
        
        # Parse environment variables from Doppler output
        for line in result.stdout.split('\n'):
            if '=' in line and not line.startswith('#'):
                key, value = line.split('=', 1)
                os.environ[key] = value
        
        logger.info("✅ Environment variables loaded from Doppler")
        return True
    except (FileNotFoundError, subprocess.CalledProcessError):
        logger.debug("   Doppler not available or failed")
        return False

def load_env_from_file():
    """Try to load environment variables from .env file"""
    env_file = os.path.join(os.path.dirname(__file__), '.env')
    if os.path.exists(env_file):
        try:
            logger.info("📄 Loading environment from .env file...")
            with open(env_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        os.environ[key] = value
            logger.info("✅ Environment variables loaded from .env")
            return True
        except Exception as e:
            logger.debug(f"   Failed to load .env: {e}")
    return False

def check_required_env():
    """Check if required environment variables are available"""
    logger.info("🔍 Checking required environment variables...")
    
    # Try to load from Doppler or .env first
    if not os.getenv('OPENAI_API_KEY'):
        load_env_from_doppler() or load_env_from_file()
    
    missing = []
    
    # Check OpenAI API key
    if not os.getenv('OPENAI_API_KEY'):
        missing.append('OPENAI_API_KEY')
        logger.warning("⚠️  OPENAI_API_KEY not found")
    else:
        logger.info("✅ OPENAI_API_KEY found")
    
    # Check AWS credentials
    aws_creds_ok = False
    if os.getenv('AWS_ACCESS_KEY_ID') and os.getenv('AWS_SECRET_ACCESS_KEY'):
        logger.info("✅ AWS credentials found in environment variables")
        aws_creds_ok = True
    elif os.path.exists(os.path.expanduser('~/.aws/credentials')):
        logger.info("✅ AWS credentials file found")
        aws_creds_ok = True
    else:
        logger.warning("⚠️  AWS credentials not found")
        logger.warning("   Please set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY")
        logger.warning("   OR configure AWS CLI: aws configure")
    
    if missing:
        logger.error("❌ Missing required environment variables:")
        for var in missing:
            logger.error(f"   - {var}")
        logger.error("\n   Please set these environment variables before running.")
        return False
    
    if not aws_creds_ok:
        logger.error("❌ AWS credentials not available. Cannot upload to S3.")
        return False
    
    return True

def get_bucket_name():
    """Get S3 bucket name from environment or Terraform"""
    bucket = os.getenv('PDF_STORAGE_BUCKET')
    
    if bucket:
        logger.info(f"✅ Using bucket from environment: {bucket}")
        return bucket
    
    # Try to get from Terraform
    logger.info("📦 Getting bucket name from Terraform...")
    try:
        import subprocess
        result = subprocess.run(
            ['terraform', 'output', '-raw', 'pdf_storage_bucket'],
            cwd='terraform',
            capture_output=True,
            text=True,
            check=True
        )
        bucket = result.stdout.strip().strip('"')
        logger.info(f"✅ Using bucket from Terraform: {bucket}")
        os.environ['PDF_STORAGE_BUCKET'] = bucket
        return bucket
    except Exception as e:
        logger.warning(f"⚠️  Could not get bucket from Terraform: {e}")
        logger.warning("   Using default bucket name")
        return 'line-bot-pdf-reports'

def generate_and_upload_pdf(ticker: str = "AAPL19"):
    """
    Generate PDF report and upload to S3, return presigned URL
    
    Args:
        ticker: Ticker symbol (default: AAPL19)
    
    Returns:
        Presigned URL string or None if failed
    """
    print("=" * 80)
    print(f"PDF GENERATION & S3 UPLOAD - {ticker}")
    print("=" * 80)
    print()
    
    # Check required environment variables
    if not check_required_env():
        logger.error("❌ Required environment variables not available.")
        return None
    
    # Get bucket name
    bucket_name = get_bucket_name()
    os.environ['PDF_STORAGE_BUCKET'] = bucket_name
    
    try:
        # Import required modules
        logger.info("📚 Importing modules...")
        from src.agent import TickerAnalysisAgent
        from src.formatters.pdf_storage import PDFStorage
        
        # Initialize agent
        logger.info("🔄 Initializing TickerAnalysisAgent...")
        agent = TickerAnalysisAgent()
        logger.info("✅ Agent initialized")
        
        # Initialize PDF storage
        logger.info("🔄 Initializing PDFStorage...")
        storage = PDFStorage()
        
        if not storage.is_available():
            logger.error("❌ S3 client not available. Check AWS credentials.")
            return None
        
        logger.info(f"✅ PDFStorage initialized: bucket={storage.bucket_name}")
        print()
        
        # Generate PDF report
        logger.info(f"📊 Generating PDF report for {ticker}...")
        logger.info("   This will:")
        logger.info("   1. Fetch ticker data")
        logger.info("   2. Calculate technical indicators")
        logger.info("   3. Fetch and analyze news")
        logger.info("   4. Generate chart visualization")
        logger.info("   5. Create narrative report")
        logger.info("   6. Compile into PDF with Thai fonts")
        print()
        logger.info("⏳ Please wait... (this may take 10-15 seconds)")
        print()
        
        pdf_bytes = agent.generate_pdf_report(ticker=ticker)
        
        if not pdf_bytes or len(pdf_bytes) == 0:
            logger.error("❌ PDF generation returned empty bytes")
            return None
        
        size_kb = len(pdf_bytes) / 1024
        logger.info(f"✅ PDF generated successfully")
        logger.info(f"   Size: {len(pdf_bytes):,} bytes ({size_kb:.1f} KB)")
        print()
        
        # Upload to S3 and get presigned URL
        logger.info(f"📤 Uploading PDF to S3...")
        logger.info(f"   Bucket: {storage.bucket_name}")
        
        pdf_url = storage.upload_and_get_url(pdf_bytes, ticker)
        
        logger.info(f"✅ PDF uploaded and presigned URL generated")
        logger.info(f"   URL expires in: {storage.url_expiration_hours} hours")
        print()
        
        # Display results
        print("=" * 80)
        print("SUCCESS!")
        print("=" * 80)
        print()
        print("📄 PDF Report Details:")
        print(f"   Ticker: {ticker}")
        print(f"   Size: {len(pdf_bytes):,} bytes ({size_kb:.1f} KB)")
        print(f"   Bucket: {storage.bucket_name}")
        print()
        print("🔗 Presigned URL (valid for 24 hours):")
        print("   " + "-" * 76)
        print(f"   {pdf_url}")
        print("   " + "-" * 76)
        print()
        print("💡 You can:")
        print("   - Copy the URL above and paste it into your browser")
        print("   - Share the URL with others (valid for 24 hours)")
        print("   - Download the PDF directly from the URL")
        print()
        print("=" * 80)
        
        return pdf_url
        
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        print()
        print("=" * 80)
        print("FAILED")
        print("=" * 80)
        return None


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Generate PDF report with Thai fonts and upload to S3"
    )
    parser.add_argument(
        "--ticker",
        type=str,
        default="AAPL19",
        help="Ticker symbol to generate report for (default: AAPL19)"
    )
    
    args = parser.parse_args()
    
    url = generate_and_upload_pdf(args.ticker)
    
    if url:
        sys.exit(0)
    else:
        sys.exit(1)
