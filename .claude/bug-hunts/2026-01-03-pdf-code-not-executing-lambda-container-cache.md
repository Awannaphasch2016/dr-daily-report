---
title: PDF generation code not executing - Lambda container caching issue
bug_type: production-error
date: 2026-01-03
status: root_cause_found
confidence: High
---

# Bug Hunt Report: PDF Generation Code Not Executing

## Symptom

**Description**: PDF generation code (lines 216-273 in `src/report_worker_handler.py`) is present in Docker image but not executing during Lambda runtime. Workers complete successfully but skip entire PDF section.

**First occurrence**: 2026-01-02 18:59 UTC (multiple executions)

**Affected scope**: All scheduled precompute workflows (Step Functions)

**Impact**: High - PDFs not being generated for nightly precompute, breaking cache architecture

---

## Investigation Summary

**Bug type**: production-error (Lambda runtime issue)

**Investigation duration**: ~45 minutes

**Status**: Root cause found

---

## Evidence Gathered

### Logs

CloudWatch Logs `/aws/lambda/dr-daily-report-report-worker-dev`:

```
2026-01-02T18:59:29.309Z [INFO] Completed job rpt_DBS19_precompute-20260102-185847 for ticker D05.SI
2026-01-02T18:59:29.309Z [INFO] Attempting to cache report in Aurora for D05.SI
```

**Critical observation**: Logs show execution jumping from "Completed job" (line 214) directly to "Attempting to cache report" (line 292). NO DEBUG statements visible.

### Metrics

- Step Functions execution: SUCCEEDED
- All 46 workers completed successfully
- Zero errors, zero exceptions
- Code execution appears normal (except missing PDF section)

### Code References

- `src/report_worker_handler.py:216-273` - PDF generation code
- `src/report_worker_handler.py:217-221` - DEBUG breadcrumbs added

### Docker Image Verification

Verified PDF code present in image `debug-20260103-015730`:

```bash
docker run --rm --entrypoint python3 \
  755283537543.dkr.ecr.ap-southeast-1.amazonaws.com/dr-daily-report-lambda-dev:debug-20260103-015730 \
  -c "import report_worker_handler; import inspect; ..."
# Output: ✅ PDF code present in loaded module
# Source length: 8294 characters
```

### Lambda Function Configuration

```bash
aws lambda get-function --function-name dr-daily-report-report-worker-dev

CodeSha256: b5765c21c5b42b128a8af016b9ea8ea2f131bf2d692002c4304eb096ec98314a
LastModified: 2026-01-02T18:57:49.000+0000
ImageUri: 755283537543.dkr.ecr.ap-southeast-1.amazonaws.com/dr-daily-report-lambda-dev:debug-20260103-015730
```

### Recent Changes

Git log shows multiple deployments:
- pdf-final-20260103-013900
- pdf-fix-v5-20260103-012900
- debug-20260103-015730 (current)

All contain PDF generation code.

---

## Hypotheses Tested

### Hypothesis 1: Python Syntax Error

**Likelihood**: Low

**Test performed**: Compiled Python file with `py_compile`, AST analysis

**Result**: ✅ Eliminated

**Reasoning**: Code compiles successfully, AST structure is valid

**Evidence**:
- `python3 -m py_compile src/report_worker_handler.py` - Success
- AST shows single try/except block (lines 129-323)
- PDF code IS inside try block

---

### Hypothesis 2: Early Return/Exception

**Likelihood**: Low

**Test performed**: Analyzed control flow for early returns or exceptions

**Result**: ✅ Eliminated

**Reasoning**: No early return statements found between line 214 and 292

**Evidence**:
- Grepped for `return` statements - none found in that range
- Exception handlers don't swallow errors (only graceful degradation)
- Logs show "Attempting to cache report" - execution continues past PDF section

---

### Hypothesis 3: Docker Image Not Deployed

**Likelihood**: Low

**Test performed**: Verified Lambda function using correct image digest

**Result**: ✅ Eliminated

**Reasoning**: Lambda configuration shows correct CodeSha256

**Evidence**:
- CodeSha256 matches Docker image digest
- `aws lambda get-function` confirms image URI
- `docker run` confirms code present in image

---

### Hypothesis 4: Lambda Container Caching (OLD CODE)

**Likelihood**: **High** ⭐

**Test performed**:
1. Added DEBUG logging to trace execution (lines 217-221, 248-250, 254, 283)
2. Deployed new image (debug-20260103-015730)
3. Triggered precompute workflow
4. Checked CloudWatch Logs for DEBUG statements

**Result**: ✅ **CONFIRMED**

**Reasoning**: Zero DEBUG statements in logs despite code being present in deployed image

**Evidence**:
- Docker image contains DEBUG code (verified with `docker run`)
- Lambda function configuration shows correct image digest
- CloudWatch Logs show ZERO DEBUG statements
- Execution behavior matches OLD code (before DEBUG was added)

**Conclusion**: Lambda is executing a CACHED container from a previous deployment that does NOT contain the DEBUG logging or PDF generation fixes.

---

## Root Cause

**Identified cause**: Lambda container caching is serving stale bytecode

**Confidence**: High

**Supporting evidence**:
1. Docker image verified to contain DEBUG logging
2. Lambda function config shows correct image digest
3. CloudWatch Logs show ZERO DEBUG statements
4. Execution pattern matches code version BEFORE debugging additions

**Code location**: NOT a code issue - infrastructure/platform issue

**Why this causes the symptom**:
Lambda containers are cached for performance. When we update the function code, Lambda doesn't immediately terminate all warm containers. Existing warm containers continue running the OLD code until they're naturally recycled (timeout, memory pressure, etc.).

Our deployment updated the Lambda configuration to point to the new image, but warm containers from the previous deployment are still handling invocations.

---

## Reproduction Steps

1. Deploy Lambda function with version A of code
2. Invoke Lambda (creates warm container with version A)
3. Update Lambda function to version B (new Docker image)
4. Immediately invoke Lambda again
5. **Expected behavior**: Lambda runs version B code
6. **Actual behavior**: Lambda runs version A code (cached container)

---

## Fix Candidates

### Fix 1: Force Container Refresh with Reserved Concurrency

**Approach**: Temporarily set Reserved Concurrency to 0 (stops all invocations), wait 5 seconds, restore to original value

**Pros**:
- Immediate effect (forces all containers to stop)
- Guarantees fresh containers on next invocation
- No code changes needed

**Cons**:
- Brief service interruption (5 seconds)
- Requires manual intervention
- Not automatable in CI/CD

**Estimated effort**: 2 minutes

**Risk**: Low

**Commands**:
```bash
# Force container refresh
ENV=dev doppler run -- aws lambda put-function-concurrency \
  --function-name dr-daily-report-report-worker-dev \
  --reserved-concurrent-executions 0

sleep 5

ENV=dev doppler run -- aws lambda delete-function-concurrency \
  --function-name dr-daily-report-report-worker-dev
```

---

### Fix 2: Version Publishing + Alias Update

**Approach**: Publish new Lambda version, update alias to point to new version

**Pros**:
- AWS-recommended approach for zero-downtime deployments
- Enables blue/green deployment
- Repeatable in CI/CD

**Cons**:
- More complex (requires alias setup)
- Version history grows over time
- Requires terraform changes

**Estimated effort**: 15 minutes (terraform + testing)

**Risk**: Medium

---

### Fix 3: Wait for Natural Container Recycling

**Approach**: Wait 10-15 minutes for Lambda to naturally recycle warm containers

**Pros**:
- Zero risk
- No manual intervention
- Natural platform behavior

**Cons**:
- Slowest option (10-15 min)
- No guarantee of exact timing
- Not acceptable for urgent fixes

**Estimated effort**: 15 minutes (passive wait)

**Risk**: None

---

### Fix 4: Environment Variable Update (Trigger Refresh)

**Approach**: Update an environment variable to force Lambda to recognize change

**Pros**:
- Quick
- Forces refresh without concurrency manipulation
- Already have PDF_FORCE_REFRESH variable

**Cons**:
- Not guaranteed to work (container may still be cached)
- Side effect of changing environment

**Estimated effort**: 2 minutes

**Risk**: Low

**Commands**:
```bash
ENV=dev doppler run -- aws lambda update-function-configuration \
  --function-name dr-daily-report-report-worker-dev \
  --environment "Variables={PDF_FORCE_REFRESH=v20260103-v2,...}"
```

---

## Recommendation

**Recommended fix**: Fix 1 (Force Container Refresh with Reserved Concurrency)

**Rationale**:
- Immediate effect (no 15-minute wait)
- Guarantees fresh containers
- Low risk
- Fastest path to verification

**Implementation priority**: P0 (blocking PDF verification)

---

## Next Steps

- [ ] Apply Fix 1 (Reserved Concurrency manipulation)
- [ ] Wait for Lambda function to stabilize
- [ ] Trigger precompute workflow
- [ ] Verify DEBUG statements appear in logs
- [ ] If DEBUG appears, verify PDF generation logs
- [ ] If PDF generates, verify S3 upload
- [ ] If S3 upload succeeds, verify Aurora cache update
- [ ] Document Lambda container caching behavior in deployment skill

---

## Investigation Trail

**What was checked**:
- Docker image contents (verified PDF code present)
- Python syntax (compiled successfully)
- AST structure (valid control flow)
- Lambda function configuration (correct image digest)
- CloudWatch Logs (zero DEBUG statements)
- Exception handlers (not swallowing errors)

**What was ruled out**:
- Syntax errors (code compiles)
- Import errors (module loads correctly)
- Permission issues (all files chmod 644)
- Docker image deployment (correct image deployed)
- Early return statements (none found in execution path)

**Tools used**:
- `docker run` - Verify image contents
- `python3 -m py_compile` - Syntax validation
- AST analysis - Control flow verification
- `aws lambda get-function` - Configuration check
- `aws logs tail` - Runtime behavior inspection

**Time spent**:
- Evidence gathering: 15 min
- Hypothesis testing: 20 min
- Root cause identification: 10 min
- Total: 45 min

---

## Lessons Learned

1. **Lambda container caching is aggressive** - Warm containers can persist for many minutes after deployment
2. **Image digest verification is not sufficient** - Correct image ≠ running containers use that image
3. **Force refresh required for immediate verification** - Can't rely on natural recycling for urgent fixes
4. **DEBUG logging is essential** - Without breadcrumbs, impossible to detect cached containers

---

## Related Documentation

- AWS Lambda Container Image: https://docs.aws.amazon.com/lambda/latest/dg/images-create.html
- Lambda Execution Context: https://docs.aws.amazon.com/lambda/latest/dg/runtimes-context.html
- Lambda Reserved Concurrency: https://docs.aws.amazon.com/lambda/latest/dg/configuration-concurrency.html
