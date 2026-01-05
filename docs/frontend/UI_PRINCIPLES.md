# UI/Frontend Development Principles

This document captures principles and patterns discovered through building the Telegram Mini App frontend (Twinbar). These are **hard-won lessons** from real bugs, performance issues, and architectural challenges.

**Tech Stack:**
- React 19 + TypeScript
- Zustand (state management)
- TanStack React Query (server state)
- Tailwind CSS 4 + Headless UI
- Recharts (charting)
- Vitest + Testing Library + fast-check

---

## Table of Contents

- [State Management](#state-management)
  - [Normalized State Pattern](#normalized-state-pattern)
  - [Single Source of Truth](#single-source-of-truth)
  - [Intelligent Merge Strategies](#intelligent-merge-strategies)
  - [Monotonic Data Invariants](#monotonic-data-invariants)
- [Data Flow Patterns](#data-flow-patterns)
  - [Stale-While-Revalidate](#stale-while-revalidate)
  - [Optimistic UI Updates](#optimistic-ui-updates)
- [Testing Principles](#testing-principles)
  - [Property-Based Testing](#property-based-testing)
  - [Invariant-Based Testing](#invariant-based-testing)
  - [Generative Test Case Strategy](#generative-test-case-strategy)
  - [Test-Driven Bug Fixing](#test-driven-bug-fixing)
- [React/TypeScript Patterns](#reacttypescript-patterns)
  - [TypeScript Prop Interfaces](#typescript-prop-interfaces)
  - [Zustand State Management](#zustand-state-management)
  - [Component Composition](#component-composition)
- [Data Visualization Principles](#data-visualization-principles)
  - [Visual Prominence Through Layering](#visual-prominence-through-layering)
  - [Domain Compatibility for Mathematical Correctness](#domain-compatibility-for-mathematical-correctness)
  - [Framework-Native Over Custom Solutions](#framework-native-over-custom-solutions)
  - [Edge Cases Reveal Mathematical Bugs](#edge-cases-reveal-mathematical-bugs)
  - [Progressive Evidence for UI Validation](#progressive-evidence-for-ui-validation)
- [Anti-Patterns to Avoid](#anti-patterns-to-avoid)
- [Real-World Case Study](#real-world-case-study)
- [References](#references)

---

## State Management

### Normalized State Pattern

**Principle:** Store entity IDs instead of object copies. Derive data from a single source of truth via selectors.

**Why It Matters:**
- Eliminates entire class of "stale copy" bugs
- Automatic updates when source data changes
- Simpler mental model (one source, multiple views)
- No need to manually sync multiple copies

**Example Problem (Object Copy):**

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

**Solution (Normalized State):**

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

**Benefits:**
- ✅ No stale data
- ✅ One source of truth
- ✅ Automatic updates
- ✅ Less memory (store ID not full object)

**When to Use:**
- ✓ Selecting items from lists
- ✓ Master-detail views
- ✓ Any case where you "copy" data from one place to another

**See Real-World Example:** `frontend/twinbar/src/stores/marketStore.ts` (refactored from object copy to ID reference)

---

### Single Source of Truth

**Principle:** Each piece of data should have exactly one canonical location. All other views derive from that source.

**Why It Matters:**
- No synchronization bugs
- Clear ownership of data
- Easy to reason about data flow
- Simpler debugging (one place to look)

**Example:**

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

**Pattern:**

```
Source (markets[])
  ↓
Selector (getSelectedMarket)
  ↓
Component (displays derived data)
```

**Rule of Thumb:** If you find yourself calling `setState` to "sync" two pieces of data, you probably need a single source + selector pattern instead.

---

### Intelligent Merge Strategies

**Principle:** When updating state from API, preserve valuable cached data. Only overwrite if new data is demonstrably better (non-empty AND larger/fresher).

**Why It Matters:**
- Robust against partial API failures
- Handles degraded responses gracefully
- Prevents data loss from race conditions
- Better UX during API errors

**Example Problem:**

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

**Solution:**

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

**Pattern:**

```typescript
// Merge strategy template
newData && newData.length > cachedData.length
  ? newData      // Upgrade to better data
  : cachedData   // Preserve what we have
```

**When to Use:**
- ✓ Updating from slow/unreliable APIs
- ✓ Merging cached + fresh data
- ✓ Any case where API might return partial data

**See Real-World Example:** `frontend/twinbar/src/stores/marketStore.ts:fetchReport()` (lines 276-289)

---

### Monotonic Data Invariants

**Principle:** Some data structures should only grow or stay the same, never shrink. Enforce this via merge logic and property-based tests.

**Why It Matters:**
- Predictable behavior (data never disappears)
- Catches API bugs (partial responses detected)
- Documented guarantees (invariants are promises)
- Regression prevention (tests enforce it)

**Example:**

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

**Testing the Invariant:**

```typescript
import * as fc from 'fast-check';

it('INVARIANT: price_history never shrinks', () => {
  fc.assert(
    fc.property(
      // Generate random sequences of updates
      fc.array(
        fc.record({
          newData: fc.array(fc.anything(), { maxLength: 365 }),
          shouldBeEmpty: fc.boolean(),
        })
      ),
      (updates) => {
        let currentLength = 0;

        for (const update of updates) {
          const merged = updatePriceHistory(update.newData, currentData);
          const newLength = merged.length;

          // INVARIANT: Never shrinks
          if (currentLength > 0 && newLength < currentLength) {
            return false;  // Violation!
          }

          currentLength = newLength;
        }

        return true;  // Invariant held
      }
    ),
    { numRuns: 1000 }  // 1000 random test cases
  );
});
```

**Common Monotonic Data:**
- Price history (never shrink chart data)
- Event logs (never delete history)
- Cached API responses (never reduce cache size)
- Aggregated metrics (only add, never remove)

**See Real-World Example:** `frontend/twinbar/src/stores/marketStore.test.ts` (property-based tests for chart monotonicity)

---

## Data Flow Patterns

### Stale-While-Revalidate

**Principle:** Show cached data immediately for instant UI feedback, then fetch fresh data in background and upgrade UI when it arrives.

**Why It Matters:**
- Perceived performance (instant UI)
- Better UX (users don't wait)
- Handles slow APIs gracefully
- Progressive enhancement (fast → slow)

**Pattern:**

```
User Action
  ↓
1. Show cached data (instant)
  ↓
2. Fetch fresh data (background)
  ↓
3. Update UI when fresh data arrives
```

**Example:**

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

**Benefits:**
- ✅ Instant feedback
- ✅ Graceful degradation (cached data if API fails)
- ✅ Progressive enhancement (fast → better)

**When NOT to Use:**
- ✗ Security-critical data (always need fresh)
- ✗ Financial transactions (stale data dangerous)
- ✗ Real-time collaborative editing

**See Real-World Example:** `frontend/twinbar/src/stores/marketStore.ts:fetchReport()` preserves cached chart while fetching full report

---

### Optimistic UI Updates

**Principle:** Update UI immediately with predicted/cached data, then reconcile with server response.

**Why It Matters:**
- Responsive UI (no waiting)
- Better perceived performance
- Smoother user experience
- Handles network latency

**Example:**

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

**Pattern:**

```
1. Apply change locally (optimistic)
2. Send request to server
3. On success: reconcile with server response
4. On failure: rollback + show error
```

**When to Use:**
- ✓ User actions (votes, likes, toggles)
- ✓ Form submissions
- ✓ Adding/deleting items from lists

**See Also:** TanStack React Query's `optimisticUpdate` for automated optimistic updates with rollback.

---

## Testing Principles

### Property-Based Testing

**Principle:** Instead of writing individual test cases, generate random test inputs and verify invariants always hold.

**Why It Matters:**
- Finds edge cases you wouldn't think of
- Tests behavior, not specific scenarios
- Scales better (1000+ test cases from one property)
- Documents system invariants

**Traditional Example-Based Testing:**

```typescript
// ❌ Limited: Only tests specific cases
it('merge preserves data', () => {
  const cached = [{ date: '2024-01-01', price: 100 }];
  const fresh = [];

  const result = merge(fresh, cached);
  expect(result).toEqual(cached);
});

// Only tests ONE scenario: empty fresh data
// What about: partial fresh data? Larger fresh data?
```

**Property-Based Testing:**

```typescript
import * as fc from 'fast-check';

// ✅ GOOD: Tests ALL scenarios
it('merge never shrinks data', () => {
  fc.assert(
    fc.property(
      // Generate random cached data
      fc.array(fc.record({
        date: fc.date(),
        price: fc.float({ min: 0, max: 1000 }),
      })),

      // Generate random fresh data
      fc.array(fc.record({
        date: fc.date(),
        price: fc.float({ min: 0, max: 1000 }),
      })),

      (cached, fresh) => {
        const result = merge(fresh, cached);

        // PROPERTY: Result never smaller than cached
        return result.length >= cached.length;
      }
    ),
    { numRuns: 1000 }  // Test 1000 random combinations!
  );
});
```

**Benefits:**
- ✅ Found a bug: merge() was shrinking data when `fresh.length < cached.length` but `fresh.length > 0`
- ✅ This scenario never appeared in manual tests
- ✅ 1000 test cases from 10 lines of code

**Common Properties to Test:**
- Monotonicity: `output.length >= input.length`
- Idempotence: `f(f(x)) === f(x)`
- Commutativity: `f(a, b) === f(b, a)`
- Reversibility: `decode(encode(x)) === x`

**Tools:**
- `fast-check` (JavaScript/TypeScript)
- `hypothesis` (Python)
- `QuickCheck` (Haskell, the original)

---

### Invariant-Based Testing

**Principle:** Define properties that must ALWAYS be true, regardless of input. Test these properties hold under all conditions.

**Why It Matters:**
- Documents system guarantees
- Catches subtle bugs
- Survives refactoring (tests behavior, not implementation)
- Self-documenting (invariants are promises)

**Example Invariants:**

```typescript
// INVARIANT 1: selectedTicker always corresponds to market in markets[]
it('INVARIANT: selectedTicker always valid or null', () => {
  fc.assert(
    fc.property(
      // Generate random sequences of actions
      fc.array(fc.oneof(
        fc.record({ action: fc.constant('SELECT'), ticker: fc.string() }),
        fc.record({ action: fc.constant('CLEAR') }),
        fc.record({ action: fc.constant('UPDATE_MARKETS'), tickers: fc.array(fc.string()) }),
      )),
      (actions) => {
        const store = createStore();

        for (const action of actions) {
          if (action.action === 'SELECT') {
            store.setSelectedTicker(action.ticker);
          } else if (action.action === 'CLEAR') {
            store.setSelectedTicker(null);
          } else if (action.action === 'UPDATE_MARKETS') {
            store.setMarkets(action.tickers.map(t => ({ id: t })));
          }

          // INVARIANT CHECK after each action
          const selectedTicker = store.selectedTicker;
          const markets = store.markets;
          const selectedMarket = store.getSelectedMarket();

          if (selectedTicker !== null) {
            const marketExists = markets.some(m => m.id === selectedTicker);

            // INVARIANT 1: If ticker is set but doesn't exist, getSelectedMarket returns null
            if (!marketExists && selectedMarket !== null) {
              return false;  // Violation!
            }

            // INVARIANT 2: If ticker exists, getSelectedMarket returns it
            if (marketExists && selectedMarket === null) {
              return false;  // Violation!
            }
          }
        }

        return true;  // All invariants held
      }
    )
  );
});
```

**Common Invariants:**
- **Data integrity:** `price_history.length` never decreases
- **State validity:** `selectedItem` always in `items[]` or `null`
- **Referential integrity:** All IDs reference valid entities
- **Type safety:** Fields always have expected types

**Pattern:**

```typescript
1. Define invariant as boolean property
2. Generate random state transitions
3. Check invariant holds after EACH transition
4. Return false on first violation
```

---

### Generative Test Case Strategy

**Principle:** Don't write individual test cases for every scenario. Write generators that produce varied inputs, let tool find counterexamples.

**Why It Matters:**
- Tests scale better (maintain 1 property, get 1000+ test cases)
- Finds unexpected interactions
- Less maintenance burden
- Better coverage of input space

**Example:**

```typescript
// ❌ BAD: Manual test cases
it('handles empty array', () => { /* test */ });
it('handles single item', () => { /* test */ });
it('handles two items', () => { /* test */ });
it('handles 100 items', () => { /* test */ });
it('handles negative numbers', () => { /* test */ });
it('handles zero', () => { /* test */ });
// 100 more manual cases...

// ✅ GOOD: Generative strategy
it('PROPERTY: sort is stable', () => {
  fc.assert(
    fc.property(
      fc.array(fc.integer()),  // Generate ANY array of integers
      (arr) => {
        const sorted = mySort(arr);

        // Property: Adjacent elements are in order
        for (let i = 0; i < sorted.length - 1; i++) {
          if (sorted[i] > sorted[i + 1]) {
            return false;
          }
        }

        return true;
      }
    ),
    { numRuns: 1000 }
  );
});
```

**Generators in fast-check:**

```typescript
// Basic types
fc.integer({ min: 0, max: 100 })
fc.float({ min: 0, max: 1 })
fc.string({ minLength: 1, maxLength: 20 })
fc.boolean()
fc.date({ min: new Date('2024-01-01'), max: new Date('2024-12-31') })

// Composite types
fc.array(fc.integer(), { minLength: 0, maxLength: 100 })
fc.record({
  id: fc.string(),
  price: fc.float({ min: 0 }),
  date: fc.date(),
})

// Constrained values
fc.constantFrom('yes', 'no', 'maybe')
fc.oneof(fc.integer(), fc.string(), fc.boolean())

// Custom generators
const marketGenerator = fc.record({
  id: fc.string({ minLength: 3, maxLength: 10 }),
  price: fc.float({ min: 10, max: 1000 }),
  volume: fc.integer({ min: 1000, max: 1000000 }),
});
```

---

### Test-Driven Bug Fixing

**Principle:** When you find a bug, write a property test that fails, fix the implementation to make it pass, test now guards against regression.

**Why It Matters:**
- Bugs become test cases
- Regression prevention built-in
- Documents the bug and fix
- Forces you to understand root cause

**Workflow:**

```
1. Bug discovered: Chart data disappearing
   ↓
2. Write failing property test:
   it('INVARIANT: price_history never shrinks', () => {
     // Test fails with current implementation
   })
   ↓
3. Fix implementation:
   Upgrade merge logic to enforce monotonicity
   ↓
4. Test passes
   ↓
5. Bug can never come back (test guards it)
```

**Real Example from Chart Display Bug:**

```typescript
// STEP 1: Bug found
// User reports: "Chart shows 30 days, then disappears when API returns"

// STEP 2: Write failing test
it('INVARIANT: price_history never shrinks', () => {
  fc.assert(
    fc.property(
      fc.array(fc.record({
        priceHistory: fc.array(fc.anything()),
        shouldBeEmpty: fc.boolean(),
      })),
      (updates) => {
        let currentLength = 0;

        for (const update of updates) {
          const merged = merge(update.priceHistory, currentData);
          const newLength = merged.length;

          // FAILS: Sometimes newLength < currentLength
          if (currentLength > 0 && newLength < currentLength) {
            return false;
          }

          currentLength = newLength;
        }

        return true;
      }
    )
  );
});
// Test FAILS with counterexample: [30 items] → [10 items]

// STEP 3: Fix implementation
function merge(fresh, cached) {
  // OLD (buggy):
  // return fresh.length > 0 ? fresh : cached;

  // NEW (fixed):
  return fresh.length > cached.length ? fresh : cached;
}

// STEP 4: Test passes

// STEP 5: Bug can never come back!
```

---

## React/TypeScript Patterns

### TypeScript Prop Interfaces

**Principle:** Define strict interfaces for component props. Use literal types for fixed values.

**Why It Matters:**
- Type safety (catch errors at compile time)
- IDE autocomplete
- Self-documenting (interface is the contract)
- Refactoring safety

**Example:**

```typescript
// ✅ GOOD: Strict prop interface
interface ChartProps {
  data: PriceDataPoint[];  // Required
  indicators?: {           // Optional, but when present has shape
    sma20?: boolean;
    sma50?: boolean;
    rsi?: boolean;
  };
  isLoading?: boolean;
  onDataPointClick?: (point: PriceDataPoint) => void;
  theme?: 'light' | 'dark';  // Literal type
}

function Chart({ data, indicators, isLoading = false, onDataPointClick, theme = 'light' }: ChartProps) {
  // TypeScript knows exact types, IDE autocompletes
}

// Usage
<Chart
  data={priceHistory}
  indicators={{ sma20: true }}
  theme="dark"  // Autocompletes: 'light' | 'dark'
/>
```

**Patterns:**

```typescript
// Optional props with defaults
interface Props {
  required: string;
  optional?: boolean;
}

function Component({ required, optional = false }: Props) { }

// Literal types for constrained values
interface Props {
  size: 'sm' | 'md' | 'lg';
  variant: 'primary' | 'secondary' | 'danger';
}

// Union types for flexible props
interface Props {
  value: string | number | null;
}

// Generic components
interface ListProps<T> {
  items: T[];
  renderItem: (item: T) => React.ReactNode;
}

function List<T>({ items, renderItem }: ListProps<T>) {
  return <>{items.map(renderItem)}</>;
}
```

**See Also:** `frontend/twinbar/src/components/FullChart.tsx` for real-world TypeScript prop interfaces

---

### Zustand State Management

**Principle:** Use Zustand for global UI state with immutable updates. Selectors for derived data. `getState()` for reading fresh state.

**Why It Matters:**
- Lightweight (no Provider wrapping needed)
- Simple API (just `create()` and hooks)
- Predictable updates (immutable patterns)
- Easy debugging (DevTools support)

**Basic Pattern:**

```typescript
import { create } from 'zustand';

interface AppState {
  // State
  count: number;
  user: User | null;

  // Actions
  increment: () => void;
  setUser: (user: User) => void;

  // Selectors (derived data)
  isLoggedIn: () => boolean;
}

const useStore = create<AppState>((set, get) => ({
  // Initial state
  count: 0,
  user: null,

  // Actions
  increment: () => set((state) => ({ count: state.count + 1 })),
  setUser: (user) => set({ user }),

  // Selectors
  isLoggedIn: () => get().user !== null,
}));

// Use in component
function Counter() {
  const count = useStore((state) => state.count);
  const increment = useStore((state) => state.increment);

  return <button onClick={increment}>{count}</button>;
}
```

**Reading Fresh State:**

```typescript
// Inside async function or event handler
async function handleAction() {
  // ✅ GOOD: Read fresh state
  const currentState = useStore.getState();
  const { markets, selectedTicker } = currentState;

  // Do work with current state
}

// ❌ BAD: Using stale closure
const markets = useStore(state => state.markets);  // Captured at render
async function handleAction() {
  // markets might be stale here!
}
```

**Selector Pattern:**

```typescript
// Derive data from source
const useStore = create<AppState>((set, get) => ({
  markets: [],
  selectedTicker: null,

  // Selector: Always returns fresh derived data
  getSelectedMarket: () => {
    const { markets, selectedTicker } = get();
    if (!selectedTicker) return null;
    return markets.find(m => m.id === selectedTicker) || null;
  },
}));

// Use in component
const selectedMarket = useStore(state => state.getSelectedMarket());
```

**See Real-World Example:** `frontend/twinbar/src/stores/marketStore.ts`

---

### Component Composition

**Principle:** Small, focused components with single responsibility. Compose complex UI from simple pieces. Props for configuration, children for content.

**Why It Matters:**
- Reusability (components like LEGO blocks)
- Testability (small components easier to test)
- Maintainability (change one, don't break others)
- Separation of concerns

**Example:**

```typescript
// ✅ GOOD: Composed components

// Small, focused components
function Card({ children, className }: { children: React.ReactNode; className?: string }) {
  return (
    <div className={`border rounded-lg p-4 ${className}`}>
      {children}
    </div>
  );
}

function CardHeader({ children }: { children: React.ReactNode }) {
  return <div className="font-bold mb-2">{children}</div>;
}

function CardBody({ children }: { children: React.ReactNode }) {
  return <div>{children}</div>;
}

// Compose into complex UI
function MarketCard({ market }: { market: Market }) {
  return (
    <Card className="hover:shadow-lg">
      <CardHeader>
        {market.title}
      </CardHeader>
      <CardBody>
        <PriceDisplay price={market.price} />
        <MiniChart data={market.priceHistory} />
        <SocialProof data={market.socialProof} />
      </CardBody>
    </Card>
  );
}
```

**Composition Patterns:**

```typescript
// 1. Props for configuration
<Button variant="primary" size="lg" />

// 2. Children for content
<Card>
  <CardHeader>Title</CardHeader>
  <CardBody>Content</CardBody>
</Card>

// 3. Render props for flexibility
<List
  items={markets}
  renderItem={(market) => <MarketCard market={market} />}
/>

// 4. Compound components
<Tabs>
  <Tab label="Overview" />
  <Tab label="Details" />
</Tabs>
```

**Avoid Prop Drilling:**

```typescript
// ❌ BAD: Prop drilling
<App user={user} theme={theme} locale={locale} />
  → <Dashboard user={user} theme={theme} locale={locale} />
    → <Sidebar user={user} theme={theme} />
      → <UserMenu user={user} theme={theme} />

// ✅ GOOD: Context for global values
const ThemeContext = createContext('light');
const UserContext = createContext(null);

function App() {
  return (
    <ThemeContext.Provider value={theme}>
      <UserContext.Provider value={user}>
        <Dashboard />
      </UserContext.Provider>
    </ThemeContext.Provider>
  );
}

function UserMenu() {
  const theme = useContext(ThemeContext);
  const user = useContext(UserContext);
  // No prop drilling!
}

// Or use Zustand for global state
const user = useStore(state => state.user);
```

---

## Data Visualization Principles

### Visual Prominence Through Layering

**Principle:** Use shaded regions (fills) + bold trendlines + layer ordering for visual hierarchy in data visualizations.

**Why It Matters:**
- Simple lines blend into busy charts (low contrast)
- Shaded areas create immediate pattern recognition
- Layer ordering ensures important elements always visible
- Matches user expectations from professional tools

**Context:** Time-series charts, technical analysis, pattern overlays

**Example Problem:**

```javascript
// ❌ BAD: Simple thin lines blend into chart
datasets.push({
    type: 'line',
    data: trendlinePoints,
    borderColor: '#FF6B6B',
    borderWidth: 2,  // Too thin
});
// Pattern hard to see against candlesticks
```

**Solution:**

```javascript
// ✅ GOOD: Shaded region + bold trendline with layering
// 1. Fill layer (rendered behind)
datasets.push({
    type: 'line',
    label: 'Pattern Area',
    data: polygonPoints,
    backgroundColor: 'rgba(38, 166, 154, 0.25)',  // 25% opacity
    fill: true,
    borderColor: 'transparent',
    order: 3,  // Behind trendlines
    pointRadius: 0
});

// 2. Trendline layer (rendered in front of fill)
datasets.push({
    type: 'line',
    label: 'Trendline',
    data: trendlinePoints,
    borderColor: '#26A69A',
    borderWidth: 3,  // Bold (3px)
    fill: false,
    order: 2,  // In front of fill
    pointRadius: 0
});

// 3. Data layer (highest priority - always visible)
datasets.push({
    type: 'candlestick',
    data: ohlcData,
    order: 1  // Front-most layer
});
```

**Visual Hierarchy:**

```
Layer 1 (order: 1) - Data (candlesticks) - Always visible
Layer 2 (order: 2) - Overlays (trendlines) - Clear boundaries
Layer 3 (order: 3) - Fills (shaded areas) - Context/emphasis
Layer 4 (order: 4) - Background (support/resistance) - Context
```

**Opacity Guidelines:**

- **Web displays**: 25-30% opacity for visibility
- **Print/paper**: 10-15% opacity sufficient (different medium)
- **Test on actual medium** (screenshots on screen, not code)

**Benefits:**
- ✅ Patterns 3-5x more visually prominent
- ✅ Immediate pattern recognition
- ✅ Matches industry standards (TradingView, mplfinance)
- ✅ Candlesticks remain fully visible

**When to Use:**
- ✓ Overlaying patterns on time-series charts
- ✓ Highlighting regions of interest
- ✓ Showing confidence bands
- ✓ Any visualization where context matters

**Anti-pattern:**
```javascript
// ❌ All layers same order (unpredictable z-index)
datasets.push({ order: 1 });  // Fill
datasets.push({ order: 1 });  // Line
datasets.push({ order: 1 });  // Data
// Random rendering order!
```

**See Also:** `.claude/implementations/2026-01-05-shaded-pattern-visualization.md`

---

### Domain Compatibility for Mathematical Correctness

**Principle:** Mathematical operations (regression, interpolation) must use the same domain as the visualization axis.

**Why It Matters:**
- Domain mismatch creates visual artifacts
- Regression with wrong domain produces wavy lines
- Breaks at irregular data spacing (weekend gaps, holidays)
- Mathematical correctness ≠ visual correctness without domain match

**Context:** Any chart with mathematical overlays (trendlines, moving averages, regressions)

**Example Problem:**

```javascript
// ❌ BAD: Index-based regression on continuous time axis
function fitLinearTrendline(points) {
    const n = points.length;

    // BUG: Using array indices (0,1,2,3) for X
    const sumX = points.reduce((sum, p, i) => sum + i, 0);
    const sumXY = points.reduce((sum, p, i) => sum + i * p.y, 0);
    const sumX2 = points.reduce((sum, p, i) => sum + i * i, 0);

    const slope = (n * sumXY - sumX * sumY) / (n * sumX2 - sumX * sumX);
    const intercept = (sumY - slope * sumX) / n;

    // Returns Y calculated from indices, but X uses timestamps
    return points.map((p, i) => ({
        x: p.x,                    // Real timestamp (milliseconds)
        y: slope * i + intercept   // Index-based Y - DOMAIN MISMATCH!
    }));
}

// Chart configuration
scales: {
    x: {
        type: 'time',  // Continuous calendar time (includes weekends)
    }
}

// Result: Lines appear wavy at weekend gaps
// Why: Y assumes uniform spacing (indices), but X has variable spacing (time)
```

**Visual Impact:**

```
Price Chart (continuous time axis):
Mon  Tue  Wed  [weekend gap]  Mon  Tue
 •    •    •                    •    •
  \    \    \                  /  /    ← Line "bends" at gap
   Index: 0→1→2              →3→4

Spacing in indices: 1 day, 1 day, 1 day, 1 day
Spacing on X-axis:  1 day, 1 day, 3 days, 1 day (gap!)
Result: Line slope changes at gap (looks wavy)
```

**Solution:**

```javascript
// ✅ GOOD: Timestamp-based regression matches time axis
function fitLinearTrendline(points) {
    const n = points.length;

    // Use actual timestamps (p.x) for X domain
    const sumX = points.reduce((sum, p) => sum + p.x, 0);
    const sumXY = points.reduce((sum, p) => sum + p.x * p.y, 0);
    const sumX2 = points.reduce((sum, p) => sum + p.x * p.x, 0);

    const slope = (n * sumXY - sumX * sumY) / (n * sumX2 - sumX * sumX);
    const intercept = (sumY - slope * sumX) / n;

    // Y calculated from timestamps - DOMAIN MATCH!
    return points.map((p) => ({
        x: p.x,                      // Real timestamp
        y: slope * p.x + intercept   // Timestamp-based Y
    }));
}

// Result: Lines stay straight across weekend gaps
```

**Domain Compatibility Rule:**

```
Regression domain MUST match visualization axis domain

Continuous time axis → Use timestamps in regression
Discrete index axis  → Use indices in regression
Mixed domains        → Convert to common domain first
```

**Testing Strategy:**

```javascript
// Test with irregular spacing (weekend gaps)
const testData = [
    { x: Date.parse('2024-01-01'), y: 100 },  // Mon
    { x: Date.parse('2024-01-02'), y: 102 },  // Tue
    { x: Date.parse('2024-01-03'), y: 104 },  // Wed
    // Weekend gap (Thu, Fri, Sat, Sun missing)
    { x: Date.parse('2024-01-08'), y: 106 },  // Mon (5 days later!)
    { x: Date.parse('2024-01-09'), y: 108 },  // Tue
];

const trendline = fitLinearTrendline(testData);

// Visual inspection: Line should stay straight across gap
// If wavy → domain mismatch bug
```

**Common Domain Mismatches:**

| Axis Type | Correct Domain | Wrong Domain | Symptom |
|-----------|---------------|--------------|---------|
| Continuous time | Timestamps (ms) | Array indices | Wavy at gaps |
| Discrete categories | Category indices | Alphabetical | Wrong ordering |
| Log scale | Log-transformed values | Raw values | Curved line |
| Polar coordinates | Angles (radians) | Linear spacing | Spiral artifacts |

**Benefits:**
- ✅ Mathematically correct trendlines
- ✅ Straight lines across irregular spacing
- ✅ Matches professional tools
- ✅ No visual artifacts

**Anti-pattern:**
```javascript
// ❌ Assuming domains are equivalent
// "Indices and timestamps are basically the same, right?"
// NO! Domain mismatch causes subtle but critical bugs
```

**See Also:** `.claude/implementations/2026-01-05-proper-pattern-trendlines-all-types.md`

---

### Framework-Native Over Custom Solutions

**Principle:** Use charting framework's built-in features instead of custom implementations.

**Why It Matters:**
- Native features are optimized and tested
- Documentation available
- Less code to maintain
- Fewer edge case bugs
- Framework updates benefit you

**Context:** Chart.js, D3.js, Recharts, any visualization library

**Example Problem:**

```javascript
// ❌ BAD: Custom polygon fill implementation
function createPolygonFill(upperLine, lowerLine) {
    // Concatenate upper + reversed lower to create closed polygon
    const polygonData = [
        ...upperLine,
        ...lowerLine.slice().reverse()
    ];

    return {
        type: 'line',
        data: polygonData,
        fill: true,  // Expects polygon to auto-close
        borderColor: 'transparent'
    };
}

// Result: Doesn't render correctly in Chart.js
// Why: Chart.js doesn't handle concatenated polygon arrays this way
```

**Solution:**

```javascript
// ✅ GOOD: Chart.js dataset-to-dataset fill (native feature)
const datasets = [];

// 1. Draw lower boundary first
const lowerIndex = datasets.length;
datasets.push({
    type: 'line',
    label: 'Lower Boundary',
    data: lowerLine,
    borderColor: '#26A69A',
    borderWidth: 3,
    fill: false,  // No fill on this dataset
    order: 2
});

// 2. Draw upper boundary with fill TO lower boundary
datasets.push({
    type: 'line',
    label: 'Upper Boundary',
    data: upperLine,
    borderColor: '#26A69A',
    borderWidth: 3,
    backgroundColor: 'rgba(38, 166, 154, 0.25)',
    fill: lowerIndex,  // Fill to dataset at index (Chart.js native)
    order: 2
});

// Chart.js handles the fill rendering automatically
```

**Research Pattern:**

Before implementing custom solution:

1. **Read framework docs** - "How to fill between lines in Chart.js?"
2. **Check examples** - Official examples often show the pattern
3. **Search issues** - GitHub issues reveal common patterns
4. **Prefer configuration over code** - Declarative > imperative

**Benefits:**
- ✅ Works reliably (framework-tested)
- ✅ Future-proof (framework updates maintain compatibility)
- ✅ Less code (50 lines custom → 2 config properties)
- ✅ Better performance (framework optimized)

**Pattern Recognition:**

```
If you're writing complex code → Framework probably has built-in feature
If you're fighting the framework → You're probably doing it wrong
If documentation seems lacking → You're looking in wrong section
```

**When Custom Is Acceptable:**
- ✓ Framework doesn't support use case (verify first!)
- ✓ Performance critical and framework too slow (profile first!)
- ✓ Very domain-specific calculation (not visualization itself)

**Anti-pattern:**
```javascript
// ❌ Reimplementing what framework provides
// "I'll just build my own zoom/pan/tooltip/legend system"
// Framework has this! Use it!
```

**See Also:** Chart.js `fill` documentation, D3.js `area` generators

---

### Edge Cases Reveal Mathematical Bugs

**Principle:** Test visualizations with irregular data (gaps, holidays, missing values) to verify mathematical correctness.

**Why It Matters:**
- Regular spacing hides domain mismatches
- Irregular spacing reveals bugs immediately
- Visual inspection alone insufficient
- "Looks okay" ≠ mathematically correct

**Context:** Any time-series visualization with mathematical operations

**Example Edge Cases:**

```javascript
// 1. Weekend gaps (financial data)
const weekendGapData = [
    { date: '2024-01-01', value: 100 },  // Monday
    { date: '2024-01-02', value: 102 },  // Tuesday
    { date: '2024-01-03', value: 104 },  // Wednesday
    // Weekend: Thu, Fri, Sat, Sun missing
    { date: '2024-01-08', value: 106 },  // Monday (5 days later!)
];

// 2. Holidays (irregular gaps)
const holidayData = [
    { date: '2024-12-23', value: 100 },
    { date: '2024-12-24', value: 102 },
    // Christmas break: 4 days missing
    { date: '2024-12-30', value: 106 },
];

// 3. Missing data points
const missingData = [
    { date: '2024-01-01', value: 100 },
    { date: '2024-01-02', value: null },  // Missing!
    { date: '2024-01-03', value: 104 },
];

// 4. Variable sampling rates
const variableSampling = [
    { date: '2024-01-01', value: 100 },  // Daily
    { date: '2024-01-02', value: 102 },  // Daily
    { date: '2024-01-10', value: 110 },  // Weekly
    { date: '2024-02-01', value: 120 },  // Monthly
];
```

**Testing Strategy:**

```javascript
// ✅ GOOD: Test with edge case data DURING development
describe('Trendline rendering', () => {
    it('stays straight across weekend gaps', () => {
        const testData = createWeekendGapData();
        const trendline = fitLinearTrendline(testData);

        // Visual test: Render to canvas, check for curvature
        const chart = renderChart({ data: testData, trendline });
        const screenshot = captureScreenshot(chart);

        // Pixel-based test: Line should be straight
        expect(screenshot).toMatchSnapshot();
    });

    it('handles missing data gracefully', () => {
        const testData = createMissingData();
        const trendline = fitLinearTrendline(testData);

        // Should not crash, should skip null values
        expect(trendline).toBeDefined();
        expect(trendline.every(p => p.y !== null)).toBe(true);
    });
});
```

**Validation Checklist:**

- [ ] Test with weekend gaps (financial data)
- [ ] Test with holidays (irregular gaps)
- [ ] Test with missing values (nulls)
- [ ] Test with variable sampling (daily → weekly → monthly)
- [ ] Test with single data point (edge case)
- [ ] Test with two data points (minimum for trend)
- [ ] Test with empty array (boundary case)

**Visual Inspection Pattern:**

```
1. Render chart with edge case data
2. Zoom into gap area
3. Check: Is line straight or wavy?
4. If wavy → Domain mismatch bug
5. If straight → Mathematical correctness verified
```

**Benefits:**
- ✅ Catch bugs before production
- ✅ Verify mathematical correctness
- ✅ Document expected behavior
- ✅ Prevent regressions

**Anti-pattern:**
```javascript
// ❌ Testing only with perfect data
const testData = [
    { date: '2024-01-01', value: 100 },
    { date: '2024-01-02', value: 102 },
    { date: '2024-01-03', value: 104 },
    { date: '2024-01-04', value: 106 },
];
// All perfectly spaced - hides bugs!
```

**Real-World Impact:**

- Bug found: Index-based regression created wavy lines at weekends
- Discovery method: User noticed "lines not straight"
- Prevention: Test with weekend data during development
- Fix: Timestamp-based regression

**See Also:** Property-based testing (generate random gaps), visual regression testing

---

### Progressive Evidence for UI Validation

**Principle:** Verify UI correctness through multiple evidence layers: visual → code → edge cases → mathematical verification.

**Why It Matters:**
- Visual appearance alone doesn't prove correctness
- Screenshots show "looks good" but hide mathematical bugs
- Need multiple validation levels for confidence
- Each layer catches different bug types

**Context:** Data visualizations, charts, mathematical overlays

**Evidence Hierarchy:**

```
Layer 1 (Surface): Visual Inspection
  → Does it LOOK right? (screenshots, manual testing)
  → Catches: Layout issues, color problems, obvious rendering bugs
  → Misses: Mathematical correctness, edge cases

Layer 2 (Content): Code Review
  → Does code use framework correctly? (code patterns, API usage)
  → Catches: Anti-patterns, wrong framework usage
  → Misses: Domain mismatches, algorithm bugs

Layer 3 (Observability): Edge Case Testing
  → Does it work with irregular data? (weekends, gaps, nulls)
  → Catches: Domain bugs, regression errors, brittleness
  → Misses: Subtle mathematical errors

Layer 4 (Ground Truth): Mathematical Verification
  → Is the formula correct? (algorithm analysis, property tests)
  → Catches: Algorithm bugs, numerical errors, domain mismatches
  → Highest confidence level
```

**Example Validation:**

```javascript
// Layer 1: Visual Inspection
console.log('📸 Taking screenshot...');
const screenshot = await captureChart();
// ✅ Pattern visible? ✅ Colors correct? ✅ Layout good?

// Layer 2: Code Review
console.log('🔍 Reviewing code...');
const usesNativeFeatures = checkDatasetToDatasetFill();
// ✅ Using Chart.js fill? ✅ Proper layering? ✅ No mutations?

// Layer 3: Edge Case Testing
console.log('🧪 Testing edge cases...');
const weekendData = createWeekendGapData();
const renderedOk = renderChart(weekendData);
// ✅ No crashes? ✅ Handles nulls? ✅ Lines straight?

// Layer 4: Mathematical Verification
console.log('🔬 Verifying algorithm...');
const regression = fitLinearTrendline(weekendData);
const usesCorrectDomain = verifyTimestampBased(regression);
// ✅ Domain matches axis? ✅ Formula correct? ✅ Numerically stable?

// All layers passed → HIGH CONFIDENCE
```

**Validation Matrix:**

| Layer | Tool | What It Catches | What It Misses | Time Cost |
|-------|------|-----------------|----------------|-----------|
| **L1: Visual** | Screenshots, Manual | Layout, colors | Math bugs | Low (1 min) |
| **L2: Code** | Code review, Linter | Patterns, API misuse | Algorithm errors | Medium (5 min) |
| **L3: Edge** | Unit tests, Edge data | Brittle code | Subtle math errors | Medium (10 min) |
| **L4: Math** | Formula analysis, Property tests | Algorithm bugs | None | High (30 min) |

**Progressive Strategy:**

```
New feature implementation:
1. Start Layer 1 (visual) → Quick feedback loop
2. Progress to Layer 2 (code) → Ensure correct patterns
3. Add Layer 3 (edge) → Verify robustness
4. Finish Layer 4 (math) → Guarantee correctness

Bug investigation (reverse order):
1. Start Layer 4 (math) → Is algorithm wrong?
2. Fallback Layer 3 (edge) → Does it handle gaps?
3. Check Layer 2 (code) → Framework used correctly?
4. Finally Layer 1 (visual) → What does user see?
```

**Benefits:**
- ✅ Multi-layer confidence
- ✅ Different layers catch different bugs
- ✅ Progressive approach (fast → slow, cheap → expensive)
- ✅ Each layer documents expectations

**Anti-pattern:**
```javascript
// ❌ Stopping at Layer 1 (visual only)
console.log('Screenshot looks good! ✅ Ship it!');
// Missing: Code review, edge cases, math verification
// Result: Mathematical bugs in production
```

**Real-World Application:**

```
Trendline Implementation:
L1: ✅ Screenshot shows shaded region (looks good)
L2: ✅ Using Chart.js dataset-to-dataset fill (correct API)
L3: ⚠️  Lines wavy at weekends (edge case revealed bug!)
L4: ❌ Index-based regression on time axis (domain mismatch)

Fix: Update Layer 4 → Timestamp-based regression
Revalidate: L1 ✅ L2 ✅ L3 ✅ L4 ✅ (all layers pass)
```

**See Also:** Progressive Evidence Strengthening (CLAUDE.md Principle #2)

---

## Anti-Patterns to Avoid

### ❌ Stale Object Copies

```typescript
// BAD: Storing copy of object from array
const [selectedMarket, setSelectedMarket] = useState<Market | null>(null);
const [markets, setMarkets] = useState<Market[]>([]);

// User selects market
setSelectedMarket(markets[0]);  // Copy created

// Later, markets update
setMarkets(newMarkets);  // selectedMarket is now stale!

// FIX: Store ID, derive from source
const [selectedId, setSelectedId] = useState<string | null>(null);
const selectedMarket = markets.find(m => m.id === selectedId);
```

### ❌ Prop Drilling

```typescript
// BAD: Passing props through many levels
<App theme={theme}>
  <Dashboard theme={theme}>
    <Sidebar theme={theme}>
      <Menu theme={theme}>
        <MenuItem theme={theme} />  // 5 levels deep!
      </Menu>
    </Sidebar>
  </Dashboard>
</App>

// FIX: Context or global state
const theme = useTheme();  // From context or Zustand
```

### ❌ Object Spreading Without Merge Logic

```typescript
// BAD: Blindly replace entire object
const updatedMarket = {
  ...existingMarket,
  report: newReport,  // Might be empty!
};

// FIX: Intelligent merge
const updatedMarket = {
  ...existingMarket,
  report: {
    ...existingMarket.report,
    ...newReport,
    // Preserve valuable fields if new data is empty
    priceHistory:
      newReport.priceHistory?.length > 0
        ? newReport.priceHistory
        : existingMarket.report?.priceHistory || [],
  },
};
```

### ❌ Mutating State Directly

```typescript
// BAD: Mutating array
markets.push(newMarket);  // Mutates original!
setMarkets(markets);      // React might not detect change

// FIX: Immutable update
setMarkets([...markets, newMarket]);

// BAD: Mutating object
market.price = 100;  // Mutates!
setMarket(market);   // React might not detect

// FIX: Create new object
setMarket({ ...market, price: 100 });
```

---

## Real-World Case Study

**Problem:** Price charts disappeared in modal when API returned partial data.

**Root Cause:** Merge logic replaced cached 30-day chart data with empty array from slow-loading API.

**Solution Applied:**

1. **Normalized State Pattern**
   - Changed from `selectedMarket: Market | null` to `selectedTicker: string | null`
   - Derived market via selector `getSelectedMarket()`
   - Eliminated stale data bugs

2. **Intelligent Merge Strategies**
   - Modified `fetchReport()` to preserve cached data when new data is empty or smaller
   - Only replace if new data demonstrably better (larger length)

3. **Monotonic Data Invariants**
   - Enforced: `price_history.length` never decreases
   - Added property-based tests to verify invariant

4. **Property-Based Testing**
   - Created tests with fast-check generating 1000+ random scenarios
   - Found edge case: API returning smaller (but non-empty) data was shrinking chart
   - Upgraded merge logic to handle this case

**Files Modified:**
- `frontend/twinbar/src/stores/marketStore.ts` - Normalized state + intelligent merge
- `frontend/twinbar/src/App.tsx` - Use selector pattern
- `frontend/twinbar/src/stores/marketStore.test.ts` - Property-based tests (NEW)

**Outcome:**
- ✅ Charts display immediately with cached data
- ✅ Charts upgrade seamlessly when full data arrives
- ✅ No more empty charts from API race conditions
- ✅ Tests prevent regression

---

## References

**React & TypeScript:**
- [React Documentation](https://react.dev) - Official React docs
- [TypeScript Handbook](https://www.typescriptlang.org/docs/handbook/intro.html) - TypeScript guide
- [React TypeScript Cheatsheet](https://react-typescript-cheatsheet.netlify.app/) - Common patterns

**State Management:**
- [Zustand Documentation](https://zustand.docs.pmnd.rs/) - Zustand state management
- [TanStack Query](https://tanstack.com/query/latest) - Server state management

**Testing:**
- [fast-check Documentation](https://fast-check.dev/) - Property-based testing
- [Testing Library](https://testing-library.com/) - React component testing
- [Vitest](https://vitest.dev/) - Test runner

**Design Patterns:**
- [Patterns.dev](https://www.patterns.dev/) - Modern web design patterns
- [Kent C. Dodds Blog](https://kentcdodds.com/blog) - React best practices

**Formal Methods:**
- [Property-Based Testing with fast-check](https://fast-check.dev/docs/introduction/) - Generative testing
- [Hillel Wayne: Practical TLA+](https://learntla.com/) - Formal specification

**Data Visualization:**
- [Chart.js Documentation](https://www.chartjs.org/docs/latest/) - Chart.js API and patterns
- [mplfinance](https://github.com/matplotlib/mplfinance) - Financial charting (Python, visual reference)
- [BennyThadikaran/stock-pattern](https://github.com/BennyThadikaran/stock-pattern) - Pattern visualization reference
- [D3.js](https://d3js.org/) - Low-level visualization primitives
- [Recharts](https://recharts.org/) - React charting library

---

**Last Updated:** January 2026
**Version:** 1.1.0
**Maintainer:** @claude (distilled from real implementation)

**Changelog:**
- **v1.1.0 (2026-01-05)**: Added Data Visualization Principles section (5 principles from candlestick chart pattern work)
- **v1.0.0 (2025-12)**: Initial version with state management, testing, and React/TypeScript patterns
