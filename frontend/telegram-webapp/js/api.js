/**
 * API Client for DR Daily Report
 */

const API = {
    /**
     * Make authenticated API request
     */
    async request(endpoint, options = {}) {
        const url = `${Config.API_BASE_URL}${endpoint}`;

        const headers = {
            'Content-Type': 'application/json',
            ...options.headers
        };

        // Add authentication header
        const initData = Config.getInitData();
        if (initData) {
            headers['X-Telegram-Init-Data'] = initData;
        } else {
            // Development fallback
            headers['X-Telegram-User-Id'] = Config.getUserId();
        }

        Config.debug('API Request:', { url, method: options.method || 'GET', headers });

        try {
            const response = await fetch(url, {
                ...options,
                headers
            });

            const data = await response.json();

            if (!response.ok) {
                throw new APIError(
                    data.error?.code || 'UNKNOWN_ERROR',
                    data.error?.message || 'An error occurred',
                    response.status
                );
            }

            Config.debug('API Response:', data);
            return data;

        } catch (error) {
            if (error instanceof APIError) {
                throw error;
            }
            throw new APIError('NETWORK_ERROR', error.message, 0);
        }
    },

    /**
     * Search tickers
     */
    async searchTickers(query, limit = 10) {
        if (!query || query.length < 1) {
            return { results: [] };
        }
        return this.request(`/search?q=${encodeURIComponent(query)}&limit=${limit}`);
    },

    /**
     * Get ticker report
     */
    async getReport(ticker) {
        return this.request(`/report/${encodeURIComponent(ticker)}`);
    },

    /**
     * Get rankings by category
     */
    async getRankings(category = 'top_gainers', limit = 10) {
        return this.request(`/rankings?category=${encodeURIComponent(category)}&limit=${limit}`);
    },

    /**
     * Get user watchlist
     */
    async getWatchlist() {
        return this.request('/watchlist');
    },

    /**
     * Add ticker to watchlist
     */
    async addToWatchlist(ticker) {
        return this.request('/watchlist', {
            method: 'POST',
            body: JSON.stringify({ ticker })
        });
    },

    /**
     * Remove ticker from watchlist
     */
    async removeFromWatchlist(ticker) {
        return this.request(`/watchlist/${encodeURIComponent(ticker)}`, {
            method: 'DELETE'
        });
    },

    /**
     * Check API health
     */
    async checkHealth() {
        return this.request('/health');
    }
};

/**
 * Custom API Error class
 */
class APIError extends Error {
    constructor(code, message, statusCode) {
        super(message);
        this.name = 'APIError';
        this.code = code;
        this.statusCode = statusCode;
    }
}

// Simple cache implementation
const Cache = {
    _data: new Map(),

    set(key, value) {
        this._data.set(key, {
            value,
            timestamp: Date.now()
        });
    },

    get(key) {
        const entry = this._data.get(key);
        if (!entry) return null;

        // Check if expired
        if (Date.now() - entry.timestamp > Config.CACHE_TTL_MS) {
            this._data.delete(key);
            return null;
        }

        return entry.value;
    },

    clear() {
        this._data.clear();
    }
};
