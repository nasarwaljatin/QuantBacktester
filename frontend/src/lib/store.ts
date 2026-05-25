// frontend/src/lib/store.ts
// Zustand store for client-side state management

import { create } from "zustand";
import type { BacktestConfig } from "@/types/backtest";

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

interface BacktestStore {
  // Currency selection
  currency: string;
  setCurrency: (currency: string) => void;

  // Strategy editor
  strategyCode: string;
  setStrategyCode: (code: string) => void;

  // Ticker selection
  ticker: string;
  setTicker: (ticker: string) => void;

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

  // Reset
  reset: () => void;
}

export const useBacktestStore = create<BacktestStore>((set) => ({
  currency: "$",
  setCurrency: (currency) => set({ currency }),

  strategyCode: DEFAULT_STRATEGY,
  setStrategyCode: (code) => set({ strategyCode: code }),

  ticker: "AAPL",
  setTicker: (ticker) => set({ ticker }),

  startDate: "2020-01-01",
  endDate: "2024-01-01",
  setStartDate: (startDate) => set({ startDate }),
  setEndDate: (endDate) => set({ endDate }),

  config: {
    initial_capital: 100000,
    commission: 0.001,
    slippage: 0.0005,
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

  reset: () =>
    set({
      taskId: null,
      isRunning: false,
      runStep: "",
      error: null,
    }),
}));
