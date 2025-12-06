/**
 * API Client Configuration
 *
 * Configuration constants for the API client layer.
 */

/**
 * Base URL for API requests
 * Loaded from environment variable via Vite
 */
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '';

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

/**
 * API version prefix
 */
export const API_VERSION = '/api/v1';

/**
 * Full API base path (URL + version)
 */
export const API_BASE_PATH = `${API_BASE_URL}${API_VERSION}`;
