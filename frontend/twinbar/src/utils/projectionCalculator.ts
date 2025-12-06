/**
 * Statistical projection calculator for portfolio return forecasting
 *
 * Calculates 7-day future projections with confidence bands based on:
 * - Linear regression trend line
 * - Standard deviation for volatility
 * - Widening confidence intervals (fan out over time)
 */

import type { PriceDataPoint, ProjectionBand } from '../types/report';

/**
 * Calculate historical returns from price data
 * Returns cumulative return % from entry point for each day
 */
function calculateHistoricalReturns(data: PriceDataPoint[]): number[] {
  if (data.length === 0) return [];

  const returns: number[] = [];
  const entryPrice = data[0].close;

  for (const point of data) {
    // Calculate return % from entry point
    const returnPct = ((point.close - entryPrice) / entryPrice) * 100;
    returns.push(returnPct);
  }

  return returns;
}

/**
 * Calculate simple linear regression trend
 * Returns slope and intercept for y = mx + b
 */
function calculateLinearTrend(returns: number[]): {
  slope: number;
  intercept: number;
  predict: (x: number) => number;
} {
  const n = returns.length;
  if (n === 0) return { slope: 0, intercept: 0, predict: () => 0 };

  // Calculate means
  const xMean = (n - 1) / 2; // x values are 0, 1, 2, ..., n-1
  const yMean = returns.reduce((sum, y) => sum + y, 0) / n;

  // Calculate slope (m)
  let numerator = 0;
  let denominator = 0;
  for (let i = 0; i < n; i++) {
    const xDiff = i - xMean;
    const yDiff = returns[i] - yMean;
    numerator += xDiff * yDiff;
    denominator += xDiff * xDiff;
  }

  const slope = denominator !== 0 ? numerator / denominator : 0;
  const intercept = yMean - slope * xMean;

  return {
    slope,
    intercept,
    predict: (x: number) => slope * x + intercept,
  };
}

/**
 * Calculate standard deviation of returns (volatility measure)
 */
function calculateStandardDeviation(returns: number[]): number {
  if (returns.length === 0) return 0;

  const mean = returns.reduce((sum, val) => sum + val, 0) / returns.length;
  const squaredDiffs = returns.map((val) => Math.pow(val - mean, 2));
  const variance = squaredDiffs.reduce((sum, val) => sum + val, 0) / returns.length;

  return Math.sqrt(variance);
}

/**
 * Add days to a date
 */
function addDays(date: Date, days: number): Date {
  const result = new Date(date);
  result.setDate(result.getDate() + days);
  return result;
}

/**
 * Calculate 7-day future projections with statistical confidence bands
 *
 * @param historicalData - Historical price data points
 * @param initialInvestment - Starting portfolio value in dollars (e.g., 1000)
 * @param daysAhead - Number of days to project (default: 7)
 * @returns Array of projection bands with best/expected/worst case scenarios
 *
 * @example
 * ```typescript
 * const projections = calculateProjections(priceHistory, 1000, 7);
 * // Returns 7 projection bands, one for each future day
 * // projections[0] = tomorrow's projection
 * // projections[6] = 7 days from now projection
 * ```
 */
export function calculateProjections(
  historicalData: PriceDataPoint[],
  initialInvestment: number,
  daysAhead: number = 7
): ProjectionBand[] {
  if (historicalData.length === 0) {
    console.warn('calculateProjections: No historical data provided');
    return [];
  }

  // 1. Calculate historical returns from entry point
  const returns = calculateHistoricalReturns(historicalData);

  // 2. Calculate trend using linear regression
  const trend = calculateLinearTrend(returns);

  // 3. Calculate volatility (standard deviation of returns)
  const stdDev = calculateStandardDeviation(returns);

  // 4. Project future values with widening confidence bands
  const projections: ProjectionBand[] = [];
  const lastIndex = returns.length - 1;

  for (let day = 1; day <= daysAhead; day++) {
    const futureIndex = lastIndex + day;
    const futureDate = addDays(new Date(), day);

    // Expected return from trend line
    const expectedReturn = trend.predict(futureIndex);

    // Gradually widen confidence bands (fan out over time)
    // Day 1: 14% of std dev, Day 7: 100% of std dev
    const widening = day / daysAhead;

    // Best case: expected + std dev (widening)
    const bestCaseReturn = expectedReturn + (stdDev * widening);

    // Worst case: expected - std dev (widening)
    const worstCaseReturn = expectedReturn - (stdDev * widening);

    // Convert return % to portfolio NAV
    const expectedNav = initialInvestment * (1 + expectedReturn / 100);
    const bestCaseNav = initialInvestment * (1 + bestCaseReturn / 100);
    const worstCaseNav = initialInvestment * (1 + worstCaseReturn / 100);

    projections.push({
      date: futureDate.toISOString().split('T')[0],
      expected_return: Number(expectedReturn.toFixed(2)),
      best_case_return: Number(bestCaseReturn.toFixed(2)),
      worst_case_return: Number(worstCaseReturn.toFixed(2)),
      expected_nav: Number(expectedNav.toFixed(2)),
      best_case_nav: Number(bestCaseNav.toFixed(2)),
      worst_case_nav: Number(worstCaseNav.toFixed(2)),
    });
  }

  return projections;
}

/**
 * Enhance historical price data with portfolio metrics
 * Adds return_pct and portfolio_nav to each data point
 *
 * @param data - Historical price data
 * @param initialInvestment - Starting portfolio value
 * @returns Enhanced price data with portfolio metrics
 */
export function enhanceHistoricalData(
  data: PriceDataPoint[],
  initialInvestment: number
): PriceDataPoint[] {
  if (data.length === 0) return [];

  const entryPrice = data[0].close;

  return data.map((point) => {
    const returnPct = ((point.close - entryPrice) / entryPrice) * 100;
    const portfolioNav = initialInvestment * (1 + returnPct / 100);

    return {
      ...point,
      return_pct: Number(returnPct.toFixed(2)),
      portfolio_nav: Number(portfolioNav.toFixed(2)),
      is_projection: false,
    };
  });
}
