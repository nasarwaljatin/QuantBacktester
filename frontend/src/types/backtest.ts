// frontend/src/types/backtest.ts
// TypeScript interfaces matching backend Pydantic schemas

export interface BacktestConfig {
  initial_capital: number;
  commission: number;
  slippage: number;
  allocation_pct: number;
}

export interface BacktestRequest {
  strategy_code: string;
  ticker?: string; // Deprecated, use tickers
  tickers?: string[];
  ticker_weights?: Record<string, number>;
  start_date: string;
  end_date: string;
  config: BacktestConfig;
}

export interface EquityCurvePoint {
  date: string;
  value: number;
}

export interface TradeRecord {
  entry_date: string;
  exit_date: string;
  size: number;
  entry_price: number;
  exit_price: number;
  pnl: number;
  pnl_pct: number;
  ticker?: string;
}

export interface PerformanceMetrics {
  total_return: number;
  annualized_return: number;
  sharpe_ratio: number;
  sortino_ratio: number;
  max_drawdown: number;
  calmar_ratio: number;
  win_rate: number;
  profit_factor: number;
  total_trades: number;
  avg_holding_period: number;
}

export interface MonteCarloResult {
  paths: number[][];
  percentile_5: number[];
  percentile_50: number[];
  percentile_95: number[];
  final_values: number[];
  prob_profit: number;
}

export interface BacktestResponse {
  task_id: string;
  status: string;
  ticker?: string;
  tickers?: string[];
  ticker_weights?: Record<string, number>;
  start_date?: string;
  end_date?: string;
  equity_curve?: EquityCurvePoint[];
  benchmark_curve?: EquityCurvePoint[];
  trades?: TradeRecord[];
  metrics?: PerformanceMetrics;
  monte_carlo?: MonteCarloResult;
  error?: string;
  step?: string;
  allocation_pct?: number;
  position_sizing?: string;
}

export interface TickerResult {
  symbol: string;
  name: string;
  exchange: string;
}

export interface StrategyTemplate {
  name: string;
  code: string;
}
