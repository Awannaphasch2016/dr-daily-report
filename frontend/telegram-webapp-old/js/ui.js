/**
 * Twinbar UI Components and Helpers
 */

const UI = {
    // DOM element references (cached after init)
    elements: {},

    /**
     * Initialize UI - cache DOM elements
     */
    init() {
        this.elements = {
            searchInput: document.getElementById('search-input'),
            searchBtn: document.getElementById('search-btn'),
            searchResults: document.getElementById('search-results'),
            categoryChips: document.querySelectorAll('.category-chip'),
            sortBtns: document.querySelectorAll('.sort-btn'),
            marketsGrid: document.getElementById('markets-grid'),
            marketModal: document.getElementById('market-modal'),
            marketTitle: document.getElementById('market-title'),
            marketBody: document.getElementById('market-body'),
            modalClose: document.querySelector('.modal-close'),
            toastContainer: document.getElementById('toast-container')
        };
    },

    /**
     * Show toast notification
     */
    showToast(message, type = 'info', duration = 3000) {
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        toast.textContent = message;

        this.elements.toastContainer.appendChild(toast);

        requestAnimationFrame(() => {
            toast.classList.add('visible');
        });

        setTimeout(() => {
            toast.classList.remove('visible');
            setTimeout(() => toast.remove(), 300);
        }, duration);

        if (type === 'error') {
            Config.haptic('error');
        } else if (type === 'success') {
            Config.haptic('success');
        }
    },

    /**
     * Show loading state
     */
    showLoading(container, message = 'Loading...') {
        container.innerHTML = `
            <div class="loading-indicator">
                <span class="spinner"></span>
                <span>${message}</span>
            </div>
        `;
    },

    /**
     * Show empty state
     */
    showEmpty(container, icon = '📋', message = 'No data', hint = '') {
        container.innerHTML = `
            <div class="empty-state">
                <span class="empty-icon">${icon}</span>
                <p>${message}</p>
                ${hint ? `<p class="text-hint">${hint}</p>` : ''}
            </div>
        `;
    },

    /**
     * Show error state
     */
    showError(container, message = 'Failed to load data') {
        container.innerHTML = `
            <div class="empty-state">
                <span class="empty-icon">❌</span>
                <p>${message}</p>
                <p class="text-hint">Tap to retry</p>
            </div>
        `;
    },

    /**
     * Render market card
     */
    renderMarketCard(market) {
        const card = document.createElement('div');
        card.className = 'market-card';
        card.dataset.marketId = market.id;

        const yesOdds = market.yes_odds || market.yesOdds || 50;
        const noOdds = market.no_odds || market.noOdds || 50;

        card.innerHTML = `
            ${market.image ? `<img src="${market.image}" alt="" class="market-image">` : ''}
            <div class="market-title">${market.title || market.question}</div>
            <div class="market-meta">
                <span class="market-volume">${this.formatVolume(market.volume)}</span>
                ${market.ends_at ? `<span class="market-ends">Ends ${this.formatDate(market.ends_at)}</span>` : ''}
            </div>
            <div class="market-outcomes">
                <button class="outcome-btn yes" data-outcome="yes" data-market-id="${market.id}">
                    <span class="outcome-label">Yes</span>
                    <span class="outcome-odds">${yesOdds}¢</span>
                </button>
                <button class="outcome-btn no" data-outcome="no" data-market-id="${market.id}">
                    <span class="outcome-label">No</span>
                    <span class="outcome-odds">${noOdds}¢</span>
                </button>
            </div>
        `;

        return card;
    },

    /**
     * Render markets grid
     */
    renderMarkets(markets) {
        const grid = this.elements.marketsGrid;
        grid.innerHTML = '';

        if (!markets || markets.length === 0) {
            this.showEmpty(grid, '🔍', 'No markets found', 'Try a different category or search');
            return;
        }

        markets.forEach(market => {
            const card = this.renderMarketCard(market);
            grid.appendChild(card);
        });
    },

    /**
     * Render market detail in modal
     */
    renderMarketDetail(market) {
        const yesOdds = market.yes_odds || market.yesOdds || 50;
        const noOdds = market.no_odds || market.noOdds || 50;

        return `
            ${market.image ? `<img src="${market.image}" alt="" class="market-image" style="height: 180px;">` : ''}

            <div class="market-description" style="margin-bottom: var(--spacing-md);">
                ${market.description || 'No description available.'}
            </div>

            <div class="market-stats" style="display: grid; grid-template-columns: 1fr 1fr; gap: var(--spacing-md); margin-bottom: var(--spacing-lg);">
                <div style="text-align: center;">
                    <div class="text-hint" style="font-size: var(--font-xs);">Volume</div>
                    <div style="font-weight: var(--weight-semibold);">${this.formatVolume(market.volume)}</div>
                </div>
                <div style="text-align: center;">
                    <div class="text-hint" style="font-size: var(--font-xs);">Liquidity</div>
                    <div style="font-weight: var(--weight-semibold);">${this.formatVolume(market.liquidity)}</div>
                </div>
            </div>

            <div style="margin-bottom: var(--spacing-md);">
                <div class="text-hint" style="font-size: var(--font-xs); margin-bottom: var(--spacing-sm);">Current Odds</div>
                <div class="market-outcomes">
                    <button class="outcome-btn yes" data-outcome="yes" data-market-id="${market.id}" style="flex-direction: row; justify-content: space-between;">
                        <span>Buy Yes</span>
                        <span class="outcome-odds">${yesOdds}¢</span>
                    </button>
                    <button class="outcome-btn no" data-outcome="no" data-market-id="${market.id}" style="flex-direction: row; justify-content: space-between;">
                        <span>Buy No</span>
                        <span class="outcome-odds">${noOdds}¢</span>
                    </button>
                </div>
            </div>

            ${market.ends_at ? `
            <div class="text-hint" style="font-size: var(--font-xs); text-align: center;">
                Market ends ${this.formatDate(market.ends_at)}
            </div>
            ` : ''}
        `;
    },

    /**
     * Format volume display
     */
    formatVolume(volume) {
        if (!volume) return '$0';
        if (volume >= 1000000) return `$${(volume / 1000000).toFixed(1)}M`;
        if (volume >= 1000) return `$${(volume / 1000).toFixed(1)}K`;
        return `$${volume}`;
    },

    /**
     * Format date display
     */
    formatDate(dateStr) {
        if (!dateStr) return '';
        const date = new Date(dateStr);
        const now = new Date();
        const diffDays = Math.ceil((date - now) / (1000 * 60 * 60 * 24));

        if (diffDays <= 0) return 'Today';
        if (diffDays === 1) return 'Tomorrow';
        if (diffDays <= 7) return `in ${diffDays} days`;
        return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
    },

    /**
     * Show modal
     */
    showModal() {
        this.elements.marketModal.classList.remove('hidden');
        requestAnimationFrame(() => {
            this.elements.marketModal.classList.add('visible');
        });
        document.body.style.overflow = 'hidden';
    },

    /**
     * Hide modal
     */
    hideModal() {
        this.elements.marketModal.classList.remove('visible');
        setTimeout(() => {
            this.elements.marketModal.classList.add('hidden');
            document.body.style.overflow = '';
        }, 300);
    },

    /**
     * Switch category
     */
    switchCategory(categoryId) {
        this.elements.categoryChips.forEach(chip => {
            chip.classList.toggle('active', chip.dataset.category === categoryId);
        });
        Config.haptic('light');
    },

    /**
     * Switch sort
     */
    switchSort(sortId) {
        this.elements.sortBtns.forEach(btn => {
            btn.classList.toggle('active', btn.dataset.sort === sortId);
        });
        Config.haptic('light');
    }
};
