# Telegram Mini App Anti-Patterns

Common mistakes to avoid when building Telegram Mini App (React + TypeScript + Zustand).

**Source**: Extracted from `docs/frontend/UI_PRINCIPLES.md` - learned from real bugs and regressions.

---

## Anti-Pattern 1: Stale Object Copies

**Problem**: Storing copies of objects from arrays creates stale data bugs when the source array updates.

### The Bug

```typescript
// ❌ BAD: Storing copy of object
interface AppState {
  markets: Market[];
  selectedMarket: Market | null;  // Copy of a market from markets[]
}

const useMarketStore = create<AppState>((set) => ({
  markets: [],
  selectedMarket: null,

  // User clicks market card
  selectMarket: (market: Market) => {
    set({ selectedMarket: market });  // Creates copy
  },

  // Later, markets array updates...
  setMarkets: (newMarkets: Market[]) => {
    set({ markets: newMarkets });  // selectedMarket is now stale!
  },
}));

// Bug: selectedMarket still has old price even when markets[] updated
```

### Real-World Impact

```typescript
// User clicks market card showing price $100
selectMarket({ id: 'NVDA19', price: 100 });

// WebSocket updates market price to $150
setMarkets([{ id: 'NVDA19', price: 150 }]);

// Modal shows STALE price $100 instead of fresh $150
const selectedMarket = useMarketStore(state => state.selectedMarket);
console.log(selectedMarket.price);  // 100 ❌ (should be 150)
```

### The Fix: Normalized State Pattern

```typescript
// ✅ GOOD: Store ID reference, derive from source
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

  selectMarket: (ticker: string) => {
    set({ selectedTicker: ticker });  // Store ID, not copy
  },

  setMarkets: (markets: Market[]) => {
    set({ markets });  // Updates propagate automatically!
  },
}));

// Use in component
function MarketModal() {
  const selectedMarket = useMarketStore(state => state.getSelectedMarket());
  // Always fresh data, even when markets array updates!
}
```

**Why This Works:**
- ✅ Single source of truth (markets array)
- ✅ Automatic updates (selector re-runs when markets change)
- ✅ No stale data bugs
- ✅ Less memory (store ID not full object)

---

## Anti-Pattern 2: Prop Drilling

**Problem**: Passing props through many component levels creates brittle, hard-to-maintain code.

### The Bug

```typescript
// ❌ BAD: Prop drilling (5 levels deep!)
function App() {
  const [theme, setTheme] = useState('light');
  return <Dashboard theme={theme} />;
}

function Dashboard({ theme }: { theme: string }) {
  return <Sidebar theme={theme} />;
}

function Sidebar({ theme }: { theme: string }) {
  return <Menu theme={theme} />;
}

function Menu({ theme }: { theme: string }) {
  return <MenuItem theme={theme} />;
}

function MenuItem({ theme }: { theme: string }) {
  return <div className={theme === 'dark' ? 'bg-black' : 'bg-white'}>...</div>;
}
```

**Problems:**
- ❌ Every intermediate component must accept and pass `theme`
- ❌ Adding new global state requires updating ALL components in chain
- ❌ Hard to refactor (move MenuItem to different parent)
- ❌ TypeScript interfaces become cluttered with pass-through props

### The Fix: Global State (Zustand) or Context

```typescript
// ✅ GOOD: Zustand for global state (preferred)
const useThemeStore = create<{
  theme: 'light' | 'dark';
  setTheme: (theme: 'light' | 'dark') => void;
}>((set) => ({
  theme: 'light',
  setTheme: (theme) => set({ theme }),
}));

function App() {
  return <Dashboard />;  // No prop passing
}

function Dashboard() {
  return <Sidebar />;
}

function Sidebar() {
  return <Menu />;
}

function Menu() {
  return <MenuItem />;
}

function MenuItem() {
  const theme = useThemeStore(state => state.theme);  // Direct access!
  return <div className={theme === 'dark' ? 'bg-black' : 'bg-white'}>...</div>;
}
```

**Alternative: React Context (for simple cases)**

```typescript
// ✅ ALSO GOOD: Context for simple global values
const ThemeContext = createContext<'light' | 'dark'>('light');

function App() {
  const [theme, setTheme] = useState<'light' | 'dark'>('light');

  return (
    <ThemeContext.Provider value={theme}>
      <Dashboard />
    </ThemeContext.Provider>
  );
}

function MenuItem() {
  const theme = useContext(ThemeContext);  // No prop drilling!
  return <div className={theme === 'dark' ? 'bg-black' : 'bg-white'}>...</div>;
}
```

**When to Use Each:**
- **Zustand**: For complex state with actions (markets, user data, UI state)
- **Context**: For simple values that rarely change (theme, locale)
- **Props**: For component-specific configuration (only 1-2 levels deep)

---

## Anti-Pattern 3: Object Spreading Without Merge Logic

**Problem**: Blindly replacing state with new data can lose valuable cached information.

### The Bug

```typescript
// ❌ BAD: Blindly replace entire object
const useMarketStore = create<MarketState>((set) => ({
  report: null,

  updateReport: (newReport: Report) => {
    set({
      report: newReport,  // Might be empty or partial!
    });
  },
}));

// User sees chart disappear when API returns empty response
```

### Real-World Scenario

```typescript
// State: User has 30-day price chart cached
const cachedReport = {
  priceHistory: [/* 30 days of data */],
  projections: [/* 5 projections */],
};

// API returns partial response (slow loading)
const apiResponse = {
  priceHistory: [],  // Empty! Still loading...
  projections: [],
};

// Blindly replace → Chart disappears!
updateReport(apiResponse);  // ❌ Lost 30 days of cached data
```

### The Fix: Intelligent Merge Strategy

```typescript
// ✅ GOOD: Intelligent merge (only upgrade if better)
const useMarketStore = create<MarketState>((set, get) => ({
  report: null,

  updateReport: (apiResponse: Report) => {
    const currentReport = get().report;

    const cachedHistoryLength = currentReport?.priceHistory?.length || 0;
    const newHistoryLength = apiResponse.priceHistory?.length || 0;

    set({
      report: {
        // Preserve valuable fields if new data is empty or smaller
        priceHistory:
          newHistoryLength > cachedHistoryLength
            ? apiResponse.priceHistory  // Upgrade to better data
            : currentReport?.priceHistory || [],  // Keep cached

        projections:
          apiResponse.projections?.length > (currentReport?.projections?.length || 0)
            ? apiResponse.projections
            : currentReport?.projections || [],
      },
    });
  },
}));
```

**Pattern Template:**

```typescript
newData && newData.length > cachedData.length
  ? newData      // Upgrade to better data
  : cachedData   // Preserve what we have
```

**When to Use:**
- ✓ Updating from slow/unreliable APIs
- ✓ Merging cached + fresh data
- ✓ Any case where API might return partial/incomplete data

---

## Anti-Pattern 4: Mutating State Directly

**Problem**: Mutating arrays/objects in place breaks React's change detection.

### The Bug

```typescript
// ❌ BAD: Mutating array directly
const useMarketStore = create<MarketState>((set, get) => ({
  markets: [],

  addMarket: (newMarket: Market) => {
    const markets = get().markets;
    markets.push(newMarket);  // Mutates original array!
    set({ markets });         // React might not detect change
  },

  updateMarketPrice: (ticker: string, price: number) => {
    const markets = get().markets;
    const market = markets.find(m => m.ticker === ticker);
    if (market) {
      market.price = price;  // Mutates original object!
      set({ markets });      // React might not re-render
    }
  },
}));
```

**Why This Fails:**
- React compares state by reference (`oldMarkets === newMarkets`)
- Mutating the same array → same reference → React thinks nothing changed
- Components don't re-render even though data changed

### The Fix: Immutable Updates

```typescript
// ✅ GOOD: Immutable array updates
const useMarketStore = create<MarketState>((set, get) => ({
  markets: [],

  addMarket: (newMarket: Market) => {
    set((state) => ({
      markets: [...state.markets, newMarket],  // New array
    }));
  },

  removeMarket: (ticker: string) => {
    set((state) => ({
      markets: state.markets.filter(m => m.ticker !== ticker),  // New array
    }));
  },

  updateMarketPrice: (ticker: string, price: number) => {
    set((state) => ({
      markets: state.markets.map(m =>
        m.ticker === ticker
          ? { ...m, price }  // New object
          : m
      ),
    }));
  },
}));
```

**Immutable Update Patterns:**

```typescript
// Arrays
const newArray = [...oldArray, newItem];              // Add
const newArray = oldArray.filter(item => ...);        // Remove
const newArray = oldArray.map(item => ...);           // Update
const newArray = [newItem, ...oldArray];              // Prepend

// Objects
const newObject = { ...oldObject, key: newValue };    // Update field
const newObject = { ...oldObject, ...updates };       // Merge
const { removed, ...newObject } = oldObject;          // Remove field

// Nested updates
const newState = {
  ...state,
  user: {
    ...state.user,
    profile: {
      ...state.user.profile,
      name: 'New Name',
    },
  },
};
```

---

## Summary: Red Flags

| Red Flag | Anti-Pattern | Fix |
|----------|--------------|-----|
| `selectedMarket: Market \| null` | Stale Object Copies | Store ID + selector |
| Props passed 3+ levels deep | Prop Drilling | Zustand or Context |
| `set({ data: apiResponse })` | No Merge Logic | Intelligent merge |
| `array.push()` or `object.field = value` | Direct Mutation | Immutable updates |

---

## Real-World Case Study

**Problem**: Price charts disappeared in modal when API returned partial data.

**Root Causes:**
1. **Stale Object Copies**: `selectedMarket` stored copy, became stale when markets updated
2. **No Merge Logic**: API partial response replaced cached 30-day chart with empty array

**Solution Applied:**

```typescript
// Before (BUGGY)
interface AppState {
  markets: Market[];
  selectedMarket: Market | null;  // Stale copy
  updateReport: (r: Report) => void;  // No merge
}

// After (FIXED)
interface AppState {
  markets: Market[];
  selectedTicker: string | null;  // ID reference
  getSelectedMarket: () => Market | null;  // Selector
  updateReport: (r: Report) => void;  // Intelligent merge
}

const useMarketStore = create<AppState>((set, get) => ({
  markets: [],
  selectedTicker: null,

  // Selector: Always fresh
  getSelectedMarket: () => {
    const { markets, selectedTicker } = get();
    if (!selectedTicker) return null;
    return markets.find(m => m.id === selectedTicker) || null;
  },

  // Intelligent merge: only upgrade if better
  updateReport: (apiResponse: Report) => {
    const current = get().report;
    set({
      report: {
        priceHistory:
          apiResponse.priceHistory.length > (current?.priceHistory.length || 0)
            ? apiResponse.priceHistory  // Better data
            : current?.priceHistory || [],  // Keep cached
      },
    });
  },
}));
```

**Outcome:**
- ✅ Charts display immediately with cached data
- ✅ Charts upgrade seamlessly when full data arrives
- ✅ No more empty charts from API race conditions
- ✅ Tests prevent regression

---

## References

- **Correct patterns**: See [STATE-PATTERNS.md](STATE-PATTERNS.md), [REACT-PATTERNS.md](REACT-PATTERNS.md)
- **Testing**: See [TESTING.md](TESTING.md) for testing these patterns
- **Complete guide**: `docs/frontend/UI_PRINCIPLES.md`
- **React Docs**: https://react.dev (immutability, state management)
- **Zustand Docs**: https://zustand.docs.pmnd.rs/ (state management patterns)
