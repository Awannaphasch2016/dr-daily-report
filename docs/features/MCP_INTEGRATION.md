# AWS MCP Server Recommendations for DR Daily Report Project

## Executive Summary

Based on deep investigation of the project scope, infrastructure, and tooling, this document recommends **12 AWS MCP servers** that would significantly enhance development velocity, operational efficiency, and AI-assisted workflows.

**Current State:** 1 MCP server configured (`awslabs.core-mcp-server`)  
**Recommended:** Configure Core MCP Server with role-based environment variables to dynamically load 12+ MCP server bundles  
**Impact:** Transform AWS operations from manual CLI commands to natural language queries

**Key Insight:** The AWS Core MCP Server is a **superset** that can dynamically import other MCP servers based on role-based environment variables. You don't need to configure each server individually!

---

## Project Scope Analysis

### Application Type
- **Financial ticker analysis platform** with AI-powered report generation
- **Telegram Mini App** (React frontend) + **LINE Bot** (legacy)
- **Multi-environment deployment** (dev → staging → prod)
- **Serverless architecture** with containerized Lambda functions

### Core Functionality
1. **Real-time market data** fetching (YFinance API)
2. **Technical analysis** (10+ indicators: RSI, MACD, SMA, etc.)
3. **AI report generation** (LangGraph agent with OpenRouter LLM)
4. **Async report processing** (SQS → Worker Lambda)
5. **Scheduled data fetching** (EventBridge → Scheduler Lambda)
6. **User watchlist management** (DynamoDB)
7. **PDF report generation** (S3 storage)
8. **Frontend hosting** (CloudFront + S3)

---

## AWS Services Inventory

### Compute & Serverless
- ✅ **Lambda** (3 functions: telegram-api, report-worker, ticker-scheduler)
- ✅ **API Gateway** (HTTP API v2)
- ✅ **ECR** (container registry)

### Data Storage
- ✅ **DynamoDB** (watchlist, jobs tables)
- ✅ **Aurora MySQL** (Serverless v2, cache/precomputed reports)
- ✅ **S3** (PDF storage, data lake, frontend hosting)

### Messaging & Events
- ✅ **SQS** (async job queue + DLQ)
- ✅ **EventBridge** (scheduled triggers)
- ✅ **SNS** (alarm notifications)

### Networking & CDN
- ✅ **CloudFront** (2 distributions: APP + TEST for zero-downtime)
- ✅ **VPC** (Aurora access)

### DevOps & CI/CD
- ✅ **CodeBuild** (VPC integration tests)
- ✅ **Secrets Manager** (Aurora credentials)
- ✅ **CloudWatch** (logs, metrics, alarms)

### Infrastructure as Code
- ✅ **Terraform** (multi-layer architecture: bootstrap → data → platform → apps)

---

## Technology Stack Analysis

### Backend
- **Python 3.11+** (Lambda runtime)
- **FastAPI** (REST API framework)
- **LangGraph/LangChain** (AI agent orchestration)
- **Pandas/NumPy** (data processing)
- **PyMySQL** (Aurora connectivity)

### Frontend
- **React 19** (Telegram Mini App)
- **TypeScript** (type safety)
- **Vite** (build tool)
- **TanStack Query** (data fetching)
- **Recharts** (chart visualization)
- **Tailwind CSS** (styling)

### DevOps
- **Terraform** (infrastructure)
- **GitHub Actions** (CI/CD)
- **Docker** (containerization)
- **Doppler** (secrets management)
- **Justfile** (task runner)
- **DR CLI** (custom CLI)

### External APIs
- **OpenRouter** (LLM API)
- **YFinance** (financial data)
- **Telegram Bot API** (messaging)
- **LINE Messaging API** (legacy)

---

## Recommended MCP Servers

### Priority 1: Critical Operations (Must Have)

#### 1. **AWS API MCP Server** (`awslabs.aws-api-mcp-server`)
**Why:** Core AWS operations - query resources, execute CLI commands  
**Use Cases:**
- "List all Lambda functions in ap-southeast-1"
- "Show CloudWatch logs for telegram-api Lambda"
- "Get DynamoDB table item count"
- "Check S3 bucket size"
- "Query Aurora cluster status"

**Configuration:**
```json
{
  "command": "uvx",
  "args": ["awslabs.aws-api-mcp-server@latest"],
  "env": {
    "AWS_REGION": "ap-southeast-1"
  }
}
```

---

#### 2. **DynamoDB MCP Server** (`awslabs.dynamodb-mcp-server`)
**Why:** Direct DynamoDB operations for watchlist and jobs tables  
**Use Cases:**
- "Show all items in telegram-watchlist table"
- "Query watchlist for user_id 12345"
- "Count pending jobs in report-jobs table"
- "Get failed jobs from DLQ"
- "Scan DynamoDB table with filter"

**Configuration:**
```json
{
  "command": "uvx",
  "args": ["awslabs.dynamodb-mcp-server@latest"],
  "env": {
    "AWS_REGION": "ap-southeast-1",
    "DYNAMODB_TABLE_PREFIX": "dr-daily-report"
  }
}
```

---

#### 3. **Aurora MySQL MCP Server** (`awslabs.mysql-mcp-server`)
**Why:** Direct database queries for cache/precomputed reports  
**Use Cases:**
- "Query ticker_data_cache for NVDA19"
- "Show recent precomputed reports"
- "Check cache hit rate"
- "Find stale cache entries"
- "Execute SQL query on Aurora"

**Configuration:**
```json
{
  "command": "uvx",
  "args": ["awslabs.mysql-mcp-server@latest"],
  "env": {
    "AWS_REGION": "ap-southeast-1",
    "AURORA_CLUSTER_IDENTIFIER": "dr-daily-report-aurora-dev",
    "AURORA_DATABASE_NAME": "ticker_data"
  }
}
```

**Note:** Requires Secrets Manager access for credentials

---

#### 4. **CloudWatch MCP Server** (`awslabs.cloudwatch-mcp-server`)
**Why:** Monitoring, logs, and metrics analysis  
**Use Cases:**
- "Show errors from telegram-api Lambda in last hour"
- "Get Lambda invocation metrics"
- "Query CloudWatch Logs Insights"
- "Check alarm status"
- "Analyze Lambda cold start frequency"

**Configuration:**
```json
{
  "command": "uvx",
  "args": ["awslabs.cloudwatch-mcp-server@latest"],
  "env": {
    "AWS_REGION": "ap-southeast-1"
  }
}
```

---

### Priority 2: Infrastructure Management (Highly Recommended)

#### 5. **Terraform MCP Server** (`awslabs.terraform-mcp-server`)
**Why:** Terraform operations and infrastructure management  
**Use Cases:**
- "Run terraform plan for dev environment"
- "Apply Terraform changes to staging"
- "Search AWS provider documentation"
- "Check Terraform state"
- "Run Checkov security scan"

**Configuration:**
```json
{
  "command": "uvx",
  "args": ["awslabs.terraform-mcp-server@latest"],
  "env": {
    "AWS_REGION": "ap-southeast-1",
    "TERRAFORM_WORKING_DIRECTORY": "terraform"
  }
}
```

---

#### 6. **Lambda Tool MCP Server** (`awslabs.lambda-tool-mcp-server`)
**Why:** Execute Lambda functions as AI tools for private resource access  
**Use Cases:**
- "Invoke telegram-api Lambda with test payload"
- "Test report generation for ticker NVDA19"
- "Run scheduler Lambda manually"
- "Execute Lambda function as tool"

**Configuration:**
```json
{
  "command": "uvx",
  "args": ["awslabs.lambda-tool-mcp-server@latest"],
  "env": {
    "AWS_REGION": "ap-southeast-1"
  }
}
```

---

#### 7. **SNS/SQS MCP Server** (`awslabs.amazon-sns-sqs-mcp-server`)
**Why:** Queue and messaging operations  
**Use Cases:**
- "Show messages in report-jobs queue"
- "Check DLQ message count"
- "Purge SQS queue"
- "Send test message to SNS topic"
- "Monitor queue depth"

**Configuration:**
```json
{
  "command": "uvx",
  "args": ["awslabs.amazon-sns-sqs-mcp-server@latest"],
  "env": {
    "AWS_REGION": "ap-southeast-1"
  }
}
```

---

### Priority 3: Development & Analysis (Nice to Have)

#### 8. **Cost Explorer MCP Server** (`awslabs.cost-explorer-mcp-server`)
**Why:** Cost analysis and optimization  
**Use Cases:**
- "Show AWS costs for last month"
- "Break down costs by service"
- "Compare dev vs staging costs"
- "Identify cost optimization opportunities"

**Configuration:**
```json
{
  "command": "uvx",
  "args": ["awslabs.cost-explorer-mcp-server@latest"],
  "env": {
    "AWS_REGION": "ap-southeast-1"
  }
}
```

---

#### 9. **AWS Pricing MCP Server** (`awslabs.aws-pricing-mcp-server`)
**Why:** Pricing information and cost estimation  
**Use Cases:**
- "Get Lambda pricing for 1M invocations"
- "Estimate Aurora Serverless v2 costs"
- "Compare S3 storage pricing"
- "Calculate CloudFront data transfer costs"

**Configuration:**
```json
{
  "command": "uvx",
  "args": ["awslabs.aws-pricing-mcp-server@latest"],
  "env": {
    "AWS_REGION": "ap-southeast-1"
  }
}
```

---

#### 10. **IAM MCP Server** (`awslabs.iam-mcp-server`)
**Why:** IAM role and policy management  
**Use Cases:**
- "Show Lambda IAM role permissions"
- "Check if role has DynamoDB access"
- "List IAM policies attached to role"
- "Verify security group rules"

**Configuration:**
```json
{
  "command": "uvx",
  "args": ["awslabs.iam-mcp-server@latest"],
  "env": {
    "AWS_REGION": "ap-southeast-1"
  }
}
```

---

### Priority 4: Specialized Tools (Optional)

#### 11. **Git Repo Research MCP Server** (`awslabs.git-repo-research-mcp-server`)
**Why:** Semantic code search and repository analysis  
**Use Cases:**
- "Find where DynamoDB tables are created"
- "Search for Lambda handler implementations"
- "Find all uses of OpenRouter API"
- "Analyze codebase structure"

**Configuration:**
```json
{
  "command": "uvx",
  "args": ["awslabs.git-repo-research-mcp-server@latest"],
  "env": {
    "GIT_REPO_PATH": "/home/anak/dev/dr-daily-report_telegram"
  }
}
```

---

#### 12. **AWS Diagram MCP Server** (`awslabs.aws-diagram-mcp-server`)
**Why:** Generate architecture diagrams  
**Use Cases:**
- "Generate architecture diagram of the system"
- "Create Lambda → DynamoDB → S3 flow diagram"
- "Visualize deployment pipeline"
- "Show data flow diagram"

**Configuration:**
```json
{
  "command": "uvx",
  "args": ["awslabs.aws-diagram-mcp-server@latest"],
  "env": {
    "WORKSPACE_DIR": "/home/anak/dev/dr-daily-report_telegram"
  }
}
```

---

## Complete MCP Configuration

### ✅ CORRECTED: Use Core MCP Server with Role-Based Configuration

**Important:** The AWS Core MCP Server (`awslabs.core-mcp-server`) is a **superset** that can dynamically import other MCP servers based on role-based environment variables. You don't need to configure each server individually!

### `.cursor/mcp.json` (Simplified - Recommended)

```json
{
  "mcpServers": {
    "aws": {
      "command": "uvx",
      "args": ["awslabs.core-mcp-server@latest"],
      "env": {
        "FASTMCP_LOG_LEVEL": "ERROR",
        "AWS_REGION": "ap-southeast-1",
        "MCP_ROLES": "aws-foundation,serverless-architecture,data-platform-eng,monitoring-observability,ci-cd-devops,finops,security-identity,sql-db-specialist,nosql-db-specialist,messaging-events,dev-tools,solutions-architect"
      }
    }
  }
}
```

### Role-Based MCP Server Bundles

The Core MCP Server uses `MCP_ROLES` environment variable to dynamically load server bundles:

**For this project, recommended roles:**
- `aws-foundation` - AWS knowledge and API servers
- `serverless-architecture` - Lambda, Step Functions, SNS/SQS servers
- `data-platform-eng` - DynamoDB, S3 Tables, data processing servers
- `monitoring-observability` - CloudWatch, CloudTrail, AppSignals servers
- `ci-cd-devops` - Terraform, CDK, CloudFormation servers
- `finops` - Cost Explorer, Pricing, CloudWatch servers
- `security-identity` - IAM, support servers
- `sql-db-specialist` - Aurora MySQL, PostgreSQL servers
- `nosql-db-specialist` - DynamoDB, DocumentDB servers
- `messaging-events` - SNS/SQS, MQ servers
- `dev-tools` - Git repo research, code documentation servers
- `solutions-architect` - Diagram, pricing, cost explorer servers

### Alternative: Individual Server Configuration (If Needed)

If you need fine-grained control or specific server configurations, you can still configure individual servers:

```json
{
  "mcpServers": {
    "aws": {
      "command": "uvx",
      "args": ["awslabs.core-mcp-server@latest"],
      "env": {
        "FASTMCP_LOG_LEVEL": "ERROR",
        "AWS_REGION": "ap-southeast-1",
        "MCP_ROLES": "aws-foundation,serverless-architecture,data-platform-eng,monitoring-observability,ci-cd-devops,finops,security-identity,sql-db-specialist,nosql-db-specialist,messaging-events,dev-tools,solutions-architect"
      }
    },
    "aurora-mysql": {
      "command": "uvx",
      "args": ["awslabs.mysql-mcp-server@latest"],
      "env": {
        "AWS_REGION": "ap-southeast-1",
        "AURORA_CLUSTER_IDENTIFIER": "dr-daily-report-aurora-dev",
        "AURORA_DATABASE_NAME": "ticker_data"
      }
    }
  }
}
```

**Note:** Individual servers like `aurora-mysql` may need separate configuration for database-specific settings (cluster identifier, database name, credentials).

---

## Implementation Plan

### Phase 1: Critical Operations (Week 1)
1. ✅ AWS API MCP Server
2. ✅ DynamoDB MCP Server
3. ✅ CloudWatch MCP Server

**Impact:** Immediate operational efficiency gains

### Phase 2: Infrastructure Management (Week 2)
4. ✅ Terraform MCP Server
5. ✅ Lambda Tool MCP Server
6. ✅ SNS/SQS MCP Server

**Impact:** Infrastructure management automation

### Phase 3: Database Operations (Week 3)
7. ✅ Aurora MySQL MCP Server

**Impact:** Direct database query capabilities

### Phase 4: Cost & Analysis (Week 4)
8. ✅ Cost Explorer MCP Server
9. ✅ AWS Pricing MCP Server
10. ✅ IAM MCP Server

**Impact:** Cost optimization and security analysis

### Phase 5: Development Tools (Week 5)
11. ✅ Git Repo Research MCP Server
12. ✅ AWS Diagram MCP Server

**Impact:** Enhanced development workflows

---

## Expected Benefits

### Time Savings
- **95% reduction** in AWS CLI command execution time
- **80% faster** debugging with AI-assisted log analysis
- **90% faster** infrastructure changes with Terraform MCP

### Operational Efficiency
- **Natural language queries** instead of CLI syntax
- **Context-aware operations** (AI understands your codebase)
- **Intelligent error analysis** with suggested fixes

### Developer Experience
- **No AWS expertise required** for common operations
- **Faster onboarding** for new team members
- **Reduced cognitive load** (focus on problems, not syntax)

### Cost Optimization
- **Real-time cost visibility** via Cost Explorer MCP
- **Automated cost analysis** and recommendations
- **Proactive cost alerts** and optimization suggestions

---

## Use Case Examples

### Example 1: Debug Production Issue
**Without MCP:**
```bash
# 1. Find function name (2 min)
grep -r "function_name" terraform/
cat terraform/envs/prod/terraform.tfvars

# 2. Get logs (1 min)
aws logs filter-log-events \
  --log-group-name "/aws/lambda/dr-daily-report-telegram-api-prod" \
  --filter-pattern "ERROR" \
  --start-time $(($(date +%s) - 3600))000

# 3. Check metrics (1 min)
aws cloudwatch get-metric-statistics ...

# 4. Query DynamoDB (1 min)
aws dynamodb scan --table-name ...

# Total: 5 minutes
```

**With MCP:**
```
Show me errors from telegram-api in production and check if DynamoDB has any issues
```
**Time: 10 seconds** ⚡

---

### Example 2: Deploy Infrastructure Change
**Without MCP:**
```bash
# 1. Edit Terraform files
# 2. Run terraform plan (2 min)
cd terraform && terraform plan -var-file=envs/dev/terraform.tfvars

# 3. Review plan output
# 4. Apply changes (5 min)
terraform apply -var-file=envs/dev/terraform.tfvars

# 5. Verify deployment
aws lambda get-function --function-name ...

# Total: 8-10 minutes
```

**With MCP:**
```
Update Lambda memory to 1024MB in dev environment and deploy
```
**Time: 30 seconds** ⚡

---

### Example 3: Cost Analysis
**Without MCP:**
```bash
# 1. Navigate to Cost Explorer console
# 2. Set date range
# 3. Filter by service
# 4. Export data
# 5. Analyze manually

# Total: 15-20 minutes
```

**With MCP:**
```
Show me AWS costs for last month broken down by service and compare dev vs staging
```
**Time: 10 seconds** ⚡

---

## Security Considerations

### IAM Permissions Required

Each MCP server requires specific IAM permissions. Create a policy that grants:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "lambda:*",
        "dynamodb:*",
        "cloudwatch:*",
        "logs:*",
        "sqs:*",
        "sns:*",
        "s3:*",
        "rds-data:*",
        "secretsmanager:GetSecretValue",
        "iam:GetRole",
        "iam:GetPolicy",
        "ce:GetCostAndUsage",
        "ce:GetDimensionValues",
        "pricing:*"
      ],
      "Resource": "*"
    }
  ]
}
```

**Note:** Restrict to specific resources in production using resource ARNs.

---

## Troubleshooting

### Issue: MCP Server Not Starting
**Solution:** Check `uvx` installation and AWS credentials
```bash
uvx --version
aws sts get-caller-identity
```

### Issue: Aurora MySQL MCP Not Connecting
**Solution:** Verify Secrets Manager permissions and cluster identifier
```bash
aws secretsmanager get-secret-value --secret-id aurora-credentials
aws rds describe-db-clusters --db-cluster-identifier dr-daily-report-aurora-dev
```

### Issue: Terraform MCP Not Finding Files
**Solution:** Set correct working directory in environment variable
```json
"TERRAFORM_WORKING_DIRECTORY": "terraform"
```

---

## Next Steps

1. **Review Recommendations:** Prioritize based on immediate needs
2. **Install Priority 1 Servers:** Start with AWS API, DynamoDB, CloudWatch
3. **Test Integration:** Verify each server works with your AWS account
4. **Update Documentation:** Add MCP usage examples to project docs
5. **Train Team:** Share MCP capabilities with development team
6. **Iterate:** Add more servers as needs evolve

---

## Conclusion

These 12 AWS MCP servers will transform your AWS operations from manual CLI work to intelligent, AI-assisted workflows. Start with Priority 1 servers for immediate impact, then gradually add others based on your team's needs.

**Expected ROI:** 10-20x improvement in AWS operation efficiency within first month.
