"""PDF Storage Module for S3 Integration

Handles uploading PDF reports to S3 and generating presigned URLs for LINE bot integration.
"""

import os
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# Try to import boto3, but handle gracefully if not available
try:
    import boto3
    from botocore.exceptions import ClientError
    BOTO3_AVAILABLE = True
except ImportError:
    BOTO3_AVAILABLE = False
    logger.debug("boto3 not available (likely local environment)")

class PDFStorage:
    """Handle PDF storage in S3 and URL generation"""
    
    def __init__(self):
        """Initialize PDF storage with S3 client"""
        if not BOTO3_AVAILABLE:
            logger.debug("boto3 not available - PDF storage disabled")
            self.s3_client = None
            self.bucket_name = None
            self.url_expiration_hours = 24
            return
        
        try:
            self.s3_client = boto3.client('s3')
            self.bucket_name = os.getenv('PDF_STORAGE_BUCKET', 'line-bot-pdf-reports')
            self.url_expiration_hours = int(os.getenv('PDF_URL_EXPIRATION_HOURS', '24'))
            logger.info(f"PDFStorage initialized: bucket={self.bucket_name}, expiration={self.url_expiration_hours}h")
        except Exception as e:
            logger.warning(f"Failed to initialize S3 client (may be local env): {e}")
            self.s3_client = None
            self.bucket_name = None
            self.url_expiration_hours = 24
    
    def upload_pdf(self, pdf_bytes: bytes, ticker: str, date_str: str = None) -> str:
        """
        Upload PDF to S3 and return object key
        
        Args:
            pdf_bytes: PDF file bytes
            ticker: Ticker symbol (e.g., "DBS19")
            date_str: Optional date string (defaults to today)
            
        Returns:
            S3 object key (path)
            
        Raises:
            ValueError: If S3 client not available or upload fails
        """
        if self.s3_client is None:
            raise ValueError("S3 client not available (likely local environment)")
        
        if date_str is None:
            date_str = datetime.now().strftime('%Y%m%d')
        
        # Create object key: reports/DBS19/20251110/DBS19_report_20251110_143022.pdf
        timestamp = datetime.now().strftime('%H%M%S')
        object_key = f"reports/{ticker}/{date_str}/{ticker}_report_{date_str}_{timestamp}.pdf"
        
        try:
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=object_key,
                Body=pdf_bytes,
                ContentType='application/pdf',
                Metadata={
                    'ticker': ticker,
                    'generated_at': datetime.now().isoformat()
                }
            )
            logger.info(f"✅ PDF uploaded to S3: s3://{self.bucket_name}/{object_key} ({len(pdf_bytes)} bytes)")
            return object_key
        except Exception as e:
            logger.error(f"❌ Failed to upload PDF to S3: {e}")
            raise ValueError(f"S3 upload failed: {str(e)}")
    
    def get_presigned_url(self, object_key: str, expiration_hours: int = None) -> str:
        """
        Generate presigned URL for PDF download
        
        Args:
            object_key: S3 object key
            expiration_hours: URL expiration time (defaults to instance default)
            
        Returns:
            Presigned URL string
            
        Raises:
            ValueError: If S3 client not available or URL generation fails
        """
        if self.s3_client is None:
            raise ValueError("S3 client not available (likely local environment)")
        
        if expiration_hours is None:
            expiration_hours = self.url_expiration_hours
        
        try:
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket_name, 'Key': object_key},
                ExpiresIn=expiration_hours * 3600  # Convert hours to seconds
            )
            logger.info(f"✅ Generated presigned URL (expires in {expiration_hours}h)")
            return url
        except Exception as e:
            logger.error(f"❌ Failed to generate presigned URL: {e}")
            raise ValueError(f"Presigned URL generation failed: {str(e)}")
    
    def upload_and_get_url(self, pdf_bytes: bytes, ticker: str) -> str:
        """
        Convenience method: Upload PDF and return presigned URL
        
        Args:
            pdf_bytes: PDF file bytes
            ticker: Ticker symbol
            
        Returns:
            Presigned URL string
            
        Raises:
            ValueError: If upload or URL generation fails
        """
        object_key = self.upload_pdf(pdf_bytes, ticker)
        return self.get_presigned_url(object_key)
    
    def is_available(self) -> bool:
        """
        Check if S3 storage is available
        
        Returns:
            True if S3 client is available, False otherwise
        """
        return self.s3_client is not None
