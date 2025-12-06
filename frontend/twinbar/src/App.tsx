import { useState, useEffect, useMemo } from 'react';
import { Header } from './components/Header';
import { SearchBar } from './components/SearchBar';
import { CategoryNav } from './components/CategoryNav';
import { SortBar } from './components/SortBar';
import { MarketsGrid } from './components/MarketsGrid';
import { MarketModal } from './components/MarketModal';
import { useMarketStore } from './stores/marketStore';
import type { Market, MarketCategory, SortOption } from './types/market';
import { useTelegramWebApp } from './hooks/useTelegramWebApp';
import { useTelegramTheme } from './hooks/useTelegramTheme';
import { apiClient } from './api/client';

function App() {
  const {
    markets,
    selectedMarket,
    category,
    sortBy,
    isLoading,
    setSelectedMarket,
    setCategory,
    setSortBy,
    fetchMarkets,
    // fetchReport, // TODO: Use when implementing detailed report loading
  } = useMarketStore();

  const [searchQuery, setSearchQuery] = useState('');
  const [isModalOpen, setIsModalOpen] = useState(false);

  // Initialize Telegram WebApp SDK
  const { webApp, initData, user, isTelegram, isReady } = useTelegramWebApp();
  useTelegramTheme(); // Apply Telegram theme

  // Initialize API client and load data
  useEffect(() => {
    if (!isReady) return;

    // Configure API authentication
    if (isTelegram && initData) {
      apiClient.setInitData(initData);
      console.log('✅ Telegram auth configured');
    } else {
      // Development mode - use fake user ID
      apiClient.setDevUserId('dev_user_12345');
      console.log('🔧 Development mode - using dev user ID');
    }

    // Fetch markets from API
    fetchMarkets();
  }, [isReady, isTelegram, initData, fetchMarkets]);

  // Filter and sort markets
  const filteredMarkets = useMemo(() => {
    let result = [...markets];

    // Filter by category
    if (category !== 'all') {
      result = result.filter((m) => m.category === category);
    }

    // Filter by search
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      result = result.filter(
        (m) =>
          m.title.toLowerCase().includes(query) ||
          m.description?.toLowerCase().includes(query)
      );
    }

    // Sort
    switch (sortBy) {
      case 'volume':
        result.sort((a, b) => b.volume - a.volume);
        break;
      case 'ending':
        result.sort((a, b) => {
          if (!a.endsAt) return 1;
          if (!b.endsAt) return -1;
          return new Date(a.endsAt).getTime() - new Date(b.endsAt).getTime();
        });
        break;
      case 'newest':
      default:
        result.sort(
          (a, b) =>
            new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime()
        );
    }

    return result;
  }, [markets, category, sortBy, searchQuery]);

  const handleCategoryChange = (newCategory: MarketCategory) => {
    setCategory(newCategory);
  };

  const handleSortChange = (newSort: SortOption) => {
    setSortBy(newSort);
  };

  const handleSearch = (query: string) => {
    setSearchQuery(query);
  };

  const handleSelectMarket = (market: Market) => {
    setSelectedMarket(market);
    setIsModalOpen(true);

    // Optionally fetch full report when market is selected
    // fetchReport(market.id);
  };

  const handleCloseModal = () => {
    setIsModalOpen(false);
    setSelectedMarket(null);
  };

  // Telegram back button integration
  useEffect(() => {
    if (!webApp) return;

    if (isModalOpen) {
      // Show back button when modal is open
      webApp.BackButton.show();
      webApp.BackButton.onClick(handleCloseModal);
    } else {
      // Hide back button when modal is closed
      webApp.BackButton.hide();
      webApp.BackButton.offClick(handleCloseModal);
    }

    // Cleanup
    return () => {
      if (webApp && webApp.BackButton) {
        webApp.BackButton.offClick(handleCloseModal);
      }
    };
  }, [webApp, isModalOpen]);

  const handleBuy = (marketId: string, outcome: 'yes' | 'no') => {
    const market = markets.find((m) => m.id === marketId);
    if (market) {
      // TODO: Connect to actual trading API
      console.log(`Buy ${outcome} on "${market.title}"`);
      alert(`Bought ${outcome.toUpperCase()} on "${market.title}"`);
    }
  };

  return (
    <div id="app" className="min-h-screen flex flex-col">
      {/* Development mode banner */}
      {!isTelegram && (
        <div className="bg-amber-500 text-white px-4 py-2 text-center text-sm font-medium">
          🔧 Development Mode - Not running in Telegram
        </div>
      )}

      {/* User greeting (Telegram only) */}
      {isTelegram && user && (
        <div className="bg-[var(--tg-theme-button-color)] text-[var(--tg-theme-button-text-color)] px-4 py-2 text-center text-sm">
          👋 Hello, {user.firstName}!
        </div>
      )}

      <Header />
      <SearchBar onSearch={handleSearch} />
      <CategoryNav active={category} onChange={handleCategoryChange} />
      <SortBar active={sortBy} onChange={handleSortChange} />

      <main className="markets-container flex-1 p-4 overflow-y-auto">
        <MarketsGrid
          markets={filteredMarkets}
          isLoading={isLoading}
          onSelect={handleSelectMarket}
          onBuy={handleBuy}
        />
      </main>

      <MarketModal
        market={selectedMarket}
        isOpen={isModalOpen}
        onClose={handleCloseModal}
        onBuy={handleBuy}
      />

      {/* Toast container for notifications */}
      <div id="toast-container" className="fixed top-4 left-1/2 -translate-x-1/2 z-[2000] flex flex-col gap-2" />
    </div>
  );
}

export default App;
