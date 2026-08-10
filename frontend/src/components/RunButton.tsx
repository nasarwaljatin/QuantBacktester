// frontend/src/components/RunButton.tsx
"use client";

import { useRouter } from "next/navigation";
import { useBacktestStore } from "@/lib/store";
import {
  submitBacktest,
  getBacktestResult,
  submitSweep,
  getSweepResult,
  submitWalkForward,
  getWalkForwardResult,
} from "@/lib/api";
import { buildParamGrid } from "./OptimizationConfig";

export default function RunButton() {
  const router = useRouter();
  const {
    strategyCode,
    ticker,
    tickers,
    tickerWeights,
    startDate,
    endDate,
    config,
    optimizationMode,
    paramGridRaw,
    inSampleDays,
    outOfSampleDays,
    wfaObjective,
    wfaWindowType,
    wfaAnchored,
    wfaMaxCombinations,
    wfaEstimate,
    isRunning,
    setIsRunning,
    runStep,
    setRunStep,
    error,
    setError,
    setTaskId,
    setSweepResult,
    setWfaResult,
    setOptimizationProgress,
  } = useBacktestStore();

  // ─── Label for button ───────────────────────────────────────────────────
  const modeLabel =
    optimizationMode === "sweep"
      ? "Run Parameter Sweep"
      : optimizationMode === "walk_forward"
      ? "Run Walk-Forward Analysis"
      : "Run Backtest";

  // ─── Single backtest ────────────────────────────────────────────────────
  const handleSingle = async () => {
    setRunStep("Submitting backtest...");
    const activeWeights = Object.keys(tickerWeights).some((k) => tickerWeights[k] > 0)
      ? tickerWeights
      : undefined;

    const { task_id } = await submitBacktest({
      strategy_code: strategyCode,
      ticker,
      tickers,
      ticker_weights: activeWeights,
      start_date: startDate,
      end_date: endDate,
      config,
    });
    setTaskId(task_id);
    setRunStep("Fetching data...");

    for (let i = 0; i < 200; i++) {
      await new Promise((r) => setTimeout(r, 1500));
      const result = await getBacktestResult(task_id);
      if (result.status === "success") {
        setRunStep("Done!");
        setIsRunning(false);
        router.push(`/results/${task_id}`);
        return;
      }
      if (result.status === "failed") throw new Error(result.error || "Backtest failed");
      setRunStep(result.step || (result.status === "running" ? "Running backtest..." : "Processing..."));
    }
    throw new Error("Backtest timed out after 5 minutes");
  };

  // ─── Parameter sweep ────────────────────────────────────────────────────
  const handleSweep = async () => {
    const paramGrid = buildParamGrid(paramGridRaw);
    if (Object.keys(paramGrid).length === 0) {
      throw new Error(
        "No parameter values specified. Fill in comma-separated values in the Parameter Grid above."
      );
    }
    setRunStep("Submitting sweep...");
    const { task_id } = await submitSweep({
      strategy_code: strategyCode,
      tickers,
      start_date: startDate,
      end_date: endDate,
      param_grid: paramGrid,
      config,
      objective: wfaObjective,
    });
    setTaskId(task_id);
    setRunStep("Running sweep...");

    for (let i = 0; i < 600; i++) {
      await new Promise((r) => setTimeout(r, 2000));
      const result = await getSweepResult(task_id);
      if (result.progress) setOptimizationProgress(result.progress);
      if (result.status === "success") {
        setSweepResult(result);
        setRunStep("Done!");
        setIsRunning(false);
        router.push(`/results/${task_id}`);
        return;
      }
      if (result.status === "failed") throw new Error(result.error || "Sweep failed");
      setRunStep(`Sweep running… ${result.progress ?? ""}`);
    }
    throw new Error("Sweep timed out after 20 minutes");
  };

  // ─── Walk-forward analysis ───────────────────────────────────────────────
  const handleWFA = async () => {
    const paramGrid = buildParamGrid(paramGridRaw);
    if (Object.keys(paramGrid).length === 0) {
      throw new Error(
        "No parameter values specified. Fill in comma-separated values in the Parameter Grid above."
      );
    }
    setRunStep("Submitting walk-forward...");
    const { task_id } = await submitWalkForward({
      strategy_code: strategyCode,
      tickers,
      start_date: startDate,
      end_date: endDate,
      param_grid: paramGrid,
      config,
      in_sample_days: inSampleDays,
      out_of_sample_days: outOfSampleDays,
      objective: wfaObjective,
      window_type: wfaWindowType,
      anchored: wfaAnchored,
      max_combinations: wfaMaxCombinations,
    });
    setTaskId(task_id);
    setRunStep("Running walk-forward windows...");

    for (let i = 0; i < 600; i++) {
      await new Promise((r) => setTimeout(r, 2000));
      const result = await getWalkForwardResult(task_id);
      if (result.progress) setOptimizationProgress(result.progress);
      if (result.status === "success") {
        setWfaResult(result);
        setRunStep("Done!");
        setIsRunning(false);
        router.push(`/results/${task_id}`);
        return;
      }
      if (result.status === "failed") throw new Error(result.error || "Walk-forward analysis failed");
      setRunStep(`Walk-forward running… ${result.progress ?? ""}`);
    }
    throw new Error("Walk-forward timed out after 20 minutes");
  };

  // ─── Main handler ────────────────────────────────────────────────────────
  const handleRun = async () => {
    setError(null);
    setIsRunning(true);
    setSweepResult(null);
    setWfaResult(null);
    setOptimizationProgress("");

    try {
      if (optimizationMode === "sweep") {
        await handleSweep();
      } else if (optimizationMode === "walk_forward") {
        await handleWFA();
      } else {
        await handleSingle();
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "An unexpected error occurred");
      setIsRunning(false);
      setRunStep("");
    }
  };

  // WFA is disabled when the pre-flight estimate says infeasible
  const wfaBlocked =
    optimizationMode === "walk_forward" &&
    wfaEstimate !== null &&
    !wfaEstimate.feasible;

  return (
    <div className="space-y-3">
      <button
        id="run-backtest-button"
        onClick={handleRun}
        disabled={isRunning || wfaBlocked}
        className={`
          w-full py-3.5 px-6 rounded-xl font-semibold text-sm transition-all duration-300 
          flex items-center justify-center gap-3
          ${
            isRunning
              ? "bg-gray-700/50 text-gray-400 cursor-not-allowed border border-gray-600/30"
              : optimizationMode !== "single"
              ? "bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-500 hover:to-violet-500 text-white shadow-lg shadow-indigo-500/25 hover:shadow-indigo-500/40 hover:scale-[1.02] active:scale-[0.98]"
              : "bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-white shadow-lg shadow-cyan-500/25 hover:shadow-cyan-500/40 hover:scale-[1.02] active:scale-[0.98]"
          }
        `}
      >
        {isRunning ? (
          <>
            <div className="w-5 h-5 border-2 border-gray-400 border-t-transparent rounded-full animate-spin" />
            <span>{runStep}</span>
          </>
        ) : (
          <>
            {optimizationMode === "sweep" && (
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                  d="M4 6h16M4 10h16M4 14h8M4 18h8" />
              </svg>
            )}
            {optimizationMode === "walk_forward" && (
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                  d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
            )}
            {optimizationMode === "single" && (
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                  d="M14.828 14.828a4 4 0 01-5.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            )}
            <span>{modeLabel}</span>
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7l5 5m0 0l-5 5m5-5H6" />
            </svg>
          </>
        )}
      </button>

      {error && (
        <div className="bg-red-500/10 border border-red-500/30 rounded-xl px-4 py-3 flex items-start gap-3">
          <svg className="w-5 h-5 text-red-400 shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
              d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <p className="text-sm text-red-300">{error}</p>
        </div>
      )}
    </div>
  );
}
