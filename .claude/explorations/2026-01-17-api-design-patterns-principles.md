# Exploration: API Design Patterns, Principles & Best Practices

**Date**: 2026-01-17
**Goal**: Research API design (generalized + web-specialized) patterns, principles, and best practices
**Focus**: Comprehensive
**Status**: Complete

---

## Problem Decomposition

**Context**: The `/rankings` endpoint is "overloaded" - doing too much in a single request:
1. Fetching real-time prices (47 yfinance calls)
2. Querying cached analysis data (47 Aurora queries)
3. Computing rankings (in-memory sorting)
4. Formatting responses (transformation logic)

**Core Questions**:
1. What API design principles should guide endpoint structure?
2. What patterns optimize for performance, caching, and scalability?
3. What web-specific patterns apply to our Telegram Mini App architecture?
4. How should we restructure `/rankings` based on best practices?

---

## 1. Core REST API Design Principles

### 1.1 Single Responsibility Principle (SRP) for Endpoints

**Principle**: Each endpoint should have ONE specific responsibility.

> "If you need to use the word 'AND' to describe what an endpoint does, it probably violates SRP."

| Violation | Correct Separation |
|-----------|-------------------|
| `/rankings` returns prices AND charts AND scores | `/prices`, `/rankings`, `/reports/{ticker}` |
| `POST /users` creates user AND sends email | `POST /users` creates, webhook triggers email |
| `GET /dashboard` returns all data for page | Separate endpoints, frontend aggregates |

**Application to our codebase**:
```
Current:
  GET /rankings → real-time prices + cached reports + rankings computation

Better:
  GET /prices → real-time price data only (cached 1 min)
  GET /rankings → precomputed rankings (cached 5 min)
  GET /reports/{ticker} → full report data
```

### 1.2 Resource-Oriented Design

**Principle**: Model URLs as nouns (resources), not verbs (actions).

```
Good:                     Bad:
GET /users                GET /getUsers
POST /users               POST /createUser
GET /users/123            GET /getUserById?id=123
DELETE /users/123         POST /deleteUser
PATCH /users/123          POST /updateUser
```

**HTTP methods as verbs**:
| Method | Meaning | Idempotent |
|--------|---------|------------|
| GET | Read | ✅ Yes |
| POST | Create | ❌ No |
| PUT | Replace | ✅ Yes |
| PATCH | Partial update | ✅ Yes |
| DELETE | Remove | ✅ Yes |

### 1.3 Richardson Maturity Model

**Level 0**: Single URI, single verb (RPC-style)
**Level 1**: Multiple URIs for resources
**Level 2**: HTTP verbs used properly
**Level 3**: HATEOAS (hypermedia controls)

Most production APIs target Level 2. Level 3 (HATEOAS) adds discoverability but increases complexity.

---

## 2. API Architecture Patterns

### 2.1 API Gateway Pattern

**Problem**: Multiple microservices require unified entry point.

**Solution**: Single gateway handles:
- Request routing
- Authentication/authorization
- Rate limiting
- Load balancing
- Request/response transformation
- Caching
- Monitoring

```
Client → API Gateway → Service A
                    → Service B
                    → Service C
```

**Our architecture**:
```
Telegram Mini App → API Gateway → Lambda (FastAPI)
                               → Aurora
                               → DynamoDB
```

### 2.2 Backend for Frontend (BFF) Pattern

**Problem**: Different clients (web, mobile, 3rd party) need different data shapes.

**Solution**: Dedicated backend per frontend type.

```
Web App    → BFF-Web    → Microservices
Mobile App → BFF-Mobile → Microservices
3rd Party  → BFF-API    → Microservices
```

**Benefits**:
- Frontend-optimized responses (no over/under-fetching)
- Frontend team owns their BFF
- Different caching strategies per client
- Tailored security per client type

**When to use**:
- Multiple client types with different needs
- Frontend teams want autonomy
- Different performance requirements per client

**Our application**: Telegram Mini App is our single frontend, but we could benefit from BFF thinking:
- Aggregate data on server side (reduce client-side API calls)
- Pre-format data for UI consumption
- Handle authentication complexity server-side

### 2.3 CQRS (Command Query Responsibility Segregation)

**Problem**: Read and write operations have different requirements.

**Solution**: Separate read models from write models.

```
Commands (writes):          Queries (reads):
POST /orders                GET /orders
  → Validate                  → Query optimized view
  → Apply business rules      → No validation needed
  → Write to event store      → Can use replica/cache
  → Trigger projections
```

**Application to rankings**:
- Write path: Precompute workflow writes to `precomputed_reports`
- Read path: `/rankings` reads from cached/aggregated view

### 2.4 Event Sourcing

**Problem**: Need audit trail and temporal queries.

**Solution**: Store state changes as events.

```
Events:
  OrderCreated { id: 1, items: [...], total: 100 }
  OrderShipped { id: 1, tracking: "ABC123" }
  OrderDelivered { id: 1, signature: "..." }

Current State:
  { id: 1, status: "delivered", ... }
```

Not directly applicable to our current needs, but useful for audit logging.

---

## 3. Caching Patterns

### 3.1 Cache Hierarchy

**Principle**: Cache as close to the user as possible.

```
┌─────────────────────────────────────────────────────────┐
│                     CLIENT                              │
│  Browser Cache → Service Worker → IndexedDB             │
├─────────────────────────────────────────────────────────┤
│                      CDN                                │
│  CloudFront Edge → Regional Edge Cache                  │
├─────────────────────────────────────────────────────────┤
│                    GATEWAY                              │
│  API Gateway Cache (300s TTL)                           │
├─────────────────────────────────────────────────────────┤
│                  APPLICATION                            │
│  In-Memory Cache (Lambda) → Redis/ElastiCache           │
├─────────────────────────────────────────────────────────┤
│                   DATABASE                              │
│  Query Cache → Buffer Pool → Disk                       │
└─────────────────────────────────────────────────────────┘
```

### 3.2 Static API Pattern

**Problem**: Dynamic API calls are expensive (Lambda invocations, database queries).

**Solution**: Pre-generate API responses as static files.

```
Scheduler (every 5 min)
    │
    ▼
Generate JSON files
    │
    ▼
Upload to S3
    │
    ▼
CloudFront serves static JSON
```

**Benefits**:
- Zero Lambda invocations for reads
- Sub-10ms latency (edge cached)
- 99.99% availability (S3 + CloudFront)
- Cost: ~$0.01 per 10,000 requests

**When to use**:
- Data changes infrequently (> 1 min intervals)
- High read volume
- Latency-sensitive endpoints

**Application to `/rankings`**:
```
Current:
  GET /rankings → Lambda → yfinance + Aurora

Static API:
  Scheduler → Generate rankings.json → S3 → CloudFront
  GET /rankings → CloudFront serves static JSON
```

### 3.3 Lambda@Edge Pattern

**Problem**: Need dynamic logic at edge, but want caching benefits.

**Solution**: Lambda@Edge for request/response modification.

```
CloudFront → Lambda@Edge (viewer request) → Origin
          ← Lambda@Edge (viewer response) ←
```

**Use cases**:
- A/B testing
- URL rewriting
- Header manipulation
- Authentication
- Response customization

### 3.4 Cache Invalidation Strategies

| Strategy | Description | When to Use |
|----------|-------------|-------------|
| **TTL-based** | Expires after time | Predictable staleness acceptable |
| **Event-driven** | Invalidate on write | Strong consistency needed |
| **Version-based** | New URL per version | Immutable content |
| **Stale-while-revalidate** | Serve stale, refresh async | High availability priority |

---

## 4. Pagination Patterns

### 4.1 Offset Pagination

```
GET /items?limit=10&offset=20
```

**Pros**: Simple, allows random page access
**Cons**: Performance degrades at high offsets, inconsistent with concurrent writes

**Use when**: Small datasets (<10K records), admin dashboards

### 4.2 Cursor Pagination

```
GET /items?limit=10&after=cursor_abc123
```

**Pros**: Consistent performance, handles concurrent writes
**Cons**: No random page access, cursor management complexity

**Use when**: Large datasets, infinite scroll, real-time data

### 4.3 Keyset Pagination

```
GET /items?limit=10&created_after=2026-01-17T00:00:00Z&id_after=12345
```

**Pros**: Most performant, uses indexes directly
**Cons**: Requires stable sort columns, complex implementation

**Use when**: Maximum performance needed, sorted by indexed columns

---

## 5. Error Handling Patterns

### 5.1 HTTP Status Codes

| Code | Meaning | When to Use |
|------|---------|-------------|
| 200 | OK | Successful GET/PUT/PATCH |
| 201 | Created | Successful POST |
| 204 | No Content | Successful DELETE |
| 400 | Bad Request | Malformed syntax |
| 401 | Unauthorized | Missing/invalid auth |
| 403 | Forbidden | Valid auth, insufficient permissions |
| 404 | Not Found | Resource doesn't exist |
| 409 | Conflict | State conflict (duplicate, version mismatch) |
| 422 | Unprocessable | Valid syntax, invalid semantics |
| 429 | Too Many Requests | Rate limited |
| 500 | Internal Error | Unexpected server error |
| 502 | Bad Gateway | Upstream service error |
| 503 | Service Unavailable | Temporary outage |
| 504 | Gateway Timeout | Upstream timeout |

### 5.2 Error Response Format (RFC 9457)

```json
{
  "type": "https://api.example.com/errors/ticker-not-found",
  "title": "Ticker Not Found",
  "status": 404,
  "detail": "Ticker 'NVDA' is not in the supported ticker list",
  "instance": "/api/v1/report/NVDA",
  "ticker": "NVDA",
  "supported_count": 47
}
```

**Key fields**:
- `type`: URI identifying error type (machine-readable)
- `title`: Short summary (human-readable)
- `status`: HTTP status code
- `detail`: Specific explanation
- `instance`: URI of failing request

### 5.3 Error Categories

| Category | HTTP Code | Retry? | Example |
|----------|-----------|--------|---------|
| Client error | 4xx | ❌ No | Invalid input |
| Server error (transient) | 503, 504 | ✅ Yes (backoff) | Overload |
| Server error (permanent) | 500 | ❌ No | Bug |
| Upstream error | 502 | ✅ Yes (backoff) | Third-party down |

---

## 6. Versioning Strategies

### 6.1 URL Path Versioning (Recommended)

```
GET /api/v1/users
GET /api/v2/users
```

**Pros**: Explicit, easy to route, cache-friendly
**Cons**: URL pollution

### 6.2 Header Versioning

```
GET /api/users
Accept-Version: v2
```

**Pros**: Clean URLs
**Cons**: Hidden, harder to debug, cache complications

### 6.3 Query Parameter Versioning

```
GET /api/users?version=2
```

**Pros**: Explicit, easy default
**Cons**: Less RESTful, analytics complexity

### 6.4 Content Negotiation

```
Accept: application/vnd.myapi.v2+json
```

**Pros**: True REST, per-resource versioning
**Cons**: Complex, rarely used

**Recommendation**: URL path versioning (`/api/v1/`) for simplicity and industry standard compliance.

---

## 7. Performance Optimization Patterns

### 7.1 Response Optimization

| Technique | Latency Reduction | Implementation |
|-----------|------------------|----------------|
| GZIP/Brotli compression | 60-80% size | Enable in CloudFront/API Gateway |
| Field filtering | 20-50% size | `?fields=id,name,price` |
| Sparse fieldsets | 30-60% size | JSON:API style `?fields[user]=name` |
| Connection keep-alive | 50-100ms RTT | HTTP/1.1+ default |
| HTTP/2 | 20-40% latency | Multiplexing, header compression |

### 7.2 Database Query Optimization

| Issue | Solution | Impact |
|-------|----------|--------|
| N+1 queries | Eager loading, batching | 10-100x faster |
| Missing indexes | Add indexes on filter/sort columns | 10-1000x faster |
| Large offsets | Switch to cursor pagination | 10-100x faster |
| Connection overhead | Connection pooling (RDS Proxy) | 5-10x faster |

### 7.3 Async Processing Pattern

**Problem**: Long-running operations block response.

**Solution**: Submit job, poll for status.

```
POST /jobs/report/NVDA → { job_id: "abc123", status: "pending" }
GET /jobs/abc123 → { status: "in_progress", progress: 50 }
GET /jobs/abc123 → { status: "completed", result_url: "/reports/abc123" }
```

**Already implemented**: Our async report generation uses this pattern.

### 7.4 Precomputation Pattern

**Problem**: Complex calculations slow down reads.

**Solution**: Compute ahead of time, serve from cache.

```
Write path (async):
  Scheduler → Compute rankings → Write to cache

Read path (sync):
  GET /rankings → Read from cache → Return
```

**Already implemented**: `precompute_workflow` generates reports ahead of time.

---

## 8. GraphQL vs REST Decision Matrix

| Factor | REST | GraphQL |
|--------|------|---------|
| Caching | ✅ HTTP caching native | ❌ Requires custom caching |
| Bandwidth | ❌ Over/under-fetching | ✅ Request exactly what you need |
| Learning curve | ✅ Simple | ⚠️ Moderate |
| Tooling | ✅ Mature | ✅ Good |
| Multiple clients | ⚠️ BFF pattern needed | ✅ Clients define queries |
| Performance at scale | ✅ Distributes load | ⚠️ Single endpoint bottleneck |
| Real-time | ⚠️ Requires WebSocket | ✅ Subscriptions built-in |

**Recommendation for our project**: Stay with REST.
- Single client (Telegram Mini App)
- Heavy use of CDN caching
- Simpler operational model
- Already invested in REST infrastructure

---

## 9. Web Application Specialized Patterns

### 9.1 Response Shaping for SPAs

**Pattern**: Return data in UI-ready format.

```json
// Bad: Requires frontend transformation
{
  "user": { "id": 1, "first_name": "John", "last_name": "Doe" },
  "orders": [{ "id": 101, "total_cents": 5000 }]
}

// Good: Ready for UI consumption
{
  "displayName": "John Doe",
  "orderSummary": {
    "count": 1,
    "totalFormatted": "$50.00"
  }
}
```

### 9.2 Optimistic Updates

**Pattern**: Return created/updated resource immediately.

```
POST /orders
Request:  { "items": [...] }
Response: { "id": 123, "status": "pending", ... }  // Full resource
```

### 9.3 Bulk Operations

**Pattern**: Single endpoint for batch operations.

```
POST /users/bulk
{
  "operations": [
    { "method": "create", "data": { "name": "Alice" } },
    { "method": "update", "id": 1, "data": { "name": "Bob" } },
    { "method": "delete", "id": 2 }
  ]
}
```

### 9.4 Health Check Endpoints

**Pattern**: Structured health reporting.

```json
GET /health
{
  "status": "healthy",
  "version": "1.2.3",
  "timestamp": "2026-01-17T13:00:00Z",
  "dependencies": {
    "database": { "status": "healthy", "latency_ms": 5 },
    "cache": { "status": "healthy", "latency_ms": 1 },
    "external_api": { "status": "degraded", "latency_ms": 500 }
  }
}
```

---

## 10. Application to `/rankings` Redesign

### Current State (Problems)

```
GET /api/v1/rankings?category=top_gainers

Flow:
1. Fetch 47 tickers from yfinance (parallel) - 2-5s
2. Query 47 cached reports from Aurora (parallel) - 0.5-1s
3. Compute rankings (in-memory) - <10ms
4. Format response - <10ms

Issues:
- SRP violation (prices + reports + rankings)
- Connection exhaustion (47 parallel Aurora queries)
- Slow (blocked by yfinance)
- No CDN caching (dynamic)
```

### Proposed Redesign Options

#### Option A: Split Endpoints

```
GET /api/v1/prices                    # Real-time prices only (cached 1 min)
GET /api/v1/rankings?category=...     # Precomputed rankings (cached 5 min)
GET /api/v1/reports/{ticker}          # Full report data

Frontend aggregates as needed.
```

**Pros**: Clean separation, independent caching
**Cons**: Multiple API calls from frontend

#### Option B: Static API

```
Scheduler (every 5 min):
  1. Fetch all prices
  2. Compute all rankings
  3. Generate rankings.json
  4. Upload to S3

GET /static/rankings.json → CloudFront (cached 5 min)
```

**Pros**: Zero Lambda, sub-10ms latency, 99.99% availability
**Cons**: 5-min staleness, S3/CloudFront setup

#### Option C: Pre-Aggregated Cache Table

```
Write path (precompute workflow):
  1. Generate full reports
  2. Write to precomputed_reports
  3. Also write to rankings_cache (aggregated view)

Read path:
  GET /rankings → Single Aurora query to rankings_cache
```

**Pros**: Single query, existing infrastructure
**Cons**: Still requires Lambda + Aurora

#### Option D: Hybrid (Recommended)

```
Real-time data (prices):
  GET /api/v1/prices → yfinance + 1 min cache

Static data (rankings with reports):
  GET /static/rankings/top_gainers.json → S3 + CloudFront

Full reports:
  GET /api/v1/reports/{ticker} → Aurora precomputed_reports
```

**Pros**: Best of both worlds - real-time prices, fast cached rankings
**Cons**: Two data sources for frontend

---

## Evaluation Matrix

| Criterion | Option A | Option B | Option C | Option D |
|-----------|----------|----------|----------|----------|
| Performance | 6/10 | 10/10 | 7/10 | 9/10 |
| Cost | 6/10 | 9/10 | 7/10 | 8/10 |
| Complexity | 7/10 | 6/10 | 8/10 | 6/10 |
| Consistency | 8/10 | 6/10 | 9/10 | 7/10 |
| Maintainability | 8/10 | 7/10 | 8/10 | 7/10 |
| **Total** | **35** | **38** | **39** | **37** |

---

## Recommendations

### Immediate Actions

1. **Separate `/prices` from `/rankings`**
   - New endpoint: `GET /api/v1/prices?tickers=A,B,C`
   - Rankings endpoint no longer fetches real-time prices

2. **Pre-aggregate rankings data**
   - Modify precompute workflow to write `rankings_cache` table
   - `/rankings` reads from cache (single query)

3. **Add response caching headers**
   - `Cache-Control: public, max-age=300` for rankings
   - `Cache-Control: public, max-age=60` for prices

### Future Improvements

4. **Static API for rankings**
   - Generate `rankings/top_gainers.json` etc.
   - Serve from S3 + CloudFront

5. **Cursor pagination for large lists**
   - Replace offset-based pagination
   - Especially for historical data endpoints

---

## Resources Gathered

### Official Documentation
- [Microsoft Azure API Design Best Practices](https://learn.microsoft.com/en-us/azure/architecture/best-practices/api-design)
- [AWS Backends for Frontends Pattern](https://aws.amazon.com/blogs/mobile/backends-for-frontends-pattern/)
- [Microservice API Patterns](https://microservice-api-patterns.org/)

### Design Guides
- [REST API Design Guide - Strapi](https://strapi.io/blog/restful-api-design-guide-principles-best-practices)
- [Stack Overflow REST API Best Practices](https://stackoverflow.blog/2020/03/02/best-practices-for-rest-api-design/)
- [Postman API Design Principles](https://www.postman.com/api-platform/api-design/)

### Patterns & Architecture
- [Sam Newman - Backends For Frontends](https://samnewman.io/patterns/architectural/bff/)
- [API Gateway Pattern - microservices.io](https://microservices.io/patterns/apigateway.html)
- [BFF Patterns](https://bff-patterns.com/)

### Performance & Caching
- [Caching for Serverless Applications](https://theburningmonk.com/2019/10/all-you-need-to-know-about-caching-for-serverless-applications/)
- [Lambda@Edge Best Practices](https://aws.amazon.com/blogs/networking-and-content-delivery/lambdaedge-design-best-practices/)
- [API Latency Optimization](https://www.gravitee.io/blog/cut-api-latency-diagnose-measure-and-optimize)

### Pagination
- [API Pagination: Offset vs Cursor](https://embedded.gusto.com/blog/api-pagination/)
- [Pagination Best Practices - Speakeasy](https://www.speakeasy.com/api-design/pagination)

### Error Handling
- [REST API Error Handling - Baeldung](https://www.baeldung.com/rest-api-error-handling-best-practices)
- [RFC 9457 - Problem Details for HTTP APIs](https://www.rfc-editor.org/rfc/rfc9457.html)

### Versioning
- [API Versioning Strategies - daily.dev](https://daily.dev/blog/api-versioning-strategies-best-practices-guide)
- [API Versioning Best Practices - Ambassador](https://www.getambassador.io/blog/api-versioning-best-practices)

### GraphQL vs REST
- [GraphQL vs REST 2025 - API7.ai](https://api7.ai/blog/graphql-vs-rest-api-comparison-2025)
- [AWS GraphQL vs REST Comparison](https://aws.amazon.com/compare/the-difference-between-graphql-and-rest/)

---

## Next Steps

```bash
# Converge on specific redesign
/specify "Hybrid API redesign: Static rankings + Real-time prices"

# Or compare top options
/what-if "compare Static API vs Pre-aggregated Cache for rankings"

# Validate performance assumptions
/validate "hypothesis: Static API latency < 50ms vs current 2-5s"
```
