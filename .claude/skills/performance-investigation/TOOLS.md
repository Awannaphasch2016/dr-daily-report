# Performance Investigation Tools

## Browser DevTools

### Network Tab
**Purpose**: Analyze request waterfall, timing, payload sizes

**Key Features**:
- Filter by XHR (API calls only)
- Timing breakdown (DNS, Connect, TTFB, Download)
- Response size and compression
- Caching status (from disk/memory/network)

**How to Use**:
```
1. Open DevTools (F12)
2. Go to Network tab
3. Check "Disable cache" for accurate measurements
4. Reload page or perform action
5. Click request → Timing tab for breakdown
```

**Key Columns**:
| Column | What It Shows |
|--------|---------------|
| Status | HTTP status code |
| Type | xhr, script, stylesheet, etc. |
| Size | Transfer size (compressed) |
| Time | Total request time |
| Waterfall | Visual timing breakdown |

---

### Performance Tab
**Purpose**: CPU profiling, rendering analysis, long tasks

**Key Features**:
- Flame graph of JavaScript execution
- Main thread activity
- Paint and layout events
- Long tasks (>50ms) highlighted

**How to Use**:
```
1. Open DevTools (F12)
2. Go to Performance tab
3. Click Record (or Ctrl+E)
4. Perform the slow action
5. Stop recording
6. Analyze flame graph
```

**What to Look For**:
- **Red frames**: Missed 60fps target
- **Yellow blocks**: JavaScript execution
- **Purple blocks**: Rendering/layout
- **Green blocks**: Painting

---

### Lighthouse
**Purpose**: Automated audit of Core Web Vitals and best practices

**How to Use**:
```
1. Open DevTools (F12)
2. Go to Lighthouse tab
3. Select: Performance, Desktop/Mobile
4. Click "Analyze page load"
5. Review scores and opportunities
```

**Score Interpretation**:
| Score | Meaning |
|-------|---------|
| 90-100 | Good (green) |
| 50-89 | Needs improvement (orange) |
| 0-49 | Poor (red) |

---

### Coverage Tab
**Purpose**: Find unused JavaScript and CSS

**How to Use**:
```
1. Open DevTools (F12)
2. Ctrl+Shift+P → Type "Coverage"
3. Click "Start instrumenting coverage"
4. Navigate through app
5. View unused bytes per file
```

**Interpretation**:
- Red bars = unused code
- High unused % = candidate for code splitting

---

### React DevTools
**Purpose**: Component profiling, state inspection

**Installation**: Chrome/Firefox extension

**Profiler Tab**:
```
1. Open React DevTools → Profiler
2. Click Record
3. Perform action
4. Stop recording
5. View component render times
```

**What to Look For**:
- Components rendering without prop changes
- Expensive render times (>16ms)
- Cascading re-renders

---

## AWS CloudWatch

### Lambda Metrics
**Path**: CloudWatch → Metrics → Lambda → By Function Name

**Key Metrics**:
| Metric | What It Shows |
|--------|---------------|
| Duration | Execution time (ms) |
| Invocations | Number of calls |
| Errors | Error count |
| ConcurrentExecutions | Simultaneous runs |
| Throttles | Rate limit hits |

**Cold Start Detection**:
```
1. Go to Duration metric
2. Look for spikes after periods of no invocations
3. Cold start = spike of 1-2 seconds
```

---

### Lambda Logs
**Path**: CloudWatch → Log groups → `/aws/lambda/telegram_api`

**Filter Patterns**:
```
# Find cache hits
"Cache HIT"

# Find errors
"ERROR"

# Find timing info
"⏱️"

# Find slow queries (if instrumented)
"duration"
```

---

### API Gateway Metrics
**Path**: CloudWatch → Metrics → API Gateway → By API

**Key Metrics**:
| Metric | What It Shows |
|--------|---------------|
| Count | Total requests |
| Latency | Response time (ms) |
| IntegrationLatency | Lambda execution time |
| 4XXError | Client errors |
| 5XXError | Server errors |

---

### CloudFront Reports
**Path**: CloudFront → Distribution → Reports

**Key Reports**:
- **Cache Statistics**: Hit ratio, miss ratio
- **Popular Objects**: Most requested files
- **Top Referrers**: Traffic sources
- **Usage**: Data transfer, requests

---

## Performance Libraries

### web-vitals
**Purpose**: Measure Core Web Vitals in production

**Installation**:
```bash
npm install web-vitals
```

**Usage**:
```typescript
import { onLCP, onFID, onCLS, onINP, onTTFB } from 'web-vitals';

onLCP(console.log);   // Largest Contentful Paint
onFID(console.log);   // First Input Delay
onCLS(console.log);   // Cumulative Layout Shift
onINP(console.log);   // Interaction to Next Paint
onTTFB(console.log);  // Time to First Byte
```

---

### @vercel/speed-insights
**Purpose**: Easy RUM (Real User Monitoring) setup

**Installation**:
```bash
npm install @vercel/speed-insights
```

**Usage**:
```typescript
import { SpeedInsights } from '@vercel/speed-insights/react';

function App() {
  return (
    <>
      <SpeedInsights />
      {/* app content */}
    </>
  );
}
```

---

### react-scan
**Purpose**: Visualize React renders

**Installation**:
```bash
npm install react-scan
```

**Usage**:
```typescript
// In development only
if (process.env.NODE_ENV === 'development') {
  import('react-scan').then(({ scan }) => {
    scan({
      enabled: true,
      log: true,
    });
  });
}
```

---

### why-did-you-render
**Purpose**: Detect unnecessary re-renders

**Installation**:
```bash
npm install @welldone-software/why-did-you-render
```

**Usage**:
```typescript
// wdyr.ts (import first in index.tsx)
import React from 'react';

if (process.env.NODE_ENV === 'development') {
  const whyDidYouRender = require('@welldone-software/why-did-you-render');
  whyDidYouRender(React, {
    trackAllPureComponents: true,
  });
}

// On specific component
MarketCard.whyDidYouRender = true;
```

---

## CLI Tools

### Vite Bundle Analyzer
```bash
# Install
npm install -D rollup-plugin-visualizer

# Add to vite.config.ts
import { visualizer } from 'rollup-plugin-visualizer';

plugins: [
  visualizer({
    open: true,
    filename: 'bundle-stats.html',
  }),
]

# Build and view
npm run build
# Opens interactive treemap
```

---

### AWS CLI Performance Commands

**Check Lambda Configuration**:
```bash
aws lambda get-function-configuration \
  --function-name dr-daily-report-telegram-api-dev \
  --query '{Memory: MemorySize, Timeout: Timeout}'
```

**View Recent Lambda Duration**:
```bash
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Duration \
  --dimensions Name=FunctionName,Value=dr-daily-report-telegram-api-dev \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 300 \
  --statistics Average Maximum \
  --output table
```

**Check CloudFront Cache Hit Ratio**:
```bash
aws cloudfront get-distribution \
  --id YOUR_DISTRIBUTION_ID \
  --query 'Distribution.Status'
```

---

## Quick Reference Commands

| Task | Command |
|------|---------|
| Check bundle size | `npm run build && ls -la dist/assets/*.js` |
| Profile React | DevTools → React DevTools → Profiler |
| Find long tasks | DevTools → Performance → Record |
| Check Lambda duration | CloudWatch → Lambda → Duration |
| View API latency | CloudWatch → API Gateway → Latency |
| Analyze cache hits | CloudWatch Logs → filter "Cache HIT" |
