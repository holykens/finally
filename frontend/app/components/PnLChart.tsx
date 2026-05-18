"use client";

import { useCallback, useEffect, useState } from "react";
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { PortfolioSnapshot } from "../types";

interface ChartPoint {
  t: number;
  value: number;
  label: string;
}

export default function PnLChart() {
  const [data, setData] = useState<ChartPoint[]>([]);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const res = await fetch("/api/portfolio/history");
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const body = await res.json();
      const snapshots: PortfolioSnapshot[] = Array.isArray(body)
        ? body
        : Array.isArray(body?.snapshots)
          ? body.snapshots
          : [];
      const points: ChartPoint[] = snapshots
        .map((s) => {
          const t = Date.parse(s.recorded_at);
          return {
            t,
            value: s.total_value,
            label: new Date(t).toLocaleTimeString(),
          };
        })
        .filter((p) => Number.isFinite(p.t))
        .sort((a, b) => a.t - b.t);
      setData(points);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load history");
    }
  }, []);

  useEffect(() => {
    load();
    const id = setInterval(load, 30000);
    return () => clearInterval(id);
  }, [load]);

  return (
    <section className="flex flex-col h-full bg-surface border border-border-dim rounded">
      <div className="px-3 py-2 border-b border-border-dim flex items-center justify-between">
        <h2 className="text-xs uppercase tracking-widest text-text-muted">
          P&amp;L Over Time
        </h2>
        {error && <span className="text-price-down text-xs">{error}</span>}
      </div>
      <div className="flex-1 relative min-h-0">
        {data.length < 2 ? (
          <div className="absolute inset-0 flex items-center justify-center text-text-muted text-sm">
            Collecting snapshots...
          </div>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <LineChart
              data={data}
              margin={{ top: 8, right: 16, bottom: 8, left: 8 }}
            >
              <CartesianGrid stroke="#1f2630" strokeDasharray="2 2" />
              <XAxis
                dataKey="label"
                stroke="#8b949e"
                tick={{ fontSize: 10 }}
                minTickGap={32}
              />
              <YAxis
                stroke="#8b949e"
                tick={{ fontSize: 10 }}
                domain={["auto", "auto"]}
                tickFormatter={(v) =>
                  typeof v === "number"
                    ? `$${v.toLocaleString(undefined, { maximumFractionDigits: 0 })}`
                    : String(v)
                }
                width={70}
              />
              <Tooltip
                contentStyle={{
                  background: "#161b22",
                  border: "1px solid #30363d",
                  fontSize: 12,
                }}
                labelStyle={{ color: "#8b949e" }}
                formatter={(v) => {
                  const n = typeof v === "number" ? v : Number(v);
                  return [
                    Number.isFinite(n) ? `$${n.toFixed(2)}` : String(v),
                    "Total Value",
                  ];
                }}
              />
              <Line
                type="monotone"
                dataKey="value"
                stroke="#209dd7"
                strokeWidth={2}
                dot={false}
                isAnimationActive={false}
              />
            </LineChart>
          </ResponsiveContainer>
        )}
      </div>
    </section>
  );
}
