# Lambda Versioning Strategy

Zero-downtime deployment pattern using Lambda versions and aliases.

---

## Mental Model

```
$LATEST (mutable)          ← New code lands here first
    │
    │ test passes?
    ▼
Version N (immutable)      ← Snapshot created via publish-version
    │
    ▼
"live" alias               ← API Gateway invokes this
```

**Key Principle:** The `live` alias is the contract with API Gateway. Until you move that pointer, users get the old code.

---

## Why This Matters

- `$LATEST` is a staging area for testing
- Versions are immutable snapshots (can't be changed)
- Alias is the pointer that controls production traffic
- Terraform uses `ignore_changes = [function_version]` to let deploy scripts control the alias

---

## Deployment Flow

```bash
# 1. Update function code (moves $LATEST pointer)
aws lambda update-function-code \
  --function-name dr-daily-report-telegram-api-dev \
  --image-uri $ECR_REPO:$TAG

# 2. Wait for update to complete (CRITICAL - use waiter, not sleep)
aws lambda wait function-updated \
  --function-name dr-daily-report-telegram-api-dev

# 3. Test $LATEST via smoke test
aws lambda invoke \
  --function-name dr-daily-report-telegram-api-dev \
  --qualifier $LATEST \
  --payload '{"httpMethod": "GET", "path": "/api/v1/health"}' \
  /tmp/smoke-test.json

# 4. If test passes, publish immutable version
VERSION=$(aws lambda publish-version \
  --function-name dr-daily-report-telegram-api-dev \
  --query 'Version' \
  --output text)

# 5. Update "live" alias to new version (zero-downtime cutover)
aws lambda update-alias \
  --function-name dr-daily-report-telegram-api-dev \
  --name live \
  --function-version $VERSION
```

---

## Rollback Strategy

Instant rollback - just move the alias pointer back:

```bash
# Rollback to previous version (no rebuild needed!)
aws lambda update-alias \
  --function-name dr-daily-report-telegram-api-dev \
  --name live \
  --function-version <previous-version-number>
```

Previous versions are immutable snapshots - always available for instant rollback.

---

## Monitoring Deployment Status

**CRITICAL: Never use `sleep X` to wait for deployments.**

```bash
# WRONG: Time-based waiting
aws lambda update-function-code ...
sleep 60  # ❌ Might not be ready, or wastes time

# RIGHT: Use AWS waiters (blocks until actual completion)
aws lambda update-function-code ...
aws lambda wait function-updated --function-name $FUNC  # ✅ Blocks until done
```

**Why waiters matter:**
- **Accuracy**: Know when deployment is ACTUALLY done, not guessing
- **Debugging**: Don't chase phantom bugs that are just timing issues
- **Reliability**: CI/CD scripts fail properly when deployments fail

---

## Terraform Integration

Terraform creates infrastructure but doesn't manage version/alias (by design):

```hcl
# terraform/telegram_api.tf
resource "aws_lambda_alias" "live" {
  name             = "live"
  function_name    = aws_lambda_function.telegram_api.function_name
  function_version = "$LATEST"  # Initial value

  lifecycle {
    ignore_changes = [function_version]  # Let deploy scripts manage this
  }
}
```

**Why `ignore_changes`:**
- Terraform declares infrastructure (Lambda exists, alias exists)
- Deploy scripts manage pointer (which version is "live")
- Separation of concerns: infra vs deployment

---

## Complete Deployment Script Example

```bash
#!/bin/bash
set -euo pipefail

FUNCTION_NAME="dr-daily-report-telegram-api-dev"
ECR_REPO="755283537543.dkr.ecr.ap-southeast-1.amazonaws.com/dr-daily-report-lambda-dev"
TAG="$1"  # e.g., "sha-abc123"

echo "📦 Updating Lambda to $TAG..."

# 1. Update function code
aws lambda update-function-code \
  --function-name $FUNCTION_NAME \
  --image-uri $ECR_REPO:$TAG \
  --query 'FunctionArn' \
  --output text

# 2. Wait for update (CRITICAL - blocks until done)
echo "⏳ Waiting for Lambda update to complete..."
aws lambda wait function-updated --function-name $FUNCTION_NAME
echo "✅ Lambda updated"

# 3. Smoke test $LATEST
echo "🧪 Running smoke test on $LATEST..."
aws lambda invoke \
  --function-name $FUNCTION_NAME \
  --qualifier '$LATEST' \
  --payload '{"httpMethod": "GET", "path": "/api/v1/health"}' \
  /tmp/smoke-test.json

if ! grep -q '"statusCode":200' /tmp/smoke-test.json; then
  echo "❌ Smoke test failed!"
  cat /tmp/smoke-test.json
  exit 1
fi
echo "✅ Smoke test passed"

# 4. Publish immutable version
echo "📸 Publishing new version..."
VERSION=$(aws lambda publish-version \
  --function-name $FUNCTION_NAME \
  --query 'Version' \
  --output text)
echo "✅ Published version: $VERSION"

# 5. Update "live" alias (zero-downtime cutover)
echo "🔄 Updating 'live' alias to version $VERSION..."
aws lambda update-alias \
  --function-name $FUNCTION_NAME \
  --name live \
  --function-version $VERSION
echo "✅ Deployment complete! Version $VERSION is now live"
```

---

## Comparison with Other Deployment Methods

| Method | Downtime | Rollback Speed | Complexity |
|--------|----------|----------------|------------|
| Direct update | Yes (during deploy) | Slow (rebuild) | Low |
| Blue/Green (separate functions) | No | Fast | High |
| **Alias-based (our approach)** | **No** | **Instant** | **Medium** |

---

## See Also

- [Deployment Workflow](WORKFLOW.md) - Complete deployment process
- [CI/CD Architecture](CI_CD.md) - GitHub Actions integration
- [Monitoring Guide](MONITORING.md) - Proper waiter usage
