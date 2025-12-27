# React + TypeScript + Zustand Patterns

Patterns for building Telegram Mini App (React 19 + TypeScript + Zustand).

**Source**: Extracted from `docs/frontend/UI_PRINCIPLES.md` - battle-tested React patterns.

---

## TypeScript Prop Interfaces

**Principle**: Strict TypeScript prop interfaces catch bugs at compile time and enable IDE autocomplete.

### Pattern: Strict Prop Types with Literal Types

```typescript
// ✅ GOOD: Strict interface with literal types
interface MarketCardProps {
  ticker: string;
  price: number;
  change: number;
  status: 'active' | 'inactive' | 'delisted';  // Literal union type
  onSelect: (ticker: string) => void;
  className?: string;  // Optional prop
}

function MarketCard({ ticker, price, change, status, onSelect, className }: MarketCardProps) {
  return (
    <div className={className} onClick={() => onSelect(ticker)}>
      <h3>{ticker}</h3>
      <p className={change >= 0 ? 'text-green' : 'text-red'}>
        {price} ({change >= 0 ? '+' : ''}{change}%)
      </p>
      <span>{status}</span>
    </div>
  );
}
```

**Benefits:**
- ✅ TypeScript validates status is one of the allowed values
- ✅ IDE autocompletes literal options
- ✅ Compile-time errors if wrong value passed

### Pattern: Readonly Arrays for Immutability

```typescript
// ✅ GOOD: Readonly array prevents accidental mutation
interface ChartProps {
  data: readonly { date: string; price: number }[];
  width?: number;
  height?: number;
}

function PriceChart({ data, width = 600, height = 400 }: ChartProps) {
  // data.push(...) → TypeScript error (readonly)
  return <ResponsiveContainer width={width} height={height}>...</ResponsiveContainer>;
}
```

### Pattern: Generic Components

```typescript
// ✅ GOOD: Generic component for reusability
interface ListProps<T> {
  items: readonly T[];
  renderItem: (item: T) => React.ReactNode;
  keyExtractor: (item: T) => string;
}

function List<T>({ items, renderItem, keyExtractor }: ListProps<T>) {
  return (
    <ul>
      {items.map(item => (
        <li key={keyExtractor(item)}>
          {renderItem(item)}
        </li>
      ))}
    </ul>
  );
}

// Usage
<List
  items={markets}
  renderItem={(market) => <MarketCard {...market} />}
  keyExtractor={(market) => market.id}
/>
```

### Pattern: Event Handlers with Proper Types

```typescript
// ✅ GOOD: Typed event handlers
interface SearchBarProps {
  onSearch: (query: string) => void;
  placeholder?: string;
}

function SearchBar({ onSearch, placeholder = 'Search tickers...' }: SearchBarProps) {
  const handleSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const formData = new FormData(e.currentTarget);
    const query = formData.get('query') as string;
    onSearch(query);
  };

  return (
    <form onSubmit={handleSubmit}>
      <input type="text" name="query" placeholder={placeholder} />
      <button type="submit">Search</button>
    </form>
  );
}
```

---

## Zustand State Management

**Principle**: Zustand provides minimal, performant global state without boilerplate.

### Pattern: Create Store with Initial State + Actions

```typescript
import { create } from 'zustand';

interface Market {
  id: string;
  ticker: string;
  price: number;
  change_pct: number;
}

interface MarketState {
  // State
  markets: Market[];
  selectedTicker: string | null;
  isLoading: boolean;
  error: string | null;

  // Selectors (derived state)
  getSelectedMarket: () => Market | null;

  // Actions
  setMarkets: (markets: Market[]) => void;
  setSelectedTicker: (ticker: string | null) => void;
  updateMarketPrice: (ticker: string, price: number) => void;
  fetchMarkets: () => Promise<void>;
}

const useMarketStore = create<MarketState>((set, get) => ({
  // Initial state
  markets: [],
  selectedTicker: null,
  isLoading: false,
  error: null,

  // Selector: Derive selected market from markets array
  getSelectedMarket: () => {
    const { markets, selectedTicker } = get();
    if (!selectedTicker) return null;
    return markets.find(m => m.ticker === selectedTicker) || null;
  },

  // Actions
  setMarkets: (markets) => set({ markets }),

  setSelectedTicker: (ticker) => set({ selectedTicker: ticker }),

  updateMarketPrice: (ticker, price) => set((state) => ({
    markets: state.markets.map(m =>
      m.ticker === ticker ? { ...m, price } : m
    ),
  })),

  fetchMarkets: async () => {
    set({ isLoading: true, error: null });
    try {
      const response = await fetch('/api/markets');
      const markets = await response.json();
      set({ markets, isLoading: false });
    } catch (error) {
      set({ error: error.message, isLoading: false });
    }
  },
}));

export default useMarketStore;
```

### Pattern: Selector Pattern for Fine-Grained Subscriptions

```typescript
// ✅ GOOD: Subscribe to specific state slice
function MarketList() {
  // Component only re-renders when markets array changes
  const markets = useMarketStore(state => state.markets);

  return (
    <ul>
      {markets.map(market => (
        <MarketCard key={market.id} {...market} />
      ))}
    </ul>
  );
}

// ✅ GOOD: Subscribe to derived state
function MarketModal() {
  // Only re-renders when selected market changes
  const selectedMarket = useMarketStore(state => state.getSelectedMarket());

  if (!selectedMarket) return null;

  return (
    <div className="modal">
      <h2>{selectedMarket.ticker}</h2>
      <p>Price: ${selectedMarket.price}</p>
    </div>
  );
}

// ❌ BAD: Subscribes to entire store
function MarketCard() {
  const state = useMarketStore();  // Re-renders on ANY state change!
  return <div>{state.markets[0].ticker}</div>;
}
```

### Pattern: Reading Fresh State with getState()

```typescript
// ✅ GOOD: Read fresh state in async function
const useMarketStore = create<MarketState>((set, get) => ({
  // ...state

  openModal: async (ticker: string) => {
    // Set selected ticker immediately
    set({ selectedTicker: ticker, isModalOpen: true });

    // Fetch full report in background
    try {
      const report = await fetch(`/api/reports/${ticker}`).then(r => r.json());

      // Read fresh state (may have changed during async operation)
      const currentState = get();

      // Only update if user hasn't switched tickers
      if (currentState.selectedTicker === ticker) {
        set({ fullReport: report });
      }
    } catch (error) {
      set({ error: error.message });
    }
  },
}));
```

### Pattern: Async Actions with Error Handling

```typescript
const useMarketStore = create<MarketState>((set, get) => ({
  // ...state

  fetchReport: async (ticker: string) => {
    const cachedReport = get().reports[ticker];

    // Show cached data immediately (Stale-While-Revalidate)
    if (cachedReport) {
      set({ currentReport: cachedReport });
    }

    // Fetch fresh data in background
    set({ isLoadingReport: true });
    try {
      const fresh = await fetch(`/api/reports/${ticker}`).then(r => r.json());

      // Intelligent merge: only upgrade if fresh data is better
      const merged = {
        ...cachedReport,
        priceHistory:
          fresh.priceHistory.length > (cachedReport?.priceHistory.length || 0)
            ? fresh.priceHistory
            : cachedReport?.priceHistory || [],
      };

      set({
        currentReport: merged,
        reports: { ...get().reports, [ticker]: merged },
        isLoadingReport: false,
      });
    } catch (error) {
      // Keep cached data on error
      set({
        error: error.message,
        isLoadingReport: false
      });
    }
  },
}));
```

---

## Component Composition

**Principle**: Build complex UIs from small, focused components using composition.

### Pattern: Small, Focused Components

```typescript
// ✅ GOOD: Small components with single responsibility

// Component 1: Display market price
function MarketPrice({ price, change }: { price: number; change: number }) {
  const color = change >= 0 ? 'text-green-500' : 'text-red-500';
  return (
    <div>
      <span className="text-2xl font-bold">${price.toFixed(2)}</span>
      <span className={`ml-2 ${color}`}>
        {change >= 0 ? '+' : ''}{change.toFixed(2)}%
      </span>
    </div>
  );
}

// Component 2: Display market status badge
function MarketStatus({ status }: { status: 'active' | 'inactive' }) {
  const bgColor = status === 'active' ? 'bg-green-100' : 'bg-gray-100';
  const textColor = status === 'active' ? 'text-green-800' : 'text-gray-800';
  return (
    <span className={`px-2 py-1 rounded ${bgColor} ${textColor}`}>
      {status}
    </span>
  );
}

// Component 3: Compose into MarketCard
function MarketCard({ ticker, price, change, status }: MarketCardProps) {
  return (
    <div className="p-4 border rounded">
      <h3 className="text-lg font-bold">{ticker}</h3>
      <MarketPrice price={price} change={change} />
      <MarketStatus status={status} />
    </div>
  );
}
```

### Pattern: Props for Configuration, Children for Content

```typescript
// ✅ GOOD: Children prop for flexible content
interface CardProps {
  title: string;
  variant?: 'default' | 'highlighted';
  children: React.ReactNode;
}

function Card({ title, variant = 'default', children }: CardProps) {
  const bgColor = variant === 'highlighted' ? 'bg-blue-50' : 'bg-white';

  return (
    <div className={`p-4 border rounded ${bgColor}`}>
      <h2 className="text-xl font-bold mb-2">{title}</h2>
      {children}
    </div>
  );
}

// Usage: Card accepts ANY content
<Card title="Market Overview">
  <MarketPrice price={150.25} change={2.5} />
  <p>Additional details...</p>
  <button>View Report</button>
</Card>

<Card title="Top Gainers" variant="highlighted">
  <MarketList markets={topGainers} />
</Card>
```

### Pattern: Avoid Prop Drilling (Use Context or Zustand)

```typescript
// ❌ BAD: Prop drilling (passing props through many levels)
function App() {
  const [theme, setTheme] = useState('light');
  return <Dashboard theme={theme} />;
}

function Dashboard({ theme }: { theme: string }) {
  return <Sidebar theme={theme} />;
}

function Sidebar({ theme }: { theme: string }) {
  return <UserMenu theme={theme} />;
}

function UserMenu({ theme }: { theme: string }) {
  return <div className={theme === 'dark' ? 'bg-black' : 'bg-white'}>...</div>;
}

// ✅ GOOD: Use Zustand for global state (preferred)
const useThemeStore = create<{ theme: string; setTheme: (t: string) => void }>((set) => ({
  theme: 'light',
  setTheme: (theme) => set({ theme }),
}));

function App() {
  return <Dashboard />;
}

function Dashboard() {
  return <Sidebar />;
}

function Sidebar() {
  return <UserMenu />;
}

function UserMenu() {
  const theme = useThemeStore(state => state.theme);  // No prop drilling!
  return <div className={theme === 'dark' ? 'bg-black' : 'bg-white'}>...</div>;
}
```

### Pattern: Separation of Concerns

```typescript
// ✅ GOOD: Separate data fetching from presentation

// Container component: Handles data fetching
function MarketDashboardContainer() {
  const markets = useMarketStore(state => state.markets);
  const isLoading = useMarketStore(state => state.isLoading);
  const fetchMarkets = useMarketStore(state => state.fetchMarkets);

  useEffect(() => {
    fetchMarkets();
  }, [fetchMarkets]);

  if (isLoading) return <LoadingSpinner />;

  return <MarketDashboard markets={markets} />;
}

// Presentational component: Pure rendering
interface MarketDashboardProps {
  markets: readonly Market[];
}

function MarketDashboard({ markets }: MarketDashboardProps) {
  return (
    <div className="grid grid-cols-3 gap-4">
      {markets.map(market => (
        <MarketCard key={market.id} {...market} />
      ))}
    </div>
  );
}
```

---

## Real-World Example: Market Modal

**Complete example combining all patterns:**

```typescript
// 1. Type definitions
interface Market {
  id: string;
  ticker: string;
  price: number;
  change_pct: number;
}

interface Report {
  priceHistory: readonly { date: string; price: number }[];
  projections: readonly number[];
}

// 2. Zustand store
const useMarketStore = create<MarketState>((set, get) => ({
  markets: [],
  selectedTicker: null,
  isModalOpen: false,
  fullReport: null,

  // Selector: Derive selected market
  getSelectedMarket: () => {
    const { markets, selectedTicker } = get();
    if (!selectedTicker) return null;
    return markets.find(m => m.ticker === selectedTicker) || null;
  },

  // Action: Open modal with stale-while-revalidate pattern
  openModal: async (ticker: string) => {
    set({ selectedTicker: ticker, isModalOpen: true });

    // Fetch full report in background
    try {
      const report = await fetch(`/api/reports/${ticker}`).then(r => r.json());
      if (get().selectedTicker === ticker) {
        set({ fullReport: report });
      }
    } catch (error) {
      console.error('Failed to fetch report:', error);
    }
  },

  closeModal: () => set({ isModalOpen: false, selectedTicker: null }),
}));

// 3. Presentational components
function MarketModal() {
  const isOpen = useMarketStore(state => state.isModalOpen);
  const selectedMarket = useMarketStore(state => state.getSelectedMarket());
  const fullReport = useMarketStore(state => state.fullReport);
  const closeModal = useMarketStore(state => state.closeModal);

  if (!isOpen || !selectedMarket) return null;

  return (
    <div className="modal-overlay" onClick={closeModal}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <h2>{selectedMarket.ticker}</h2>
        <MarketPrice price={selectedMarket.price} change={selectedMarket.change_pct} />

        {fullReport ? (
          <PriceChart data={fullReport.priceHistory} />
        ) : (
          <LoadingSpinner />
        )}

        <button onClick={closeModal}>Close</button>
      </div>
    </div>
  );
}

// 4. Usage in parent component
function MarketCard({ ticker, price, change }: MarketCardProps) {
  const openModal = useMarketStore(state => state.openModal);

  return (
    <div className="card" onClick={() => openModal(ticker)}>
      <h3>{ticker}</h3>
      <MarketPrice price={price} change={change} />
    </div>
  );
}
```

---

## Quick Reference

### TypeScript Patterns
- ✅ Use literal union types for constrained values
- ✅ Mark props `readonly` to prevent mutation
- ✅ Generic components for reusability
- ✅ Proper event handler types (`React.FormEvent`, `React.MouseEvent`)

### Zustand Patterns
- ✅ Selectors for fine-grained subscriptions
- ✅ `getState()` for reading fresh state in async functions
- ✅ Derived state via selector functions
- ✅ Async actions with error handling

### Component Patterns
- ✅ Small, focused components (single responsibility)
- ✅ Props for configuration, children for content
- ✅ Avoid prop drilling (use Zustand for global state)
- ✅ Separation of concerns (container vs presentational)

---

## References

- **React Patterns**: See [STATE-PATTERNS.md](STATE-PATTERNS.md) for state management
- **Testing**: See [TESTING.md](TESTING.md) for component testing
- **Anti-Patterns**: See [ANTI-PATTERNS.md](ANTI-PATTERNS.md) for what to avoid
- **Complete guide**: `docs/frontend/UI_PRINCIPLES.md`
- **React Docs**: https://react.dev
- **Zustand Docs**: https://zustand.docs.pmnd.rs/
- **TypeScript Handbook**: https://www.typescriptlang.org/docs/handbook/intro.html
