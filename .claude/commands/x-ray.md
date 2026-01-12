---
name: x-ray
description: Deep structural inspection - reveal components, boundaries, dependencies, patterns, and trade-offs in existing systems
accepts_args: true
arg_schema:
  - name: scope
    required: true
    description: "System or component to inspect (e.g., 'report generation pipeline', 'telegram bot architecture')"
composition:
  - skill: research
---

# X-Ray Command

**Purpose**: Reveal the internal structure of existing systems - components, boundaries, dependencies, patterns, and trade-offs.

**Core Philosophy**: "See inside before changing" - X-ray reveals what exists, it doesn't propose what should exist. For creating new designs, use `/design`.

**Naming rationale**: Like a medical X-ray, this command reveals internal structure without modifying it. Inspection, not creation.

**When to use**:
- Before major refactoring (understand current architecture)
- Onboarding to codebase (understand system structure)
- Debugging distributed systems (map component interactions)
- Planning scalability improvements (identify bottlenecks)
- Analyzing legacy code (reveal hidden dependencies)

**When NOT to use**:
- Creating new designs → use `/design`
- Comparing alternatives → use `/what-if`
- Quick lookups → use Grep/Read directly
- Single-component changes → use `/explore`

---

## X-Ray vs Related Commands

| Command | Purpose | Action |
|---------|---------|--------|
| `/x-ray` | Reveal existing structure | Inspect |
| `/design` | Create new solutions | Create |
| `/analysis` | Think about implications | Analyze |
| `/what-if` | Explore alternatives | Compare |

**Workflow:**
```bash
/x-ray "current auth system"     # SEE what exists
/what-if "OAuth instead of JWT"  # THINK about alternatives
/design "new OAuth2 flow"        # CREATE new solution
```

---

## Quick Reference

```bash
# Understand report generation architecture
/x-ray "report generation pipeline"
→ Components: Scheduler, Lambda, Aurora, S3, Cache
→ Boundaries: Service (Lambda→Aurora), Data (Python→MySQL), Network (VPC)
→ Dependencies: Scheduler→Lambda→Aurora→S3
→ Pattern: Event-driven + ETL
→ Trade-offs: Consistency vs Availability, Cost vs Performance

# Inspect data flow
/x-ray "user request to report delivery"
→ Trace: API Gateway → Lambda → Aurora → Response
→ Boundaries: API Gateway→Lambda (HTTP), Lambda→Aurora (MySQL protocol)
→ Bottlenecks: Aurora query latency, Lambda cold start

# Analyze deployment infrastructure
/x-ray "CI/CD pipeline"
→ Components: GitHub Actions, ECR, Lambda, CloudWatch
→ Pattern: Build-Push-Deploy-Verify
→ Boundaries: GitHub→AWS (OIDC), ECR→Lambda (container image)
```

---

## Execution Flow

### Phase 1: Component Identification

**Identify all system components**:

1. **Compute components**: Lambda functions, EC2 instances, containers
2. **Storage components**: Aurora, S3, DynamoDB, ElastiCache
3. **Integration components**: API Gateway, SQS, SNS, Step Functions, EventBridge
4. **Network components**: VPC, Load Balancers, CloudFront
5. **Supporting components**: IAM roles, CloudWatch, Secrets Manager

**For each component**:
- **Purpose**: What does it do?
- **Technology**: What is it built with? (Python, Node.js, MySQL, etc.)
- **Configuration**: Key settings (timeout, memory, concurrency, etc.)
- **Location**: Where in codebase? (file paths, Terraform resources)

**Output**: Component inventory with purpose and location

---

### Phase 2: Boundary Analysis

**Identify system boundaries** (where components interact):

**1. Service Boundaries** (component-to-component):
```
API Gateway → Lambda (HTTP/REST boundary)
Lambda → Aurora (MySQL protocol boundary)
Lambda → S3 (AWS SDK boundary)
Lambda → SQS (Message queue boundary)
Step Functions → Lambda (JSON event boundary)
```

**2. Data Boundaries** (type system transitions):
```
Python dict → JSON (serialization boundary)
JSON → MySQL VARCHAR/JSON (type boundary)
NumPy float64 → MySQL DECIMAL (precision boundary)
Python datetime → MySQL DATETIME (timezone boundary)
```

**3. Phase Boundaries** (lifecycle transitions):
```
Build → Runtime (artifact deployment boundary)
Development → Production (environment boundary)
Code → Container (Docker image boundary)
Container → Lambda (cold start boundary)
```

**4. Network Boundaries** (network transitions):
```
Public internet → API Gateway (ingress boundary)
VPC → RDS (internal network boundary)
Lambda → External API (egress boundary)
Region → Region (cross-region boundary)
```

**5. Permission Boundaries** (security transitions):
```
Unauthenticated → Authenticated (API Gateway authorizer)
Lambda Execution Role → Aurora (IAM to database)
User → Admin (authorization boundary)
```

**For each boundary**:
- **Contract**: What format/protocol is expected?
- **Validation**: How is contract enforced?
- **Failure mode**: What happens if contract violated?

**Output**: Boundary map with contracts and failure modes

---

### Phase 3: Dependency Mapping

**Map component dependencies** (who calls whom, what data flows where):

**1. Control Flow** (execution order):
```
Scheduler → Lambda (trigger)
Lambda → Aurora (query)
Lambda → S3 (store result)
Lambda → Cache (update)

Sequential: A → B → C (blocking)
Parallel: A → [B, C, D] (concurrent)
Conditional: A → B (if X) or C (if Y)
```

**2. Data Flow** (data movement):
```
User Input → API Gateway → Lambda → Aurora → Response

Transformations:
- JSON request → Python dict (API Gateway)
- Python dict → SQL parameters (Lambda)
- MySQL result → Python dict (Lambda)
- Python dict → JSON response (API Gateway)
```

**3. Dependency Graph**:
```
          ┌─────────────┐
          │  Scheduler  │
          └──────┬──────┘
                 │ (triggers)
          ┌──────▼──────┐
          │   Lambda    │
          └──┬────┬────┬┘
             │    │    │
    (query)  │    │    │ (store)
             │    │    │
    ┌────────▼┐  │  ┌─▼────────┐
    │  Aurora │  │  │    S3    │
    └─────────┘  │  └──────────┘
                 │ (update)
          ┌──────▼──────┐
          │   Cache     │
          └─────────────┘
```

**4. Critical Path Analysis**:
- **Longest path**: Determines end-to-end latency
- **Bottlenecks**: Components on critical path
- **Parallelization opportunities**: Independent branches

**Output**: Dependency graph with control flow, data flow, and critical path

---

### Phase 4: Pattern Recognition

**Identify architectural patterns in use**:

**1. Overall Architecture Pattern**:
- **Monolith**: Single deployable unit
- **Microservices**: Independent services
- **Serverless**: Event-driven functions
- **Event-Driven**: Publish-subscribe messaging
- **Layered**: Presentation → Business → Data
- **Hexagonal**: Ports and adapters
- **CQRS**: Command-Query Responsibility Segregation

**2. Integration Patterns**:
- **Synchronous**: Request-Response (API Gateway → Lambda → Aurora)
- **Asynchronous**: Fire-and-Forget (SQS → Lambda)
- **Event Streaming**: Pub-Sub (EventBridge → Multiple Lambdas)
- **Batch Processing**: Scheduled jobs (EventBridge Scheduler → Lambda)

**3. Data Patterns**:
- **ETL**: Extract-Transform-Load (yfinance → Lambda → Aurora)
- **Cache-Aside**: Check cache, then database
- **Write-Through**: Write to cache and database
- **Event Sourcing**: Store events, not state
- **CQRS**: Separate read and write models

**4. Design Patterns** (code-level):
- **Repository**: Data access abstraction
- **Factory**: Object creation
- **Singleton**: Single instance (Aurora connection pool)
- **Decorator**: Behavior wrapping (retry logic)
- **Strategy**: Interchangeable algorithms

**5. Anti-Patterns** (bad practices):
- **God Object**: Component doing too much
- **Spaghetti Code**: Tangled dependencies
- **Golden Hammer**: Using same solution everywhere
- **Premature Optimization**: Optimizing before measuring
- **Not Invented Here**: Rejecting external solutions

**Output**: Pattern classification with examples from codebase

---

### Phase 5: Trade-off Analysis

**Evaluate architectural trade-offs**:

**1. Performance vs Scalability**:
```
Performance: Single request latency (P50, P99)
Scalability: Requests per second (throughput)

Example:
- In-memory cache: High performance, Low scalability (single instance)
- Distributed cache: Medium performance, High scalability (horizontal)

Current choice: [Which chosen, why]
```

**2. Consistency vs Availability** (CAP theorem):
```
Consistency: All nodes see same data
Availability: All requests get response
Partition Tolerance: System works despite network splits

Example:
- Aurora read replica: Eventual consistency, High availability
- Aurora writer: Strong consistency, Lower availability

Current choice: [Which chosen, why]
```

**3. Simplicity vs Flexibility**:
```
Simplicity: Easy to understand, maintain
Flexibility: Easy to extend, customize

Example:
- Monolithic Lambda: Simple deployment, Inflexible scaling
- Microservices: Complex deployment, Flexible scaling

Current choice: [Which chosen, why]
```

**4. Cost vs Capability**:
```
Cost: Infrastructure spend
Capability: Features available

Example:
- Lambda 128MB: Low cost, Low capability (timeouts)
- Lambda 1024MB: Higher cost, Higher capability (faster)

Current choice: [Which chosen, why]
```

**5. Security vs Convenience**:
```
Security: Protection against threats
Convenience: Ease of use

Example:
- VPC Lambda: High security (isolated), Low convenience (NAT gateway needed)
- Public Lambda: Low security (internet), High convenience (direct access)

Current choice: [Which chosen, why]
```

**For each trade-off**:
- **Current position**: Where on spectrum?
- **Rationale**: Why this choice?
- **Alternatives**: Other options considered?
- **Constraints**: What limits choice? (budget, time, compliance)

**Output**: Trade-off matrix with current choices and rationale

---

### Phase 6: Architecture Assessment

**Evaluate architecture quality**:

**1. Strengths** (what works well):
- Clear separation of concerns?
- Well-defined boundaries?
- Appropriate pattern choices?
- Good performance characteristics?
- Cost-effective?

**2. Weaknesses** (what needs improvement):
- Tight coupling?
- Missing boundaries?
- Pattern mismatches?
- Performance bottlenecks?
- Cost inefficiencies?

**3. Scalability Assessment**:
```
Vertical scalability (scale up):
- Can components handle more load with more resources?
- Limits: Lambda max memory, Aurora max instance size

Horizontal scalability (scale out):
- Can components handle more load with more instances?
- Limits: Lambda concurrency, Aurora read replicas

Bottlenecks:
- Which components limit scalability?
- How to address?
```

**4. Reliability Assessment**:
```
Single points of failure:
- Aurora writer (mitigate: Multi-AZ, read replicas)
- Single Lambda (mitigate: Concurrency, retries)

Fault tolerance:
- Retry logic present?
- Circuit breakers?
- Graceful degradation?

Recovery:
- RTO (Recovery Time Objective): How long to recover?
- RPO (Recovery Point Objective): How much data loss acceptable?
```

**5. Maintainability Assessment**:
```
Code organization:
- Clear module structure?
- Consistent naming?
- Appropriate abstraction levels?

Documentation:
- Architecture diagrams present?
- Component responsibilities clear?
- Integration contracts documented?

Testing:
- Unit tests cover logic?
- Integration tests cover boundaries?
- End-to-end tests cover workflows?
```

**Output**: Assessment report with strengths, weaknesses, and observations

---

### Phase 7: Generate X-Ray Report

**Output format**:

```markdown
# X-Ray: {scope}

**Date**: {YYYY-MM-DD}
**Scope**: {What system/component inspected}

---

## Executive Summary

**Architecture Pattern**: {Primary pattern identified}

**Key Observations**:
- {Observation 1}
- {Observation 2}
- {Observation 3}

**Notable Trade-offs**:
1. {Trade-off 1 and current choice}
2. {Trade-off 2 and current choice}

---

## Component Inventory

### Compute Components
{Table of compute components}

### Storage Components
{Table of storage components}

### Integration Components
{Table of integration components}

---

## Boundary Map

### Service Boundaries
{List of service boundaries with contracts}

### Data Boundaries
{List of data boundaries with type transitions}

### Phase/Network/Permission Boundaries
{Other boundary types}

---

## Dependency Graph

```
{ASCII diagram of dependencies}
```

**Critical Path**: {Longest latency path}
**Bottlenecks**: {Components on critical path}

---

## Pattern Analysis

**Overall Pattern**: {Pattern name and how applied}

**Integration Patterns**:
{Sync, async, batch patterns in use}

**Anti-Patterns Detected**:
{Any problematic patterns found}

---

## Trade-off Analysis

| Trade-off | Current Position | Rationale |
|-----------|-----------------|-----------|
| Performance vs Scalability | {Position} | {Why} |
| Consistency vs Availability | {Position} | {Why} |
| ... | ... | ... |

---

## Assessment

### Strengths
{What works well}

### Weaknesses
{What needs improvement}

### Scalability
{Vertical/horizontal limits}

### Reliability
{SPOFs, fault tolerance, recovery}

---

## Observations (Not Recommendations)

X-ray reveals structure, it doesn't prescribe changes.
For design recommendations, use `/design` after this analysis.

**Observations for further investigation**:
- {Observation that might need `/what-if` analysis}
- {Observation that might need `/design` work}
```

---

## Examples

### Example 1: Report Generation Pipeline

```bash
/x-ray "report generation pipeline"
```

**Output**:
```markdown
# X-Ray: Report Generation Pipeline

**Pattern**: Event-Driven + ETL

**Components**:
- EventBridge Scheduler: Triggers daily at 5:33 AM Bangkok
- Lambda (Precompute): ETL worker (timeout: 300s, memory: 1024MB)
- Aurora MySQL: Source of truth (dr-daily-report-aurora-dev)
- S3: Artifact storage (PDF reports)
- DynamoDB: Cache layer (user_facing_scores)

**Boundaries**:
- Service: Scheduler → Lambda (JSON event), Lambda → Aurora (MySQL protocol)
- Data: Python dict → JSON → MySQL JSON column
- Phase: Docker build → Lambda deployment (container image)
- Network: VPC-isolated Lambda → VPC Aurora, NAT Gateway → Internet

**Dependencies**:
Scheduler → Lambda → [Aurora, S3, DynamoDB] (parallel after Lambda)

**Pattern**: ETL
- Extract: yfinance API (market data)
- Transform: Lambda (calculate scores, generate PDF)
- Load: Aurora (precomputed_reports), S3 (PDFs), DynamoDB (cache)

**Trade-offs**:
- Performance vs Cost: Chose 1024MB Lambda (faster) over 128MB (cheaper)
  - Rationale: PDF generation needs memory, timeout critical
- Consistency vs Availability: Chose eventual consistency (cache) over strong
  - Rationale: Stale cache acceptable for 1-day-old reports

**Strengths**:
- Clear separation: ETL (precompute) vs API (read-only)
- Aurora-first: APIs don't call external services
- Event-driven: Scheduler decouples trigger from execution

**Weaknesses**:
- Single Lambda: No parallel processing of 46 tickers
- No retry: Scheduler doesn't retry failed jobs
- Missing monitoring: No alerts on precompute failures

**Observations for further investigation**:
- Consider `/what-if "parallel Lambda processing"`
- Consider `/design "retry mechanism for precompute"`
```

---

### Example 2: Data Flow Inspection

```bash
/x-ray "user request to report delivery"
```

**Output**:
```markdown
# X-Ray: User Request to Report Delivery

**Trace**:
```
User → Telegram Bot → API Gateway → Lambda → Aurora → Response → User
```

**Boundaries Crossed**:
1. User → Telegram: HTTPS, Telegram Bot API
2. Telegram → API Gateway: Webhook (POST /callback)
3. API Gateway → Lambda: JSON event, IAM auth
4. Lambda → Aurora: MySQL protocol, VPC network
5. Lambda → Response: JSON, HTTP 200
6. Response → User: Telegram message with PDF/chart

**Latency Breakdown** (typical):
- Telegram webhook: ~50ms
- API Gateway: ~10ms
- Lambda cold start: ~1-3s (if cold)
- Lambda warm: ~50ms
- Aurora query: ~10-100ms
- Response: ~50ms
- **Total**: ~200ms warm, ~3.5s cold

**Bottlenecks Identified**:
1. Lambda cold start (dominates latency)
2. Aurora query (complex joins)

**Data Transformations**:
- Telegram message → Python dict (webhook handler)
- Dict → SQL query (report service)
- MySQL result → ReportResponse (Pydantic)
- ReportResponse → JSON → Telegram message

**Observations**:
- Cold start is the primary latency bottleneck
- Consider `/what-if "provisioned concurrency"` for latency reduction
```

---

## Relationship to Other Commands

**Before `/x-ray`**:
- Use when you need to understand existing system

**After `/x-ray`**:
- `/what-if` - Compare alternatives identified
- `/design` - Create new solutions for weaknesses found
- `/impact` - Assess impact of proposed changes

**Workflow**:
```bash
# Understand current architecture
/x-ray "report generation pipeline"
  ↓ (reveals weaknesses: single Lambda, no retry)

# Explore alternatives
/what-if "parallel Lambda processing vs sequential"
  ↓ (compares parallelization approaches)

# Create new design
/design aws "parallel report generation with Step Functions"
  ↓ (designs new architecture)

# Assess impact
/impact "migrate to parallel Lambda processing"
  ↓ (evaluates migration risk, effort, benefit)
```

---

## Integration with CLAUDE.md Principles

**Principle #20 (Execution Boundaries)**:
- X-ray systematically identifies execution boundaries
- Service, data, phase, network, permission boundaries
- Reveals WHERE code runs, WHAT it needs

**Principle #19 (Cross-Boundary Contract Testing)**:
- Boundary analysis identifies contracts to test
- Phase boundaries (build → runtime) need deployment fidelity tests
- Data boundaries (Python → MySQL) need type conversion tests

**Principle #2 (Progressive Evidence Strengthening)**:
- Component analysis: Surface evidence (exists in codebase)
- Dependency mapping: Content evidence (control/data flow)
- Pattern recognition: Observability evidence (logs, metrics)
- Assessment: Ground truth evidence (actual behavior)

---

## See Also

- **Commands**:
  - `/design` - Create new solutions (after X-ray)
  - `/what-if` - Compare alternatives
  - `/analysis` - Comprehensive analysis workflow
  - `/impact` - Assess change impact

- **Skills**:
  - [research](../skills/research/) - Investigation methodology
  - [code-review](../skills/code-review/) - PR review with architecture awareness

- **Principles**:
  - Principle #20: Execution Boundary Discipline
  - Principle #19: Cross-Boundary Contract Testing
  - Principle #2: Progressive Evidence Strengthening
