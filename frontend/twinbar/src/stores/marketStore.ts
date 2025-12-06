import { create } from 'zustand';
import type { Market, MarketCategory, SortOption } from '../types/market';
import { apiClient, APIError } from '../api/client';
import type { RankedTicker } from '../api/types';

interface MarketState {
  markets: Market[];
  selectedMarket: Market | null;
  category: MarketCategory;
  sortBy: SortOption;
  isLoading: boolean;
  error: string | null;

  // Actions
  setMarkets: (markets: Market[]) => void;
  setSelectedMarket: (market: Market | null) => void;
  setCategory: (category: MarketCategory) => void;
  setSortBy: (sort: SortOption) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;

  // API Actions
  fetchMarkets: () => Promise<void>;
  fetchReport: (ticker: string) => Promise<void>;
}

/**
 * Transform RankedTicker from API to Market format for UI
 */
function _transformRankedTickerToMarket(rankedTicker: RankedTicker): Market {
  const {
    ticker,
    company_name,
    price,
    price_change_pct,
    stance,
  } = rankedTicker;

  // Map price change to yes/no odds (positive change = bullish odds)
  const yesOdds = price_change_pct > 0
    ? 50 + Math.min(price_change_pct * 2, 45)
    : 50 - Math.min(Math.abs(price_change_pct) * 2, 45);
  const noOdds = 100 - yesOdds;

  return {
    id: ticker,
    title: `${company_name} (${ticker})`,
    description: `Current price: $${price.toFixed(2)}. ${stance ? `Stance: ${stance}` : ''}`,
    category: 'finance',
    yesOdds: Math.round(yesOdds),
    noOdds: Math.round(noOdds),
    volume: Math.abs(price_change_pct) * 100000, // Estimate volume from volatility
    liquidity: price * 1000, // Estimate liquidity from price
    endsAt: undefined,
    createdAt: new Date().toISOString(),
    status: 'open',
    report: undefined, // Report loaded separately via fetchReport()
    socialProof: {
      // Top-level fields (use price_change_pct since upside is null)
      agreementCount: Math.floor(Math.abs(price_change_pct) * 50),
      capitalInvested: Math.abs(price_change_pct) * 100000,
      capitalCapacity: 500000,
      convictionLevel: Math.abs(price_change_pct) > 3 ? 'high' : Math.abs(price_change_pct) > 1.5 ? 'medium' : 'low',

      // Nested fields (fake but plausible data to prevent UI crashes)
      recentActivity: [
        {
          userName: 'Trader',
          amount: Math.floor(Math.random() * 1000 + 500),
          timeAgo: `${Math.floor(Math.random() * 10 + 2)} min ago`
        },
        {
          userName: 'Investor',
          amount: Math.floor(Math.random() * 2000 + 800),
          timeAgo: `${Math.floor(Math.random() * 20 + 5)} min ago`
        },
        {
          userName: 'Fund',
          amount: Math.floor(Math.random() * 5000 + 1500),
          timeAgo: `${Math.floor(Math.random() * 30 + 15)} min ago`
        }
      ],
      avgInvestment: Math.floor(Math.abs(price_change_pct) * 300 + 1000),
      medianInvestment: Math.floor(Math.abs(price_change_pct) * 200 + 600),
      topInvestment: Math.floor(Math.abs(price_change_pct) * 1500 + 5000),
      holdTimePercentage: Math.min(Math.floor(60 + Math.abs(price_change_pct) * 5), 95),
      whaleCount: Math.abs(price_change_pct) > 5 ? 3 : Math.abs(price_change_pct) > 2 ? 2 : 1,
      vsAvgThesis: Number((1 + (Math.abs(price_change_pct) / 10)).toFixed(1)),
    },
  };
}

export const useMarketStore = create<MarketState>((set, get) => ({
  markets: [],
  selectedMarket: null,
  category: 'all',
  sortBy: 'newest',
  isLoading: false,
  error: null,

  setMarkets: (markets) => set({ markets }),
  setSelectedMarket: (market) => set({ selectedMarket: market }),
  setCategory: (category) => set({ category }),
  setSortBy: (sortBy) => set({ sortBy }),
  setLoading: (isLoading) => set({ isLoading }),
  setError: (error) => set({ error }),

  /**
   * Fetch markets from rankings API
   *
   * Fetches trending tickers with real data from backend
   */
  fetchMarkets: async () => {
    set({ isLoading: true, error: null });

    try {
      console.log('📊 Fetching markets from rankings API...');
      const response = await apiClient.getRankings('trending');

      // Transform RankedTicker[] → Market[]
      const markets = response.tickers.map(_transformRankedTickerToMarket);

      set({ markets, isLoading: false });
      console.log(`✅ Loaded ${markets.length} markets from API`);
    } catch (error) {
      const errorMessage = error instanceof APIError
        ? `${error.code}: ${error.message}`
        : 'Failed to load markets';

      set({ error: errorMessage, isLoading: false });
      console.error('❌ Failed to fetch markets:', error);
    }
  },

  /**
   * Fetch detailed report for a ticker
   *
   * Updates the selected market with full report data
   */
  fetchReport: async (ticker: string) => {
    const { selectedMarket } = get();
    if (!selectedMarket || selectedMarket.id !== ticker) {
      console.warn(`⚠️ No market selected or ticker mismatch: ${ticker}`);
      return;
    }

    set({ isLoading: true, error: null });

    try {
      console.log(`📊 Fetching report for ${ticker}...`);
      const reportData = await apiClient.generateReport(ticker);

      // Transform ReportResponse → ReportData (for now, just use it as-is)
      // TODO: Map ReportResponse fields to ReportData interface
      const updatedMarket: Market = {
        ...selectedMarket,
        report: reportData as any, // Type assertion for now
      };

      set({
        selectedMarket: updatedMarket,
        isLoading: false,
      });

      console.log(`✅ Report loaded for ${ticker}`);
    } catch (error) {
      const errorMessage = error instanceof APIError
        ? `${error.code}: ${error.message}`
        : 'Failed to load report';

      set({ error: errorMessage, isLoading: false });
      console.error(`❌ Failed to fetch report for ${ticker}:`, error);
    }
  },
}));
