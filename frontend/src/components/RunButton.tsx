// frontend/src/components/RunButton.tsx
"use client";

import { useRouter } from "next/navigation";
import { useBacktestStore } from "@/lib/store";
import { submitBacktest, getBacktestResult } from "@/lib/api";

export default function RunButton() {
  const router = useRouter();
  const {
    strategyCode, ticker, tickers, tickerWeights, startDate, endDate, config,
    isRunning, setIsRunning, runStep, setRunStep,
    error, setError, setTaskId,
  } = useBacktestStore();

  const handleRun = async () => {
    setError(null);
    setIsRunning(true);
    setRunStep("Submitting backtest...");

    // Filter weights: only pass them if at least one weight is > 0
    const activeWeights = Object.keys(tickerWeights).some(k => tickerWeights[k] > 0)
      ? tickerWeights
      : undefined;

    try {
      // Submit backtest
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

      // Poll for results
      let attempts = 0;
      const maxAttempts = 200; // ~5 minutes at 1.5s intervals

      while (attempts < maxAttempts) {
        await new Promise((resolve) => setTimeout(resolve, 1500));
        attempts++;

        const result = await getBacktestResult(task_id);

        if (result.status === "success") {
          setRunStep("Done!");
          setIsRunning(false);
          router.push(`/results/${task_id}`);
          return;
        }

        if (result.status === "failed") {
          throw new Error(result.error || "Backtest failed");
        }

        // Update step display
        if (result.step) {
          setRunStep(result.step);
        } else if (result.status === "running") {
          setRunStep("Running backtest...");
        } else {
          setRunStep("Processing...");
        }
      }

      throw new Error("Backtest timed out after 5 minutes");
    } catch (err) {
      setError(err instanceof Error ? err.message : "An unexpected error occurred");
      setIsRunning(false);
      setRunStep("");
    }
  };

  return (
    <div className="space-y-3">
      <button
        id="run-backtest-button"
        onClick={handleRun}
        disabled={isRunning}
        className={`
          w-full py-3.5 px-6 rounded-xl font-semibold text-sm transition-all duration-300 
          flex items-center justify-center gap-3
          ${isRunning
            ? "bg-gray-700/50 text-gray-400 cursor-not-allowed border border-gray-600/30"
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
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.828 14.828a4 4 0 01-5.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <span>Run Backtest</span>
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7l5 5m0 0l-5 5m5-5H6" />
            </svg>
          </>
        )}
      </button>

      {error && (
        <div className="bg-red-500/10 border border-red-500/30 rounded-xl px-4 py-3 flex items-start gap-3">
          <svg className="w-5 h-5 text-red-400 shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <p className="text-sm text-red-300">{error}</p>
        </div>
      )}
    </div>
  );
}
