/**
 * MiniChart Component
 *
 * Displays a compact price trend line chart in market cards.
 * Uses Recharts LineChart with simplified styling.
 *
 * Color coding:
 * - Bullish: Green (#10b981)
 * - Bearish: Red (#ef4444)
 * - Neutral: Gray (#6b7280)
 */

import { useMemo } from 'react';
import { LineChart, Line, ResponsiveContainer, YAxis } from 'recharts';
import type { PriceDataPoint } from '../types/report';

interface MiniChartProps {
  data: PriceDataPoint[];
  stance: 'bullish' | 'bearish' | 'neutral';
}

/**
 * Get chart color based on stance
 */
function getChartColor(stance: 'bullish' | 'bearish' | 'neutral'): string {
  switch (stance) {
    case 'bullish':
      return '#10b981'; // green
    case 'bearish':
      return '#ef4444'; // red
    case 'neutral':
      return '#6b7280'; // gray
  }
}

/**
 * Format price data for Recharts (only need date and close price)
 */
function formatChartData(data: PriceDataPoint[]) {
  return data.map((point) => ({
    date: point.date,
    price: point.close,
  }));
}

export function MiniChart({ data, stance }: MiniChartProps) {
  const chartData = useMemo(() => formatChartData(data), [data]);
  const chartColor = useMemo(() => getChartColor(stance), [stance]);

  // Calculate min/max for Y axis domain (add 2% padding)
  const prices = chartData.map((d) => d.price);
  const minPrice = Math.min(...prices);
  const maxPrice = Math.max(...prices);
  const padding = (maxPrice - minPrice) * 0.02;
  const yDomain = [minPrice - padding, maxPrice + padding];

  return (
    <div
      data-testid="mini-chart"
      className="mini-chart w-full h-16 mb-3"
      aria-label={`Price trend chart showing ${stance} stance`}
    >
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={chartData} margin={{ top: 2, right: 5, left: 5, bottom: 2 }}>
          {/* Hidden Y axis for domain calculation */}
          <YAxis domain={yDomain} hide />

          {/* Trend line */}
          <Line
            type="monotone"
            dataKey="price"
            stroke={chartColor}
            strokeWidth={2}
            dot={false}
            isAnimationActive={false}
            className="recharts-line-curve"
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
