import { create } from 'zustand';
import type { Market, MarketCategory, SortOption } from '../types/market';
import { apiClient, APIError } from '../api/client';
// import type { RankedTicker } from '../api/types';  // Not used when mock data enabled
import { mockNVDAReport, mockAAPLReport } from '../mocks/reportData';

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

/* Commented out while using mock data
function _transformRankedTickerToMarket(rankedTicker: RankedTicker): Market {
  const {
    ticker,
    company_name,
    price,
    price_change_pct,
    stance,
    estimated_upside_pct,
    risk_level,
  } = rankedTicker;

  const yesOdds = price_change_pct > 0 ? 50 + Math.min(price_change_pct * 2, 45) : 50 - Math.min(Math.abs(price_change_pct) * 2, 45);
  const noOdds = 100 - yesOdds;

  return {
    id: ticker,
    title: `${company_name} (${ticker})`,
    description: `Current price: ${price}. ${stance ? `Stance: ${stance}` : ''}`,
    category: 'finance',
    yesOdds: Math.round(yesOdds),
    noOdds: Math.round(noOdds),
    volume: Math.abs(price_change_pct) * 100000,
    liquidity: price * 1000,
    endsAt: undefined,
    createdAt: new Date().toISOString(),
    status: 'open',
    report: undefined,
    socialProof: estimated_upside_pct ? {
      agreementCount: Math.floor(Math.abs(estimated_upside_pct) * 10),
      capitalInvested: Math.abs(estimated_upside_pct) * 50000,
      capitalCapacity: 500000,
      convictionLevel: risk_level === 'low' ? 'high' : risk_level === 'high' ? 'low' : 'medium',
    } : undefined,
  };
}
*/

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
   * Fetch markets - USING MOCK DATA for UI preview
   *
   * Using pre-designed mock data to showcase TwinBar UI in Telegram Mini App
   */
  fetchMarkets: async () => {
    set({ isLoading: true, error: null });

    // Simulate API delay
    await new Promise(resolve => setTimeout(resolve, 500));

    set({ markets: mockMarkets, isLoading: false });
    console.log(`✅ Loaded ${mockMarkets.length} mock markets for UI preview`);
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

// Mock data for UI preview in Telegram Mini App
export const mockMarkets: Market[] = [
  {
    id: '1',
    title: 'Will BTC reach $100K by end of 2025?',
    description: 'Bitcoin must reach or exceed $100,000 USD at any point before December 31, 2025.',
    category: 'crypto',
    yesOdds: 67,
    noOdds: 33,
    volume: 2500000,
    liquidity: 850000,
    endsAt: '2025-12-31T23:59:59Z',
    createdAt: '2025-01-01T00:00:00Z',
    status: 'open',
    report: mockNVDAReport, // Enhanced with mock report data
    socialProof: {
      agreementCount: 127,
      capitalInvested: 340000,
      capitalCapacity: 500000,
      convictionLevel: 'high', // 68% filled
      // Detailed metrics for SocialProofPanel
      recentActivity: [
        { userName: 'Sarah', amount: 500, timeAgo: '2 min ago' },
        { userName: 'Mike', amount: 1200, timeAgo: '5 min ago' },
        { userName: 'Alex', amount: 350, timeAgo: '8 min ago' },
      ],
      avgInvestment: 2680,
      medianInvestment: 1200,
      topInvestment: 15000,
      holdTimePercentage: 78, // 78% hold >7 days
      whaleCount: 3, // 3 investors >$10K
      vsAvgThesis: 2.3, // 2.3x more popular than average
    },
  },
  {
    id: '2',
    title: 'Fed rate cut in Q1 2025?',
    description: 'Federal Reserve will announce at least one interest rate cut during Q1 2025.',
    category: 'finance',
    yesOdds: 45,
    noOdds: 55,
    volume: 1200000,
    liquidity: 420000,
    endsAt: '2025-03-31T23:59:59Z',
    createdAt: '2025-01-01T00:00:00Z',
    status: 'open',
    report: mockAAPLReport, // Enhanced with mock report data
    socialProof: {
      agreementCount: 89,
      capitalInvested: 180000,
      capitalCapacity: 400000,
      convictionLevel: 'medium', // 45% filled
      recentActivity: [
        { userName: 'Jordan', amount: 750, timeAgo: '10 min ago' },
        { userName: 'Emma', amount: 2000, timeAgo: '25 min ago' },
      ],
      avgInvestment: 2022,
      medianInvestment: 950,
      topInvestment: 8500,
      holdTimePercentage: 62,
      whaleCount: 1,
      vsAvgThesis: 1.5,
    },
  },
  {
    id: '3',
    title: 'Tesla stock above $400 by March?',
    description: 'TSLA share price will close above $400 on any trading day before April 1, 2025.',
    category: 'finance',
    yesOdds: 38,
    noOdds: 62,
    volume: 890000,
    liquidity: 315000,
    endsAt: '2025-03-31T23:59:59Z',
    createdAt: '2025-01-05T00:00:00Z',
    status: 'open',
    report: mockNVDAReport, // Enhanced with mock report data
    socialProof: {
      agreementCount: 23,
      capitalInvested: 50000,
      capitalCapacity: 200000,
      convictionLevel: 'low', // 25% filled
      recentActivity: [{ userName: 'Chris', amount: 300, timeAgo: '1h ago' }],
      avgInvestment: 2174,
      medianInvestment: 800,
      topInvestment: 5000,
      holdTimePercentage: 45,
      whaleCount: 0,
      vsAvgThesis: 0.8,
    },
  },
  {
    id: '4',
    title: 'ETH above $5K before BTC halving anniversary?',
    description: 'Ethereum will trade above $5,000 USD before April 20, 2025.',
    category: 'crypto',
    yesOdds: 52,
    noOdds: 48,
    volume: 1800000,
    liquidity: 620000,
    endsAt: '2025-04-20T00:00:00Z',
    createdAt: '2025-01-02T00:00:00Z',
    status: 'open',
    report: mockAAPLReport, // Enhanced with mock report data
    socialProof: {
      agreementCount: 234,
      capitalInvested: 850000,
      capitalCapacity: 1000000,
      convictionLevel: 'high', // 85% filled
      recentActivity: [
        { userName: 'Taylor', amount: 5000, timeAgo: '3 min ago' },
        { userName: 'Jordan', amount: 3500, timeAgo: '15 min ago' },
        { userName: 'Morgan', amount: 2200, timeAgo: '30 min ago' },
      ],
      avgInvestment: 3632,
      medianInvestment: 2500,
      topInvestment: 25000,
      holdTimePercentage: 85,
      whaleCount: 8,
      vsAvgThesis: 4.2,
    },
  },
  {
    id: '5',
    title: 'S&P 500 new all-time high in January?',
    description: 'S&P 500 index will set a new all-time high during January 2025.',
    category: 'finance',
    yesOdds: 71,
    noOdds: 29,
    volume: 3200000,
    liquidity: 980000,
    endsAt: '2025-01-31T23:59:59Z',
    createdAt: '2025-01-01T00:00:00Z',
    status: 'open',
    report: mockAAPLReport, // Enhanced with mock report data
    socialProof: {
      agreementCount: 8,
      capitalInvested: 12000,
      capitalCapacity: 500000,
      convictionLevel: 'early', // 2.4% filled
      recentActivity: [{ userName: 'Pat', amount: 1500, timeAgo: '2h ago' }],
      avgInvestment: 1500,
      medianInvestment: 1200,
      topInvestment: 5000,
      holdTimePercentage: 75,
      whaleCount: 0,
      vsAvgThesis: 0.2,
    },
  },
  {
    id: '6',
    title: 'Apple Vision Pro 2 announced at WWDC?',
    description: 'Apple will announce a second-generation Vision Pro headset at WWDC 2025.',
    category: 'trending',
    yesOdds: 58,
    noOdds: 42,
    volume: 450000,
    liquidity: 180000,
    endsAt: '2025-06-15T00:00:00Z',
    createdAt: '2025-01-10T00:00:00Z',
    status: 'open',
    report: mockNVDAReport, // Enhanced with mock report data
    socialProof: {
      agreementCount: 56,
      capitalInvested: 110000,
      capitalCapacity: 200000,
      convictionLevel: 'medium', // 55% filled
      recentActivity: [
        { userName: 'Casey', amount: 1000, timeAgo: '20 min ago' },
        { userName: 'Riley', amount: 850, timeAgo: '45 min ago' },
      ],
      avgInvestment: 1964,
      medianInvestment: 1100,
      topInvestment: 7500,
      holdTimePercentage: 68,
      whaleCount: 1,
      vsAvgThesis: 1.8,
    },
  },
];
