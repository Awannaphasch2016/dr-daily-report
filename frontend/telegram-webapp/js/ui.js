/**
 * UI Components and Helpers
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
            tabBtns: document.querySelectorAll('.tab-btn'),
            tabPanels: document.querySelectorAll('.tab-panel'),
            categoryBtns: document.querySelectorAll('.category-btn'),
            rankingsList: document.getElementById('rankings-list'),
            watchlistList: document.getElementById('watchlist-list'),
            reportModal: document.getElementById('report-modal'),
            reportTicker: document.getElementById('report-ticker'),
            reportBody: document.getElementById('report-body'),
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

        // Trigger animation
        requestAnimationFrame(() => {
            toast.classList.add('visible');
        });

        // Remove after duration
        setTimeout(() => {
            toast.classList.remove('visible');
            setTimeout(() => toast.remove(), 300);
        }, duration);

        // Haptic feedback
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
                ${hint ? `<p class="empty-hint">${hint}</p>` : ''}
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
                <p class="empty-hint">Tap to retry</p>
            </div>
        `;
    },

    /**
     * Render ticker card
     */
    renderTickerCard(ticker, options = {}) {
        const {
            showPrice = true,
            showChange = true,
            showWatchlist = true,
            isInWatchlist = false,
            onClick = null
        } = options;

        const changeClass = ticker.price_change_pct >= 0 ? 'positive' : 'negative';
        const changeSign = ticker.price_change_pct >= 0 ? '+' : '';

        const card = document.createElement('div');
        card.className = 'ticker-card';
        card.dataset.ticker = ticker.ticker;

        card.innerHTML = `
            <div class="ticker-info">
                <div class="ticker-symbol">${ticker.ticker}</div>
                <div class="ticker-name">${ticker.company_name || ''}</div>
            </div>
            ${showPrice ? `
            <div class="ticker-price">
                ${ticker.price ? `<div class="ticker-price-value">${this.formatPrice(ticker.price, ticker.currency)}</div>` : ''}
                ${showChange && ticker.price_change_pct !== undefined ? `
                    <div class="ticker-price-change ${changeClass}">
                        ${changeSign}${ticker.price_change_pct.toFixed(2)}%
                    </div>
                ` : ''}
            </div>
            ` : ''}
            ${showWatchlist ? `
            <div class="ticker-actions">
                <button class="watchlist-btn ${isInWatchlist ? 'active' : ''}" data-ticker="${ticker.ticker}">
                    ${isInWatchlist ? '⭐' : '☆'}
                </button>
            </div>
            ` : ''}
        `;

        if (onClick) {
            card.addEventListener('click', (e) => {
                if (!e.target.closest('.watchlist-btn')) {
                    onClick(ticker);
                }
            });
        }

        return card;
    },

    /**
     * Render search result item
     */
    renderSearchResult(result) {
        const item = document.createElement('div');
        item.className = 'search-result-item';
        item.dataset.ticker = result.ticker;

        item.innerHTML = `
            <div class="ticker-info">
                <div class="ticker-symbol">${result.ticker}</div>
                <div class="ticker-name">${result.company_name || ''}</div>
            </div>
        `;

        return item;
    },

    /**
     * Render report modal content
     */
    renderReport(report) {
        const stanceClass = report.stance === 'bullish' ? 'text-bullish' :
                           report.stance === 'bearish' ? 'text-bearish' : 'text-neutral';
        const stanceEmoji = report.stance === 'bullish' ? '📈' :
                           report.stance === 'bearish' ? '📉' : '➡️';

        return `
            <div class="report-header">
                <div>
                    <div class="report-company-name">${report.company_name}</div>
                    <div class="text-hint">${report.currency} • ${report.as_of}</div>
                </div>
            </div>

            <div class="report-stance">
                <div class="report-stance-label">Market Stance</div>
                <div class="report-stance-value ${stanceClass}">
                    ${stanceEmoji} ${report.stance?.toUpperCase() || 'N/A'}
                    ${report.confidence ? `<span class="text-hint">(${report.confidence} confidence)</span>` : ''}
                </div>
            </div>

            ${report.summary_sections ? this.renderSummarySections(report.summary_sections) : ''}

            ${report.narrative_report ? this.renderNarrativeReport(report.narrative_report) : ''}

            ${report.technical_metrics?.length ? `
            <div class="report-section">
                <div class="report-section-title">📊 Technical Metrics</div>
                <div class="report-section-content">
                    ${report.technical_metrics.map(m => `
                        <div class="report-metric">
                            <span class="report-metric-name">${m.name}</span>
                            <span class="report-metric-value">${m.value}${m.unit || ''}</span>
                        </div>
                    `).join('')}
                </div>
            </div>
            ` : ''}

            ${report.fundamentals ? this.renderFundamentals(report.fundamentals) : ''}

            ${report.peers?.length ? `
            <div class="report-section">
                <div class="report-section-title">👥 Related Peers</div>
                <div class="peers-list">
                    ${report.peers.map(p => `
                        <span class="peer-chip" data-ticker="${p.ticker}">${p.ticker}</span>
                    `).join('')}
                </div>
            </div>
            ` : ''}

            ${report.news?.length ? `
            <div class="report-section">
                <div class="report-section-title">📰 Recent News</div>
                <div class="report-section-content">
                    ${report.news.slice(0, 3).map(n => `
                        <div class="news-item">
                            <div class="news-title">${n.title}</div>
                            <div class="news-meta">
                                <span>${n.source}</span>
                                <span>${n.timestamp}</span>
                            </div>
                        </div>
                    `).join('')}
                </div>
            </div>
            ` : ''}

            ${report.risk ? `
            <div class="report-section">
                <div class="report-section-title">⚠️ Risk Assessment</div>
                <div class="badge badge-${report.risk.risk_level || 'medium'}">${report.risk.risk_level || 'N/A'}</div>
                <div class="report-section-content" style="margin-top: var(--spacing-sm);">
                    ${report.risk.risk_bullets?.map(b => `
                        <div class="report-bullet">${b}</div>
                    `).join('') || ''}
                </div>
            </div>
            ` : ''}
        `;
    },

    /**
     * Render summary sections
     */
    renderSummarySections(sections) {
        let html = '';

        if (sections.key_takeaways?.length) {
            html += `
            <div class="report-section">
                <div class="report-section-title">💡 Key Takeaways</div>
                <div class="report-section-content">
                    ${sections.key_takeaways.map(t => `
                        <div class="report-bullet">${t}</div>
                    `).join('')}
                </div>
            </div>
            `;
        }

        if (sections.price_drivers?.length) {
            html += `
            <div class="report-section">
                <div class="report-section-title">🚀 Price Drivers</div>
                <div class="report-section-content">
                    ${sections.price_drivers.map(d => `
                        <div class="report-bullet">${d}</div>
                    `).join('')}
                </div>
            </div>
            `;
        }

        if (sections.risks_to_watch?.length) {
            html += `
            <div class="report-section">
                <div class="report-section-title">👁️ Risks to Watch</div>
                <div class="report-section-content">
                    ${sections.risks_to_watch.map(r => `
                        <div class="report-bullet">${r}</div>
                    `).join('')}
                </div>
            </div>
            `;
        }

        return html;
    },

    /**
     * Render narrative report (LLM-generated analysis)
     * This is the full Thai language analysis explaining the "why" behind the takeaways
     */
    renderNarrativeReport(narrativeReport) {
        if (!narrativeReport) return '';

        // Convert markdown-style formatting to HTML
        // **text** -> <strong>text</strong>
        // \n -> <br> for line breaks
        let formattedReport = narrativeReport
            .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
            .replace(/\n\n/g, '</p><p>')
            .replace(/\n/g, '<br>');

        return `
        <div class="report-section">
            <div class="report-section-title">📝 Analysis Report</div>
            <div class="report-section-content narrative-report">
                <p>${formattedReport}</p>
            </div>
        </div>
        `;
    },

    /**
     * Render fundamentals section
     * API returns: fundamentals.valuation, fundamentals.growth, fundamentals.profitability
     */
    renderFundamentals(fundamentals) {
        let html = '<div class="report-section"><div class="report-section-title">📈 Fundamentals</div>';
        html += '<div class="report-section-content">';

        // Valuation metrics (P/E, Market Cap)
        if (fundamentals.valuation?.length) {
            html += '<div class="report-subsection"><strong>Valuation</strong></div>';
            html += fundamentals.valuation.map(m => `
                <div class="report-metric">
                    <span class="report-metric-name">${m.name}</span>
                    <span class="report-metric-value">${this.formatMetricValue(m.value, m.name)}${m.unit || ''}</span>
                </div>
            `).join('');
        }

        // Growth metrics (Revenue Growth, Earnings Growth)
        if (fundamentals.growth?.length) {
            html += '<div class="report-subsection"><strong>Growth</strong></div>';
            html += fundamentals.growth.map(m => `
                <div class="report-metric">
                    <span class="report-metric-name">${m.name}</span>
                    <span class="report-metric-value">${this.formatMetricValue(m.value, m.name)}${m.unit || ''}</span>
                </div>
            `).join('');
        }

        // Profitability metrics (EPS, Dividend Yield)
        if (fundamentals.profitability?.length) {
            html += '<div class="report-subsection"><strong>Profitability</strong></div>';
            html += fundamentals.profitability.map(m => `
                <div class="report-metric">
                    <span class="report-metric-name">${m.name}</span>
                    <span class="report-metric-value">${this.formatMetricValue(m.value, m.name)}${m.unit || ''}</span>
                </div>
            `).join('');
        }

        html += '</div></div>';
        return html;
    },

    /**
     * Format metric value based on metric name
     */
    formatMetricValue(value, name) {
        if (value === null || value === undefined) return 'N/A';

        // Format large numbers (Market Cap)
        if (name?.toLowerCase().includes('market cap')) {
            if (value >= 1e12) return `$${(value / 1e12).toFixed(1)}T`;
            if (value >= 1e9) return `$${(value / 1e9).toFixed(1)}B`;
            if (value >= 1e6) return `$${(value / 1e6).toFixed(1)}M`;
            return `$${value.toLocaleString()}`;
        }

        // Format percentages (Growth, Yield)
        if (name?.toLowerCase().includes('growth') || name?.toLowerCase().includes('yield')) {
            return `${value.toFixed(1)}%`;
        }

        // Format ratios (P/E, EPS)
        if (typeof value === 'number') {
            return value.toFixed(2);
        }

        return value;
    },

    /**
     * Format price with currency
     */
    formatPrice(price, currency = 'USD') {
        const formatter = new Intl.NumberFormat('en-US', {
            style: 'currency',
            currency: currency,
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        });
        return formatter.format(price);
    },

    /**
     * Show modal
     */
    showModal() {
        this.elements.reportModal.classList.remove('hidden');
        requestAnimationFrame(() => {
            this.elements.reportModal.classList.add('visible');
        });
        document.body.style.overflow = 'hidden';
    },

    /**
     * Hide modal
     */
    hideModal() {
        this.elements.reportModal.classList.remove('visible');
        setTimeout(() => {
            this.elements.reportModal.classList.add('hidden');
            document.body.style.overflow = '';
        }, 300);
    },

    /**
     * Switch tab
     */
    switchTab(tabId) {
        // Update tab buttons
        this.elements.tabBtns.forEach(btn => {
            btn.classList.toggle('active', btn.dataset.tab === tabId);
        });

        // Update tab panels
        this.elements.tabPanels.forEach(panel => {
            panel.classList.toggle('hidden', panel.id !== `${tabId}-tab`);
            panel.classList.toggle('active', panel.id === `${tabId}-tab`);
        });

        Config.haptic('light');
    },

    /**
     * Switch category
     */
    switchCategory(categoryId) {
        this.elements.categoryBtns.forEach(btn => {
            btn.classList.toggle('active', btn.dataset.category === categoryId);
        });
        Config.haptic('light');
    }
};
