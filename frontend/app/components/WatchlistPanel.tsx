"use client";

import { useCallback, useEffect, useState } from "react";
import type { PriceUpdate } from "../types";
import Sparkline from "./Sparkline";

interface WatchlistPanelProps {
  prices: Record<string, PriceUpdate>;
  sparklines: Record<string, number[]>;
  flashMap: Record<string, "up" | "down">;
  selectedTicker: string | null;
  onSelectTicker: (ticker: string) => void;
}

interface WatchlistRow {
  ticker: string;
}

export default function WatchlistPanel({
  prices,
  sparklines,
  flashMap,
  selectedTicker,
  onSelectTicker,
}: WatchlistPanelProps) {
  const [watchlist, setWatchlist] = useState<WatchlistRow[]>([]);
  const [newTicker, setNewTicker] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const fetchWatchlist = useCallback(async () => {
    try {
      const res = await fetch("/api/watchlist");
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      const items: WatchlistRow[] = Array.isArray(data)
        ? data.map((item: { ticker: string }) => ({ ticker: item.ticker }))
        : Array.isArray(data?.tickers)
          ? data.tickers.map((t: string) => ({ ticker: t }))
          : [];
      setWatchlist(items);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load watchlist");
    }
  }, []);

  useEffect(() => {
    fetchWatchlist();
    const id = setInterval(fetchWatchlist, 15000);
    return () => clearInterval(id);
  }, [fetchWatchlist]);

  const addTicker = async (e: React.FormEvent) => {
    e.preventDefault();
    const t = newTicker.trim().toUpperCase();
    if (!t) return;
    setLoading(true);
    setError(null);
    try {
      const res = await fetch("/api/watchlist", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ticker: t }),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail || `HTTP ${res.status}`);
      }
      setNewTicker("");
      await fetchWatchlist();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to add ticker");
    } finally {
      setLoading(false);
    }
  };

  const removeTicker = async (ticker: string) => {
    try {
      const res = await fetch(`/api/watchlist/${encodeURIComponent(ticker)}`, {
        method: "DELETE",
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      await fetchWatchlist();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to remove ticker");
    }
  };

  return (
    <section className="flex flex-col h-full bg-surface border border-border-dim rounded">
      <div className="px-3 py-2 border-b border-border-dim flex items-center justify-between">
        <h2 className="text-xs uppercase tracking-widest text-text-muted">
          Watchlist
        </h2>
        <span className="text-xs text-text-muted tabular-nums">
          {watchlist.length}
        </span>
      </div>

      <div className="flex-1 overflow-y-auto">
        <table className="w-full text-sm">
          <thead className="sticky top-0 bg-surface z-10">
            <tr className="text-text-muted text-xs uppercase tracking-wider">
              <th className="text-left px-3 py-1.5 font-normal">Ticker</th>
              <th className="text-right px-2 py-1.5 font-normal">Price</th>
              <th className="text-right px-2 py-1.5 font-normal">Chg %</th>
              <th className="px-2 py-1.5 font-normal">Trend</th>
              <th className="w-6"></th>
            </tr>
          </thead>
          <tbody>
            {watchlist.map(({ ticker }) => {
              const p = prices[ticker];
              const price = p?.price;
              const prev = p?.previous_price;
              const flash = flashMap[ticker];
              const changePct =
                price !== undefined && prev !== undefined && prev !== 0
                  ? ((price - prev) / prev) * 100
                  : 0;
              const isPositive = changePct >= 0;
              const isSelected = selectedTicker === ticker;
              const spark = sparklines[ticker] || [];
              return (
                <tr
                  key={ticker}
                  onClick={() => onSelectTicker(ticker)}
                  className={`cursor-pointer border-t border-border-dim hover:bg-surface-hover ${
                    isSelected ? "bg-surface-hover" : ""
                  }`}
                >
                  <td className="px-3 py-2 font-semibold text-text-primary">
                    {ticker}
                  </td>
                  <td
                    className={`text-right px-2 py-2 tabular-nums ${
                      flash === "up"
                        ? "flash-up"
                        : flash === "down"
                          ? "flash-down"
                          : ""
                    }`}
                  >
                    {price !== undefined ? price.toFixed(2) : "—"}
                  </td>
                  <td
                    className={`text-right px-2 py-2 tabular-nums ${
                      isPositive ? "text-price-up" : "text-price-down"
                    }`}
                  >
                    {price !== undefined
                      ? `${isPositive ? "+" : ""}${changePct.toFixed(2)}%`
                      : "—"}
                  </td>
                  <td className="px-2 py-2">
                    <Sparkline data={spark} positive={isPositive} />
                  </td>
                  <td className="px-1">
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        removeTicker(ticker);
                      }}
                      className="text-text-muted hover:text-price-down text-xs px-1"
                      aria-label={`Remove ${ticker}`}
                      title="Remove"
                    >
                      ×
                    </button>
                  </td>
                </tr>
              );
            })}
            {watchlist.length === 0 && (
              <tr>
                <td
                  colSpan={5}
                  className="text-center text-text-muted py-6 text-xs"
                >
                  No tickers yet. Add one below.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      <form
        onSubmit={addTicker}
        className="border-t border-border-dim p-2 flex gap-2"
      >
        <input
          type="text"
          value={newTicker}
          onChange={(e) => setNewTicker(e.target.value)}
          placeholder="Add ticker (e.g. NVDA)"
          className="flex-1 bg-terminal border border-border-dim rounded px-2 py-1 text-sm text-text-primary placeholder:text-text-muted focus:outline-none focus:border-accent-blue uppercase"
          disabled={loading}
        />
        <button
          type="submit"
          disabled={loading || !newTicker.trim()}
          className="px-3 py-1 bg-accent-blue text-white text-sm rounded hover:opacity-90 disabled:opacity-50"
        >
          Add
        </button>
      </form>
      {error && (
        <div className="text-price-down text-xs px-3 pb-2">{error}</div>
      )}
    </section>
  );
}
