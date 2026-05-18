"use client";

import { useEffect, useRef, useState } from "react";
import type { ChatMessage, ExecutedTrade, WatchlistChange } from "../types";

interface ChatPanelProps {
  open: boolean;
  onToggle: () => void;
  onActionsExecuted: () => void;
}

interface ChatApiResponse {
  message: string;
  trades?: ExecutedTrade[];
  executed_trades?: ExecutedTrade[];
  watchlist_changes?: WatchlistChange[];
  errors?: string[];
}

export default function ChatPanel({
  open,
  onToggle,
  onActionsExecuted,
}: ChatPanelProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      role: "assistant",
      content:
        "Hi — I'm FinAlly, your AI trading assistant. Ask me to analyze your portfolio, suggest trades, or manage your watchlist.",
    },
  ]);
  const [input, setInput] = useState("");
  const [pending, setPending] = useState(false);
  const scrollRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({
      top: scrollRef.current.scrollHeight,
      behavior: "smooth",
    });
  }, [messages, pending]);

  const send = async (e: React.FormEvent) => {
    e.preventDefault();
    const text = input.trim();
    if (!text || pending) return;
    const userMsg: ChatMessage = { role: "user", content: text };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setPending(true);
    try {
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: text }),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail || `HTTP ${res.status}`);
      }
      const data: ChatApiResponse = await res.json();
      const trades = data.executed_trades ?? data.trades ?? [];
      const watchlist = data.watchlist_changes ?? [];
      const errors = data.errors ?? [];
      const assistantMsg: ChatMessage = {
        role: "assistant",
        content: data.message ?? "",
        executed_trades: trades,
        watchlist_changes: watchlist,
        errors,
      };
      setMessages((prev) => [...prev, assistantMsg]);
      if (trades.length > 0 || watchlist.length > 0) onActionsExecuted();
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content:
            err instanceof Error
              ? `Error: ${err.message}`
              : "Something went wrong calling the assistant.",
        },
      ]);
    } finally {
      setPending(false);
    }
  };

  if (!open) {
    return (
      <button
        onClick={onToggle}
        className="fixed right-4 bottom-4 bg-accent-purple text-white px-4 py-2 rounded-full shadow-lg hover:opacity-90 z-30"
      >
        AI Chat
      </button>
    );
  }

  return (
    <aside className="flex flex-col h-full bg-surface border border-border-dim rounded">
      <div className="px-3 py-2 border-b border-border-dim flex items-center justify-between">
        <h2 className="text-xs uppercase tracking-widest text-text-muted">
          FinAlly Assistant
        </h2>
        <button
          onClick={onToggle}
          className="text-text-muted hover:text-text-primary text-sm"
          aria-label="Close chat"
        >
          ×
        </button>
      </div>

      <div ref={scrollRef} className="flex-1 overflow-y-auto p-3 space-y-3">
        {messages.map((m, idx) => (
          <div
            key={idx}
            className={`flex flex-col ${
              m.role === "user" ? "items-end" : "items-start"
            }`}
          >
            <div
              className={`max-w-[85%] rounded px-3 py-2 text-sm whitespace-pre-wrap ${
                m.role === "user"
                  ? "bg-accent-blue/20 text-text-primary"
                  : "bg-terminal text-text-primary border border-border-dim"
              }`}
            >
              {m.content}
            </div>
            {m.executed_trades && m.executed_trades.length > 0 && (
              <div className="flex flex-wrap gap-1 mt-1">
                {m.executed_trades.map((t, i) => (
                  <span
                    key={i}
                    className={`text-xs px-2 py-0.5 rounded ${
                      t.side === "buy"
                        ? "bg-price-up/20 text-price-up"
                        : "bg-price-down/20 text-price-down"
                    }`}
                  >
                    {t.side.toUpperCase()} {t.quantity} {t.ticker}
                    {t.price !== undefined ? ` @ $${t.price.toFixed(2)}` : ""}
                  </span>
                ))}
              </div>
            )}
            {m.watchlist_changes && m.watchlist_changes.length > 0 && (
              <div className="flex flex-wrap gap-1 mt-1">
                {m.watchlist_changes.map((w, i) => (
                  <span
                    key={i}
                    className="text-xs px-2 py-0.5 rounded bg-accent-yellow/20 text-accent-yellow"
                  >
                    {w.action === "add" ? "+ " : "− "}
                    {w.ticker}
                  </span>
                ))}
              </div>
            )}
            {m.errors && m.errors.length > 0 && (
              <div className="flex flex-wrap gap-1 mt-1">
                {m.errors.map((e, i) => (
                  <span
                    key={i}
                    className="text-xs px-2 py-0.5 rounded bg-price-down/20 text-price-down"
                  >
                    {e}
                  </span>
                ))}
              </div>
            )}
          </div>
        ))}
        {pending && (
          <div className="flex items-start">
            <div className="bg-terminal border border-border-dim rounded px-3 py-2 text-sm text-text-muted">
              <span className="pulse-dot">●</span>
              <span className="pulse-dot ml-1">●</span>
              <span className="pulse-dot ml-1">●</span>
            </div>
          </div>
        )}
      </div>

      <form onSubmit={send} className="border-t border-border-dim p-2 flex gap-2">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask FinAlly a message..."
          disabled={pending}
          className="flex-1 bg-terminal border border-border-dim rounded px-2 py-1.5 text-sm text-text-primary placeholder:text-text-muted focus:outline-none focus:border-accent-purple"
        />
        <button
          type="submit"
          disabled={pending || !input.trim()}
          className="px-3 py-1.5 bg-accent-purple text-white text-sm rounded hover:opacity-90 disabled:opacity-50"
        >
          Send
        </button>
      </form>
    </aside>
  );
}
