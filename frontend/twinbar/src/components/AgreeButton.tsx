/**
 * AgreeButton Component
 *
 * Single "Agree" button for asymmetric commitment.
 * Replaces Yes/No buttons - users can only agree with pre-selected favorable opportunities.
 *
 * Features:
 * - Color-coded by stance (green=bullish, red=bearish, blue=neutral)
 * - Pulse animation for high-conviction opportunities
 * - Hover effects
 */

import type { Market } from '../types/market';

interface AgreeButtonProps {
  market: Market;
  onAgree: (marketId: string) => void;
}

/**
 * Get button colors based on market stance
 */
function getStanceColors(stance?: string): {
  bg: string;
  bgHover: string;
  text: string;
  border: string;
} {
  switch (stance) {
    case 'bullish':
      return {
        bg: 'bg-green-500',
        bgHover: 'hover:bg-green-600',
        text: 'text-white',
        border: 'border-green-600',
      };
    case 'bearish':
      return {
        bg: 'bg-red-500',
        bgHover: 'hover:bg-red-600',
        text: 'text-white',
        border: 'border-red-600',
      };
    case 'neutral':
    default:
      return {
        bg: 'bg-blue-500',
        bgHover: 'hover:bg-blue-600',
        text: 'text-white',
        border: 'border-blue-600',
      };
  }
}

/**
 * Determine if button should have pulse animation (high conviction)
 */
function shouldPulse(market: Market): boolean {
  return market.socialProof?.convictionLevel === 'high';
}

export function AgreeButton({ market, onAgree }: AgreeButtonProps) {
  const stance = market.report?.stance || 'neutral';
  const colors = getStanceColors(stance);
  const pulse = shouldPulse(market);

  return (
    <button
      data-testid="agree-button"
      data-stance={stance}
      data-market-id={market.id}
      onClick={(e) => {
        e.stopPropagation();
        onAgree(market.id);
      }}
      className={`
        w-full py-3 px-4 rounded-lg font-semibold
        transition-all duration-200
        ${colors.bg} ${colors.bgHover} ${colors.text}
        border-2 ${colors.border}
        hover:scale-[1.02] hover:shadow-lg
        ${pulse ? 'animate-pulse' : ''}
        focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-${stance === 'bullish' ? 'green' : stance === 'bearish' ? 'red' : 'blue'}-500
      `}
    >
      <div className="flex items-center justify-center gap-2">
        <span>✓</span>
        <span>Agree with Event</span>
      </div>
    </button>
  );
}
