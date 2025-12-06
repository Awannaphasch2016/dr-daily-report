/**
 * Mock report data for testing enhanced UI
 * Simulates backend ReportResponse structure
 */

import type { ReportData, PriceDataPoint } from '../types/report';

/**
 * Generate mock price history (30 days of OHLCV data)
 */
function generateMockPriceHistory(basePrice: number, trend: 'up' | 'down' | 'sideways'): PriceDataPoint[] {
  const data: PriceDataPoint[] = [];
  const now = new Date();
  let currentPrice = basePrice;

  for (let i = 30; i >= 0; i--) {
    const date = new Date(now);
    date.setDate(date.getDate() - i);

    // Random volatility
    const volatility = currentPrice * 0.02; // 2% daily volatility
    const change = (Math.random() - 0.5) * volatility;

    // Apply trend bias
    let trendBias = 0;
    if (trend === 'up') trendBias = volatility * 0.3;
    else if (trend === 'down') trendBias = -volatility * 0.3;

    const open = currentPrice;
    const close = currentPrice + change + trendBias;
    const high = Math.max(open, close) + Math.random() * volatility * 0.5;
    const low = Math.min(open, close) - Math.random() * volatility * 0.5;
    const volume = Math.floor(1000000 + Math.random() * 500000);

    data.push({
      date: date.toISOString().split('T')[0],
      open: Number(open.toFixed(2)),
      high: Number(high.toFixed(2)),
      low: Number(low.toFixed(2)),
      close: Number(close.toFixed(2)),
      volume,
    });

    currentPrice = close;
  }

  return data;
}

/**
 * Mock report for NVDA (bullish example)
 */
export const mockNVDAReport: ReportData = {
  ticker: 'NVDA',
  company_name: 'NVIDIA Corporation',
  current_price: 495.50,
  price_change_pct: 2.35,
  stance: 'bullish',

  price_history: generateMockPriceHistory(485, 'up'),

  key_scores: [
    {
      category: 'Fundamental Score',
      score: 9,
      maxScore: 10,
      rationale: 'Strong revenue growth (265% YoY), dominant GPU market position, AI leadership',
      color: '#10b981', // green
    },
    {
      category: 'Selling Pressure',
      score: 3,
      maxScore: 10,
      rationale: 'Low institutional selling, insider buying signals confidence',
      color: '#10b981', // green (low is good)
    },
    {
      category: 'Liquidity',
      score: 8,
      maxScore: 10,
      rationale: 'High daily volume ($45B), tight spreads, easy entry/exit',
      color: '#10b981', // green
    },
  ],

  all_scores: [
    {
      category: 'Fundamental Score',
      score: 9,
      maxScore: 10,
      rationale: 'Strong revenue growth (265% YoY), dominant GPU market position, AI leadership',
    },
    {
      category: 'Selling Pressure',
      score: 3,
      maxScore: 10,
      rationale: 'Low institutional selling, insider buying signals confidence',
    },
    {
      category: 'Liquidity',
      score: 8,
      maxScore: 10,
      rationale: 'High daily volume ($45B), tight spreads, easy entry/exit',
    },
    {
      category: 'Technical Momentum',
      score: 8,
      maxScore: 10,
      rationale: 'RSI at 62 (strong but not overbought), MACD bullish crossover',
    },
    {
      category: 'Valuation',
      score: 6,
      maxScore: 10,
      rationale: 'Premium valuation justified by growth, but vulnerable to corrections',
    },
    {
      category: 'Risk Level',
      score: 6,
      maxScore: 10,
      rationale: 'Moderate volatility, sector rotation risk, high expectations',
    },
  ],

  technical_metrics: [
    {
      name: 'RSI (14)',
      value: 62.3,
      status: 'bullish',
      percentile: 68,
      signal: 'Strong momentum, not overbought',
      color: '#10b981',
    },
    {
      name: 'MACD',
      value: 1.25,
      status: 'bullish',
      percentile: 72,
      signal: 'Bullish crossover confirmed',
      color: '#10b981',
    },
    {
      name: 'SMA 20/50',
      value: 1.08,
      status: 'bullish',
      percentile: 65,
      signal: 'Price above both moving averages',
      color: '#10b981',
    },
    {
      name: 'Volume Trend',
      value: 125,
      status: 'bullish',
      percentile: 78,
      signal: 'Above average volume supporting uptrend',
      color: '#10b981',
    },
  ],

  narrative_sections: [
    {
      title: 'Key Takeaways',
      bullets: [
        'Stocks You Usually Buy - AI/Tech growth plays with strong fundamentals',
        'Yuanta Recommendation - Upgraded to "Strong Buy" with $550 target',
        'Fundamentally Sound - Revenue +265% YoY, gross margin 75%+',
        'New Sector In Your Portfolio Helps Improve Diversification Exposure',
        'Benefits from lowering interest rate - Reduces cost of capital for expansion',
        'Good Bet If Trump Wins - Pro-tech policies, reduced regulation',
      ],
      fullText: `NVIDIA continues to dominate the AI accelerator market with 80%+ market share...

Recent developments:
- H100 GPU demand remains strong despite competition
- B100 (Blackwell) launch scheduled for Q4 2024
- Cloud partnerships with MSFT, GOOGL, AMZN expanding
- Automotive AI division growing 15% sequentially

Technical Setup:
- Broke above $490 resistance with strong volume
- Pattern: Ascending triangle breakout (target $520)
- Support levels: $480 (SMA20), $470 (SMA50)
- Resistance: $500 psychological, $520 measured move`,
    },
    {
      title: 'Risks to Consider',
      bullets: [
        'Valuation risk - PE ratio of 65x, vulnerable to market corrections',
        'Competition heating up - AMD MI300X gaining traction',
        'China export restrictions - 25% of revenue at risk',
        'High expectations - Must maintain 200%+ growth rate',
      ],
      fullText: 'Despite strong fundamentals, NVDA faces execution risks...',
    },
  ],

  fundamentals: {
    valuation: {
      pe_ratio: 65.2,
      pb_ratio: 28.5,
      ps_ratio: 22.3,
      ev_ebitda: 48.7,
    },
    growth: {
      revenue_growth: 265.2,
      earnings_growth: 422.5,
      eps_growth: 420.8,
    },
    profitability: {
      profit_margin: 55.2,
      roe: 85.3,
      roa: 65.8,
      roic: 72.4,
    },
  },

  risk: {
    risk_level: 'medium',
    volatility_score: 65,
    uncertainty_score: 58,
    factors: [
      'High valuation multiples',
      'Sector rotation risk',
      'Geopolitical (China export restrictions)',
      'Competition from AMD, Intel',
    ],
  },

  news_items: [
    {
      title: 'NVIDIA H100 GPU Demand Remains Strong Despite Competition',
      url: 'https://example.com/nvda-h100-demand',
      source: 'Reuters',
      published_at: '2024-01-15T10:30:00Z',
      sentiment: 'positive',
      relevance_score: 95,
    },
    {
      title: 'AMD Launches MI300X to Challenge NVIDIA in AI Market',
      url: 'https://example.com/amd-mi300x',
      source: 'Bloomberg',
      published_at: '2024-01-14T14:20:00Z',
      sentiment: 'negative',
      relevance_score: 78,
    },
    {
      title: 'Cloud Giants Expand NVIDIA GPU Orders for AI Infrastructure',
      url: 'https://example.com/cloud-gpu-orders',
      source: 'Wall Street Journal',
      published_at: '2024-01-13T09:15:00Z',
      sentiment: 'positive',
      relevance_score: 88,
    },
  ],

  peers: [
    { ticker: 'AMD', company_name: 'Advanced Micro Devices', correlation: 0.78, sector: 'Semiconductors' },
    { ticker: 'AVGO', company_name: 'Broadcom Inc', correlation: 0.72, sector: 'Semiconductors' },
    { ticker: 'TSM', company_name: 'Taiwan Semiconductor', correlation: 0.68, sector: 'Semiconductors' },
    { ticker: 'INTC', company_name: 'Intel Corporation', correlation: 0.65, sector: 'Semiconductors' },
    { ticker: 'QCOM', company_name: 'Qualcomm Inc', correlation: 0.62, sector: 'Semiconductors' },
  ],

  generated_at: new Date().toISOString(),
  report_version: 'v1.0-mock',
};

/**
 * Mock report for AAPL (neutral example)
 */
export const mockAAPLReport: ReportData = {
  ticker: 'AAPL',
  company_name: 'Apple Inc',
  current_price: 185.25,
  price_change_pct: -0.45,
  stance: 'neutral',

  price_history: generateMockPriceHistory(185, 'sideways'),

  key_scores: [
    {
      category: 'Fundamental Score',
      score: 7,
      maxScore: 10,
      rationale: 'Stable business, strong brand, but slowing iPhone growth',
      color: '#f59e0b', // amber
    },
    {
      category: 'Selling Pressure',
      score: 5,
      maxScore: 10,
      rationale: 'Moderate selling from funds rebalancing',
      color: '#f59e0b', // amber
    },
    {
      category: 'Liquidity',
      score: 9,
      maxScore: 10,
      rationale: 'Highest liquidity in market, easy entry/exit',
      color: '#10b981', // green
    },
  ],

  all_scores: [
    {
      category: 'Fundamental Score',
      score: 7,
      maxScore: 10,
      rationale: 'Stable business, strong brand, but slowing iPhone growth',
    },
    {
      category: 'Selling Pressure',
      score: 5,
      maxScore: 10,
      rationale: 'Moderate selling from funds rebalancing',
    },
    {
      category: 'Liquidity',
      score: 9,
      maxScore: 10,
      rationale: 'Highest liquidity in market, easy entry/exit',
    },
    {
      category: 'Technical Momentum',
      score: 5,
      maxScore: 10,
      rationale: 'RSI at 48 (neutral), consolidating in range',
    },
    {
      category: 'Valuation',
      score: 6,
      maxScore: 10,
      rationale: 'Fair valuation at 28x PE, premium to market but justified',
    },
  ],

  technical_metrics: [
    {
      name: 'RSI (14)',
      value: 48.2,
      status: 'neutral',
      percentile: 52,
      signal: 'Neutral momentum, range-bound',
      color: '#6b7280',
    },
    {
      name: 'MACD',
      value: -0.15,
      status: 'bearish',
      percentile: 42,
      signal: 'Slight bearish divergence',
      color: '#ef4444',
    },
    {
      name: 'SMA 20/50',
      value: 0.98,
      status: 'neutral',
      percentile: 48,
      signal: 'Price near moving averages',
      color: '#6b7280',
    },
  ],

  narrative_sections: [
    {
      title: 'Key Takeaways',
      bullets: [
        'Wait-and-see mode - Consolidating after recent run-up',
        'iPhone 15 sales mixed - China weakness offset by US strength',
        'Services revenue strong - Growing 15% YoY, high margin business',
        'Vision Pro launch upcoming - New product cycle catalyst',
      ],
      fullText: 'Apple is in consolidation mode after strong 2023 performance...',
    },
  ],

  fundamentals: {
    valuation: {
      pe_ratio: 28.5,
      pb_ratio: 42.8,
      ps_ratio: 7.2,
    },
    growth: {
      revenue_growth: 2.8,
      earnings_growth: 8.5,
    },
    profitability: {
      profit_margin: 25.3,
      roe: 162.5,
      roa: 28.5,
    },
  },

  risk: {
    risk_level: 'low',
    volatility_score: 35,
    uncertainty_score: 42,
    factors: ['China revenue concentration', 'Product cycle dependency'],
  },

  news_items: [
    {
      title: 'Apple iPhone 15 Sales Meet Expectations in US Market',
      url: 'https://example.com/iphone-15-sales',
      source: 'CNBC',
      sentiment: 'neutral',
      relevance_score: 85,
    },
  ],

  peers: [
    { ticker: 'MSFT', company_name: 'Microsoft Corporation', correlation: 0.65 },
    { ticker: 'GOOGL', company_name: 'Alphabet Inc', correlation: 0.62 },
  ],

  generated_at: new Date().toISOString(),
  report_version: 'v1.0-mock',
};

/**
 * Map ticker to mock report
 */
export const mockReportsMap: Record<string, ReportData> = {
  NVDA: mockNVDAReport,
  AAPL: mockAAPLReport,
};

/**
 * Get mock report by ticker (simulates API call)
 */
export function getMockReport(ticker: string): ReportData | null {
  return mockReportsMap[ticker.toUpperCase()] || null;
}
