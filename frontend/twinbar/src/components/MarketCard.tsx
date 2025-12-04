import type { Market } from '../types/market';
import { formatVolume, formatEndsAt } from '../lib/format';

interface MarketCardProps {
  market: Market;
  onSelect: (market: Market) => void;
  onBuy: (marketId: string, outcome: 'yes' | 'no') => void;
}

export function MarketCard({ market, onSelect, onBuy }: MarketCardProps) {
  return (
    <div
      className="market-card bg-[var(--color-bg)] border border-[var(--color-border)] rounded-xl p-4 cursor-pointer transition-all hover:shadow-lg hover:-translate-y-0.5 hover:border-[var(--color-primary-light)]"
      data-market-id={market.id}
    >
      {market.image && (
        <img
          src={market.image}
          alt=""
          className="market-image w-full h-28 object-cover rounded-lg mb-3 bg-[var(--color-bg-secondary)]"
        />
      )}

      <div
        className="market-title text-base font-semibold mb-2 leading-snug line-clamp-2 cursor-pointer"
        onClick={() => onSelect(market)}
      >
        {market.title}
      </div>

      <div className="market-meta flex items-center gap-4 mb-4 text-xs text-[var(--color-text-secondary)]">
        <span className="market-volume">Vol: {formatVolume(market.volume)}</span>
        {market.endsAt && (
          <span className="market-ends">Ends {formatEndsAt(market.endsAt)}</span>
        )}
      </div>

      <div className="market-outcomes flex gap-2">
        <button
          className="outcome-btn yes flex-1 flex flex-col items-center py-2 px-4 rounded-lg font-semibold transition-colors bg-[var(--color-yes-light)] text-[var(--color-yes)] border border-[var(--color-yes)] hover:bg-[var(--color-yes)] hover:text-white"
          data-outcome="yes"
          data-market-id={market.id}
          onClick={(e) => {
            e.stopPropagation();
            onBuy(market.id, 'yes');
          }}
        >
          <span className="outcome-label text-sm">Yes</span>
          <span className="outcome-odds text-lg font-bold">{market.yesOdds}¢</span>
        </button>

        <button
          className="outcome-btn no flex-1 flex flex-col items-center py-2 px-4 rounded-lg font-semibold transition-colors bg-[var(--color-no-light)] text-[var(--color-no)] border border-[var(--color-no)] hover:bg-[var(--color-no)] hover:text-white"
          data-outcome="no"
          data-market-id={market.id}
          onClick={(e) => {
            e.stopPropagation();
            onBuy(market.id, 'no');
          }}
        >
          <span className="outcome-label text-sm">No</span>
          <span className="outcome-odds text-lg font-bold">{market.noOdds}¢</span>
        </button>
      </div>
    </div>
  );
}
