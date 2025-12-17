# PDF Storage and LINE Bot Integration Guide

## Overview
This document outlines different approaches for storing PDF reports and integrating them with the LINE bot, allowing users to access detailed PDF reports via links.

## Architecture Options

### Option 1: AWS S3 with Presigned URLs (Recommended) ⭐

**Pros:**
- Secure, temporary access via presigned URLs
- Cost-effective (S3 storage is cheap)
- Scalable and reliable
- No public exposure of files
- Can set expiration times (e.g., 24 hours, 7 days)

**Cons:**
- Requires S3 bucket setup
- URLs expire after set time

**Implementation:**
```python
# Store PDF in S3 and generate presigned URL
# URL valid for 24 hours
# Format: "รายงานฉบับเต็ม: [PDF Link]\n\n[Current Text Output]"
```

### Option 2: AWS S3 + CloudFront (Public Access)

**Pros:**
- Fast CDN delivery
- Public URLs (no expiration)
- Better for sharing

**Cons:**
- Files are publicly accessible
- Need to manage public access
- Higher cost than S3 alone

### Option 3: LINE Rich Menu with File Upload

**Pros:**
- Native LINE integration
- Files stored by LINE

**Cons:**
- LINE file size limits
- More complex implementation
- Requires LINE API file upload

### Option 4: Database Storage (Not Recommended)

**Cons:**
- Database bloat
- Slow retrieval
- Not designed for binary files

---

## Recommended Implementation: S3 + Presigned URLs

### Step 1: Create S3 PDF Storage Module

Create `src/pdf_storage.py`:

```python
import boto3
import os
from datetime import datetime, timedelta
from botocore.exceptions import ClientError
import logging

logger = logging.getLogger(__name__)

class PDFStorage:
    """Handle PDF storage in S3 and URL generation"""
    
    def __init__(self):
        self.s3_client = boto3.client('s3')
        self.bucket_name = os.getenv('PDF_STORAGE_BUCKET', 'line-bot-pdf-reports')
        self.url_expiration_hours = int(os.getenv('PDF_URL_EXPIRATION_HOURS', '24'))
    
    def upload_pdf(self, pdf_bytes: bytes, ticker: str, date_str: str = None) -> str:
        """
        Upload PDF to S3 and return object key
        
        Args:
            pdf_bytes: PDF file bytes
            ticker: Ticker symbol (e.g., "DBS19")
            date_str: Optional date string (defaults to today)
            
        Returns:
            S3 object key (path)
        """
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
            logger.info(f"✅ PDF uploaded to S3: s3://{self.bucket_name}/{object_key}")
            return object_key
        except ClientError as e:
            logger.error(f"❌ Failed to upload PDF to S3: {e}")
            raise
    
    def get_presigned_url(self, object_key: str, expiration_hours: int = None) -> str:
        """
        Generate presigned URL for PDF download
        
        Args:
            object_key: S3 object key
            expiration_hours: URL expiration time (defaults to instance default)
            
        Returns:
            Presigned URL string
        """
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
        except ClientError as e:
            logger.error(f"❌ Failed to generate presigned URL: {e}")
            raise
    
    def upload_and_get_url(self, pdf_bytes: bytes, ticker: str) -> str:
        """
        Convenience method: Upload PDF and return presigned URL
        
        Args:
            pdf_bytes: PDF file bytes
            ticker: Ticker symbol
            
        Returns:
            Presigned URL string
        """
        object_key = self.upload_pdf(pdf_bytes, ticker)
        return self.get_presigned_url(object_key)
```

### Step 2: Update LINE Bot to Include PDF Link

Modify `src/line_bot.py`:

```python
from src.pdf_storage import PDFStorage

class LineBot:
    def __init__(self):
        # ... existing initialization ...
        self.pdf_storage = PDFStorage()
    
    def format_message_with_pdf_link(self, report_text: str, pdf_url: str, ticker: str) -> str:
        """
        Format message with PDF link at top, followed by report text
        
        Args:
            report_text: Current report text output
            pdf_url: Presigned URL to PDF
            ticker: Ticker symbol
            
        Returns:
            Formatted message in Thai
        """
        # Thai message for PDF link
        pdf_message = f"""📄 รายงานฉบับเต็ม: {pdf_url}

💡 รายงาน PDF ประกอบด้วยข้อมูลที่ละเอียดกว่า รวมถึง:
   • กราฟวิเคราะห์ทางเทคนิค
   • สถิติเปอร์เซ็นไทล์แบบละเอียด
   • การวิเคราะห์เปรียบเทียบ
   • คะแนนคุณภาพรายงาน

⏰ ลิงก์นี้ใช้งานได้ 24 ชั่วโมง

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{report_text}"""
        
        return pdf_message
    
    def handle_message(self, event):
        """Handle incoming message"""
        # ... existing code ...
        
        # After generating report
        report_text = self.agent.analyze_ticker(matched_ticker)
        
        # Generate PDF and get URL
        try:
            pdf_bytes = self.agent.generate_pdf_report(matched_ticker)
            pdf_url = self.pdf_storage.upload_and_get_url(pdf_bytes, matched_ticker)
            
            # Format message with PDF link
            final_message = self.format_message_with_pdf_link(report_text, pdf_url, matched_ticker)
            
            return final_message
        except Exception as e:
            logger.error(f"Failed to generate PDF: {e}")
            # Fallback: return text report only
            return report_text
```

### Step 3: Terraform Configuration

Add S3 bucket for PDF storage in `terraform/main.tf`:

```hcl
# S3 bucket for PDF reports
resource "aws_s3_bucket" "pdf_reports" {
  bucket = "line-bot-pdf-reports-${data.aws_caller_identity.current.account_id}"
  
  tags = {
    Name        = "line-bot-pdf-reports"
    Environment = "prod"
    Project     = "LineBot"
  }
}

# Bucket versioning (optional)
resource "aws_s3_bucket_versioning" "pdf_reports" {
  bucket = aws_s3_bucket.pdf_reports.id
  
  versioning_configuration {
    status = "Enabled"
  }
}

# Lifecycle policy - delete PDFs older than 30 days
resource "aws_s3_bucket_lifecycle_configuration" "pdf_reports" {
  bucket = aws_s3_bucket.pdf_reports.id
  
  rule {
    id     = "delete_old_pdfs"
    status = "Enabled"
    
    expiration {
      days = 30
    }
  }
}

# IAM policy for Lambda to access S3
resource "aws_iam_role_policy" "lambda_s3_pdf_access" {
  name = "lambda-s3-pdf-access"
  role = aws_iam_role.lambda_role.id
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:PutObject",
          "s3:GetObject",
          "s3:DeleteObject"
        ]
        Resource = "${aws_s3_bucket.pdf_reports.arn}/*"
      },
      {
        Effect = "Allow"
        Action = [
          "s3:ListBucket"
        ]
        Resource = aws_s3_bucket.pdf_reports.arn
      }
    ]
  })
}
```

### Step 4: Environment Variables

Add to Lambda environment variables:

```hcl
environment {
  variables = {
    # ... existing variables ...
    PDF_STORAGE_BUCKET      = aws_s3_bucket.pdf_reports.id
    PDF_URL_EXPIRATION_HOURS = "24"
  }
}
```

---

## Alternative: LINE File Upload API

If you prefer native LINE integration:

```python
def upload_pdf_to_line(self, pdf_bytes: bytes, ticker: str) -> str:
    """
    Upload PDF to LINE and return file URL
    
    Note: LINE Messaging API doesn't directly support file uploads.
    This would require using LINE Notify or LINE Rich Menu.
    """
    # LINE doesn't have direct file upload API
    # Would need to use LINE Notify or external storage
    pass
```

---

## Message Format Options

### Option A: Link at Top (Recommended)
```
📄 รายงานฉบับเต็ม: [PDF URL]

💡 รายงาน PDF ประกอบด้วยข้อมูลที่ละเอียดกว่า...

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[Current Report Text]
```

### Option B: Link at Bottom
```
[Current Report Text]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📄 ดาวน์โหลดรายงานฉบับเต็ม (PDF): [PDF URL]
⏰ ลิงก์ใช้งานได้ 24 ชั่วโมง
```

### Option C: Separate Message
Send PDF link as a separate LINE message (requires multiple messages)

---

## Cost Estimation

**S3 Storage:**
- Storage: $0.023 per GB/month
- PUT requests: $0.005 per 1,000 requests
- GET requests: $0.0004 per 1,000 requests
- Example: 1,000 PDFs/month @ 500KB each = ~$0.50/month

**Data Transfer:**
- First 1GB/month: Free
- After: $0.09 per GB

**Total estimated cost: < $5/month for moderate usage**

---

## Security Considerations

1. **Presigned URLs:**
   - Set appropriate expiration (24 hours recommended)
   - URLs are cryptographically signed
   - Cannot be guessed or brute-forced

2. **S3 Bucket:**
   - Keep bucket private (no public access)
   - Use IAM roles for access control
   - Enable versioning for recovery

3. **PDF Content:**
   - PDFs contain financial data - treat as sensitive
   - Consider encryption at rest (S3 default)
   - Log access for audit trail

---

## Implementation Checklist

- [ ] Create `src/pdf_storage.py` module
- [ ] Add S3 bucket in Terraform
- [ ] Update IAM role with S3 permissions
- [ ] Update `LineBot` class to generate PDFs
- [ ] Add PDF link formatting method
- [ ] Test PDF generation and upload
- [ ] Test presigned URL generation
- [ ] Test message formatting
- [ ] Add error handling for PDF failures
- [ ] Set up lifecycle policies for old PDFs
- [ ] Monitor S3 costs

---

## Testing

```python
# Test PDF storage
from src.pdf_storage import PDFStorage
from src.agent import TickerAnalysisAgent

agent = TickerAnalysisAgent()
storage = PDFStorage()

# Generate PDF
pdf_bytes = agent.generate_pdf_report("DBS19")

# Upload and get URL
pdf_url = storage.upload_and_get_url(pdf_bytes, "DBS19")
print(f"PDF URL: {pdf_url}")
```

---

## Next Steps

1. Implement Option 1 (S3 + Presigned URLs)
2. Test with a few tickers
3. Monitor costs and performance
4. Consider adding PDF caching (don't regenerate if exists)
5. Add analytics tracking for PDF downloads
