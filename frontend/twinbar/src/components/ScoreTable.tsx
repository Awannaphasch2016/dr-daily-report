/**
 * ScoreTable Component
 *
 * Compact 3-column table for score display on market cards.
 * Replaces vertical ScoreBadge components with dense table layout.
 *
 * Columns:
 * 1. Metric (abbreviated name, max 12 chars)
 * 2. Score (ratio format: 9/10)
 * 3. Dot (colored indicator)
 *
 * Color coding:
 * - Green (8-10): Strong, supports thesis
 * - Amber (5-7): Moderate, neutral
 * - Red (0-4): Warning, clarifies risk
 */

import type { ScoringMetric } from '../types/report';

interface ScoreTableProps {
  scores: ScoringMetric[];
}

/**
 * Abbreviate metric names for compact UI (max 12 chars)
 */
function abbreviateMetric(category: string): string {
  const abbreviations: Record<string, string> = {
    'Fundamental': 'Fund.',
    'Fundamental Score': 'Fund.',
    'Liquidity': 'Liquid.',
    'Momentum': 'Momentum',
    'Risk Level': 'Risk',
    'Selling Pressure': 'Sell Pres.',
    'Valuation': 'Valuation',
    'Growth': 'Growth',
    'Technical': 'Technical',
    'Sentiment': 'Sentiment',
  };

  return abbreviations[category] || category.slice(0, 12);
}

/**
 * Get dot color class based on score value
 */
function getDotColor(score: number, maxScore: number): string {
  const percentage = (score / maxScore) * 100;

  if (percentage >= 80) return 'bg-green-500'; // Green (8-10/10)
  if (percentage >= 50) return 'bg-amber-500'; // Amber (5-7/10)
  return 'bg-red-500'; // Red (0-4/10)
}

export function ScoreTable({ scores }: ScoreTableProps) {
  if (!scores || scores.length === 0) {
    return null;
  }

  return (
    <div data-testid="score-table" className="space-y-1">
      {scores.map((score, index) => (
        <div
          key={index}
          data-testid="score-row"
          className="grid grid-cols-[1fr_auto_auto] gap-2 items-center text-sm"
        >
          {/* Column 1: Metric name (abbreviated) */}
          <div
            data-testid="score-metric"
            className="text-[var(--color-text-secondary)] truncate"
          >
            {abbreviateMetric(score.category)}
          </div>

          {/* Column 2: Score value (ratio) */}
          <div
            data-testid="score-value"
            className="font-medium text-[var(--color-text)] tabular-nums"
          >
            {score.score}/{score.maxScore}
          </div>

          {/* Column 3: Colored dot */}
          <div
            data-testid="score-dot"
            className={`w-2 h-2 rounded-full ${getDotColor(score.score, score.maxScore)}`}
            aria-label={`Score indicator: ${score.score}/${score.maxScore}`}
          />
        </div>
      ))}
    </div>
  );
}
