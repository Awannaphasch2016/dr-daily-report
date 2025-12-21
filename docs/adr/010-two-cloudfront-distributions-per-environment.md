# ADR-010: Two CloudFront Distributions Per Environment

**Status:** ✅ Accepted
**Date:** 2024-02
**Deciders:** Development Team

## Context

Frontend deployments to CloudFront face a critical problem: cache invalidation is atomic and immediate. Once invalidated, all users instantly see new files. If E2E tests run AFTER invalidation and fail, users have already been exposed to the broken frontend.

### The Problem

**Traditional Single CloudFront Deployment:**
```
S3 Sync → CloudFront Invalidation → Users see new files → E2E tests run
                                    ↑
                                    └─ If tests fail, damage already done!
```

**Why This Fails:**
- CloudFront cache invalidation is immediate (users see new files within seconds)
- E2E tests take 2-5 minutes to run
- No way to "test before users see" with a single distribution
- Rollback requires another invalidation (more downtime)

### CloudFront Constraints

- Cache invalidation cannot be delayed or staged
- No "canary release" support for static content
- Client-side `Cache-Control: no-cache` headers are NOT honored by CloudFront edge caches
- Once invalidated, edge caches immediately request new objects from origin

## Decision

Create TWO CloudFront distributions per environment: TEST and APP.

### Deployment Flow

```
Same S3 Bucket
     │
     ├── TEST CloudFront → Invalidated first
     │                     E2E tests run against TEST
     │                     Smoke tests verify
     │
     └── APP CloudFront  → Invalidated ONLY after E2E tests pass
                          Users always access APP
```

### Zero-Risk Pattern

1. **Sync S3**: Upload new files to bucket (doesn't affect users - CloudFront serves cached version)
2. **Invalidate TEST**: Clear TEST distribution cache
3. **Run E2E Tests**: Playwright tests run against TEST distribution URL
4. **Verify Tests Pass**: If any test fails → STOP, do NOT invalidate APP
5. **Invalidate APP**: Only if E2E tests pass → clear APP distribution cache
6. **Users See Update**: Users get new version only after validation

### Configuration

**Terraform:**
```hcl
# TEST distribution - for E2E testing
resource "aws_cloudfront_distribution" "test" {
  comment = "dr-daily-report TEST CloudFront - ${var.environment}"
  # Same origin as APP (same S3 bucket)
  # Different distribution ID
}

# APP distribution - for users
resource "aws_cloudfront_distribution" "app" {
  comment = "dr-daily-report APP CloudFront - ${var.environment}"
  # Same origin as TEST (same S3 bucket)
  # Different distribution ID
}
```

**GitHub Secrets (per environment):**
- `CLOUDFRONT_TEST_DISTRIBUTION_ID`: E2E test target
- `CLOUDFRONT_DISTRIBUTION_ID`: User-facing (only invalidated after tests pass)

**CI/CD Implementation:**
```yaml
- name: Sync S3
  run: aws s3 sync dist/ s3://bucket/ --delete

- name: Invalidate TEST CloudFront
  run: |
    aws cloudfront create-invalidation \
      --distribution-id ${{ secrets.CLOUDFRONT_TEST_DISTRIBUTION_ID }} \
      --paths "/*"

- name: Wait for TEST invalidation
  run: |
    INVALIDATION_ID=$(aws cloudfront list-invalidations ...)
    aws cloudfront wait invalidation-completed \
      --distribution-id ${{ secrets.CLOUDFRONT_TEST_DISTRIBUTION_ID }} \
      --id $INVALIDATION_ID

- name: Run E2E tests against TEST
  run: |
    E2E_BASE_URL=https://test-d123.cloudfront.net \
    npx playwright test

- name: Invalidate APP CloudFront (only if E2E passed!)
  if: success()
  run: |
    aws cloudfront create-invalidation \
      --distribution-id ${{ secrets.CLOUDFRONT_DISTRIBUTION_ID }} \
      --paths "/*"
```

## Consequences

### Positive

- ✅ **Zero-Risk**: Users NEVER see untested frontend code
- ✅ **Mirrors Backend Pattern**: Like Lambda's `$LATEST` (TEST) vs `live` alias (APP)
- ✅ **Instant Rollback**: Simply don't invalidate APP = users keep old working version
- ✅ **No S3 Duplication**: Both CloudFronts serve same bucket (no storage cost)
- ✅ **Fail-Safe Default**: If E2E fails, APP stays on last known good version
- ✅ **Separate Test Environment**: Can test against TEST URL without affecting users

### Negative

- ❌ **2x CloudFront Costs**: ~$1-5/month per distribution per environment
- ❌ **More GitHub Secrets**: Need TEST and APP distribution IDs
- ❌ **Longer Deployment**: Must wait for TEST invalidation before running E2E
- ❌ **Configuration Complexity**: Two distributions to manage

### Cost Analysis

**Monthly CloudFront Costs:**
- Single distribution: $1-3/month (low traffic)
- Two distributions: $2-6/month
- **Trade-off**: $3/month extra cost vs zero-risk deployments

**Verdict:** Safety > $3/month cost.

## Alternatives Considered

### Alternative 1: Separate S3 Buckets (Blue/Green)

**Example:**
```
s3://app-blue/   → CloudFront (users)
s3://app-green/  → Deploy here, test, then swap CloudFront origin
```

**Why Rejected:**
- **Doubles Storage Costs**: Two copies of all frontend files
- **Sync Complexity**: Must copy files between buckets
- **Origin Switching**: Changing CloudFront origin triggers full cache invalidation anyway
- **More Infrastructure**: Two buckets to manage, backup, secure

### Alternative 2: S3 Versioning + Rollback

**Why Rejected:**
- S3 versioning doesn't prevent CloudFront from serving new files
- Rollback still requires invalidation (doesn't prevent initial exposure)
- Complex: Must track which object versions are "good"

### Alternative 3: Feature Flags in Frontend Code

**Example:**
```javascript
if (featureFlags.newDashboard) {
  // New code (potentially broken)
} else {
  // Old code (known working)
}
```

**Why Rejected:**
- **Code Bloat**: Feature flags accumulate over time
- **Still Deploys Broken Code**: Just hides it behind flag
- **Runtime Overhead**: Checking flags on every render
- **Doesn't Prevent Bugs**: Can't test "no feature flag" path

### Alternative 4: CloudFront Canary Releases (Lambda@Edge)

**Why Rejected:**
- CloudFront doesn't natively support canary for static content
- Requires Lambda@Edge (more complexity + cost)
- Lambda@Edge has cold start issues for every request
- Overkill for small project

## References

- **Terraform Config**: `terraform/frontend.tf` (defines both distributions)
- **CI/CD Pipeline**: `.github/workflows/deploy-frontend.yml`
- **Distribution IDs**: GitHub Secrets per environment
- **Backend Pattern**: Similar to Lambda `$LATEST` vs `live` alias (ADR-009)

## Decision Drivers

1. **User Safety**: Never expose users to untested code
2. **Deployment Confidence**: E2E tests must pass before user exposure
3. **CloudFront Constraints**: Cache invalidation is atomic and immediate
4. **Cost Acceptable**: $3/month extra cost < risk of broken deployments

## Historical Context

Implemented after realizing CloudFront doesn't honor client-side `Cache-Control: no-cache` headers. Initial attempts to "test before users see" with a single distribution all failed - there's no way to delay or stage cache invalidation.

This pattern mirrors the Lambda alias pattern (ADR-009) that solved the same problem for backend deployments: test in mutable environment ($LATEST/TEST), promote to immutable pointer (alias/APP) only after validation.

## Distribution Naming Convention

**Comment Field Pattern:**
- TEST: `"dr-daily-report TEST CloudFront - ${environment}"`
- APP: `"dr-daily-report APP CloudFront - ${environment}"`

**Why This Matters:**
- AWS CLI queries use comment field to identify distributions
- Infrastructure-deployment contract validation relies on consistent naming
- Makes distribution purpose obvious in AWS Console

**Example Validation:**
```bash
# Find TEST distribution by comment
aws cloudfront list-distributions \
  --query 'DistributionList.Items[?Comment==`dr-daily-report TEST CloudFront - dev`].Id' \
  --output text
```

## Rollback Strategy

**Traditional Rollback (with single distribution):**
```
Deploy broken code → Invalidate → Users see bug → Rollback → Invalidate again
                                 ↑
                                 └─ 5-10 minutes of downtime
```

**Two-Distribution Rollback:**
```
Deploy broken code → Invalidate TEST → E2E fails → Don't invalidate APP
                                      ↑
                                      └─ Zero user impact, APP still serves old version
```

**Instant Fix:** Simply don't invalidate APP distribution. Users continue seeing last known good version indefinitely.

## Infrastructure-Deployment Contract

This decision requires Infrastructure-Deployment Contract Validation (from CLAUDE.md):

**Pattern:**
```yaml
# First job in deployment pipeline
validate-deployment-config:
  steps:
    - name: Validate CloudFront Distributions
      run: |
        # Query actual AWS infrastructure
        ACTUAL_TEST=$(aws cloudfront list-distributions \
          --query 'DistributionList.Items[?Comment==`dr-daily-report TEST CloudFront - dev`].Id' \
          --output text)

        ACTUAL_APP=$(aws cloudfront list-distributions \
          --query 'DistributionList.Items[?Comment==`dr-daily-report APP CloudFront - dev`].Id' \
          --output text)

        # Validate GitHub secrets match reality
        if [ "$ACTUAL_TEST" != "${{ secrets.CLOUDFRONT_TEST_DISTRIBUTION_ID }}" ]; then
          echo "❌ Mismatch: CLOUDFRONT_TEST_DISTRIBUTION_ID"
          exit 1
        fi

        if [ "$ACTUAL_APP" != "${{ secrets.CLOUDFRONT_DISTRIBUTION_ID }}" ]; then
          echo "❌ Mismatch: CLOUDFRONT_DISTRIBUTION_ID"
          exit 1
        fi
```

**Why This Pattern:**
- Catches configuration drift before deployment
- Self-healing: Automatically detects when secrets are stale
- Fails fast (< 30 seconds) instead of mid-deployment

## E2E Test Requirements

With two distributions, E2E tests must target TEST distribution URL:

```javascript
// playwright.config.ts
export default {
  use: {
    baseURL: process.env.E2E_BASE_URL || 'http://localhost:3000',
  },
};

// CI sets: E2E_BASE_URL=https://test-d123.cloudfront.net
// Users access: https://app-d456.cloudfront.net (different distribution)
```

**Critical:** E2E tests MUST run against TEST distribution URL, not APP distribution URL.
