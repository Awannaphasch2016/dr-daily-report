import { useState, useEffect, useMemo } from 'react';
import { Header } from './components/Header';
import { SearchBar } from './components/SearchBar';
import { CategoryNav } from './components/CategoryNav';
import { SortBar } from './components/SortBar';
import { MarketsGrid } from './components/MarketsGrid';
import { MarketModal } from './components/MarketModal';
import { useMarketStore, mockMarkets } from './stores/marketStore';
import type { Market, MarketCategory, SortOption } from './types/market';

function App() {
  const {
    markets,
    selectedMarket,
    category,
    sortBy,
    isLoading,
    setMarkets,
    setSelectedMarket,
    setCategory,
    setSortBy,
    setLoading,
  } = useMarketStore();

  const [searchQuery, setSearchQuery] = useState('');
  const [isModalOpen, setIsModalOpen] = useState(false);

  // Load initial data
  useEffect(() => {
    setLoading(true);
    // Simulate API call - replace with actual API
    setTimeout(() => {
      setMarkets(mockMarkets);
      setLoading(false);
    }, 500);
  }, [setMarkets, setLoading]);

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
  };

  const handleCloseModal = () => {
    setIsModalOpen(false);
    setSelectedMarket(null);
  };

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
