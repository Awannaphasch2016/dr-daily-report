/**
 * SocialProofBar Component
 *
 * Compact social proof display for market cards.
 * Shows agreement count, capital commitment, and conviction level.
 *
 * Format: "👥 127 agree  💰 $340K/$500K (68%) ⚡High Conv."
 *
 * Conviction Badges:
 * - ⚡ High Conv. (70-100% filled)
 * - ⚠️ Low Conv. (<30% filled)
 * - 🔵 Early Stage (explicit early level)
 * - (no badge for medium 30-70%)
 */

import type { SocialProof } from '../types/market';

interface SocialProofBarProps {
  socialProof: SocialProof;
}

/**
 * Format number as compact currency (e.g., 340000 → $340K, 1200000 → $1.2M)
 */
function formatCompactCurrency(amount: number): string {
  if (amount >= 1_000_000) {
    return `$${(amount / 1_000_000).toFixed(1)}M`;
  } else if (amount >= 1_000) {
    return `$${Math.round(amount / 1_000)}K`;
  } else {
    return `$${amount}`;
  }
}

/**
 * Get conviction badge based on level
 */
function getConvictionBadge(level: SocialProof['convictionLevel']): { emoji: string; text: string } | null {
  switch (level) {
    case 'high':
      return { emoji: '⚡', text: 'High Conv.' };
    case 'low':
      return { emoji: '⚠️', text: 'Low Conv.' };
    case 'early':
      return { emoji: '🔵', text: 'Early Stage' };
    case 'medium':
      return null; // No badge for medium conviction
    default:
      return null;
  }
}

export function SocialProofBar({ socialProof }: SocialProofBarProps) {
  const { agreementCount, capitalInvested, capitalCapacity } = socialProof;

  // Calculate percentage filled
  const percentFilled = Math.round((capitalInvested / capitalCapacity) * 100);

  // Get conviction badge (may be null for medium)
  const badge = getConvictionBadge(socialProof.convictionLevel);

  return (
    <div
      data-testid="social-proof-bar"
      className="flex items-center gap-3 text-xs text-[var(--color-text-secondary)] py-2 border-t border-[var(--color-border)]"
    >
      {/* Agreement count */}
      <span data-testid="agreement-count" className="flex items-center gap-1">
        <span>👥</span>
        <span>{agreementCount} agree</span>
      </span>

      {/* Capital commitment */}
      <span data-testid="capital-commitment" className="flex items-center gap-1">
        <span>💰</span>
        <span>
          {formatCompactCurrency(capitalInvested)}/{formatCompactCurrency(capitalCapacity)} ({percentFilled}%)
        </span>
      </span>

      {/* Conviction badge (if present) */}
      {badge && (
        <span
          data-testid="conviction-badge"
          className="flex items-center gap-1 font-medium"
        >
          <span>{badge.emoji}</span>
          <span>{badge.text}</span>
        </span>
      )}
    </div>
  );
}
