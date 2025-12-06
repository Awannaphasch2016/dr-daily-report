/**
 * ScoreBadge Component
 *
 * Displays a single score metric with color coding.
 * Used in market cards to show key scores (top 3).
 *
 * Color scheme:
 * - High (8-10): Green (#10b981)
 * - Medium (5-7): Amber (#f59e0b)
 * - Low (0-4): Red (#ef4444)
 */

import type { ScoringMetric } from '../types/report';

interface ScoreBadgeProps {
  score: ScoringMetric;
  compact?: boolean; // Compact mode for card display
}

/**
 * Get color classes based on score value
 */
function getScoreColorClasses(score: number, maxScore: number = 10): {
  bg: string;
  text: string;
  border: string;
  indicator: 'green' | 'amber' | 'red';
} {
  const percentage = (score / maxScore) * 100;

  if (percentage >= 80) {
    return {
      bg: 'bg-green-50 dark:bg-green-950',
      text: 'text-green-700 dark:text-green-300',
      border: 'border-green-200 dark:border-green-800',
      indicator: 'green',
    };
  } else if (percentage >= 50) {
    return {
      bg: 'bg-amber-50 dark:bg-amber-950',
      text: 'text-amber-700 dark:text-amber-300',
      border: 'border-amber-200 dark:border-amber-800',
      indicator: 'amber',
    };
  } else {
    return {
      bg: 'bg-red-50 dark:bg-red-950',
      text: 'text-red-700 dark:text-red-300',
      border: 'border-red-200 dark:border-red-800',
      indicator: 'red',
    };
  }
}

export function ScoreBadge({ score, compact = false }: ScoreBadgeProps) {
  const colors = getScoreColorClasses(score.score, score.maxScore);

  if (compact) {
    // Compact mode: Single line for card display
    return (
      <div
        data-testid="score-badge"
        className={`flex items-center justify-between gap-2 px-3 py-2 rounded-lg border ${colors.bg} ${colors.border} ${colors.text}`}
      >
        <span data-testid="score-category" className="text-xs font-medium truncate">
          {score.category}
        </span>
        <span data-testid="score-value" className="text-sm font-bold whitespace-nowrap">
          {score.score}/{score.maxScore}
        </span>
      </div>
    );
  }

  // Full mode: With rationale (for modal/expanded view)
  return (
    <div
      data-testid="score-badge"
      className={`px-4 py-3 rounded-lg border ${colors.bg} ${colors.border}`}
    >
      <div className="flex items-center justify-between mb-1">
        <span data-testid="score-category" className={`text-sm font-semibold ${colors.text}`}>
          {score.category}
        </span>
        <span data-testid="score-value" className={`text-lg font-bold ${colors.text}`}>
          {score.score}/{score.maxScore}
        </span>
      </div>

      {score.rationale && (
        <p data-testid="score-rationale" className="text-xs text-gray-600 dark:text-gray-400 mt-1">
          {score.rationale}
        </p>
      )}
    </div>
  );
}
