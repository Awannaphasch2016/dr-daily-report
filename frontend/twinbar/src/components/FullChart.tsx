/**
 * FullChart Component
 *
 * Displays a comprehensive candlestick chart with technical indicators
 * and chart pattern overlays.
 *
 * Features:
 * - Candlestick OHLC visualization
 * - SMA indicator lines
 * - Chart pattern overlays (flags, triangles, wedges, double top/bottom, etc.)
 * - Responsive design
 */

import { useMemo } from 'react';
import {
  ComposedChart,
  Bar,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceArea,
} from 'recharts';
import type { PriceDataPoint, ChartPattern } from '../types/report';

interface FullChartProps {
  data: PriceDataPoint[];
  chartPatterns?: ChartPattern[];
  indicators?: {
    sma20?: boolean;
    sma50?: boolean;
  };
}

/**
 * Get color for pattern based on sentiment
 */
function getPatternColor(type: string): { fill: string; stroke: string } {
  const bullishPatterns = [
    'bullish_flag', 'bullish_vcp', 'reverse_head_shoulders',
    'double_bottom', 'falling_wedge', 'ascending_triangle'
  ];
  const bearishPatterns = [
    'bearish_flag', 'bearish_vcp', 'head_shoulders',
    'double_top', 'rising_wedge', 'descending_triangle'
  ];

  if (bullishPatterns.some(p => type.toLowerCase().includes(p.replace('_', '')))) {
    return { fill: 'rgba(34, 197, 94, 0.15)', stroke: '#22c55e' }; // Green
  }
  if (bearishPatterns.some(p => type.toLowerCase().includes(p.replace('_', '')))) {
    return { fill: 'rgba(239, 68, 68, 0.15)', stroke: '#ef4444' }; // Red
  }
  return { fill: 'rgba(59, 130, 246, 0.15)', stroke: '#3b82f6' }; // Blue (neutral)
}

/**
 * Parse bar index from start/end string
 * Handles formats: "12", "bar_12"
 */
function parseBarIndex(value?: string): number | null {
  if (!value) return null;
  const match = value.match(/^(?:bar_)?(\d+)$/);
  return match ? parseInt(match[1], 10) : null;
}

/**
 * Format chart data for Recharts
 * Adds candlestick body/wick calculations
 */
function formatCandlestickData(data: PriceDataPoint[]) {
  return data.map((point) => {
    const isGreen = point.close >= point.open;
    return {
      date: point.date,
      open: point.open,
      high: point.high,
      low: point.low,
      close: point.close,
      volume: point.volume,
      // Candlestick visual properties
      candleTop: Math.max(point.open, point.close),
      candleBottom: Math.min(point.open, point.close),
      candleHeight: Math.abs(point.close - point.open),
      wickHigh: point.high,
      wickLow: point.low,
      isGreen,
    };
  });
}

/**
 * Calculate Simple Moving Average
 */
function calculateSMA(data: PriceDataPoint[], period: number): number[] {
  const sma: number[] = [];
  for (let i = 0; i < data.length; i++) {
    if (i < period - 1) {
      sma.push(NaN); // Not enough data
    } else {
      const slice = data.slice(i - period + 1, i + 1);
      const avg = slice.reduce((sum, point) => sum + point.close, 0) / period;
      sma.push(Number(avg.toFixed(2)));
    }
  }
  return sma;
}


export function FullChart({
  data,
  chartPatterns = [],
  indicators = { sma20: true, sma50: true }
}: FullChartProps) {
  // ALWAYS render component - show empty state if no data
  // Principle: Observability > conditional rendering (CLAUDE.md:342-346)
  const isEmpty = !data || data.length === 0;

  if (isEmpty) {
    return (
      <div
        data-testid="full-chart"
        className="full-chart full-chart--empty w-full h-96 flex items-center justify-center border border-dashed border-[var(--color-border)] rounded-lg"
        aria-label="Price chart (no data)"
      >
        <div className="empty-state text-center text-[var(--color-text-secondary)]">
          <div className="empty-state__icon text-4xl mb-2">📈</div>
          <div className="empty-state__text text-sm">No price data available</div>
          <div className="text-xs mt-1 opacity-70">Chart will appear when data is loaded</div>
        </div>
      </div>
    );
  }

  // Format data and calculate indicators
  const chartData = useMemo(() => {
    const formatted = formatCandlestickData(data);

    // Calculate SMAs if enabled
    if (indicators.sma20) {
      const sma20 = calculateSMA(data, 20);
      formatted.forEach((point, i) => {
        (point as any).sma20 = sma20[i];
      });
    }

    if (indicators.sma50) {
      const sma50 = calculateSMA(data, 50);
      formatted.forEach((point, i) => {
        (point as any).sma50 = sma50[i];
      });
    }

    return formatted;
  }, [data, indicators]);

  // Calculate Y-axis domain
  const prices = data.flatMap((d) => [d.low, d.high]);
  const minPrice = Math.min(...prices);
  const maxPrice = Math.max(...prices);
  const padding = (maxPrice - minPrice) * 0.05;
  const yDomain = [minPrice - padding, maxPrice + padding];

  // Process chart patterns for overlay rendering
  const patternOverlays = useMemo(() => {
    if (!chartPatterns || chartPatterns.length === 0) return [];

    return chartPatterns.map((pattern, idx) => {
      const startIdx = parseBarIndex(pattern.start);
      const endIdx = parseBarIndex(pattern.end);

      // Skip patterns without valid indices
      if (startIdx === null || endIdx === null) return null;
      if (startIdx >= data.length || endIdx >= data.length) return null;

      const colors = getPatternColor(pattern.type);
      const startDate = data[startIdx]?.date;
      const endDate = data[endIdx]?.date;

      if (!startDate || !endDate) return null;

      // Get price range for the pattern area
      const patternData = data.slice(
        Math.min(startIdx, endIdx),
        Math.max(startIdx, endIdx) + 1
      );
      const patternHigh = Math.max(...patternData.map(d => d.high));
      const patternLow = Math.min(...patternData.map(d => d.low));

      // Extract key points from pattern data
      const points = pattern.points || {};

      return {
        key: `pattern-${idx}`,
        type: pattern.type,
        startDate,
        endDate,
        startIdx,
        endIdx,
        patternHigh,
        patternLow,
        colors,
        points,
        confidence: pattern.confidence,
      };
    }).filter(Boolean);
  }, [chartPatterns, data]);

  return (
    <div data-testid="full-chart" className="full-chart w-full h-96">
      {/* Indicator & Pattern Legend */}
      <div data-testid="chart-indicators" className="flex flex-wrap gap-4 mb-2 text-xs">
        <span className="text-gray-600 dark:text-gray-400">Indicators:</span>
        {indicators.sma20 && (
          <span className="flex items-center gap-1">
            <div className="w-3 h-0.5 bg-blue-500" />
            <span>SMA 20</span>
          </span>
        )}
        {indicators.sma50 && (
          <span className="flex items-center gap-1">
            <div className="w-3 h-0.5 bg-purple-500" />
            <span>SMA 50</span>
          </span>
        )}
        {patternOverlays.length > 0 && (
          <>
            <span className="text-gray-600 dark:text-gray-400 ml-2">Patterns:</span>
            {patternOverlays.slice(0, 3).map((overlay: any) => (
              <span key={overlay.key} className="flex items-center gap-1">
                <div
                  className="w-3 h-3 rounded-sm border"
                  style={{
                    backgroundColor: overlay.colors.fill,
                    borderColor: overlay.colors.stroke
                  }}
                />
                <span className="capitalize">
                  {overlay.type.replace(/_/g, ' ').replace('bullish ', '').replace('bearish ', '')}
                </span>
              </span>
            ))}
            {patternOverlays.length > 3 && (
              <span className="text-gray-500">+{patternOverlays.length - 3} more</span>
            )}
          </>
        )}
      </div>

      <ResponsiveContainer width="100%" height="100%">
        <ComposedChart data={chartData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#374151" opacity={0.3} />

          <XAxis
            dataKey="date"
            tick={{ fill: 'var(--color-text-secondary)', fontSize: 11 }}
            tickFormatter={(value) => {
              const date = new Date(value);
              return `${date.getMonth() + 1}/${date.getDate()}`;
            }}
          />

          <YAxis
            domain={yDomain}
            tick={{ fill: 'var(--color-text-secondary)', fontSize: 11 }}
            tickFormatter={(value) => `$${value.toFixed(0)}`}
          />

          <Tooltip
            contentStyle={{
              backgroundColor: 'var(--color-bg-secondary)',
              border: '1px solid var(--color-border)',
              borderRadius: '8px',
              fontSize: '12px',
            }}
            formatter={(value: any, name: string) => {
              if (name === 'volume') return [Number(value).toLocaleString(), 'Volume'];
              if (name === 'sma20') return [`$${Number(value).toFixed(2)}`, 'SMA 20'];
              if (name === 'sma50') return [`$${Number(value).toFixed(2)}`, 'SMA 50'];
              return [`$${Number(value).toFixed(2)}`, name];
            }}
            labelFormatter={(label) => `Date: ${label}`}
          />

          {/* Chart Pattern Overlays - render behind candlesticks */}
          {patternOverlays.map((overlay: any) => (
            <ReferenceArea
              key={overlay.key}
              x1={overlay.startDate}
              x2={overlay.endDate}
              y1={overlay.patternLow}
              y2={overlay.patternHigh}
              fill={overlay.colors.fill}
              stroke={overlay.colors.stroke}
              strokeWidth={2}
              strokeDasharray="4 2"
              fillOpacity={0.3}
              label={{
                value: overlay.type.replace(/_/g, ' ').split(' ').map((w: string) => w[0]?.toUpperCase()).join(''),
                position: 'insideTopRight',
                fill: overlay.colors.stroke,
                fontSize: 10,
                fontWeight: 'bold',
              }}
            />
          ))}

          {/* Candlesticks - render from low to high for full range */}
          <Bar
            dataKey="high"
            shape={(props: any) => {
              const { x, width, payload } = props;
              if (!payload || width <= 0) return <g />; // Return empty group instead of null

              // We need to manually calculate Y positions using the chart's scale
              // Since we don't have direct access to yScale in Bar shape,
              // we'll use the relative positioning approach

              // Get the Y-axis domain from the chart
              const domain = yDomain;
              const priceRange = domain[1] - domain[0];

              // Estimate chart height (this is approximate)
              // The actual plot area is smaller than h-96 due to margins
              const chartHeight = 300; // Approximate plot area height in pixels

              // Calculate pixel positions for OHLC values
              const priceToPixel = (price: number) => {
                const ratio = (domain[1] - price) / priceRange;
                return ratio * chartHeight + 10; // +10 for top margin
              };

              const highY = priceToPixel(payload.high);
              const lowY = priceToPixel(payload.low);
              const openY = priceToPixel(payload.open);
              const closeY = priceToPixel(payload.close);

              const candleTop = Math.min(openY, closeY);
              const candleBottom = Math.max(openY, closeY);

              const isGreen = payload.close >= payload.open;
              const candleColor = isGreen ? '#26a69a' : '#ef5350';

              const candleWidth = Math.max(width * 0.7, 3);
              const candleX = x + (width - candleWidth) / 2;
              const wickX = x + width / 2;

              return (
                <g className="candlestick">
                  {/* Wick from high to low */}
                  <line
                    x1={wickX}
                    y1={highY}
                    x2={wickX}
                    y2={lowY}
                    stroke={candleColor}
                    strokeWidth={1}
                  />
                  {/* Body from open to close */}
                  {candleBottom - candleTop < 1 ? (
                    // Doji: horizontal line
                    <line
                      x1={x}
                      x2={x + width}
                      y1={candleTop}
                      y2={candleTop}
                      stroke={candleColor}
                      strokeWidth={1}
                    />
                  ) : (
                    <rect
                      x={candleX}
                      y={candleTop}
                      width={candleWidth}
                      height={candleBottom - candleTop}
                      fill={candleColor}
                      stroke="none"
                      className="candlestick"
                    />
                  )}
                </g>
              );
            }}
            isAnimationActive={false}
          />

          {/* SMA 20 */}
          {indicators.sma20 && (
            <Line
              type="monotone"
              dataKey="sma20"
              stroke="#3b82f6"
              strokeWidth={2}
              dot={false}
              isAnimationActive={false}
              connectNulls
            />
          )}

          {/* SMA 50 */}
          {indicators.sma50 && (
            <Line
              type="monotone"
              dataKey="sma50"
              stroke="#a855f7"
              strokeWidth={2}
              dot={false}
              isAnimationActive={false}
              connectNulls
            />
          )}
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}
