/**
 * ChartPatternsPanel Component
 *
 * Displays detected chart patterns (VCP, Head & Shoulders, flags, triangles, etc.)
 * from the pattern detection service.
 *
 * Features:
 * - Pattern type with bullish/bearish indicator
 * - Confidence badge (high/medium/low)
 * - Date range for pattern
 * - Expandable pattern details
 */

import { useState } from 'react';
import { ChevronDownIcon } from '@heroicons/react/24/outline';
import type { ChartPattern } from '../api/types';

interface ChartPatternsPanelProps {
  patterns: ChartPattern[];
}

/**
 * Get sentiment from pattern type
 */
function getPatternSentiment(type: string): 'bullish' | 'bearish' | 'neutral' {
  const bullishPatterns = [
    'bullish_flag', 'bullish_vcp', 'reverse_head_shoulders',
    'double_bottom', 'falling_wedge', 'ascending_triangle'
  ];
  const bearishPatterns = [
    'bearish_flag', 'bearish_vcp', 'head_shoulders',
    'double_top', 'rising_wedge', 'descending_triangle'
  ];

  if (bullishPatterns.some(p => type.toLowerCase().includes(p.replace('_', '')))) {
    return 'bullish';
  }
  if (bearishPatterns.some(p => type.toLowerCase().includes(p.replace('_', '')))) {
    return 'bearish';
  }
  return 'neutral';
}

/**
 * Get display name for pattern type
 */
function getPatternDisplayName(type: string): string {
  return type
    .replace(/_/g, ' ')
    .replace(/\b\w/g, l => l.toUpperCase());
}

/**
 * Get color for confidence level
 */
function getConfidenceColor(confidence: string): string {
  switch (confidence) {
    case 'high':
      return 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300';
    case 'medium':
      return 'bg-amber-100 text-amber-800 dark:bg-amber-900 dark:text-amber-300';
    case 'low':
      return 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-300';
    default:
      return 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300';
  }
}

/**
 * Get sentiment color
 */
function getSentimentColor(sentiment: 'bullish' | 'bearish' | 'neutral'): string {
  switch (sentiment) {
    case 'bullish':
      return 'text-green-600 dark:text-green-400';
    case 'bearish':
      return 'text-red-600 dark:text-red-400';
    default:
      return 'text-gray-600 dark:text-gray-400';
  }
}

/**
 * Get sentiment icon
 */
function getSentimentIcon(sentiment: 'bullish' | 'bearish' | 'neutral'): string {
  switch (sentiment) {
    case 'bullish':
      return '\u2191'; // Up arrow
    case 'bearish':
      return '\u2193'; // Down arrow
    default:
      return '\u2194'; // Left-right arrow
  }
}

/**
 * Format date or bar index for display
 *
 * The start/end fields can be either:
 * - ISO date strings (e.g., "2024-01-15")
 * - Bar indices (e.g., "12", "bar_12")
 *
 * For bar indices, we display them as relative positions.
 */
function formatDateOrIndex(value?: string): string {
  if (!value) return '-';

  // Handle bar index format (e.g., "12", "bar_12")
  if (/^(\d+|bar_\d+)$/.test(value)) {
    const barIndex = value.replace('bar_', '');
    return `Bar ${barIndex}`;
  }

  // Try to parse as date
  try {
    const date = new Date(value);
    if (!isNaN(date.getTime())) {
      return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
    }
  } catch {
    // Fall through to return raw value
  }

  return value;
}

/**
 * Individual Pattern Item Component
 */
function PatternItem({ pattern }: { pattern: ChartPattern }) {
  const [isExpanded, setIsExpanded] = useState(false);
  const sentiment = getPatternSentiment(pattern.type);
  const displayName = getPatternDisplayName(pattern.type);
  const hasDetails = pattern.points && Object.keys(pattern.points).length > 0;

  return (
    <div
      data-testid="pattern-item"
      className="border border-[var(--color-border)] rounded-lg overflow-hidden"
    >
      {/* Pattern Header */}
      <button
        data-testid="expand-pattern"
        onClick={() => hasDetails && setIsExpanded(!isExpanded)}
        className={`w-full p-4 flex items-center justify-between ${
          hasDetails ? 'hover:bg-[var(--color-bg-secondary)] cursor-pointer' : 'cursor-default'
        } transition-colors`}
        disabled={!hasDetails}
      >
        <div className="flex-1 text-left">
          <div className="flex items-center gap-2 mb-1">
            {/* Sentiment indicator */}
            <span className={`text-lg font-bold ${getSentimentColor(sentiment)}`}>
              {getSentimentIcon(sentiment)}
            </span>

            {/* Pattern name */}
            <span data-testid="pattern-name" className="font-semibold">
              {displayName}
            </span>

            {/* Confidence badge */}
            <span
              data-testid="pattern-confidence"
              className={`text-xs px-2 py-0.5 rounded-full ${getConfidenceColor(pattern.confidence)}`}
            >
              {pattern.confidence}
            </span>
          </div>

          {/* Date range or bar index range */}
          <div className="text-sm text-[var(--color-text-secondary)]">
            {pattern.start && pattern.end ? (
              <>
                {formatDateOrIndex(pattern.start)} - {formatDateOrIndex(pattern.end)}
              </>
            ) : (
              <span>Recent pattern</span>
            )}
            {pattern.implementation && (
              <span className="ml-2 text-xs opacity-60">
                [{pattern.implementation}]
              </span>
            )}
          </div>
        </div>

        {/* Expand icon */}
        {hasDetails && (
          <ChevronDownIcon
            className={`w-5 h-5 ml-3 text-[var(--color-text-secondary)] transition-transform ${
              isExpanded ? 'rotate-180' : ''
            }`}
          />
        )}
      </button>

      {/* Expanded Details */}
      {isExpanded && hasDetails && (
        <div
          data-testid="pattern-details"
          className="px-4 pb-4 pt-2 text-sm border-t border-[var(--color-border)]"
        >
          <div className="text-xs text-[var(--color-text-secondary)] mb-2">
            Pattern Code: <span className="font-mono">{pattern.pattern}</span>
          </div>
          <div className="grid grid-cols-2 gap-2">
            {Object.entries(pattern.points).map(([key, value]) => (
              <div key={key} className="text-xs">
                <span className="text-[var(--color-text-secondary)]">
                  {key.replace(/_/g, ' ')}:
                </span>{' '}
                <span className="font-medium">
                  {typeof value === 'number' ? value.toFixed(2) : String(value)}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

export function ChartPatternsPanel({ patterns }: ChartPatternsPanelProps) {
  const isEmpty = !patterns || patterns.length === 0;

  if (isEmpty) {
    return (
      <div
        data-testid="chart-patterns-panel"
        className="chart-patterns-panel--empty w-full py-8 flex items-center justify-center border border-dashed border-[var(--color-border)] rounded-lg"
      >
        <div className="empty-state text-center text-[var(--color-text-secondary)]">
          <div className="empty-state__icon text-3xl mb-2">\uD83D\uDCC8</div>
          <div className="empty-state__text text-sm">No chart patterns detected</div>
          <div className="text-xs mt-1 opacity-70">
            Patterns like VCP, flags, and triangles will appear here
          </div>
        </div>
      </div>
    );
  }

  // Group patterns by sentiment
  const bullishPatterns = patterns.filter(p => getPatternSentiment(p.type) === 'bullish');
  const bearishPatterns = patterns.filter(p => getPatternSentiment(p.type) === 'bearish');
  const neutralPatterns = patterns.filter(p => getPatternSentiment(p.type) === 'neutral');

  return (
    <div data-testid="chart-patterns-panel" className="space-y-3">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold">Chart Patterns</h3>
        <div className="flex gap-2 text-xs">
          {bullishPatterns.length > 0 && (
            <span className="text-green-600 dark:text-green-400">
              {bullishPatterns.length} bullish
            </span>
          )}
          {bearishPatterns.length > 0 && (
            <span className="text-red-600 dark:text-red-400">
              {bearishPatterns.length} bearish
            </span>
          )}
          {neutralPatterns.length > 0 && (
            <span className="text-gray-600 dark:text-gray-400">
              {neutralPatterns.length} neutral
            </span>
          )}
        </div>
      </div>

      {patterns.map((pattern, index) => (
        <PatternItem key={`${pattern.type}-${index}`} pattern={pattern} />
      ))}
    </div>
  );
}
