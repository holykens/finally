"use client";

import { useEffect, useState } from "react";
import type { PriceUpdate } from "../types";

export type ConnectionStatus = "connected" | "reconnecting" | "disconnected";

export function usePrices() {
  const [prices, setPrices] = useState<Record<string, PriceUpdate>>({});
  const [sparklines, setSparklines] = useState<Record<string, number[]>>({});
  const [status, setStatus] = useState<ConnectionStatus>("disconnected");
  const [flashMap, setFlashMap] = useState<Record<string, "up" | "down">>({});

  useEffect(() => {
    let es: EventSource | null = null;
    let reconnectTimer: ReturnType<typeof setTimeout> | null = null;
    const flashTimers: Record<string, ReturnType<typeof setTimeout>> = {};
    let closed = false;

    function connect() {
      if (closed) return;
      setStatus("reconnecting");

      try {
        es = new EventSource("/api/stream/prices");
      } catch {
        setStatus("disconnected");
        reconnectTimer = setTimeout(connect, 3000);
        return;
      }

      es.onopen = () => {
        if (!closed) setStatus("connected");
      };

      es.onmessage = (event) => {
        try {
          const payload: Record<string, PriceUpdate> = JSON.parse(event.data);
          const updates = Object.values(payload);

          setPrices((prev) => {
            const next = { ...prev };
            for (const u of updates) next[u.ticker] = u;
            return next;
          });

          setSparklines((prev) => {
            const next = { ...prev };
            for (const u of updates) {
              const existing = next[u.ticker] || [];
              next[u.ticker] = [...existing, u.price].slice(-60);
            }
            return next;
          });

          for (const u of updates) {
            if (u.direction !== "flat") {
              setFlashMap((prev) => ({
                ...prev,
                [u.ticker]: u.direction as "up" | "down",
              }));
              if (flashTimers[u.ticker]) clearTimeout(flashTimers[u.ticker]);
              flashTimers[u.ticker] = setTimeout(() => {
                setFlashMap((prev) => {
                  const n = { ...prev };
                  delete n[u.ticker];
                  return n;
                });
              }, 600);
            }
          }
        } catch {
          // ignore malformed payloads
        }
      };

      es.onerror = () => {
        if (closed) return;
        setStatus("disconnected");
        es?.close();
        es = null;
        reconnectTimer = setTimeout(connect, 3000);
      };
    }

    connect();

    return () => {
      closed = true;
      es?.close();
      if (reconnectTimer) clearTimeout(reconnectTimer);
      Object.values(flashTimers).forEach(clearTimeout);
    };
  }, []);

  return { prices, sparklines, status, flashMap };
}
