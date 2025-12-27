---
date: 2025-12-26
type: multi-way-comparison
status: example
tags: [caching, redis, dynamodb, elasticache, infrastructure]
---

# Multi-Way Comparison: Redis vs DynamoDB vs ElastiCache for Caching

**Example demonstrating the multi-way comparison pattern for `/what-if` command**

---

## COMPARISON CONTEXT

**Purpose**: Caching layer for report data
**Scale**: 10k requests/day
**Budget**: <$50/month
**Current state**: No caching (direct Aurora queries)

---

## Option 1: Redis (Self-Managed)

**Description**: In-memory key-value store running on EC2 instance

**Strengths**:
- Extremely fast (sub-ms latency)
- Rich data structures (lists, sets, sorted sets, hashes)
- Pub/sub for real-time features
- Atomic operations (INCR, ZADD with score updates)
- Lua scripting for complex operations

**Weaknesses**:
- Requires EC2 instance management (or use ElastiCache)
- In-memory only (expensive for large datasets)
- Manual clustering for HA
- Persistence configuration required (RDB/AOF)
- Single point of failure (unless clustered)

**Cost**: $15-30/month (t3.micro EC2 + EBS for persistence)
**Complexity**: Medium-High (need to manage instance, monitoring, backups)
**Performance**: 9/10 (sub-millisecond reads, <1ms p50)

---

## Option 2: DynamoDB

**Description**: Serverless NoSQL database with on-demand pricing

**Strengths**:
- Serverless (no infrastructure management)
- Built-in HA across 3 AZs
- Pay-per-request pricing (good for bursty workloads)
- Auto-scaling capacity
- Point-in-time recovery
- Global tables for multi-region

**Weaknesses**:
- Higher latency than Redis (single-digit ms vs sub-ms)
- More expensive for high throughput
- Limited query patterns (primary key + sort key only)
- 400KB item size limit
- No complex data structures

**Cost**: $5-15/month (on-demand, 10k req/day = ~300k reads/month)
**Complexity**: Low (fully managed, no infrastructure)
**Performance**: 7/10 (5-10ms reads, 10-15ms p95)

---

## Option 3: ElastiCache (Managed Redis)

**Description**: AWS managed Redis service

**Strengths**:
- Managed Redis (automatic backups, patching)
- Multi-AZ replication
- Better than self-managed Redis (less ops overhead)
- Same performance as Redis
- Automatic failover

**Weaknesses**:
- Same as Redis (in-memory cost, limited by RAM)
- Still need to manage connections (pooling)
- Overkill for simple caching
- More expensive than self-managed
- Network-based (not local like in-memory)

**Cost**: $30-50/month (cache.t3.micro with multi-AZ)
**Complexity**: Medium (connection management, cache invalidation)
**Performance**: 9/10 (same as Redis, sub-ms latency)

---

## COMPARISON MATRIX

| Criterion | Redis (EC2) | DynamoDB | ElastiCache |
|-----------|-------------|----------|-------------|
| **Performance** | 9/10 (sub-ms) | 7/10 (5-10ms) | 9/10 (sub-ms) |
| **Cost** | 7/10 ($15-30) | 9/10 ($5-15) | 6/10 ($30-50) |
| **Complexity** | 6/10 (manage EC2) | 9/10 (serverless) | 7/10 (less ops than EC2) |
| **Scalability** | 7/10 (manual clustering) | 10/10 (auto-scale) | 8/10 (managed scaling) |
| **TOTAL** | **29/40** | **35/40** ✅ | **30/40** |

---

## SIMILARITIES

**What all three share**:
- Support key-value storage
- Available in AWS ecosystem
- Sub-second read latency
- Support TTL for automatic expiration
- Can cache JSON data
- Suitable for our scale (10k req/day)

---

## DIFFERENCES

**Architecture**:
- Redis/ElastiCache: In-memory (fast, expensive per GB)
- DynamoDB: Disk-backed SSD (slower, cheaper per GB)

**Management**:
- Redis: Self-managed (EC2 instance, backups, monitoring)
- DynamoDB: Fully serverless (zero ops overhead)
- ElastiCache: Managed but not serverless (still need connection pooling)

**Pricing model**:
- Redis: Pay for instance hours (fixed cost)
- DynamoDB: Pay per request or provisioned capacity (variable cost)
- ElastiCache: Pay for instance hours + data transfer (fixed + variable)

**Data structures**:
- Redis/ElastiCache: Rich (lists, sets, sorted sets, hashes)
- DynamoDB: Simple (attribute-value pairs, no complex structures)

**Latency**:
- Redis/ElastiCache: Sub-millisecond (0.1-1ms)
- DynamoDB: Single-digit milliseconds (5-10ms)

---

## RELATIONSHIPS

### Substitution: Partial ⚠️

**DynamoDB can substitute Redis for simple key-value caching** (5-10ms acceptable):
- ✅ Can replace: Simple cache lookups (ticker data, report JSON)
- ❌ Cannot replace: Real-time features needing sub-ms latency
- ❌ Cannot replace: Complex data structures (sorted sets for leaderboards)

**ElastiCache is NOT a substitution** - it's managed Redis (same technology, different deployment)

### Complement: YES ✅

**Redis + DynamoDB complement each other** (multi-tier caching):
- Redis: Hot data cache (frequently accessed, sub-ms reads)
- DynamoDB: Persistent storage + cold cache (5-10ms acceptable)

**Example complementary usage**:
```
User Request
    ↓
Check Redis (hot cache)
    ↓ miss
Check DynamoDB (cold cache)
    ↓ miss
Compute from Aurora
    ↓
Write to DynamoDB (persistence) → Write to Redis (hot cache)
```

**Benefits**:
- Most requests hit Redis (sub-ms)
- DynamoDB provides fallback (5-10ms)
- Aurora only queried on full cache miss (20-50ms)

### Composition: YES ✅

**Can compose both in layered architecture**:
```
Layer 1 (Hot): Redis cache (in-memory, sub-ms)
    ↓ (if miss)
Layer 2 (Warm): DynamoDB cache (disk-backed, 5-10ms)
    ↓ (if miss)
Layer 3 (Cold): Aurora query (database, 20-50ms)
```

**Trade-off**:
- Complexity: Need to manage 2 cache layers
- Cost: Paying for both Redis + DynamoDB
- Benefit: 95%+ requests hit hot cache (sub-ms latency)

### Part-Whole: NO

- ElastiCache is NOT a superset of Redis (it's managed Redis, not different technology)
- DynamoDB is NOT part of Redis (different technologies)
- Redis is NOT part of DynamoDB (different technologies)
- They are **peer technologies** for caching

---

## RECOMMENDATION: DynamoDB (Score: 35/40) ✅

### Why DynamoDB?

**Primary reasons**:
1. **Lowest total cost** for our scale (10k req/day = $5-15/month)
2. **Serverless** (zero ops overhead, no instance management)
3. **Good enough latency** (5-10ms vs 1ms not critical for our use case)
4. **Auto-scaling** (handles traffic spikes without manual intervention)

**Trade-offs we accept**:
- **Lose**: 5ms latency compared to Redis (5-10ms vs sub-ms)
- **Lose**: Rich data structures (can't use sorted sets, lists)
- **Gain**: $10-20/month cost savings
- **Gain**: Zero ops overhead (no EC2 management)

**When we would choose Redis/ElastiCache instead**:
- Need sub-millisecond latency (not our current requirement)
- Using Redis-specific features (pub/sub for real-time updates, sorted sets for leaderboards)
- Budget allows $30-50/month for caching infrastructure
- Already have Redis expertise in team

**When we would choose multi-tier (Redis + DynamoDB)**:
- Traffic grows to 100k+ req/day (justify Redis cost)
- Sub-ms latency becomes critical (user experience requirement)
- Budget increases to $50-100/month for infrastructure

---

## NEXT STEPS

**Recommended workflow**:

```bash
# Step 1: Validate our latency assumption
/validate "DynamoDB latency < 10ms for our access patterns"
# → Ensure 5-10ms is acceptable for report API

# Step 2: Specify DynamoDB caching implementation
/specify "DynamoDB caching layer for report data"
# → Design schema (PK: ticker, SK: report_type, TTL: 24h)

# Step 3: Plan implementation
EnterPlanMode
# → Create DynamoDB table, update API to use cache, add TTL

# Step 4: Deploy to dev and measure
# → Confirm latency, cost, and cache hit rate assumptions

# Step 5: Monitor for 1 week
# → If assumptions hold, promote to staging/prod
# → If latency too high, revisit Redis option
```

**Success criteria**:
- ✅ API latency < 15ms p95 (with DynamoDB cache)
- ✅ Cache hit rate > 80% (most requests hit cache)
- ✅ Cost < $15/month (on-demand pricing at 10k req/day)
- ✅ Zero manual ops overhead (no instance management)

---

## LESSONS LEARNED

**Why this comparison was valuable**:
1. **Avoided anchoring** - First instinct was Redis (performance), comparison revealed DynamoDB better for our constraints
2. **Cost-performance trade-off** - 5ms latency difference not worth $20/month + ops overhead
3. **Serverless alignment** - DynamoDB fits our serverless architecture (Lambda, API Gateway)
4. **Scaling path** - Can upgrade to Redis later if traffic justifies cost

**Pattern**: Always compare 3+ options with evaluation matrix - prevents anchoring on first idea
