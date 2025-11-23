#!/usr/bin/env python3
"""Test PDF storage and upload with DBS19 using Doppler environment variables"""

import os
import sys
import subprocess
import logging
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def load_doppler_env():
    """Load environment variables from Doppler"""
    logger.info("📡 Loading environment variables from Doppler...")
    try:
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
        
        # Get actual bucket name from Terraform if PDF_STORAGE_BUCKET not set
        if 'PDF_STORAGE_BUCKET' not in os.environ:
            logger.info("   PDF_STORAGE_BUCKET not in Doppler, fetching from Terraform...")
            try:
                tf_result = subprocess.run(
                    ['terraform', 'output', '-raw', 'pdf_storage_bucket'],
                    cwd='terraform',
                    capture_output=True,
                    text=True,
                    check=True
                )
                bucket_name = tf_result.stdout.strip().strip('"')
                os.environ['PDF_STORAGE_BUCKET'] = bucket_name
                logger.info(f"   ✅ Set PDF_STORAGE_BUCKET={bucket_name} from Terraform")
            except Exception as e:
                logger.warning(f"   ⚠️  Could not get bucket from Terraform: {e}")
                logger.warning("   Using default bucket name")
        
        logger.info("✅ Environment variables loaded from Doppler")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ Failed to load Doppler env: {e}")
        logger.error(f"   stdout: {e.stdout}")
        logger.error(f"   stderr: {e.stderr}")
        return False
    except FileNotFoundError:
        logger.error("❌ Doppler CLI not found. Please install Doppler CLI first.")
        return False

def test_boto3_import():
    """Test that boto3 is available"""
    logger.info("\n" + "="*80)
    logger.info("TEST 1: boto3 Import")
    logger.info("="*80)
    
    try:
        import boto3
        logger.info(f"✅ boto3 imported successfully (version: {boto3.__version__})")
        return True
    except ImportError as e:
        logger.error(f"❌ boto3 not available: {e}")
        logger.error("   Please install boto3: pip install boto3")
        return False

def test_pdf_storage_init():
    """Test PDF storage initialization"""
    logger.info("\n" + "="*80)
    logger.info("TEST 2: PDF Storage Initialization")
    logger.info("="*80)
    
    try:
        from src.formatters.pdf_storage import PDFStorage
        
        storage = PDFStorage()
        
        if storage.is_available():
            logger.info("✅ PDFStorage initialized and S3 client available")
            logger.info(f"   Bucket: {storage.bucket_name}")
            logger.info(f"   URL Expiration: {storage.url_expiration_hours}h")
            return True
        else:
            logger.warning("⚠️  PDFStorage initialized but S3 client not available")
            logger.warning("   This might be due to missing AWS credentials")
            return False
    except Exception as e:
        logger.error(f"❌ PDFStorage initialization failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_pdf_generation():
    """Test PDF generation for DBS19"""
    logger.info("\n" + "="*80)
    logger.info("TEST 3: PDF Generation for DBS19")
    logger.info("="*80)
    
    try:
        from src.agent import TickerAnalysisAgent
        
        logger.info("📊 Initializing TickerAnalysisAgent...")
        agent = TickerAnalysisAgent()
        
        ticker = "DBS19"
        logger.info(f"📄 Generating PDF report for {ticker}...")
        
        pdf_bytes = agent.generate_pdf_report(ticker)
        
        if pdf_bytes and len(pdf_bytes) > 0:
            size_kb = len(pdf_bytes) / 1024
            logger.info(f"✅ PDF generated successfully")
            logger.info(f"   Size: {len(pdf_bytes):,} bytes ({size_kb:.1f} KB)")
            return pdf_bytes
        else:
            logger.error("❌ PDF generation returned empty bytes")
            return None
            
    except Exception as e:
        logger.error(f"❌ PDF generation failed: {e}")
        import traceback
        traceback.print_exc()
        return None

def test_s3_upload(pdf_bytes):
    """Test uploading PDF to S3"""
    logger.info("\n" + "="*80)
    logger.info("TEST 4: S3 Upload")
    logger.info("="*80)
    
    if not pdf_bytes:
        logger.error("❌ No PDF bytes to upload")
        return None
    
    try:
        from src.formatters.pdf_storage import PDFStorage
        
        storage = PDFStorage()
        
        if not storage.is_available():
            logger.error("❌ S3 client not available. Check AWS credentials.")
            return None
        
        ticker = "DBS19"
        logger.info(f"📤 Uploading PDF for {ticker} to S3...")
        
        object_key = storage.upload_pdf(pdf_bytes, ticker)
        
        logger.info(f"✅ PDF uploaded successfully")
        logger.info(f"   Object Key: {object_key}")
        logger.info(f"   Bucket: {storage.bucket_name}")
        return object_key
        
    except Exception as e:
        logger.error(f"❌ S3 upload failed: {e}")
        import traceback
        traceback.print_exc()
        return None

def test_presigned_url(object_key):
    """Test presigned URL generation"""
    logger.info("\n" + "="*80)
    logger.info("TEST 5: Presigned URL Generation")
    logger.info("="*80)
    
    if not object_key:
        logger.error("❌ No object key provided")
        return None
    
    try:
        from src.formatters.pdf_storage import PDFStorage
        
        storage = PDFStorage()
        
        logger.info(f"🔗 Generating presigned URL for: {object_key}")
        
        url = storage.get_presigned_url(object_key)
        
        logger.info(f"✅ Presigned URL generated successfully")
        logger.info(f"   URL: {url[:100]}...")
        logger.info(f"   Expires in: {storage.url_expiration_hours} hours")
        return url
        
    except Exception as e:
        logger.error(f"❌ Presigned URL generation failed: {e}")
        import traceback
        traceback.print_exc()
        return None

def test_line_bot_integration():
    """Test LINE bot integration (message formatting)"""
    logger.info("\n" + "="*80)
    logger.info("TEST 6: LINE Bot Integration")
    logger.info("="*80)
    
    try:
        from src.integrations.line_bot import LineBot
        
        # Create instance without full initialization (to avoid OpenAI requirement)
        bot = object.__new__(LineBot)
        
        test_report = "📖 **เรื่องราวของหุ้นตัวนี้**\n\nหุ้น D05.SI..."
        test_url = "https://example.com/test.pdf"
        
        formatted = bot.format_message_with_pdf_link(test_report, test_url)
        
        if formatted and "รายงานฉบับเต็ม" in formatted and test_url in formatted:
            logger.info("✅ Message formatting works correctly")
            logger.info(f"   Message length: {len(formatted)} chars")
            logger.info(f"   Preview:\n{formatted[:200]}...")
            return True
        else:
            logger.error("❌ Message formatting failed")
            return False
            
    except Exception as e:
        logger.error(f"❌ LINE bot integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all tests"""
    logger.info("\n" + "="*80)
    logger.info("PDF STORAGE & S3 UPLOAD TEST - DBS19")
    logger.info("="*80)
    
    results = []
    
    # Load environment variables
    if not load_doppler_env():
        logger.error("\n❌ Failed to load environment variables. Exiting.")
        return 1
    
    # Test 1: boto3 import
    results.append(("boto3 Import", test_boto3_import()))
    
    # Test 2: PDF Storage initialization
    results.append(("PDF Storage Init", test_pdf_storage_init()))
    
    # Test 3: PDF Generation
    pdf_bytes = test_pdf_generation()
    results.append(("PDF Generation", pdf_bytes is not None))
    
    # Test 4: S3 Upload (only if PDF was generated)
    object_key = None
    if pdf_bytes:
        object_key = test_s3_upload(pdf_bytes)
        results.append(("S3 Upload", object_key is not None))
    else:
        results.append(("S3 Upload", False))
    
    # Test 5: Presigned URL (only if upload succeeded)
    url = None
    if object_key:
        url = test_presigned_url(object_key)
        results.append(("Presigned URL", url is not None))
    else:
        results.append(("Presigned URL", False))
    
    # Test 6: LINE Bot Integration
    results.append(("LINE Bot Integration", test_line_bot_integration()))
    
    # Summary
    logger.info("\n" + "="*80)
    logger.info("TEST SUMMARY")
    logger.info("="*80)
    
    passed = 0
    failed = 0
    
    for test_name, result in results:
        if result:
            status = "✅ PASSED"
            passed += 1
        else:
            status = "❌ FAILED"
            failed += 1
        logger.info(f"{status}: {test_name}")
    
    logger.info("\n" + "-"*80)
    logger.info(f"Total: {len(results)} tests")
    logger.info(f"✅ Passed: {passed}")
    logger.info(f"❌ Failed: {failed}")
    logger.info("-"*80)
    
    if url:
        logger.info(f"\n📄 PDF URL (valid for 24 hours):")
        logger.info(f"   {url}")
    
    if failed == 0:
        logger.info("\n✅ All tests passed! Ready to deploy.")
        return 0
    else:
        logger.info("\n❌ Some tests failed. Please fix before deploying.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
