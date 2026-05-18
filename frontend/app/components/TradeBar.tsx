"use client";

import { useEffect, useState } from "react";

interface TradeBarProps {
  selectedTicker: string | null;
  onTradeComplete: () => void;
}

type Toast = { kind: "success" | "error"; message: string } | null;

export default function TradeBar({
  selectedTicker,
  onTradeComplete,
}: TradeBarProps) {
  const [ticker, setTicker] = useState("");
  const [quantity, setQuantity] = useState("1");
  const [submitting, setSubmitting] = useState(false);
  const [toast, setToast] = useState<Toast>(null);

  useEffect(() => {
    if (selectedTicker) setTicker(selectedTicker);
  }, [selectedTicker]);

  useEffect(() => {
    if (!toast) return;
    const id = setTimeout(() => setToast(null), 3500);
    return () => clearTimeout(id);
  }, [toast]);

  const submit = async (side: "buy" | "sell") => {
    const t = ticker.trim().toUpperCase();
    const q = parseFloat(quantity);
    if (!t) {
      setToast({ kind: "error", message: "Enter a ticker symbol" });
      return;
    }
    if (!Number.isFinite(q) || q <= 0) {
      setToast({ kind: "error", message: "Quantity must be > 0" });
      return;
    }
    setSubmitting(true);
    try {
      const res = await fetch("/api/portfolio/trade", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ticker: t, quantity: q, side }),
      });
      const body = await res.json().catch(() => ({}));
      if (!res.ok) {
        throw new Error(body.detail || body.error || `HTTP ${res.status}`);
      }
      setToast({
        kind: "success",
        message: `${side.toUpperCase()} ${q} ${t} executed`,
      });
      onTradeComplete();
    } catch (err) {
      setToast({
        kind: "error",
        message: err instanceof Error ? err.message : "Trade failed",
      });
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <section className="flex items-center gap-3 bg-surface border border-border-dim rounded px-3 py-2">
      <span className="text-xs uppercase tracking-widest text-text-muted">
        Trade
      </span>
      <input
        type="text"
        value={ticker}
        onChange={(e) => setTicker(e.target.value.toUpperCase())}
        placeholder="TICKER"
        className="bg-terminal border border-border-dim rounded px-2 py-1 text-sm w-24 text-text-primary placeholder:text-text-muted focus:outline-none focus:border-accent-blue uppercase"
        disabled={submitting}
      />
      <input
        type="number"
        value={quantity}
        onChange={(e) => setQuantity(e.target.value)}
        min={0.01}
        step={0.01}
        placeholder="Qty"
        className="bg-terminal border border-border-dim rounded px-2 py-1 text-sm w-24 text-text-primary placeholder:text-text-muted focus:outline-none focus:border-accent-blue tabular-nums"
        disabled={submitting}
      />
      <button
        onClick={() => submit("buy")}
        disabled={submitting}
        className="px-4 py-1.5 bg-accent-blue text-white text-sm font-semibold rounded hover:opacity-90 disabled:opacity-50"
      >
        BUY
      </button>
      <button
        onClick={() => submit("sell")}
        disabled={submitting}
        className="px-4 py-1.5 bg-price-down text-white text-sm font-semibold rounded hover:opacity-90 disabled:opacity-50"
      >
        SELL
      </button>
      {toast && (
        <span
          className={`text-xs ml-2 px-2 py-1 rounded ${
            toast.kind === "success"
              ? "bg-price-up/20 text-price-up"
              : "bg-price-down/20 text-price-down"
          }`}
        >
          {toast.message}
        </span>
      )}
    </section>
  );
}
