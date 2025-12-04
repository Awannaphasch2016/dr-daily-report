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
