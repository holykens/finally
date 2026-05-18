"use client";

import type { Portfolio } from "../types";
import type { ConnectionStatus } from "../hooks/usePrices";

interface HeaderProps {
  portfolio: Portfolio | null;
  status: ConnectionStatus;
}

const statusColor: Record<ConnectionStatus, string> = {
  connected: "bg-price-up",
  reconnecting: "bg-accent-yellow",
  disconnected: "bg-price-down",
};

const statusLabel: Record<ConnectionStatus, string> = {
  connected: "LIVE",
  reconnecting: "RECONNECTING",
  disconnected: "OFFLINE",
};

function formatCurrency(value: number | undefined | null) {
  if (value === undefined || value === null || Number.isNaN(value)) return "—";
  return value.toLocaleString("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

export default function Header({ portfolio, status }: HeaderProps) {
  const total = portfolio?.total_value ?? null;
  const cash = portfolio?.cash_balance ?? null;
  const pnl = portfolio?.total_pnl ?? 0;
  const pnlPositive = pnl >= 0;

  return (
    <header className="h-14 flex items-center justify-between px-4 border-b border-border-dim bg-surface">
      <div className="flex items-center gap-3">
        <span className="text-accent-yellow font-bold text-xl tracking-wide">
          FinAlly
        </span>
        <span className="text-text-muted text-xs uppercase tracking-widest">
          AI Trading Workstation
        </span>
      </div>

      <div className="flex items-center gap-6 text-sm">
        <div className="flex flex-col items-end">
          <span className="text-text-muted text-xs">Total Value</span>
          <span className="text-accent-blue font-semibold text-lg tabular-nums">
            {formatCurrency(total)}
          </span>
        </div>
        <div className="flex flex-col items-end">
          <span className="text-text-muted text-xs">Cash</span>
          <span className="font-semibold text-text-primary tabular-nums">
            {formatCurrency(cash)}
          </span>
        </div>
        <div className="flex flex-col items-end">
          <span className="text-text-muted text-xs">Unrealized P&amp;L</span>
          <span
            className={`font-semibold tabular-nums ${
              pnlPositive ? "text-price-up" : "text-price-down"
            }`}
          >
            {pnlPositive ? "+" : ""}
            {formatCurrency(pnl)}
          </span>
        </div>
        <div className="flex items-center gap-2 pl-4 border-l border-border-dim">
          <span
            className={`inline-block w-2.5 h-2.5 rounded-full ${statusColor[status]} ${
              status === "reconnecting" ? "pulse-dot" : ""
            }`}
            aria-label={`Connection: ${status}`}
          />
          <span className="text-text-muted text-xs uppercase tracking-widest">
            {statusLabel[status]}
          </span>
        </div>
      </div>
    </header>
  );
}
