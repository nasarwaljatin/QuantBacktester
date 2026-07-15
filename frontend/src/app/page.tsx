// frontend/src/app/page.tsx
// Home page — Strategy editor, configuration, and run button
"use client";

import StrategyEditor from "@/components/StrategyEditor";
import TickerSearch from "@/components/TickerSearch";
import DateRangePicker from "@/components/DateRangePicker";
import BacktestConfig from "@/components/BacktestConfig";
import RunButton from "@/components/RunButton";
import { useBacktestStore } from "@/lib/store";

const STRATEGY_CARDS = [
  {
    name: "3/30 EMA Crossover",
    description: "Buy when 3 EMA crosses above 30 EMA, sell on cross below",
    icon: "📈",
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
  {
    name: "RSI Mean Reversion",
    description: "Buy when RSI drops below 30 (oversold), sell above 70 (overbought)",
    icon: "🔄",
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
  {
    name: "Bollinger Bands",
    description: "Buy below lower band, sell above upper band using 20-period bands",
    icon: "📊",
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
  {
    name: "MACD",
    description: "Buy when MACD crosses above signal line, sell on cross below",
    icon: "⚡",
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
];

export default function Home() {
  const setStrategyCode = useBacktestStore((s) => s.setStrategyCode);

  return (
    <main className="min-h-screen bg-grid-pattern">
      {/* Gradient orbs for visual flair */}
      <div className="fixed inset-0 pointer-events-none overflow-hidden">
        <div className="absolute -top-40 -right-40 w-96 h-96 rounded-full bg-cyan-500/10 blur-3xl animate-float" />
        <div className="absolute top-1/3 -left-40 w-80 h-80 rounded-full bg-blue-500/10 blur-3xl animate-float" style={{ animationDelay: "2s" }} />
        <div className="absolute -bottom-40 right-1/3 w-72 h-72 rounded-full bg-violet-500/8 blur-3xl animate-float" style={{ animationDelay: "4s" }} />
      </div>

      <div className="relative z-10 max-w-5xl mx-auto px-4 py-12">
        {/* Header */}
        <header className="text-center mb-12 animate-slide-up">
          <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-cyan-500/10 border border-cyan-500/20 mb-6">
            <div className="w-2 h-2 rounded-full bg-cyan-400 animate-pulse" />
            <span className="text-xs font-medium text-cyan-400">Algorithmic Trading Platform</span>
          </div>
          <h1 className="text-5xl md:text-6xl font-bold bg-gradient-to-r from-white via-cyan-200 to-blue-400 bg-clip-text text-transparent mb-4">
            QuantBacktester
          </h1>
          <p className="text-lg text-gray-400 max-w-2xl mx-auto">
            Write trading strategies in Python, backtest against real historical data,
            and analyze performance with interactive charts and risk metrics.
          </p>
        </header>

        {/* Strategy Editor */}
        <div className="space-y-6 animate-slide-up" style={{ animationDelay: "0.1s" }}>
          <StrategyEditor />

          {/* Configuration */}
          <div className="glass-card rounded-2xl p-6 space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <TickerSearch />
              <div className="md:col-span-2">
                <DateRangePicker />
              </div>
            </div>
            <BacktestConfig />
          </div>

          {/* Run Button */}
          <RunButton />
        </div>

        {/* Strategy Example Cards */}
        <div className="mt-16 animate-slide-up" style={{ animationDelay: "0.2s" }}>
          <div className="text-center mb-8">
            <h2 className="text-2xl font-bold text-white mb-2">Example Strategies</h2>
            <p className="text-sm text-gray-500">Click any card to load it into the editor</p>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {STRATEGY_CARDS.map((card) => (
              <button
                key={card.name}
                onClick={() => setStrategyCode(card.code)}
                className="group text-left glass-card rounded-xl p-5 hover:border-cyan-500/30 hover:shadow-lg hover:shadow-cyan-500/5 transition-all duration-300 hover:scale-[1.02] active:scale-[0.98]"
              >
                <div className="text-3xl mb-3">{card.icon}</div>
                <h3 className="text-sm font-semibold text-white group-hover:text-cyan-300 transition-colors mb-1.5">
                  {card.name}
                </h3>
                <p className="text-xs text-gray-500 leading-relaxed">{card.description}</p>
              </button>
            ))}
          </div>
        </div>

        {/* Footer */}
        <footer className="mt-20 text-center">
          <div className="h-px bg-gradient-to-r from-transparent via-gray-700 to-transparent mb-6" />
          <p className="text-xs text-gray-600">
            QuantBacktester · Built with FastAPI, Backtrader, Next.js, and Plotly.js
          </p>
        </footer>
      </div>
    </main>
  );
}
