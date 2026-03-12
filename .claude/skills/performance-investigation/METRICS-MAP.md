# Metrics → Infrastructure → Code Mapping

## Frontend Metrics

### LCP (Largest Contentful Paint)

| Factor | File | Line(s) | Optimization |
|--------|------|---------|--------------|
| Bundle size | `vite.config.ts` | all | Add code splitting, tree shaking |
| Initial API call | `marketStore.ts` | 224-244 | `fetchMarkets()` optimization |
| React hydration | `main.tsx` | 6-12 | Lazy load non-critical components |
| CSS loading | `index.css` | all | Critical CSS inline |
| Image loading | `MarketCard.tsx` | 22-28 | Add `loading="lazy"` |

### INP (Interaction to Next Paint)

| Interaction | Handler Location | Optimization |
|-------------|------------------|--------------|
| Card click | `App.tsx:111-118` | Skip fetch if data exists |
| Search input | `SearchBar.tsx:24-25` | Add debounce |
| Category change | `App.tsx:99-101` | Already fast (local state) |
| Sort change | `App.tsx:103-105` | Already fast (local state) |
| Modal close | `App.tsx:120-124` | Already fast (local state) |

### CLS (Cumulative Layout Shift)

| Shift Cause | File | Fix |
|-------------|------|-----|
| Cards loading | `MarketsGrid.tsx` | Skeleton with fixed dimensions |
| Images loading | `MarketCard.tsx` | Set width/height attributes |
| Modal opening | `MarketModal.tsx` | Fixed modal dimensions |
| Chart rendering | `FullChart.tsx` | Container with fixed height |

---

## Network Metrics

### TTFB (Time to First Byte)

| Layer | Config Location | Current Value | Optimization |
|-------|-----------------|---------------|--------------|
| CloudFront | `terraform/frontend.tf:91` | TTL 1hr | Increase for static content |
| API Gateway | `terraform/api_gateway.tf:59` | 30s timeout | Expected, can't change |
| Lambda cold start | `terraform/telegram_api.tf:143` | 512-1024MB | Increase memory |
| Lambda warm | N/A | ~50-100ms | Already optimized |
| Aurora | `terraform/aurora.tf:25-31` | 0.5-2 ACU | Increase min ACU |

### Request/Response Size

| Endpoint | Response Size | Optimization |
|----------|--------------|--------------|
| `/rankings` | ~15KB (10 tickers) | Already optimized |
| `/report/{ticker}` | ~50-100KB | Add field selection |
| Static JS | ~200KB (bundled) | Code splitting |
| Static CSS | ~30KB | Already small |

---

## Backend Metrics

### Lambda Duration

| Function | File | Typical Duration | Bottleneck |
|----------|------|------------------|------------|
| telegram_api | `src/api/app.py` | 100-500ms | Aurora query |
| report_worker | `src/worker/report_worker.py` | 50-60s | LLM generation |
| ticker_fetcher | `src/scheduler/ticker_fetcher.py` | 30-60s | Yahoo Finance API |

### Aurora Query Time

| Query | Service | Typical Time | Optimization |
|-------|---------|--------------|--------------|
| Get cached report | `precompute_service.py:get_cached_report()` | 50-200ms | Add index on ticker |
| Search tickers | `ticker_service.py:search()` | 20-50ms | Already indexed |
| Get rankings | `rankings_service.py:get_rankings()` | 100-300ms | Batch queries |

---

## Infrastructure Metrics

### CloudFront Cache

| Asset Type | TTL Config | File |
|------------|-----------|------|
| HTML | 5 minutes | `terraform/frontend.tf:112` |
| JavaScript | 24 hours | `terraform/frontend.tf:133` |
| CSS | 24 hours | `terraform/frontend.tf:153` |
| Default | 1 hour | `terraform/frontend.tf:91` |

### Lambda Concurrency

| Function | Current Config | File |
|----------|----------------|------|
| telegram_api | Unreserved (default) | `terraform/telegram_api.tf` |
| report_worker | Unreserved (default) | `terraform/async_report.tf` |

**No provisioned concurrency configured** - opportunity for cold start elimination.

---

## Quick Lookup: Symptom → File

```
SLOW INITIAL LOAD
├─ Check: vite.config.ts (bundle config)
├─ Check: terraform/frontend.tf (CDN TTL)
└─ Check: marketStore.ts:224-244 (initial fetch)

SLOW MODAL OPEN
├─ Check: App.tsx:111-118 (handleSelectMarket)
├─ Check: marketStore.ts:251-340 (fetchReport)
├─ Check: src/api/app.py:224-342 (GET /report)
└─ Check: src/data/aurora/precompute_service.py (cache lookup)

SLOW CHART RENDER
├─ Check: FullChart.tsx (memoization)
├─ Check: MiniChart.tsx (data processing)
└─ Check: marketStore.ts:278-316 (data transformation)

INTERMITTENT SLOWNESS
├─ Check: CloudWatch → Lambda duration metrics
├─ Check: CloudWatch → Lambda concurrent executions
├─ Check: terraform/telegram_api.tf:143 (memory config)
└─ Check: terraform/aurora.tf:25 (min ACU)

LAYOUT SHIFTS
├─ Check: MarketsGrid.tsx (skeleton dimensions)
├─ Check: MarketCard.tsx:22-28 (image dimensions)
└─ Check: MarketModal.tsx (modal dimensions)
```

---

## CloudWatch Metric Locations

| Metric | CloudWatch Path | Alarm Threshold |
|--------|-----------------|-----------------|
| Lambda Duration | Lambda → telegram_api → Duration | 45s (terraform/monitoring.tf:150) |
| Lambda Errors | Lambda → telegram_api → Errors | 5 errors/5min |
| API 5xx | API Gateway → 5xx | 10 errors/5min |
| API 4xx | API Gateway → 4xx | 50 errors/15min |
| Aurora CPU | RDS → aurora-cluster → CPUUtilization | Not configured |
| Aurora Connections | RDS → aurora-cluster → DatabaseConnections | Not configured |

---

## Adding Performance Instrumentation

### Frontend (web-vitals)

```typescript
// main.tsx - Add after React render
import { onLCP, onFID, onCLS, onINP, onTTFB } from 'web-vitals';

const reportMetric = (metric: Metric) => {
  console.log(`[Performance] ${metric.name}: ${metric.value}`);
  // Optional: Send to analytics endpoint
};

onLCP(reportMetric);
onFID(reportMetric);
onCLS(reportMetric);
onINP(reportMetric);
onTTFB(reportMetric);
```

### Backend (timing logs)

```python
# src/api/app.py - Add timing decorator
import time
from functools import wraps

def log_timing(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        start = time.time()
        result = await func(*args, **kwargs)
        duration = time.time() - start
        logger.info(f"⏱️ {func.__name__}: {duration:.3f}s")
        return result
    return wrapper
```

### Aurora Query Timing

```python
# Already implemented in src/api/app.py:263-271
cache_start = time.time()
cached_report = precompute_service.get_cached_report(yahoo_ticker)
cache_duration = time.time() - cache_start
logger.info(f"✅ Cache HIT for {ticker_upper} ({cache_duration:.3f}s)")
```
