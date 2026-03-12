# Performance Investigation Checklist

## Before You Start

- [ ] Reproduce the issue consistently
- [ ] Note the specific user action causing slowness
- [ ] Determine if it's always slow or intermittent

---

## Phase 1: Measure Baseline

### Browser Metrics (DevTools)
- [ ] Open DevTools (F12) → Network tab
- [ ] Clear cache and hard reload
- [ ] Record: Total load time, # requests, total size
- [ ] Check TTFB for API calls
- [ ] Note largest/slowest resources

### Core Web Vitals (Lighthouse)
- [ ] Run Lighthouse in incognito mode
- [ ] Set device to "Mobile" for real-world simulation
- [ ] Record LCP, FID/INP, CLS, TBT scores
- [ ] Screenshot opportunities and diagnostics

### Performance Recording
- [ ] DevTools → Performance tab → Record
- [ ] Perform the slow action
- [ ] Stop recording
- [ ] Identify long tasks (>50ms) in flame graph
- [ ] Check main thread blocking time

---

## Phase 2: Identify Bottleneck Layer

### Is it Frontend? (Check first if LCP/TBT high)
- [ ] Check bundle size: DevTools → Network → JS files
- [ ] Check React renders: React DevTools → Profiler
- [ ] Check for layout thrashing: Performance → Layout events
- [ ] Verify memoization: Check useMemo/useCallback usage

### Is it Network? (Check if TTFB high)
- [ ] Check request waterfall timing
- [ ] Verify CloudFront cache status (x-cache header)
- [ ] Check response payload size
- [ ] Test with different network throttling

### Is it Backend? (Check CloudWatch)
- [ ] Check Lambda duration metric
- [ ] Check for cold starts (duration spike after idle)
- [ ] Check Aurora query time (if instrumented)
- [ ] Check error rates

---

## Phase 3: Map to Code

Use METRICS-MAP.md to find affected files:

### Frontend Issues
- [ ] Slow initial load → `vite.config.ts`, `main.tsx`
- [ ] Slow interaction → Handler in `App.tsx` or component
- [ ] Layout shifts → Component render order
- [ ] Chart slowness → `FullChart.tsx`, `MiniChart.tsx`

### Backend Issues
- [ ] Slow API → `src/api/app.py` endpoint
- [ ] Slow query → `src/data/aurora/` service
- [ ] Cold starts → `terraform/telegram_api.tf`

---

## Phase 4: Apply Optimization

### Quick Wins (Do First)
- [ ] Cache-first loading (`App.tsx:handleSelectMarket`)
- [ ] Skeleton loading states (`MarketModal.tsx`)
- [ ] Image lazy loading (`MarketCard.tsx`)
- [ ] Search debouncing (`SearchBar.tsx`)

### Medium Effort
- [ ] Implement React Query (replace manual fetching)
- [ ] Add code splitting (`vite.config.ts`)
- [ ] Expand rankings response (backend)

### Infrastructure
- [ ] Increase Lambda memory (if cold start issue)
- [ ] Add provisioned concurrency (if cold start persists)
- [ ] Increase Aurora min ACU (if query slowness)

---

## Phase 5: Validate Improvement

- [ ] Re-run same measurements from Phase 1
- [ ] Compare before/after metrics
- [ ] Check for regressions in other areas
- [ ] Test on different devices/networks
- [ ] Document changes and results

---

## Quick Diagnosis Guide

### Symptom: Modal takes >1 second to show content

```
1. DevTools → Network → Filter XHR
2. Click a card
3. Find the /report/{ticker} request
4. Check timing:
   - TTFB > 500ms? → Backend issue (Lambda or Aurora)
   - Download > 500ms? → Payload too large
   - TTFB < 100ms but still slow? → Frontend rendering
```

### Symptom: First click after idle is slow

```
1. CloudWatch → Lambda → telegram_api → Duration
2. Look for spikes after gaps in invocations
3. If spike = 1-2s, it's Lambda cold start
4. Solution: Increase memory or add provisioned concurrency
```

### Symptom: Page feels janky when scrolling

```
1. DevTools → Performance → Record while scrolling
2. Look for:
   - Red frames (missed paint deadline)
   - Long paint times (>16ms)
   - Layout events during scroll
3. Solution: Virtualization, reduce DOM complexity
```

### Symptom: Search is laggy

```
1. DevTools → Performance → Record while typing
2. Look for:
   - Main thread blocking during keystrokes
   - Filter/sort operations taking >50ms
3. Solution: Debounce input, useDeferredValue
```

---

## Metrics Targets

| Metric | Current (Estimate) | Target | Action if Exceeded |
|--------|-------------------|--------|-------------------|
| LCP | ~3s | <2.5s | Code splitting, cache-first |
| INP | ~300ms | <200ms | Memoization, skip fetches |
| CLS | ~0.15 | <0.1 | Skeletons, fixed dimensions |
| TTFB | ~500ms | <200ms | Provisioned concurrency |
| Bundle Size | ~200KB | <150KB | Code splitting |
| API Response | ~50KB | <30KB | Field selection |

---

## Post-Optimization Checklist

- [ ] Metrics improved as expected
- [ ] No regressions in other metrics
- [ ] Changes documented
- [ ] Tests still pass
- [ ] Deployed to dev environment
- [ ] Verified in real conditions (mobile, slow network)
