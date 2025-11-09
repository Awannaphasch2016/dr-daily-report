# S3 + /tmp Hybrid Deployment Implementation Summary

## ✅ Implementation Complete

All code changes have been implemented for the S3 + /tmp hybrid deployment approach. This allows Lambda to load heavy data science dependencies (numpy, pandas, matplotlib) from S3 at runtime, bypassing the 250MB deployment package limit.

## Changes Made

### 1. **New Files Created**
- `requirements_heavy.txt` - Contains numpy, pandas, matplotlib (75MB ZIP uploaded to S3)
- `src/dependency_loader.py` - Handles S3 download and extraction of heavy dependencies
- `test_s3_dependency_loading.py` - Test script for verifying dependency loading

### 2. **Files Modified**
- `src/lambda_handler.py` - Added lazy loading call at module level
- `requirements_minimal.txt` - Removed heavy dependencies, kept lightweight ones
- `requirements_nodeps.txt` - Updated comment to reflect S3 approach
- `terraform/main.tf` - Removed Lambda Layer, added S3 read permissions

### 3. **S3 Resources**
- Heavy dependencies ZIP uploaded to: `s3://line-bot-ticker-deploy-20251030/python-libs/data-science-libs.zip` (75MB)

## Architecture

```
Lambda Cold Start Flow:
1. Lambda handler starts
2. dependency_loader.py checks /tmp/python-libs
3. If not exists → Download from S3 → Extract to /tmp → Add to sys.path
4. Import heavy modules (numpy, pandas, matplotlib)
5. Continue normal execution

Warm Invocations:
- Libraries already in /tmp → Skip download → Fast startup
```

## Deployment Steps

### 1. Verify Terraform Configuration
```bash
cd terraform
terraform plan
```

### 2. Deploy Infrastructure
```bash
terraform apply
```

This will:
- Build deployment package with minimal dependencies (~20-30MB)
- Upload to S3
- Update Lambda function
- Remove Lambda Layer reference
- Add S3 read permissions

### 3. Test Deployment

#### Option A: Test via Lambda Function URL
```bash
# Get function URL
aws lambda get-function-url-config --function-name line-bot-ticker-report

# Test with a ticker request
curl -X POST <FUNCTION_URL> \
  -H "Content-Type: application/json" \
  -d '{"events":[{"type":"message","message":{"type":"text","text":"PFIZER19"}}]}'
```

#### Option B: Test Locally (with mocked S3)
```bash
python3 test_s3_dependency_loading.py
```

## Monitoring

### Check CloudWatch Logs
```bash
aws logs tail /aws/lambda/line-bot-ticker-report --follow
```

Look for:
- `"Downloading heavy dependencies from s3://..."` - Cold start
- `"Heavy dependencies already loaded from /tmp"` - Warm start
- `"Heavy dependencies loaded successfully"` - Success

### Expected Behavior

**Cold Start (first invocation):**
- Download time: ~2-5 seconds (depends on network)
- Extraction time: ~1-2 seconds
- Total cold start penalty: ~3-7 seconds

**Warm Start (subsequent invocations):**
- No download needed
- Libraries reused from /tmp
- Normal execution speed

## Troubleshooting

### Issue: ImportError for numpy/pandas/matplotlib
**Solution:** Check CloudWatch logs for dependency_loader errors. Verify:
- S3 bucket permissions are correct
- S3 object exists at correct path
- /tmp has sufficient space (512MB default, can increase to 10GB)

### Issue: Slow cold starts
**Expected:** First invocation will be slower due to S3 download. Subsequent invocations within the same container reuse /tmp.

### Issue: Lambda timeout
**Solution:** Increase timeout in terraform/main.tf if needed. Cold start + processing may take longer.

## Configuration

### S3 Bucket/Key
Configured in `src/dependency_loader.py`:
```python
S3_BUCKET = "line-bot-ticker-deploy-20251030"
S3_KEY = "python-libs/data-science-libs.zip"
```

### /tmp Directory
```python
TMP_DIR = "/tmp/python-libs"
```

### Ephemeral Storage
Current: 512MB (default)
Can increase up to 10GB in terraform if needed:
```hcl
ephemeral_storage {
  size = 10240  # 10GB in MB
}
```

## Benefits

✅ **No new AWS permissions needed** - Uses existing S3 access
✅ **Bypasses 250MB ZIP limit** - Heavy deps stored separately
✅ **Works with current IAM setup** - No ECR permissions required
✅ **Warm invocations unaffected** - Libraries cached in /tmp

## Trade-offs

⚠️ **Cold start penalty** - +3-7 seconds on first invocation
⚠️ **/tmp space usage** - ~75MB for extracted libraries
⚠️ **Network dependency** - Requires S3 access (usually reliable)

## Next Steps

1. Run `terraform apply` to deploy changes
2. Test with a real ticker request
3. Monitor CloudWatch logs for any issues
4. Consider increasing ephemeral storage if needed
5. Monitor cold start metrics vs warm start metrics
