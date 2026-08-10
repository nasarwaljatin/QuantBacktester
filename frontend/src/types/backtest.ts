// frontend/src/types/backtest.ts
// TypeScript interfaces matching backend Pydantic schemas

export interface BacktestConfig {
  initial_capital: number;
  commission: number;
  slippage: number;
  allocation_pct: number;
  sizing_model?: string;
  sizing_params?: Record<string, any>;
  commission_type?: string;
  commission_value?: number;
  commission_tier_limit?: number;
  commission_tier_value?: number;
  slippage_type?: string;
  slippage_value?: number;
  spread?: number;
  volume_limit_pct?: number | null;
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

// ---------------------------------------------------------------------------
// Phase 4: Parameter Sweep & Walk-Forward Optimization
// ---------------------------------------------------------------------------

export interface SweepRequest {
  strategy_code: string;
  tickers: string[];
  ticker_weights?: Record<string, number>;
  start_date: string;
  end_date: string;
  param_grid: Record<string, (number | string)[]>;
  config: BacktestConfig;
  objective?: string;
}

export interface WFARequest {
  strategy_code: string;
  tickers: string[];
  ticker_weights?: Record<string, number>;
  start_date: string;
  end_date: string;
  param_grid: Record<string, (number | string)[]>;
  config: BacktestConfig;
  in_sample_days?: number;
  out_of_sample_days?: number;
  window_type?: "rolling" | "expanding";
  anchored?: boolean;
  max_combinations?: number;
  objective?: string;
}

export interface SweepResultItem {
  combo_index: number;
  parameters: Record<string, any>;
  metrics?: Record<string, any> | null;
  equity_curve?: EquityCurvePoint[] | null;
  status: string;
  error_message?: string | null;
}

export interface WFAWindowResult {
  window_index: number;
  in_sample_start: string;
  in_sample_end: string;
  out_of_sample_start: string;
  out_of_sample_end: string;
  optimized_params?: Record<string, any> | null;
  in_sample_metrics?: Record<string, any> | null;
  out_of_sample_metrics?: Record<string, any> | null;
  /** OOS objective / IS objective; >= 0.7 good, < 0.5 overfitting signal */
  efficiency_ratio?: number | null;
  status: string;
}

export interface SweepResponse {
  task_id: string;
  status: string;
  run_type: "sweep";
  progress?: string;
  sweep_results?: SweepResultItem[];
  best_params?: Record<string, any>;
  total_combinations?: number;
  objective?: string;
  param_grid?: Record<string, any[]>;
  error?: string;
}

export interface WFAResponse {
  task_id: string;
  status: string;
  run_type: "walk_forward";
  progress?: string;
  wfa_windows?: WFAWindowResult[];
  combined_oos_equity?: EquityCurvePoint[];
  aggregate_oos_metrics?: Record<string, any>;
  total_windows?: number;
  in_sample_days?: number;
  out_of_sample_days?: number;
  window_type?: "rolling" | "expanding";
  anchored?: boolean;
  param_grid?: Record<string, any[]>;
  objective?: string;
  /** Per-fold {window_index, is_value, oos_value, ratio} */
  efficiency_ratios?: Array<{
    window_index: number;
    is_value: number | null;
    oos_value: number | null;
    ratio: number | null;
  }>;
  /** Mean efficiency ratio across folds; < 0.5 = likely overfit */
  aggregate_efficiency_ratio?: number | null;
  /** CV per parameter across folds; high CV = unstable */
  param_stability?: Record<string, number | null>;
  error?: string;
}

export interface WFAEstimateRequest {
  tickers: string[];
  start_date: string;
  end_date: string;
  param_grid: Record<string, (number | string)[]>;
  in_sample_days?: number;
  out_of_sample_days?: number;
  window_type?: "rolling" | "expanding";
  anchored?: boolean;
  max_combinations?: number;
}

export interface WFAEstimateResponse {
  n_folds: number;
  n_combinations: number;
  total_runs: number;
  feasible: boolean;
  error?: string | null;
}
