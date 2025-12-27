# Testing Patterns for Telegram Mini App

Testing strategies for React + TypeScript + Zustand frontend.

**Tools**: Vitest + Testing Library + fast-check (property-based testing)

---

## Property-Based Testing

**Principle**: Instead of writing individual test cases, generate random test inputs and verify invariants always hold.

### Why It Matters
- Finds edge cases you wouldn't think of
- Tests behavior, not specific scenarios
- Scales better (1000+ test cases from one property)
- Documents system invariants

### Traditional Example-Based Testing

```typescript
// ❌ Limited: Only tests specific cases
it('merge preserves data', () => {
  const cached = [{ date: '2024-01-01', price: 100 }];
  const fresh = [];

  const result = merge(fresh, cached);
  expect(result).toEqual(cached);
});

// Only tests ONE scenario: empty fresh data
// What about: partial fresh data? Larger fresh data? Malformed data?
```

### Property-Based Testing

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

// This ONE property test effectively runs 1000+ individual tests
```

### Benefits
- ✅ Finds edge cases (empty arrays, negative numbers, malformed data)
- ✅ Documents invariants ("data never shrinks")
- ✅ Scales (1 property = 1000+ tests)
- ✅ Regression prevention (invariants enforced)

---

## Invariant-Based Testing

**Principle**: Define system invariants (properties that must ALWAYS be true) and verify they hold under all conditions.

### Common Invariants for Telegram Mini App

#### Invariant 1: Monotonic Data

```typescript
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
        let state = { priceHistory: [] };

        for (const update of updates) {
          state = updatePriceHistory(state, update.newData);
          const newLength = state.priceHistory.length;

          // INVARIANT: Never shrinks
          if (currentLength > 0 && newLength < currentLength) {
            return false;  // Violation!
          }

          currentLength = newLength;
        }

        return true;  // Invariant held across all updates
      }
    ),
    { numRuns: 1000 }
  );
});
```

#### Invariant 2: Type Safety

```typescript
it('INVARIANT: selectedTicker is always null or valid string', () => {
  fc.assert(
    fc.property(
      fc.oneof(
        fc.constant(null),
        fc.string(),
        fc.integer(),  // Invalid type
        fc.array(fc.string()),  // Invalid type
      ),
      (input) => {
        try {
          setSelectedTicker(input);
          const selected = getSelectedTicker();

          // INVARIANT: Result is null or string, never other types
          return selected === null || typeof selected === 'string';
        } catch {
          // Throwing is acceptable for invalid input
          return true;
        }
      }
    ),
    { numRuns: 500 }
  );
});
```

#### Invariant 3: Selector Consistency

```typescript
it('INVARIANT: getSelectedMarket returns market from markets array', () => {
  fc.assert(
    fc.property(
      fc.array(
        fc.record({
          id: fc.string(),
          name: fc.string(),
          price: fc.float({ min: 0, max: 1000 }),
        })
      ),
      fc.string(),
      (markets, selectedId) => {
        // Setup state
        setMarkets(markets);
        setSelectedTicker(selectedId);

        const result = getSelectedMarket();

        // INVARIANT: Result is either null or comes from markets array
        if (result === null) {
          return !markets.some(m => m.id === selectedId);
        } else {
          return markets.some(m => m.id === result.id);
        }
      }
    ),
    { numRuns: 1000 }
  );
});
```

---

## Generative Test Case Strategy

### Use fast-check Generators

```typescript
// Custom generator for market data
const marketArbitrary = fc.record({
  id: fc.string({ minLength: 1, maxLength: 10 }),
  ticker: fc.stringMatching(/^[A-Z]{2,4}[0-9]{2}$/),  // Pattern: NVDA19
  price: fc.float({ min: 0.01, max: 10000, noNaN: true }),
  change_pct: fc.float({ min: -100, max: 100 }),
  volume: fc.integer({ min: 0, max: 1_000_000_000 }),
});

// Use in tests
it('handles any valid market data', () => {
  fc.assert(
    fc.property(
      fc.array(marketArbitrary, { minLength: 1, maxLength: 50 }),
      (markets) => {
        setMarkets(markets);
        const retrieved = getMarkets();

        // Verify all markets retrieved correctly
        return retrieved.length === markets.length;
      }
    ),
    { numRuns: 500 }
  );
});
```

### Shrinking (Minimal Failing Example)

fast-check automatically shrinks failing test cases to minimal examples:

```typescript
// If this test fails...
it('processes any ticker correctly', () => {
  fc.assert(
    fc.property(
      fc.array(fc.string()),  // Generate array of strings
      (tickers) => {
        return tickers.every(t => processTicker(t) !== null);
      }
    )
  );
});

// fast-check might find failure with:
// Input: ["NVDA19", "AAPL34", "", "MSFT11"]  (original random input)
//
// Then automatically shrink to minimal failing case:
// Input: [""]  (empty string causes failure)
```

---

## Component Testing with Testing Library

### Test User Interactions

```typescript
import { render, screen, fireEvent } from '@testing-library/react';

it('opens modal when market card clicked', async () => {
  const { user } = render(<MarketDashboard />);

  // Find and click market card
  const card = screen.getByText('NVDA19');
  await user.click(card);

  // Verify modal opened
  expect(screen.getByRole('dialog')).toBeInTheDocument();
  expect(screen.getByText('NVIDIA Corp')).toBeInTheDocument();
});
```

### Test State Updates

```typescript
it('updates UI when market data changes', async () => {
  const { rerender } = render(<MarketCard ticker="NVDA19" />);

  // Initial state
  expect(screen.getByText('$100.00')).toBeInTheDocument();

  // Update store
  useMarketStore.getState().updateMarketPrice('NVDA19', 150.00);

  // Re-render
  rerender(<MarketCard ticker="NVDA19" />);

  // Verify UI updated
  expect(screen.getByText('$150.00')).toBeInTheDocument();
});
```

---

## Test-Driven Bug Fixing

**Pattern**: When you find a bug, write a failing test first, then fix the bug.

### Example Bug Fix Workflow

```typescript
// 1. Bug Report: "Chart data disappears when API returns empty response"

// 2. Write failing test (reproduces bug)
it('BUG: chart disappears on empty API response', () => {
  // Setup: Chart with data
  const state = {
    priceHistory: [
      { date: '2024-01-01', price: 100 },
      { date: '2024-01-02', price: 105 },
    ]
  };

  // Action: API returns empty response
  const apiResponse = { price_history: [] };
  const newState = updateFromAPI(apiResponse, state);

  // Expected: Chart data preserved
  expect(newState.priceHistory.length).toBe(2);  // FAILS (bug reproduced)
});

// 3. Fix the bug (implement intelligent merge)
function updateFromAPI(apiResponse, currentState) {
  return {
    priceHistory:
      apiResponse.price_history.length > currentState.priceHistory.length
        ? apiResponse.price_history
        : currentState.priceHistory  // Preserve cached data
  };
}

// 4. Test now passes (bug fixed)

// 5. Add property-based test to prevent regression
it('INVARIANT: updateFromAPI never shrinks priceHistory', () => {
  fc.assert(
    fc.property(
      fc.record({ price_history: fc.array(fc.anything()) }),
      fc.record({ priceHistory: fc.array(fc.anything()) }),
      (apiResponse, currentState) => {
        const newState = updateFromAPI(apiResponse, currentState);
        return newState.priceHistory.length >= currentState.priceHistory.length;
      }
    ),
    { numRuns: 1000 }
  );
});
```

---

## Visual Regression Testing

### Testing Charts

```typescript
it('chart renders correctly', () => {
  const { container } = render(
    <PriceChart
      data={[
        { date: '2024-01-01', price: 100 },
        { date: '2024-01-02', price: 105 },
      ]}
    />
  );

  // Verify SVG elements present
  expect(container.querySelector('svg')).toBeInTheDocument();
  expect(container.querySelectorAll('.recharts-line-curve')).toHaveLength(1);
});
```

### Testing Responsive Behavior

```typescript
it('chart adapts to container width', () => {
  const { rerender, container } = render(
    <div style={{ width: 600 }}>
      <PriceChart data={mockData} />
    </div>
  );

  const chart = container.querySelector('.recharts-wrapper');
  expect(chart).toHaveStyle({ width: '600px' });

  // Resize container
  rerender(
    <div style={{ width: 400 }}>
      <PriceChart data={mockData} />
    </div>
  );

  expect(chart).toHaveStyle({ width: '400px' });
});
```

---

## Summary: Testing Strategy

| Test Type | Tool | Use Case | Runs |
|-----------|------|----------|------|
| Property-based | fast-check | Invariants (monotonic data, type safety) | 1000+ |
| Component | Testing Library | User interactions, UI updates | Per scenario |
| Visual | Testing Library | Chart rendering, responsive design | Per component |
| Integration | Vitest | API → State → UI flow | Critical paths |

---

## Quick Reference

### Property-Based Test Template

```typescript
it('INVARIANT: description', () => {
  fc.assert(
    fc.property(
      fc.arbitrary(),  // Input generator
      (input) => {
        const result = functionUnderTest(input);
        return invariantCondition(result);  // True if invariant holds
      }
    ),
    { numRuns: 1000 }
  );
});
```

### Component Test Template

```typescript
it('description', async () => {
  const { user } = render(<Component />);

  // Action
  await user.click(screen.getByText('Button'));

  // Assertion
  expect(screen.getByText('Result')).toBeInTheDocument();
});
```

---

## References

- **State patterns to test**: See [STATE-PATTERNS.md](STATE-PATTERNS.md)
- **React patterns**: See [REACT-PATTERNS.md](REACT-PATTERNS.md)
- **fast-check docs**: https://github.com/dubzzz/fast-check
- **Testing Library docs**: https://testing-library.com/react
- **Complete guide**: `docs/frontend/UI_PRINCIPLES.md`
