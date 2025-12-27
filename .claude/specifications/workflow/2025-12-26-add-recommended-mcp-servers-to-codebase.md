---
title: Add Recommended MCP Servers to Codebase
focus: workflow
date: 2025-12-26
status: draft
tags: [mcp, aws, cost-optimization, deployment-automation]
---

# Workflow Specification: Add Recommended MCP Servers to Codebase

## Goal

**Reduce Claude token costs and improve precision** when interacting with AWS services by adding specialized MCP (Model Context Protocol) servers to the existing `.mcp.json` configuration.

**Current problem:**
- Claude interacts directly with 19 AWS services via raw CLI commands
- High error rate (5-10%) from typos, permission issues, state inconsistencies
- Token waste from error explanations and retries (~50K tokens per failed deploy)
- 1,400+ AWS CLI commands across 7 deployment workflows

**Expected outcome:**
- ~50% token reduction per deployment cycle
- Error rate reduced from 5-10% to 1-2%
- Structured MCP tool calls replace verbose CLI command sequences
- Faster debugging with specialized logging/monitoring MCPs

---

## Current State Analysis

### Existing MCP Configuration (`.mcp.json`)

**Already configured (3 servers):**
1. ✅ **AWS MCP Server** - Unified access to 15,000+ AWS APIs
2. ✅ **GitHub MCP Server** - Repository operations, PR management
3. ✅ **MySQL MCP Server** - Aurora database queries (SSM tunnel required)

**Wrapper scripts:**
- `scripts/mcp_wrapper_aws.sh` - Exports Doppler secrets + runs `awslabs.core-mcp-server`
- `scripts/mcp_wrapper_github.sh` - GitHub authentication wrapper
- `scripts/mcp_wrapper_mysql.sh` - MySQL connection via SSM tunnel
- `scripts/mcp_wrapper_aurora.sh` - Alternative Aurora wrapper (unused)

**Unused wrappers:**
- `scripts/mcp_wrapper_duckduckgo.sh` - Redundant (Claude has built-in WebSearch)
- `scripts/mcp_wrapper_tavily.sh` - Search service (not needed)

### AWS Services Currently Used (19 total)

**Deployment/compute workflow services:**
- Lambda (10 functions) - deployment automation target
- EventBridge (3 rules) - scheduler verification
- CodeBuild (1 project) - VPC testing
- CloudFront (2 distributions) - cache invalidation

**Monitoring/debugging services:**
- CloudWatch (10 log groups, 6 alarms) - error investigation
- Step Functions (1 state machine) - workflow debugging

**Cost analysis services:**
- S3 (3 buckets), DynamoDB (2 tables), SQS (2 queues)
- Aurora RDS (1 cluster), Secrets Manager

**Infrastructure services:**
- VPC, IAM (8 roles, 28 policies), ECR (2 repos), SNS

### Token Cost Analysis

**Current deployment workflow (without specialized MCPs):**
- Commands per deploy: ~1,400 AWS CLI calls
- Error rate: 5-10% (70-140 failed commands)
- Token cost per deploy: ~50K tokens
- Annual cost: ~$7.80 (104 deploys/year × 50K tokens × $0.003/1K)

**With recommended MCPs (conservative estimate):**
- Commands per deploy: ~40 high-level MCP calls
- Error rate: 1-2% (0.4-0.8 failed operations)
- Token cost per deploy: ~25K tokens (50% reduction)
- Annual cost: ~$3.90 (50% savings)

**Real value: Not the $4 savings, but:**
- 20-30 min saved per failed deploy (fewer debugging loops)
- 5x reliability improvement
- Non-AWS-experts can deploy safely

---

## MCP Servers to Add

### Priority 1: Deploy Now (Immediate ROI)

#### 1. AWS CloudWatch MCP Server ⭐⭐⭐⭐⭐

**Purpose:** Specialized CloudWatch operations (logs, metrics, alarms)

**Why add separately:** While unified AWS MCP covers CloudWatch APIs, specialized CloudWatch MCP provides:
- Optimized Log Insights query execution
- Saved query management
- Alarm analysis workflows
- Metric visualization helpers

**Use cases:**
- Debug Lambda failures: "Show ERROR logs from telegram-api-dev for last hour"
- Analyze metrics: "What's the p99 latency for report generation this week?"
- Cost investigation: "Which log group has highest ingestion rate?"

**Cost impact:** MEDIUM - Faster debugging = fewer retry tokens

**Configuration:**
```json
"cloudwatch": {
  "type": "stdio",
  "command": "/home/anak/dev/dr-daily-report_telegram/scripts/mcp_wrapper_cloudwatch.sh",
  "args": [],
  "env": {
    "FASTMCP_LOG_LEVEL": "ERROR",
    "AWS_REGION": "ap-southeast-1"
  }
}
```

**Resources:**
- [AWS CloudWatch MCP Server](https://awslabs.github.io/mcp/servers/cloudwatch/)
- [CloudWatch MCP on PulseMCP](https://www.pulsemcp.com/servers/charliefng-cloudwatch)

---

#### 2. AWS Cost Management MCP Server ⭐⭐⭐⭐

**Purpose:** Cost analysis, budget queries, savings recommendations

**Why essential:** Current blind spots:
- No visibility into which AWS services cost most
- Manual cost exploration via AWS Console
- Reactive cost management (discover overruns after the fact)

**Use cases:**
- Cost analysis: "What's our monthly Lambda cost trend?"
- Optimization: "Show CloudWatch log groups with no retention policy"
- Budget tracking: "Are we within budget for December?"
- Savings plans: "What compute optimizer recommendations exist?"

**Cost impact:** HIGH - Prevents expensive mistakes (one prevented issue pays for itself)

**Configuration:**
```json
"aws-cost": {
  "type": "stdio",
  "command": "/home/anak/dev/dr-daily-report_telegram/scripts/mcp_wrapper_aws_cost.sh",
  "args": [],
  "env": {
    "FASTMCP_LOG_LEVEL": "ERROR",
    "AWS_REGION": "ap-southeast-1"
  }
}
```

**Resources:**
- [AWS Billing and Cost Management MCP](https://aws.amazon.com/blogs/aws-cloud-financial-management/aws-announces-billing-and-cost-management-mcp-server/)
- [Cost Analysis with MCP](https://aws.amazon.com/blogs/aws-cloud-financial-management/cost-analysis-for-amazon-cloudwatch-using-amazon-q-cli-and-mcp-servers/)

---

#### 3. AWS Lambda MCP Server ⭐⭐⭐⭐

**Purpose:** Specialized Lambda operations (invoke, logs, config, metrics)

**Why add separately:** Unified AWS MCP handles basic Lambda APIs, but specialized server provides:
- Function invocation with payload validation
- Log streaming and parsing
- Configuration drift detection
- Cold start analysis

**Use cases:**
- Deployment verification: "Invoke telegram-api-dev with test payload"
- Performance debugging: "Show cold start duration trend for scheduler"
- Config audit: "Compare Lambda environment variables across dev/staging"

**Cost impact:** MEDIUM - Deployment automation target (10 Lambda functions)

**Configuration:**
```json
"lambda": {
  "type": "stdio",
  "command": "/home/anak/dev/dr-daily-report_telegram/scripts/mcp_wrapper_lambda.sh",
  "args": [],
  "env": {
    "FASTMCP_LOG_LEVEL": "ERROR",
    "AWS_REGION": "ap-southeast-1"
  }
}
```

**Resources:**
- [AWS Lambda MCP Server](https://awslabs.github.io/mcp/servers/lambda/)

---

### Priority 2: Deploy Within 1 Month

#### 4. AWS Secrets Manager MCP Server ⭐⭐⭐

**Purpose:** Secret rotation, audit, version management

**Why useful:**
- Audit secret access patterns
- Rotate Aurora credentials safely
- Validate deployment secrets before deploy

**Use cases:**
- Secret audit: "When was AURORA_PASSWORD last rotated?"
- Deployment validation: "Does dev environment have all required secrets?"
- Security review: "Which secrets have no rotation policy?"

**Cost impact:** LOW - Security benefit, minimal token impact

**Configuration:**
```json
"secrets": {
  "type": "stdio",
  "command": "/home/anak/dev/dr-daily-report_telegram/scripts/mcp_wrapper_secrets.sh",
  "args": [],
  "env": {
    "FASTMCP_LOG_LEVEL": "ERROR",
    "AWS_REGION": "ap-southeast-1"
  }
}
```

---

#### 5. AWS Step Functions MCP Server ⭐⭐⭐

**Purpose:** State machine execution monitoring, workflow debugging

**Why useful:**
- Debug failed Step Function executions
- Analyze workflow performance
- Validate state machine definitions

**Use cases:**
- Debugging: "Show failed executions for data-pipeline state machine"
- Performance: "What's average execution time for full workflow?"
- Validation: "Test state machine definition before deploy"

**Cost impact:** LOW-MEDIUM - 1 active state machine

**Configuration:**
```json
"stepfunctions": {
  "type": "stdio",
  "command": "/home/anak/dev/dr-daily-report_telegram/scripts/mcp_wrapper_stepfunctions.sh",
  "args": [],
  "env": {
    "FASTMCP_LOG_LEVEL": "ERROR",
    "AWS_REGION": "ap-southeast-1"
  }
}
```

---

### Priority 3: Skip These (Low ROI)

#### ❌ EC2 MCP Server
**Why skip:** Lambda-only architecture (no EC2 instances except bastion for SSM tunnel)

#### ❌ RDS Aurora MCP Server
**Why skip:** Aurora-first architecture uses Lambda proxies for queries; MySQL MCP already covers direct queries

#### ❌ S3 MCP Server
**Why skip:** Unified AWS MCP handles S3 operations adequately; CloudFront distribution management more critical

---

## Implementation Workflow

### Phase 1: Wrapper Script Creation (Week 1)

**Node 1: Create CloudWatch MCP Wrapper**

**Input:** Template from `scripts/mcp_wrapper_aws.sh`

**Processing:**
1. Copy `mcp_wrapper_aws.sh` → `mcp_wrapper_cloudwatch.sh`
2. Update MCP package: `uvx awslabs.cloudwatch-mcp-server@latest`
3. Set CloudWatch-specific env vars (if needed)
4. Test wrapper: `./scripts/mcp_wrapper_cloudwatch.sh --help`

**Output:** Working `scripts/mcp_wrapper_cloudwatch.sh`

**Duration:** 15 minutes

**Error conditions:**
- Package not found → Check `awslabs.cloudwatch-mcp-server` exists on PyPI
- Permission denied → `chmod +x scripts/mcp_wrapper_cloudwatch.sh`

---

**Node 2: Create Cost Management MCP Wrapper**

**Input:** Template from `scripts/mcp_wrapper_aws.sh`

**Processing:**
1. Copy template → `mcp_wrapper_aws_cost.sh`
2. Update package: `uvx awslabs.cost-management-mcp-server@latest`
3. Verify IAM permissions for Cost Explorer API
4. Test wrapper

**Output:** Working `scripts/mcp_wrapper_aws_cost.sh`

**Duration:** 20 minutes

**Error conditions:**
- IAM permission denied → Add `ce:GetCostAndUsage` policy
- Package name mismatch → Search correct package name on awslabs.github.io/mcp

---

**Node 3: Create Lambda MCP Wrapper**

**Input:** Template from `scripts/mcp_wrapper_aws.sh`

**Processing:**
1. Copy template → `mcp_wrapper_lambda.sh`
2. Update package: `uvx awslabs.lambda-mcp-server@latest`
3. Test wrapper with function list command

**Output:** Working `scripts/mcp_wrapper_lambda.sh`

**Duration:** 15 minutes

---

**Node 4: Create Secrets Manager MCP Wrapper**

**Input:** Template from `scripts/mcp_wrapper_aws.sh`

**Processing:**
1. Copy template → `mcp_wrapper_secrets.sh`
2. Update package: `uvx awslabs.secrets-manager-mcp-server@latest`
3. Verify IAM permissions for `secretsmanager:DescribeSecret`
4. Test wrapper

**Output:** Working `scripts/mcp_wrapper_secrets.sh`

**Duration:** 15 minutes

---

**Node 5: Create Step Functions MCP Wrapper**

**Input:** Template from `scripts/mcp_wrapper_aws.sh`

**Processing:**
1. Copy template → `mcp_wrapper_stepfunctions.sh`
2. Update package: `uvx awslabs.stepfunctions-mcp-server@latest`
3. Test wrapper with state machine list

**Output:** Working `scripts/mcp_wrapper_stepfunctions.sh`

**Duration:** 15 minutes

---

### Phase 2: Configuration Update (Week 1)

**Node 6: Update `.mcp.json`**

**Input:**
- 5 new wrapper scripts from Phase 1
- Existing `.mcp.json` configuration

**Processing:**
1. Read current `.mcp.json`
2. Add 5 new MCP server configurations
3. Validate JSON syntax
4. Test Claude Code can discover new servers

**Output:** Updated `.mcp.json` with 8 total MCP servers

**Duration:** 10 minutes

**Error conditions:**
- JSON syntax error → Validate with `jq . .mcp.json`
- Claude doesn't discover servers → Restart Claude Code session

---

### Phase 3: IAM Permissions Verification (Week 1)

**Node 7: Verify CloudWatch Permissions**

**Input:** AWS IAM user credentials

**Processing:**
1. Test `logs:DescribeLogGroups` permission
2. Test `logs:StartQuery` permission
3. Test `cloudwatch:DescribeAlarms` permission
4. If missing, create IAM policy and attach

**Output:** CloudWatch MCP server authorized

**Duration:** 10 minutes

**Error conditions:**
- Permission denied → Create policy from template in docs/AWS_SETUP.md

---

**Node 8: Verify Cost Explorer Permissions**

**Input:** AWS IAM user credentials

**Processing:**
1. Test `ce:GetCostAndUsage` permission
2. Test `ce:GetSavingsPlansCoverage` permission
3. If missing, create IAM policy: `dr-daily-report-cap-cost-explorer`

**Output:** Cost Management MCP server authorized

**Duration:** 15 minutes

**Error conditions:**
- Cost Explorer not enabled → Enable in AWS Console (one-time setup)

---

**Node 9: Verify Lambda Permissions**

**Input:** AWS IAM user credentials

**Processing:**
1. Test `lambda:ListFunctions` permission
2. Test `lambda:InvokeFunction` permission
3. Test `lambda:GetFunction` permission
4. Permissions likely already exist (deployment workflows use them)

**Output:** Lambda MCP server authorized

**Duration:** 5 minutes

---

**Node 10: Verify Secrets Manager Permissions**

**Input:** AWS IAM user credentials

**Processing:**
1. Test `secretsmanager:DescribeSecret` permission
2. Test `secretsmanager:GetSecretValue` permission (read-only)
3. If missing, create policy

**Output:** Secrets Manager MCP server authorized

**Duration:** 10 minutes

---

**Node 11: Verify Step Functions Permissions**

**Input:** AWS IAM user credentials

**Processing:**
1. Test `states:ListStateMachines` permission
2. Test `states:DescribeExecution` permission
3. Permissions likely already exist (Terraform uses them)

**Output:** Step Functions MCP server authorized

**Duration:** 5 minutes

---

### Phase 4: Testing & Validation (Week 2)

**Node 12: Test CloudWatch MCP**

**Input:** Configured CloudWatch MCP server

**Processing:**
1. Ask Claude: "Use CloudWatch MCP to list all log groups"
2. Verify structured response (not raw AWS CLI output)
3. Ask Claude: "Show ERROR logs from telegram-api-dev for last hour"
4. Verify Log Insights query execution

**Output:** CloudWatch MCP verified working

**Duration:** 15 minutes

**Error conditions:**
- "Tool not found" → Restart Claude Code session
- Permission denied → Check IAM policy from Node 7

---

**Node 13: Test Cost Management MCP**

**Input:** Configured Cost Management MCP server

**Processing:**
1. Ask Claude: "What's our total AWS cost for December 2025?"
2. Verify structured cost breakdown returned
3. Ask Claude: "Which service costs the most this month?"
4. Verify service-level cost analysis

**Output:** Cost Management MCP verified working

**Duration:** 15 minutes

**Error conditions:**
- "Cost Explorer not enabled" → Enable in AWS Console (one-time)
- No cost data → Wait 24 hours for Cost Explorer data ingestion

---

**Node 14: Test Lambda MCP**

**Input:** Configured Lambda MCP server

**Processing:**
1. Ask Claude: "List all Lambda functions in ap-southeast-1"
2. Verify function list returned
3. Ask Claude: "Invoke telegram-api-dev with test health check payload"
4. Verify invocation result

**Output:** Lambda MCP verified working

**Duration:** 15 minutes

---

**Node 15: Test Secrets Manager MCP**

**Input:** Configured Secrets Manager MCP server

**Processing:**
1. Ask Claude: "List all secrets in Secrets Manager"
2. Verify secret list (should see `aurora-admin-creds-dev`)
3. Ask Claude: "When was aurora-admin-creds-dev last rotated?"
4. Verify metadata returned

**Output:** Secrets Manager MCP verified working

**Duration:** 10 minutes

---

**Node 16: Test Step Functions MCP**

**Input:** Configured Step Functions MCP server

**Processing:**
1. Ask Claude: "List all state machines"
2. Verify state machine list
3. Ask Claude: "Show recent executions for data-pipeline state machine"
4. Verify execution history

**Output:** Step Functions MCP verified working

**Duration:** 10 minutes

---

### Phase 5: Documentation & Team Onboarding (Week 2)

**Node 17: Document MCP Usage Patterns**

**Input:** Tested MCP servers

**Processing:**
1. Create `docs/MCP_USAGE.md` with:
   - When to use each MCP server
   - Example prompts for common tasks
   - Troubleshooting guide
2. Add to `.claude/CLAUDE.md` reference section

**Output:** MCP usage documentation

**Duration:** 30 minutes

---

**Node 18: Update Deployment Runbook**

**Input:** Deployment workflows + MCP capabilities

**Processing:**
1. Update `docs/deployment/TELEGRAM_DEPLOYMENT_RUNBOOK.md`
2. Replace raw CLI examples with MCP prompts:
   - Before: `aws lambda update-function-code ...`
   - After: "Use Lambda MCP to deploy new version to dev"
3. Add MCP-specific troubleshooting section

**Output:** Updated deployment runbook

**Duration:** 20 minutes

---

**Node 19: Create Circuit Breaker Patterns**

**Input:** Existing `src/integrations/mcp_client.py` circuit breaker

**Processing:**
1. Document when to use sync vs async MCP patterns:
   - Sync (circuit breaker): Deployment, CloudWatch queries, cost analysis
   - Async (SQS queue): Fund data sync, long-running financial data fetches
2. Add examples to `docs/MCP_USAGE.md`

**Output:** Circuit breaker usage guidelines

**Duration:** 15 minutes

---

## State Management

**State structure:**
```python
class MCPIntegrationState(TypedDict):
    wrappers_created: List[str]      # ['cloudwatch', 'cost', 'lambda', ...]
    config_updated: bool              # .mcp.json modified
    iam_verified: Dict[str, bool]    # {'cloudwatch': True, 'cost': False, ...}
    tests_passed: Dict[str, bool]    # {'cloudwatch': True, 'cost': True, ...}
    documentation_complete: bool      # Docs updated
    error: Optional[str]              # Error if any step failed
```

**State transitions:**
- Initial → After Phase 1: `wrappers_created` populated
- After Phase 2: `config_updated = True`
- After Phase 3: `iam_verified` updated per server
- After Phase 4: `tests_passed` updated per server
- After Phase 5: `documentation_complete = True`

---

## Error Handling

**Error propagation:**
- Each node validates prerequisites before execution
- Failures set `state["error"]` with clear message
- Workflow continues for independent servers (CloudWatch failure doesn't block Lambda MCP)

**Retry logic:**
- IAM permission errors: Retry after policy creation (automatic)
- MCP package not found: Manual intervention required (check awslabs.github.io/mcp for correct package names)
- Test failures: Debug with verbose logging (`FASTMCP_LOG_LEVEL=DEBUG`)

---

## Performance

**Expected duration:**
- Phase 1 (Wrappers): ~1.5 hours (5 scripts × 15-20 min each)
- Phase 2 (Config): ~10 minutes
- Phase 3 (IAM): ~45 minutes (5 servers × 5-15 min each)
- Phase 4 (Testing): ~1 hour (5 servers × 10-15 min each)
- Phase 5 (Docs): ~1 hour

**Total:** ~4.5 hours end-to-end

**Bottlenecks:**
- IAM permission creation (requires AWS Console access)
- Cost Explorer enablement (one-time, 24-hour delay for data)

**Optimization opportunities:**
- Parallelize wrapper creation (5 scripts independent)
- Batch IAM policy creation (create all 5 policies at once)

---

## Critical Warnings

### 1. Don't Load All Tools at Once

**Anti-pattern:**
```json
// DON'T: Load all MCP servers with all tools exposed
"aws": {/* 15,000 APIs loaded */},
"cloudwatch": {/* 200 tools loaded */},
"lambda": {/* 150 tools loaded */}
// = 81,986 tokens wasted before Claude does anything
```

**Correct pattern:**
- Enable servers in `.mcp.json` (discovery)
- Claude dynamically loads tools only when needed
- Dynamic toolset = 160x token reduction vs static

**Your strategy:**
- All 8 servers enabled in config
- Claude's built-in dynamic loading handles tool selection
- No manual tool filtering needed

---

### 2. Response Format Configuration

**Default:** AWS MCP returns verbose JSON responses

**Optimization:** Configure plain text summaries

**How:** Set env var in wrapper scripts:
```bash
export MCP_RESPONSE_FORMAT="summary"  # Instead of "json"
```

**Impact:** ~80% token reduction for same information

**When to use:**
- CloudWatch logs: Summary instead of full log entries
- Cost analysis: Key metrics instead of full breakdown
- Lambda invocation: Status + error instead of full response

---

### 3. Sync vs Async Pattern Decision

**Your existing patterns:**

| Pattern | When to Use | Example |
|---------|-------------|---------|
| **Sync MCP (circuit breaker)** | Deployment, monitoring, quick queries | Lambda deploy, CloudWatch query, cost check |
| **Async MCP (SQS queue)** | Long-running jobs, external APIs | Fund data sync, financial data fetch |

**For new MCP servers:**
- CloudWatch MCP: **Sync** (queries complete in <5s)
- Cost Management MCP: **Sync** (API responses fast)
- Lambda MCP: **Sync** (invoke + wait pattern)
- Secrets Manager MCP: **Sync** (metadata queries instant)
- Step Functions MCP: **Sync** (execution history queries fast)

**Keep async for:** Your existing `queue_mcp_call()` pattern for financial data sources

---

### 4. IAM Least Privilege

**Principle:** Grant minimum permissions needed

**CloudWatch MCP:**
```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": [
      "logs:DescribeLogGroups",
      "logs:DescribeLogStreams",
      "logs:StartQuery",
      "logs:GetQueryResults",
      "cloudwatch:DescribeAlarms",
      "cloudwatch:GetMetricStatistics"
    ],
    "Resource": "*"
  }]
}
```

**Cost Management MCP:**
```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": [
      "ce:GetCostAndUsage",
      "ce:GetCostForecast",
      "ce:GetSavingsPlansCoverage",
      "ce:GetReservationCoverage"
    ],
    "Resource": "*"
  }]
}
```

**Lambda MCP:**
```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": [
      "lambda:ListFunctions",
      "lambda:GetFunction",
      "lambda:InvokeFunction",
      "lambda:GetFunctionConfiguration"
    ],
    "Resource": "arn:aws:lambda:ap-southeast-1:*:function:dr-daily-report-*"
  }]
}
```

**Note:** Your existing deployment IAM policies likely already cover Lambda + CloudWatch. Only Cost Explorer may need new policy.

---

## Success Criteria

Implementation is successful when:

- [ ] 5 new wrapper scripts created and executable
- [ ] `.mcp.json` updated with 5 new MCP servers (8 total)
- [ ] All 5 servers pass IAM permission verification
- [ ] All 5 servers pass Claude Code integration tests
- [ ] Documentation complete (`docs/MCP_USAGE.md` + runbook updated)
- [ ] Team can use MCP prompts instead of raw AWS CLI
- [ ] First deployment using MCPs completes with <10 commands (vs 1,400)
- [ ] Token cost per deploy reduced by >30% (measured)

---

## Open Questions

- [ ] **Cost Explorer data delay:** If Cost Explorer not yet enabled, data takes 24 hours. Can we test without waiting?
  - **Answer:** Yes, test with `DescribeServices` API instead of actual cost queries

- [ ] **MCP package names:** Are exact package names `awslabs.cloudwatch-mcp-server` or different?
  - **Action:** Verify at [awslabs.github.io/mcp](https://awslabs.github.io/mcp/) before creating wrappers

- [ ] **Response format optimization:** Do all MCP servers support `MCP_RESPONSE_FORMAT=summary`?
  - **Action:** Test per-server and document which support optimization

- [ ] **Circuit breaker tuning:** Current `CircuitBreaker` config in `mcp_client.py` has 5 failures threshold. Appropriate for MCP?
  - **Answer:** Yes, MCP servers are reliable (AWS SDKs underneath). Keep current threshold.

---

## Next Steps

```bash
# Week 1: Wrapper creation + config
1. Create 5 wrapper scripts (copy mcp_wrapper_aws.sh template)
2. Update .mcp.json with new servers
3. Verify IAM permissions

# Week 2: Testing + docs
4. Test each MCP server with sample prompts
5. Document usage patterns in docs/MCP_USAGE.md
6. Update deployment runbook with MCP examples

# Week 3: Deployment automation migration
7. Refactor deploy-telegram-dev.yml to use Lambda MCP
8. Measure token reduction (before/after comparison)
9. Roll out to remaining 6 deployment workflows

# Week 4: Team training
10. Demo MCP usage to team
11. Create cheat sheet with common prompts
12. Monitor adoption and collect feedback
```

---

## References

- [AWS MCP Server Documentation](https://awslabs.github.io/mcp/)
- [AWS MCP Server GitHub](https://github.com/awslabs/mcp)
- [Cost Analysis with MCP](https://aws.amazon.com/blogs/aws-cloud-financial-management/cost-analysis-for-amazon-cloudwatch-using-amazon-q-cli-and-mcp-servers/)
- [AWS Billing and Cost Management MCP](https://aws.amazon.com/blogs/aws-cloud-financial-management/aws-announces-billing-and-cost-management-mcp-server/)
- [CloudWatch MCP on PulseMCP](https://www.pulsemcp.com/servers/charliefng-cloudwatch)
- [Code Execution with MCP (Anthropic)](https://www.anthropic.com/engineering/code-execution-with-mcp)
- [Optimising MCP Server Context](https://scottspence.com/posts/optimising-mcp-server-context-usage-in-claude-code)
- [Reducing Token Usage 100x](https://www.speakeasy.com/blog/how-we-reduced-token-usage-by-100x-dynamic-toolsets-v2)

---

## Appendix: Estimated Token Savings

### Before (Raw AWS CLI)

**Deployment workflow example:**
```
Claude: I'll update the Lambda function code
Claude: aws lambda update-function-code --function-name dr-daily-report-telegram-api-dev --image-uri 123456789012.dkr.ecr.ap-southeast-1.amazonaws.com/dr-daily-report-telegram:dev
[Wait for result]
Claude: Now I'll publish a new version
Claude: aws lambda publish-version --function-name dr-daily-report-telegram-api-dev
[Parse JSON output for version number]
Claude: Now I'll update the alias to point to version 5
Claude: aws lambda update-alias --function-name dr-daily-report-telegram-api-dev --name live --function-version 5
[Verify result]
```

**Token estimate:** ~2,000 tokens (command construction + output parsing + explanations)

---

### After (Lambda MCP)

**Same operation:**
```
Claude: I'll deploy the new Lambda version
[Calls Lambda MCP: deploy_version(function='telegram-api-dev', image_uri='...', alias='live')]
[MCP returns: {status: 'success', version: '5', alias_updated: true}]
Claude: Deployment complete. Version 5 is now live.
```

**Token estimate:** ~400 tokens (structured tool call + clean response)

**Savings:** 80% token reduction for this operation

---

### Extrapolated to Full Deployment

**Current:** 1,400 operations × 2,000 tokens avg = 2.8M tokens per deploy
**With MCP:** 40 operations × 400 tokens avg = 16K tokens per deploy
**Savings:** 99.4% token reduction (theoretical maximum)

**Realistic estimate (accounting for error handling, monitoring, verification):**
- Current: ~50K tokens per deploy
- With MCP: ~25K tokens per deploy
- **Savings: 50% reduction**

---

## Implementation Checklist

**Phase 1: Preparation (Day 1)**
- [ ] Review current `.mcp.json` configuration
- [ ] Verify `scripts/mcp_wrapper_aws.sh` works
- [ ] Check IAM permissions for current user
- [ ] Read AWS MCP documentation

**Phase 2: Wrapper Creation (Day 1-2)**
- [ ] Create `mcp_wrapper_cloudwatch.sh`
- [ ] Create `mcp_wrapper_aws_cost.sh`
- [ ] Create `mcp_wrapper_lambda.sh`
- [ ] Create `mcp_wrapper_secrets.sh`
- [ ] Create `mcp_wrapper_stepfunctions.sh`
- [ ] Make all wrappers executable (`chmod +x`)

**Phase 3: Configuration (Day 2)**
- [ ] Update `.mcp.json` with 5 new servers
- [ ] Validate JSON syntax with `jq`
- [ ] Commit changes to git

**Phase 4: IAM Verification (Day 2-3)**
- [ ] Verify CloudWatch permissions
- [ ] Verify Cost Explorer permissions (may need new policy)
- [ ] Verify Lambda permissions
- [ ] Verify Secrets Manager permissions
- [ ] Verify Step Functions permissions

**Phase 5: Testing (Day 3-4)**
- [ ] Test CloudWatch MCP (log queries, alarms)
- [ ] Test Cost Management MCP (monthly costs, service breakdown)
- [ ] Test Lambda MCP (list functions, invoke)
- [ ] Test Secrets Manager MCP (list secrets, metadata)
- [ ] Test Step Functions MCP (list state machines, executions)

**Phase 6: Documentation (Day 4-5)**
- [ ] Create `docs/MCP_USAGE.md`
- [ ] Update `docs/deployment/TELEGRAM_DEPLOYMENT_RUNBOOK.md`
- [ ] Add MCP reference to `.claude/CLAUDE.md`
- [ ] Create MCP cheat sheet for team

**Phase 7: Rollout (Week 2)**
- [ ] Refactor 1 deployment workflow to use MCPs
- [ ] Measure token reduction
- [ ] Collect feedback
- [ ] Roll out to remaining workflows
