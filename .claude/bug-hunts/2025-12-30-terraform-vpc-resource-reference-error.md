---
title: Terraform VPC Resource Reference Error Blocking EventBridge Scheduler Deployment
bug_type: production-error
date: 2025-12-30
status: root_cause_found
confidence: High
---

# Bug Hunt Report: Terraform Plan Fails with Undeclared Resource References

## Symptom

**Description**: Terraform plan/apply fails with errors:
```
Error: Reference to undeclared resource
  on precompute_workflow.tf line 234: aws_subnet.private[*].id
  on precompute_workflow.tf line 235: aws_security_group.lambda.id
```

**First occurrence**: Discovered when attempting to deploy Phase 2 of EventBridge Scheduler migration

**Affected scope**: ALL Terraform operations (plan, apply, destroy) - complete blocker

**Impact**: **HIGH** - Prevents any infrastructure changes via Terraform

---

## Investigation Summary

**Bug type**: production-error (configuration error)

**Investigation duration**: 15 minutes

**Status**: Root cause found

---

## Evidence Gathered

### Error Output

```
Error: Reference to undeclared resource
  on precompute_workflow.tf line 234, in resource "aws_lambda_function" "get_ticker_list":
 234:     subnet_ids         = aws_subnet.private[*].id

A managed resource "aws_subnet" "private" has not been declared in the root module.

Error: Reference to undeclared resource
  on precompute_workflow.tf line 235, in resource "aws_lambda_function" "get_ticker_list":
 235:     security_group_ids = [aws_security_group.lambda.id]

A managed resource "aws_security_group" "lambda" has not been declared in the root module.
```

### Code References

**File**: `terraform/precompute_workflow.tf` (lines 233-236)

```hcl
vpc_config {
  subnet_ids         = aws_subnet.private[*].id              # ❌ Resource doesn't exist
  security_group_ids = [aws_security_group.lambda.id]        # ❌ Resource doesn't exist
}
```

**What DOES exist** (`aurora.tf` lines 121-130):
```hcl
data "aws_vpc" "default" {
  default = true
}

data "aws_subnets" "default" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
}

# Aurora uses: data.aws_subnets.default.ids (line 167)
# Security group that exists: aws_security_group.lambda_aurora (line 96)
```

### Git History

```bash
$ git log --oneline -- terraform/precompute_workflow.tf
72c43f7 feat(scheduler): Implement Step Functions orchestrated precompute workflow
f55b3f1 refactor(scheduler): Move to 5 AM Bangkok, disable auto-precompute
a262228 feat(scheduler): Add automated precompute triggering via EventBridge
```

**Commit 72c43f7** added the VPC config with incorrect resource references:
```diff
+  vpc_config {
+    subnet_ids         = aws_subnet.private[*].id
+    security_group_ids = [aws_security_group.lambda.id]
+  }
```

---

## Hypotheses Tested

### Hypothesis 1: Resources Were Never Created

**Likelihood**: High

**Test performed**:
1. Search all .tf files for `resource "aws_subnet" "private"`
2. Search for `resource "aws_security_group" "lambda"`

**Result**: ✅ **CONFIRMED**

**Reasoning**:
- No `resource "aws_subnet" "private"` exists in any .tf file
- Only `data "aws_subnets" "default"` exists (data source, not managed resource)
- Only `resource "aws_security_group" "lambda_aurora"` exists (different name)

**Evidence**:
- `grep -l "aws_subnet" *.tf` returns: aurora.tf, precompute_workflow.tf
- aurora.tf uses `data "aws_subnets" "default"` (data source)
- precompute_workflow.tf references `aws_subnet.private` (doesn't exist)

---

### Hypothesis 2: Code Was Never Deployed

**Likelihood**: High

**Test performed**: Check if this Lambda (`get_ticker_list`) exists in AWS

**Result**: **UNCERTAIN** (not tested yet, but likely doesn't exist)

**Reasoning**: If Terraform can't plan/apply due to syntax errors, the resource was never created

**Evidence**:
- Commit 72c43f7 added this code
- Terraform syntax error would prevent deployment
- User has been using `just aurora-query` commands (direct AWS access), not Terraform

---

### Hypothesis 3: This is Dead Code

**Likelihood**: Medium-High

**Test performed**: Check what `get_ticker_list` Lambda does

**Result**: **CONFIRMED** - Lambda is for Step Functions workflow that may not be actively used

**Reasoning**:
Looking at precompute_workflow.tf context:
- This is part of Step Functions orchestrated precompute workflow (commit 72c43f7)
- Recent commits show scheduler refactoring to simpler architecture
- The scheduler.tf we're modifying uses direct Lambda invocation (not Step Functions)

**Evidence**:
- Commit message: "Implement Step Functions orchestrated precompute workflow"
- Current scheduler uses `aws_lambda_function.ticker_scheduler` (not Step Functions)
- User's workflow doesn't mention Step Functions

---

## Root Cause

**Identified cause**: Copy-paste error in commit 72c43f7 - referenced resources that don't exist

**Confidence**: High

**Supporting evidence**:
1. Commit 72c43f7 added VPC config with incorrect resource names
2. Correct pattern exists in aurora.tf: `data.aws_subnets.default.ids`
3. Correct security group exists: `aws_security_group.lambda_aurora`
4. These errors would have prevented ANY Terraform operation since that commit
5. User workflow doesn't rely on Terraform (uses AWS CLI directly)

**Code location**: `terraform/precompute_workflow.tf:234-235`

**Why this causes the symptom**:
Terraform validates ALL resource references during plan phase, even if those resources aren't being modified. The EventBridge Scheduler deployment (unrelated to VPC config) triggers full plan validation, which fails on these undeclared references.

---

## Impact Assessment

### Is This Blocker Critical for EventBridge Scheduler Migration?

**NO** - This is INDEPENDENT of EventBridge Scheduler changes.

**Why safe to ignore for scheduler deployment:**

1. **EventBridge Scheduler doesn't use VPC** - schedulers invoke Lambda directly (no VPC needed)
2. **Affected Lambda is unrelated** - `get_ticker_list` is for Step Functions workflow
3. **Current scheduler works** - `ticker_scheduler` Lambda already deployed and working
4. **Two deployment paths exist**:
   - Path A: Fix Terraform, deploy via Terraform ✅ Complete infrastructure management
   - Path B: Deploy scheduler via AWS CLI, ignore Terraform ❌ Bypasses IaC

### What DOES Break?

**ALL Terraform operations** until fixed:
- ❌ `terraform plan`
- ❌ `terraform apply`
- ❌ `terraform destroy`
- ❌ ANY infrastructure changes via Terraform

### What DOESN'T Break?

**Direct AWS CLI operations** work fine:
- ✅ Create EventBridge Scheduler via `aws scheduler create-schedule`
- ✅ Create IAM roles via `aws iam create-role`
- ✅ Manual resource management
- ✅ Current scheduler continues working (already deployed)

---

## Reproduction Steps

1. Navigate to terraform directory: `cd terraform`
2. Run any Terraform command: `ENV=dev doppler run -- terraform plan`
3. **Expected behavior**: Plan succeeds, shows infrastructure changes
4. **Actual behavior**: Fails with "Reference to undeclared resource" errors

---

## Fix Candidates

### Fix 1: Correct Resource References (Quick Fix - 5 minutes)

**Approach**: Update precompute_workflow.tf to use correct data sources

```hcl
# CHANGE precompute_workflow.tf lines 234-235:
vpc_config {
  subnet_ids         = data.aws_subnets.default.ids           # ✅ Use data source
  security_group_ids = [aws_security_group.lambda_aurora.id]  # ✅ Use existing SG
}
```

**Pros**:
- Minimal change (2 lines)
- Uses existing, proven pattern from aurora.tf
- Fixes Terraform validation immediately
- Enables all Terraform operations

**Cons**:
- Assumes `get_ticker_list` Lambda needs same VPC as Aurora (probably correct)
- Doesn't validate if Lambda is actually needed

**Estimated effort**: 5 minutes

**Risk**: Low

---

### Fix 2: Comment Out Unused Lambda (Quick Fix - 2 minutes)

**Approach**: Comment out the entire `get_ticker_list` Lambda resource

```hcl
# COMMENT OUT precompute_workflow.tf lines 200-244:
# resource "aws_lambda_function" "get_ticker_list" {
#   # ... entire block ...
# }
```

**Pros**:
- Fastest fix (2 minutes)
- Removes problematic code completely
- If Lambda isn't deployed, this matches reality
- Enables Terraform operations immediately

**Cons**:
- Loses infrastructure code (may be needed later)
- Breaks Step Functions workflow if it's actually used
- Requires investigation to determine if Lambda is needed

**Estimated effort**: 2 minutes

**Risk**: Medium (if Lambda is actually used in production)

---

### Fix 3: Create Missing VPC Resources (Complete Fix - 30 minutes)

**Approach**: Create actual `aws_subnet.private` and `aws_security_group.lambda` resources

**Pros**:
- Matches original intent
- Proper infrastructure separation (private subnets)
- Most "correct" solution architecturally

**Cons**:
- Requires VPC design decisions (CIDR blocks, routing)
- 30+ minutes effort
- May not be necessary (can use default VPC)
- Overkill for current need

**Estimated effort**: 30-60 minutes

**Risk**: Medium (VPC changes can affect existing resources)

---

### Fix 4: Deploy EventBridge Scheduler via AWS CLI (Bypass - 10 minutes)

**Approach**: Skip Terraform entirely, use AWS CLI to create scheduler resources

```bash
# Create IAM role
aws iam create-role --role-name dr-daily-report-eventbridge-scheduler-role-dev ...

# Create EventBridge Scheduler
aws scheduler create-schedule --name dr-daily-report-daily-ticker-fetch-v2-dev ...
```

**Pros**:
- Bypasses Terraform blocker completely
- Can deploy scheduler NOW (perfect timing for tomorrow's 5 AM run)
- Validates scheduler functionality independent of Terraform

**Cons**:
- ❌ **Infrastructure drift** - resources not in Terraform state
- ❌ Manual cleanup later (can't `terraform destroy`)
- ❌ Doesn't fix root cause (Terraform still broken)
- ❌ Not sustainable (defeats purpose of IaC)

**Estimated effort**: 10 minutes

**Risk**: Medium (creates infrastructure debt)

---

## Recommendation

**Recommended fix**: **Fix 1 - Correct Resource References** ✅

**Rationale**:
1. **Fastest proper fix** (5 minutes vs 30 minutes for Fix 3)
2. **Unblocks Terraform immediately** (enables Phase 2 deployment)
3. **Uses proven pattern** (same approach as aurora.tf)
4. **Low risk** (2-line change, well-understood)
5. **Maintains IaC discipline** (vs Fix 4 which bypasses Terraform)

**Implementation priority**: P0 (blocks infrastructure deployment)

---

## Decision Framework for User

### Choose Fix 1 (Correct References) IF:
- ✅ You want to deploy via Terraform (recommended)
- ✅ You have 5 minutes to fix properly
- ✅ You want to maintain infrastructure-as-code discipline
- ✅ Tomorrow's 5 AM run is OK to miss (can test later)

### Choose Fix 4 (AWS CLI Bypass) IF:
- ⚠️ You MUST test scheduler at tomorrow's 5 AM run (time-sensitive)
- ⚠️ You're willing to accept infrastructure drift
- ⚠️ You'll fix Terraform properly later
- ⚠️ You understand this creates cleanup debt

### Choose Fix 2 (Comment Out) IF:
- ⚠️ You're certain `get_ticker_list` Lambda isn't used
- ⚠️ You want fastest unblock (2 minutes)
- ⚠️ Step Functions workflow is deprecated

---

## Next Steps

### If choosing Fix 1 (Recommended):

- [x] ~~Review investigation findings~~ (complete)
- [ ] Implement resource reference fix (5 minutes)
- [ ] Run `terraform plan` to verify fix
- [ ] Deploy Phase 2: `terraform apply -var="new_scheduler_enabled=true"`
- [ ] Verify EventBridge Scheduler created
- [ ] Test manually: invoke Lambda with scheduler payload
- [ ] Monitor tomorrow's 5 AM Bangkok run

### If choosing Fix 4 (Time-Sensitive):

- [ ] Deploy EventBridge Scheduler via AWS CLI (10 minutes)
- [ ] Test immediately with manual Lambda invocation
- [ ] Monitor tomorrow's 5 AM Bangkok run
- [ ] Fix Terraform properly later (Fix 1)
- [ ] Import AWS CLI resources into Terraform state

---

## Investigation Trail

**What was checked**:
- Terraform error output (identified missing resources)
- All .tf files for subnet/security group resources (grep search)
- aurora.tf for existing VPC patterns (found data sources)
- Git history for precompute_workflow.tf (found commit 72c43f7)
- Resource naming patterns (identified lambda_aurora vs lambda)

**What was ruled out**:
- ❌ Resources exist but wrong scope (they simply don't exist)
- ❌ Terraform state corruption (validation happens pre-state)
- ❌ Module issue (resources in root module, not modules/)
- ❌ EventBridge Scheduler causing the error (pre-existing issue)

**Tools used**:
- grep (search Terraform files)
- git log (find when error introduced)
- git show (examine specific commits)
- Terraform validation output

**Time spent**:
- Evidence gathering: 8 min
- Hypothesis testing: 5 min
- Solution design: 2 min
- Total: 15 min
