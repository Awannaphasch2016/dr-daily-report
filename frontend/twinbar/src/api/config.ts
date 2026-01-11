/**
 * API Client Configuration
 *
 * Configuration constants for the API client layer.
 */

/**
 * API version prefix
 */
export const API_VERSION = '/api/v1';

/**
 * Get full API base path for requests
 *
 * Priority:
 * 1. Runtime injection via window.TELEGRAM_API_URL (CI/CD workflow)
 *    - Already includes /api/v1, use as-is
 * 2. Build-time VITE_API_BASE_URL from .env files
 *    - Append API_VERSION
 * 3. Empty string with API_VERSION (relative URLs for same-origin)
 */
const getApiBasePath = (): string => {
  // Runtime injection from CI/CD workflow (sed into index.html)
  // NOTE: TELEGRAM_API_URL already includes /api/v1, don't append again
  if (typeof window !== 'undefined' && (window as any).TELEGRAM_API_URL) {
    return (window as any).TELEGRAM_API_URL;
  }
  // Build-time environment variable - append API_VERSION
  const baseUrl = import.meta.env.VITE_API_BASE_URL || '';
  return `${baseUrl}${API_VERSION}`;
};

export const API_BASE_PATH = getApiBasePath();

/**
 * Request timeout in milliseconds
 * Matches API Gateway HTTP API timeout (30s max)
 */
export const REQUEST_TIMEOUT = 30000; // 30s

/**
 * Polling interval for async job status checks
 */
export const POLL_INTERVAL = 5000; // 5s

/**
 * Maximum number of poll attempts for async jobs
 * Total time: POLL_INTERVAL * MAX_POLL_ATTEMPTS = 5s * 60 = 5 minutes
 */
export const MAX_POLL_ATTEMPTS = 60;
