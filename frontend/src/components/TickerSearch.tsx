// frontend/src/components/TickerSearch.tsx
"use client";

import { useState, useEffect, useRef } from "react";
import { useBacktestStore } from "@/lib/store";
import { searchTickers } from "@/lib/api";
import type { TickerResult } from "@/types/backtest";

export default function TickerSearch() {
  const tickers = useBacktestStore((s) => s.tickers);
  const setTickers = useBacktestStore((s) => s.setTickers);
  const tickerWeights = useBacktestStore((s) => s.tickerWeights);
  const setTickerWeights = useBacktestStore((s) => s.setTickerWeights);

  const [query, setQuery] = useState("");
  const [results, setResults] = useState<TickerResult[]>([]);
  const [isOpen, setIsOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const wrapperRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (wrapperRef.current && !wrapperRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  useEffect(() => {
    if (query.length < 1) {
      setResults([]);
      return;
    }

    const timer = setTimeout(async () => {
      setIsLoading(true);
      try {
        const data = await searchTickers(query);
        setResults(data.results || []);
      } catch {
        setResults([]);
      } finally {
        setIsLoading(false);
      }
    }, 300);

    return () => clearTimeout(timer);
  }, [query]);

  const handleSelect = (result: TickerResult) => {
    const symbol = result.symbol.toUpperCase();
    if (!tickers.includes(symbol)) {
      setTickers([...tickers, symbol]);
      setTickerWeights({ ...tickerWeights, [symbol]: 0 });
    }
    setQuery("");
    setIsOpen(false);
  };

  const handleRemove = (symbol: string) => {
    setTickers(tickers.filter((t) => t !== symbol));
    const nextWeights = { ...tickerWeights };
    delete nextWeights[symbol];
    setTickerWeights(nextWeights);
  };

  const handleWeightChange = (symbol: string, value: string) => {
    const num = parseFloat(value) || 0;
    setTickerWeights({ ...tickerWeights, [symbol]: num });
  };

  const totalWeight = Object.values(tickerWeights).reduce((sum, w) => sum + w, 0);
  const showWeightWarning = totalWeight > 0 && Math.abs(totalWeight - 100) > 0.01;

  return (
    <div ref={wrapperRef} className="space-y-4">
      <div className="relative">
        <label htmlFor="ticker-search" className="block text-xs font-medium text-gray-400 mb-1.5">
          Search Tickers
        </label>
        <div className="relative">
          <svg className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
          <input
            id="ticker-search"
            type="text"
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
              setIsOpen(true);
            }}
            onFocus={() => setIsOpen(true)}
            placeholder="Search ticker (e.g. AAPL, MSFT)..."
            className="w-full bg-gray-800/80 border border-gray-600/50 rounded-lg pl-10 pr-4 py-2.5 text-sm text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-cyan-500/50 focus:border-cyan-500/50 backdrop-blur-sm transition-all"
          />
          {isLoading && (
            <div className="absolute right-3 top-1/2 -translate-y-1/2">
              <div className="w-4 h-4 border-2 border-cyan-400 border-t-transparent rounded-full animate-spin" />
            </div>
          )}
        </div>

        {isOpen && results.length > 0 && (
          <div className="absolute z-50 w-full mt-1 bg-gray-800/95 backdrop-blur-xl border border-gray-600/50 rounded-xl shadow-2xl shadow-black/50 max-h-60 overflow-auto">
            {results.map((r) => (
              <button
                key={r.symbol}
                onClick={() => handleSelect(r)}
                className="w-full px-4 py-2.5 text-left hover:bg-cyan-500/10 transition-colors flex items-center justify-between group"
              >
                <div>
                  <span className="text-sm font-semibold text-cyan-400 group-hover:text-cyan-300">{r.symbol}</span>
                  <span className="text-xs text-gray-400 ml-2">{r.name}</span>
                </div>
                <span className="text-[10px] px-2 py-0.5 rounded-full bg-gray-700/50 text-gray-400">{r.exchange}</span>
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Selected Tickers & Weights List */}
      {tickers.length > 0 && (
        <div className="bg-gray-800/30 rounded-xl p-4 border border-gray-700/40 space-y-3">
          <div className="flex justify-between items-center text-xs font-semibold text-gray-400 pb-2 border-b border-gray-850">
            <span>Asset Portfolio</span>
            <span>Weight (%)</span>
          </div>
          <div className="space-y-2.5 max-h-48 overflow-y-auto pr-1">
            {tickers.map((symbol) => (
              <div key={symbol} className="flex justify-between items-center gap-3">
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={() => handleRemove(symbol)}
                    className="text-gray-500 hover:text-red-400 transition-colors text-xs p-1"
                    title="Remove ticker"
                  >
                    ✕
                  </button>
                  <span className="text-sm font-bold text-white">{symbol}</span>
                </div>
                <input
                  type="number"
                  min="0"
                  max="100"
                  value={tickerWeights[symbol] || 0}
                  onChange={(e) => handleWeightChange(symbol, e.target.value)}
                  placeholder="0"
                  className="w-20 bg-gray-950/50 border border-gray-700/50 rounded px-2.5 py-1 text-right text-sm text-cyan-400 font-mono focus:outline-none focus:border-cyan-500/50"
                />
              </div>
            ))}
          </div>
          {tickers.length > 1 && (
            <div className="pt-2 border-t border-gray-850 flex justify-between items-center">
              <span className="text-xs text-gray-500">
                {totalWeight === 0
                  ? "Equal weight allocation"
                  : `Total specified weight: ${totalWeight.toFixed(1)}%`}
              </span>
              {showWeightWarning && (
                <span className="text-[10px] text-amber-400/90 font-medium animate-pulse">
                  ⚠ Must sum to 100%
                </span>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
