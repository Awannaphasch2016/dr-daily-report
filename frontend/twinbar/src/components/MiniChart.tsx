/**
 * MiniChart Component - Enhanced with Dual Y-Axis and Future Projections
 *
 * Displays portfolio performance with:
 * - Historical returns (solid line)
 * - 7-day projections (dashed lines)
 * - Confidence bands (best/worst case shaded area)
 * - Zero baseline (break-even reference)
 * - Dual Y-axis: Return % (left) + Portfolio NAV $ (right)
 *
 * Visual Design:
 * - Historical: Solid stance-based color
 * - Projections: Dashed lines with lower opacity
 * - Best case: Green (#10b981)
 * - Worst case: Red (#ef4444)
 * - Zero baseline: Gray dotted line
 */

import { useMemo } from 'react';
import {
  ComposedChart,
  Line,
  Area,
  ReferenceLine,
  XAxis,
  YAxis,
  ResponsiveContainer,
  Tooltip,
} from 'recharts';
import type { PriceDataPoint, ProjectionBand } from '../types/report';

interface MiniChartProps {
  data: PriceDataPoint[]; // Historical data with return_pct and portfolio_nav
  projections?: ProjectionBand[]; // 7-day future projections
  initialInvestment: number; // For NAV calculation (e.g., 1000)
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
 * Merge historical data and projections into single dataset for Recharts
 */
function mergeDataForChart(
  historical: PriceDataPoint[],
  projections: ProjectionBand[]
): any[] {
  const chartData: any[] = [];

  // Add historical data points
  historical.forEach((point) => {
    chartData.push({
      date: point.date,
      return_pct: point.return_pct ?? 0,
      portfolio_nav: point.portfolio_nav ?? 0,
      is_projection: false,
    });
  });

  // Add projection data points
  projections.forEach((proj) => {
    chartData.push({
      date: proj.date,
      expected_return: proj.expected_return,
      best_case_return: proj.best_case_return,
      worst_case_return: proj.worst_case_return,
      expected_nav: proj.expected_nav,
      best_case_nav: proj.best_case_nav,
      worst_case_nav: proj.worst_case_nav,
      is_projection: true,
    });
  });

  return chartData;
}

export function MiniChart({
  data,
  projections = [],
  initialInvestment,
  stance,
}: MiniChartProps) {
  const chartColor = useMemo(() => getChartColor(stance), [stance]);
  const chartData = useMemo(
    () => mergeDataForChart(data, projections),
    [data, projections]
  );

  // Calculate Y-axis domains
  const allReturns = [
    ...data.map((d) => d.return_pct ?? 0),
    ...projections.flatMap((p) => [p.best_case_return, p.worst_case_return]),
  ];
  const allNavs = [
    ...data.map((d) => d.portfolio_nav ?? initialInvestment),
    ...projections.flatMap((p) => [p.best_case_nav, p.worst_case_nav]),
  ];

  const minReturn = Math.min(...allReturns);
  const maxReturn = Math.max(...allReturns);
  const minNav = Math.min(...allNavs);
  const maxNav = Math.max(...allNavs);

  // Add 5% padding to domains
  const returnPadding = Math.max((maxReturn - minReturn) * 0.05, 1);
  const navPadding = Math.max((maxNav - minNav) * 0.05, 10);

  const returnDomain = [minReturn - returnPadding, maxReturn + returnPadding];
  const navDomain = [minNav - navPadding, maxNav + navPadding];

  return (
    <div
      data-testid="mini-chart"
      className="mini-chart w-full h-24 mb-3"
      aria-label="Portfolio performance chart with projections"
    >
      <ResponsiveContainer width="100%" height="100%">
        <ComposedChart data={chartData} margin={{ top: 4, right: 10, left: 0, bottom: 2 }}>
          {/* Left Y-axis: Return % */}
          <YAxis
            yAxisId="left"
            domain={returnDomain}
            tick={{ fill: 'var(--color-text-secondary)', fontSize: 9 }}
            tickFormatter={(value) => `${value > 0 ? '+' : ''}${value.toFixed(0)}%`}
            width={35}
          />

          {/* Right Y-axis: Portfolio NAV $ */}
          <YAxis
            yAxisId="right"
            orientation="right"
            domain={navDomain}
            tick={{ fill: 'var(--color-text-secondary)', fontSize: 9 }}
            tickFormatter={(value) => `$${value.toFixed(0)}`}
            width={35}
          />

          {/* X-axis: Dates (hidden for compact view) */}
          <XAxis dataKey="date" hide />

          {/* Tooltip for hover information */}
          <Tooltip
            contentStyle={{
              backgroundColor: 'var(--color-bg-secondary)',
              border: '1px solid var(--color-border)',
              borderRadius: '6px',
              fontSize: '11px',
            }}
            formatter={(value: any, name: string) => {
              if (name.includes('return')) return [`${Number(value).toFixed(2)}%`, name];
              if (name.includes('nav')) return [`$${Number(value).toFixed(2)}`, name];
              return [value, name];
            }}
            labelFormatter={(label) => `Date: ${label}`}
          />

          {/* Zero baseline reference line */}
          <ReferenceLine
            yAxisId="left"
            y={0}
            stroke="#6b7280"
            strokeDasharray="2 2"
            strokeWidth={1}
            opacity={0.5}
            label={{ value: 'Break-even', fill: '#6b7280', fontSize: 9, position: 'insideTopRight' }}
          />

          {/* Confidence band area (best case to worst case) */}
          {projections.length > 0 && (
            <Area
              yAxisId="left"
              dataKey="best_case_return"
              fill="#9ca3af"
              fillOpacity={0.2}
              stroke="none"
              isAnimationActive={false}
            />
          )}

          {/* Historical return line (solid) */}
          <Line
            yAxisId="left"
            type="monotone"
            dataKey="return_pct"
            stroke={chartColor}
            strokeWidth={2}
            dot={false}
            isAnimationActive={false}
            connectNulls={false}
          />

          {/* Projected expected return (dashed) */}
          {projections.length > 0 && (
            <Line
              yAxisId="left"
              type="monotone"
              dataKey="expected_return"
              stroke={chartColor}
              strokeWidth={2}
              strokeDasharray="5 5"
              dot={false}
              isAnimationActive={false}
              opacity={0.8}
              connectNulls={false}
            />
          )}

          {/* Best case scenario (green dashed) */}
          {projections.length > 0 && (
            <Line
              yAxisId="left"
              type="monotone"
              dataKey="best_case_return"
              stroke="#10b981"
              strokeWidth={1.5}
              strokeDasharray="5 5"
              dot={false}
              isAnimationActive={false}
              opacity={0.6}
              connectNulls={false}
            />
          )}

          {/* Worst case scenario (red dashed) */}
          {projections.length > 0 && (
            <Line
              yAxisId="left"
              type="monotone"
              dataKey="worst_case_return"
              stroke="#ef4444"
              strokeWidth={1.5}
              strokeDasharray="5 5"
              dot={false}
              isAnimationActive={false}
              opacity={0.6}
              connectNulls={false}
            />
          )}
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}
