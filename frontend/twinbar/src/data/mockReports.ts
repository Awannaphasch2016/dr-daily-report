/**
 * Mock Report Data for TwinBar UI Preview
 *
 * This provides sample data to showcase the UI design in Telegram Mini App
 * without requiring real API calls.
 */

export const mockNVDAReport: any = {
  ticker: 'NVDA',
  companyName: 'NVIDIA Corporation',

  narrative: `**NVIDIA Corporation** continues to dominate the AI chip market with unprecedented demand for its H100 and upcoming H200 GPUs. The company's data center revenue has surged 279% year-over-year, driven by massive investments from cloud providers and enterprises building AI infrastructure.

However, valuation concerns are mounting as the stock trades at 25x forward sales. Competition from AMD and custom chips by hyperscalers (Google's TPU, Amazon's Trainium) could erode margins. Export restrictions to China also pose geopolitical risks.

**Investment Thesis:** Strong buy for AI exposure, but consider taking profits above $140 given stretched valuations. The long-term AI secular trend remains intact, but near-term volatility expected as market digests competition and regulatory headwinds.`,

  keyTakeaways: [
    'Data center revenue up 279% YoY - AI infrastructure boom',
    'H100 supply constraints easing, H200 launch imminent',
    'Trading at 25x forward sales - historically expensive',
    'Competition intensifying from AMD and custom hyperscaler chips',
  ],

  technicalAnalysis: {
    trend: 'Bullish',
    support: 485,
    resistance: 505,
    rsi: 68,
    macd: 'Positive momentum',
    signals: [
      { indicator: 'RSI (68)', signal: 'Neutral', strength: 'medium' },
      { indicator: 'MACD', signal: 'Buy', strength: 'strong' },
      { indicator: '50-day MA', signal: 'Buy', strength: 'strong' },
      { indicator: 'Volume', signal: 'Above average', strength: 'medium' },
    ],
  },

  fundamentalMetrics: [
    { label: 'P/E Ratio', value: '65.2', change: '+5%', status: 'elevated' },
    { label: 'Revenue Growth', value: '206%', change: '+15%', status: 'strong' },
    { label: 'Gross Margin', value: '75%', change: '+2%', status: 'excellent' },
    { label: 'Free Cash Flow', value: '$12.5B', change: '+180%', status: 'strong' },
  ],

  riskFactors: [
    'Valuation risk: Trading at premium multiples',
    'Competitive threats from AMD and custom chips',
    'China export restrictions impact 20% of revenue',
    'Hyperscaler customers developing in-house alternatives',
  ],

  analystConsensus: {
    rating: 'Strong Buy',
    priceTarget: 525,
    upside: 7.5,
    numberOfAnalysts: 42,
    distribution: { buy: 38, hold: 4, sell: 0 },
  },

  socialProofMetrics: {
    agreementScore: 85,
    capitalInvested: 2400000,
    capitalCapacity: 3000000,
    convictionLevel: 'high',
    recentActivity: [
      { userName: 'Alex_Trades', amount: 5000, timeAgo: '2 min ago' },
      { userName: 'Sarah_K', amount: 12000, timeAgo: '8 min ago' },
      { userName: 'Mike_Investor', amount: 3500, timeAgo: '15 min ago' },
    ],
  },
};

export const mockAAPLReport: any = {
  ticker: 'AAPL',
  companyName: 'Apple Inc.',

  narrative: `**Apple Inc.** faces a transitional period as iPhone growth slows but Services revenue accelerates. The company's Services segment (iCloud, Apple Music, App Store) now generates $85B annually at 70% gross margins, providing a stable revenue base.

The Vision Pro launch represents Apple's bet on spatial computing, but initial sales have been tepid at $3,500 price point. More concerning is China weakness - revenue down 8% YoY as Huawei's resurgence and nationalist sentiment impact market share.

**Investment Thesis:** Hold for dividend income and Services growth. The stock trades at 28x earnings - reasonable for quality but limited upside. Wait for pullback to $170 for accumulation. Long-term, AR/VR and India manufacturing shift are positive catalysts.`,

  keyTakeaways: [
    'Services revenue $85B annually at 70% margins - growth engine',
    'iPhone sales flat, China revenue down 8% YoY',
    'Vision Pro sales disappointing - needs price cut or killer app',
    'Trading at 28x P/E - fair value, limited upside near-term',
  ],

  technicalAnalysis: {
    trend: 'Sideways',
    support: 170,
    resistance: 185,
    rsi: 52,
    macd: 'Neutral',
    signals: [
      { indicator: 'RSI (52)', signal: 'Neutral', strength: 'low' },
      { indicator: 'MACD', signal: 'Neutral', strength: 'low' },
      { indicator: '200-day MA', signal: 'Support', strength: 'medium' },
      { indicator: 'Volume', signal: 'Below average', strength: 'low' },
    ],
  },

  fundamentalMetrics: [
    { label: 'P/E Ratio', value: '28.3', change: '-2%', status: 'fair' },
    { label: 'Revenue Growth', value: '2%', change: '-3%', status: 'slow' },
    { label: 'Services Margin', value: '70%', change: '+1%', status: 'excellent' },
    { label: 'Buyback Yield', value: '3.2%', change: '0%', status: 'good' },
  ],

  riskFactors: [
    'China revenue declining - geopolitical + competition',
    'iPhone upgrade cycles lengthening',
    'Vision Pro adoption slower than expected',
    'Regulatory scrutiny on App Store fees (EU DMA)',
  ],

  analystConsensus: {
    rating: 'Hold',
    priceTarget: 185,
    upside: 3.2,
    numberOfAnalysts: 38,
    distribution: { buy: 18, hold: 18, sell: 2 },
  },

  socialProofMetrics: {
    agreementScore: 58,
    capitalInvested: 950000,
    capitalCapacity: 2000000,
    convictionLevel: 'medium',
    recentActivity: [
      { userName: 'DividendKing', amount: 8000, timeAgo: '12 min ago' },
      { userName: 'TechBull22', amount: 2500, timeAgo: '1h ago' },
    ],
  },
};
