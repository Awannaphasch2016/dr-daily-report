import type { Market } from '../types/market';
import { formatVolume, formatEndsAt } from '../lib/format';
import { MiniChart } from './MiniChart';
import { ScoreTable } from './ScoreTable';
import { SocialProofBar } from './SocialProofBar';
import { AgreeButton } from './AgreeButton';

interface MarketCardProps {
  market: Market;
  onSelect: (market: Market) => void;
  onBuy: (marketId: string, outcome: 'yes' | 'no') => void;
  onAgree?: (marketId: string) => void; // New: Handle single "Agree" action
}

export function MarketCard({ market, onSelect, onBuy, onAgree }: MarketCardProps) {
  return (
    <div
      className="market-card bg-[var(--color-bg)] border border-[var(--color-border)] rounded-xl p-4 cursor-pointer transition-all hover:shadow-lg hover:-translate-y-0.5 hover:border-[var(--color-primary-light)]"
      data-market-id={market.id}
      onClick={() => onSelect(market)}
    >
      {market.image && (
        <img
          src={market.image}
          alt=""
          className="market-image w-full h-28 object-cover rounded-lg mb-3 bg-[var(--color-bg-secondary)]"
        />
      )}

      <div
        className="market-title text-base font-semibold mb-3 leading-snug line-clamp-2"
      >
        {market.title}
      </div>

      {/* HORIZONTAL LAYOUT: Chart LEFT (40%), Score Table RIGHT (60%) */}
      {market.report && (
        <div data-testid="horizontal-content" className="flex gap-3 mb-3">
          {/* LEFT: Mini Chart (40% width) */}
          {market.report.price_history && market.report.price_history.length > 0 && (
            <div className="w-2/5 flex-shrink-0">
              <MiniChart data={market.report.price_history} stance={market.report.stance} />
            </div>
          )}

          {/* RIGHT: Score Table (60% width) */}
          {market.report.key_scores && market.report.key_scores.length > 0 && (
            <div className="flex-1">
              <ScoreTable scores={market.report.key_scores.slice(0, 5)} />
            </div>
          )}
        </div>
      )}

      <div className="market-meta flex items-center gap-4 mb-4 text-xs text-[var(--color-text-secondary)]">
        <span className="market-volume">Vol: {formatVolume(market.volume)}</span>
        {market.endsAt && (
          <span className="market-ends">Ends {formatEndsAt(market.endsAt)}</span>
        )}
      </div>

      {/* Social Proof Bar - Show agreement count & capital commitment */}
      {market.socialProof && <SocialProofBar socialProof={market.socialProof} />}

      {/* Agree Button - Single asymmetric commitment action */}
      <div className="mt-4" onClick={(e) => e.stopPropagation()}>
        <AgreeButton
          market={market}
          onAgree={onAgree || ((id) => onBuy(id, 'yes'))} // Fallback to onBuy if onAgree not provided
        />
      </div>
    </div>
  );
}
