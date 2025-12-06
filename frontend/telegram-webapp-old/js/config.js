/**
 * Configuration for DR Daily Report Telegram Mini App
 */

const Config = {
    // API Base URL - configurable via window.TELEGRAM_API_URL (set by deployment)
    // Falls back to dev API if not set
    API_BASE_URL: window.TELEGRAM_API_URL || 'https://ou0ivives1.execute-api.ap-southeast-1.amazonaws.com/api/v1',

    // Telegram WebApp instance
    tg: window.Telegram?.WebApp,

    // Feature flags
    ENABLE_HAPTIC_FEEDBACK: true,
    ENABLE_DEBUG_MODE: false,

    // Cache settings
    CACHE_TTL_MS: 5 * 60 * 1000, // 5 minutes

    // Rankings categories
    RANKING_CATEGORIES: [
        { id: 'top_gainers', label: '🚀 Top Gainers' },
        { id: 'top_losers', label: '📉 Top Losers' },
        { id: 'volume_surge', label: '📊 Volume Surge' },
        { id: 'trending', label: '🔥 Trending' }
    ],

    /**
     * Get initData for API authentication
     */
    getInitData() {
        if (this.tg?.initData) {
            return this.tg.initData;
        }
        return null;
    },

    /**
     * Get user ID (for development/testing)
     */
    getUserId() {
        if (this.tg?.initDataUnsafe?.user?.id) {
            return String(this.tg.initDataUnsafe.user.id);
        }
        // Fallback for development
        return 'dev_user_' + Date.now();
    },

    /**
     * Check if running in Telegram WebApp
     */
    isInTelegram() {
        return Boolean(this.tg?.initData);
    },

    /**
     * Initialize Telegram WebApp
     */
    initTelegram() {
        if (!this.tg) {
            console.warn('Telegram WebApp not available');
            return;
        }

        // Expand to full height
        this.tg.expand();

        // Enable closing confirmation if needed
        // this.tg.enableClosingConfirmation();

        // Set header color
        this.tg.setHeaderColor('bg_color');

        // Ready signal
        this.tg.ready();

        console.log('Telegram WebApp initialized', {
            version: this.tg.version,
            platform: this.tg.platform,
            colorScheme: this.tg.colorScheme,
            userId: this.getUserId()
        });
    },

    /**
     * Trigger haptic feedback
     */
    haptic(type = 'light') {
        if (!this.ENABLE_HAPTIC_FEEDBACK || !this.tg?.HapticFeedback) {
            return;
        }

        switch (type) {
            case 'light':
                this.tg.HapticFeedback.impactOccurred('light');
                break;
            case 'medium':
                this.tg.HapticFeedback.impactOccurred('medium');
                break;
            case 'heavy':
                this.tg.HapticFeedback.impactOccurred('heavy');
                break;
            case 'success':
                this.tg.HapticFeedback.notificationOccurred('success');
                break;
            case 'error':
                this.tg.HapticFeedback.notificationOccurred('error');
                break;
            case 'warning':
                this.tg.HapticFeedback.notificationOccurred('warning');
                break;
        }
    },

    /**
     * Debug log (only in debug mode)
     */
    debug(...args) {
        if (this.ENABLE_DEBUG_MODE) {
            console.log('[DEBUG]', ...args);
        }
    }
};

// Freeze config to prevent modifications
Object.freeze(Config);
