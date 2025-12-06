/**
 * Telegram WebApp SDK Hook
 *
 * React hook to initialize and manage Telegram WebApp SDK.
 * Provides access to:
 * - initData for authentication
 * - user information
 * - theme parameters
 * - platform detection
 * - WebApp methods (ready, expand, close, etc.)
 *
 * Usage:
 * ```typescript
 * const { webApp, initData, user, isTelegram } = useTelegramWebApp();
 *
 * if (isTelegram) {
 *   // Running in Telegram
 *   apiClient.setInitData(initData);
 * } else {
 *   // Local development
 *   apiClient.setDevUserId('12345');
 * }
 * ```
 */

import { useEffect, useState } from 'react';

/**
 * Telegram WebApp type definitions
 * Based on https://core.telegram.org/bots/webapps#initializing-mini-apps
 */
declare global {
  interface Window {
    Telegram?: {
      WebApp: {
        initData: string;
        initDataUnsafe: {
          query_id?: string;
          user?: {
            id: number;
            first_name: string;
            last_name?: string;
            username?: string;
            language_code?: string;
            is_premium?: boolean;
          };
          auth_date: number;
          hash: string;
        };
        version: string;
        platform: string;
        colorScheme: 'light' | 'dark';
        themeParams: {
          bg_color?: string;
          text_color?: string;
          hint_color?: string;
          link_color?: string;
          button_color?: string;
          button_text_color?: string;
          secondary_bg_color?: string;
        };
        isExpanded: boolean;
        viewportHeight: number;
        viewportStableHeight: number;
        headerColor: string;
        backgroundColor: string;
        BackButton: {
          isVisible: boolean;
          show: () => void;
          hide: () => void;
          onClick: (callback: () => void) => void;
          offClick: (callback: () => void) => void;
        };
        MainButton: {
          text: string;
          color: string;
          textColor: string;
          isVisible: boolean;
          isActive: boolean;
          isProgressVisible: boolean;
          setText: (text: string) => void;
          onClick: (callback: () => void) => void;
          offClick: (callback: () => void) => void;
          show: () => void;
          hide: () => void;
          enable: () => void;
          disable: () => void;
          showProgress: (leaveActive?: boolean) => void;
          hideProgress: () => void;
          setParams: (params: {
            text?: string;
            color?: string;
            text_color?: string;
            is_active?: boolean;
            is_visible?: boolean;
          }) => void;
        };
        HapticFeedback: {
          impactOccurred: (style: 'light' | 'medium' | 'heavy' | 'rigid' | 'soft') => void;
          notificationOccurred: (type: 'error' | 'success' | 'warning') => void;
          selectionChanged: () => void;
        };
        ready: () => void;
        expand: () => void;
        close: () => void;
        enableClosingConfirmation: () => void;
        disableClosingConfirmation: () => void;
        sendData: (data: string) => void;
        openLink: (url: string, options?: { try_instant_view?: boolean }) => void;
        openTelegramLink: (url: string) => void;
        openInvoice: (url: string, callback?: (status: string) => void) => void;
        showPopup: (params: {
          title?: string;
          message: string;
          buttons?: Array<{
            id?: string;
            type?: 'default' | 'ok' | 'close' | 'cancel' | 'destructive';
            text?: string;
          }>;
        }, callback?: (buttonId: string) => void) => void;
        showAlert: (message: string, callback?: () => void) => void;
        showConfirm: (message: string, callback?: (confirmed: boolean) => void) => void;
        showScanQrPopup: (params: { text?: string }, callback?: (data: string) => void) => void;
        closeScanQrPopup: () => void;
        readTextFromClipboard: (callback?: (text: string) => void) => void;
        requestWriteAccess: (callback?: (granted: boolean) => void) => void;
        requestContact: (callback?: (granted: boolean, contact?: any) => void) => void;
      };
    };
  }
}

export interface TelegramWebApp {
  webApp: any; // Telegram WebApp SDK object or null
  initData: string;
  user: {
    id: number;
    firstName: string;
    lastName?: string;
    username?: string;
    languageCode?: string;
    isPremium?: boolean;
  } | null;
  colorScheme: 'light' | 'dark';
  platform: string;
  version: string;
  isTelegram: boolean;
  isReady: boolean;
}

/**
 * useTelegramWebApp Hook
 *
 * Initializes Telegram WebApp SDK and provides reactive state
 */
export function useTelegramWebApp(): TelegramWebApp {
  const [isReady, setIsReady] = useState(false);

  useEffect(() => {
    const tg = window.Telegram?.WebApp;

    if (tg) {
      // Initialize Telegram WebApp
      tg.ready();
      tg.expand();
      tg.enableClosingConfirmation();

      console.log('✅ Telegram WebApp initialized');
      console.log('  Platform:', tg.platform);
      console.log('  Version:', tg.version);
      console.log('  Color scheme:', tg.colorScheme);
      console.log('  User:', tg.initDataUnsafe.user);

      setIsReady(true);
    } else {
      console.log('⚠️ Not running in Telegram WebApp (local development)');
      setIsReady(true);
    }
  }, []);

  const tg = window.Telegram?.WebApp;
  const isTelegram = !!tg;

  return {
    webApp: tg || null,
    initData: tg?.initData || '',
    user: tg?.initDataUnsafe.user ? {
      id: tg.initDataUnsafe.user.id,
      firstName: tg.initDataUnsafe.user.first_name,
      lastName: tg.initDataUnsafe.user.last_name,
      username: tg.initDataUnsafe.user.username,
      languageCode: tg.initDataUnsafe.user.language_code,
      isPremium: tg.initDataUnsafe.user.is_premium,
    } : null,
    colorScheme: tg?.colorScheme || 'light',
    platform: tg?.platform || 'web',
    version: tg?.version || '0.0.0',
    isTelegram,
    isReady,
  };
}
