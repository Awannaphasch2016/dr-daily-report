/**
 * TypeScript types matching backend Pydantic models
 *
 * These types mirror the API response structures from src/api/models.py
 * to provide type safety for frontend API calls.
 */

// ============================================================================
// Search Types
// ============================================================================

export interface SearchResult {
  ticker: string;
  company_name: string;
  exchange: string;
  currency: string;
  type: 'equity' | 'etf' | 'fund';
}

export interface SearchResponse {
  results: SearchResult[];
}

// ============================================================================
// Report Types
// ============================================================================

export interface SummarySections {
  key_takeaways: string[];
  price_drivers: string[];
  risks_to_watch: string[];
}

export interface TechnicalMetric {
  name: string;
  value: number;
  percentile: number;
  category: 'momentum' | 'trend' | 'volatility' | 'liquidity';
  status: 'bullish' | 'bearish' | 'neutral' | 'elevated_risk';
  explanation: string;
}

export interface FundamentalMetric {
  name: string;
  value: number;
  percentile?: number;
  comment: string;
}

export interface Fundamentals {
  valuation: FundamentalMetric[];
  growth: FundamentalMetric[];
  profitability: FundamentalMetric[];
}

export interface NewsItem {
  title: string;
  url: string;
  source: string;
  published_at: string; // ISO datetime string
  sentiment_label: 'positive' | 'neutral' | 'negative';
  sentiment_score: number; // 0-1
}

export interface OverallSentiment {
  positive_pct: number; // 0-100
  neutral_pct: number; // 0-100
  negative_pct: number; // 0-100
}

export interface UncertaintyScore {
  value: number; // 0-100
  percentile: number;
}

export interface Risk {
  risk_level: 'low' | 'medium' | 'high';
  volatility_score: number;
  uncertainty_score: UncertaintyScore;
  risk_bullets: string[];
}

export interface Peer {
  ticker: string;
  company_name: string;
  estimated_upside_pct?: number;
  stance: 'bullish' | 'bearish' | 'neutral';
  valuation_label: 'cheap' | 'fair' | 'expensive';
}

export interface GenerationMetadata {
  agent_version: string;
  strategy: string;
  generated_at: string; // ISO datetime string
  cache_hit: boolean;
}

export interface ReportResponse {
  // Basic info
  ticker: string;
  company_name: string;
  price: number;
  price_change_pct: number;
  currency: string;
  as_of: string; // ISO datetime string

  // Investment stance
  stance: 'bullish' | 'bearish' | 'neutral';
  estimated_upside_pct?: number;
  confidence: 'high' | 'medium' | 'low';
  investment_horizon: string;

  // Full narrative report (Thai language)
  narrative_report: string;

  // Report sections
  summary_sections: SummarySections;
  technical_metrics: TechnicalMetric[];
  fundamentals: Fundamentals;
  news_items: NewsItem[];
  overall_sentiment: OverallSentiment;
  risk: Risk;
  peers: Peer[];

  // Price history and projections
  price_history: PriceDataPoint[];
  projections: ProjectionBand[];
  initial_investment: number;

  // Investment scores
  key_scores: ScoringMetric[]; // Top 3 scores
  all_scores: ScoringMetric[]; // All 5-6 scores

  // Additional data
  data_sources: string[];
  pdf_report_url?: string;
  generation_metadata: GenerationMetadata;
}

// ============================================================================
// Rankings Types
// ============================================================================

export interface ScoringMetric {
  category: string;
  score: number;
  max_score: number;
  rationale?: string;
}

export interface PriceDataPoint {
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  return_pct?: number;
  portfolio_nav?: number;
  is_projection?: boolean;
}

export interface ProjectionBand {
  date: string;
  expected_return: number;
  best_case_return: number;
  worst_case_return: number;
  expected_nav: number;
  best_case_nav: number;
  worst_case_nav: number;
}

export interface ChartData {
  price_history: PriceDataPoint[];
  projections: ProjectionBand[];
  initial_investment: number;
}

export interface RankedTicker {
  ticker: string;
  company_name: string;
  price: number;
  price_change_pct: number;
  currency: string;
  stance?: 'bullish' | 'bearish' | 'neutral';
  estimated_upside_pct?: number;
  risk_level?: 'low' | 'medium' | 'high';

  // NEW: Lightweight report data from Aurora cache
  chart_data?: ChartData;
  key_scores?: ScoringMetric[];
}

export interface RankingsResponse {
  category: 'top_gainers' | 'top_losers' | 'volume_surge' | 'trending';
  as_of: string; // ISO datetime string
  tickers: RankedTicker[];
}

// ============================================================================
// Watchlist Types
// ============================================================================

export interface WatchlistItem {
  ticker: string;
  company_name: string;
  added_at: string; // ISO datetime string
}

export interface WatchlistResponse {
  tickers: WatchlistItem[];
}

export interface WatchlistAddRequest {
  ticker: string;
}

export interface WatchlistOperationResponse {
  status: 'ok';
  ticker: string;
}

// ============================================================================
// Async Job Types
// ============================================================================

export interface JobSubmitResponse {
  job_id: string;
  status: 'pending' | 'completed'; // 'completed' for cache hits
}

export interface JobStatusResponse {
  job_id: string;
  ticker: string;
  status: 'pending' | 'in_progress' | 'completed' | 'failed';
  created_at: string; // ISO datetime string
  started_at?: string; // ISO datetime string
  finished_at?: string; // ISO datetime string
  result?: Record<string, any>; // ReportResponse when completed
  error?: string;
}

// ============================================================================
// Error Types
// ============================================================================

export interface ErrorDetail {
  ticker?: string;
  field?: string;
}

export interface ErrorResponse {
  code: string;
  message: string;
  details?: ErrorDetail;
}

export interface ErrorEnvelope {
  error: ErrorResponse;
}

// ============================================================================
// API Client Error Class
// ============================================================================

export class APIError extends Error {
  code: string;
  statusCode: number;
  details?: ErrorDetail;

  constructor(
    code: string,
    message: string,
    statusCode: number,
    details?: ErrorDetail
  ) {
    super(message);
    this.name = 'APIError';
    this.code = code;
    this.statusCode = statusCode;
    this.details = details;
  }
}
