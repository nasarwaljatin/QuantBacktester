// frontend/src/lib/store.ts
// Zustand store for client-side state management

import { create } from "zustand";
import type { BacktestConfig, SweepResponse, WFAResponse, WFAEstimateResponse } from "@/types/backtest";

const DEFAULT_STRATEGY = `class UserStrategy(bt.Strategy):
    params = dict(fast=50, slow=200)

    def __init__(self):
        self.fast_ma = bt.ind.SMA(period=self.p.fast)
        self.slow_ma = bt.ind.SMA(period=self.p.slow)
        self.crossover = bt.ind.CrossOver(self.fast_ma, self.slow_ma)

    def next(self):
        if not self.position:
            if self.crossover > 0:
                self.buy()
        elif self.crossover < 0:
            self.close()
`;

// "single" | "sweep" | "walk_forward"
export type OptimizationMode = "single" | "sweep" | "walk_forward";

interface BacktestStore {
  // Currency selection
  currency: string;
  setCurrency: (currency: string) => void;

  // Strategy editor
  strategyCode: string;
  setStrategyCode: (code: string) => void;

  // Ticker selection
  ticker: string;
  tickers: string[];
  setTicker: (ticker: string) => void;
  setTickers: (tickers: string[]) => void;
  tickerWeights: Record<string, number>;
  setTickerWeights: (weights: Record<string, number>) => void;

  // Date range
  startDate: string;
  endDate: string;
  setStartDate: (date: string) => void;
  setEndDate: (date: string) => void;

  // Config
  config: BacktestConfig;
  setConfig: (config: Partial<BacktestConfig>) => void;

  // Task state
  taskId: string | null;
  setTaskId: (id: string | null) => void;
  isRunning: boolean;
  setIsRunning: (running: boolean) => void;
  runStep: string;
  setRunStep: (step: string) => void;
  error: string | null;
  setError: (error: string | null) => void;

  // ─── Phase 4: Optimization ───────────────────────────────────────────────
  optimizationMode: OptimizationMode;
  setOptimizationMode: (mode: OptimizationMode) => void;

  // Parameter grid: { paramName: "3, 5, 10" } (raw comma-sep strings from inputs)
  paramGridRaw: Record<string, string>;
  setParamGridRaw: (grid: Record<string, string>) => void;

  // Walk-forward settings
  inSampleDays: number;
  setInSampleDays: (days: number) => void;
  outOfSampleDays: number;
  setOutOfSampleDays: (days: number) => void;
  wfaObjective: string;
  setWfaObjective: (obj: string) => void;
  wfaWindowType: "rolling" | "expanding";
  setWfaWindowType: (t: "rolling" | "expanding") => void;
  wfaAnchored: boolean;
  setWfaAnchored: (v: boolean) => void;
  wfaMaxCombinations: number;
  setWfaMaxCombinations: (n: number) => void;
  /** Pre-flight estimate result (updated on config change) */
  wfaEstimate: WFAEstimateResponse | null;
  setWfaEstimate: (e: WFAEstimateResponse | null) => void;

  // Sweep / WFA results
  sweepResult: SweepResponse | null;
  setSweepResult: (r: SweepResponse | null) => void;
  wfaResult: WFAResponse | null;
  setWfaResult: (r: WFAResponse | null) => void;

  // Sweep progress label (updated while polling)
  optimizationProgress: string;
  setOptimizationProgress: (progress: string) => void;
  // ─────────────────────────────────────────────────────────────────────────

  // Reset
  reset: () => void;
}

export const useBacktestStore = create<BacktestStore>((set) => ({
  currency: "$",
  setCurrency: (currency) => set({ currency }),

  strategyCode: DEFAULT_STRATEGY,
  setStrategyCode: (code) => set({ strategyCode: code }),

  ticker: "AAPL",
  tickers: ["AAPL"],
  tickerWeights: {},
  setTicker: (ticker) => set({ ticker, tickers: [ticker] }),
  setTickers: (tickers) => set({ tickers, ticker: tickers[0] || "" }),
  setTickerWeights: (tickerWeights) => set({ tickerWeights }),

  startDate: "2020-01-01",
  endDate: "2024-01-01",
  setStartDate: (startDate) => set({ startDate }),
  setEndDate: (endDate) => set({ endDate }),

  config: {
    initial_capital: 100000,
    commission: 0.001,
    slippage: 0.0005,
    allocation_pct: 100,
    sizing_model: "all_in",
    sizing_params: {},
    commission_type: "percent",
    commission_value: 0.001,
    commission_tier_limit: 1000,
    commission_tier_value: 0.003,
    slippage_type: "percent",
    slippage_value: 0.0005,
    spread: 0.0,
    volume_limit_pct: null,
  },
  setConfig: (partial) =>
    set((state) => ({ config: { ...state.config, ...partial } })),

  taskId: null,
  setTaskId: (taskId) => set({ taskId }),
  isRunning: false,
  setIsRunning: (isRunning) => set({ isRunning }),
  runStep: "",
  setRunStep: (runStep) => set({ runStep }),
  error: null,
  setError: (error) => set({ error }),

  // Phase 4 defaults
  optimizationMode: "single",
  setOptimizationMode: (optimizationMode) => set({ optimizationMode }),

  paramGridRaw: {},
  setParamGridRaw: (paramGridRaw) => set({ paramGridRaw }),

  inSampleDays: 365,
  setInSampleDays: (inSampleDays) => set({ inSampleDays }),
  outOfSampleDays: 90,
  setOutOfSampleDays: (outOfSampleDays) => set({ outOfSampleDays }),
  wfaObjective: "sharpe_ratio",
  setWfaObjective: (wfaObjective) => set({ wfaObjective }),
  wfaWindowType: "rolling",
  setWfaWindowType: (wfaWindowType) => set({ wfaWindowType }),
  wfaAnchored: false,
  setWfaAnchored: (wfaAnchored) => set({ wfaAnchored }),
  wfaMaxCombinations: 200,
  setWfaMaxCombinations: (wfaMaxCombinations) => set({ wfaMaxCombinations }),
  wfaEstimate: null,
  setWfaEstimate: (wfaEstimate) => set({ wfaEstimate }),

  sweepResult: null,
  setSweepResult: (sweepResult) => set({ sweepResult }),
  wfaResult: null,
  setWfaResult: (wfaResult) => set({ wfaResult }),

  optimizationProgress: "",
  setOptimizationProgress: (optimizationProgress) => set({ optimizationProgress }),

  reset: () =>
    set({
      taskId: null,
      isRunning: false,
      runStep: "",
      error: null,
      sweepResult: null,
      wfaResult: null,
      optimizationProgress: "",
      wfaEstimate: null,
    }),
}));
