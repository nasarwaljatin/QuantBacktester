// frontend/src/components/StrategyTemplates.tsx
"use client";

import { useState } from "react";
import { useBacktestStore } from "@/lib/store";

const TEMPLATES: Record<string, { name: string; code: string }> = {
  sma_crossover: {
    name: "SMA Crossover",
    code: `class UserStrategy(bt.Strategy):
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
`,
  },
  ema_crossover: {
    name: "EMA Crossover (3/30)",
    code: `class UserStrategy(bt.Strategy):
    params = dict(fast=3, slow=30)

    def __init__(self):
        self.fast_ma = bt.ind.EMA(period=self.p.fast)
        self.slow_ma = bt.ind.EMA(period=self.p.slow)
        self.crossover = bt.ind.CrossOver(self.fast_ma, self.slow_ma)

    def next(self):
        if not self.position:
            if self.crossover > 0:
                self.buy()
        elif self.crossover < 0:
            self.close()
`,
  },
  rsi_mean_reversion: {
    name: "RSI Mean Reversion",
    code: `class UserStrategy(bt.Strategy):
    params = dict(rsi_period=14, oversold=30, overbought=70)

    def __init__(self):
        self.rsi = bt.ind.RSI(period=self.p.rsi_period)

    def next(self):
        if not self.position:
            if self.rsi < self.p.oversold:
                self.buy()
        else:
            if self.rsi > self.p.overbought:
                self.close()
`,
  },
  bollinger_bands: {
    name: "Bollinger Bands",
    code: `class UserStrategy(bt.Strategy):
    params = dict(period=20, devfactor=2.0)

    def __init__(self):
        self.bband = bt.ind.BollingerBands(period=self.p.period, devfactor=self.p.devfactor)

    def next(self):
        if not self.position:
            if self.data.close[0] < self.bband.lines.bot[0]:
                self.buy()
        else:
            if self.data.close[0] > self.bband.lines.top[0]:
                self.close()
`,
  },
  macd: {
    name: "MACD",
    code: `class UserStrategy(bt.Strategy):
    params = dict(fast=12, slow=26, signal=9)

    def __init__(self):
        self.macd = bt.ind.MACD(
            period_me1=self.p.fast,
            period_me2=self.p.slow,
            period_signal=self.p.signal,
        )
        self.crossover = bt.ind.CrossOver(self.macd.macd, self.macd.signal)

    def next(self):
        if not self.position:
            if self.crossover > 0:
                self.buy()
        elif self.crossover < 0:
            self.close()
`,
  },
};

export default function StrategyTemplates() {
  const setStrategyCode = useBacktestStore((s) => s.setStrategyCode);
  const [selected, setSelected] = useState("sma_crossover");

  const handleChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const key = e.target.value;
    setSelected(key);
    if (TEMPLATES[key]) {
      setStrategyCode(TEMPLATES[key].code);
    }
  };

  return (
    <div className="flex items-center gap-3">
      <label
        htmlFor="strategy-template-select"
        className="text-sm font-medium text-gray-300"
      >
        Template:
      </label>
      <select
        id="strategy-template-select"
        value={selected}
        onChange={handleChange}
        className="bg-gray-800/80 border border-gray-600/50 rounded-lg px-3 py-2 text-sm text-gray-200 focus:outline-none focus:ring-2 focus:ring-cyan-500/50 focus:border-cyan-500/50 backdrop-blur-sm transition-all"
      >
        {Object.entries(TEMPLATES).map(([key, tpl]) => (
          <option key={key} value={key}>
            {tpl.name}
          </option>
        ))}
      </select>
    </div>
  );
}
