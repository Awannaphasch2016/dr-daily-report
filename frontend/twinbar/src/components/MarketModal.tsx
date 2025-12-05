import { Dialog, DialogPanel, DialogTitle, Tab, TabGroup, TabList, TabPanel, TabPanels } from '@headlessui/react';
import { XMarkIcon } from '@heroicons/react/24/outline';
import type { Market } from '../types/market';
import { formatVolume, formatEndsAt } from '../lib/format';
import { FullChart } from './FullChart';
import { ScoringPanel } from './ScoringPanel';
import { NarrativePanel } from './NarrativePanel';
import { SocialProofPanel } from './SocialProofPanel';

interface MarketModalProps {
  market: Market | null;
  isOpen: boolean;
  onClose: () => void;
  onBuy: (marketId: string, outcome: 'yes' | 'no') => void;
}

export function MarketModal({ market, isOpen, onClose, onBuy }: MarketModalProps) {
  if (!market) return null;

  const hasReport = market.report !== undefined;

  return (
    <Dialog open={isOpen} onClose={onClose} className="relative z-50">
      {/* Backdrop */}
      <div className="fixed inset-0 bg-black/50" aria-hidden="true" />

      {/* Modal container */}
      <div className="fixed inset-0 flex items-end justify-center">
        <DialogPanel
          id="market-modal"
          className="modal-content w-full max-w-lg max-h-[90vh] overflow-y-auto bg-[var(--color-bg)] rounded-t-2xl"
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

          {/* Phase 3: Tabbed Content (if report data available) */}
          {hasReport ? (
            <TabGroup>
              {/* Tab Navigation */}
              <TabList data-testid="modal-tabs" className="flex border-b border-[var(--color-border)] px-4 sticky top-14 bg-[var(--color-bg)] z-10">
                <Tab
                  data-tab="overview"
                  className="px-4 py-3 text-sm font-medium transition-colors focus:outline-none data-[selected]:border-b-2 data-[selected]:border-[var(--color-primary)] data-[selected]:text-[var(--color-primary)]"
                >
                  Overview
                </Tab>
                <Tab
                  data-tab="technical"
                  className="px-4 py-3 text-sm font-medium transition-colors focus:outline-none data-[selected]:border-b-2 data-[selected]:border-[var(--color-primary)] data-[selected]:text-[var(--color-primary)]"
                >
                  Technical
                </Tab>
                <Tab
                  data-tab="fundamentals"
                  className="px-4 py-3 text-sm font-medium transition-colors focus:outline-none data-[selected]:border-b-2 data-[selected]:border-[var(--color-primary)] data-[selected]:text-[var(--color-primary)]"
                >
                  Fundamentals
                </Tab>
                <Tab
                  data-tab="peers"
                  className="px-4 py-3 text-sm font-medium transition-colors focus:outline-none data-[selected]:border-b-2 data-[selected]:border-[var(--color-primary)] data-[selected]:text-[var(--color-primary)]"
                >
                  Peers
                </Tab>
              </TabList>

              {/* Tab Panels */}
              <TabPanels>
                {/* Overview Tab */}
                <TabPanel className="p-4">
                  <div id="market-body" className="modal-body space-y-6">
                    {/* Phase 4: Scoring Panel */}
                    {market.report && market.report.all_scores && market.report.all_scores.length > 0 && (
                      <ScoringPanel scores={market.report.all_scores} />
                    )}

                    {/* Phase 5: LLM Narrative Panel */}
                    {market.report && market.report.narrative_sections && market.report.narrative_sections.length > 0 && (
                      <NarrativePanel sections={market.report.narrative_sections} />
                    )}

                    {/* Social Proof Panel - Detailed commitment evidence */}
                    {market.socialProof && <SocialProofPanel socialProof={market.socialProof} />}

                    {/* Existing market info */}
                    {market.image && (
                      <img
                        src={market.image}
                        alt=""
                        className="w-full h-44 object-cover rounded-lg bg-[var(--color-bg-secondary)]"
                      />
                    )}

                    <p className="text-[var(--color-text-secondary)]">
                      {market.description || 'No description available.'}
                    </p>

                    {/* Stats */}
                    <div className="grid grid-cols-2 gap-4">
                      <div className="text-center">
                        <div className="text-xs text-[var(--color-text-secondary)]">Volume</div>
                        <div className="font-semibold">{formatVolume(market.volume)}</div>
                      </div>
                      <div className="text-center">
                        <div className="text-xs text-[var(--color-text-secondary)]">Liquidity</div>
                        <div className="font-semibold">{formatVolume(market.liquidity)}</div>
                      </div>
                    </div>

                    {/* Buy buttons */}
                    <div>
                      <div className="text-xs text-[var(--color-text-secondary)] mb-2">Current Odds</div>
                      <div className="market-outcomes flex gap-2">
                        <button
                          className="outcome-btn yes flex-1 flex justify-between items-center py-3 px-4 rounded-lg font-semibold transition-colors bg-[var(--color-yes-light)] text-[var(--color-yes)] border border-[var(--color-yes)] hover:bg-[var(--color-yes)] hover:text-white"
                          data-outcome="yes"
                          data-market-id={market.id}
                          onClick={() => onBuy(market.id, 'yes')}
                        >
                          <span>Buy Yes</span>
                          <span className="outcome-odds font-bold">{market.yesOdds}¢</span>
                        </button>

                        <button
                          className="outcome-btn no flex-1 flex justify-between items-center py-3 px-4 rounded-lg font-semibold transition-colors bg-[var(--color-no-light)] text-[var(--color-no)] border border-[var(--color-no)] hover:bg-[var(--color-no)] hover:text-white"
                          data-outcome="no"
                          data-market-id={market.id}
                          onClick={() => onBuy(market.id, 'no')}
                        >
                          <span>Buy No</span>
                          <span className="outcome-odds font-bold">{market.noOdds}¢</span>
                        </button>
                      </div>
                    </div>

                    {market.endsAt && (
                      <p className="text-xs text-[var(--color-text-secondary)] text-center">
                        Market ends {formatEndsAt(market.endsAt)}
                      </p>
                    )}
                  </div>
                </TabPanel>

                {/* Technical Tab */}
                <TabPanel className="p-4">
                  {market.report && market.report.price_history && (
                    <FullChart
                      data={market.report.price_history}
                      indicators={{ sma20: true, sma50: true }}
                    />
                  )}
                </TabPanel>

                {/* Fundamentals Tab - Placeholder */}
                <TabPanel className="p-4">
                  <div data-testid="fundamentals-panel" className="text-center py-8">
                    <p className="text-[var(--color-text-secondary)]">
                      Fundamentals panel coming soon...
                    </p>
                    {market.report?.fundamentals && (
                      <div className="mt-4 space-y-4">
                        <div>
                          <h3 className="font-semibold mb-2">Valuation</h3>
                          <div className="text-sm text-[var(--color-text-secondary)]">
                            P/E: {market.report.fundamentals.valuation.pe_ratio}
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                </TabPanel>

                {/* Peers Tab - Placeholder */}
                <TabPanel className="p-4">
                  <div data-testid="peers-panel" className="space-y-3">
                    {market.report?.peers && market.report.peers.length > 0 ? (
                      market.report.peers.map((peer, index) => (
                        <div
                          key={index}
                          data-testid="peer-card"
                          className="p-3 border border-[var(--color-border)] rounded-lg"
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
                      ))
                    ) : (
                      <p className="text-center text-[var(--color-text-secondary)]">
                        No peer data available
                      </p>
                    )}
                  </div>
                </TabPanel>
              </TabPanels>
            </TabGroup>
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

              {/* Buy buttons */}
              <div className="mb-4">
                <div className="text-xs text-[var(--color-text-secondary)] mb-2">Current Odds</div>
                <div className="market-outcomes flex gap-2">
                  <button
                    className="outcome-btn yes flex-1 flex justify-between items-center py-3 px-4 rounded-lg font-semibold transition-colors bg-[var(--color-yes-light)] text-[var(--color-yes)] border border-[var(--color-yes)] hover:bg-[var(--color-yes)] hover:text-white"
                    data-outcome="yes"
                    data-market-id={market.id}
                    onClick={() => onBuy(market.id, 'yes')}
                  >
                    <span>Buy Yes</span>
                    <span className="outcome-odds font-bold">{market.yesOdds}¢</span>
                  </button>

                  <button
                    className="outcome-btn no flex-1 flex justify-between items-center py-3 px-4 rounded-lg font-semibold transition-colors bg-[var(--color-no-light)] text-[var(--color-no)] border border-[var(--color-no)] hover:bg-[var(--color-no)] hover:text-white"
                    data-outcome="no"
                    data-market-id={market.id}
                    onClick={() => onBuy(market.id, 'no')}
                  >
                    <span>Buy No</span>
                    <span className="outcome-odds font-bold">{market.noOdds}¢</span>
                  </button>
                </div>
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
