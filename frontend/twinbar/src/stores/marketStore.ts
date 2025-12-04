import { create } from 'zustand';
import type { Market, MarketCategory, SortOption } from '../types/market';

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
}

export const useMarketStore = create<MarketState>((set) => ({
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
}));

// Mock data for development
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
  },
];
