"use client";

import { ResponsiveContainer, Treemap } from "recharts";
import type { Portfolio, Position } from "../types";

interface PortfolioHeatmapProps {
  portfolio: Portfolio | null;
}

interface HeatmapCell {
  name: string;
  size: number;
  pnl_pct: number;
  pnl: number;
  [key: string]: string | number;
}

function colorForPnL(pct: number): string {
  // Smooth red -> neutral -> green based on pnl_pct.
  // Range clamped to +/- 10%.
  const clamped = Math.max(-10, Math.min(10, pct));
  if (clamped >= 0) {
    const t = clamped / 10;
    const r = Math.round(34 + (0 - 34) * t);
    const g = Math.round(197 + (160 - 197) * (1 - t * 0.5));
    const b = Math.round(94 + (94 - 94) * t);
    return `rgb(${r},${g},${b})`;
  } else {
    const t = -clamped / 10;
    const r = Math.round(239 - (239 - 180) * (1 - t));
    const g = Math.round(68 + (68 - 30) * t * 0);
    const b = Math.round(68);
    return `rgb(${r},${g},${b})`;
  }
}

interface TreemapNodeProps {
  x?: number;
  y?: number;
  width?: number;
  height?: number;
  name?: string;
  size?: number;
  pnl_pct?: number;
  pnl?: number;
  root?: unknown;
}

function CustomCell(props: TreemapNodeProps) {
  const { x = 0, y = 0, width = 0, height = 0, name = "", pnl_pct = 0 } = props;
  if (width < 2 || height < 2) return <g />;
  const fill = colorForPnL(pnl_pct);
  const showLabel = width > 50 && height > 30;
  const showPct = width > 60 && height > 50;
  return (
    <g>
      <rect
        x={x}
        y={y}
        width={width}
        height={height}
        style={{ fill, stroke: "#0d1117", strokeWidth: 2, opacity: 0.85 }}
      />
      {showLabel && (
        <text
          x={x + width / 2}
          y={y + height / 2 - (showPct ? 8 : 0)}
          textAnchor="middle"
          dominantBaseline="middle"
          fill="#fff"
          fontSize={Math.min(14, Math.max(10, width / 8))}
          fontWeight={700}
        >
          {name}
        </text>
      )}
      {showPct && (
        <text
          x={x + width / 2}
          y={y + height / 2 + 10}
          textAnchor="middle"
          dominantBaseline="middle"
          fill="#fff"
          fontSize={Math.min(12, Math.max(9, width / 10))}
        >
          {pnl_pct >= 0 ? "+" : ""}
          {pnl_pct.toFixed(2)}%
        </text>
      )}
    </g>
  );
}

export default function PortfolioHeatmap({ portfolio }: PortfolioHeatmapProps) {
  const positions: Position[] = portfolio?.positions ?? [];
  const cells: HeatmapCell[] = positions
    .filter((p) => p.market_value > 0)
    .map((p) => ({
      name: p.ticker,
      size: p.market_value,
      pnl_pct: p.pnl_pct,
      pnl: p.unrealized_pnl,
    }));

  return (
    <section className="flex flex-col h-full bg-surface border border-border-dim rounded">
      <div className="px-3 py-2 border-b border-border-dim flex items-center justify-between">
        <h2 className="text-xs uppercase tracking-widest text-text-muted">
          Portfolio Heatmap
        </h2>
        <span className="text-xs text-text-muted tabular-nums">
          {cells.length} positions
        </span>
      </div>
      <div className="flex-1 relative min-h-0">
        {cells.length === 0 ? (
          <div className="absolute inset-0 flex items-center justify-center text-text-muted text-sm">
            No open positions
          </div>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <Treemap
              data={cells}
              dataKey="size"
              isAnimationActive={false}
              content={<CustomCell />}
            />
          </ResponsiveContainer>
        )}
      </div>
    </section>
  );
}
