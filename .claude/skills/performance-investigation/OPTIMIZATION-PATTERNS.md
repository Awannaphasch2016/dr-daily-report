# Optimization Patterns

## Pattern 1: Cache-First Data Loading

**Problem**: Every click triggers API fetch even when data exists in memory.

**Current Code** (`App.tsx:111-118`):
```typescript
const handleSelectMarket = (market: Market) => {
  setSelectedTicker(market.id);
  setIsModalOpen(true);
  fetchReport(market.id);  // ALWAYS fetches
};
```

**Optimized Code**:
```typescript
const handleSelectMarket = (market: Market) => {
  setSelectedTicker(market.id);
  setIsModalOpen(true);

  // Only fetch if modal-specific data is missing
  const hasCompleteData = market.report?.all_scores?.length > 0
    && market.report?.narrative_sections?.length > 0;

  if (!hasCompleteData) {
    fetchReport(market.id);
  }
};
```

**Impact**: ~1000ms saved per repeat click

---

## Pattern 2: React Query for Automatic Caching

**Problem**: Manual cache management in Zustand, no deduplication.

**Current**: Manual fetch in `marketStore.ts`

**Optimized** (React Query already installed!):

```typescript
// hooks/useReport.ts
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../api/client';

export const useReport = (ticker: string | null) => {
  return useQuery({
    queryKey: ['report', ticker],
    queryFn: () => ticker ? apiClient.getCachedReport(ticker) : null,
    enabled: !!ticker,
    staleTime: 5 * 60 * 1000,  // 5 min - serve cached
    gcTime: 30 * 60 * 1000,    // 30 min - keep in memory
  });
};

// Usage in component
const { data: report, isLoading, error } = useReport(selectedTicker);
```

**Benefits**:
- Automatic caching (same ticker = no refetch)
- Request deduplication (rapid clicks = 1 request)
- Stale-while-revalidate (show cached, update in background)
- Automatic error handling

---

## Pattern 3: Code Splitting with Lazy Loading

**Problem**: Single 200KB+ bundle loaded upfront.

**Current** (`vite.config.ts`):
```typescript
export default defineConfig({
  plugins: [react(), tailwindcss()],
  build: {
    outDir: 'dist',
    sourcemap: false,
  },
});
```

**Optimized**:
```typescript
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';

export default defineConfig({
  plugins: [react(), tailwindcss()],
  build: {
    outDir: 'dist',
    sourcemap: false,
    rollupOptions: {
      output: {
        manualChunks: {
          'vendor-react': ['react', 'react-dom'],
          'vendor-charts': ['recharts'],
          'vendor-state': ['zustand', '@tanstack/react-query'],
        },
      },
    },
  },
});
```

**Lazy Load Modal Components**:
```typescript
// App.tsx
import { lazy, Suspense } from 'react';

const MarketModal = lazy(() => import('./components/MarketModal'));

// In render
<Suspense fallback={<ModalSkeleton />}>
  <MarketModal ... />
</Suspense>
```

**Impact**: Smaller initial bundle, faster TTI

---

## Pattern 4: Search Debouncing

**Problem**: Every keystroke triggers filter recalculation.

**Current** (`SearchBar.tsx`):
```typescript
const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
  const value = e.target.value;
  setQuery(value);
  onSearch(value);  // Fires immediately
};
```

**Optimized**:
```typescript
import { useDeferredValue, useState } from 'react';

const SearchBar = ({ onSearch }: Props) => {
  const [query, setQuery] = useState('');
  const deferredQuery = useDeferredValue(query);

  useEffect(() => {
    onSearch(deferredQuery);
  }, [deferredQuery, onSearch]);

  return (
    <input
      value={query}
      onChange={(e) => setQuery(e.target.value)}
      placeholder="Search..."
    />
  );
};
```

**Or with debounce**:
```typescript
import { useMemo, useState } from 'react';
import debounce from 'lodash.debounce';

const SearchBar = ({ onSearch }: Props) => {
  const [query, setQuery] = useState('');

  const debouncedSearch = useMemo(
    () => debounce(onSearch, 300),
    [onSearch]
  );

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    setQuery(value);
    debouncedSearch(value);
  };

  return <input value={query} onChange={handleChange} />;
};
```

---

## Pattern 5: Skeleton Loading States

**Problem**: Empty state → content jump causes CLS.

**Current**: Modal shows nothing, then full content.

**Optimized** (`MarketModal.tsx`):
```typescript
const MarketModal = ({ market, isOpen, isLoading }: Props) => {
  if (!isOpen) return null;

  return (
    <div className="modal">
      {isLoading ? (
        <ModalSkeleton />
      ) : (
        <ModalContent market={market} />
      )}
    </div>
  );
};

const ModalSkeleton = () => (
  <div className="animate-pulse">
    <div className="h-8 bg-gray-200 rounded w-3/4 mb-4" />
    <div className="h-64 bg-gray-200 rounded mb-4" />
    <div className="h-4 bg-gray-200 rounded w-1/2 mb-2" />
    <div className="h-4 bg-gray-200 rounded w-2/3" />
  </div>
);
```

**Impact**: Better perceived performance, reduced CLS

---

## Pattern 6: Image Lazy Loading

**Problem**: All images load immediately.

**Current** (`MarketCard.tsx:22-28`):
```typescript
<img src={market.image} alt="" className="..." />
```

**Optimized**:
```typescript
<img
  src={market.image}
  alt=""
  className="..."
  loading="lazy"
  width={48}
  height={48}
  decoding="async"
/>
```

**Impact**: Faster initial load, reduced bandwidth

---

## Pattern 7: Memoization for Expensive Calculations

**Problem**: Derived data recalculated on every render.

**Already Used** (`App.tsx:58-97`):
```typescript
const filteredMarkets = useMemo(() => {
  // Filtering and sorting logic
}, [markets, category, sortBy, searchQuery]);
```

**Add to Components**:
```typescript
// Wrap components that receive complex props
const MemoizedMarketCard = React.memo(MarketCard);

// Use useCallback for handlers passed to children
const handleSelect = useCallback((market: Market) => {
  setSelectedTicker(market.id);
  setIsModalOpen(true);
}, []);
```

---

## Pattern 8: Provisioned Concurrency for Lambda

**Problem**: Cold starts add 1-2s latency.

**Current** (`terraform/telegram_api.tf`):
```hcl
resource "aws_lambda_function" "telegram_api" {
  # No provisioned concurrency
}
```

**Optimized**:
```hcl
resource "aws_lambda_provisioned_concurrency_config" "telegram_api" {
  function_name                     = aws_lambda_function.telegram_api.function_name
  provisioned_concurrent_executions = 2
  qualifier                         = aws_lambda_function.telegram_api.version
}
```

**Trade-off**:
- Cost: ~$0.015/hour per provisioned instance
- Benefit: Eliminates cold starts entirely

---

## Pattern 9: Expand Rankings Response

**Problem**: Rankings returns partial data, modal needs full data.

**Current** (`rankings_service.py:127-146`):
```python
chart_data = {
    'price_history': report_json.get('price_history', []),
    'projections': report_json.get('projections', []),
}
key_scores = key_scores_data[:3]
```

**Optimized**:
```python
# Include all modal data
chart_data = {
    'price_history': report_json.get('price_history', []),
    'projections': report_json.get('projections', []),
    'initial_investment': report_json.get('initial_investment', 1000.0),
}
all_scores = report_json.get('all_scores', key_scores_data)
narrative_sections = report_json.get('narrative_sections', [])
peers = report_json.get('peers', [])
chart_patterns = report_json.get('chart_patterns', [])
```

**Trade-off**:
- Initial payload: ~15KB → ~50KB
- Modal load: 500-1500ms → 0ms

---

## Pattern 10: Web Vitals Monitoring

**Problem**: No visibility into real user performance.

**Add to** `main.tsx`:
```typescript
import { onLCP, onFID, onCLS, onINP, onTTFB } from 'web-vitals';

function sendToAnalytics(metric: Metric) {
  const body = JSON.stringify({
    name: metric.name,
    value: metric.value,
    id: metric.id,
    navigationType: metric.navigationType,
  });

  // Use sendBeacon for reliability
  if (navigator.sendBeacon) {
    navigator.sendBeacon('/api/v1/analytics', body);
  } else {
    fetch('/api/v1/analytics', { body, method: 'POST', keepalive: true });
  }
}

onLCP(sendToAnalytics);
onFID(sendToAnalytics);
onCLS(sendToAnalytics);
onINP(sendToAnalytics);
onTTFB(sendToAnalytics);
```

**Or use Vercel Speed Insights** (simpler):
```typescript
import { SpeedInsights } from '@vercel/speed-insights/react';

function App() {
  return (
    <>
      <SpeedInsights />
      {/* rest of app */}
    </>
  );
}
```

---

## Priority Matrix

| Pattern | Impact | Effort | Priority |
|---------|--------|--------|----------|
| 1. Cache-First Loading | High | Low | **Do First** |
| 5. Skeleton States | Medium | Low | **Do First** |
| 10. Web Vitals Monitoring | Low (enables others) | Low | **Do First** |
| 2. React Query | High | Medium | **This Sprint** |
| 9. Expand Rankings | High | Medium | **This Sprint** |
| 3. Code Splitting | Medium | Medium | **This Sprint** |
| 4. Search Debounce | Low | Low | **Quick Win** |
| 6. Image Lazy Load | Low | Low | **Quick Win** |
| 7. More Memoization | Medium | Medium | **As Needed** |
| 8. Provisioned Concurrency | Medium | Low | **If Cold Starts Persist** |
