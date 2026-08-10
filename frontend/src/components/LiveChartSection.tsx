// frontend/src/components/LiveChartSection.tsx
"use client";

import { useQuery } from "@tanstack/react-query";
import { getOhlcvData } from "@/lib/api";
import { useBacktestStore } from "@/lib/store";
import TradingChart from "./TradingChart";

export default function LiveChartSection() {
  const ticker = useBacktestStore((s) => s.ticker);

  // Compute 90-day window ending today
  const todayStr = new Date().toISOString().slice(0, 10);
  const ninetyDaysAgoStr = new Date(Date.now() - 90 * 24 * 60 * 60 * 1000)
    .toISOString()
    .slice(0, 10);

  // Poll price bars every 10 seconds (10000ms)
  const { data, isLoading, error } = useQuery({
    queryKey: ["live-ohlcv", ticker],
    queryFn: () => getOhlcvData(ticker, ninetyDaysAgoStr, todayStr),
    refetchInterval: 10000, // 10s poll
    enabled: !!ticker,
  });

  return (
    <div className="glass-card rounded-2xl p-6 transition-colors duration-300">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <div className="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-ping" />
          <h3 className="text-sm font-semibold text-slate-900 dark:text-white uppercase tracking-wider">
            Live Reference Chart: <span className="text-cyan-600 dark:text-cyan-400 font-bold">{ticker}</span>
          </h3>
        </div>
        <span className="text-[10px] text-gray-500 font-medium px-2 py-0.5 rounded bg-gray-100 dark:bg-gray-800 border border-gray-200 dark:border-gray-700/50">
          Refreshes every 10s · delayed feed
        </span>
      </div>

      {isLoading ? (
        <div className="h-[250px] flex items-center justify-center">
          <div className="flex items-center gap-3">
            <div className="w-5 h-5 border-2 border-cyan-400 border-t-transparent rounded-full animate-spin" />
            <span className="text-gray-400 text-sm">Loading market feed...</span>
          </div>
        </div>
      ) : error ? (
        <div className="h-[250px] flex flex-col items-center justify-center text-center">
          <span className="text-2xl mb-2">⚠️</span>
          <p className="text-xs text-red-500">Failed to load price history for {ticker}.</p>
          <p className="text-[10px] text-gray-400 mt-1">Verify that the ticker symbol is correct.</p>
        </div>
      ) : data?.data && data.data.length > 0 ? (
        <TradingChart ohlcv={data.data} height={250} showLiveIndicator={true} />
      ) : (
        <div className="h-[250px] flex items-center justify-center text-center text-gray-500 text-xs">
          No market data available for {ticker} in the last 90 days.
        </div>
      )}
    </div>
  );
}
