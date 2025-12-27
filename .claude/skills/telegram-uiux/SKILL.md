---
name: telegram-uiux
description: Build Telegram Mini App (React frontend) following state management and UX patterns. Use when building Telegram UI, fixing frontend bugs, implementing state management, or working with React/TypeScript/Zustand for Telegram Mini App.
---

# Telegram UI/UX Skill

**Tech Stack**: React 19 + TypeScript + Zustand + TanStack React Query + Tailwind CSS
**Platform**: Telegram Mini App (web-based dashboard)

**Source**: This skill extracts patterns from `docs/frontend/UI_PRINCIPLES.md` (hard-won lessons from real bugs and performance issues).

---

## Quick Pattern Selection

### State Management Decision Tree
1. **Selecting from a list?** → Use Normalized State (store ID, not object)
2. **Slow API call?** → Use Stale-While-Revalidate (show cached, fetch fresh)
3. **Data should only grow?** → Enforce Monotonic Invariants (intelligent merge)
4. **Master-detail view?** → Use Single Source of Truth (derive detail from master)

See [STATE-PATTERNS.md](STATE-PATTERNS.md) for detailed implementation.

---

## Common Workflows

### Building a New Component
1. **Define TypeScript interface** for props
   ```typescript
   interface MarketCardProps {
     ticker: string;
     onSelect: (ticker: string) => void;
   }
   ```
2. **Choose state pattern** (normalized, SWR, monotonic)
3. **Implement component** with prop validation
4. **Write property-based tests** (see [TESTING.md](TESTING.md))
5. **Verify no anti-patterns** (see [ANTI-PATTERNS.md](ANTI-PATTERNS.md))

### Fixing a Frontend Bug
1. **Identify bug category**:
   - Stale data? → Check normalized state implementation
   - Race condition? → Check SWR merge logic
   - Data disappearing? → Check monotonic invariants
2. **Reproduce with test** (property-based if applicable)
3. **Fix root cause** (not symptoms)
4. **Verify fix with invariant tests**

### Adding State to Zustand Store
1. **Determine if state is local or global**
   - Local (component-only): Use `useState`
   - Global (shared across components): Add to Zustand store
2. **Add state field** to store interface
3. **Add selector** if deriving from other state
4. **Update components** to use new state

---

## Pattern Quick Reference

### Normalized State (Prevent stale copies)

```typescript
// ❌ BAD: Object copy
interface AppState {
  markets: Market[];
  selectedMarket: Market | null;  // Copy of object
}

// ✅ GOOD: ID reference
interface AppState {
  markets: Market[];
  selectedTicker: string | null;  // Just the ID
  getSelectedMarket: () => Market | null;  // Derive from markets array
}
```

**When**: Selecting items from lists, master-detail views

### Stale-While-Revalidate (Instant UI)

```typescript
// Show cached data immediately
const cachedData = useQuery({
  queryKey: ['ticker'],
  staleTime: Infinity  // Always show cached first
});

// Fetch fresh data in background
const freshData = useQuery({
  queryKey: ['report'],
  refetchOnMount: true  // Fetch on mount
});

// UI upgrades seamlessly when fresh arrives
```

**When**: Slow/unreliable APIs, improving perceived performance

### Monotonic Invariants (Data only grows)

```typescript
// Intelligent merge: only replace if better
function updateFromAPI(apiResponse, currentState) {
  const newLength = apiResponse.price_history?.length || 0;
  const cachedLength = currentState.priceHistory?.length || 0;

  return {
    priceHistory:
      newLength > cachedLength
        ? apiResponse.price_history  // Upgrade
        : currentState.priceHistory  // Keep cached (don't downgrade)
  };
}
```

**When**: Updating from APIs that might return partial data

---

## Tech Stack Conventions

### React 19
- Functional components only (no class components)
- Hooks for state management
- Strict TypeScript prop interfaces

### Zustand (State Management)
- Global state for cross-component data
- Selectors for derived state
- Minimal re-renders (fine-grained subscriptions)

### TanStack React Query (Server State)
- Automatic caching with TTL
- Background refetching
- Optimistic updates

### Tailwind CSS 4
- Utility-first styling
- Responsive design (`sm:`, `md:`, `lg:`)
- Dark mode support (`dark:`)

### Recharts (Charts)
- Price history charts
- Responsive charts
- Custom tooltips

---

## File Organization

```
frontend/twinbar/src/
├── components/        # React components
│   ├── MarketCard.tsx
│   └── PriceChart.tsx
├── stores/           # Zustand stores
│   └── marketStore.ts
├── api/              # API clients
│   └── rankings.ts
└── types/            # TypeScript types
    └── market.ts
```

---

## Anti-Patterns to Avoid

Quick checklist (see [ANTI-PATTERNS.md](ANTI-PATTERNS.md) for details):

- ❌ Storing object copies (use IDs + selectors)
- ❌ Prop drilling beyond 2-3 levels (use Zustand)
- ❌ Blindly replacing state from API (use intelligent merge)
- ❌ Multiple sources of truth (derive from single source)
- ❌ Manual synchronization (use selectors)

---

## Testing Strategy

See [TESTING.md](TESTING.md) for complete testing guide:
- **Property-based testing** with fast-check (1000+ generated test cases)
- **Invariant testing** (monotonic data, type safety)
- **Component testing** with Testing Library
- **Visual regression testing** (charts, UI components)

---

## Next Steps

- **For state management patterns**: See [STATE-PATTERNS.md](STATE-PATTERNS.md)
- **For React/TypeScript patterns**: See [REACT-PATTERNS.md](REACT-PATTERNS.md)
- **For testing patterns**: See [TESTING.md](TESTING.md)
- **For anti-patterns**: See [ANTI-PATTERNS.md](ANTI-PATTERNS.md)
- **For complete reference**: See `docs/frontend/UI_PRINCIPLES.md`
