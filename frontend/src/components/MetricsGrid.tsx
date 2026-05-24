// frontend/src/components/MetricsGrid.tsx
"use client";

import type { PerformanceMetrics } from "@/types/backtest";

interface MetricCardProps {
  name: string;
  value: string;
  isPositive: boolean;
  tooltip: string;
}

function MetricCard({ name, value, isPositive, tooltip }: MetricCardProps) {
  return (
    <div className="group relative bg-gray-800/40 backdrop-blur-sm rounded-xl border border-gray-700/50 p-4 hover:border-cyan-500/30 transition-all duration-300 hover:shadow-lg hover:shadow-cyan-500/5">
      <p className="text-xs font-medium text-gray-400 mb-1.5 uppercase tracking-wider">{name}</p>
      <p className={`text-2xl font-bold ${isPositive ? "text-emerald-400" : "text-red-400"}`}>
        {value}
      </p>
      <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-3 py-2 bg-gray-900/95 border border-gray-600/50 rounded-lg text-xs text-gray-300 opacity-0 group-hover:opacity-100 transition-opacity duration-200 pointer-events-none whitespace-nowrap z-10 backdrop-blur-sm shadow-xl">
        {tooltip}
      </div>
    </div>
  );
}

interface MetricsGridProps {
  metrics: PerformanceMetrics;
}

export default function MetricsGrid({ metrics }: MetricsGridProps) {
  const cards: MetricCardProps[] = [
    {
      name: "Total Return",
      value: `${(metrics.total_return * 100).toFixed(2)}%`,
      isPositive: metrics.total_return >= 0,
      tooltip: "Total percentage gain/loss from start to end of the backtest period",
    },
    {
      name: "Annualized Return",
      value: `${(metrics.annualized_return * 100).toFixed(2)}%`,
      isPositive: metrics.annualized_return >= 0,
      tooltip: "Compound annual growth rate (CAGR) of the portfolio",
    },
    {
      name: "Sharpe Ratio",
      value: metrics.sharpe_ratio.toFixed(2),
      isPositive: metrics.sharpe_ratio >= 1,
      tooltip: "Risk-adjusted return. Above 1 is good, above 2 is excellent",
    },
    {
      name: "Sortino Ratio",
      value: metrics.sortino_ratio.toFixed(2),
      isPositive: metrics.sortino_ratio >= 1,
      tooltip: "Like Sharpe but only penalizes downside volatility",
    },
    {
      name: "Max Drawdown",
      value: `${(metrics.max_drawdown * 100).toFixed(2)}%`,
      isPositive: metrics.max_drawdown > -0.2,
      tooltip: "Largest peak-to-trough decline during the backtest",
    },
    {
      name: "Calmar Ratio",
      value: metrics.calmar_ratio.toFixed(2),
      isPositive: metrics.calmar_ratio >= 1,
      tooltip: "Annualized return divided by maximum drawdown",
    },
    {
      name: "Win Rate",
      value: `${(metrics.win_rate * 100).toFixed(1)}%`,
      isPositive: metrics.win_rate >= 0.5,
      tooltip: "Percentage of trades that were profitable",
    },
    {
      name: "Profit Factor",
      value: metrics.profit_factor.toFixed(2),
      isPositive: metrics.profit_factor >= 1.5,
      tooltip: "Gross profit divided by gross loss. Above 1.5 is good",
    },
    {
      name: "Total Trades",
      value: metrics.total_trades.toString(),
      isPositive: true,
      tooltip: "Total number of completed round-trip trades",
    },
    {
      name: "Avg Holding Period",
      value: `${metrics.avg_holding_period.toFixed(1)}d`,
      isPositive: true,
      tooltip: "Average number of calendar days a position was held",
    },
  ];

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <div className="w-2 h-2 rounded-full bg-emerald-400" />
        <h3 className="text-lg font-semibold text-white">Performance Metrics</h3>
      </div>
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-5 gap-3">
        {cards.map((card) => (
          <MetricCard key={card.name} {...card} />
        ))}
      </div>
    </div>
  );
}
