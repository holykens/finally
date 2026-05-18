"use client";

import { useEffect, useRef } from "react";
import {
  createChart,
  ColorType,
  type IChartApi,
  type ISeriesApi,
  LineSeries,
} from "lightweight-charts";
import type { PriceUpdate } from "../types";

interface MainChartProps {
  ticker: string | null;
  prices: Record<string, PriceUpdate>;
  sparklines: Record<string, number[]>;
}

export default function MainChart({
  ticker,
  prices,
  sparklines,
}: MainChartProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<ISeriesApi<"Line"> | null>(null);
  const lastTickerRef = useRef<string | null>(null);
  const lastTimeRef = useRef<number>(0);

  useEffect(() => {
    if (!containerRef.current) return;
    const chart = createChart(containerRef.current, {
      layout: {
        background: { type: ColorType.Solid, color: "#0d1117" },
        textColor: "#8b949e",
        fontFamily:
          "'JetBrains Mono', 'Fira Code', ui-monospace, monospace",
      },
      grid: {
        vertLines: { color: "#1f2630" },
        horzLines: { color: "#1f2630" },
      },
      rightPriceScale: { borderColor: "#30363d" },
      timeScale: {
        borderColor: "#30363d",
        timeVisible: true,
        secondsVisible: true,
      },
      autoSize: true,
      crosshair: { mode: 1 },
    });

    const series = chart.addSeries(LineSeries, {
      color: "#209dd7",
      lineWidth: 2,
      priceFormat: { type: "price", precision: 2, minMove: 0.01 },
    });

    chartRef.current = chart;
    seriesRef.current = series;

    return () => {
      chart.remove();
      chartRef.current = null;
      seriesRef.current = null;
    };
  }, []);

  // Reset data when ticker changes
  useEffect(() => {
    if (!seriesRef.current || !ticker) return;
    if (lastTickerRef.current !== ticker) {
      const seed = sparklines[ticker] || [];
      const baseTime = Math.floor(Date.now() / 1000) - seed.length;
      const seriesData = seed.map((price, i) => ({
        time: (baseTime + i) as never,
        value: price,
      }));
      seriesRef.current.setData(seriesData);
      lastTickerRef.current = ticker;
      lastTimeRef.current = baseTime + seed.length - 1;
      chartRef.current?.timeScale().fitContent();
    }
  }, [ticker, sparklines]);

  // Append new prices
  useEffect(() => {
    if (!seriesRef.current || !ticker) return;
    const p = prices[ticker];
    if (!p) return;
    const time = Math.floor(Date.now() / 1000);
    if (time <= lastTimeRef.current) return;
    lastTimeRef.current = time;
    try {
      seriesRef.current.update({ time: time as never, value: p.price });
    } catch {
      // ignore time ordering issues
    }
  }, [prices, ticker]);

  const current = ticker ? prices[ticker] : null;

  return (
    <section className="flex flex-col h-full bg-surface border border-border-dim rounded">
      <div className="px-3 py-2 border-b border-border-dim flex items-center justify-between">
        <div className="flex items-center gap-3">
          <h2 className="text-xs uppercase tracking-widest text-text-muted">
            Chart
          </h2>
          {ticker && (
            <span className="text-accent-yellow font-bold text-sm">
              {ticker}
            </span>
          )}
        </div>
        {current && (
          <div className="text-sm tabular-nums">
            <span className="text-text-primary font-semibold">
              ${current.price.toFixed(2)}
            </span>
          </div>
        )}
      </div>
      <div className="flex-1 relative min-h-0">
        {!ticker && (
          <div className="absolute inset-0 flex items-center justify-center text-text-muted text-sm">
            Select a ticker from the watchlist
          </div>
        )}
        <div ref={containerRef} className="absolute inset-0" />
      </div>
    </section>
  );
}
