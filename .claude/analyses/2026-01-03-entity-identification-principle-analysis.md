# Analysis: Do We Need an "Entity Identification" Principle?

**Date**: 2026-01-03
**Question**: Should we add a principle about "identifying entities" separate from Principle #20 (Execution Boundary Discipline)?
**Type**: Conceptual/Philosophical/Metacognitive analysis

---

## Question Reframed

**User's insight**:
> "Other than contract, boundary, cross-boundary execution, we still need to 'identify entities' involved in each boundary. This gives us idea in term of the 'physical what' that is involve rather than just the 'conceptual what'."

**Core distinction**:
- **Conceptual what**: "Code writes to Aurora" (abstract boundary)
- **Physical what**: "Lambda function `dr-daily-report-report-worker-dev` writes to Aurora cluster `dr-daily-report-aurora-dev.cluster-c9a0288e4hqm` in VPC `vpc-12345`" (concrete entities)

**Question**: Is entity identification a separate concern that needs its own principle, or is it already covered by Principle #20?

---

## Current State: Principle #20

### What Principle #20 Currently Says

**From CLAUDE.md Principle #20**:
> Before concluding "code is correct", systematically identify execution boundaries (code → runtime, code → database, service → service) and verify contracts at each boundary match reality.
>
> **Verification questions**:
> - WHERE does this code run? (Lambda, EC2, local?)
> - WHAT environment does it require? (env vars, network, permissions?)
> - WHAT external systems does it call? (Aurora schema, S3 bucket, API format?)
> - HOW do I verify the contract? (Terraform config, SHOW COLUMNS, test access?)

### What's Missing (Entity Identification)

**Current**: "Lambda writes to Aurora" (conceptual)

**Missing**:
- WHICH Lambda? (function name, ARN, version)
- WHICH Aurora? (cluster name, endpoint, database name)
- WHICH VPC? (subnet IDs, security groups)
- WHICH IAM role? (execution role name, policies attached)

**Gap**: Principle #20 identifies boundary TYPES (code → database) but not boundary INSTANCES (this specific Lambda → that specific Aurora cluster).

---

## Analysis Framework

### 1. Philosophical Level: Abstraction vs Concreteness

**Conceptual boundary** (abstraction):
- "Service A calls Service B"
- "Code writes to database"
- "Lambda accesses S3"

**Entity-level boundary** (concreteness):
- "Lambda `dr-daily-report-report-worker-dev` (ARN: `arn:aws:lambda:ap-southeast-1:123456789012:function:dr-daily-report-report-worker-dev`) calls Aurora cluster `dr-daily-report-aurora-dev` (endpoint: `dr-daily-report-aurora-dev.cluster-c9a0288e4hqm.ap-southeast-1.rds.amazonaws.com`)"

**Why both matter**:
- **Abstraction**: Guides thinking (what KIND of boundary)
- **Concreteness**: Enables verification (which SPECIFIC entities)

**Analogy**:
```
Boundary principle (conceptual): "Check that code can connect to database"
Entity principle (physical): "Verify Lambda X in subnet Y can reach Aurora Z in security group W"
```

**Philosophical insight**: You can't verify a contract without knowing WHO the contracting parties are.

---

### 2. Conceptual Level: Types vs Instances

**Type-level thinking** (Principle #20 currently):
```
Boundary: Lambda → Aurora
Contract: Can Lambda connect to Aurora?
Verification: Check VPC, security group, IAM role
```

**Instance-level thinking** (missing):
```
Entities:
  - Lambda: dr-daily-report-report-worker-dev (arn:aws:lambda:...)
  - Aurora: dr-daily-report-aurora-dev (endpoint: xxx.rds.amazonaws.com)
  - VPC: vpc-12345
  - Subnet: subnet-67890
  - Security Group (Lambda): sg-lambda-123
  - Security Group (Aurora): sg-aurora-456
  - IAM Role: dr-daily-report-worker-role-dev

Contract verification:
  - Lambda in subnet-67890?
  - Aurora in same VPC (vpc-12345)?
  - sg-lambda-123 has egress to sg-aurora-456:3306?
  - IAM role has rds-db:connect permission for arn:aws:rds-db:...?
```

**Distinction**:
- **Type**: Category of thing (Lambda, Aurora, VPC)
- **Instance**: Specific thing (THIS Lambda, THAT Aurora, THIS VPC)

**Why instance matters**:
- Two Lambdas exist (worker, controller) → which one has Aurora access?
- Three security groups exist → which ones need to allow traffic?
- Multiple IAM roles → which role needs permissions?

---

### 3. Metacognitive Level: Mental Model Completeness

**Mental model with only boundaries** (incomplete):
```
┌─────────┐           ┌─────────┐
│ Lambda  │ ────────▶ │ Aurora  │
└─────────┘           └─────────┘
     ↓
Question: "Can Lambda access Aurora?"
Answer: "Need to check VPC, security group, IAM"
Problem: Which Lambda? Which Aurora? Which security groups?
```

**Mental model with entities** (complete):
```
┌────────────────────────────────────┐
│ Lambda: report-worker-dev          │
│ ARN: arn:aws:lambda:...:report...  │
│ VPC: vpc-12345                     │
│ Subnet: subnet-67890               │
│ SG: sg-lambda-123                  │
│ Role: worker-role-dev              │
└────────────────────────────────────┘
            │
            │ (needs egress rule)
            ▼
┌────────────────────────────────────┐
│ Aurora: aurora-dev                 │
│ Endpoint: xxx.rds.amazonaws.com    │
│ VPC: vpc-12345 (same VPC ✓)       │
│ Subnet: subnet-11111               │
│ SG: sg-aurora-456                  │
│ Port: 3306                         │
└────────────────────────────────────┘

Verification checklist:
✓ Same VPC? (vpc-12345 = vpc-12345)
✓ Security group rule? (sg-lambda-123 → sg-aurora-456:3306)
✓ IAM permission? (worker-role-dev has rds-db:connect)
```

**Metacognitive insight**: Entity identification transforms abstract question ("Can Lambda access Aurora?") into concrete verification checklist.

---

## Evidence: Where Entity Identification Prevented Bugs

### Instance 1: PDF Schema Bug (Could Have Been Prevented)

**What I did** (boundary verification only):
```markdown
Boundary: Lambda writes to Aurora
Contract: INSERT columns match schema
Verification: SHOW COLUMNS FROM precomputed_reports
Result: ❌ Missing pdf_s3_key column
```

**What I missed** (entity identification):
```markdown
Entities involved:
  - Lambda: dr-daily-report-report-worker-dev
  - Code file: src/report_worker_handler.py:276-294
  - Aurora table: ticker_data.precomputed_reports
  - INSERT query: src/data/aurora/precompute_service.py:958-977

Entity-level verification:
  1. Which function writes to Aurora? → store_report_from_api()
  2. Which table does it write to? → precomputed_reports
  3. Which columns does INSERT include? → [list them]
  4. Which columns does table have? → SHOW COLUMNS
  5. Mismatch between (3) and (4)? → YES (pdf_s3_key missing)
```

**Why entity identification would help**:
- Knowing the SPECIFIC function (`store_report_from_api`) allows me to inspect EXACT INSERT query
- Knowing the SPECIFIC table (`precomputed_reports`) allows me to verify EXACT schema
- Instead of asking "Does Lambda write to Aurora correctly?" (vague), ask "Does `store_report_from_api()` INSERT match `precomputed_reports` schema?" (precise)

---

### Instance 2: Timezone Configuration (Entity Identification Done Right)

**What I did correctly**:
```markdown
Question: Is PDF timestamp Bangkok time or UTC?

Entity identification:
  - Code: src/formatters/pdf_generator.py:759
  - Code uses: datetime.now() (context-dependent)
  - Runtime: Lambda container
  - Lambda function: dr-daily-report-report-worker-dev
  - Environment variable: TZ (set in Lambda config)
  - Terraform config: terraform/lambda_worker.tf (environment block)

Verification:
  1. Which code generates timestamp? → pdf_generator.py:759
  2. How does datetime.now() determine timezone? → Respects TZ env var
  3. Which Lambda has TZ env var? → report-worker-dev
  4. What value is TZ set to? → Asia/Bangkok (verified via Terraform + AWS CLI)
  5. Conclusion: Timestamp IS Bangkok time ✓
```

**Why this worked**: I identified ALL entities in the chain (code → runtime → Lambda → env var → Terraform), not just the boundary types.

---

### Instance 3: Progress Report Architecture (Entity Mapping)

**What I did correctly**:
```markdown
Workflow architecture:

Entity 1: EventBridge Scheduler
  - Name: precompute-scheduler-dev
  - Schedule: cron(0 22 * * ? *) (5 AM Bangkok = 22:00 UTC previous day)
  - Target: Lambda controller

Entity 2: Precompute Controller Lambda
  - Function: dr-daily-report-precompute-controller-dev
  - Triggers: Step Functions execution
  - Payload: {"ticker_list": {"tickers": ["DBS19", ...]}}

Entity 3: Step Functions State Machine
  - Name: precompute-workflow-dev
  - Definition: terraform/step_functions/precompute_workflow.json
  - Map State: FanOutToWorkers (MaxConcurrency: 46)

Entity 4: SQS Queue
  - Name: dr-daily-report-worker-queue-dev
  - Receives: 46 messages (one per ticker)

Entity 5: Worker Lambda (46 parallel invocations)
  - Function: dr-daily-report-report-worker-dev
  - Trigger: SQS message
  - Processing: LLM report → PDF generation → Aurora caching

Entity 6: Aurora MySQL
  - Cluster: dr-daily-report-aurora-dev
  - Database: ticker_data
  - Table: precomputed_reports
```

**Why entity mapping worked**: By identifying SPECIFIC entities (not just "scheduler → Lambda → database"), I could trace the EXACT execution flow.

---

## Gap Analysis: What Entity Identification Adds

### Current Principle #20 (Boundary-Focused)

**Strengths**:
- ✅ Identifies boundary types (code → runtime, service → service)
- ✅ Provides verification questions (WHERE, WHAT, HOW)
- ✅ Guides thinking about contracts

**Weaknesses**:
- ❌ Doesn't explicitly require naming entities
- ❌ Doesn't distinguish between "a Lambda" vs "this specific Lambda"
- ❌ Doesn't provide entity discovery method

**Example of gap**:
```
Principle #20 asks: "WHERE does this code run?"
Answer: "Lambda"

But which Lambda?
  - dr-daily-report-report-worker-dev?
  - dr-daily-report-precompute-controller-dev?
  - dr-daily-report-api-handler-dev?

All three are "Lambda", but they have different:
  - VPC configurations
  - IAM roles
  - Environment variables
  - Timeout settings
```

---

### Proposed Entity Identification Extension

**What it adds**:
1. **Entity discovery**: How to find WHICH entities are involved
2. **Entity properties**: What properties matter for verification
3. **Entity relationships**: How entities connect (ARN references, name matching)

**Example extension to Principle #20**:

```markdown
### 20. Execution Boundary Discipline

[Current content remains...]

**Entity identification** (physical what):
Before verifying boundary contracts, identify WHICH specific entities are involved:

- Code entity: Which file, function, line number?
- Runtime entity: Which Lambda function (name, ARN, version)?
- Infrastructure entity: Which VPC, subnet, security group?
- Storage entity: Which Aurora cluster, database, table?
- Permission entity: Which IAM role, policy, resource policy?

**Entity discovery methods**:
- Code → Runtime: Check deployment config (Terraform, CloudFormation)
- Runtime → Infrastructure: Query AWS APIs (aws lambda get-function-configuration)
- Infrastructure → Storage: Inspect VPC, security groups, network routes
- Permissions: Trace IAM role → policies → resource policies

**Entity verification pattern**:
1. List all entities in boundary (Source Entity → Target Entity)
2. For each entity, note ARN/ID/name
3. Verify entity properties match requirements (VPC ID, security group rules)
4. Verify entity relationships (same VPC, security group allows traffic)
```

---

## Alternative: Extend Checklist Instead of Principle

**Option A**: Add to Principle #20 (make principle longer)

**Option B**: Keep Principle #20 focused on boundaries, extend checklist to include entity identification

**Comparison**:

| Aspect | Option A: Principle | Option B: Checklist |
|--------|---------------------|---------------------|
| **Abstraction level** | ⚠️ Adds implementation detail to principle | ✅ Keeps principle abstract |
| **Principle length** | ❌ Grows from 24 → 35+ lines | ✅ Stays ~24 lines |
| **Goldilocks Zone** | ⚠️ Risks becoming too detailed | ✅ Maintains right level |
| **Actionability** | ✅ Everything in one place | ⚠️ Must reference checklist |
| **Stability** | ⚠️ Entity discovery methods may evolve | ✅ Principle stable, checklist evolves |

**Recommendation**: **Option B** - Extend checklist, not principle

**Rationale**:
- CLAUDE.md should guide THINKING ("identify entities before verifying contracts")
- Checklist should guide DOING ("how to discover entity names/ARNs")
- Entity discovery methods evolve (new AWS services, new tools)
- Principle should be stable, checklist can be updated

---

## Proposed Solution: Two-Layer Approach

### Layer 1: CLAUDE.md Principle #20 (Add One Sentence)

**Current**:
```markdown
### 20. Execution Boundary Discipline

Before concluding "code is correct", systematically identify execution boundaries
(code → runtime, code → database, service → service) and verify contracts at each
boundary match reality.
```

**Proposed addition** (emphasize entity identification):
```markdown
### 20. Execution Boundary Discipline

Before concluding "code is correct", systematically identify execution boundaries
(code → runtime, code → database, service → service), **identify the specific entities
at each boundary** (this Lambda, that Aurora, this security group), and verify contracts
match reality.

**Verification questions**:
- WHERE does this code run? → **WHICH Lambda function?** (name, ARN, version)
- WHAT environment does it require? → **WHICH env vars in WHICH config?** (Terraform, Doppler)
- WHAT external systems does it call? → **WHICH Aurora cluster, S3 bucket, SQS queue?** (endpoints, ARNs)
- HOW do I verify the contract? → **WHICH AWS resources to inspect?** (security groups, IAM policies)
```

**Impact**: Minimal change (adds emphasis on "which specific entities"), stays in Goldilocks Zone

---

### Layer 2: Execution Boundary Checklist (Add Entity Identification Section)

**Location**: `.claude/checklists/execution-boundaries.md`

**New section** (add after existing phases):

```markdown
## Entity Identification Guide

Before verifying boundaries, identify ALL entities involved in each boundary crossing.

### Code Entity Identification

**What to identify**:
- File path (exact location of code)
- Function/class name
- Line numbers (where boundary crossing happens)

**How to discover**:
```bash
# Find WHERE code makes Aurora call
rg "aurora|pymysql|cursor.execute" src/ --type py -n

# Find WHICH function calls external API
rg "requests.get|httpx" src/ --type py -A 5
```

**Example**:
```
Code entity: src/data/aurora/precompute_service.py:958-977
Function: _store_completed_report()
Line: cursor.execute("INSERT INTO precomputed_reports...")
```

---

### Runtime Entity Identification

**What to identify**:
- Lambda function name
- ARN (Amazon Resource Name)
- Version/alias
- Runtime environment (Python 3.12, Node.js 20)

**How to discover**:
```bash
# List Lambda functions
aws lambda list-functions --query 'Functions[*].[FunctionName,FunctionArn,Runtime]'

# Get specific function details
aws lambda get-function --function-name dr-daily-report-report-worker-dev

# Get function ARN
aws lambda get-function-configuration \
  --function-name dr-daily-report-report-worker-dev \
  --query 'FunctionArn' --output text
```

**Example**:
```
Runtime entity: dr-daily-report-report-worker-dev
ARN: arn:aws:lambda:ap-southeast-1:123456789012:function:dr-daily-report-report-worker-dev
Version: $LATEST
Runtime: Python 3.12
```

---

### Infrastructure Entity Identification

**What to identify**:
- VPC ID
- Subnet IDs
- Security group IDs
- Network ACL IDs
- Route table IDs

**How to discover**:
```bash
# Get Lambda VPC configuration
aws lambda get-function-configuration \
  --function-name dr-daily-report-report-worker-dev \
  --query 'VpcConfig'

# Get Aurora VPC configuration
aws rds describe-db-clusters \
  --db-cluster-identifier dr-daily-report-aurora-dev \
  --query 'DBClusters[0].{VpcId:DbClusterParameterGroup,Subnets:DBSubnetGroup}'

# Get security group details
aws ec2 describe-security-groups --group-ids sg-12345678
```

**Example**:
```
Infrastructure entities:
  Lambda VPC: vpc-12345
  Lambda Subnets: [subnet-67890, subnet-abcde]
  Lambda Security Group: sg-lambda-123
  Aurora VPC: vpc-12345 (same VPC ✓)
  Aurora Subnets: [subnet-11111, subnet-22222]
  Aurora Security Group: sg-aurora-456
```

---

### Storage Entity Identification

**What to identify**:
- Aurora: cluster name, endpoint, database name, table name
- S3: bucket name, region, ARN
- DynamoDB: table name, region, ARN
- SQS: queue name, URL, ARN

**How to discover**:
```bash
# Aurora cluster details
aws rds describe-db-clusters \
  --db-cluster-identifier dr-daily-report-aurora-dev \
  --query 'DBClusters[0].{Endpoint:Endpoint,Database:DatabaseName}'

# S3 bucket details
aws s3api get-bucket-location --bucket dr-daily-report-dev-storage

# DynamoDB table details
aws dynamodb describe-table --table-name dr-daily-report-telegram-jobs-dev

# SQS queue details
aws sqs get-queue-attributes --queue-url https://sqs...
```

**Example**:
```
Storage entities:
  Aurora Cluster: dr-daily-report-aurora-dev
  Aurora Endpoint: dr-daily-report-aurora-dev.cluster-c9a0288e4hqm.ap-southeast-1.rds.amazonaws.com
  Database: ticker_data
  Table: precomputed_reports
```

---

### Permission Entity Identification

**What to identify**:
- IAM role name (Lambda execution role)
- IAM policies attached to role
- Resource policies (S3 bucket policy, SQS queue policy)
- Trust relationships

**How to discover**:
```bash
# Get Lambda execution role
aws lambda get-function-configuration \
  --function-name dr-daily-report-report-worker-dev \
  --query 'Role' --output text

# Get policies attached to role
aws iam list-attached-role-policies \
  --role-name dr-daily-report-worker-role-dev

# Get inline policies
aws iam list-role-policies \
  --role-name dr-daily-report-worker-role-dev

# Get policy document
aws iam get-policy-version \
  --policy-arn arn:aws:iam::...:policy/... \
  --version-id v1 \
  --query 'PolicyVersion.Document'
```

**Example**:
```
Permission entities:
  IAM Role: dr-daily-report-worker-role-dev
  ARN: arn:aws:iam::123456789012:role/dr-daily-report-worker-role-dev
  Attached Policies:
    - AWSLambdaVPCAccessExecutionRole (AWS managed)
    - dr-daily-report-worker-policy-dev (customer managed)
  Permissions:
    - rds-db:connect (Aurora access)
    - s3:PutObject (S3 upload)
    - sqs:ReceiveMessage (SQS trigger)
```

---

### Entity Relationship Verification

After identifying all entities, verify relationships:

**VPC relationships**:
```bash
# Verify Lambda and Aurora in same VPC
LAMBDA_VPC=$(aws lambda get-function-configuration \
  --function-name dr-daily-report-report-worker-dev \
  --query 'VpcConfig.VpcId' --output text)

AURORA_VPC=$(aws rds describe-db-clusters \
  --db-cluster-identifier dr-daily-report-aurora-dev \
  --query 'DBClusters[0].VpcId' --output text)

if [ "$LAMBDA_VPC" = "$AURORA_VPC" ]; then
  echo "✅ Same VPC: $LAMBDA_VPC"
else
  echo "❌ Different VPCs: Lambda=$LAMBDA_VPC, Aurora=$AURORA_VPC"
fi
```

**Security group relationships**:
```bash
# Verify Lambda security group allows egress to Aurora security group
aws ec2 describe-security-groups \
  --group-ids sg-lambda-123 \
  --query 'SecurityGroups[0].IpPermissionsEgress[?UserIdGroupPairs[?GroupId==`sg-aurora-456`]]'
```

**IAM permission relationships**:
```bash
# Verify Lambda role can connect to Aurora
aws iam simulate-principal-policy \
  --policy-source-arn arn:aws:iam::123456789012:role/dr-daily-report-worker-role-dev \
  --action-names rds-db:connect \
  --resource-arns arn:aws:rds-db:ap-southeast-1:123456789012:dbuser:dr-daily-report-aurora-dev/admin
```

---

## Checklist: Entity Identification Workflow

- [ ] **Code entity**: Which file/function/line crosses boundary?
- [ ] **Runtime entity**: Which Lambda/EC2/container executes code?
- [ ] **Infrastructure entity**: Which VPC/subnet/security group?
- [ ] **Storage entity**: Which database/bucket/queue?
- [ ] **Permission entity**: Which IAM role/policy/resource policy?
- [ ] **Relationship verification**: Do entities connect correctly?

---

## Example: Complete Entity Identification

**Scenario**: Verify Lambda can write to Aurora

### Step 1: Identify Code Entity
```
File: src/data/aurora/precompute_service.py
Function: _store_completed_report()
Line: 958-977
Operation: cursor.execute("INSERT INTO precomputed_reports...")
```

### Step 2: Identify Runtime Entity
```
Lambda Function: dr-daily-report-report-worker-dev
ARN: arn:aws:lambda:ap-southeast-1:123456789012:function:dr-daily-report-report-worker-dev
Runtime: Python 3.12
Handler: src.report_worker_handler.lambda_handler
```

### Step 3: Identify Infrastructure Entities
```
Lambda Infrastructure:
  VPC: vpc-12345
  Subnets: [subnet-67890, subnet-abcde]
  Security Group: sg-lambda-123

Aurora Infrastructure:
  VPC: vpc-12345 ✓ (same VPC)
  Subnets: [subnet-11111, subnet-22222]
  Security Group: sg-aurora-456
  Port: 3306
```

### Step 4: Identify Storage Entity
```
Aurora Cluster: dr-daily-report-aurora-dev
Endpoint: dr-daily-report-aurora-dev.cluster-c9a0288e4hqm.ap-southeast-1.rds.amazonaws.com
Database: ticker_data
Table: precomputed_reports
Schema: [see SHOW COLUMNS output]
```

### Step 5: Identify Permission Entities
```
IAM Role: dr-daily-report-worker-role-dev
Attached Policies:
  - AWSLambdaVPCAccessExecutionRole (network access)
  - dr-daily-report-worker-policy-dev (Aurora access)

Permissions needed:
  - ec2:CreateNetworkInterface (VPC Lambda)
  - ec2:DescribeNetworkInterfaces (VPC Lambda)
  - rds-db:connect (Aurora connection)
```

### Step 6: Verify Relationships
```
✓ Lambda VPC = Aurora VPC (both vpc-12345)
✓ Security group sg-lambda-123 → sg-aurora-456:3306 (egress rule exists)
✓ IAM role has rds-db:connect permission
✓ Aurora endpoint reachable from Lambda subnets
```

---

## Conclusion

**Entity identification is ALREADY IMPLICIT in Principle #20**, but making it EXPLICIT improves clarity.

**Recommendation**: Two-layer approach
1. **CLAUDE.md**: Add one sentence emphasizing "identify specific entities" (minimal change)
2. **Checklist**: Add comprehensive "Entity Identification Guide" section (detailed implementation)

This maintains Goldilocks Zone abstraction level while providing concrete guidance.
```

**Impact**:
- Principle stays concise (~26 lines with addition)
- Checklist grows with detailed entity discovery methods
- Separation of concerns: Principle guides thinking, checklist guides doing

---

## Recommendation

**DO NOT add separate principle** - Entity identification is not orthogonal to boundary verification, it's a PREREQUISITE for boundary verification.

**Instead**:
1. Add one clarifying sentence to Principle #20 (emphasize "which specific entities")
2. Extend execution boundary checklist with "Entity Identification Guide" section
3. Maintain two-layer separation: Principle (WHY + WHAT) vs Checklist (HOW)

**Rationale**:
- Entity identification is HOW you verify boundaries (implementation detail)
- Principle should focus on WHAT to verify (boundaries, contracts)
- Checklist is appropriate place for entity discovery methods

---

## Next Steps

- [ ] Review proposed Principle #20 addition (one sentence)
- [ ] Add "Entity Identification Guide" to `.claude/checklists/execution-boundaries.md`
- [ ] Test entity identification workflow on next validation task
- [ ] Refine based on real usage

---

**Analysis complete**: Entity identification is critical but belongs in checklist, not separate principle.
