# Performance Metrics Glossary

## Core Web Vitals (User-Centric)

### LCP - Largest Contentful Paint
**What**: Time until largest visible element renders
**Good**: <2.5s | **Needs Work**: 2.5-4s | **Poor**: >4s

**In our app**: Time until MarketsGrid fully renders with cards

**Affected by**:
- Bundle size (JS parsing)
- API response time (rankings fetch)
- Image loading (market card images)
- React hydration time

---

### FID - First Input Delay (Legacy)
**What**: Time from first interaction to browser response
**Good**: <100ms | **Needs Work**: 100-300ms | **Poor**: >300ms

**Replaced by**: INP (Interaction to Next Paint)

---

### INP - Interaction to Next Paint
**What**: Latency of ALL interactions (not just first)
**Good**: <200ms | **Needs Work**: 200-500ms | **Poor**: >500ms

**In our app**: Time from card click to modal content visible

**Affected by**:
- Event handler execution time
- State updates (Zustand)
- API fetch latency
- React re-render time
- Chart computation (Recharts)

---

### CLS - Cumulative Layout Shift
**What**: Visual stability (elements jumping around)
**Good**: <0.1 | **Needs Work**: 0.1-0.25 | **Poor**: >0.25

**In our app**: Layout shifts when:
- Cards load after skeleton
- Images load without dimensions
- Modal opens/closes
- Chart renders

---

## Loading Performance Metrics

### TTFB - Time to First Byte
**What**: Server response time (request sent → first byte received)

**In our architecture**:
```
Browser → CloudFront (edge) → API Gateway → Lambda → Aurora → Response
         └─ ~50-100ms ──────┘ └─ ~10-30ms ─┘ └─ ~1-2s cold / ~50ms warm ─┘
```

**Target**: <600ms (Google recommendation)

---

### FCP - First Contentful Paint
**What**: First DOM content visible (text, image, canvas)

**In our app**: React app shell renders (header, loading skeleton)

**Affected by**:
- Bundle download time
- HTML parsing
- CSS parsing
- React initialization

---

### TTI - Time to Interactive
**What**: Page fully usable (responds to input within 50ms)

**In our app**: Cards clickable, search works, filters respond

**Affected by**:
- JavaScript execution
- Main thread blocking
- Third-party scripts
- Event handlers registered

---

### TBT - Total Blocking Time
**What**: Sum of all long tasks (>50ms) blocking main thread

**In our app**: Long tasks from:
- React initial render
- Chart data processing
- Large array operations
- JSON parsing

**Target**: <200ms

---

## Network Metrics

### DNS Lookup
**What**: Domain name → IP address resolution
**Typical**: 20-120ms (cached: ~0ms)

**Our setup**: CloudFront uses AWS DNS, often cached

---

### TCP Connection
**What**: Three-way handshake time
**Typical**: 50-200ms

**Our setup**: HTTPS via CloudFront, connection reuse enabled

---

### TLS Negotiation
**What**: SSL/TLS handshake
**Typical**: 50-150ms (TLS 1.3 faster)

**Our setup**: CloudFront manages certificates, uses TLS 1.3

---

### Content Download
**What**: Time to download response body
**Depends on**: Response size, connection speed, compression

**Our setup**:
- CloudFront compression: Enabled (gzip/brotli)
- API responses: JSON (typically 5-50KB)
- Static assets: Cached at edge (24hr TTL)

---

## Backend Metrics

### Lambda Cold Start
**What**: First invocation after container spin-down
**Typical**: 1-3s depending on runtime, memory, dependencies

**Our config** (`terraform/telegram_api.tf`):
- Memory: 512-1024 MB
- Timeout: 120s
- Runtime: Python 3.11 (custom image)

**Factors affecting cold start**:
- Memory allocation (more = faster init)
- Package size (fewer imports = faster)
- VPC attachment (adds ~500ms)
- Database connections (RDS Proxy helps)

---

### Lambda Warm Latency
**What**: Execution time when container already running
**Typical**: 50-500ms for our functions

**Breakdown**:
- Handler invocation: ~10ms
- Aurora query: ~50-200ms
- Pydantic serialization: ~10-50ms
- Response formatting: ~5-10ms

---

### Aurora Query Time
**What**: Database query execution

**Factors**:
- Query complexity
- Data volume
- Index usage
- ACU scaling state (cold Aurora adds latency)

**Our config** (`terraform/aurora.tf`):
- Min ACU: 0.5
- Max ACU: 2
- Auto-pause: Disabled (prevents cold start)

---

### Connection Pool Efficiency
**What**: Reuse of database connections

**Our pattern** (`src/data/aurora/client.py`):
- Singleton connection per Lambda container
- Health check before reuse: `ping(reconnect=True)`
- No explicit connection pooling library

---

## Cache Metrics

### Cache Hit Ratio
**What**: % of requests served from cache

**CloudFront cache** (`terraform/frontend.tf`):
- HTML: 5 minute TTL
- JS/CSS: 24 hour TTL (versioned filenames)
- API responses: Not cached (dynamic)

**Target**: >80% for static assets

---

### Stale-While-Revalidate
**What**: Serve stale content while fetching fresh

**Our status**: Not implemented (opportunity!)

**How it works**:
```
Request → Is cached?
          ├─ YES, fresh → Serve immediately
          ├─ YES, stale → Serve immediately + fetch in background
          └─ NO → Fetch, cache, serve
```

---

## Rendering Metrics

### React Render Time
**What**: Component tree reconciliation + DOM update

**Expensive operations in our app**:
- `MarketsGrid` with many cards
- `FullChart` with price history
- `ScoreTable` with many rows

**Optimization**: `useMemo`, `React.memo`, virtualization

---

### Paint Time
**What**: Browser painting pixels to screen

**Affected by**:
- DOM complexity
- CSS complexity (shadows, gradients)
- Layer composition
- Hardware acceleration

---

### Layout Time
**What**: Browser calculating element positions

**Causes of layout thrashing**:
- Reading layout properties (offsetHeight) after writes
- Animations affecting layout properties
- Dynamic content insertion

---

## Measurement Tools

| Tool | Metrics Available | How to Access |
|------|-------------------|---------------|
| **Chrome DevTools** | All client metrics | F12 → Performance/Network |
| **Lighthouse** | Web Vitals, audits | F12 → Lighthouse |
| **web-vitals library** | LCP, FID, CLS, INP, TTFB | `npm install web-vitals` |
| **CloudWatch** | Lambda duration, errors | AWS Console |
| **X-Ray** | Distributed tracing | Enable in Lambda config |
| **CloudFront Reports** | Cache hit ratio, latency | CloudFront → Reports |
