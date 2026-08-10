// frontend/src/app/results/[taskId]/page.tsx
// Results page — displays backtest results (single, sweep, or walk-forward)
"use client";

import { useParams, useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { getBacktestResult } from "@/lib/api";
import MetricsGrid from "@/components/MetricsGrid";
import EquityCurveChart from "@/components/EquityCurveChart";
import TradeLogTable from "@/components/TradeLogTable";
import MonteCarloChart from "@/components/MonteCarloChart";
import SweepHeatmap from "@/components/SweepHeatmap";
import WFAResultsTable from "@/components/WFAResultsTable";
import { useBacktestStore } from "@/lib/store";
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

  // Cached optimization results from store (set by RunButton before navigation)
  const sweepResultCached = useBacktestStore((s) => s.sweepResult);
  const wfaResultCached = useBacktestStore((s) => s.wfaResult);
  const initialCapital = useBacktestStore((s) => s.config.initial_capital);

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
    const progress = (data as any)?.progress;
    const runType = (data as any)?.run_type;
    const isOpt = runType === "sweep" || runType === "walk_forward";
    return (
      <main className="min-h-screen bg-grid-pattern flex items-center justify-center">
        <div className="glass-card rounded-2xl p-12 text-center max-w-md">
          <div className={`w-16 h-16 border-4 border-t-transparent rounded-full animate-spin mx-auto mb-6 ${isOpt ? "border-indigo-400" : "border-cyan-400"}`} />
          <h2 className="text-xl font-bold text-white mb-2">
            {runType === "sweep" ? "Running Parameter Sweep" : runType === "walk_forward" ? "Running Walk-Forward Analysis" : "Processing Backtest"}
          </h2>
          {progress && (
            <div className="mt-3 mb-1">
              <div className="text-sm font-semibold text-indigo-300">{progress}</div>
            </div>
          )}
          <p className="text-sm text-gray-400">{(data as any)?.step || "Running your strategy..."}</p>
        </div>
      </main>
    );
  }

  if (data.status === "failed") {
    return (
      <main className="min-h-screen bg-grid-pattern flex items-center justify-center">
        <div className="glass-card rounded-2xl p-8 max-w-md text-center">
          <div className="text-4xl mb-4">❌</div>
          <h2 className="text-xl font-bold text-white mb-2">Run Failed</h2>
          <p className="text-sm text-red-400 mb-6">{data.error || "Unknown error"}</p>
          <button onClick={() => router.push("/")} className="px-6 py-2.5 bg-cyan-500/20 text-cyan-400 rounded-xl hover:bg-cyan-500/30 transition-all text-sm font-medium">
            ← Back to Editor
          </button>
        </div>
      </main>
    );
  }

  // ─── Determine run type ────────────────────────────────────────────────
  const runType = (data as any).run_type as string | undefined;
  const isSweep = runType === "sweep";
  const isWFA = runType === "walk_forward";

  // For sweep/WFA, prefer the cached store result (has full data)
  const sweepData = isSweep ? (sweepResultCached ?? (data as any)) : null;
  const wfaData = isWFA ? (wfaResultCached ?? (data as any)) : null;

  const ticker = (data as any).ticker || (data as any).tickers?.[0] || "—";
  const startDate = data.start_date || "";
  const endDate = data.end_date || "";

  const badgeLabel = isSweep ? "Sweep" : isWFA ? "Walk-Forward" : "Complete";
  const badgeColor = isSweep
    ? "bg-violet-500/10 border-violet-500/20 text-violet-400"
    : isWFA
    ? "bg-indigo-500/10 border-indigo-500/20 text-indigo-400"
    : "bg-emerald-500/10 border-emerald-500/20 text-emerald-400";
  const dotColor = isSweep ? "bg-violet-400" : isWFA ? "bg-indigo-400" : "bg-emerald-400";

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
                {isSweep ? "Parameter Sweep: " : isWFA ? "Walk-Forward: " : "Results: "}
                <span className="text-cyan-400">{ticker}</span>
              </h1>
              <p className="text-sm text-gray-500">{startDate} — {endDate}</p>
            </div>
          </div>
          <div className={`hidden sm:flex items-center gap-2 px-3 py-1.5 rounded-full border ${badgeColor}`}>
            <div className={`w-2 h-2 rounded-full ${dotColor}`} />
            <span className="text-xs font-medium">{badgeLabel}</span>
          </div>
        </div>

        <div className="space-y-6">
          {/* ─── Single Backtest Results ─── */}
          {!isSweep && !isWFA && (
            <>
              {data.metrics && (
                <div className="animate-slide-up" style={{ animationDelay: "0.05s" }}>
                  <MetricsGrid metrics={data.metrics} />
                </div>
              )}
              {data.equity_curve && data.equity_curve.length > 0 && (
                <div className="animate-slide-up" style={{ animationDelay: "0.1s" }}>
                  <EquityCurveChart
                    equityCurve={data.equity_curve}
                    benchmarkCurve={data.benchmark_curve || []}
                  />
                </div>
              )}
              {data.trades && data.trades.length > 0 && (
                <div className="animate-slide-up" style={{ animationDelay: "0.15s" }}>
                  <TradeLogTable trades={data.trades} />
                </div>
              )}
              {data.monte_carlo && data.monte_carlo.paths && data.monte_carlo.paths.length > 0 && (
                <div className="animate-slide-up" style={{ animationDelay: "0.2s" }}>
                  <MonteCarloChart
                    monteCarlo={data.monte_carlo}
                    actualCurve={data.equity_curve || []}
                  />
                </div>
              )}
            </>
          )}

          {/* ─── Parameter Sweep Results ─── */}
          {isSweep && sweepData && (
            <div className="glass-card rounded-2xl p-6 animate-slide-up" style={{ animationDelay: "0.05s" }}>
              <div className="flex items-center gap-2 mb-6">
                <span className="text-xl">🔍</span>
                <h2 className="text-lg font-bold text-white">Parameter Sweep Results</h2>
              </div>
              <SweepHeatmap
                sweepResults={sweepData.sweep_results ?? []}
                bestParams={sweepData.best_params ?? {}}
                paramGrid={sweepData.param_grid ?? {}}
                objective={sweepData.objective ?? "sharpe_ratio"}
                totalCombinations={sweepData.total_combinations ?? 0}
              />
            </div>
          )}

          {/* ─── Walk-Forward Analysis Results ─── */}
          {isWFA && wfaData && (
            <div className="glass-card rounded-2xl p-6 animate-slide-up" style={{ animationDelay: "0.05s" }}>
              <div className="flex items-center gap-2 mb-6">
                <span className="text-xl">📊</span>
                <h2 className="text-lg font-bold text-white">Walk-Forward Analysis Results</h2>
              </div>
              <WFAResultsTable
                windows={wfaData.wfa_windows ?? []}
                combinedOosEquity={wfaData.combined_oos_equity ?? []}
                aggregateOosMetrics={wfaData.aggregate_oos_metrics ?? {}}
                totalWindows={wfaData.total_windows ?? 0}
                inSampleDays={wfaData.in_sample_days ?? 365}
                outOfSampleDays={wfaData.out_of_sample_days ?? 90}
                windowType={wfaData.window_type ?? "rolling"}
                anchored={wfaData.anchored ?? false}
                objective={wfaData.objective ?? "sharpe_ratio"}
                initialCapital={initialCapital}
                aggregateEfficiencyRatio={wfaData.aggregate_efficiency_ratio ?? null}
                paramStability={wfaData.param_stability ?? {}}
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
