# Aurora Connection Bottleneck Research

**Date**: 2026-01-15
**Type**: Architecture Analysis
**Goal**: Research best practices for solving Aurora connection pool exhaustion in parallel Lambda workloads

---

## Executive Summary

**Current Problem**: Pattern precompute Step Functions workflow must run at `MaxConcurrency=1` because parallel Lambda invocations exhaust Aurora Serverless v2 connection pool.

**Root Cause**: Aurora Serverless v2 at 0.5-2.0 ACU provides ~22-90 connections. With 46 report workers + pattern workers competing, connections are exhausted.

**Recommendation**: **RDS Proxy** is the AWS-recommended solution for Lambda + Aurora connection management. It provides 5-10x connection multiplexing with minimal code changes. However, for your specific workload profile (once-daily batch job), the current sequential approach is pragmatic and cost-effective.

---

## Current Architecture Analysis

### Configuration (from `terraform/aurora.tf`)

```
Aurora Serverless v2:
├── min_capacity: 0.5 ACU (~1 GB RAM, ~22 connections)
├── max_capacity: 2.0 ACU (~4 GB RAM, ~90 connections)
├── engine: aurora-mysql 8.0
└── cost: ~$43/month baseline
```

### Connection Math

| ACU Level | Approx Memory | Approx max_connections |
|-----------|---------------|------------------------|
| 0.5 ACU | 1 GB | ~22 |
| 1.0 ACU | 2 GB | ~45 |
| 2.0 ACU | 4 GB | ~90 |

**Demand**: 46 report workers + 46 pattern workers = 92 potential concurrent connections

**Problem**: Even at max 2.0 ACU, connection count (92) ≥ available connections (90).

### Current Mitigation

Step Functions workflow runs pattern workers sequentially (`MaxConcurrency=1`):

```json
"FanOutToPatternWorkers": {
  "Type": "Map",
  "MaxConcurrency": 1,  // Sequential to avoid connection exhaustion
  ...
}
```

---

## Solution Options

### Option 1: RDS Proxy (AWS Recommended)

**What It Does**: Acts as a connection multiplexer between Lambda and Aurora. Maintains a warm pool of connections and reuses them across Lambda invocations.

**How It Works**:
```
Before RDS Proxy:
┌─────────┐   ┌─────────┐   ┌─────────┐
│Lambda 1 │   │Lambda 2 │   │Lambda 46│
└────┬────┘   └────┬────┘   └────┬────┘
     │             │             │
     │ 46 connections            │
     ▼             ▼             ▼
┌─────────────────────────────────────┐
│         Aurora (90 max)             │
└─────────────────────────────────────┘

After RDS Proxy:
┌─────────┐   ┌─────────┐   ┌─────────┐
│Lambda 1 │   │Lambda 2 │   │Lambda 46│
└────┬────┘   └────┬────┘   └────┬────┘
     │             │             │
     │ 46 proxy connections      │
     ▼             ▼             ▼
┌─────────────────────────────────────┐
│           RDS Proxy                 │
│     (multiplexes to ~10 real)       │
└────────────────┬────────────────────┘
                 │ ~10 connections
                 ▼
┌─────────────────────────────────────┐
│         Aurora (90 max)             │
└─────────────────────────────────────┘
```

**Benefits**:
- 5-10x connection multiplexing
- Automatic failover handling
- IAM authentication support
- Secrets Manager integration
- No Lambda code changes required

**Costs**:
- ~$0.015 per vCPU-hour (~$10.80/month per proxy endpoint)
- Additional ~$5-15/month for your workload
- Total: ~$15-25/month additional

**Terraform Addition**:
```hcl
resource "aws_db_proxy" "aurora" {
  name                   = "${var.project_name}-proxy-${var.environment}"
  engine_family          = "MYSQL"
  role_arn               = aws_iam_role.rds_proxy.arn
  vpc_security_group_ids = [aws_security_group.lambda_aurora.id]
  vpc_subnet_ids         = local.private_subnets_with_nat

  auth {
    auth_scheme               = "SECRETS"
    iam_auth                  = "DISABLED"
    secret_arn                = aws_secretsmanager_secret.aurora_credentials.arn
  }
}

resource "aws_db_proxy_default_target_group" "aurora" {
  db_proxy_name = aws_db_proxy.aurora.name

  connection_pool_config {
    max_connections_percent      = 100
    max_idle_connections_percent = 50
    connection_borrow_timeout    = 120
  }
}

resource "aws_db_proxy_target" "aurora" {
  db_proxy_name         = aws_db_proxy.aurora.name
  target_group_name     = aws_db_proxy_default_target_group.aurora.name
  db_cluster_identifier = aws_rds_cluster.aurora.id
}
```

**Limitations**:
- Adds latency (~1-5ms per query)
- Pinning issues with certain SQL operations
- Double-pooling risk if Lambda also uses connection pooling library

---

### Option 2: Increase Aurora ACU

**What It Does**: Scale up Aurora to support more connections.

**Cost Impact**:

| Configuration | Monthly Cost | max_connections |
|---------------|--------------|-----------------|
| 0.5-2.0 ACU (current) | ~$43-172 | 22-90 |
| 1.0-4.0 ACU | ~$86-344 | 45-180 |
| 2.0-8.0 ACU | ~$172-688 | 90-360 |

**Terraform Change**:
```hcl
variable "aurora_min_acu" {
  default = 1.0  # Was 0.5
}

variable "aurora_max_acu" {
  default = 4.0  # Was 2.0
}
```

**Analysis**:
- ✅ Simple change
- ✅ More headroom for future growth
- ❌ Doesn't solve the fundamental problem
- ❌ Cost doubles or quadruples
- ❌ At 46+46=92 workers, still need 4.0 ACU minimum

---

### Option 3: Add Wait State in Step Functions

**What It Does**: Add explicit delay between report workers and pattern workers to allow connection release.

**Terraform Change** (in `precompute_workflow.json`):
```json
"FanOutToWorkers": {
  "Type": "Map",
  "MaxConcurrency": 46,
  ...
  "Next": "WaitForConnectionRelease"
},

"WaitForConnectionRelease": {
  "Type": "Wait",
  "Seconds": 30,
  "Comment": "Allow Lambda containers to release DB connections before pattern workers",
  "Next": "FanOutToPatternWorkers"
},

"FanOutToPatternWorkers": {
  "Type": "Map",
  "MaxConcurrency": 10,  // Can increase from 1
  ...
}
```

**Analysis**:
- ✅ Zero cost
- ✅ No infrastructure changes
- ✅ Easy to implement
- ❌ Adds 30 seconds to workflow
- ❌ Relies on Lambda container lifecycle (not guaranteed)

---

### Option 4: Explicit Connection Close in Lambda

**What It Does**: Ensure Lambda explicitly closes connections after each invocation.

**Code Change** (in `src/data/aurora/client.py`):
```python
class AuroraClient:
    def close(self):
        """Explicitly close connection and reset singleton."""
        if self._connection:
            self._connection.close()
            self._connection = None
        AuroraClient._instance = None
```

**Handler Change**:
```python
def handler(event, context):
    try:
        result = process_ticker(event)
        return result
    finally:
        AuroraClient.get_instance().close()  # Always close
```

**Analysis**:
- ✅ Zero cost
- ✅ More deterministic than Wait state
- ⚠️ Loses connection reuse benefits within same Lambda container
- ⚠️ Small performance hit per invocation

---

### Option 5: Alternative Architecture (ECS/Fargate)

**What It Does**: Replace Lambda with long-running container that manages its own connection pool.

**Architecture**:
```
Current (Lambda):
┌─────────────────────────────────────────┐
│ Step Functions                          │
│   └── Map State (46 parallel)           │
│         └── Lambda (1 connection each)  │
│               └── Aurora                │
└─────────────────────────────────────────┘

Alternative (Fargate):
┌─────────────────────────────────────────┐
│ EventBridge (5 AM daily)                │
│   └── ECS Fargate Task                  │
│         └── Python Process              │
│               └── Connection Pool (10)  │
│                     └── Aurora          │
└─────────────────────────────────────────┘
```

**Terraform Addition**:
```hcl
resource "aws_ecs_cluster" "precompute" {
  name = "${var.project_name}-precompute-${var.environment}"
}

resource "aws_ecs_task_definition" "precompute" {
  family                   = "${var.project_name}-precompute"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = 512
  memory                   = 1024

  container_definitions = jsonencode([{
    name  = "precompute"
    image = "${aws_ecr_repository.lambda.repository_url}:${var.lambda_image_tag}"
    command = ["python", "-m", "dr_cli", "precompute", "--all"]
    ...
  }])
}
```

**Cost Estimate**:
- 0.25 vCPU, 0.5 GB RAM Fargate task
- Running ~10 minutes daily
- ~$0.50/month (vs Lambda ~$0/month for same workload)

**Analysis**:
- ✅ Single connection pool (10 connections for all tickers)
- ✅ More control over execution
- ✅ Better for long-running batch jobs
- ❌ More infrastructure to manage
- ❌ Loses event-driven benefits
- ❌ Different deployment model
- ❌ Over-engineering for current workload

---

## Trade-off Matrix

| Criterion | RDS Proxy | Increase ACU | Wait State | Explicit Close | ECS Fargate |
|-----------|-----------|--------------|------------|----------------|-------------|
| **Cost Impact** | +$15-25/mo | +$43-172/mo | $0 | $0 | +$0.50/mo |
| **Implementation Effort** | Medium | Low | Low | Low | High |
| **Parallelism Improvement** | 10-20x | 2-4x | 5-10x | 5-10x | N/A |
| **Maintenance Overhead** | Low | Low | Low | Low | High |
| **Code Changes** | None | None | Terraform only | Small | Large |
| **Architectural Fit** | ✅ | ✅ | ✅ | ✅ | ❌ |

---

## Recommendation

### For Your Specific Workload

**Current**: Daily batch job at 5 AM, processes 46 tickers, runs once/day.

**Recommended Approach**: **Keep MaxConcurrency=1 for now** + **Add Wait State** + **Increase MaxConcurrency to 5-10**.

**Rationale**:
1. **Workload doesn't justify RDS Proxy cost**: $15-25/month for a once-daily batch job that completes in <5 minutes either way
2. **Sequential is acceptable**: 46 tickers × ~3 seconds each = ~2.5 minutes total. Acceptable for background job.
3. **Wait State is free insurance**: Ensures report workers release connections before patterns start
4. **Moderate parallelism is achievable**: With explicit close + wait, MaxConcurrency=5-10 should work

### Implementation Plan

**Phase 1 (Immediate)**:
```json
// Add Wait state, increase MaxConcurrency to 5
"WaitForConnectionRelease": {
  "Type": "Wait",
  "Seconds": 15,
  "Next": "FanOutToPatternWorkers"
},

"FanOutToPatternWorkers": {
  "MaxConcurrency": 5,
  ...
}
```

**Phase 2 (If needed)**:
- Add explicit connection close in Lambda handlers
- Monitor CloudWatch metrics for connection errors
- Increase MaxConcurrency gradually (5 → 10 → 15)

**Phase 3 (If growth demands)**:
- Add RDS Proxy when:
  - Multiple concurrent batch jobs need to run
  - Interactive API endpoints need low-latency connections
  - Connection errors become frequent

### When to Reconsider Architecture

Consider ECS Fargate or RDS Proxy when:
- **Batch frequency increases**: Multiple times per day
- **Real-time requirements**: User-facing pattern detection
- **Cost becomes concern**: RDS Proxy amortizes better at scale
- **Connection errors persist**: Despite optimizations

---

## References

**AWS Documentation**:
- [Amazon RDS Proxy for Aurora](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/rds-proxy.html)
- [Aurora Serverless v2 Performance and Scaling](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/aurora-serverless-v2.setting-capacity.html)
- [Using Amazon RDS Proxy with AWS Lambda](https://aws.amazon.com/blogs/compute/using-amazon-rds-proxy-with-aws-lambda/)
- [AWS Lambda vs Fargate Decision Guide](https://docs.aws.amazon.com/decision-guides/latest/fargate-or-lambda/fargate-or-lambda.html)

**Key AWS Blog Posts**:
- [Connection management and pooling - Aurora MySQL Handbook](https://docs.aws.amazon.com/en_us/whitepapers/latest/amazon-aurora-mysql-db-admin-handbook/connection-management-and-pooling.html)
- [Step Functions Distributed Map for Large-Scale Processing](https://aws.amazon.com/blogs/aws/step-functions-distributed-map-a-serverless-solution-for-large-scale-parallel-data-processing/)
- [Accelerating workloads using parallelism in AWS Step Functions](https://aws.amazon.com/blogs/compute/accelerating-workloads-using-parallelism-in-aws-step-functions/)

---

## Appendix: Connection Formula

For Aurora MySQL, `max_connections` is approximately:

```
max_connections ≈ GREATEST({DBInstanceClassMemory/9531392}, 5)
```

For Serverless v2:
- 0.5 ACU = 1 GB = ~22 connections
- 1.0 ACU = 2 GB = ~45 connections
- 2.0 ACU = 4 GB = ~90 connections

Note: Actual connections available may be lower due to system processes.
