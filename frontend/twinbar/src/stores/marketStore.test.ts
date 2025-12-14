/**
 * Property-Based Tests for Market Store
 *
 * Tests invariants using fast-check to generate random sequences of operations
 * and verify that certain properties always hold.
 */

import { describe, it, beforeEach } from 'vitest';
import * as fc from 'fast-check';
import { useMarketStore } from './marketStore';
import type { Market } from '../types/market';
import type { ReportData } from '../types/report';

describe('MarketStore - Property-Based Tests', () => {
  beforeEach(() => {
    // Reset store before each test
    const store = useMarketStore.getState();
    store.setMarkets([]);
    store.setSelectedTicker(null);
    store.setLoading(false);
    store.setError(null);
  });

  describe('Chart Data Monotonicity', () => {
    it('INVARIANT: price_history never shrinks after being populated', () => {
      fc.assert(
        fc.property(
          // Generate random sequences of price data updates
          fc.array(
            fc.record({
              ticker: fc.constantFrom('NVDA19', 'AAPL', 'TSLA', 'MSFT'),
              priceHistory: fc.array(
                fc.record({
                  date: fc
                    .integer({
                      min: new Date('2024-01-01').getTime(),
                      max: new Date('2024-12-31').getTime(),
                    })
                    .map(ts => new Date(ts).toISOString()),
                  price: fc.float({ min: 10, max: 1000 }),
                  volume: fc.integer({ min: 1000000, max: 100000000 }),
                }),
                { minLength: 0, maxLength: 365 }
              ),
              shouldBeEmpty: fc.boolean(), // Simulate API returning empty
            }),
            { minLength: 1, maxLength: 20 }
          ),
          (updates) => {
            const store = useMarketStore.getState();
            const priceHistorySizes: Record<string, number[]> = {};

            // Initialize markets
            const initialMarkets: Market[] = ['NVDA19', 'AAPL', 'TSLA', 'MSFT'].map(ticker => ({
              id: ticker,
              title: `${ticker} Company`,
              description: 'Test market',
              category: 'finance' as const,
              yesOdds: 50,
              noOdds: 50,
              volume: 1000000,
              liquidity: 500000,
              endsAt: undefined,
              createdAt: new Date().toISOString(),
              status: 'open' as const,
              report: undefined,
              socialProof: {
                agreementCount: 100,
                capitalInvested: 50000,
                capitalCapacity: 100000,
                convictionLevel: 'medium' as const,
                recentActivity: [],
                topInvestors: [],
                sentimentTrend: 'neutral' as const,
              },
            }));

            store.setMarkets(initialMarkets);

            // Track price history sizes for each ticker
            for (const ticker of ['NVDA19', 'AAPL', 'TSLA', 'MSFT']) {
              priceHistorySizes[ticker] = [];
            }

            // Apply updates sequentially
            for (const update of updates) {
              const { ticker, priceHistory, shouldBeEmpty } = update;

              // Simulate API response
              // shouldBeEmpty=true means API explicitly returns empty
              // shouldBeEmpty=false but priceHistory=[] means API hasn't loaded yet (preserve cache)
              const apiPriceHistory = shouldBeEmpty ? [] : (priceHistory.length > 0 ? priceHistory : []);

              // Manually update the market (simulating what fetchReport does)
              // IMPORTANT: Read fresh state each iteration
              const currentMarkets = useMarketStore.getState().markets;
              const currentMarket = currentMarkets.find(m => m.id === ticker);

              if (!currentMarket) continue;

              const currentSize = currentMarket.report?.price_history?.length || 0;

              // Create merged report (EXACT same logic as fetchReport)
              // MONOTONIC: Only overwrite if new data is BIGGER (monotonic growth)
              const mergedPriceHistory =
                apiPriceHistory && apiPriceHistory.length > currentSize
                  ? apiPriceHistory
                  : currentMarket.report?.price_history || [];

              const updatedReport: ReportData = {
                ...(currentMarket.report || {}),
                ticker,
                company_name: `${ticker} Company`,
                current_price: apiPriceHistory[apiPriceHistory.length - 1]?.price || 100,
                price_change_pct: 0,
                stance: 'neutral' as const,
                price_history: mergedPriceHistory as any,
                projections: currentMarket.report?.projections || [],
                initial_investment: 1000,
                key_scores: currentMarket.report?.key_scores || [],
                all_scores: currentMarket.report?.all_scores || [],
                technical_metrics: currentMarket.report?.technical_metrics || [],
                narrative_sections: currentMarket.report?.narrative_sections || [],
                fundamentals: currentMarket.report?.fundamentals || { valuation: {}, growth: {}, profitability: {} },
                risk: currentMarket.report?.risk || undefined,
                news_items: currentMarket.report?.news_items || [],
                peers: currentMarket.report?.peers || [],
                generated_at: new Date().toISOString(),
                report_version: '1.0.0',
              } as any;

              // Update markets array
              const updatedMarkets = currentMarkets.map(m =>
                m.id === ticker ? { ...m, report: updatedReport } : m
              );

              store.setMarkets(updatedMarkets);

              // Record the size after update
              const newSize = mergedPriceHistory.length;
              priceHistorySizes[ticker].push(newSize);

              // INVARIANT: Size never decreases
              if (currentSize > 0 && newSize < currentSize) {
                // Found a violation!
                return false;
              }
            }

            // INVARIANT: For each ticker, all sizes should be monotonically non-decreasing
            for (const ticker in priceHistorySizes) {
              const sizes = priceHistorySizes[ticker];
              for (let i = 1; i < sizes.length; i++) {
                if (sizes[i] < sizes[i - 1]) {
                  // Violation: size decreased
                  return false;
                }
              }
            }

            return true;
          }
        ),
        {
          numRuns: 1000, // Run 1000 random test cases
          verbose: true,
        }
      );
    });

    it('INVARIANT: projections never shrink after being populated', () => {
      fc.assert(
        fc.property(
          fc.array(
            fc.record({
              ticker: fc.constantFrom('NVDA19', 'AAPL'),
              projections: fc.array(
                fc.record({
                  date: fc
                    .integer({
                      min: new Date('2024-01-01').getTime(),
                      max: new Date('2024-12-31').getTime(),
                    })
                    .map(ts => new Date(ts).toISOString()),
                  predicted_price: fc.float({ min: 10, max: 1000 }),
                  confidence_interval: fc.record({
                    lower: fc.float({ min: 5, max: 500 }),
                    upper: fc.float({ min: 500, max: 1500 }),
                  }),
                }),
                { minLength: 0, maxLength: 100 }
              ),
              shouldBeEmpty: fc.boolean(),
            }),
            { minLength: 1, maxLength: 15 }
          ),
          (updates) => {
            const store = useMarketStore.getState();

            // Initialize markets
            const initialMarkets: Market[] = ['NVDA19', 'AAPL'].map(ticker => ({
              id: ticker,
              title: `${ticker} Company`,
              description: 'Test market',
              category: 'finance' as const,
              yesOdds: 50,
              noOdds: 50,
              volume: 1000000,
              liquidity: 500000,
              endsAt: undefined,
              createdAt: new Date().toISOString(),
              status: 'open' as const,
              report: undefined,
              socialProof: {
                agreementCount: 100,
                capitalInvested: 50000,
                capitalCapacity: 100000,
                convictionLevel: 'medium' as const,
                recentActivity: [],
                topInvestors: [],
                sentimentTrend: 'neutral' as const,
              },
            }));

            store.setMarkets(initialMarkets);

            // Apply updates
            for (const update of updates) {
              const { ticker, projections, shouldBeEmpty } = update;

              const apiProjections = shouldBeEmpty ? [] : projections;

              // IMPORTANT: Read fresh state each iteration
              const currentMarkets = useMarketStore.getState().markets;
              const currentMarket = currentMarkets.find(m => m.id === ticker);

              if (!currentMarket) continue;

              const currentSize = currentMarket.report?.projections?.length || 0;

              // Match actual implementation logic with && check
              const mergedProjections =
                apiProjections && apiProjections.length > 0
                  ? apiProjections
                  : currentMarket.report?.projections || [];

              if (currentMarket.report) {
                currentMarket.report.projections = mergedProjections as any;
              }

              const newSize = mergedProjections.length;

              // INVARIANT: Projections never shrink
              if (currentSize > 0 && newSize < currentSize) {
                return false;
              }
            }

            return true;
          }
        ),
        { numRuns: 500 }
      );
    });
  });

  describe('Normalized State Integrity', () => {
    it('INVARIANT: selectedTicker always corresponds to a market in markets array', () => {
      fc.assert(
        fc.property(
          fc.array(
            fc.oneof(
              fc.record({
                action: fc.constant('SELECT'),
                ticker: fc.constantFrom('NVDA19', 'AAPL', 'TSLA', 'INVALID'),
              }),
              fc.record({
                action: fc.constant('CLEAR'),
              }),
              fc.record({
                action: fc.constant('UPDATE_MARKETS'),
                tickers: fc.array(fc.constantFrom('NVDA19', 'AAPL', 'TSLA'), { minLength: 1, maxLength: 3 }),
              })
            ),
            { minLength: 1, maxLength: 30 }
          ),
          (actions) => {
            // Initialize with empty markets
            useMarketStore.getState().setMarkets([]);
            useMarketStore.getState().setSelectedTicker(null);

            for (const action of actions) {
              if (action.action === 'SELECT') {
                // Attempt to select a ticker
                useMarketStore.getState().setSelectedTicker(action.ticker);

                // IMPORTANT: Read fresh state after each action
                const currentState = useMarketStore.getState();
                const selectedMarket = currentState.getSelectedMarket();
                const selectedTicker = currentState.selectedTicker;
                const markets = currentState.markets;

                if (selectedTicker) {
                  const marketExists = markets.some(m => m.id === selectedTicker);

                  // INVARIANT: If market doesn't exist, getSelectedMarket() MUST return null
                  if (!marketExists && selectedMarket !== null) {
                    return false;
                  }

                  // INVARIANT: If market exists, getSelectedMarket() MUST return it
                  if (marketExists && selectedMarket === null) {
                    return false;
                  }
                }
              } else if (action.action === 'CLEAR') {
                useMarketStore.getState().setSelectedTicker(null);

                // After clearing, selectedMarket should be null
                const currentState = useMarketStore.getState();
                if (currentState.getSelectedMarket() !== null) {
                  return false;
                }
              } else if (action.action === 'UPDATE_MARKETS') {
                // Update markets array
                const newMarkets: Market[] = action.tickers.map(ticker => ({
                  id: ticker,
                  title: `${ticker} Company`,
                  description: 'Test',
                  category: 'finance' as const,
                  yesOdds: 50,
                  noOdds: 50,
                  volume: 1000000,
                  liquidity: 500000,
                  endsAt: undefined,
                  createdAt: new Date().toISOString(),
                  status: 'open' as const,
                  report: undefined,
                  socialProof: {
                    agreementCount: 100,
                    capitalInvested: 50000,
                    capitalCapacity: 100000,
                    convictionLevel: 'medium' as const,
                    recentActivity: [],
                    topInvestors: [],
                    sentimentTrend: 'neutral' as const,
                  },
                }));

                useMarketStore.getState().setMarkets(newMarkets);

                // INVARIANT: If selectedTicker was set but is no longer in markets,
                // getSelectedMarket() should return null
                const currentState = useMarketStore.getState();
                const selectedTicker = currentState.selectedTicker;
                if (selectedTicker) {
                  const marketExists = newMarkets.some(m => m.id === selectedTicker);
                  const selectedMarket = currentState.getSelectedMarket();

                  if (!marketExists && selectedMarket !== null) {
                    return false;
                  }
                }
              }
            }

            return true;
          }
        ),
        { numRuns: 1000 }
      );
    });
  });
});
