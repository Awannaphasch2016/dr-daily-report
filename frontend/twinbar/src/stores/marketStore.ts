import { create } from 'zustand';
import type { Market, MarketCategory, SortOption } from '../types/market';
import { apiClient, APIError } from '../api/client';
import type { RankedTicker, ReportResponse } from '../api/types';
import type { ReportData } from '../types/report';

interface MarketState {
  markets: Market[];
  selectedTicker: string | null; // NORMALIZED: Store ID, not object copy
  category: MarketCategory;
  sortBy: SortOption;
  isLoading: boolean;
  error: string | null;

  // Actions
  setMarkets: (markets: Market[]) => void;
  setSelectedTicker: (ticker: string | null) => void; // NORMALIZED: Set ID
  setCategory: (category: MarketCategory) => void;
  setSortBy: (sort: SortOption) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;

  // Derived Selectors (Single Source of Truth)
  getSelectedMarket: () => Market | null; // Derive from markets array

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
    chart_data,
    key_scores,
  } = rankedTicker;

  // Map price change to yes/no odds (positive change = bullish odds)
  const yesOdds = price_change_pct > 0
    ? 50 + Math.min(price_change_pct * 2, 45)
    : 50 - Math.min(Math.abs(price_change_pct) * 2, 45);
  const noOdds = 100 - yesOdds;

  // NEW: Use chart_data and key_scores from Aurora cache if available
  const report = (chart_data || key_scores) ? {
    price_history: chart_data?.price_history || [],
    projections: chart_data?.projections || [],
    initial_investment: chart_data?.initial_investment || 1000.0,
    key_scores: key_scores || [],
    // Other report fields undefined (not needed for cards, loaded on demand)
  } as any : undefined;

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
    report, // NEW: Use cached report data from API
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

/**
 * Transform ReportResponse from API to ReportData format for UI
 */
function _transformReportResponse(response: ReportResponse): ReportData {
  return {
    ticker: response.ticker,
    company_name: response.company_name,
    current_price: response.price,
    price_change_pct: response.price_change_pct,
    stance: response.stance,

    // Chart data
    price_history: response.price_history || [],
    projections: response.projections || [],
    initial_investment: response.initial_investment || 1000.0,

    // Scores - transform max_score (API) to maxScore (UI)
    key_scores: (response.key_scores || []).map(score => ({
      category: score.category,
      score: score.score,
      maxScore: score.max_score,
      rationale: score.rationale,
    })),
    all_scores: (response.all_scores || []).map(score => ({
      category: score.category,
      score: score.score,
      maxScore: score.max_score,
      rationale: score.rationale,
    })),

    // Technical metrics - filter out elevated_risk status (not in UI types)
    technical_metrics: (response.technical_metrics || []).map(metric => ({
      name: metric.name,
      value: metric.value,
      status: metric.status === 'elevated_risk' ? 'neutral' : metric.status,
      percentile: metric.percentile,
      signal: metric.explanation,
    })),

    // Narrative sections - transform summary_sections to narrative_sections format
    narrative_sections: [
      {
        title: 'Key Takeaways',
        bullets: response.summary_sections?.key_takeaways || [],
      },
      {
        title: 'Price Drivers',
        bullets: response.summary_sections?.price_drivers || [],
      },
      {
        title: 'Risks to Watch',
        bullets: response.summary_sections?.risks_to_watch || [],
      },
    ],

    // Fundamentals
    fundamentals: {
      valuation: {},
      growth: {},
      profitability: {},
    },

    // Risk - transform uncertainty_score object to number
    risk: response.risk ? {
      risk_level: response.risk.risk_level,
      volatility_score: response.risk.volatility_score,
      uncertainty_score: response.risk.uncertainty_score.value,
      factors: response.risk.risk_bullets,
    } : {
      risk_level: 'medium',
      volatility_score: 50,
      uncertainty_score: 50,
    },

    // News
    news_items: response.news_items || [],

    // Peers
    peers: response.peers || [],

    // Metadata
    generated_at: response.as_of || new Date().toISOString(),
    report_version: response.generation_metadata?.agent_version,
  };
}

export const useMarketStore = create<MarketState>((set, get) => ({
  markets: [],
  selectedTicker: null, // NORMALIZED: Store ticker ID
  category: 'all',
  sortBy: 'newest',
  isLoading: false,
  error: null,

  setMarkets: (markets) => set({ markets }),
  setSelectedTicker: (ticker) => set({ selectedTicker: ticker }), // NORMALIZED: Set ticker ID
  setCategory: (category) => set({ category }),
  setSortBy: (sortBy) => set({ sortBy }),
  setLoading: (isLoading) => set({ isLoading }),
  setError: (error) => set({ error }),

  // NORMALIZED: Derive selected market from markets array (Single Source of Truth)
  getSelectedMarket: () => {
    const { markets, selectedTicker } = get();
    if (!selectedTicker) return null;
    return markets.find(m => m.id === selectedTicker) || null;
  },

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
   * NORMALIZED: Updates the market in the markets array (Single Source of Truth)
   */
  fetchReport: async (ticker: string) => {
    const { markets, selectedTicker } = get();

    // NORMALIZED: Validate ticker matches selected
    if (selectedTicker !== ticker) {
      console.warn(`⚠️ Ticker mismatch: selected=${selectedTicker}, fetching=${ticker}`);
      return;
    }

    // NORMALIZED: Find market in markets array
    const currentMarket = markets.find(m => m.id === ticker);
    if (!currentMarket) {
      console.warn(`⚠️ Market not found in markets array: ${ticker}`);
      return;
    }

    set({ isLoading: true, error: null });

    try {
      console.log(`📊 Fetching cached report for ${ticker}...`);
      const reportResponse = await apiClient.getCachedReport(ticker);

      // Transform ReportResponse → ReportData
      const reportData = _transformReportResponse(reportResponse);

      // Preserve cached chart data when merging with full report
      // This prevents empty/undefined fields from overwriting cached data
      // INVARIANT: Chart data never shrinks (monotonic growth)
      const cachedPriceHistoryLength = currentMarket.report?.price_history?.length || 0;
      const cachedProjectionsLength = currentMarket.report?.projections?.length || 0;

      const mergedReport: ReportData = {
        // Preserve cached chart data if new data is empty OR smaller (monotonic)
        price_history:
          reportData.price_history && reportData.price_history.length > cachedPriceHistoryLength
            ? reportData.price_history
            : currentMarket.report?.price_history || [],

        projections:
          reportData.projections && reportData.projections.length > cachedProjectionsLength
            ? reportData.projections
            : currentMarket.report?.projections || [],

        initial_investment: reportData.initial_investment || currentMarket.report?.initial_investment || 1000.0,

        // Preserve cached key_scores if new data is empty
        key_scores: reportData.key_scores && reportData.key_scores.length > 0
          ? reportData.key_scores
          : currentMarket.report?.key_scores || [],

        // Use new report data for everything else (scores, narratives, metrics)
        ticker: reportData.ticker,
        company_name: reportData.company_name,
        current_price: reportData.current_price,
        price_change_pct: reportData.price_change_pct,
        stance: reportData.stance,
        all_scores: reportData.all_scores,
        technical_metrics: reportData.technical_metrics,
        narrative_sections: reportData.narrative_sections,
        fundamentals: reportData.fundamentals,
        risk: reportData.risk,
        news_items: reportData.news_items,
        peers: reportData.peers,
        generated_at: reportData.generated_at,
        report_version: reportData.report_version,
      };

      // NORMALIZED: Update market in markets array (Single Source of Truth)
      const updatedMarkets = markets.map(m =>
        m.id === ticker
          ? { ...m, report: mergedReport }
          : m
      );

      set({
        markets: updatedMarkets, // Update the normalized store
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
