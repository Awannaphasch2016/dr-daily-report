/**
 * Type definitions for enhanced trading report data
 * Maps to backend ReportResponse from src/api/models.py
 */

/**
 * Technical indicator metric with status and percentiles
 */
export interface TechnicalMetric {
  name: string; // e.g., "RSI", "MACD", "SMA_20"
  value: number;
  status: 'bullish' | 'bearish' | 'neutral';
  percentile?: number; // Historical percentile (0-100)
  signal?: string; // Human-readable signal description
  color?: string; // For UI color coding
}

/**
 * Scoring metric for quick intuition (fundamental, risk, liquidity, etc.)
 */
export interface ScoringMetric {
  category: string; // e.g., "Fundamental", "Selling Pressure", "Liquidity"
  score: number; // 0-10 scale
  maxScore: number; // Usually 10
  rationale?: string; // Expandable explanation
  color?: string; // Dynamic color based on score
}

/**
 * LLM narrative section (bullet points + full report)
 */
export interface NarrativeSection {
  title: string; // e.g., "Key Takeaways", "Risks", "Opportunities"
  bullets: string[]; // Clickable bullet points
  fullText?: string; // Expandable full report text
  sources?: NewsItem[]; // Related news sources
}

/**
 * Fundamental metrics (valuation, growth, profitability)
 */
export interface Fundamentals {
  valuation: {
    pe_ratio?: number;
    pb_ratio?: number;
    ps_ratio?: number;
    ev_ebitda?: number;
  };
  growth: {
    revenue_growth?: number;
    earnings_growth?: number;
    eps_growth?: number;
  };
  profitability: {
    profit_margin?: number;
    roe?: number;
    roa?: number;
    roic?: number;
  };
}

/**
 * Risk assessment metrics
 */
export interface Risk {
  risk_level: 'low' | 'medium' | 'high';
  volatility_score: number; // 0-100
  uncertainty_score: number; // 0-100
  factors?: string[]; // Risk factors list
}

/**
 * News item with sentiment
 */
export interface NewsItem {
  title: string;
  url: string;
  source: string;
  published_at?: string;
  sentiment?: 'positive' | 'negative' | 'neutral';
  relevance_score?: number; // 0-100
}

/**
 * Peer/related company for comparison
 */
export interface Peer {
  ticker: string;
  company_name: string;
  correlation?: number; // Price correlation coefficient
  sector?: string;
  market_cap?: number;
}

/**
 * Price data point for charting
 * Extended to support portfolio return tracking and projections
 */
export interface PriceDataPoint {
  date: string; // ISO date
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;

  // Portfolio metrics for MiniChart dual Y-axis display
  return_pct?: number; // Algorithm return % from entry point (e.g., 8.5 = 8.5%)
  portfolio_nav?: number; // Portfolio NAV in dollars (e.g., 1085 = $1,085)
  is_projection?: boolean; // True if future projection, false if historical data
}

/**
 * Projection confidence band for future return scenarios
 * Used in MiniChart to show statistical confidence intervals (±1 std dev)
 */
export interface ProjectionBand {
  date: string; // ISO date (future date)
  expected_return: number; // Expected trajectory (trend line) in %
  best_case_return: number; // Upper band (+1 std dev) in %
  worst_case_return: number; // Lower band (-1 std dev) in %
  expected_nav: number; // Expected portfolio NAV in dollars
  best_case_nav: number; // Best case portfolio NAV in dollars
  worst_case_nav: number; // Worst case portfolio NAV in dollars
}

/**
 * Complete report data structure
 * Extends Market with comprehensive trading decision information
 */
export interface ReportData {
  ticker: string;
  company_name: string;
  current_price: number;
  price_change_pct: number;
  stance: 'bullish' | 'bearish' | 'neutral'; // Overall recommendation

  // Charting data
  price_history: PriceDataPoint[]; // Historical OHLCV data with portfolio metrics
  projections?: ProjectionBand[]; // 7-day future projections (optional)
  initial_investment?: number; // Starting portfolio value for NAV calculation (default: 1000)

  // Key scores (for card display)
  key_scores: ScoringMetric[]; // Top 3-5 most important scores

  // All scores (for modal scoring panel)
  all_scores: ScoringMetric[];

  // Technical analysis
  technical_metrics: TechnicalMetric[];

  // LLM narrative
  narrative_sections: NarrativeSection[];

  // Fundamentals
  fundamentals: Fundamentals;

  // Risk assessment
  risk: Risk;

  // News & sources
  news_items: NewsItem[];

  // Related trades/peers
  peers: Peer[];

  // Metadata
  generated_at: string; // ISO timestamp
  report_version?: string;
}

/**
 * Report loading states for UI
 */
export type ReportLoadingState = 'idle' | 'loading' | 'success' | 'error';

/**
 * Report error details
 */
export interface ReportError {
  code: string;
  message: string;
  details?: string;
}
