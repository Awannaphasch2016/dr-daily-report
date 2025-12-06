/**
 * FullChart Component
 *
 * Displays a comprehensive candlestick chart with technical indicators.
 * Used in modal Technical tab for detailed price analysis.
 *
 * Features:
 * - Candlestick OHLC visualization
 * - SMA indicator lines
 * - Volume bars (optional)
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
} from 'recharts';
import type { PriceDataPoint } from '../types/report';

interface FullChartProps {
  data: PriceDataPoint[];
  indicators?: {
    sma20?: boolean;
    sma50?: boolean;
  };
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

/**
 * Custom Candlestick Shape Component
 * Renders individual candlestick with wick and body
 */
const Candlestick = (props: any) => {
  const { x, y, width, height, payload } = props;

  if (!payload || width <= 0) return null;

  const isGreen = payload.isGreen;
  const fillColor = isGreen ? '#10b981' : '#ef4444'; // green or red
  const wickColor = '#6b7280'; // gray

  // Calculate positions
  const candleX = x;
  const candleY = y;
  const candleWidth = Math.max(width * 0.8, 2); // Min 2px width
  const wickX = x + width / 2;

  return (
    <g className="candlestick">
      {/* Wick (vertical line from low to high) */}
      <line
        x1={wickX}
        y1={y - (payload.wickHigh - payload.candleTop) * (height / payload.candleHeight)}
        x2={wickX}
        y2={y + height + (payload.candleBottom - payload.wickLow) * (height / payload.candleHeight)}
        stroke={wickColor}
        strokeWidth={1}
      />

      {/* Body (rectangle from open to close) */}
      <rect
        x={candleX}
        y={candleY}
        width={candleWidth}
        height={height}
        fill={fillColor}
        stroke={fillColor}
        strokeWidth={1}
        className="candlestick"
      />
    </g>
  );
};

export function FullChart({ data, indicators = { sma20: true, sma50: true } }: FullChartProps) {
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

  return (
    <div data-testid="full-chart" className="full-chart w-full h-96">
      {/* Indicator Legend */}
      <div data-testid="chart-indicators" className="flex gap-4 mb-2 text-xs">
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

          {/* Candlesticks using Bar with custom shape */}
          <Bar
            dataKey="candleBottom"
            fill="#10b981"
            shape={<Candlestick />}
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
