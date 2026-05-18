"use client";

import { useCallback, useState } from "react";
import Header from "./components/Header";
import WatchlistPanel from "./components/WatchlistPanel";
import MainChart from "./components/MainChart";
import PortfolioHeatmap from "./components/PortfolioHeatmap";
import PnLChart from "./components/PnLChart";
import PositionsTable from "./components/PositionsTable";
import TradeBar from "./components/TradeBar";
import ChatPanel from "./components/ChatPanel";
import { usePrices } from "./hooks/usePrices";
import { usePortfolio } from "./hooks/usePortfolio";

export default function Home() {
  const { prices, sparklines, status, flashMap } = usePrices();
  const { portfolio, refresh: refreshPortfolio } = usePortfolio(5000);
  const [selectedTicker, setSelectedTicker] = useState<string | null>(null);
  const [chatOpen, setChatOpen] = useState(true);

  const onSelectTicker = useCallback((ticker: string) => {
    setSelectedTicker(ticker);
  }, []);

  const onTradeComplete = useCallback(() => {
    refreshPortfolio();
  }, [refreshPortfolio]);

  return (
    <div className="flex flex-col h-screen w-screen overflow-hidden">
      <Header portfolio={portfolio} status={status} />

      <main className="flex-1 min-h-0 grid grid-cols-[320px_minmax(0,1fr)_360px] gap-2 p-2">
        {/* Left column: Watchlist */}
        <div className="min-h-0 overflow-hidden">
          <WatchlistPanel
            prices={prices}
            sparklines={sparklines}
            flashMap={flashMap}
            selectedTicker={selectedTicker}
            onSelectTicker={onSelectTicker}
          />
        </div>

        {/* Center column */}
        <div className="min-h-0 flex flex-col gap-2 overflow-hidden">
          <div className="flex-[2] min-h-0">
            <MainChart
              ticker={selectedTicker}
              prices={prices}
              sparklines={sparklines}
            />
          </div>
          <div className="flex-1 min-h-0 grid grid-cols-2 gap-2">
            <PortfolioHeatmap portfolio={portfolio} />
            <PnLChart />
          </div>
          <div className="flex-1 min-h-0">
            <PositionsTable
              portfolio={portfolio}
              prices={prices}
              onSelectTicker={onSelectTicker}
            />
          </div>
        </div>

        {/* Right column: Chat */}
        <div className="min-h-0 overflow-hidden">
          <ChatPanel
            open={chatOpen}
            onToggle={() => setChatOpen((v) => !v)}
            onActionsExecuted={refreshPortfolio}
          />
        </div>
      </main>

      <div className="px-2 pb-2">
        <TradeBar
          selectedTicker={selectedTicker}
          onTradeComplete={onTradeComplete}
        />
      </div>
    </div>
  );
}
