import type { ReportData } from './report';

export interface RecentActivity {
  userName: string;
  amount: number;
  timeAgo: string; // e.g., "2 min ago"
}

export interface SocialProof {
  agreementCount: number; // Number of people who agreed
  capitalInvested: number; // Total capital invested (USD)
  capitalCapacity: number; // Max capacity algorithm can absorb (USD)
  convictionLevel: 'high' | 'medium' | 'low' | 'early'; // Derived from % filled + hold time

  // Detailed metrics for SocialProofPanel
  recentActivity?: RecentActivity[]; // Recent agreements
  avgInvestment?: number; // Average investment amount
  medianInvestment?: number; // Median investment amount
  topInvestment?: number; // Largest single investment
  holdTimePercentage?: number; // % of investors holding >7 days
  whaleCount?: number; // Number of investors >$10K
  vsAvgThesis?: number; // Multiplier vs average thesis (e.g., 2.3 = 2.3x more popular)
}

export interface Market {
  id: string;
  title: string;
  description?: string;
  category: MarketCategory;
  image?: string;
  yesOdds: number;
  noOdds: number;
  volume: number;
  liquidity: number;
  endsAt?: string;
  createdAt: string;
  status: 'open' | 'closed' | 'resolved';
  resolution?: 'yes' | 'no' | null;
  // Enhanced trading data (loaded on demand)
  report?: ReportData;
  socialProof?: SocialProof; // Social commitment metrics
}

export type MarketCategory =
  | 'all'
  | 'trending'
  | 'finance'
  | 'crypto'
  | 'politics'
  | 'sports';

export type SortOption = 'newest' | 'volume' | 'ending';

export interface Position {
  marketId: string;
  outcome: 'yes' | 'no';
  shares: number;
  avgPrice: number;
  currentValue: number;
}

export interface User {
  id: string;
  balance: number;
  positions: Position[];
}
