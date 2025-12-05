/**
 * SocialProofPanel Component
 *
 * Detailed social proof display for modal Overview tab.
 * Shows comprehensive commitment evidence to build user conviction.
 *
 * Sections:
 * 1. Recent Activity Feed - Who agreed recently
 * 2. Capital Commitment Bar - Progress visualization
 * 3. Conviction Metrics - Hold time, whale participation
 * 4. Comparative Stats - vs average thesis
 */

import type { SocialProof } from '../types/market';

interface SocialProofPanelProps {
  socialProof: SocialProof;
}

/**
 * Format currency with commas (e.g., 2680 → $2,680)
 */
function formatCurrency(amount: number): string {
  return `$${amount.toLocaleString()}`;
}

/**
 * Format compact currency (e.g., 340000 → $340K)
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

export function SocialProofPanel({ socialProof }: SocialProofPanelProps) {
  const {
    agreementCount,
    capitalInvested,
    capitalCapacity,
    recentActivity = [],
    avgInvestment,
    medianInvestment,
    topInvestment,
    holdTimePercentage,
    whaleCount,
    vsAvgThesis,
  } = socialProof;

  const percentFilled = Math.round((capitalInvested / capitalCapacity) * 100);

  return (
    <div data-testid="social-proof-panel" className="space-y-6 border border-[var(--color-border)] rounded-lg p-4">
      <div>
        <h3 className="text-lg font-semibold mb-2">Social Proof & Commitment</h3>
        <p className="text-sm text-[var(--color-text-secondary)] mb-4">
          {agreementCount} people agree with this thesis
        </p>
      </div>

      {/* Section 1: Recent Activity Feed */}
      {recentActivity.length > 0 && (
        <div data-testid="recent-activity">
          <h4 className="font-semibold mb-3 text-sm">Recent Activity</h4>
          <div className="space-y-2">
            {recentActivity.slice(0, 3).map((activity, index) => (
              <div
                key={index}
                data-testid="activity-item"
                className="flex items-center justify-between text-sm bg-[var(--color-bg-secondary)] rounded p-2"
              >
                <div className="flex items-center gap-2">
                  <span className="text-lg">👤</span>
                  <span className="font-medium">{activity.userName}</span>
                  <span className="text-[var(--color-text-secondary)]">invested</span>
                  <span className="font-semibold">{formatCurrency(activity.amount)}</span>
                </div>
                <span className="text-xs text-[var(--color-text-secondary)]">
                  {activity.timeAgo}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Section 2: Capital Commitment Bar */}
      <div data-testid="capital-commitment-section">
        <h4 className="font-semibold mb-3 text-sm">Capital Commitment</h4>

        {/* Progress Bar */}
        <div className="mb-3">
          <div className="flex justify-between text-sm mb-1">
            <span className="font-medium">{formatCompactCurrency(capitalInvested)}</span>
            <span className="text-[var(--color-text-secondary)]">
              {formatCompactCurrency(capitalCapacity)} cap
            </span>
          </div>
          <div
            data-testid="capital-progress-bar"
            className="h-3 bg-[var(--color-bg-secondary)] rounded-full overflow-hidden"
          >
            <div
              className={`h-full transition-all ${
                percentFilled >= 70
                  ? 'bg-amber-500'
                  : percentFilled >= 30
                  ? 'bg-blue-500'
                  : 'bg-gray-400'
              }`}
              style={{ width: `${percentFilled}%` }}
            />
          </div>
          <div className="text-xs text-[var(--color-text-secondary)] mt-1 text-center">
            {percentFilled}% filled
            {percentFilled >= 70 && ' - High conviction'}
            {percentFilled < 30 && ' - Early opportunity'}
          </div>
        </div>

        {/* Stats Grid */}
        {(avgInvestment || medianInvestment || topInvestment) && (
          <div className="grid grid-cols-3 gap-3 text-sm">
            {avgInvestment && (
              <div data-testid="avg-investment" className="text-center">
                <div className="text-xs text-[var(--color-text-secondary)]">Avg</div>
                <div className="font-semibold">{formatCurrency(avgInvestment)}</div>
              </div>
            )}
            {medianInvestment && (
              <div className="text-center">
                <div className="text-xs text-[var(--color-text-secondary)]">Median</div>
                <div className="font-semibold">{formatCurrency(medianInvestment)}</div>
              </div>
            )}
            {topInvestment && (
              <div className="text-center">
                <div className="text-xs text-[var(--color-text-secondary)]">Top</div>
                <div className="font-semibold">{formatCurrency(topInvestment)}</div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Section 3: Conviction Metrics */}
      {(holdTimePercentage !== undefined || whaleCount !== undefined || vsAvgThesis !== undefined) && (
        <div data-testid="conviction-metrics">
          <h4 className="font-semibold mb-3 text-sm">Conviction Metrics</h4>
          <div className="space-y-3">
            {holdTimePercentage !== undefined && (
              <div data-testid="hold-time-metric">
                <div className="flex justify-between text-sm mb-1">
                  <span className="text-[var(--color-text-secondary)]">
                    High conviction (hold &gt;7 days)
                  </span>
                  <span className="font-semibold">{holdTimePercentage}%</span>
                </div>
                <div className="h-2 bg-[var(--color-bg-secondary)] rounded-full overflow-hidden">
                  <div
                    className="h-full bg-green-500 transition-all"
                    style={{ width: `${holdTimePercentage}%` }}
                  />
                </div>
              </div>
            )}

            {whaleCount !== undefined && (
              <div className="text-sm">
                <span className="text-[var(--color-text-secondary)]">Whale participation: </span>
                <span className="font-semibold">
                  {whaleCount} investor{whaleCount !== 1 ? 's' : ''} &gt;$10K each
                </span>
              </div>
            )}

            {vsAvgThesis !== undefined && (
              <div className="text-sm">
                <span className="text-[var(--color-text-secondary)]">Vs avg thesis: </span>
                <span className="font-semibold text-green-600">
                  +{vsAvgThesis.toFixed(1)}x more agreements
                </span>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
