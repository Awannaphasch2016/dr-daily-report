/**
 * Telegram Theme Hook
 *
 * Applies Telegram's theme parameters to the app's CSS variables.
 * Synchronizes the app's color scheme with the user's Telegram theme
 * (light/dark mode).
 *
 * Usage:
 * ```typescript
 * const { colorScheme, themeParams } = useTelegramTheme();
 * ```
 */

import { useEffect } from 'react';
import { useTelegramWebApp } from './useTelegramWebApp';

/**
 * Apply Telegram theme to CSS variables
 *
 * Maps Telegram's themeParams to CSS custom properties
 */
function applyTelegramTheme(
  colorScheme: 'light' | 'dark',
  themeParams?: {
    bg_color?: string;
    text_color?: string;
    hint_color?: string;
    link_color?: string;
    button_color?: string;
    button_text_color?: string;
    secondary_bg_color?: string;
  }
) {
  const root = document.documentElement;

  // Add theme class to body
  document.body.classList.remove('tg-light', 'tg-dark');
  document.body.classList.add(`tg-${colorScheme}`);

  // Apply Telegram theme parameters if available
  if (themeParams) {
    if (themeParams.bg_color) {
      root.style.setProperty('--tg-theme-bg-color', themeParams.bg_color);
      root.style.setProperty('--color-bg', themeParams.bg_color);
    }

    if (themeParams.text_color) {
      root.style.setProperty('--tg-theme-text-color', themeParams.text_color);
      root.style.setProperty('--color-text', themeParams.text_color);
    }

    if (themeParams.hint_color) {
      root.style.setProperty('--tg-theme-hint-color', themeParams.hint_color);
      root.style.setProperty('--color-text-secondary', themeParams.hint_color);
    }

    if (themeParams.link_color) {
      root.style.setProperty('--tg-theme-link-color', themeParams.link_color);
      root.style.setProperty('--color-primary', themeParams.link_color);
    }

    if (themeParams.button_color) {
      root.style.setProperty('--tg-theme-button-color', themeParams.button_color);
    }

    if (themeParams.button_text_color) {
      root.style.setProperty('--tg-theme-button-text-color', themeParams.button_text_color);
    }

    if (themeParams.secondary_bg_color) {
      root.style.setProperty('--tg-theme-secondary-bg-color', themeParams.secondary_bg_color);
      root.style.setProperty('--color-bg-secondary', themeParams.secondary_bg_color);
    }

    console.log('✅ Telegram theme applied:', colorScheme, themeParams);
  } else {
    console.log('⚠️ No Telegram theme params - using default theme');
  }
}

/**
 * useTelegramTheme Hook
 *
 * Auto-applies Telegram theme to the app
 */
export function useTelegramTheme() {
  const { colorScheme, webApp, isTelegram } = useTelegramWebApp();

  useEffect(() => {
    if (isTelegram && webApp) {
      applyTelegramTheme(colorScheme, webApp.themeParams);
    } else {
      // Local development - use default light theme
      document.body.classList.remove('tg-light', 'tg-dark');
      document.body.classList.add('tg-light');
    }
  }, [isTelegram, webApp, colorScheme]);

  return {
    colorScheme,
    themeParams: webApp?.themeParams || null,
    isTelegram,
  };
}
