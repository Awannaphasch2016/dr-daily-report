/**
 * NarrativePanel Component
 *
 * Displays LLM-generated narrative analysis with clickable bullet points.
 * Used in modal Overview tab for detailed reasoning with "narrative + numbers".
 *
 * Features:
 * - Clickable bullet points
 * - Expandable full text
 * - News source citations
 * - Progressive disclosure pattern
 */

import { useState } from 'react';
import { ChevronDownIcon, ChevronRightIcon } from '@heroicons/react/24/outline';
import type { NarrativeSection } from '../types/report';

interface NarrativePanelProps {
  sections: NarrativeSection[];
}

/**
 * Individual Narrative Section Component
 */
function NarrativeSectionComponent({ section }: { section: NarrativeSection }) {
  const [expandedBullets, setExpandedBullets] = useState<Set<number>>(new Set());
  const [showFullText, setShowFullText] = useState(false);

  const toggleBullet = (index: number) => {
    const newExpanded = new Set(expandedBullets);
    if (newExpanded.has(index)) {
      newExpanded.delete(index);
    } else {
      newExpanded.add(index);
    }
    setExpandedBullets(newExpanded);
  };

  return (
    <div className="border border-[var(--color-border)] rounded-lg p-4">
      {/* Section Title */}
      <h4 className="font-semibold mb-3">{section.title}</h4>

      {/* Bullet Points */}
      <div className="space-y-2 mb-4">
        {section.bullets.map((bullet, index) => (
          <div key={index} data-testid="narrative-bullet" className="border-l-2 border-[var(--color-primary)] pl-3">
            <button
              onClick={() => toggleBullet(index)}
              className="w-full text-left flex items-start gap-2 hover:text-[var(--color-primary)] transition-colors group"
            >
              <ChevronRightIcon
                className={`w-4 h-4 mt-0.5 flex-shrink-0 transition-transform ${
                  expandedBullets.has(index) ? 'rotate-90' : ''
                }`}
              />
              <span className="text-sm group-hover:underline">{bullet}</span>
            </button>

            {/* Expanded content for this bullet */}
            {expandedBullets.has(index) && section.fullText && (
              <div data-testid="bullet-expanded" className="mt-2 ml-6 p-3 bg-[var(--color-bg-secondary)] rounded text-xs text-[var(--color-text-secondary)]">
                <p>Additional context for: {bullet}</p>
                {section.sources && section.sources.length > 0 && (
                  <div className="mt-2">
                    <span className="font-semibold">Sources:</span>
                    <ul className="list-disc list-inside mt-1">
                      {section.sources.slice(0, 2).map((source, idx) => (
                        <li key={idx}>
                          <a
                            href={source.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="hover:underline text-[var(--color-primary)]"
                          >
                            {source.title}
                          </a>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Expand Full Report Button */}
      {section.fullText && (
        <button
          data-testid="expand-full-report"
          onClick={() => setShowFullText(!showFullText)}
          className="flex items-center gap-2 text-sm text-[var(--color-primary)] hover:underline"
        >
          <span>{showFullText ? 'Hide' : 'Read'} Full Report</span>
          <ChevronDownIcon className={`w-4 h-4 transition-transform ${showFullText ? 'rotate-180' : ''}`} />
        </button>
      )}

      {/* Full Text (expanded) */}
      {showFullText && section.fullText && (
        <div className="mt-4 p-4 bg-[var(--color-bg-secondary)] rounded-lg text-sm whitespace-pre-line">
          {section.fullText}
        </div>
      )}
    </div>
  );
}

export function NarrativePanel({ sections }: NarrativePanelProps) {
  // ALWAYS render component - show empty state if no sections
  const isEmpty = !sections || sections.length === 0;

  if (isEmpty) {
    return (
      <div
        data-testid="narrative-panel"
        className="narrative-panel--empty w-full py-12 flex items-center justify-center border border-dashed border-[var(--color-border)] rounded-lg"
      >
        <div className="empty-state text-center text-[var(--color-text-secondary)]">
          <div className="empty-state__icon text-4xl mb-2">📝</div>
          <div className="empty-state__text text-sm">No narrative analysis available</div>
          <div className="text-xs mt-1 opacity-70">AI-generated insights will appear here</div>
        </div>
      </div>
    );
  }

  return (
    <div data-testid="narrative-panel" className="space-y-4">
      <h3 className="text-lg font-semibold mb-2">Analysis & Reasoning</h3>
      <p className="text-sm text-[var(--color-text-secondary)] mb-4">
        Click on any bullet point to see detailed explanation with sources
      </p>

      {sections.map((section, index) => (
        <NarrativeSectionComponent key={index} section={section} />
      ))}
    </div>
  );
}
