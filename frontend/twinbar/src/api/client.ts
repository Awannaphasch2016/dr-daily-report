/**
 * API Client for TwinBar Frontend
 *
 * Singleton API client that handles:
 * - Telegram WebApp authentication (initData injection)
 * - Request timeout handling (30s - matches API Gateway limit)
 * - Async report polling pattern (POST → poll status → result)
 * - Error handling and type-safe responses
 *
 * Pattern: Singleton exported instance
 *   - `apiClient.setInitData(initData)` called once during app initialization
 *   - All subsequent requests auto-inject `X-Telegram-Init-Data` header
 */

import {
  API_BASE_PATH,
  STATIC_API_BASE_PATH,
  isStaticApiEnabled,
  REQUEST_TIMEOUT,
  POLL_INTERVAL,
  MAX_POLL_ATTEMPTS,
} from './config';
import type {
  SearchResponse,
  RankingsResponse,
  ReportResponse,
  JobSubmitResponse,
  JobStatusResponse,
  WatchlistResponse,
  WatchlistAddRequest,
  WatchlistOperationResponse,
  ErrorEnvelope,
} from './types';
import { APIError } from './types';

/**
 * HTTP Method types
 */
type HttpMethod = 'GET' | 'POST' | 'PUT' | 'DELETE';

/**
 * Request options
 */
interface RequestOptions {
  method?: HttpMethod;
  body?: Record<string, any>;
  headers?: Record<string, string>;
  timeout?: number;
}

/**
 * API Client Class
 *
 * Handles all HTTP communication with the backend FastAPI server.
 * Implements Telegram WebApp authentication and async job polling.
 */
class APIClient {
  private initData: string | null = null;
  private devUserId: string | null = null;

  /**
   * Set Telegram WebApp initData for authentication
   *
   * Should be called once during app initialization with value from
   * `window.Telegram.WebApp.initData`
   *
   * @param initData - Telegram WebApp initData string
   */
  setInitData(initData: string): void {
    this.initData = initData;
    console.log('✅ API Client: Telegram initData configured');
  }

  /**
   * Set development user ID for local testing
   *
   * When running locally without Telegram, use this to set a fake user ID
   * that will be sent in the `X-Telegram-User-Id` header.
   *
   * @param userId - User ID for development testing
   */
  setDevUserId(userId: string): void {
    this.devUserId = userId;
    console.log(`🔧 API Client: Dev user ID set to ${userId}`);
  }

  /**
   * Make HTTP request with timeout and error handling
   */
  private async request<T>(
    endpoint: string,
    options: RequestOptions = {}
  ): Promise<T> {
    const { method = 'GET', body, headers = {}, timeout = REQUEST_TIMEOUT } = options;

    // Build request URL
    const url = `${API_BASE_PATH}${endpoint}`;

    // Inject authentication headers
    if (this.initData) {
      // Production: Use Telegram initData for HMAC-SHA256 validation
      headers['X-Telegram-Init-Data'] = this.initData;
    } else if (this.devUserId) {
      // Development: Use simple user ID header
      headers['X-Telegram-User-Id'] = this.devUserId;
    }

    // Set content type for JSON bodies
    if (body) {
      headers['Content-Type'] = 'application/json';
    }

    // Create AbortController for timeout
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeout);

    try {
      const response = await fetch(url, {
        method,
        headers,
        body: body ? JSON.stringify(body) : undefined,
        signal: controller.signal,
      });

      clearTimeout(timeoutId);

      // Handle error responses
      if (!response.ok) {
        const errorData: ErrorEnvelope = await response.json();
        throw new APIError(
          errorData.error.code,
          errorData.error.message,
          response.status,
          errorData.error.details
        );
      }

      // Parse and return success response
      return await response.json();
    } catch (error) {
      clearTimeout(timeoutId);

      // Handle timeout
      if (error instanceof DOMException && error.name === 'AbortError') {
        throw new APIError(
          'REQUEST_TIMEOUT',
          `Request timed out after ${timeout}ms`,
          408
        );
      }

      // Handle network errors
      if (error instanceof TypeError) {
        throw new APIError(
          'NETWORK_ERROR',
          'Network error - check your connection',
          0
        );
      }

      // Re-throw APIError as-is
      if (error instanceof APIError) {
        throw error;
      }

      // Wrap unknown errors
      throw new APIError(
        'UNKNOWN_ERROR',
        error instanceof Error ? error.message : 'Unknown error occurred',
        500
      );
    }
  }

  // ============================================================================
  // Search API
  // ============================================================================

  /**
   * Search for tickers
   *
   * @param query - Search query (ticker symbol or company name)
   * @returns List of matching tickers
   *
   * @example
   * const results = await apiClient.search('NVDA');
   * // Returns: { results: [{ ticker: 'NVDA19', company_name: 'NVIDIA Corp', ... }] }
   */
  async search(query: string): Promise<SearchResponse> {
    return this.request<SearchResponse>(`/search?q=${encodeURIComponent(query)}`);
  }

  // ============================================================================
  // Rankings API
  // ============================================================================

  /**
   * Get market rankings by category
   *
   * Uses Static API (CloudFront CDN) for <50ms response time.
   * Falls back to dynamic API (Lambda) if Static API unavailable.
   *
   * @param category - Ranking category (top_gainers, top_losers, volume_surge, trending)
   * @returns List of ranked tickers
   *
   * @example
   * const rankings = await apiClient.getRankings('top_gainers');
   * // Returns: { category: 'top_gainers', tickers: [...] }
   */
  async getRankings(
    category: 'top_gainers' | 'top_losers' | 'volume_surge' | 'trending' = 'top_gainers'
  ): Promise<RankingsResponse> {
    // Try Static API first (CloudFront CDN, <50ms response)
    if (isStaticApiEnabled()) {
      try {
        const staticUrl = `${STATIC_API_BASE_PATH}/api/v1/rankings.json`;
        const response = await fetch(staticUrl);

        if (response.ok) {
          const data = await response.json();
          const cacheStatus = response.headers.get('x-cache') || 'unknown';
          console.log(`Rankings from Static API (cache: ${cacheStatus})`);

          // Transform static API response to RankingsResponse format
          return {
            category,
            as_of: data.generated_at,
            tickers: data.rankings[category] || [],
          };
        }
      } catch (error) {
        console.warn('Static API failed, falling back to dynamic:', error);
      }
    }

    // Fallback to dynamic API (Lambda + yfinance, 2-5s response)
    return this.request<RankingsResponse>(`/rankings?category=${category}`);
  }

  // ============================================================================
  // Report API (Async Pattern)
  // ============================================================================

  /**
   * Get cached report (fast, for modal display)
   *
   * Fetches report from Aurora cache. Returns immediately with cached data.
   * Use this for modal display where you want instant results.
   *
   * @param ticker - Ticker symbol
   * @returns Cached report response
   *
   * @example
   * const report = await apiClient.getCachedReport('NVDA19');
   */
  async getCachedReport(ticker: string): Promise<ReportResponse> {
    return this.request<ReportResponse>(`/report/${ticker}`, {
      method: 'GET',
    });
  }

  /**
   * Submit async report generation job
   *
   * **IMPORTANT:** Use this instead of sync GET /report/{ticker}
   * Sync endpoint will timeout (report takes ~50-60s, API Gateway limit is 30s)
   *
   * @param ticker - Ticker symbol to analyze
   * @returns Job submission response with job_id
   *
   * @example
   * const { job_id, status } = await apiClient.submitReport('NVDA19');
   * if (status === 'completed') {
   *   // Cache hit - result available immediately
   *   const report = await apiClient.getJobStatus(job_id);
   * } else {
   *   // New job - poll for completion
   *   const report = await apiClient.pollJobUntilComplete(job_id);
   * }
   */
  async submitReport(ticker: string): Promise<JobSubmitResponse> {
    return this.request<JobSubmitResponse>(`/report/${ticker}`, {
      method: 'POST',
    });
  }

  /**
   * Get job status
   *
   * @param jobId - Job ID from submitReport()
   * @returns Job status response
   */
  async getJobStatus(jobId: string): Promise<JobStatusResponse> {
    return this.request<JobStatusResponse>(`/report/status/${jobId}`);
  }

  /**
   * Poll job until completed or failed
   *
   * Polls every POLL_INTERVAL (5s) for max MAX_POLL_ATTEMPTS (60 = 5 min)
   *
   * @param jobId - Job ID to poll
   * @returns Report response when job completes
   * @throws APIError if job fails or timeout
   *
   * @example
   * try {
   *   const report = await apiClient.pollJobUntilComplete('rpt_abc123');
   *   console.log(report.ticker, report.stance);
   * } catch (error) {
   *   if (error.code === 'JOB_TIMEOUT') {
   *     console.error('Report generation timed out after 5 minutes');
   *   }
   * }
   */
  async pollJobUntilComplete(jobId: string): Promise<ReportResponse> {
    let attempts = 0;

    while (attempts < MAX_POLL_ATTEMPTS) {
      const status = await this.getJobStatus(jobId);

      if (status.status === 'completed') {
        if (!status.result) {
          throw new APIError(
            'INVALID_RESPONSE',
            'Job completed but result is missing',
            500
          );
        }
        return status.result as ReportResponse;
      }

      if (status.status === 'failed') {
        throw new APIError(
          'JOB_FAILED',
          status.error || 'Report generation failed',
          500
        );
      }

      // Wait before next poll
      await new Promise((resolve) => setTimeout(resolve, POLL_INTERVAL));
      attempts++;
    }

    // Timeout after max attempts
    throw new APIError(
      'JOB_TIMEOUT',
      `Job did not complete after ${MAX_POLL_ATTEMPTS * POLL_INTERVAL / 1000}s`,
      408
    );
  }

  /**
   * Generate report (convenience method)
   *
   * Combines submitReport() + pollJobUntilComplete() into single call.
   * Use this for simple cases where you just want the final report.
   *
   * @param ticker - Ticker symbol
   * @returns Complete report
   *
   * @example
   * const report = await apiClient.generateReport('NVDA19');
   */
  async generateReport(ticker: string): Promise<ReportResponse> {
    const { job_id, status } = await this.submitReport(ticker);

    // Cache hit - get result immediately
    if (status === 'completed') {
      const result = await this.getJobStatus(job_id);
      if (!result.result) {
        throw new APIError(
          'INVALID_RESPONSE',
          'Cache hit but result is missing',
          500
        );
      }
      return result.result as ReportResponse;
    }

    // New job - poll until complete
    return this.pollJobUntilComplete(job_id);
  }

  // ============================================================================
  // Watchlist API (Requires Authentication)
  // ============================================================================

  /**
   * Get user's watchlist
   *
   * Requires Telegram authentication (initData or dev user ID)
   *
   * @returns List of watchlist items
   */
  async getWatchlist(): Promise<WatchlistResponse> {
    return this.request<WatchlistResponse>('/watchlist');
  }

  /**
   * Add ticker to watchlist
   *
   * @param ticker - Ticker symbol to add
   * @returns Operation response
   */
  async addToWatchlist(ticker: string): Promise<WatchlistOperationResponse> {
    const body: WatchlistAddRequest = { ticker };
    return this.request<WatchlistOperationResponse>('/watchlist', {
      method: 'POST',
      body,
    });
  }

  /**
   * Remove ticker from watchlist
   *
   * @param ticker - Ticker symbol to remove
   * @returns Operation response
   */
  async removeFromWatchlist(ticker: string): Promise<WatchlistOperationResponse> {
    return this.request<WatchlistOperationResponse>(`/watchlist/${ticker}`, {
      method: 'DELETE',
    });
  }
}

/**
 * Singleton API client instance
 *
 * Import and use this instance throughout the application:
 *
 * ```typescript
 * import { apiClient } from './api/client';
 *
 * // In App.tsx:
 * apiClient.setInitData(window.Telegram.WebApp.initData);
 *
 * // Anywhere else:
 * const markets = await apiClient.getRankings('top_gainers');
 * ```
 */
export const apiClient = new APIClient();

/**
 * Export APIError class for error handling
 */
export { APIError } from './types';
