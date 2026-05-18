"use client";

import type { Portfolio, PriceUpdate } from "../types";

interface PositionsTableProps {
  portfolio: Portfolio | null;
  prices: Record<string, PriceUpdate>;
  onSelectTicker: (ticker: string) => void;
}

export default function PositionsTable({
  portfolio,
  prices,
  onSelectTicker,
}: PositionsTableProps) {
  const positions = portfolio?.positions ?? [];

  return (
    <section className="flex flex-col h-full bg-surface border border-border-dim rounded">
      <div className="px-3 py-2 border-b border-border-dim flex items-center justify-between">
        <h2 className="text-xs uppercase tracking-widest text-text-muted">
          Positions
        </h2>
        <span className="text-xs text-text-muted tabular-nums">
          {positions.length}
        </span>
      </div>
      <div className="flex-1 overflow-auto">
        <table className="w-full text-sm">
          <thead className="sticky top-0 bg-surface">
            <tr className="text-text-muted text-xs uppercase tracking-wider">
              <th className="text-left px-3 py-1.5 font-normal">Ticker</th>
              <th className="text-right px-3 py-1.5 font-normal">Qty</th>
              <th className="text-right px-3 py-1.5 font-normal">Avg Cost</th>
              <th className="text-right px-3 py-1.5 font-normal">Last</th>
              <th className="text-right px-3 py-1.5 font-normal">
                Market Value
              </th>
              <th className="text-right px-3 py-1.5 font-normal">P&amp;L</th>
              <th className="text-right px-3 py-1.5 font-normal">P&amp;L %</th>
            </tr>
          </thead>
          <tbody>
            {positions.map((p) => {
              const livePrice = prices[p.ticker]?.price ?? p.current_price;
              const positive = p.unrealized_pnl >= 0;
              return (
                <tr
                  key={p.ticker}
                  onClick={() => onSelectTicker(p.ticker)}
                  className="border-t border-border-dim cursor-pointer hover:bg-surface-hover"
                >
                  <td className="px-3 py-2 font-semibold">{p.ticker}</td>
                  <td className="text-right px-3 py-2 tabular-nums">
                    {p.quantity.toFixed(p.quantity % 1 === 0 ? 0 : 4)}
                  </td>
                  <td className="text-right px-3 py-2 tabular-nums">
                    ${p.avg_cost.toFixed(2)}
                  </td>
                  <td className="text-right px-3 py-2 tabular-nums">
                    ${livePrice.toFixed(2)}
                  </td>
                  <td className="text-right px-3 py-2 tabular-nums">
                    ${p.market_value.toFixed(2)}
                  </td>
                  <td
                    className={`text-right px-3 py-2 tabular-nums ${
                      positive ? "text-price-up" : "text-price-down"
                    }`}
                  >
                    {positive ? "+" : ""}${p.unrealized_pnl.toFixed(2)}
                  </td>
                  <td
                    className={`text-right px-3 py-2 tabular-nums ${
                      positive ? "text-price-up" : "text-price-down"
                    }`}
                  >
                    {positive ? "+" : ""}
                    {p.pnl_pct.toFixed(2)}%
                  </td>
                </tr>
              );
            })}
            {positions.length === 0 && (
              <tr>
                <td
                  colSpan={7}
                  className="text-center text-text-muted py-6 text-xs"
                >
                  No open positions. Place a trade to get started.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
}
