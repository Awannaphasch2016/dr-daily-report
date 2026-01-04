---
name: problem-statement
description: Recap current decision point with full context - explains what you're deciding and why it matters
accepts_args: false
composition:
  - skill: research
---

# Problem-Statement Command

**Purpose**: Help you understand what decision you're making when context is lost or unclear

**Core Principle**: "Informed decisions require complete context" - never ask users to decide without full understanding

**When to use**:
- Claude asks for decision but you don't know what problem this solves
- Long conversation (>30 messages) and context is buried
- Returning to conversation after break (need catch-up)
- Multiple options presented but trade-offs unclear
- Need structured comparison to make informed choice

**When NOT to use**:
- Context is fresh (just discussed in last 2-3 messages)
- Simple yes/no with obvious answer
- Already understand the problem

---

## Quick Reference

```bash
# Claude asks: "Should we use Redis or DynamoDB?"
# You think: "Wait, why do we need caching? What problem are we solving?"

/problem-statement

Output:
# Problem Statement

**Decision needed**: Choose caching technology (Redis vs DynamoDB)

## Original Goal
You requested faster API responses (currently 500ms, target <100ms)

## How We Got Here
Message 10: Requested faster API
Message 25: Identified database query latency as bottleneck
Message 40: Proposed caching solution
Message 58: Narrowed to Redis vs DynamoDB (CURRENT)

## Problem (Clear & Simple)
Your API is slow because database queries take 300ms each. Adding a cache will reduce this to ~5-10ms. Need to choose between Redis (faster but complex) or DynamoDB (simpler but slightly slower).

**In short**: Choose cache technology to make API faster

## Decision Framework
[Structured comparison with pros/cons/trade-offs]

Now you have full context to decide!
```

---

## Execution Flow

### Phase 1: Identify Current Decision Point

**What is Claude asking you to decide?**

**Scan recent messages** (last 5-10) for:
- Direct questions: "Which approach?", "Should we...?", "Do you prefer...?"
- Blocked progress: "Need your input on X", "Can't proceed without decision"
- Option presentations: "Option A: ..., Option B: ..."
- Approval requests: "Proceed with X?"

**Extract**:
```
Decision point:
- Question asked: {Exact question Claude posed}
- Options presented: {List of alternatives, if any}
- Why blocked: {Why Claude needs input to proceed}
- When asked: {Message number/timestamp}
```

**If no decision point found**:
```
No active decision point detected in recent messages.

Last 10 messages reviewed:
- Information exchange
- Code writing
- Research/exploration

No question or approval request found.

If you need context for a specific decision:
→ Ask Claude to clarify what decision is needed
→ Use /reflect to understand current task state
```

---

### Phase 2: Trace Problem Origin

**How did we get to this decision point?**

**Search conversation history backward** from current position:

1. **Find initial problem/request** (original user message):
   - Look for original goal or problem statement
   - Identify when conversation started
   - Extract user's initial intent

2. **Trace evolution** (key milestones):
   - Significant discoveries or realizations
   - Major decisions made along the way
   - Narrowing of options or focus
   - Changes in direction

3. **Build timeline**:
   ```
   Message N: {Initial problem/request}
   Message N+X: {Key discovery or decision}
   Message N+Y: {Narrowing to specific options}
   Message N+Z: {Current decision point}
   ```

**Output**:
```markdown
## How We Got Here

**Timeline**:
- Message 10: You requested "Make API faster"
- Message 15: Identified database query latency as bottleneck (300ms)
- Message 25: Proposed caching as solution
- Message 40: Researched cache options (Redis, DynamoDB, ElastiCache)
- Message 50: Narrowed to Redis vs DynamoDB
- Message 58: Asked you to choose (CURRENT)

**Narrative**:
You asked for faster API responses because users complained about slow load times. We discovered database queries were taking 300ms per request. After analyzing options, caching emerged as the best solution. Researched multiple technologies and narrowed to two viable options based on your constraints (budget, existing infrastructure). Now at decision point: which cache to implement.
```

---

### Phase 3: Gather Relevant Context

**What information is needed to make this decision?**

**Collect from conversation**:

1. **Technical Constraints**:
   - Budget limitations
   - Time constraints
   - Existing infrastructure
   - Team expertise
   - Technology stack

2. **Requirements**:
   - Performance targets
   - Scalability needs
   - Reliability requirements
   - Compliance requirements

3. **Trade-offs Discussed**:
   - Speed vs Complexity
   - Cost vs Capability
   - Simplicity vs Flexibility
   - Short-term vs Long-term

4. **Previous Decisions**:
   - What was already decided
   - Why those decisions were made
   - How they constrain current choice

5. **Context Not Yet Discussed** (but relevant):
   - Standard trade-offs for this decision type
   - Common pitfalls
   - Industry best practices

**Output**:
```markdown
## Relevant Context

### Technical Constraints
- Budget: $100/month max for infrastructure
- Timeline: Need solution in 2 weeks
- Infrastructure: AWS Lambda + Aurora MySQL
- Team: 2 developers, no dedicated DevOps
- Stack: Python 3.12, serverless architecture

### Requirements
- Performance: P99 latency < 100ms (currently 500ms)
- Scalability: Handle 1000 req/min (current: 200 req/min)
- Reliability: 99.9% uptime required
- Data freshness: 5-minute stale data acceptable

### Trade-offs in Play
- Performance vs Operational complexity
- Cost vs Capability
- Simplicity vs Future flexibility
- Build vs Buy (managed service)

### Previous Decisions
- Already decided: Use caching (not query optimization alone)
- Already decided: Stay on AWS (not multi-cloud)
- Already decided: Serverless (not EC2)

### Additional Context
- Cache miss rate: ~20% expected (80% hit rate target)
- Data size: ~1MB per cache entry
- Cache invalidation: Time-based (5 min TTL)
```

---

### Phase 4: Restate Problem Clearly

**Explain the problem in simple, clear terms** (suitable for someone joining conversation now):

**Structure**:
1. **Original goal**: What you wanted to achieve
2. **Current situation**: Where we are now
3. **Specific problem**: What's blocking progress
4. **Why decision needed**: What happens if we don't decide
5. **Impact**: How this affects the project

**Output**:
```markdown
## Problem Statement (Clear & Simple)

**Original goal**: Make API responses faster

Your users complained about slow API response times (500ms average). You wanted to improve this to under 100ms to provide better user experience.

**Current situation**:

We analyzed the performance and discovered database queries are the bottleneck, taking 300ms per request. After evaluating multiple optimization strategies, caching emerged as the most effective solution to reduce database load.

We researched several caching technologies (Redis, DynamoDB, ElastiCache, Memcached) and narrowed down to two options that fit your constraints:
- Redis: Extremely fast but requires managing separate service
- DynamoDB: Slightly slower but fully managed and simpler

**Specific problem**:

Need to choose which caching technology to implement. Can't implement both due to time and complexity constraints. Different technologies lead to different architectures and maintenance requirements.

**Why decision needed**:

This decision blocks the cache implementation (estimated 2-week task). Without choosing, we can't:
- Write cache integration code
- Set up infrastructure (Terraform)
- Test performance improvements
- Deliver faster API to users

**Impact**:

**Immediate**: Delays API performance improvement by however long decision takes

**Future**: Influences architectural patterns for other components (if we use DynamoDB for caching, natural to use it elsewhere; if Redis, need to maintain separate cache service)

**Cost**: Affects monthly infrastructure spend ($20-150/month difference)

---

**In short**: Choose between Redis (faster, more complex) or DynamoDB (simpler, slightly slower) for API caching to achieve <100ms response time goal.
```

---

### Phase 5: Present Decision Framework

**Provide structured comparison to enable informed decision**:

**For each option**:
1. **What it is**: Brief description (1-2 sentences)
2. **How it works**: Technical approach
3. **Pros**: Advantages (3-5 bullet points)
4. **Cons**: Disadvantages (3-5 bullet points)
5. **Best for**: When to choose this (conditions)
6. **Not good for**: When NOT to choose this (anti-conditions)
7. **Effort**: Implementation complexity and time

**Comparison matrix**:
- Key decision criteria in rows
- Options in columns
- Winner per criterion

**Recommendation** (if one option clearly better):
- Suggested option with rationale
- Conditions when suggestion doesn't apply

**Output**:
```markdown
## Decision Framework

### Option 1: Redis (ElastiCache)

**What it is**: In-memory cache, separate service managed by AWS ElastiCache

**How it works**:
Lambda → ElastiCache (Redis) → Aurora
- Check cache first
- If miss, query Aurora, populate cache
- If hit, return cached data

**Pros**:
- ⚡ Extremely fast: P99 < 1ms latency
- 🔧 Rich data structures: Lists, sets, sorted sets, pub/sub
- 📊 Proven at scale: Used by major companies (Twitter, GitHub, StackOverflow)
- 🔍 Advanced features: TTL, eviction policies, persistence options
- 💪 High throughput: Millions of ops/second

**Cons**:
- 💰 Higher cost: $50-150/month for managed instance
- 🛠️ Operational complexity: Separate service to monitor/maintain
- 🌐 Network hop: Lambda → VPC → ElastiCache (adds latency vs co-located)
- 🔒 VPC required: Lambda needs VPC config (cold start impact)
- 📚 Learning curve: Redis-specific knowledge needed

**Best for**:
- Need sub-5ms cache latency
- Using complex data structures (leaderboards, rate limiting)
- Already have Redis expertise
- Budget allows $100+/month
- High-traffic application (>10K req/min)

**Not good for**:
- Budget constrained (<$50/month)
- Want minimal ops overhead
- Don't need sub-5ms latency
- Small team without Redis experience

**Implementation effort**:
- Setup: 2-3 days (ElastiCache cluster, VPC config, Lambda changes)
- Complexity: Medium-High

---

### Option 2: DynamoDB

**What it is**: Managed NoSQL database, serverless, single-digit millisecond latency

**How it works**:
Lambda → DynamoDB (cache table) → Aurora
- Check DynamoDB cache first (GetItem)
- If miss, query Aurora, write to DynamoDB (PutItem)
- If hit, return cached data

**Pros**:
- 🎯 Simple integration: Native AWS SDK, no VPC needed
- 💰 Cost-effective: $10-30/month typical usage
- 🔧 Low ops overhead: Fully managed, auto-scaling
- ⚡ Serverless: No cluster to manage
- 📈 Automatic scaling: Handles traffic spikes
- 🔒 Built-in security: IAM integration, encryption

**Cons**:
- 🐌 Slower than Redis: P99 ~5-10ms (vs <1ms)
- 📦 Limited data structures: Key-value only (no lists, sets)
- 💸 Read/write units: Need to manage capacity (or use on-demand)
- 🔍 Less flexible: Limited querying compared to Redis
- ⏱️ Eventual consistency: Default read mode (can use strongly consistent)

**Best for**:
- Budget constrained (<$50/month)
- Want minimal operational overhead
- 5-10ms latency acceptable (meets <100ms requirement)
- Already using AWS serverless stack
- Small team (no dedicated DevOps)

**Not good for**:
- Need sub-5ms latency
- Need complex data structures (sorted sets, pub/sub)
- Already have Redis infrastructure
- High-frequency updates (>1000 writes/sec sustained)

**Implementation effort**:
- Setup: 1-2 days (DynamoDB table, Lambda code, TTL config)
- Complexity: Low-Medium

---

## Comparison Matrix

| Criterion | Redis (ElastiCache) | DynamoDB | Winner | Weight |
|-----------|-------------------|----------|--------|--------|
| **Latency (P99)** | <1ms | 5-10ms | Redis ⚡ | High |
| **Cost (monthly)** | $50-150 | $10-30 | DynamoDB 💰 | High |
| **Ops Complexity** | High (manage cluster) | Low (fully managed) | DynamoDB 🎯 | High |
| **Setup Time** | 2-3 days | 1-2 days | DynamoDB ⏱️ | Medium |
| **AWS Integration** | Medium (VPC needed) | High (native) | DynamoDB 🔗 | Medium |
| **Data Structures** | Rich (lists, sets, etc.) | Basic (key-value) | Redis 🔧 | Low |
| **Scalability** | Manual (resize cluster) | Automatic (serverless) | DynamoDB 📈 | Medium |
| **Learning Curve** | Steeper (Redis knowledge) | Easier (AWS SDK) | DynamoDB 📚 | Medium |

**Overall**: DynamoDB wins on cost, simplicity, and ops overhead (high-weight criteria)

---

## Recommendation

**Suggested option**: DynamoDB

**Rationale**:
1. **Meets requirement**: 5-10ms latency achieves <100ms goal (currently 500ms)
2. **Cost-effective**: $10-30/month vs $50-150/month (fits $100 budget with room for other services)
3. **Simpler ops**: Fully managed, no cluster to maintain (matches team size: 2 developers)
4. **Faster implementation**: 1-2 days vs 2-3 days (meets 2-week timeline)
5. **Native AWS integration**: Already using Lambda, Aurora (serverless stack)
6. **Auto-scaling**: Handles traffic spikes without manual intervention

**Trade-off accepted**: Slightly slower than Redis (5-10ms vs <1ms), but still 30-50x faster than current (300ms)

**When to choose Redis instead**:
- If latency requirement tightens to <5ms (currently <100ms, so plenty of headroom)
- If you need complex data structures (leaderboards, rate limiting with sorted sets)
- If budget increases significantly (>$200/month for infrastructure)
- If team gains Redis expertise or hires DevOps engineer
- If traffic grows to >10K req/min (Redis handles higher throughput)

---

## What Happens Next

### If you choose DynamoDB (recommended):

**Immediate** (today):
1. Create DynamoDB table for cache (Terraform)
   - Hash key: `cache_key` (string)
   - TTL attribute: `expires_at` (number)
   - On-demand billing mode

**Short-term** (this week):
2. Implement cache layer in Lambda:
   ```python
   def get_data(key):
       # Check DynamoDB cache
       cache = dynamodb.get_item(Key={'cache_key': key})
       if cache and not is_expired(cache):
           return cache['data']

       # Cache miss: query Aurora
       data = aurora.query(...)

       # Populate cache
       dynamodb.put_item({
           'cache_key': key,
           'data': data,
           'expires_at': time.now() + 300  # 5 min TTL
       })

       return data
   ```

3. Test with load testing
4. Deploy to dev environment
5. Monitor performance (CloudWatch)

**Expected outcome**:
- Latency: 500ms → 50-100ms (with cache) or 5-10ms (cache hit)
- Cost: +$15/month (estimated based on 1000 req/min)
- Timeline: 1-2 days implementation + 2-3 days testing = 3-5 days total

---

### If you choose Redis:

**Immediate** (today):
1. Create ElastiCache Redis cluster (Terraform)
   - Instance: cache.t3.micro (smallest) or cache.t3.small
   - VPC: Create private subnet if not exists
   - Security group: Allow Lambda access

**Short-term** (this week):
2. Configure Lambda VPC access:
   - Add VPC configuration to Lambda
   - Add NAT Gateway for internet access (if needed)
   - Update IAM roles

3. Implement cache layer:
   ```python
   import redis

   redis_client = redis.Redis(host=REDIS_ENDPOINT)

   def get_data(key):
       # Check Redis cache
       cached = redis_client.get(key)
       if cached:
           return json.loads(cached)

       # Cache miss: query Aurora
       data = aurora.query(...)

       # Populate cache with TTL
       redis_client.setex(key, 300, json.dumps(data))

       return data
   ```

4. Test with load testing
5. Deploy to dev environment
6. Monitor performance + ops (CloudWatch + Redis metrics)

**Expected outcome**:
- Latency: 500ms → 20-50ms (with cache) or <1ms (cache hit)
- Cost: +$50-80/month (ElastiCache + NAT Gateway)
- Timeline: 2-3 days implementation + 2-3 days testing + VPC setup = 5-7 days total

---

### If you're still unsure:

**Get more information**:
1. Run load test simulation to verify latency requirements
2. Profile current queries to confirm caching will help
3. Prototype both solutions (1 day each) and compare

**Ask clarifying questions**:
- What's the actual latency requirement? (<100ms or tighter?)
- What's the budget flexibility? ($100 hard limit or negotiable?)
- How important is operational simplicity vs raw performance?

**Test assumptions**:
```bash
/validate "hypothesis: DynamoDB 5-10ms latency sufficient for <100ms requirement"
→ Verify: Current 300ms + 5-10ms cache = 305ms → Still need query optimization
→ Or: Cache eliminates query → 5-10ms total latency ✅
```
```

---

## Output Format

```markdown
# Problem Statement

**Decision needed**: {What you need to decide}

**Asked at**: {When/where Claude asked}

---

## Original Goal

**What you wanted**: {Initial request or goal}

**Started**: {When conversation began}

---

## How We Got Here

**Timeline**:
- Message {N}: {Initial problem/request}
- Message {N+X}: {Key discovery}
- Message {N+Y}: {Narrowing}
- Message {N+Z}: {Current decision point}

**Narrative**:
{How conversation evolved to this point}

---

## Relevant Context

### Technical Constraints
- {Constraint 1}: {Details}
- {Constraint 2}: {Details}

### Requirements
- {Requirement 1}: {Target}
- {Requirement 2}: {Target}

### Trade-offs in Play
- {Trade-off 1}: {Dimensions}
- {Trade-off 2}: {Dimensions}

### Previous Decisions
- {Decision 1}: {What + Why}
- {Decision 2}: {What + Why}

---

## Problem Statement (Clear & Simple)

{2-3 paragraphs explaining problem for someone joining now}

**In short**: {One sentence summary}

---

## Decision Framework

### Option 1: {Name}

**What it is**: {Brief description}

**How it works**: {Technical approach}

**Pros**:
- {Advantage 1}
- {Advantage 2}
- {Advantage 3}

**Cons**:
- {Disadvantage 1}
- {Disadvantage 2}
- {Disadvantage 3}

**Best for**:
- {Condition 1}
- {Condition 2}

**Not good for**:
- {Anti-condition 1}
- {Anti-condition 2}

**Implementation effort**: {Time + Complexity}

---

[Repeat for each option]

---

## Comparison Matrix

| Criterion | Option 1 | Option 2 | Winner | Weight |
|-----------|----------|----------|--------|--------|
| {Criterion 1} | {Score} | {Score} | {Better} | {Importance} |
| {Criterion 2} | {Score} | {Score} | {Better} | {Importance} |

**Overall**: {Which option wins overall}

---

## Recommendation (If Clear)

**Suggested option**: {Option name}

**Rationale**:
- {Reason 1}
- {Reason 2}
- {Reason 3}

**Trade-off accepted**: {What you give up with this choice}

**When to choose {other option} instead**:
- {Condition 1}
- {Condition 2}

---

## What Happens Next

### If you choose {Option 1}:

**Immediate**: {First steps}

**Short-term**: {Implementation tasks}

**Expected outcome**: {Results + Timeline}

---

### If you choose {Option 2}:

**Immediate**: {First steps}

**Short-term**: {Implementation tasks}

**Expected outcome**: {Results + Timeline}

---

### If you're still unsure:

**Get more information**: {How to learn more}

**Ask clarifying questions**: {What to ask}

**Test assumptions**: {How to validate}
```

---

## Examples

### Example 1: Caching Decision (from above)

```bash
# After 60-message conversation about API performance
# Claude asks: "Redis or DynamoDB?"
# User doesn't remember why caching is needed

/problem-statement

[See detailed output above]
```

---

### Example 2: Architecture Decision

```bash
# Conversation about system redesign
# Claude asks: "Microservices or monolith?"
# User needs full context

/problem-statement

Output:
# Problem Statement

**Decision needed**: Choose between microservices or monolithic architecture

## Original Goal
You want to rebuild the system for better scalability and team autonomy

## How We Got Here
- Message 5: Requested system redesign advice
- Message 20: Identified scaling bottlenecks in current monolith
- Message 40: Discussed team structure (3 teams, 12 developers)
- Message 55: Narrowed to microservices vs improved monolith
- Message 60: Asked you to choose (CURRENT)

## Problem (Clear & Simple)
Current monolith has scaling issues and teams step on each other's toes. Microservices would give team autonomy but add operational complexity. Improved monolith (modular) would be simpler but might not solve team coordination.

**In short**: Choose architecture that balances team autonomy with operational complexity

## Decision Framework

### Option 1: Microservices
**Pros**: Team autonomy, independent scaling, fault isolation
**Cons**: Operational complexity, distributed system challenges, higher cost
**Best for**: Large teams (>10 per service), need independent scaling
**Not good for**: Small teams, limited DevOps expertise

### Option 2: Modular Monolith
**Pros**: Simpler operations, easier debugging, lower cost
**Cons**: Shared scaling, team coordination still needed, deployment coupling
**Best for**: Teams <20 total, limited DevOps, simpler domains
**Not good for**: Very different scaling needs per module

## Comparison Matrix
[Detailed comparison]

## Recommendation
Modular Monolith → Microservices (staged migration)
- Start with modular monolith (3 months)
- Identify most problematic module
- Extract to microservice (3 months)
- Repeat as needed

Rationale: Reduces risk, allows learning, doesn't commit to full microservices
```

---

### Example 3: Simple Decision (doesn't need /problem-statement)

```bash
# Recent context (5 messages ago):
# Claude: "I found a typo in README.md: 'teh' should be 'the'"
# Claude: "Should I fix it?"

# User doesn't need /problem-statement here - context is clear
# Just answer: "Yes, fix it"
```

---

## Best Practices

### Do
- **Use when lost** (context buried in long conversation)
- **Use before big decisions** (understand what you're choosing)
- **Read full output** (all sections provide context)
- **Use comparison matrix** (structured analysis helps)
- **Consider recommendation** (but make your own choice)

### Don't
- **Don't use for obvious questions** (wastes time)
- **Don't skip reading output** (defeats purpose)
- **Don't blindly follow recommendation** (it's a suggestion, not mandate)
- **Don't use if context is fresh** (<5 messages ago)

---

## Integration with Other Commands

**`/problem-statement` → Decision → Continue**:
```
/problem-statement (understand decision)
  ↓
Make informed choice
  ↓
Claude proceeds with chosen option
```

**`/problem-statement` → `/architect` (if architecture decision)**:
```
/problem-statement (what are options?)
  ↓
/architect (deep dive into each option)
  ↓
Make decision with full architectural understanding
```

**`/problem-statement` → `/check-principles` (before deploying choice)**:
```
/problem-statement (understand decision)
  ↓
Make choice
  ↓
/check-principles (verify choice follows principles)
  ↓
Deploy
```

**`/reflect` → `/problem-statement` (if stuck)**:
```
/reflect (realize you're stuck on decision)
  ↓
/problem-statement (get context to decide)
  ↓
Make decision, unstuck
```

---

## See Also

- **Commands**:
  - `/architect` - Deep architectural analysis (complements architecture decisions)
  - `/what-if` - Compare alternatives (provides trade-off analysis)
  - `/reflect` - Understand why stuck (metacognitive awareness)
  - `/summary` - Summarize what happened (backward-looking, not decision-focused)

- **Skills**:
  - [research](../skills/research/) - Systematic investigation
  - [deployment](../skills/deployment/) - Deployment decisions

- **Principles**:
  - All 20 principles relevant (decision should follow principles)

---

## Prompt Template

You are executing the `/problem-statement` command.

---

### Execution Steps

**Phase 1: Identify Current Decision Point**

Scan last 5-10 messages for:
- Direct questions to user
- Blocked progress statements
- Option presentations
- Approval requests

Extract:
- Question asked
- Options presented
- Why blocked
- When asked

**Phase 2: Trace Problem Origin**

Search conversation history backward:
1. Find initial problem/request
2. Identify key milestones
3. Build timeline (Message N: event)
4. Create narrative of evolution

**Phase 3: Gather Relevant Context**

Collect from conversation:
1. Technical constraints (budget, time, infrastructure, expertise, stack)
2. Requirements (performance, scalability, reliability, compliance)
3. Trade-offs discussed (what's being balanced)
4. Previous decisions (what was already decided, why)
5. Additional context (standard trade-offs for this decision type)

**Phase 4: Restate Problem Clearly**

Explain in 2-3 paragraphs:
1. Original goal (what user wanted)
2. Current situation (where we are)
3. Specific problem (what's blocking)
4. Why decision needed (what happens if not decided)
5. Impact (how this affects project)

Add one-sentence summary: "In short: {summary}"

**Phase 5: Present Decision Framework**

For each option:
1. What it is (1-2 sentence description)
2. How it works (technical approach)
3. Pros (3-5 advantages)
4. Cons (3-5 disadvantages)
5. Best for (conditions when to choose)
6. Not good for (when NOT to choose)
7. Implementation effort (time + complexity)

Create comparison matrix:
- Criteria in rows
- Options in columns
- Winner per criterion
- Weight (importance)

Provide recommendation if clear:
- Suggested option
- Rationale (why this option)
- Trade-off accepted (what you give up)
- When to choose alternative (conditions)

Describe what happens next:
- For each option: immediate steps + short-term tasks + expected outcome
- If unsure: how to get more info, what to ask, how to test

---

### Output

Use the output format above, including all 5 phases with clear, simple language.
