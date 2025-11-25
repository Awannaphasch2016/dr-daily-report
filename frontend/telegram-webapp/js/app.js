/**
 * Main Application Entry Point
 */

const App = {
    // Current state
    state: {
        currentTab: 'rankings',
        currentCategory: 'top_gainers',
        watchlist: new Set(),
        searchDebounce: null
    },

    /**
     * Initialize application
     */
    async init() {
        console.log('🚀 Initializing DR Daily Report...');

        // Initialize Telegram WebApp
        Config.initTelegram();

        // Initialize UI
        UI.init();

        // Setup event listeners
        this.setupEventListeners();

        // Initial data load
        await this.loadInitialData();

        console.log('✅ App initialized');
    },

    /**
     * Setup all event listeners
     */
    setupEventListeners() {
        // Search input
        UI.elements.searchInput.addEventListener('input', (e) => {
            this.handleSearchInput(e.target.value);
        });

        UI.elements.searchInput.addEventListener('focus', () => {
            if (UI.elements.searchInput.value) {
                UI.elements.searchResults.classList.remove('hidden');
            }
        });

        // Close search results on click outside
        document.addEventListener('click', (e) => {
            if (!e.target.closest('.search-section')) {
                UI.elements.searchResults.classList.add('hidden');
            }
        });

        // Search button
        UI.elements.searchBtn.addEventListener('click', () => {
            this.handleSearch(UI.elements.searchInput.value);
        });

        // Tab navigation
        UI.elements.tabBtns.forEach(btn => {
            btn.addEventListener('click', () => {
                const tabId = btn.dataset.tab;
                this.handleTabSwitch(tabId);
            });
        });

        // Category buttons
        UI.elements.categoryBtns.forEach(btn => {
            btn.addEventListener('click', () => {
                const category = btn.dataset.category;
                this.handleCategorySwitch(category);
            });
        });

        // Modal close
        UI.elements.modalClose.addEventListener('click', () => {
            UI.hideModal();
        });

        UI.elements.reportModal.addEventListener('click', (e) => {
            if (e.target === UI.elements.reportModal) {
                UI.hideModal();
            }
        });

        // Watchlist buttons (delegated)
        document.addEventListener('click', (e) => {
            const watchlistBtn = e.target.closest('.watchlist-btn');
            if (watchlistBtn) {
                e.stopPropagation();
                this.handleWatchlistToggle(watchlistBtn.dataset.ticker);
            }
        });

        // Search results click (delegated)
        UI.elements.searchResults.addEventListener('click', (e) => {
            const resultItem = e.target.closest('.search-result-item');
            if (resultItem) {
                this.handleTickerSelect(resultItem.dataset.ticker);
            }
        });

        // Peer chips click (delegated)
        document.addEventListener('click', (e) => {
            const peerChip = e.target.closest('.peer-chip');
            if (peerChip) {
                this.handleTickerSelect(peerChip.dataset.ticker);
            }
        });
    },

    /**
     * Load initial data
     */
    async loadInitialData() {
        try {
            // Load watchlist first to know which tickers are starred
            await this.loadWatchlist();

            // Load rankings
            await this.loadRankings(this.state.currentCategory);

        } catch (error) {
            console.error('Failed to load initial data:', error);
            UI.showToast('Failed to load data', 'error');
        }
    },

    /**
     * Handle search input (with debounce)
     */
    handleSearchInput(query) {
        clearTimeout(this.state.searchDebounce);

        if (!query || query.length < 1) {
            UI.elements.searchResults.classList.add('hidden');
            return;
        }

        this.state.searchDebounce = setTimeout(async () => {
            await this.performSearch(query);
        }, 300);
    },

    /**
     * Perform search
     */
    async performSearch(query) {
        try {
            const data = await API.searchTickers(query);

            if (data.results && data.results.length > 0) {
                UI.elements.searchResults.innerHTML = '';
                data.results.forEach(result => {
                    const item = UI.renderSearchResult(result);
                    UI.elements.searchResults.appendChild(item);
                });
                UI.elements.searchResults.classList.remove('hidden');
            } else {
                UI.elements.searchResults.innerHTML = `
                    <div class="search-result-item">
                        <div class="text-hint">No results found</div>
                    </div>
                `;
                UI.elements.searchResults.classList.remove('hidden');
            }

        } catch (error) {
            console.error('Search error:', error);
        }
    },

    /**
     * Handle direct search (Enter key or button click)
     */
    handleSearch(query) {
        if (query) {
            this.handleTickerSelect(query.toUpperCase());
        }
    },

    /**
     * Handle tab switch
     */
    handleTabSwitch(tabId) {
        this.state.currentTab = tabId;
        UI.switchTab(tabId);

        if (tabId === 'watchlist') {
            this.loadWatchlist();
        } else if (tabId === 'rankings') {
            this.loadRankings(this.state.currentCategory);
        }
    },

    /**
     * Handle category switch
     */
    async handleCategorySwitch(category) {
        this.state.currentCategory = category;
        UI.switchCategory(category);
        await this.loadRankings(category);
    },

    /**
     * Load rankings
     */
    async loadRankings(category) {
        UI.showLoading(UI.elements.rankingsList, 'Loading rankings...');

        try {
            const data = await API.getRankings(category);

            if (!data.tickers || data.tickers.length === 0) {
                UI.showEmpty(
                    UI.elements.rankingsList,
                    '📊',
                    'No ranking data available',
                    'Data may be delayed outside market hours'
                );
                return;
            }

            UI.elements.rankingsList.innerHTML = '';
            data.tickers.forEach(ticker => {
                const isInWatchlist = this.state.watchlist.has(ticker.ticker);
                const card = UI.renderTickerCard(ticker, {
                    isInWatchlist,
                    onClick: (t) => this.handleTickerSelect(t.ticker)
                });
                UI.elements.rankingsList.appendChild(card);
            });

        } catch (error) {
            console.error('Failed to load rankings:', error);
            UI.showError(UI.elements.rankingsList, 'Failed to load rankings');
            UI.elements.rankingsList.onclick = () => this.loadRankings(category);
        }
    },

    /**
     * Load watchlist
     */
    async loadWatchlist() {
        UI.showLoading(UI.elements.watchlistList, 'Loading watchlist...');

        try {
            const data = await API.getWatchlist();

            // Update local watchlist state
            this.state.watchlist = new Set(data.tickers?.map(t => t.ticker) || []);

            if (!data.tickers || data.tickers.length === 0) {
                UI.showEmpty(
                    UI.elements.watchlistList,
                    '⭐',
                    'Your watchlist is empty',
                    'Search for tickers to add them'
                );
                return;
            }

            UI.elements.watchlistList.innerHTML = '';
            data.tickers.forEach(ticker => {
                const card = UI.renderTickerCard({
                    ticker: ticker.ticker,
                    company_name: ticker.company_name
                }, {
                    showPrice: false,
                    isInWatchlist: true,
                    onClick: (t) => this.handleTickerSelect(t.ticker)
                });
                UI.elements.watchlistList.appendChild(card);
            });

        } catch (error) {
            console.error('Failed to load watchlist:', error);
            UI.showError(UI.elements.watchlistList, 'Failed to load watchlist');
            UI.elements.watchlistList.onclick = () => this.loadWatchlist();
        }
    },

    /**
     * Handle ticker selection - show report
     */
    async handleTickerSelect(ticker) {
        UI.elements.searchResults.classList.add('hidden');
        UI.elements.searchInput.value = '';

        UI.elements.reportTicker.textContent = ticker;
        UI.showLoading(UI.elements.reportBody, 'Generating AI analysis...');
        UI.showModal();

        Config.haptic('medium');

        try {
            const report = await API.getReport(ticker);
            UI.elements.reportBody.innerHTML = UI.renderReport(report);

        } catch (error) {
            console.error('Failed to load report:', error);
            UI.elements.reportBody.innerHTML = `
                <div class="empty-state">
                    <span class="empty-icon">❌</span>
                    <p>Failed to generate report</p>
                    <p class="empty-hint">${error.message}</p>
                </div>
            `;
            Config.haptic('error');
        }
    },

    /**
     * Handle watchlist toggle
     */
    async handleWatchlistToggle(ticker) {
        const isInWatchlist = this.state.watchlist.has(ticker);

        try {
            if (isInWatchlist) {
                await API.removeFromWatchlist(ticker);
                this.state.watchlist.delete(ticker);
                UI.showToast(`Removed ${ticker} from watchlist`, 'success');
            } else {
                await API.addToWatchlist(ticker);
                this.state.watchlist.add(ticker);
                UI.showToast(`Added ${ticker} to watchlist`, 'success');
            }

            // Update UI
            this.updateWatchlistButtons();

            // Refresh watchlist if on that tab
            if (this.state.currentTab === 'watchlist') {
                await this.loadWatchlist();
            }

            Config.haptic('success');

        } catch (error) {
            console.error('Watchlist toggle error:', error);
            UI.showToast(error.message || 'Failed to update watchlist', 'error');
            Config.haptic('error');
        }
    },

    /**
     * Update all watchlist buttons to reflect current state
     */
    updateWatchlistButtons() {
        document.querySelectorAll('.watchlist-btn').forEach(btn => {
            const ticker = btn.dataset.ticker;
            const isInWatchlist = this.state.watchlist.has(ticker);
            btn.classList.toggle('active', isInWatchlist);
            btn.textContent = isInWatchlist ? '⭐' : '☆';
        });
    }
};

// Initialize app when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    App.init();
});
