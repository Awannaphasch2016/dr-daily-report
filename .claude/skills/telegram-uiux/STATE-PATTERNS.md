# State Management Patterns

Patterns for managing state in Telegram Mini App (React + Zustand).

**Source**: Extracted from `docs/frontend/UI_PRINCIPLES.md` - hard-won lessons from real bugs.

---

## Normalized State Pattern

**Principle**: Store entity IDs instead of object copies. Derive data from a single source of truth via selectors.

### Why It Matters
- Eliminates entire class of "stale copy" bugs
- Automatic updates when source data changes
- Simpler mental model (one source, multiple views)
- No need to manually sync multiple copies

### Example Problem (Object Copy)

```typescript
// ❌ BAD: Storing object copy
interface AppState {
  markets: Market[];
  selectedMarket: Market | null;  // Copy of a market from markets[]
}

// User clicks market card
function handleSelect(market: Market) {
  setSelectedMarket(market);  // Creates copy
}

// Later, markets array updates...
function updateMarkets(newMarkets: Market[]) {
  setMarkets(newMarkets);  // selectedMarket is now stale!
}

// Bug: selectedMarket still has old data!
```

### Solution (Normalized State)

```typescript
// ✅ GOOD: Storing ID reference
interface AppState {
  markets: Market[];
  selectedTicker: string | null;  // Just the ID

  // Selector derives market from source
  getSelectedMarket: () => Market | null;
}

const useMarketStore = create<AppState>((set, get) => ({
  markets: [],
  selectedTicker: null,

  // Derive from single source
  getSelectedMarket: () => {
    const { markets, selectedTicker } = get();
    if (!selectedTicker) return null;
    return markets.find(m => m.id === selectedTicker) || null;
  },

  setSelectedTicker: (ticker: string | null) => set({ selectedTicker: ticker }),
  setMarkets: (markets: Market[]) => set({ markets }),
}));

// Use in component
function MarketModal() {
  const selectedMarket = useMarketStore(state => state.getSelectedMarket());
  // Always fresh data, even when markets array updates!
}
```

### Benefits
- ✅ No stale data
- ✅ One source of truth
- ✅ Automatic updates
- ✅ Less memory (store ID not full object)

### When to Use
- ✓ Selecting items from lists
- ✓ Master-detail views
- ✓ Any case where you "copy" data from one place to another

**Real-World Example**: `frontend/twinbar/src/stores/marketStore.ts` (refactored from object copy to ID reference)

---

## Single Source of Truth

**Principle**: Each piece of data should have exactly one canonical location. All other views derive from that source.

### Why It Matters
- No synchronization bugs
- Clear ownership of data
- Easy to reason about data flow
- Simpler debugging (one place to look)

### Example

```typescript
// ❌ BAD: Multiple sources of truth
const [markets, setMarkets] = useState([]);
const [selectedMarket, setSelectedMarket] = useState(null);
const [selectedMarketData, setSelectedMarketData] = useState(null);
// Three copies of market data - nightmare to keep in sync!

// ✅ GOOD: Single source
const markets = useMarketStore(state => state.markets);  // Source
const selectedMarket = useMarketStore(state => state.getSelectedMarket());  // Derived
// One source, one derived view
```

### Pattern

```
Source (markets[])
  ↓
Selector (getSelectedMarket)
  ↓
Component (displays derived data)
```

### Rule of Thumb
If you find yourself calling `setState` to "sync" two pieces of data, you probably need a single source + selector pattern instead.

---

## Intelligent Merge Strategies

**Principle**: When updating state from API, preserve valuable cached data. Only overwrite if new data is demonstrably better (non-empty AND larger/fresher).

### Why It Matters
- Robust against partial API failures
- Handles degraded responses gracefully
- Prevents data loss from race conditions
- Better UX during API errors

### Example Problem

```typescript
// ❌ BAD: Blindly replace with API response
function updateFromAPI(apiResponse: Report) {
  setState({
    priceHistory: apiResponse.price_history,  // Might be empty!
    projections: apiResponse.projections,      // Might be []!
  });
}

// User sees chart disappear when API returns empty response
```

### Solution

```typescript
// ✅ GOOD: Intelligent merge
function updateFromAPI(apiResponse: Report, currentState: Report) {
  const cachedPriceHistoryLength = currentState.priceHistory?.length || 0;
  const newPriceHistoryLength = apiResponse.price_history?.length || 0;

  setState({
    priceHistory:
      // Only use new data if it's BETTER (larger, non-empty)
      newPriceHistoryLength > cachedPriceHistoryLength
        ? apiResponse.price_history
        : currentState.priceHistory || [],  // Keep cached

    projections:
      apiResponse.projections?.length > (currentState.projections?.length || 0)
        ? apiResponse.projections
        : currentState.projections || [],
  });
}
```

### Pattern Template

```typescript
// Merge strategy template
newData && newData.length > cachedData.length
  ? newData      // Upgrade to better data
  : cachedData   // Preserve what we have
```

### When to Use
- ✓ Updating from slow/unreliable APIs
- ✓ Merging cached + fresh data
- ✓ Any case where API might return partial data

**Real-World Example**: `frontend/twinbar/src/stores/marketStore.ts:fetchReport()` (lines 276-289)

---

## Monotonic Data Invariants

**Principle**: Some data structures should only grow or stay the same, never shrink. Enforce this via merge logic and property-based tests.

### Why It Matters
- Predictable behavior (data never disappears)
- Catches API bugs (partial responses detected)
- Documented guarantees (invariants are promises)
- Regression prevention (tests enforce it)

### Example

```typescript
// INVARIANT: price_history.length never decreases after being populated

// ✅ GOOD: Enforce monotonicity
function updatePriceHistory(newData: PricePoint[], cached: PricePoint[]) {
  const cachedLength = cached?.length || 0;
  const newLength = newData?.length || 0;

  // Only replace if NEW DATA IS BIGGER
  if (newLength > cachedLength) {
    return newData;
  }

  // Otherwise keep what we have
  return cached;
}

// Example sequence:
// Initial: [] → Load 30 days → [30 items]
// Later: [30 items] + API returns 10 items → Keep [30 items] (don't shrink!)
// Later: [30 items] + API returns 365 items → Upgrade to [365 items]
```

### Testing the Invariant

See [TESTING.md](TESTING.md) for property-based testing patterns that verify monotonic invariants with 1000+ generated test cases.

### Common Monotonic Data
- Price history (never shrink chart data)
- Event logs (never delete history)
- Cached API responses (never reduce cache size)
- Aggregated metrics (only add, never remove)

**Real-World Example**: `frontend/twinbar/src/stores/marketStore.test.ts` (property-based tests for chart monotonicity)

---

## Stale-While-Revalidate

**Principle**: Show cached data immediately for instant UI feedback, then fetch fresh data in background and upgrade UI when it arrives.

### Why It Matters
- Perceived performance (instant UI)
- Better UX (users don't wait)
- Handles slow APIs gracefully
- Progressive enhancement (fast → slow)

### Pattern Flow

```
User Action
  ↓
1. Show cached data (instant)
  ↓
2. Fetch fresh data (background)
  ↓
3. Update UI when fresh data arrives
```

### Example

```typescript
// ✅ GOOD: Stale-while-revalidate
function openMarketModal(marketId: string) {
  // 1. Open modal immediately with cached data (30-day chart)
  setSelectedTicker(marketId);
  setIsModalOpen(true);

  // 2. Fetch full report in background (365-day chart)
  fetchReport(marketId);  // async, not awaited

  // 3. UI updates automatically when fresh data arrives
  //    (Zustand re-renders components when state changes)
}

// fetchReport implementation
async function fetchReport(ticker: string) {
  const cached = getCurrentCachedData(ticker);  // 30 days

  try {
    const fresh = await api.getFullReport(ticker);  // 365 days

    // Merge: Keep cached data, upgrade to fresh if better
    const merged = {
      priceHistory:
        fresh.priceHistory.length > cached.priceHistory.length
          ? fresh.priceHistory
          : cached.priceHistory,
    };

    updateState(merged);
  } catch (error) {
    // On error, cached data still shows
    console.error('Failed to fetch fresh data, showing cached');
  }
}
```

### Benefits
- ✅ Instant feedback
- ✅ Graceful degradation (cached data if API fails)
- ✅ Progressive enhancement (fast → better)

### When NOT to Use
- ✗ Security-critical data (always need fresh)
- ✗ Financial transactions (stale data dangerous)
- ✗ Real-time collaborative editing

**Real-World Example**: `frontend/twinbar/src/stores/marketStore.ts:fetchReport()` preserves cached chart while fetching full report

---

## Optimistic UI Updates

**Principle**: Update UI immediately with predicted/cached data, then reconcile with server response.

### Why It Matters
- Responsive UI (no waiting)
- Better perceived performance
- Smoother user experience
- Handles network latency

### Example

```typescript
// ✅ GOOD: Optimistic update
function handleVote(marketId: string, vote: 'yes' | 'no') {
  // 1. Update UI immediately (optimistic)
  updateMarketLocally(marketId, (market) => ({
    ...market,
    userVote: vote,
    yesVotes: vote === 'yes' ? market.yesVotes + 1 : market.yesVotes,
  }));

  // 2. Send to server (async)
  api.submitVote(marketId, vote)
    .then((serverResponse) => {
      // 3. Reconcile with server truth
      updateMarketFromServer(marketId, serverResponse);
    })
    .catch((error) => {
      // 4. Rollback on error
      revertMarketUpdate(marketId);
      showError('Vote failed, please try again');
    });
}
```

### Pattern Flow

```
1. Apply change locally (optimistic)
2. Send request to server
3. On success: reconcile with server response
4. On failure: rollback + show error
```

### When to Use
- ✓ User actions (votes, likes, toggles)
- ✓ Form submissions
- ✓ Adding/deleting items from lists

**See Also**: TanStack React Query's `optimisticUpdate` for automated optimistic updates with rollback.

---

## Summary: Pattern Selection

| Scenario | Pattern |
|----------|---------|
| Selecting item from list | Normalized State (ID + selector) |
| Multiple components need same data | Single Source of Truth (Zustand store) |
| API might return partial data | Intelligent Merge Strategy |
| Data should never shrink | Monotonic Data Invariants |
| Slow API, need instant UI | Stale-While-Revalidate |
| User action, need responsive UI | Optimistic UI Updates |

---

## References

- **Testing these patterns**: See [TESTING.md](TESTING.md)
- **React/Zustand specifics**: See [REACT-PATTERNS.md](REACT-PATTERNS.md)
- **Anti-patterns**: See [ANTI-PATTERNS.md](ANTI-PATTERNS.md)
- **Complete guide**: `docs/frontend/UI_PRINCIPLES.md`
