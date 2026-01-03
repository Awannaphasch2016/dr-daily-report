---
name: architect
description: Architecture analysis - components, boundaries, dependencies, patterns, and trade-offs
accepts_args: true
arg_schema:
  - name: scope
    required: true
    description: "System or component to analyze (e.g., 'report generation pipeline', 'telegram bot architecture')"
composition:
  - skill: research
---

# Architect Command

**Purpose**: Analyze system architecture from components to trade-offs

**Core Principle**: "Understand the system structure before making changes" - architectural analysis reveals components, boundaries, dependencies, patterns, and trade-offs.

**When to use**:
- Before major refactoring (understand current architecture)
- Making architectural decisions (compare patterns, evaluate trade-offs)
- Onboarding to codebase (understand system structure)
- Planning scalability improvements (identify bottlenecks, constraints)
- Debugging distributed systems (map component interactions)

**When NOT to use**:
- Simple code changes (no architectural impact)
- Single-component modifications (use `/explore` instead)
- Quick lookups (use Grep/Read instead)

---

## Quick Reference

```bash
# Understand report generation architecture
/architect "report generation pipeline"
→ Components: Scheduler, Lambda, Aurora, S3, Cache
→ Boundaries: Service (Lambda→Aurora), Data (Python→MySQL), Network (VPC)
→ Dependencies: Scheduler→Lambda→Aurora→S3
→ Pattern: Event-driven + ETL
→ Trade-offs: Consistency vs Availability, Cost vs Performance

# Compare deployment architectures
/architect "current deployment vs blue-green"
→ Components: GitHub Actions, ECR, Lambda, Step Functions
→ Pattern: Current = Direct deployment, Blue-Green = Parallel environments
→ Trade-offs: Simplicity vs Zero-downtime

# Analyze data flow
/architect "user request to report delivery"
→ Trace: API Gateway → Lambda → Aurora → Response
→ Boundaries: API Gateway→Lambda (HTTP), Lambda→Aurora (MySQL protocol)
→ Bottlenecks: Aurora query latency, Lambda cold start
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

**Output**: Assessment report with strengths, weaknesses, and recommendations

---

### Phase 7: Recommendations

**Provide actionable architecture improvements**:

**1. Immediate Improvements** (low effort, high impact):
- Quick wins that improve architecture without major changes
- Example: Add connection pooling, implement caching, add retry logic

**2. Short-term Improvements** (medium effort, medium impact):
- Incremental changes over 1-2 sprints
- Example: Refactor monolithic Lambda, add API Gateway caching, implement CDN

**3. Long-term Improvements** (high effort, high impact):
- Strategic changes over multiple months
- Example: Migrate to microservices, implement CQRS, add event sourcing

**4. Technology Recommendations**:
- Better tools/libraries for current patterns
- Example: Use connection pooler (RDS Proxy), adopt ORM (SQLAlchemy), use caching library (Redis)

**5. Pattern Recommendations**:
- Better architectural patterns for requirements
- Example: Event-driven for async, CQRS for read-heavy, Saga for distributed transactions

**For each recommendation**:
- **What**: Specific change
- **Why**: Problem it solves
- **How**: Implementation approach
- **Effort**: Time/complexity estimate
- **Risk**: What could go wrong
- **Priority**: Critical/High/Medium/Low

**Output**: Prioritized recommendation list with implementation guidance

---

## Output Format

```markdown
# Architecture Analysis: {scope}

**Date**: {YYYY-MM-DD}
**Scope**: {What system/component analyzed}

---

## Executive Summary

**Architecture Pattern**: {Primary pattern identified}

**Key Findings**:
- {Finding 1}
- {Finding 2}
- {Finding 3}

**Top Recommendations**:
1. {Recommendation 1}
2. {Recommendation 2}
3. {Recommendation 3}

---

## Component Inventory

### Compute Components

**{Component Name}** (Lambda/EC2/Container)
- **Purpose**: {What it does}
- **Technology**: {Python 3.12, Node.js 18, etc.}
- **Configuration**: {Timeout: 30s, Memory: 512MB, etc.}
- **Location**: {file paths, Terraform: aws_lambda_function.name}

[Repeat for each compute component]

### Storage Components

**{Component Name}** (Aurora/S3/DynamoDB)
- **Purpose**: {What data it stores}
- **Technology**: {MySQL 8.0, etc.}
- **Configuration**: {Instance type, storage size, etc.}
- **Location**: {Terraform: aws_db_instance.name}

[Repeat for each storage component]

### Integration Components

[Similar structure for API Gateway, SQS, SNS, Step Functions, EventBridge]

---

## Boundary Map

### Service Boundaries

**{Boundary Name}** ({Component A} → {Component B})
- **Protocol**: {HTTP/REST, MySQL, AWS SDK, etc.}
- **Contract**: {Expected format/structure}
- **Validation**: {How enforced}
- **Failure Mode**: {What happens when violated}
- **Evidence**: {Code location, Terraform resource}

[Repeat for each service boundary]

### Data Boundaries

**{Boundary Name}** ({Type A} → {Type B})
- **Transformation**: {How data converted}
- **Validation**: {Type checking, schema validation}
- **Failure Mode**: {Type error, schema mismatch}
- **Evidence**: {Code location}

[Repeat for each data boundary]

### Phase Boundaries

[Similar structure]

### Network Boundaries

[Similar structure]

### Permission Boundaries

[Similar structure]

---

## Dependency Graph

### Control Flow Diagram

```
┌─────────────┐
│  Component  │
└──────┬──────┘
       │ (relationship)
┌──────▼──────┐
│  Component  │
└─────────────┘
```

### Data Flow Diagram

```
[Input] → [Transform] → [Process] → [Store] → [Output]
```

### Critical Path

**Path**: {Component A} → {Component B} → {Component C}
**Total Latency**: {Sum of component latencies}
**Bottleneck**: {Slowest component}

---

## Pattern Analysis

### Overall Architecture Pattern

**Pattern**: {Microservices | Serverless | Event-Driven | Layered | etc.}

**How applied**:
{Explanation of how pattern manifests in codebase}

**Alignment**: {Good fit | Partial fit | Misalignment}

**Evidence**:
- {Example 1 from codebase}
- {Example 2 from codebase}

### Integration Patterns

**Synchronous Integration**:
- {Component A} → {Component B}: Request-Response via {protocol}

**Asynchronous Integration**:
- {Component X} → Queue → {Component Y}: Fire-and-Forget via SQS

**Batch Processing**:
- Scheduler → Lambda: Scheduled job every {interval}

### Data Patterns

**ETL Pattern**:
- Extract: {Source}
- Transform: {Lambda function}
- Load: {Destination}

**Caching Pattern**:
- Type: {Cache-Aside | Write-Through | etc.}
- Implementation: {DynamoDB, ElastiCache, etc.}

### Anti-Patterns Detected

**{Anti-Pattern Name}**:
- **Where**: {Component/file location}
- **Impact**: {How it hurts}
- **Fix**: {How to resolve}

---

## Trade-off Analysis

### Performance vs Scalability

**Current Position**: {Where on spectrum}

**Choice**: {What chosen}

**Rationale**: {Why chosen}

**Alternatives Considered**:
- {Alternative 1}: {Trade-off}
- {Alternative 2}: {Trade-off}

**Constraints**: {What limited choice}

---

[Repeat for each trade-off dimension]

---

## Architecture Assessment

### Strengths

1. **{Strength 1}**: {Explanation}
   - Example: {Evidence from codebase}

2. **{Strength 2}**: {Explanation}

[Continue...]

### Weaknesses

1. **{Weakness 1}**: {Explanation}
   - Impact: {How it hurts}
   - Evidence: {Location in codebase}

2. **{Weakness 2}**: {Explanation}

[Continue...]

### Scalability Assessment

**Vertical Scalability**: {Assessment}
- Limits: {What prevents scale-up}
- Headroom: {How much more capacity}

**Horizontal Scalability**: {Assessment}
- Limits: {What prevents scale-out}
- Bottlenecks: {Which components limit}

**Recommendation**: {How to improve scalability}

### Reliability Assessment

**Single Points of Failure**:
- {Component}: {How it fails, mitigation}

**Fault Tolerance**:
- Retry logic: {Present/Missing}
- Circuit breakers: {Present/Missing}
- Graceful degradation: {Present/Missing}

**Recovery**:
- RTO: {Recovery time objective}
- RPO: {Recovery point objective}

### Maintainability Assessment

**Code Organization**: {Assessment}

**Documentation**: {Assessment}

**Testing**: {Assessment}

---

## Recommendations

### Immediate (Low Effort, High Impact)

**1. {Recommendation}**
- **What**: {Specific change}
- **Why**: {Problem solved}
- **How**: {Implementation steps}
- **Effort**: {1-2 days}
- **Risk**: {Low/Medium/High}
- **Priority**: Critical

[Repeat for each immediate recommendation]

### Short-term (Medium Effort, Medium Impact)

[Similar structure, 1-2 weeks effort]

### Long-term (High Effort, High Impact)

[Similar structure, 1-3 months effort]

### Technology Recommendations

**Replace {Current Tech} with {Recommended Tech}**:
- **Why**: {Benefits}
- **Migration Path**: {How to migrate}
- **Risks**: {What could go wrong}

### Pattern Recommendations

**Adopt {Pattern Name}**:
- **Where**: {Which component/system}
- **Why**: {Problem it solves}
- **How**: {Implementation approach}
- **Examples**: {Similar systems using this pattern}

---

## Appendix

### Component List
{Complete list of all components with metadata}

### Boundary List
{Complete list of all boundaries with contracts}

### Dependency Matrix
{Matrix showing which components depend on which}

### Technology Stack
{All technologies/libraries/frameworks used}
```

---

## Examples

### Example 1: Report Generation Pipeline

```bash
/architect "report generation pipeline"
```

**Output**:
```markdown
# Architecture Analysis: Report Generation Pipeline

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
- Network: VPC-isolated Lambda → VPC Aurora, NAT Gateway → Internet (yfinance API)

**Dependencies**:
Scheduler → Lambda → [Aurora, S3, DynamoDB] (parallel after Lambda)

**Pattern**: ETL
- Extract: yfinance API (market data)
- Transform: Lambda (calculate scores, generate PDF)
- Load: Aurora (precomputed_reports), S3 (PDFs), DynamoDB (cache)

**Trade-offs**:
- Performance vs Cost: Chose 1024MB Lambda (faster) over 128MB (cheaper)
  - Rationale: PDF generation needs memory, timeout critical
- Consistency vs Availability: Chose eventual consistency (cache) over strong consistency
  - Rationale: Stale cache acceptable for 1-day-old reports

**Strengths**:
- Clear separation: ETL (precompute) vs API (read-only)
- Aurora-first: APIs don't call external services
- Event-driven: Scheduler decouples trigger from execution

**Weaknesses**:
- Single Lambda: No parallel processing of 46 tickers
- No retry: Scheduler doesn't retry failed jobs
- Missing monitoring: No alerts on precompute failures

**Recommendations**:
1. **Immediate**: Add CloudWatch alarm on Lambda errors
2. **Short-term**: Implement retry logic in Step Functions
3. **Long-term**: Parallelize ticker processing (46 concurrent Lambdas)
```

---

### Example 2: Compare Architectures

```bash
/architect "current SQS architecture vs direct Step Functions invocation"
```

**Output**:
```markdown
# Architecture Analysis: SQS vs Direct Invocation

## Current Architecture (SQS-based)

**Components**:
- Step Functions: Orchestrator
- SQS Queue: Message buffer
- Lambda: Worker (polls SQS)

**Flow**: Step Functions → SQS → Lambda (async)

**Pattern**: Producer-Consumer via message queue

**Trade-offs**:
- Decoupling: High (queue buffers requests)
- Complexity: Medium (SQS config, DLQ, visibility timeout)
- Cost: Medium (SQS charges per request)
- Latency: Higher (queue polling delay)

---

## Alternative Architecture (Direct Invocation)

**Components**:
- Step Functions: Orchestrator
- Lambda: Worker (direct invoke)

**Flow**: Step Functions → Lambda (sync)

**Pattern**: Direct function call

**Trade-offs**:
- Decoupling: Low (tight coupling)
- Complexity: Low (no queue config)
- Cost: Low (no SQS charges)
- Latency: Lower (direct invocation)

---

## Comparison Matrix

| Aspect | SQS-based | Direct Invocation | Winner |
|--------|-----------|-------------------|--------|
| Decoupling | High (queue buffer) | Low (tight coupling) | SQS |
| Complexity | Medium (queue config) | Low (simple) | Direct |
| Cost | Medium (SQS charges) | Low (Lambda only) | Direct |
| Latency | Higher (polling delay) | Lower (immediate) | Direct |
| Retry | Built-in (SQS) | Manual (Step Functions) | SQS |
| Monitoring | 2 components | 1 component | Direct |

**Recommendation**: Switch to Direct Invocation
- Current system doesn't benefit from SQS decoupling
- Synchronous processing is acceptable
- Simplicity > Decoupling for this use case
- Cost savings: Eliminate SQS charges
```

---

## Relationship to Other Commands

**Before `/architect`**:
- `/explore` - Quick understanding of system
- `/research` - General investigation

**After `/architect`**:
- `/what-if` - Compare architectural alternatives
- `/impact` - Assess impact of architectural changes
- `/check-principles` - Verify architecture follows CLAUDE.md principles

**Workflow**:
```bash
# Understand current architecture
/architect "report generation pipeline"
  ↓ (identifies weaknesses: single Lambda, no retry)

# Explore alternatives
/what-if "parallel Lambda processing vs sequential"
  ↓ (compares parallelization approaches)

# Assess impact
/impact "migrate to parallel Lambda processing"
  ↓ (evaluates migration risk, effort, benefit)

# Verify compliance
/check-principles
  ↓ (checks if new architecture follows principles)
```

---

## Best Practices

### Do
- **Start broad, then narrow** (overall pattern → components → details)
- **Map all boundaries** (not just components)
- **Identify trade-offs explicitly** (not just "it works")
- **Use diagrams** (visual > text for architecture)
- **Reference real code** (file paths, Terraform resources)
- **Categorize recommendations** (immediate, short-term, long-term)

### Don't
- **Don't skip boundary analysis** (boundaries reveal integration issues)
- **Don't ignore anti-patterns** (they predict future problems)
- **Don't assume optimal** (every architecture has trade-offs)
- **Don't forget constraints** (budget, time, compliance affect choices)
- **Don't recommend without rationale** (explain WHY change needed)

---

## Integration with CLAUDE.md Principles

**Principle #20 (Execution Boundaries)**:
- Architect command systematically identifies execution boundaries
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
  - `/explore` - Quick multi-angle exploration
  - `/research` - Systematic investigation
  - `/what-if` - Compare alternatives
  - `/impact` - Assess change impact
  - `/check-principles` - Verify compliance

- **Skills**:
  - [research](../skills/research/) - Investigation methodology
  - [code-review](../skills/code-review/) - PR review with architecture awareness

- **Checklists**:
  - [execution-boundaries.md](../checklists/execution-boundaries.md) - Boundary verification

- **Principles**:
  - Principle #20: Execution Boundary Discipline
  - Principle #19: Cross-Boundary Contract Testing
  - Principle #2: Progressive Evidence Strengthening

---

## Prompt Template

You are executing the `/architect` command with arguments: $ARGUMENTS

**Scope**: $1

---

### Execution Steps

**Phase 1: Component Identification**

Identify all components in scope:
1. Compute: Lambda, EC2, containers
2. Storage: Aurora, S3, DynamoDB, caches
3. Integration: API Gateway, SQS, SNS, Step Functions, EventBridge
4. Network: VPC, Load Balancers, CloudFront
5. Supporting: IAM, CloudWatch, Secrets Manager

For each: purpose, technology, configuration, location (code/Terraform)

**Phase 2: Boundary Analysis**

Identify boundaries:
1. Service boundaries (component-to-component)
2. Data boundaries (type system transitions)
3. Phase boundaries (lifecycle transitions)
4. Network boundaries (network transitions)
5. Permission boundaries (security transitions)

For each: contract, validation, failure mode

**Phase 3: Dependency Mapping**

Map dependencies:
1. Control flow (execution order)
2. Data flow (data movement)
3. Dependency graph (visualization)
4. Critical path (latency analysis)

**Phase 4: Pattern Recognition**

Identify patterns:
1. Overall architecture pattern (microservices, serverless, event-driven, etc.)
2. Integration patterns (sync, async, batch)
3. Data patterns (ETL, caching, event sourcing)
4. Design patterns (repository, factory, singleton)
5. Anti-patterns (god object, spaghetti, etc.)

**Phase 5: Trade-off Analysis**

Evaluate trade-offs:
1. Performance vs Scalability
2. Consistency vs Availability
3. Simplicity vs Flexibility
4. Cost vs Capability
5. Security vs Convenience

For each: current position, rationale, alternatives, constraints

**Phase 6: Architecture Assessment**

Assess quality:
1. Strengths (what works well)
2. Weaknesses (what needs improvement)
3. Scalability assessment (vertical, horizontal, bottlenecks)
4. Reliability assessment (SPOF, fault tolerance, recovery)
5. Maintainability assessment (code org, docs, tests)

**Phase 7: Recommendations**

Provide improvements:
1. Immediate (low effort, high impact)
2. Short-term (medium effort, medium impact)
3. Long-term (high effort, high impact)
4. Technology recommendations
5. Pattern recommendations

For each: what, why, how, effort, risk, priority

---

### Output

Use the output format above, including:
- Executive summary (pattern, findings, top recommendations)
- Component inventory (all components with metadata)
- Boundary map (all boundaries with contracts)
- Dependency graph (visual representation)
- Pattern analysis (patterns and anti-patterns)
- Trade-off analysis (current choices and rationale)
- Architecture assessment (strengths, weaknesses, scalability, reliability, maintainability)
- Recommendations (prioritized with implementation guidance)
