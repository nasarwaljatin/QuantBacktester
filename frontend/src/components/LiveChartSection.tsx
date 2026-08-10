// frontend/src/components/LiveChartSection.tsx
"use client";

import { useEffect, useState } from "react";
import { useThemeStore } from "@/lib/themeStore";
import { useBacktestStore } from "@/lib/store";

// Normalizes symbols from internal/yfinance formats to TradingView conventions
export function mapSymbolToTradingView(symbol: string): string {
  if (!symbol) return "NASDAQ:AAPL";
  const clean = symbol.toUpperCase().trim();

  // Indian Stock Exchange (National Stock Exchange of India)
  if (clean.endsWith(".NS")) {
    return `NSE:${clean.slice(0, -3)}`;
  }
  // Bombay Stock Exchange
  if (clean.endsWith(".BO")) {
    return `BSE:${clean.slice(0, -3)}`;
  }
  // Major Cryptocurrencies
  if (clean === "BTC-USD" || clean === "BTCUSD") {
    return "BINANCE:BTCUSDT";
  }
  if (clean === "ETH-USD" || clean === "ETHUSD") {
    return "BINANCE:ETHUSDT";
  }
  if (clean.includes("-USD")) {
    return `BINANCE:${clean.replace("-USD", "USDT")}`;
  }
  // Forex/Currency pairs
  if (clean.endsWith("=X")) {
    return `FX:${clean.replace("=X", "")}`;
  }

  // Common US Tech Stock Listings on NASDAQ
  const commonNasdaq = ["AAPL", "MSFT", "GOOGL", "GOOG", "AMZN", "META", "TSLA", "NVDA", "NFLX", "AMD", "INTC", "QQQ"];
  if (commonNasdaq.includes(clean)) {
    return `NASDAQ:${clean}`;
  }
  // Common US Listings on NYSE
  const commonNyse = ["SPY", "DIA", "IWM", "NIO", "F", "GM", "JPM", "BAC", "WMT", "DIS", "KO", "XOM", "CVX", "V", "MA"];
  if (commonNyse.includes(clean)) {
    return `NYSE:${clean}`;
  }

  // Fallback: Let TradingView auto-resolve without exchange prefix
  return clean;
}

// Declares the global TradingView object added by the tv.js script
declare global {
  interface Window {
    TradingView: any;
  }
}

export default function LiveChartSection() {
  const ticker = useBacktestStore((s) => s.ticker);
  const theme = useThemeStore((s) => s.theme);
  const [scriptLoaded, setScriptLoaded] = useState(false);
  const [isModalOpen, setIsModalOpen] = useState(false);

  // Load the TradingView widget loader script dynamically
  useEffect(() => {
    const existingScript = document.getElementById("tradingview-widget-script");
    if (existingScript) {
      setScriptLoaded(true);
      return;
    }

    const script = document.createElement("script");
    script.id = "tradingview-widget-script";
    script.src = "https://s3.tradingview.com/tv.js";
    script.async = true;
    script.onload = () => setScriptLoaded(true);
    script.onerror = () => console.error("Failed to load TradingView tv.js script");
    document.body.appendChild(script);
  }, []);

  const tvSymbol = mapSymbolToTradingView(ticker);
  const containerId = `tv-chart-${tvSymbol.replace(":", "-")}`;

  // Initialize the inline widget
  useEffect(() => {
    if (!scriptLoaded || !tvSymbol) return;

    const timer = setTimeout(() => {
      try {
        if (window.TradingView && window.TradingView.widget) {
          new window.TradingView.widget({
            autosize: true,
            symbol: tvSymbol,
            interval: "D",
            timezone: "Etc/UTC",
            theme: theme,
            style: "1", // Candlesticks
            locale: "en",
            enable_publishing: false,
            hide_top_toolbar: true,
            hide_legend: false,
            save_image: false,
            container_id: containerId,
          });
        }
      } catch (e) {
        console.error("Failed to initialize TradingView widget:", e);
      }
    }, 50);

    return () => clearTimeout(timer);
  }, [scriptLoaded, tvSymbol, theme, containerId]);

  // Initialize the fullscreen modal widget
  useEffect(() => {
    if (!isModalOpen || !scriptLoaded || !tvSymbol) return;

    const timer = setTimeout(() => {
      try {
        if (window.TradingView && window.TradingView.widget) {
          new window.TradingView.widget({
            autosize: true,
            symbol: tvSymbol,
            interval: "D",
            timezone: "Etc/UTC",
            theme: theme,
            style: "1",
            locale: "en",
            enable_publishing: false,
            hide_side_toolbar: false, // Show indicators/drawing tools
            hide_top_toolbar: false,
            container_id: "tv-chart-fullscreen",
          });
        }
      } catch (e) {
        console.error("Failed to initialize fullscreen TradingView widget:", e);
      }
    }, 100);

    return () => clearTimeout(timer);
  }, [isModalOpen, scriptLoaded, tvSymbol, theme]);

  const externalLink = `https://www.tradingview.com/symbols/${tvSymbol.replace(":", "-")}/`;

  return (
    <div className="glass-card rounded-2xl p-6 transition-colors duration-300">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <div className="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse" />
          <h3 className="text-sm font-semibold text-slate-900 dark:text-white uppercase tracking-wider">
            Live Reference Chart: <span className="text-cyan-600 dark:text-cyan-400 font-bold">{ticker}</span>
          </h3>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-[10px] text-gray-500 font-medium px-2 py-0.5 rounded bg-gray-100 dark:bg-gray-800 border border-gray-200 dark:border-gray-700/50">
            Live via TradingView
          </span>

          {/* Action buttons */}
          <button
            onClick={() => setIsModalOpen(true)}
            className="p-1.5 rounded-lg bg-gray-100 dark:bg-gray-800/60 border border-gray-200 dark:border-gray-700/50 text-gray-600 dark:text-gray-400 hover:text-cyan-500 dark:hover:text-cyan-400 hover:border-cyan-500/30 transition-all cursor-pointer"
            title="Expand Fullscreen Chart"
            aria-label="Expand Fullscreen Chart"
          >
            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5v-4m0 4h-4m4 0l-5-5" />
            </svg>
          </button>
          
          <a
            href={externalLink}
            target="_blank"
            rel="noopener noreferrer"
            className="p-1.5 rounded-lg bg-gray-100 dark:bg-gray-800/60 border border-gray-200 dark:border-gray-700/50 text-gray-600 dark:text-gray-400 hover:text-cyan-500 dark:hover:text-cyan-400 hover:border-cyan-500/30 transition-all"
            title="Open on TradingView.com"
          >
            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
            </svg>
          </a>
        </div>
      </div>

      <div className="relative w-full h-[250px] bg-gray-900/10 dark:bg-gray-950/20 rounded-xl overflow-hidden border border-gray-200/50 dark:border-gray-800/50">
        {!scriptLoaded ? (
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="flex items-center gap-3">
              <div className="w-5 h-5 border-2 border-cyan-400 border-t-transparent rounded-full animate-spin" />
              <span className="text-gray-400 text-sm">Connecting to TradingView...</span>
            </div>
          </div>
        ) : (
          <div key={tvSymbol} id={containerId} className="w-full h-full" />
        )}
      </div>

      {/* Fullscreen In-App Modal */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-gray-950/80 backdrop-blur-md">
          <div className="relative w-full max-w-6xl h-[85vh] bg-white dark:bg-gray-900 rounded-2xl border border-gray-200 dark:border-gray-850 flex flex-col overflow-hidden shadow-2xl animate-slide-up">
            
            {/* Modal Header */}
            <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 dark:border-gray-800">
              <div className="flex items-center gap-3">
                <span className="text-lg">📊</span>
                <h3 className="text-base font-semibold text-slate-900 dark:text-white uppercase tracking-wider">
                  TradingView Technical Panel: <span className="text-cyan-500 font-bold">{ticker}</span>
                </h3>
                <span className="text-[10px] text-gray-500 font-medium px-2 py-0.5 rounded bg-gray-100 dark:bg-gray-800 border border-gray-200 dark:border-gray-700/50">
                  Interactive Chart
                </span>
              </div>
              <button
                onClick={() => setIsModalOpen(false)}
                className="p-1.5 rounded-lg bg-gray-100 dark:bg-gray-850 border border-gray-200 dark:border-gray-800 text-gray-500 hover:text-slate-900 dark:hover:text-white hover:bg-gray-200 dark:hover:bg-gray-800 transition-all cursor-pointer"
                title="Close Panel"
                aria-label="Close Panel"
              >
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            {/* Modal Chart Container */}
            <div className="flex-1 w-full bg-gray-950 relative">
              <div id="tv-chart-fullscreen" className="w-full h-full" />
            </div>

          </div>
        </div>
      )}
    </div>
  );
}
