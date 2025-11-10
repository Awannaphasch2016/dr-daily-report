# PDF Storage & LINE Integration - Implementation Summary

## ✅ Implementation Complete

### Files Created/Modified

1. **`src/pdf_storage.py`** (NEW)
   - `PDFStorage` class for S3 integration
   - Methods: `upload_pdf()`, `get_presigned_url()`, `upload_and_get_url()`
   - Handles errors gracefully, works in Lambda and local environments

2. **`src/line_bot.py`** (MODIFIED)
   - Added `PDFStorage` import and initialization
   - Added `format_message_with_pdf_link()` method (concise format)
   - Updated `handle_message()` to generate PDFs and include links
   - Graceful fallback to text-only if PDF generation fails

3. **`terraform/main.tf`** (MODIFIED)
   - Added S3 bucket for PDF storage
   - Added lifecycle policy (delete after 30 days)
   - Added IAM permissions for Lambda to access PDF bucket
   - Added environment variables: `PDF_STORAGE_BUCKET`, `PDF_URL_EXPIRATION_HOURS`

4. **`terraform/outputs.tf`** (MODIFIED)
   - Added `pdf_storage_bucket` output

---

## 📋 Message Format (Concise)

```
📄 รายงานฉบับเต็ม: [PDF URL]
⏰ ใช้งานได้ 24 ชั่วโมง

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[Current Report Text]
```

---

## 🔧 How It Works

1. **User requests ticker** (e.g., "DBS19")
2. **Bot generates text report** (existing flow)
3. **Bot generates PDF** (new)
4. **PDF uploaded to S3** → `s3://bucket/reports/DBS19/20251110/DBS19_report_20251110_143022.pdf`
5. **Presigned URL generated** (valid 24 hours)
6. **Message formatted** with PDF link at top + report text below
7. **User receives message** with clickable PDF link

---

## 🛡️ Error Handling

- **PDF generation fails**: Falls back to text-only report
- **S3 upload fails**: Falls back to text-only report
- **Local environment**: PDF storage gracefully disabled
- **All errors logged**: For debugging without exposing to users

---

## 📦 S3 Structure

```
s3://line-bot-pdf-reports-{account-id}/
  └── reports/
      └── DBS19/
          └── 20251110/
              └── DBS19_report_20251110_143022.pdf
```

---

## ⚙️ Configuration

**Environment Variables:**
- `PDF_STORAGE_BUCKET`: S3 bucket name (auto-set by Terraform)
- `PDF_URL_EXPIRATION_HOURS`: URL expiration (default: 24)

**Lifecycle Policy:**
- PDFs auto-deleted after 30 days

---

## 🚀 Next Steps

1. **Deploy**: Run `terraform apply`
2. **Test**: Send ticker to LINE bot
3. **Verify**: Check PDF link works, S3 bucket has files
4. **Monitor**: Check CloudWatch logs for PDF generation

---

## 💰 Cost Estimate

- **Storage**: ~$0.023/GB/month
- **Requests**: ~$0.005 per 1,000 uploads
- **Total**: ~$0.50-5/month for moderate usage

---

## ✅ Testing Checklist

- [ ] Deploy Terraform changes
- [ ] Test PDF generation locally (optional)
- [ ] Test with LINE bot (send ticker)
- [ ] Verify PDF link works
- [ ] Check S3 bucket has PDFs
- [ ] Verify presigned URLs expire correctly
- [ ] Test error handling (simulate PDF failure)
- [ ] Monitor CloudWatch logs
