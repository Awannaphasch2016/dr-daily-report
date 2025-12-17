# PDF Storage & LINE Integration - Quick Reference

## 🎯 Recommended Approach: AWS S3 + Presigned URLs

### Why This Approach?
- ✅ Secure (temporary URLs, not public)
- ✅ Cost-effective (~$5/month)
- ✅ Scalable
- ✅ Easy to implement
- ✅ Can set expiration (24 hours recommended)

---

## 📋 Implementation Steps

### 1. Create PDF Storage Module (`src/pdf_storage.py`)
- Upload PDFs to S3
- Generate presigned URLs (24h expiration)
- Handle errors gracefully

### 2. Update LINE Bot (`src/line_bot.py`)
- Generate PDF after analysis
- Upload to S3
- Format message with PDF link at top
- Fallback to text-only if PDF fails

### 3. Terraform Configuration
- Add S3 bucket for PDFs
- Configure lifecycle (delete after 30 days)
- Add IAM permissions for Lambda

---

## 💬 Thai Message Options

### Option 1: Professional & Informative (Recommended)
```
📄 รายงานฉบับเต็ม: [PDF URL]

💡 รายงาน PDF ประกอบด้วยข้อมูลที่ละเอียดกว่า รวมถึง:
   • กราฟวิเคราะห์ทางเทคนิค
   • สถิติเปอร์เซ็นไทล์แบบละเอียด
   • การวิเคราะห์เปรียบเทียบ
   • คะแนนคุณภาพรายงาน

⏰ ลิงก์นี้ใช้งานได้ 24 ชั่วโมง

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[Current Report Text]
```

### Option 2: Concise
```
📄 รายงานฉบับเต็ม: [PDF URL]
⏰ ใช้งานได้ 24 ชั่วโมง

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[Current Report Text]
```

### Option 3: Friendly & Casual
```
📄 ดูรายงานฉบับเต็มได้ที่: [PDF URL]

รายงาน PDF มีข้อมูลครบถ้วนกว่า รวมกราฟและสถิติละเอียด
ลิงก์ใช้งานได้ 24 ชั่วโมงนะครับ 📊

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[Current Report Text]
```

### Option 4: Minimal
```
📄 รายงาน PDF: [PDF URL]

[Current Report Text]
```

---

## 🔧 Quick Implementation

### Core Code Structure:

```python
# In handle_message() method:

# 1. Generate text report (existing)
report_text = self.agent.analyze_ticker(matched_ticker)

# 2. Generate PDF
try:
    pdf_bytes = self.agent.generate_pdf_report(matched_ticker)
    pdf_url = self.pdf_storage.upload_and_get_url(pdf_bytes, matched_ticker)
    
    # 3. Format message
    message = f"""📄 รายงานฉบับเต็ม: {pdf_url}

💡 รายงาน PDF ประกอบด้วยข้อมูลที่ละเอียดกว่า...

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{report_text}"""
    
    return message
except Exception as e:
    # Fallback: return text only
    logger.warning(f"PDF generation failed: {e}")
    return report_text
```

---

## 💰 Cost Breakdown

| Item | Cost |
|------|------|
| S3 Storage (1GB) | $0.023/month |
| PUT Requests (1K) | $0.005 |
| GET Requests (1K) | $0.0004 |
| Data Transfer (1GB) | $0.09 |
| **Total (1K PDFs/month)** | **~$0.50-5/month** |

---

## 🚀 Alternative Options

### Option B: CloudFront (Public URLs)
- Faster delivery
- No expiration
- Public access (less secure)
- Higher cost

### Option C: LINE Rich Menu
- Native LINE integration
- More complex
- File size limits

---

## ✅ Implementation Checklist

- [ ] Create `src/pdf_storage.py`
- [ ] Add S3 bucket in Terraform
- [ ] Update IAM permissions
- [ ] Modify `LineBot.handle_message()`
- [ ] Add PDF link formatting
- [ ] Test end-to-end
- [ ] Add error handling
- [ ] Set lifecycle policies
- [ ] Monitor costs

---

## 📝 Notes

- PDFs are regenerated each time (can add caching later)
- URLs expire after 24 hours (configurable)
- Old PDFs auto-deleted after 30 days
- Fallback to text-only if PDF fails
- All PDFs stored in: `s3://bucket/reports/TICKER/DATE/file.pdf`
