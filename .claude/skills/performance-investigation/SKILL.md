# Performance Investigation Skill

**Purpose**: Systematic web performance investigation for Telegram Mini App + AWS Lambda architecture.

**When to use**:
- Diagnosing slow page loads or interactions
- Investigating API latency issues
- Optimizing bundle size or rendering
- Analyzing CloudWatch metrics for bottlenecks

---

## Performance Investigation Workflow

```
┌─────────────────────────────────────────────────────────────────┐
│                    PERFORMANCE INVESTIGATION                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. MEASURE (Baseline)                                          │
│     ├─ Core Web Vitals (LCP, FID/INP, CLS)                      │
│     ├─ Network waterfall (TTFB, download times)                 │
│     └─ CloudWatch metrics (Lambda duration, cold starts)        │
│                                                                 │
│  2. IDENTIFY (Bottleneck Layer)                                 │
│     ├─ Frontend? (bundle size, rendering, JS execution)         │
│     ├─ Network? (latency, payload size, connection reuse)       │
│     ├─ Backend? (Lambda, Aurora, serialization)                 │
│     └─ Infrastructure? (cold starts, CDN cache misses)          │
│                                                                 │
│  3. MAP (Code Location)                                         │
│     ├─ Use METRICS-MAP.md to find affected files                │
│     ├─ Add timing instrumentation if needed                     │
│     └─ Correlate user actions to backend traces                 │
│                                                                 │
│  4. OPTIMIZE (Apply Fix)                                        │
│     ├─ Use OPTIMIZATION-PATTERNS.md for solutions               │
│     ├─ Prioritize by impact/effort ratio                        │
│     └─ Verify improvement with same measurement                 │
│                                                                 │
│  5. VALIDATE (Confirm)                                          │
│     ├─ Re-measure with same methodology                         │
│     ├─ Check for regressions in other metrics                   │
│     └─ Document in performance changelog                        │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Quick Reference: Metric → Layer → File

| Symptom | Likely Layer | Check First |
|---------|--------------|-------------|
| Slow initial load (>3s) | Bundle/CDN | `vite.config.ts`, CloudFront TTL |
| Slow modal open (>500ms) | API/Cache | `App.tsx:handleSelectMarket`, `marketStore.ts` |
| Janky scrolling | Rendering | Component memoization, virtualization |
| First click delay (>1s) | Lambda cold start | `terraform/telegram_api.tf` memory/concurrency |
| Intermittent slowness | Aurora scaling | ACU config, connection pooling |

---

## Investigation Decision Tree

```
Is the issue with INITIAL PAGE LOAD?
├─ YES → Check bundle size, code splitting, CDN caching
│        Files: vite.config.ts, terraform/frontend.tf
│
└─ NO → Is it with SPECIFIC USER ACTION?
        ├─ YES → Which action?
        │        ├─ Click card → Check fetchReport, cache-first logic
        │        ├─ Search → Check debouncing, query optimization
        │        ├─ Scroll → Check virtualization, rendering
        │        └─ Chart interaction → Check Recharts optimization
        │
        └─ NO → Is it RANDOM/INTERMITTENT?
                ├─ First request after idle → Lambda cold start
                ├─ After period of load → Aurora ACU scaling
                └─ Specific times of day → Check CloudWatch patterns
```

---

## Files in This Skill

| File | Purpose |
|------|---------|
| `SKILL.md` | Overview and decision tree (this file) |
| `METRICS-GLOSSARY.md` | Terminology and definitions |
| `METRICS-MAP.md` | Metrics → Infrastructure → Code mapping |
| `OPTIMIZATION-PATTERNS.md` | Common fixes with code examples |
| `TOOLS.md` | Browser DevTools, AWS tools, libraries |
| `CHECKLIST.md` | Step-by-step investigation checklist |

---

## See Also

- `telegram-uiux` skill - React/Zustand patterns
- `deployment` skill - Lambda configuration
- `error-investigation` skill - CloudWatch log analysis
