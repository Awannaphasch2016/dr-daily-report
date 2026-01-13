# Frontend Invariants

**Domain**: React, Telegram Mini App, Charts, State Management, UI
**Load when**: frontend, UI, chart, component, state, React, Zustand, TailwindCSS

**Related**: [telegram-uiux skill](../skills/telegram-uiux/), [Frontend Design skill](../skills/frontend-design/)

---

## Critical Path

```
User Action → State Update → API Call → State Update → Render
```

Every frontend operation must preserve this invariant: **UI reflects state, state reflects reality.**

---

## Level 4: Configuration Invariants

### Environment Variables
- [ ] `VITE_API_URL` set (API endpoint)
- [ ] `VITE_TELEGRAM_BOT_USERNAME` set (if needed)
- [ ] Build-time env vars baked into bundle

### Build Configuration
- [ ] `vite.config.ts` correct for target environment
- [ ] TailwindCSS configured properly
- [ ] TypeScript strict mode enabled
- [ ] No build warnings or errors

### Dependencies
- [ ] `package.json` versions locked
- [ ] No security vulnerabilities (`npm audit`)
- [ ] React version compatible with libraries

### Verification Commands
```bash
# Check environment setup
cat frontend/twinbar/.env

# Verify build succeeds
cd frontend/twinbar && npm run build

# Check for vulnerabilities
cd frontend/twinbar && npm audit

# Verify TypeScript compiles
cd frontend/twinbar && npm run type-check
```

---

## Level 3: Infrastructure Invariants

### Asset Delivery
- [ ] CloudFront serves static assets
- [ ] Cache headers configured correctly
- [ ] Gzip/Brotli compression enabled
- [ ] CORS headers allow API calls

### API Connectivity
- [ ] Frontend can reach backend API
- [ ] HTTPS enforced
- [ ] API timeout configured (30s for reports)
- [ ] Network errors handled gracefully

### Telegram Integration
- [ ] Mini App registered with BotFather
- [ ] Web App URL configured correctly
- [ ] Telegram WebApp SDK initialized
- [ ] Theme colors sync with Telegram

### Verification Commands
```bash
# Check CloudFront distribution
aws cloudfront list-distributions --query "DistributionList.Items[?Comment=='dr-daily-report']"

# Test API endpoint from browser console
fetch('https://api.example.com/health').then(r => r.json())

# Verify Telegram integration
# Open Mini App in Telegram, check console for errors
```

---

## Level 2: Data Invariants

### State Shape
- [ ] TypeScript types match actual state
- [ ] No `any` types in state definitions
- [ ] State is JSON-serializable
- [ ] Initial state is valid

### Data Never Shrinks (Monotonic)
- [ ] Array lengths don't decrease unexpectedly
- [ ] Loaded data persists until explicit clear
- [ ] Pagination adds, doesn't replace
- [ ] Cache invalidation is explicit

### Data Freshness
- [ ] Timestamps indicate data age
- [ ] Stale data marked visually
- [ ] Auto-refresh for time-sensitive data
- [ ] Manual refresh available

### Type Safety
- [ ] API responses validated against types
- [ ] No runtime type coercion
- [ ] Nullable fields handled explicitly
- [ ] Date/time parsed correctly

### Verification Commands
```bash
# Check TypeScript types
cd frontend/twinbar && npm run type-check

# Search for 'any' types
grep -r ": any" frontend/twinbar/src/

# Check state types
cat frontend/twinbar/src/stores/*.ts

# Verify data freshness handling
grep -r "updatedAt\|lastFetched" frontend/twinbar/src/
```

---

## Level 1: Service Invariants

### Rendering
- [ ] Components render without errors
- [ ] No React key warnings
- [ ] No memory leaks (useEffect cleanup)
- [ ] Loading states shown during async ops

### State Management (Zustand)
- [ ] Actions update state immutably
- [ ] Selectors prevent unnecessary re-renders
- [ ] No state mutations outside actions
- [ ] Persist middleware configured (if needed)

### Error Handling
- [ ] API errors caught and displayed
- [ ] Error boundaries prevent white screen
- [ ] Retry mechanisms for transient failures
- [ ] User-friendly error messages

### Performance
- [ ] Initial load < 3s
- [ ] Interaction response < 100ms
- [ ] No jank during scrolling
- [ ] Images optimized and lazy-loaded

### Verification Commands
```bash
# Check for React warnings (in browser console)
# Open app and check console for:
# - "Warning: Each child in a list should have a unique 'key' prop"
# - "Warning: Can't perform a React state update on an unmounted component"

# Run lint
cd frontend/twinbar && npm run lint

# Check bundle size
cd frontend/twinbar && npm run build && du -sh dist/

# Lighthouse audit
# Run in Chrome DevTools > Lighthouse
```

---

## Level 0: User Invariants

### Visual Feedback
- [ ] Loading spinners during data fetch
- [ ] Success/error toasts for actions
- [ ] Disabled buttons prevent double-submit
- [ ] Progress indicators for long operations

### Navigation
- [ ] Back button works correctly
- [ ] Deep links preserved
- [ ] State survives navigation
- [ ] No unexpected redirects

### Data Display
- [ ] Numbers formatted correctly (commas, decimals)
- [ ] Dates in Bangkok timezone
- [ ] Charts render with correct data
- [ ] Tables sortable/filterable

### Accessibility
- [ ] Keyboard navigation works
- [ ] Screen reader compatible
- [ ] Color contrast sufficient
- [ ] Touch targets >= 44px

### Verification Commands
```bash
# Manual testing checklist:
# 1. Open Mini App in Telegram
# 2. Navigate through all screens
# 3. Verify loading states appear
# 4. Verify data displays correctly
# 5. Test error scenarios (offline, API down)
# 6. Check chart interactions

# Accessibility audit
# Run axe DevTools in browser
```

---

## Chart Invariants

### Data Accuracy
- [ ] OHLCV values match API response
- [ ] Dates on X-axis correct
- [ ] Price scale accurate
- [ ] Volume scale accurate

### Visual Rendering
- [ ] Candlesticks render correctly (green up, red down)
- [ ] Pattern overlays align with candles
- [ ] Tooltips show accurate data
- [ ] Responsive across screen sizes

### Interactions
- [ ] Zoom works correctly
- [ ] Pan works correctly
- [ ] Crosshair follows cursor
- [ ] Touch gestures work on mobile

### Pattern Overlays (if applicable)
- [ ] Patterns render at correct positions
- [ ] Pattern colors match type
- [ ] Legend shows active patterns
- [ ] Can toggle patterns on/off

### Verification Commands
```bash
# Visual verification:
# 1. Load chart with known ticker
# 2. Verify candles match API data
# 3. Enable pattern overlays
# 4. Verify patterns align with candles
# 5. Test zoom/pan
# 6. Test on mobile device
```

---

## State Management Invariants (Zustand)

### Store Structure
```typescript
// Expected store shape
interface TickerStore {
  // Data
  tickers: Ticker[];
  selectedTicker: Ticker | null;

  // Loading states
  isLoading: boolean;
  error: Error | null;

  // Actions
  fetchTickers: () => Promise<void>;
  selectTicker: (symbol: string) => void;
}
```

### Action Invariants
- [ ] Actions are synchronous state updates
- [ ] Async operations use proper loading states
- [ ] Errors captured in state
- [ ] Success clears error state

### Selector Invariants
- [ ] Selectors are memoized
- [ ] Derived state computed in selectors
- [ ] No component-level filtering (use selectors)

---

## Anti-Patterns (What Breaks Invariants)

| Anti-Pattern | Invariant Violated | Fix |
|--------------|-------------------|-----|
| Mutating state directly | Level 1 (immutability) | Use spread or immer |
| Missing loading state | Level 0 (feedback) | Add isLoading to store |
| `any` type on API response | Level 2 (type safety) | Create proper types |
| Missing error boundary | Level 1 (error handling) | Add ErrorBoundary component |
| Hardcoded API URL | Level 4 (config) | Use environment variable |
| Data shrinks on refetch | Level 2 (monotonic) | Merge, don't replace |
| Missing key prop | Level 1 (rendering) | Add unique key |
| useEffect without cleanup | Level 1 (memory) | Return cleanup function |

---

## Component Checklist Template

For each new component:

### Design
- [ ] Props interface defined (TypeScript)
- [ ] State requirements identified
- [ ] Loading/error states designed
- [ ] Mobile responsive

### Implementation
- [ ] Component created in correct directory
- [ ] Props destructured with types
- [ ] Hooks at top level
- [ ] Error handling implemented

### Styling
- [ ] TailwindCSS classes used
- [ ] Dark mode supported (if applicable)
- [ ] Telegram theme colors used
- [ ] Responsive breakpoints handled

### Testing
- [ ] Renders without error
- [ ] Loading state displays
- [ ] Error state displays
- [ ] User interactions work

---

## Claiming "Frontend Work Done"

```markdown
✅ Frontend work complete: {description}

**Type**: {new component | bug fix | feature | styling}
**Component**: {component path}

**Invariants Verified**:
- [x] Level 4: Env vars set, build succeeds, types compile
- [x] Level 3: API connectivity works, assets served
- [x] Level 2: State shape correct, data doesn't shrink
- [x] Level 1: Renders without errors, state updates correctly
- [x] Level 0: Loading states, error handling, accessibility

**Confidence**: {HIGH | MEDIUM | LOW}
**Evidence**: {Screenshot, test results, console output}
```

---

*Domain: frontend*
*Last updated: 2026-01-12*
