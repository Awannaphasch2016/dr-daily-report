# Relationship Analysis Guide

**Purpose**: Systematic approach to analyzing concept relationships using formal ontology semantics.

**Principle**: Use formal ontology relationships (OWL, RDF) for structured concept comparison. Eliminates "it depends" answers with precise analytical frameworks.

---

## The Comparison Problem

When analyzing "X vs Y" or "how do X and Y relate", vague answers happen because:

```
Developer asks: "Should I use X or Y?"

Vague answer: "It depends on your use case"
Problem: No structured way to analyze the relationship
```

**Common Issues with Unstructured Comparison:**

| Problem | Example | Impact |
|---------|---------|--------|
| **Ambiguous terminology** | "They're related" | Meaningless - everything is "related" somehow |
| **False dichotomy** | "X instead of Y" | Misses cases where both complement each other |
| **Hidden assumptions** | "X is better" | Better for what? Under which constraints? |
| **Anchoring bias** | First option considered | Prevents comprehensive analysis of alternatives |
| **Lack of framework** | "It depends" | No systematic way to evaluate trade-offs |

---

## Four Fundamental Relationship Types

### Overview: OWL Ontology Mapping

These 4 relationship types from Web Ontology Language (OWL) and RDF Schema cover 90% of practical concept comparisons:

| OWL Relationship | Software Pattern | Question | Example |
|------------------|------------------|----------|---------|
| **rdfs:subClassOf** (subsumption) | Part-Whole / Layering | "Is X part of Y or vice versa?" | Lambda is part of AWS (component hierarchy) |
| **owl:complementOf** (complement) | Complementary Patterns | "Do X and Y work together (non-overlapping)?" | CDN (static) + Cache (dynamic) = complete solution |
| **owl:equivalentClass** (equivalence) | Substitution / Alternatives | "Can X replace Y in some/all scenarios?" | Redis can substitute DynamoDB for simple caching |
| **owl:ObjectProperty** (composition) | Composition / Layering | "Can X and Y be combined/layered?" | CDN → App Cache → Database (3-tier composition) |

### Type 1: Part-Whole Relationship (rdfs:subClassOf)

**OWL Concept**: `rdfs:subClassOf` (subsumption, mereology)

**Software Pattern**: Component hierarchy, layering, abstraction levels

**Question**: "Is X part of Y, or is Y part of X, or are they peer concepts?"

**When YES**:
```
Example: Lambda Function is part of AWS
- Lambda ⊂ AWS (Lambda is a subset/component of AWS)
- Clear hierarchy: AWS (whole) → Lambda (part)
```

**When NO** (peer concepts):
```
Example: Redis and DynamoDB
- Neither is part of the other
- Both are peer technologies (different databases)
- Operate at same abstraction level
```

**Software Examples**:
- YES: Controller ⊂ MVC Framework (part-whole)
- YES: HTTP ⊂ TCP/IP Stack (layer subsumption)
- NO: React and Angular (peer frameworks)
- NO: MySQL and PostgreSQL (peer databases)

### Type 2: Complement Relationship (owl:complementOf)

**OWL Concept**: `owl:complementOf` (disjoint classes that together form complete coverage)

**Software Pattern**: Non-overlapping concerns that work together synergistically

**Question**: "Do X and Y handle different, non-overlapping concerns that work better together?"

**When YES**:
```
Example: CDN (static assets) + Application Cache (dynamic data)
- CDN handles: HTML, CSS, JS, images (static, immutable)
- Cache handles: API responses, computed data (dynamic, changing)
- Non-overlapping domains
- Together provide complete performance strategy
```

**When NO** (overlapping or conflicting):
```
Example: Redis and Memcached
- Both handle in-memory caching (overlapping domain)
- Compete for same use case (not complementary)
- Would duplicate effort if used together
```

**Software Examples**:
- YES: Frontend (UI) + Backend (API) - different concerns
- YES: Static analysis (code quality) + Runtime monitoring (production health)
- NO: Jest and Mocha (overlapping test frameworks)
- NO: Webpack and Rollup (overlapping bundlers)

### Type 3: Substitution Relationship (owl:equivalentClass)

**OWL Concept**: `owl:equivalentClass` (functional equivalence with trade-offs)

**Software Pattern**: Alternative technologies/patterns that can replace each other

**Question**: "Can X replace Y in some or all scenarios? What are the trade-offs?"

**Full Substitution** (YES):
```
Example: String concatenation with + vs .join()
- Functionally identical for simple cases
- Same input → same output
- No architectural difference
```

**Partial Substitution** (PARTIAL):
```
Example: DynamoDB can substitute Redis for simple key-value caching
✅ Can substitute:
  - Simple cache lookups (get/set by key)
  - TTL-based expiration
  - Read-heavy workloads

❌ Cannot substitute:
  - Sub-millisecond latency requirements (DynamoDB = 5-10ms, Redis < 1ms)
  - Complex data structures (sorted sets, pub/sub)
  - Atomic operations (INCR, ZADD)

Trade-off: Lose 5ms latency, gain serverless simplicity
```

**No Substitution** (NO):
```
Example: CDN cannot substitute Application Cache for user-specific data
- CDN: Public, edge-cached data (no auth)
- App Cache: Private, user-specific data (requires auth context)
- Fundamentally different use cases
```

**Software Examples**:
- YES: localStorage and sessionStorage (same API, different persistence)
- PARTIAL: REST API and GraphQL (can replace for some use cases)
- NO: SQL database and Message Queue (different purposes)

### Type 4: Composition Relationship (owl:ObjectProperty)

**OWL Concept**: `owl:ObjectProperty` (objects compose to form emergent system)

**Software Pattern**: Layered architecture, multi-tier systems

**Question**: "Can X and Y be layered/composed into a multi-tier system?"

**When YES**:
```
Example: CDN → Application Cache → Database (3-tier caching)

Layer 1 (Edge): CloudFront CDN
  - Latency: <10ms (geographic proximity)
  - Hit rate: 95%+ for static assets
    ↓ (miss or dynamic request)
Layer 2 (Application): DynamoDB cache
  - Latency: 5-10ms (single region)
  - Hit rate: 80%+ for computed data
    ↓ (miss)
Layer 3 (Source): Aurora database
  - Latency: 20-50ms (database query)
  - Hit rate: Only on full cache miss (5-20% of requests)

Benefits:
- Layered fallback (each tier provides faster access)
- 95%+ requests never reach database (cost reduction)
- Each layer handles different data types
```

**When NO** (cannot compose meaningfully):
```
Example: Two ORMs (TypeORM + Sequelize)
- No meaningful layering (both operate at same abstraction level)
- Would conflict (duplicate database access logic)
- Composition creates complexity without benefit
```

**Software Examples**:
- YES: Nginx → API Gateway → Lambda → Database (request pipeline)
- YES: Browser Cache → CDN → Origin Server (HTTP caching hierarchy)
- NO: Multiple state management libraries (Redux + MobX)
- NO: Multiple authentication systems (overlap, conflict)

---

## Step-by-Step Analysis Framework

### Phase 1: Define Concepts

```markdown
## Concepts Being Analyzed

### Concept 1: {Name A}
**Definition**: {What it is in one sentence}
**Location**: {Where it operates (layer, component, domain)}
**Purpose**: {Why it exists - problem it solves}
**Examples**: {3-5 concrete instances}

### Concept 2: {Name B}
[Same structure]
```

**Example**:
```markdown
### Concept 1: Caching
**Definition**: Storing computed results to avoid re-computation
**Location**: Application layer (API server, Lambda function)
**Purpose**: Reduce database load, improve response time, avoid expensive computation
**Examples**:
- Redis (in-memory cache)
- DynamoDB (persistent cache)
- HTTP response caching
- In-memory Python dict
```

### Phase 2: Similarity and Difference Analysis

**Similarities** (what they share):
```markdown
## SIMILARITY ANALYSIS

**What they share**:
- ✅ {Shared characteristic 1}
- ✅ {Shared characteristic 2}
- ✅ {Shared characteristic 3}

**Similarity score**: X/10 (High = 8-10, Medium = 4-7, Low = 1-3)
```

**Differences** (how they diverge):
```markdown
## DIFFERENCE ANALYSIS

**What makes them different**:

| Aspect | Concept A | Concept B |
|--------|-----------|-----------|
| **{Dimension 1}** | {A value} | {B value} |
| **{Dimension 2}** | {A value} | {B value} |
| **{Dimension 3}** | {A value} | {B value} |

**Difference score**: X/10 (High = 8-10, Medium = 4-7, Low = 1-3)
```

### Phase 3: Apply 4 Relationship Types

For each relationship type, answer:
1. **Does this relationship exist?** (YES / NO / PARTIAL)
2. **What evidence supports this?** (concrete examples)
3. **What are the implications?** (how does this affect usage)

```markdown
## RELATIONSHIP TYPES

### 1. Part-Whole Relationship: {YES | NO}
**Analysis**: {Is one part of the other, or are they peers?}
**Evidence**: {Concrete example showing hierarchy or lack thereof}

### 2. Complement Relationship: {YES | NO}
**Analysis**: {Do they handle non-overlapping concerns?}
**Evidence**: {Example showing complementary usage}

### 3. Substitution Relationship: {YES | NO | PARTIAL}
**Analysis**: {Can one replace the other? Under what conditions?}
**Trade-offs**: {What you gain vs what you lose}

### 4. Composition Relationship: {YES | NO}
**Analysis**: {Can they be layered/composed?}
**Pattern**: {Diagram showing composition structure}
```

### Phase 4: Interaction Patterns and Recommendations

```markdown
## INTERACTION PATTERNS

### Pattern 1: {Name} (e.g., Independent Usage)
{Description of how they interact or don't interact}

### Pattern 2: {Name} (e.g., Overlapping Usage)
{Scenarios where they overlap or conflict}

---

## RECOMMENDATION

**Use both** | **Use only A** | **Use only B** | **Depends on...**

**Rationale**:
{Why this recommendation based on relationship analysis}

**Avoid**:
- ❌ {Anti-pattern 1}
- ❌ {Anti-pattern 2}

**Best practice**:
{Concrete recommended usage pattern}
```

---

## Case Study 1: Caching vs CDN

### Concepts Defined

**Caching**:
- **Definition**: Storing computed results to avoid re-computation
- **Location**: Application layer (API server, Lambda function)
- **Purpose**: Reduce database load, improve response time, avoid expensive computation
- **Examples**: Redis, DynamoDB, HTTP response caching, in-memory cache

**CDN (Content Delivery Network)**:
- **Definition**: Geographic distribution of static assets via edge locations
- **Location**: Network edge (between user and origin server)
- **Purpose**: Reduce latency by serving from nearby edge, decrease origin load, improve availability
- **Examples**: CloudFront (AWS), Cloudflare, Fastly, Akamai

### Relationship Analysis

#### 1. Part-Whole: NO ❌

**Analysis**: CDN and caching are **peer concepts** operating at different layers
```
User
  ↓
CDN (Layer 7: Network edge)
  ↓
API Gateway (Layer 6: API routing)
  ↓
Cache (Layer 5: Application)
  ↓
Database (Layer 4: Persistence)
```
- CDN is NOT part of caching (different layers)
- Caching is NOT part of CDN (different mechanisms)

#### 2. Complement: YES ✅

**Analysis**: CDN and caching complement each other perfectly

**Evidence**:
```
CDN serves (edge, <10ms):
  - index.html, app.bundle.js, styles.css, logo.png (static assets)
    ↓
Browser makes API request to backend
    ↓
Cache serves (application, 5-10ms):
  - /api/ticker/AAPL response (dynamic data)
  - /api/rankings response (computed data)
  - User preferences (user-specific data)
```

**Why they complement**:
- **Non-overlapping domains**: CDN = static assets, Cache = dynamic data
- **Mutual enhancement**: Both reduce origin load (additive benefit)
- **Complementary strengths**: CDN reduces network latency, Cache reduces computation time

#### 3. Substitution: PARTIAL ⚠️

**Analysis**: CDN can substitute caching for STATIC content only

**✅ Can substitute**:
- CloudFront can cache API responses (if you set `Cache-Control` headers)
- Suitable for public, read-only API responses that don't change often
- Example: `/api/tickers/list` (changes once per day)

**❌ Cannot substitute**:
- User-specific data (cache based on auth token)
- Frequently changing data (requires immediate invalidation)
- Complex cache logic (cache dependencies, partial invalidation)
- Application-level cache operations (atomic updates, cache-aside pattern)

**Trade-off**: CDN caching is harder to invalidate programmatically (5-30s propagation delay)

#### 4. Composition: YES ✅

**Analysis**: Caching and CDN compose into 3-tier architecture

**Pattern**:
```
Layer 1 (Edge): CloudFront CDN
  - Static assets (HTML, CSS, JS, images)
  - TTL: 1 year (immutable, cache-busting via versioned filenames)
  - Latency: <10ms, Hit rate: 95%+
    ↓ (if miss or dynamic request)
Layer 2 (Application): DynamoDB cache
  - Computed data (ticker analysis, rankings)
  - User-specific data (preferences, watchlists)
  - TTL: 5 minutes - 24 hours (based on data freshness)
  - Latency: 5-10ms, Hit rate: 80%+
    ↓ (if miss)
Layer 3 (Database): Aurora query
  - Source of truth (always up-to-date)
  - Latency: 20-50ms, Hit rate: Only on full cache miss (5-20%)
```

**Benefits of composition**:
- Layered fallback (each tier provides progressively slower but more comprehensive data)
- 80-95% of requests never reach database (cost reduction)
- Performance tiers: Fast (CDN <10ms) → Medium (Cache 5-10ms) → Slow (DB 20-50ms)

**Trade-offs**:
- Complexity (managing 2+ cache layers with different TTLs)
- Cost (paying for both CDN + Cache infrastructure)
- Consistency challenges (multiple caches can diverge)

### Recommendation

**Use Both (Complement Pattern)** ✅

**Rationale**:
- CDN and cache complement each other (non-overlapping domains)
- CDN = static assets only (HTML, CSS, JS, images)
- Cache = dynamic data only (API responses, computed data)
- Clean separation of concerns

**Avoid**:
- ❌ Using CDN to cache API responses (hard to invalidate, consistency issues)
- ❌ Using application cache for static assets (inefficient, CDN is better suited)
- ❌ Caching user-specific data at CDN layer (privacy risk, no auth at edge)

**Best practice**:
```
Static assets → CDN (CloudFront)
  - TTL: 1 year (immutable, versioned URLs)
  - Invalidation: Rarely needed

API responses → Application cache (DynamoDB)
  - TTL: 5 minutes - 24 hours (based on freshness requirements)
  - Invalidation: Programmatic (on data update)
```

---

## Case Study 2: Redis vs DynamoDB vs ElastiCache (Multi-Way Comparison)

### Comparison Context

**Purpose**: Caching layer for report data
**Scale**: 10k requests/day
**Budget**: <$50/month
**Current state**: No caching (direct Aurora queries)

### Options Defined

**Option 1: Redis (Self-Managed)**
- In-memory key-value store on EC2
- Strengths: Extremely fast (sub-ms), rich data structures, Lua scripting
- Weaknesses: Requires EC2 management, in-memory only (expensive), manual clustering for HA
- Cost: $15-30/month, Complexity: Medium-High, Performance: 9/10

**Option 2: DynamoDB**
- Serverless NoSQL database with on-demand pricing
- Strengths: Serverless (no ops), built-in HA, pay-per-request, auto-scaling
- Weaknesses: Higher latency (5-10ms vs sub-ms), limited query patterns, 400KB item limit
- Cost: $5-15/month, Complexity: Low, Performance: 7/10

**Option 3: ElastiCache (Managed Redis)**
- AWS managed Redis service
- Strengths: Managed Redis (auto backups, patching), multi-AZ, automatic failover
- Weaknesses: Same as Redis (in-memory cost), more expensive than self-managed
- Cost: $30-50/month, Complexity: Medium, Performance: 9/10

### Comparison Matrix

| Criterion | Redis (EC2) | DynamoDB | ElastiCache |
|-----------|-------------|----------|-------------|
| **Performance** | 9/10 (sub-ms) | 7/10 (5-10ms) | 9/10 (sub-ms) |
| **Cost** | 7/10 ($15-30) | 9/10 ($5-15) | 6/10 ($30-50) |
| **Complexity** | 6/10 (manage EC2) | 9/10 (serverless) | 7/10 (less ops than EC2) |
| **Scalability** | 7/10 (manual clustering) | 10/10 (auto-scale) | 8/10 (managed scaling) |
| **TOTAL** | **29/40** | **35/40** ✅ | **30/40** |

### Relationship Analysis

**Substitution**: PARTIAL
- DynamoDB can substitute Redis for simple key-value caching (5-10ms acceptable)
- Cannot replace for sub-ms latency or complex data structures

**Complement**: YES
- Redis (hot cache) + DynamoDB (persistent storage) = multi-tier caching
- Most requests hit Redis (sub-ms), DynamoDB provides fallback (5-10ms)

**Composition**: YES
```
Layer 1 (Hot): Redis cache (in-memory, sub-ms)
    ↓ (if miss)
Layer 2 (Warm): DynamoDB cache (disk-backed, 5-10ms)
    ↓ (if miss)
Layer 3 (Cold): Aurora query (database, 20-50ms)
```

### Recommendation

**DynamoDB (Score: 35/40)** ✅

**Why DynamoDB**:
1. Lowest total cost for our scale ($5-15/month vs $30-50/month)
2. Serverless (zero ops overhead)
3. Good enough latency (5-10ms vs sub-ms not critical for report API)
4. Auto-scaling (handles traffic spikes without manual intervention)

**Trade-offs we accept**:
- Lose: 5ms latency compared to Redis
- Lose: Rich data structures (sorted sets, pub/sub)
- Gain: $10-20/month cost savings
- Gain: Zero ops overhead

**When we would choose Redis/ElastiCache instead**:
- Need sub-millisecond latency (real-time features)
- Using Redis-specific features (pub/sub, sorted sets for leaderboards)
- Budget allows $30-50/month for caching infrastructure
- Traffic justifies cost (100k+ req/day)

---

## Reusable Prompt Engineering Template

Use this template to apply OWL-based relationship analysis to any domain:

### Step 1: Define Your Domain

```markdown
**Domain**: {software architecture | business process | decision-making | ...}
**Concepts to analyze**: {X} and {Y}
**Goal**: {What you want to learn about their relationship}
```

### Step 2: Select OWL Relationship Types

Choose 3-5 relationship types relevant to your domain:

1. **Part-Whole** - "Is X part of Y or vice versa?"
2. **Complement** - "Do X and Y work together (non-overlapping)?"
3. **Substitution** - "Can X replace Y in some/all scenarios?"
4. **Composition** - "Can X and Y be combined/layered?"

### Step 3: Map to Domain Patterns

| OWL Type | Your Domain Equivalent | Example Question |
|----------|------------------------|------------------|
| `rdfs:subClassOf` | {Part-whole pattern in your domain} | {Domain-specific question} |
| `owl:complementOf` | {Complement pattern in your domain} | {Domain-specific question} |
| `owl:equivalentClass` | {Substitution pattern in your domain} | {Domain-specific question} |
| `owl:ObjectProperty` | {Composition pattern in your domain} | {Domain-specific question} |

### Step 4: Create Analysis Template

```markdown
## RELATIONSHIP TYPES

### 1. {Domain-specific name for Part-Whole}: {YES | NO}
**Question**: {Domain-specific question}
**Analysis**: {Evidence and reasoning}
**Example**: {Concrete instance from domain}

### 2. {Domain-specific name for Complement}: {YES | NO}
**Question**: {Domain-specific question}
**Analysis**: {Evidence and reasoning}
**Example**: {Concrete instance from domain}

[Repeat for each relationship type]
```

### Step 5: Validation Checklist

- [ ] Each relationship type has clear YES/NO/PARTIAL answer
- [ ] Analysis section includes concrete evidence (not abstract theory)
- [ ] Examples are grounded in real scenarios (not hypothetical)
- [ ] OWL concepts mapped to domain-specific terms
- [ ] Recommendation based on relationship analysis (not intuition)

---

## When to Use Relationship Analysis

### ✅ Use Relationship Analysis When:

| Scenario | Why | Example |
|----------|-----|---------|
| **Multi-way comparison** | Comparing 3+ alternatives with trade-offs | "Redis vs DynamoDB vs ElastiCache for caching" |
| **Architectural decisions** | Choosing between patterns or technologies | "Microservices vs Monolith" |
| **Technology selection** | Evaluating if X can replace Y | "Can GraphQL replace REST API?" |
| **Pattern composition** | Understanding how patterns compose | "How do CQRS and Event Sourcing relate?" |
| **Concept clarification** | Disambiguating vague "X vs Y" questions | "Caching vs CDN - when to use which?" |

### ❌ Skip Relationship Analysis When:

| Scenario | Why | Alternative |
|----------|-----|-------------|
| **Single option** | No comparison needed | Use `/specify` to design implementation |
| **Clear dichotomy** | Obviously mutually exclusive | Simple decision matrix |
| **Trivial decision** | No meaningful trade-offs | Direct implementation |
| **Debugging tasks** | Finding bugs, not comparing concepts | Use `/bug-hunt` or `/research` |

---

## References

### Formal Ontology Specifications
- [OWL 2 Web Ontology Language Primer](https://www.w3.org/TR/owl2-primer/)
- [RDF Schema 1.1](https://www.w3.org/TR/rdf-schema/)
- [Description Logic Basics](https://arxiv.org/abs/cs/0703127)

### Software Architecture
- [Martin Fowler: Software Architecture Guide](https://martinfowler.com/architecture/)
- [Microsoft Architecture Center](https://docs.microsoft.com/en-us/azure/architecture/)

### Example Analyses
- [Caching vs CDN Relationship Analysis](.claude/what-if/2025-12-26-relationship-analysis-caching-vs-cdn.md)
- [Redis vs DynamoDB vs ElastiCache Multi-Way Comparison](.claude/what-if/2025-12-26-multi-way-comparison-redis-vs-dynamodb-vs-elasticache.md)

### Related Commands
- [/what-if](.claude/commands/what-if.md) - Relationship analysis, multi-way comparison, counterfactual exploration
- [/specify](.claude/commands/specify.md) - Design alternatives explored in what-if
- [/validate](.claude/commands/validate.md) - Test assumptions from relationship analysis
