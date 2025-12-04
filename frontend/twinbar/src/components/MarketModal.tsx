import { Dialog, DialogPanel, DialogTitle } from '@headlessui/react';
import { XMarkIcon } from '@heroicons/react/24/outline';
import type { Market } from '../types/market';
import { formatVolume, formatEndsAt } from '../lib/format';

interface MarketModalProps {
  market: Market | null;
  isOpen: boolean;
  onClose: () => void;
  onBuy: (marketId: string, outcome: 'yes' | 'no') => void;
}

export function MarketModal({ market, isOpen, onClose, onBuy }: MarketModalProps) {
  if (!market) return null;

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
          <div className="modal-header flex justify-between items-center p-4 border-b border-[var(--color-border)] sticky top-0 bg-[var(--color-bg)]">
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

          {/* Body */}
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
        </DialogPanel>
      </div>
    </Dialog>
  );
}
