import { Dialog, DialogPanel, DialogTitle } from '@headlessui/react';
import { XMarkIcon } from '@heroicons/react/24/outline';
import type { Market } from '../types/market';
import { formatVolume, formatEndsAt } from '../lib/format';
import { FullChart } from './FullChart';
import { ScoringPanel } from './ScoringPanel';
import { NarrativePanel } from './NarrativePanel';
import { SocialProofPanel } from './SocialProofPanel';
import { AgreeButton } from './AgreeButton';
import { ChartPatternsPanel } from './ChartPatternsPanel';

interface MarketModalProps {
  market: Market | null;
  isOpen: boolean;
  onClose: () => void;
  onBuy: (marketId: string, outcome: 'yes' | 'no') => void;
  onAgree?: (marketId: string) => void;
}

export function MarketModal({ market, isOpen, onClose, onBuy, onAgree }: MarketModalProps) {
  if (!market) return null;

  // ALWAYS show report layout with empty states (observability principle)
  // Even when market.report is undefined, we show all sections with placeholders
  const hasReport = true;  // Changed: was market.report !== undefined

  return (
    <Dialog open={isOpen} onClose={onClose} className="relative z-50">
      {/* Backdrop */}
      <div className="fixed inset-0 bg-black/50" aria-hidden="true" />

      {/* Modal container - WIDER, uses ~80% of screen */}
      <div className="fixed inset-0 flex items-end justify-center px-4">
        <DialogPanel
          id="market-modal"
          className="modal-content w-full max-w-4xl max-h-[90vh] overflow-y-auto bg-[var(--color-bg)] rounded-t-2xl"
        >
          {/* Header */}
          <div className="modal-header flex justify-between items-center p-4 border-b border-[var(--color-border)] sticky top-0 bg-[var(--color-bg)] z-10">
            <DialogTitle id="market-title" className="text-lg font-semibold pr-4">
              {market.title}
            </DialogTitle>
            <button
              onClick={onClose}
              className="modal-close w-8 h-8 flex items-center justify-center text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-secondary)] rounded-full"
            >
              <XMarkIcon className="w-5 h-5" />
            </button>
          </div>

          {/* Single scrollable layout - ALL content in one page */}
          {/* ALWAYS render sections - show empty states when data missing (TDD principle) */}
          {hasReport ? (
            <div id="market-body" className="modal-body p-6 space-y-8">
              {/* SECTION 1: Technical Chart - FULL WIDTH AT TOP */}
              <section>
                <h2 className="text-sm font-semibold text-[var(--color-text-secondary)] uppercase tracking-wider mb-3">
                  Price Chart
                </h2>
                <div data-testid="full-chart-section">
                  <FullChart
                    data={market.report?.price_history || []}
                    indicators={{ sma20: true, sma50: true }}
                  />
                </div>
              </section>

              {/* SECTION 1.5: Chart Patterns - VCP, flags, triangles, etc. */}
              <section>
                <ChartPatternsPanel patterns={market.report?.chart_patterns || []} />
              </section>

              {/* SECTION 2: 2-Column Layout - Scoring (LEFT) + Peers (RIGHT) */}
              <section className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {/* LEFT: Scoring Panel */}
                <div>
                  <h2 className="text-sm font-semibold text-[var(--color-text-secondary)] uppercase tracking-wider mb-3">
                    Key Scores
                  </h2>
                  <ScoringPanel scores={market.report?.all_scores || []} />
                </div>

                {/* RIGHT: Peers */}
                <div>
                  <h2 className="text-sm font-semibold text-[var(--color-text-secondary)] uppercase tracking-wider mb-3">
                    Related Markets
                  </h2>
                  {market.report?.peers && market.report.peers.length > 0 ? (
                    <div data-testid="peers-panel" className="space-y-3">
                      {market.report.peers.map((peer, index) => (
                        <div
                          key={index}
                          data-testid="peer-card"
                          className="p-3 border border-[var(--color-border)] rounded-lg hover:border-[var(--color-primary-light)] transition-colors"
                        >
                          <div className="flex justify-between items-center">
                            <span data-testid="peer-ticker" className="font-semibold">
                              {peer.ticker}
                            </span>
                            <span data-testid="peer-correlation" className="text-sm text-[var(--color-text-secondary)]">
                              {peer.correlation && `Corr: ${(peer.correlation * 100).toFixed(0)}%`}
                            </span>
                          </div>
                          <div className="text-sm text-[var(--color-text-secondary)] mt-1">
                            {peer.company_name}
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div
                      data-testid="peers-panel"
                      className="peers-panel--empty w-full py-12 flex items-center justify-center border border-dashed border-[var(--color-border)] rounded-lg"
                    >
                      <div className="empty-state text-center text-[var(--color-text-secondary)]">
                        <div className="empty-state__icon text-4xl mb-2">🔗</div>
                        <div className="empty-state__text text-sm">No peer data available</div>
                        <div className="text-xs mt-1 opacity-70">Related markets will appear here</div>
                      </div>
                    </div>
                  )}
                </div>
              </section>

              {/* SECTION 3: LLM Narrative */}
              <section>
                <h2 className="text-sm font-semibold text-[var(--color-text-secondary)] uppercase tracking-wider mb-3">
                  Analysis
                </h2>
                <NarrativePanel sections={market.report?.narrative_sections || []} />
              </section>

              {/* SECTION 4: Social Proof */}
              <section>
                <h2 className="text-sm font-semibold text-[var(--color-text-secondary)] uppercase tracking-wider mb-3">
                  Community Consensus
                </h2>
                {market.socialProof ? (
                  <SocialProofPanel socialProof={market.socialProof} />
                ) : (
                  <div className="social-proof--empty w-full py-12 flex items-center justify-center border border-dashed border-[var(--color-border)] rounded-lg">
                    <div className="empty-state text-center text-[var(--color-text-secondary)]">
                      <div className="empty-state__icon text-4xl mb-2">👥</div>
                      <div className="empty-state__text text-sm">No consensus data available</div>
                      <div className="text-xs mt-1 opacity-70">Community predictions will appear here</div>
                    </div>
                  </div>
                )}
              </section>

              {/* SECTION 5: Market Stats + Agree Button */}
              <section>
                <div className="grid grid-cols-2 gap-4 mb-6">
                  <div className="text-center p-4 bg-[var(--color-bg-secondary)] rounded-lg">
                    <div className="text-xs text-[var(--color-text-secondary)] mb-1">Volume</div>
                    <div className="font-semibold text-lg">{formatVolume(market.volume)}</div>
                  </div>
                  <div className="text-center p-4 bg-[var(--color-bg-secondary)] rounded-lg">
                    <div className="text-xs text-[var(--color-text-secondary)] mb-1">Liquidity</div>
                    <div className="font-semibold text-lg">{formatVolume(market.liquidity)}</div>
                  </div>
                </div>

                {/* Agree Button - Prominent CTA */}
                <AgreeButton
                  market={market}
                  onAgree={onAgree || ((id) => onBuy(id, 'yes'))}
                />

                {market.endsAt && (
                  <p className="text-xs text-[var(--color-text-secondary)] text-center mt-4">
                    Market ends {formatEndsAt(market.endsAt)}
                  </p>
                )}
              </section>
            </div>
          ) : (
            // Fallback: Original modal content for markets without reports
            <div id="market-body" className="modal-body p-4">
              {market.image && (
                <img
                  src={market.image}
                  alt=""
                  className="w-full h-44 object-cover rounded-lg mb-4 bg-[var(--color-bg-secondary)]"
                />
              )}

              <p className="text-[var(--color-text-secondary)] mb-4">
                {market.description || 'No description available.'}
              </p>

              {/* Stats */}
              <div className="grid grid-cols-2 gap-4 mb-6">
                <div className="text-center">
                  <div className="text-xs text-[var(--color-text-secondary)]">Volume</div>
                  <div className="font-semibold">{formatVolume(market.volume)}</div>
                </div>
                <div className="text-center">
                  <div className="text-xs text-[var(--color-text-secondary)]">Liquidity</div>
                  <div className="font-semibold">{formatVolume(market.liquidity)}</div>
                </div>
              </div>

              {/* Agree Button - Single asymmetric commitment */}
              <div className="mb-4">
                <AgreeButton
                  market={market}
                  onAgree={onAgree || ((id) => onBuy(id, 'yes'))}
                />
              </div>

              {market.endsAt && (
                <p className="text-xs text-[var(--color-text-secondary)] text-center">
                  Market ends {formatEndsAt(market.endsAt)}
                </p>
              )}
            </div>
          )}
        </DialogPanel>
      </div>
    </Dialog>
  );
}
