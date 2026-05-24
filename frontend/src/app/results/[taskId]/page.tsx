// frontend/src/app/results/[taskId]/page.tsx
// Results page — displays backtest results with charts, metrics, trade log, Monte Carlo
"use client";

import { useParams, useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { getBacktestResult } from "@/lib/api";
import MetricsGrid from "@/components/MetricsGrid";
import EquityCurveChart from "@/components/EquityCurveChart";
import TradeLogTable from "@/components/TradeLogTable";
import MonteCarloChart from "@/components/MonteCarloChart";
import type { BacktestResponse } from "@/types/backtest";

function SkeletonBlock({ className }: { className?: string }) {
  return (
    <div className={`bg-gray-800/40 rounded-2xl border border-gray-700/50 animate-pulse ${className || ""}`}>
      <div className="p-6 space-y-4">
        <div className="h-4 bg-gray-700/50 rounded w-1/4" />
        <div className="h-48 bg-gray-700/30 rounded-xl" />
      </div>
    </div>
  );
}

export default function ResultsPage() {
  const params = useParams();
  const router = useRouter();
  const taskId = params.taskId as string;

  const { data, isLoading, error } = useQuery<BacktestResponse>({
    queryKey: ["backtest", taskId],
    queryFn: () => getBacktestResult(taskId),
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      if (status === "success" || status === "failed") return false;
      return 1500;
    },
  });

  if (isLoading) {
    return (
      <main className="min-h-screen bg-grid-pattern">
        <div className="max-w-6xl mx-auto px-4 py-8 space-y-6">
          <SkeletonBlock className="h-24" />
          <SkeletonBlock className="h-64" />
          <SkeletonBlock className="h-96" />
          <SkeletonBlock className="h-64" />
        </div>
      </main>
    );
  }

  if (error) {
    return (
      <main className="min-h-screen bg-grid-pattern flex items-center justify-center">
        <div className="glass-card rounded-2xl p-8 max-w-md text-center">
          <div className="text-4xl mb-4">⚠️</div>
          <h2 className="text-xl font-bold text-white mb-2">Error Loading Results</h2>
          <p className="text-sm text-gray-400 mb-6">{(error as Error).message}</p>
          <button onClick={() => router.push("/")} className="px-6 py-2.5 bg-cyan-500/20 text-cyan-400 rounded-xl hover:bg-cyan-500/30 transition-all text-sm font-medium">
            ← Back to Editor
          </button>
        </div>
      </main>
    );
  }

  if (!data || data.status === "pending" || data.status === "running") {
    return (
      <main className="min-h-screen bg-grid-pattern flex items-center justify-center">
        <div className="glass-card rounded-2xl p-12 text-center">
          <div className="w-16 h-16 border-4 border-cyan-400 border-t-transparent rounded-full animate-spin mx-auto mb-6" />
          <h2 className="text-xl font-bold text-white mb-2">Processing Backtest</h2>
          <p className="text-sm text-gray-400">{data?.step || "Running your strategy..."}</p>
        </div>
      </main>
    );
  }

  if (data.status === "failed") {
    return (
      <main className="min-h-screen bg-grid-pattern flex items-center justify-center">
        <div className="glass-card rounded-2xl p-8 max-w-md text-center">
          <div className="text-4xl mb-4">❌</div>
          <h2 className="text-xl font-bold text-white mb-2">Backtest Failed</h2>
          <p className="text-sm text-red-400 mb-6">{data.error || "Unknown error"}</p>
          <button onClick={() => router.push("/")} className="px-6 py-2.5 bg-cyan-500/20 text-cyan-400 rounded-xl hover:bg-cyan-500/30 transition-all text-sm font-medium">
            ← Back to Editor
          </button>
        </div>
      </main>
    );
  }

  // Success state
  const ticker = data.ticker || "—";
  const startDate = data.start_date || "";
  const endDate = data.end_date || "";

  return (
    <main className="min-h-screen bg-grid-pattern">
      {/* Gradient orbs */}
      <div className="fixed inset-0 pointer-events-none overflow-hidden">
        <div className="absolute -top-40 -right-40 w-96 h-96 rounded-full bg-cyan-500/8 blur-3xl animate-float" />
        <div className="absolute bottom-0 -left-40 w-80 h-80 rounded-full bg-blue-500/8 blur-3xl animate-float" style={{ animationDelay: "3s" }} />
      </div>

      <div className="relative z-10 max-w-6xl mx-auto px-4 py-8">
        {/* Header */}
        <div className="flex items-center justify-between mb-8 animate-slide-up">
          <div className="flex items-center gap-4">
            <button
              onClick={() => router.push("/")}
              className="flex items-center gap-2 px-4 py-2 rounded-xl bg-gray-800/60 border border-gray-700/50 text-sm text-gray-300 hover:text-white hover:border-gray-600 transition-all group"
            >
              <svg className="w-4 h-4 group-hover:-translate-x-0.5 transition-transform" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
              </svg>
              Back
            </button>
            <div>
              <h1 className="text-2xl font-bold text-white">
                Results: <span className="text-cyan-400">{ticker}</span>
              </h1>
              <p className="text-sm text-gray-500">{startDate} — {endDate}</p>
            </div>
          </div>
          <div className="hidden sm:flex items-center gap-2 px-3 py-1.5 rounded-full bg-emerald-500/10 border border-emerald-500/20">
            <div className="w-2 h-2 rounded-full bg-emerald-400" />
            <span className="text-xs font-medium text-emerald-400">Complete</span>
          </div>
        </div>

        <div className="space-y-6">
          {/* Metrics */}
          {data.metrics && (
            <div className="animate-slide-up" style={{ animationDelay: "0.05s" }}>
              <MetricsGrid metrics={data.metrics} />
            </div>
          )}

          {/* Equity Curve */}
          {data.equity_curve && data.equity_curve.length > 0 && (
            <div className="animate-slide-up" style={{ animationDelay: "0.1s" }}>
              <EquityCurveChart
                equityCurve={data.equity_curve}
                benchmarkCurve={data.benchmark_curve || []}
              />
            </div>
          )}

          {/* Trade Log */}
          {data.trades && data.trades.length > 0 && (
            <div className="animate-slide-up" style={{ animationDelay: "0.15s" }}>
              <TradeLogTable trades={data.trades} />
            </div>
          )}

          {/* Monte Carlo */}
          {data.monte_carlo && data.monte_carlo.paths && data.monte_carlo.paths.length > 0 && (
            <div className="animate-slide-up" style={{ animationDelay: "0.2s" }}>
              <MonteCarloChart
                monteCarlo={data.monte_carlo}
                actualCurve={data.equity_curve || []}
              />
            </div>
          )}
        </div>

        {/* Footer */}
        <footer className="mt-16 text-center">
          <div className="h-px bg-gradient-to-r from-transparent via-gray-700 to-transparent mb-6" />
          <p className="text-xs text-gray-600">
            QuantBacktester · Task ID: {taskId}
          </p>
        </footer>
      </div>
    </main>
  );
}
