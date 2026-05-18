export interface PriceUpdate {
  ticker: string;
  price: number;
  previous_price: number;
  direction: "up" | "down" | "flat";
  timestamp: string;
}

export interface Position {
  ticker: string;
  quantity: number;
  avg_cost: number;
  current_price: number;
  market_value: number;
  unrealized_pnl: number;
  pnl_pct: number;
}

export interface Portfolio {
  cash_balance: number;
  positions: Position[];
  total_value: number;
  total_pnl: number;
}

export interface WatchlistEntry {
  ticker: string;
  price: number;
  previous_price: number;
  direction: string;
}

export interface PortfolioSnapshot {
  total_value: number;
  recorded_at: string;
}

export interface ExecutedTrade {
  ticker: string;
  side: "buy" | "sell";
  quantity: number;
  price?: number;
}

export interface WatchlistChange {
  ticker: string;
  action: "add" | "remove";
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  executed_trades?: ExecutedTrade[];
  watchlist_changes?: WatchlistChange[];
  errors?: string[];
}
