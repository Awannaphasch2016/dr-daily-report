/**
 * ScoringPanel Component
 *
 * Displays all scoring metrics with expandable rationales.
 * Used in modal Overview tab for comprehensive score breakdown.
 *
 * Features:
 * - Accordion-style expandable items
 * - Color-coded score indicators
 * - Progress bar visualization
 * - Expandable rationale text
 */

import { useState } from 'react';
import { ChevronDownIcon } from '@heroicons/react/24/outline';
import type { ScoringMetric } from '../types/report';

interface ScoringPanelProps {
  scores: ScoringMetric[];
}

/**
 * Get color for score value
 */
function getScoreColor(score: number, maxScore: number = 10): string {
  const percentage = (score / maxScore) * 100;
  if (percentage >= 80) return 'bg-green-500';
  if (percentage >= 50) return 'bg-amber-500';
  return 'bg-red-500';
}

/**
 * Get text color for score
 */
function getScoreTextColor(score: number, maxScore: number = 10): string {
  const percentage = (score / maxScore) * 100;
  if (percentage >= 80) return 'text-green-600 dark:text-green-400';
  if (percentage >= 50) return 'text-amber-600 dark:text-amber-400';
  return 'text-red-600 dark:text-red-400';
}

/**
 * Individual Score Item Component
 */
function ScoreItem({ score }: { score: ScoringMetric }) {
  const [isExpanded, setIsExpanded] = useState(false);

  const percentage = (score.score / score.maxScore) * 100;
  const barColor = getScoreColor(score.score, score.maxScore);
  const textColor = getScoreTextColor(score.score, score.maxScore);

  return (
    <div data-testid="score-item" className="border border-[var(--color-border)] rounded-lg overflow-hidden">
      {/* Score Header (always visible) */}
      <button
        data-testid="expand-score"
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full p-4 flex items-center justify-between hover:bg-[var(--color-bg-secondary)] transition-colors"
      >
        <div className="flex-1 text-left">
          <div className="flex items-center justify-between mb-2">
            <span data-testid="score-category" className="font-semibold">
              {score.category}
            </span>
            <span data-testid="score-value" className={`text-lg font-bold ${textColor}`}>
              {score.score}/{score.maxScore}
            </span>
          </div>

          {/* Progress bar */}
          <div className="w-full h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
            <div
              className={`h-full ${barColor} transition-all duration-300`}
              style={{ width: `${percentage}%` }}
            />
          </div>
        </div>

        {/* Expand icon */}
        <ChevronDownIcon
          className={`w-5 h-5 ml-3 text-[var(--color-text-secondary)] transition-transform ${
            isExpanded ? 'rotate-180' : ''
          }`}
        />
      </button>

      {/* Expanded Rationale */}
      {isExpanded && score.rationale && (
        <div data-testid="score-rationale" className="px-4 pb-4 pt-2 text-sm text-[var(--color-text-secondary)] border-t border-[var(--color-border)]">
          {score.rationale}
        </div>
      )}
    </div>
  );
}

export function ScoringPanel({ scores }: ScoringPanelProps) {
  // ALWAYS render component - show empty state if no scores
  const isEmpty = !scores || scores.length === 0;

  if (isEmpty) {
    return (
      <div
        data-testid="scoring-panel"
        className="scoring-panel--empty w-full py-12 flex items-center justify-center border border-dashed border-[var(--color-border)] rounded-lg"
      >
        <div className="empty-state text-center text-[var(--color-text-secondary)]">
          <div className="empty-state__icon text-4xl mb-2">📊</div>
          <div className="empty-state__text text-sm">No scoring data available</div>
          <div className="text-xs mt-1 opacity-70">Scores will appear when analysis is complete</div>
        </div>
      </div>
    );
  }

  return (
    <div data-testid="scoring-panel" className="space-y-3">
      <h3 className="text-lg font-semibold mb-4">Comprehensive Scores</h3>
      {scores.map((score, index) => (
        <ScoreItem key={index} score={score} />
      ))}
    </div>
  );
}
