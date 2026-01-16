/**
 * API Client Configuration
 *
 * Configuration constants for the API client layer.
 *
 * Two API endpoints:
 * 1. API_BASE_PATH - Dynamic API (Lambda + Aurora) for real-time data
 * 2. STATIC_API_BASE_PATH - Static API (CloudFront CDN) for precomputed data
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

/**
 * Get static API base path for precomputed data
 *
 * Static API serves precomputed JSON from CloudFront CDN for faster performance.
 * Falls back to dynamic API if STATIC_API_URL not configured.
 *
 * Priority:
 * 1. Runtime injection via window.STATIC_API_URL (CI/CD workflow)
 * 2. Build-time VITE_STATIC_API_URL from .env files
 * 3. Falls back to dynamic API_BASE_PATH
 */
const getStaticApiBasePath = (): string => {
  // Runtime injection from CI/CD workflow
  if (typeof window !== 'undefined' && (window as any).STATIC_API_URL) {
    return (window as any).STATIC_API_URL;
  }
  // Build-time environment variable
  const staticUrl = import.meta.env.VITE_STATIC_API_URL;
  if (staticUrl) {
    return staticUrl;
  }
  // Fallback to dynamic API (no CDN benefit but works)
  return getApiBasePath();
};

export const API_BASE_PATH = getApiBasePath();

/**
 * Static API base path for precomputed data (served from CloudFront CDN)
 *
 * Use this for:
 * - Rankings data (/rankings.json)
 * - Individual reports (/reports/{ticker}.json)
 * - Pattern data (/patterns/{ticker}.json)
 *
 * Benefits:
 * - TTFB < 50ms (vs ~500ms for Lambda)
 * - No Aurora load
 * - Global edge caching
 */
export const STATIC_API_BASE_PATH = getStaticApiBasePath();

/**
 * Check if static API is available (not falling back to dynamic API)
 */
export const isStaticApiEnabled = (): boolean => {
  return STATIC_API_BASE_PATH !== API_BASE_PATH;
};

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
