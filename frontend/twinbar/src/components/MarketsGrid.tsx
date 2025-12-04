import type { Market } from '../types/market';
import { MarketCard } from './MarketCard';

interface MarketsGridProps {
  markets: Market[];
  isLoading: boolean;
  onSelect: (market: Market) => void;
  onBuy: (marketId: string, outcome: 'yes' | 'no') => void;
}

export function MarketsGrid({ markets, isLoading, onSelect, onBuy }: MarketsGridProps) {
  if (isLoading) {
    return (
      <div className="loading-indicator flex flex-col items-center justify-center py-12 gap-4 text-[var(--color-text-secondary)]">
        <div className="spinner w-8 h-8 border-3 border-[var(--color-bg-secondary)] border-t-[var(--color-primary)] rounded-full animate-spin" />
        <span>Loading markets...</span>
      </div>
    );
  }

  if (!markets.length) {
    return (
      <div className="empty-state flex flex-col items-center justify-center py-12 text-center text-[var(--color-text-secondary)]">
        <span className="text-5xl mb-4">🔍</span>
        <p>No markets found</p>
        <p className="text-sm">Try a different category or search</p>
      </div>
    );
  }

  return (
    <div id="markets-grid" className="markets-grid grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      {markets.map((market) => (
        <MarketCard
          key={market.id}
          market={market}
          onSelect={onSelect}
          onBuy={onBuy}
        />
      ))}
    </div>
  );
}
