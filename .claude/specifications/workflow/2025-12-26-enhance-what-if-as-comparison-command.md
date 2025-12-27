---
title: Enhance /what-if as Comprehensive Comparison Command
focus: workflow
date: 2025-12-26
status: draft
tags: [commands, thinking-architecture, comparison]
---

# Specification: Enhance /what-if as Comprehensive Comparison Command

## Goal

**Reposition `/what-if` as the primary comparison command** by adding multi-way comparison and relationship analysis capabilities, eliminating the need for a separate `/compare` command.

**Current state**: `/what-if` handles binary comparisons (current vs alternative) well but:
- Not explicitly positioned as "the comparison command"
- Lacks multi-way comparison (X vs Y vs Z)
- Missing relationship analysis (part-whole, complement, substitution, composition)

**Desired state**: `/what-if` becomes the **comprehensive comparison command** that handles:
1. Binary comparisons (existing) - "What if we used X instead of Y?"
2. Multi-way comparisons (new) - "Compare X vs Y vs Z"
3. Relationship analysis (new) - "How do X and Y relate?"

---

## Design Principles

### 1. Backward Compatibility
- All existing `/what-if` invocations continue to work
- Binary comparison patterns preserved exactly
- No breaking changes to existing workflows

### 2. Comparison as Subset
- `/compare` functionality is a **subset** of `/what-if`
- `/what-if` = scenario analysis + comparison + relationship analysis
- Users can use natural language: "compare X and Y" maps to `/what-if`

### 3. Auto-Detection of Comparison Type
```bash
# Binary comparison (existing pattern)
/what-if "Lambda timeout 15s instead of 30s"
→ Detects: scenario analysis

# Multi-way comparison (new pattern)
/what-if "compare Redis vs DynamoDB vs ElastiCache"
→ Detects: multi-way comparison

# Relationship analysis (new pattern)
/what-if "analyze relationship between caching and CDN"
→ Detects: relationship analysis
```

---

## Enhanced Capabilities

### Capability 1: Binary Comparison (Existing - Keep As-Is)

**Pattern**: "What if we used X instead of Y?"

**Example**:
```bash
/what-if "Lambda timeout 15s instead of 30s"
```

**Output** (unchanged):
```markdown
WHAT-IF ANALYSIS: Lambda timeout 15s instead of 30s

CURRENT REALITY: timeout = 30s
UNDER NEW ASSUMPTION: timeout = 15s

What Breaks: Image processing (20-25s execution)
What Improves: Faster failure detection
Insights: 30s is minimum viable, not arbitrary

RECOMMENDATION: NO (keep 30s)
```

**No changes needed** - this already works well.

---

### Capability 2: Multi-Way Comparison (NEW)

**Pattern**: "Compare X vs Y vs Z"

**Trigger keywords**:
- "compare X vs Y vs Z"
- "compare X, Y, and Z"
- "evaluate X vs Y vs Z"
- "which is better: X, Y, or Z"

**Example**:
```bash
/what-if "compare Redis vs DynamoDB vs ElastiCache for caching"
```

**Output** (new template):
```markdown
MULTI-WAY COMPARISON: Redis vs DynamoDB vs ElastiCache

COMPARISON CONTEXT
  Purpose: Caching layer for report data
  Scale: 10k requests/day
  Budget: <$50/month

---

## Option 1: Redis

**Description**: In-memory key-value store

**Strengths**:
- Extremely fast (sub-ms latency)
- Rich data structures (lists, sets, sorted sets)
- Pub/sub for real-time features

**Weaknesses**:
- Requires ElastiCache (AWS managed) or EC2 instance
- In-memory only (expensive for large datasets)
- Manual clustering for HA

**Cost**: $15-30/month (ElastiCache t3.micro)
**Complexity**: Medium (need to manage connection pooling)
**Performance**: 9/10 (sub-millisecond reads)

---

## Option 2: DynamoDB

**Description**: Serverless NoSQL database

**Strengths**:
- Serverless (no infrastructure management)
- Built-in HA across AZs
- Pay-per-request pricing (good for bursty workloads)

**Weaknesses**:
- Higher latency than Redis (single-digit ms)
- More expensive for high throughput
- Limited query patterns (primary key + sort key only)

**Cost**: $5-15/month (on-demand, 10k req/day)
**Complexity**: Low (fully managed)
**Performance**: 7/10 (5-10ms reads)

---

## Option 3: ElastiCache

**Description**: AWS managed Redis/Memcached

**Strengths**:
- Managed Redis (automatic backups, patching)
- Multi-AZ replication
- Better than self-managed Redis

**Weaknesses**:
- Same as Redis (in-memory cost)
- Still need to manage connections
- Overkill for simple caching

**Cost**: $30-50/month (managed Redis)
**Complexity**: Medium (connection management)
**Performance**: 9/10 (same as Redis)

---

## COMPARISON MATRIX

| Criterion | Redis | DynamoDB | ElastiCache |
|-----------|-------|----------|-------------|
| **Performance** | 9/10 | 7/10 | 9/10 |
| **Cost** | 7/10 | 9/10 | 6/10 |
| **Complexity** | 6/10 | 9/10 | 6/10 |
| **Scalability** | 7/10 | 10/10 | 8/10 |
| **TOTAL** | **29/40** | **35/40** | **29/40** |

---

## SIMILARITIES

All three:
- Support key-value storage
- Available in AWS ecosystem
- Sub-second read latency
- Support TTL for automatic expiration

---

## DIFFERENCES

**Architecture**:
- Redis/ElastiCache: In-memory (fast, expensive)
- DynamoDB: Disk-backed SSD (slower, cheaper)

**Management**:
- Redis: Self-managed (EC2) or managed (ElastiCache)
- DynamoDB: Fully serverless
- ElastiCache: Managed but not serverless

**Pricing model**:
- Redis: Pay for instance hours
- DynamoDB: Pay per request or provisioned capacity
- ElastiCache: Pay for instance hours + data transfer

---

## RELATIONSHIPS

**Substitution**: DynamoDB can substitute Redis for **low-latency caching** (5-10ms acceptable)

**Complement**: Redis + DynamoDB complement each other:
- Redis: Hot data cache (frequently accessed)
- DynamoDB: Persistent storage + cold cache

**Composition**: Can compose both:
```
User Request
    ↓
Check Redis (hot cache)
    ↓ miss
Check DynamoDB (cold cache)
    ↓ miss
Compute from Aurora
    ↓
Write to DynamoDB → Write to Redis
```

**Part-Whole**: ElastiCache is **not** a superset of Redis (it's managed Redis, not different technology)

---

## RECOMMENDATION: DynamoDB (Score: 35/40)

**Why**:
- Lowest total cost for our scale (10k req/day)
- Serverless (no infrastructure management)
- Good enough latency (5-10ms vs 1ms not critical for our use case)

**Trade-off**:
- Lose: 5ms latency compared to Redis
- Gain: $10-20/month cost savings, zero ops overhead

**When to choose Redis/ElastiCache instead**:
- Need sub-millisecond latency (not our requirement)
- Using Redis-specific features (pub/sub, sorted sets)
- Budget allows $30-50/month for caching

---

## NEXT STEPS

```bash
# Recommended: Validate assumption
/validate "DynamoDB latency < 10ms for our access patterns"

# Then specify chosen approach
/specify "DynamoDB caching layer"

# Then plan implementation
EnterPlanMode
```
```

---

### Capability 3: Relationship Analysis (NEW)

**Pattern**: "Analyze relationship between X and Y"

**Trigger keywords**:
- "analyze relationship between X and Y"
- "how do X and Y relate"
- "relationship between X and Y"
- "how are X and Y connected"

**Example**:
```bash
/what-if "analyze relationship between caching and CDN"
```

**Output** (new template):
```markdown
RELATIONSHIP ANALYSIS: Caching and CDN

---

## Concepts Being Analyzed

### Concept 1: Caching
**Definition**: Storing computed results to avoid re-computation
**Location**: Application layer (API server, Lambda)
**Purpose**: Reduce database load, improve response time
**Examples**: Redis, DynamoDB, in-memory cache

### Concept 2: CDN (Content Delivery Network)
**Definition**: Geographic distribution of static assets
**Location**: Edge network (CloudFront)
**Purpose**: Reduce latency, decrease origin load
**Examples**: CloudFront, Cloudflare, Fastly

---

## SIMILARITY ANALYSIS

**What they share**:
- ✅ Both store copies of data to avoid re-fetching
- ✅ Both improve performance (reduce latency)
- ✅ Both reduce load on origin (database/server)
- ✅ Both use TTL for invalidation
- ✅ Both are performance optimizations, not core functionality

**Similarity score**: 7/10 (conceptually similar, different layers)

---

## DIFFERENCE ANALYSIS

**What makes them different**:

| Aspect | Caching | CDN |
|--------|---------|-----|
| **Layer** | Application (backend) | Network (edge) |
| **Data type** | Dynamic (API responses) | Static (images, JS, CSS) |
| **Invalidation** | Application-controlled | TTL or manual purge |
| **Location** | Centralized (single region) | Distributed (global PoPs) |
| **Latency benefit** | Avoids computation | Avoids network round-trip |
| **Cost model** | Storage + compute | Data transfer + requests |

**Difference score**: 6/10 (different layers, similar purpose)

---

## RELATIONSHIP TYPES

### 1. Part-Whole Relationship: NO
- CDN is NOT part of caching
- Caching is NOT part of CDN
- They are **peer concepts** at different layers

### 2. Complement Relationship: YES ✅
- **Caching and CDN complement each other**
- CDN handles static assets (images, JS, CSS)
- Caching handles dynamic API responses
- Together they form complete performance strategy

**Example**:
```
User Request for Dashboard
    ↓
CDN serves: HTML, CSS, JS, images (edge)
    ↓
API request to backend
    ↓
Cache serves: API response (backend)
```

### 3. Substitution Relationship: PARTIAL ⚠️
- **CDN can substitute caching for STATIC content only**
- CloudFront can cache API responses (acts as HTTP cache)
- But NOT a full replacement for application caching

**Example substitution**:
```
# Using CDN as API cache
GET /api/ticker/AAPL
  → CloudFront edge cache (if Cache-Control headers set)
  → Origin (if cache miss)

# Limitation: No application-level invalidation
```

### 4. Composition Relationship: YES ✅
- **Caching and CDN compose into layered architecture**

**Composition pattern**:
```
Layer 1 (Edge): CDN cache
    ↓ (if miss)
Layer 2 (Application): Application cache (Redis/DynamoDB)
    ↓ (if miss)
Layer 3 (Database): Aurora query
```

**Benefits of composition**:
- Multi-tier caching reduces origin load
- Each layer optimizes for different data type
- Failures gracefully degrade (CDN miss → app cache)

---

## INTERACTION PATTERNS

### Pattern 1: Independent Usage
```
CDN for static assets
  +
Caching for API responses
  =
Two separate optimizations
```

### Pattern 2: Overlapping Usage (CloudFront + Cache-Control)
```
CloudFront caches API responses (via Cache-Control headers)
  +
Application cache (Redis) for computed data
  =
Dual-layer caching
```

### Pattern 3: Conflict (Cache Invalidation)
```
Application cache invalidated (Redis FLUSHDB)
  BUT
CDN cache still holds stale data (TTL not expired)
  =
Inconsistency (users see old data via CDN)

FIX: Coordinate invalidation
```

---

## PROS & CONS OF USING BOTH

### Pros of Combined Usage
- ✅ **Comprehensive coverage**: Static (CDN) + Dynamic (cache)
- ✅ **Layered redundancy**: CDN cache → App cache → DB
- ✅ **Geographic distribution**: CDN edges worldwide
- ✅ **Reduced origin load**: 80%+ requests served from cache layers

### Cons of Combined Usage
- ❌ **Complexity**: Two invalidation strategies to manage
- ❌ **Cost**: Paying for both CDN and cache infrastructure
- ❌ **Debugging difficulty**: Hard to trace which layer served data
- ❌ **Consistency challenges**: Multiple caches can diverge

---

## RISK ANALYSIS

### Risk 1: Cache Inconsistency
**Description**: CDN and application cache hold different versions
**Likelihood**: Medium (if invalidation not coordinated)
**Mitigation**: Use same TTL, coordinate purges, version API responses

### Risk 2: Over-Caching
**Description**: Data cached at too many layers (staleness)
**Likelihood**: High (without clear caching policy)
**Mitigation**: Document what gets cached where, set conservative TTLs

### Risk 3: Cost Explosion
**Description**: Paying for CDN + Redis/DynamoDB
**Likelihood**: Low (both are pay-as-you-go)
**Mitigation**: Monitor costs, use free tiers

---

## RECOMMENDATION

**Use both (complement pattern)**:
- CDN for static assets (images, JS, CSS, HTML)
- Application cache for API responses (computed data)

**Avoid**:
- Using CDN to cache API responses (hard to invalidate)
- Using application cache for static assets (inefficient)

**Best practice**:
```
Static assets → CDN (CloudFront)
API responses → Application cache (DynamoDB)
Database queries → No CDN involvement
```

---

## NEXT STEPS

```bash
# Document this pattern
/journal architecture "CDN + Caching layered strategy"

# Specify implementation
/specify "Multi-tier caching: CloudFront + DynamoDB"

# Validate assumptions
/validate "CloudFront + DynamoDB reduces origin load by 80%"
```
```

---

## Implementation Plan

### Phase 1: Add Auto-Detection Logic (Parsing)

**Update `/what-if` command parser**:

```python
def detect_comparison_type(input_text: str) -> str:
    """
    Detect what type of comparison the user wants.

    Returns:
        - "binary": Current vs alternative scenario
        - "multi-way": Compare 3+ options
        - "relationship": Analyze how concepts relate
    """
    input_lower = input_text.lower()

    # Multi-way comparison detection
    if any(keyword in input_lower for keyword in [
        "compare ", "vs ", " vs. ",
        "which is better", "evaluate options"
    ]):
        # Count how many items being compared
        vs_count = input_lower.count(" vs ") + input_lower.count(" vs. ")
        comma_count = input_lower.count(",")
        or_count = input_lower.count(" or ")

        if vs_count >= 2 or comma_count >= 2 or or_count >= 2:
            return "multi-way"  # 3+ options
        elif vs_count >= 1:
            # Check if it's "X vs Y" (binary comparison shorthand)
            # vs "instead of" (scenario analysis)
            if "instead of" in input_lower:
                return "binary"
            else:
                return "multi-way"  # Explicit comparison request

    # Relationship analysis detection
    if any(keyword in input_lower for keyword in [
        "relationship between",
        "how do ", " and ", " relate",
        "how are ", " connected",
        "analyze relationship"
    ]):
        return "relationship"

    # Default: binary scenario analysis (existing behavior)
    return "binary"
```

**Examples**:
```python
detect_comparison_type("Lambda timeout 15s instead of 30s")
→ "binary"

detect_comparison_type("compare Redis vs DynamoDB vs ElastiCache")
→ "multi-way"

detect_comparison_type("analyze relationship between caching and CDN")
→ "relationship"

detect_comparison_type("Redis vs DynamoDB")
→ "multi-way" (explicit comparison, even though only 2 options)
```

---

### Phase 2: Create Templates

**File structure**:
```
.claude/commands/what-if.md
  ├── Section: Binary Comparison (existing)
  ├── Section: Multi-Way Comparison (new)
  └── Section: Relationship Analysis (new)
```

**Template organization**:

```markdown
# /what-if Command

## Purpose
Explore counterfactual scenarios, compare alternatives, and analyze relationships.

---

## Usage Patterns

### Pattern 1: Binary Comparison (Scenario Analysis)
/what-if "Lambda timeout 15s instead of 30s"
→ Current vs alternative scenario with cascading effects

### Pattern 2: Multi-Way Comparison
/what-if "compare Redis vs DynamoDB vs ElastiCache"
→ Compare 3+ options with evaluation matrix

### Pattern 3: Relationship Analysis
/what-if "analyze relationship between caching and CDN"
→ Similarity, differences, relationships (part-whole, complement, etc.)

---

## Templates

[Include full templates from examples above]
```

---

### Phase 3: Update Thinking Process Architecture

**File**: `.claude/diagrams/thinking-process-architecture.md`

**Update line 276**:
```markdown
OLD:
EVAL: Multiple good options?
   YES → /what-if (Compare scenarios)

NEW:
EVAL: Multiple good options?
   YES → /what-if (Compare alternatives)
      - Binary: "X instead of Y" → Scenario analysis
      - Multi-way: "Compare X vs Y vs Z" → Evaluation matrix
      - Relationship: "How do X and Y relate?" → Relationship analysis
```

---

### Phase 4: Update Command Documentation

**Files to update**:

1. **`.claude/commands/what-if.md`**:
   - Add multi-way comparison section
   - Add relationship analysis section
   - Update examples
   - Add "when to use which pattern" decision tree

2. **`.claude/commands/explore.md`** (line 414):
   - Update reference to `/what-if`
   - Clarify: use `/what-if` for deep-dive comparison of top 2-3 candidates

3. **`.claude/commands/README.md`**:
   - Update `/what-if` description to mention comparison capabilities

---

### Phase 5: Create Examples in Codebase

**Add real examples**:

```
.claude/what-if/
├── 2025-12-26-multi-way-comparison-redis-vs-dynamodb-vs-elasticache.md
└── 2025-12-26-relationship-analysis-caching-vs-cdn.md
```

These serve as:
- Reference examples for users
- Test cases for the template
- Documentation of comparison patterns

---

## Open Questions

- [ ] Should multi-way comparison support more than 5 options? (might be unwieldy)
- [ ] Should relationship analysis automatically generate diagrams (Mermaid)?
- [ ] Should we add "compatibility analysis" as 4th pattern? (Can X work with Y?)
- [ ] Should comparison matrix support custom criteria (not just perf/cost/complexity)?

---

## Success Criteria

**This enhancement succeeds if**:

✅ Users naturally use `/what-if` for comparisons (don't ask for `/compare`)
✅ Multi-way comparison produces useful evaluation matrices
✅ Relationship analysis reveals non-obvious connections
✅ No breaking changes to existing `/what-if` invocations
✅ Thinking process architecture flows naturally (explore → what-if → specify)

---

## Next Steps

- [ ] Review this specification
- [ ] Get feedback on templates (are they useful?)
- [ ] If approved, create implementation plan
- [ ] Update `.claude/commands/what-if.md` with new templates
- [ ] Update thinking process architecture diagram
- [ ] Create example what-if documents
- [ ] Test with real comparison scenarios
- [ ] Document in `.claude/commands/README.md`

---

## References

**Current `/what-if` implementation**:
- `.claude/commands/what-if.md` - Existing command documentation

**Thinking process architecture**:
- `.claude/diagrams/thinking-process-architecture.md` - Shows `/what-if` as comparison command (line 276)

**Comparison discussion**:
- User feedback: "/what-if is a subset of /compare" → Agreed, enhance /what-if instead
- Alternative: Creating separate `/compare` command → Rejected (creates overlap)
