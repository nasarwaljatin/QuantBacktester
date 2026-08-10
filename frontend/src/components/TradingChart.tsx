// frontend/src/components/TradingChart.tsx
"use client";

import { useEffect, useRef, useState } from "react";
import {
  createChart,
  ColorType,
  ISeriesApi,
  UTCTimestamp,
  SeriesMarker,
  Time,
  CandlestickSeries,
  LineSeries,
  HistogramSeries,
  createSeriesMarkers
} from "lightweight-charts";



import { useThemeStore } from "@/lib/themeStore";
import { useBacktestStore } from "@/lib/store";
import type { EquityCurvePoint, TradeRecord } from "@/types/backtest";

interface OHLCVRecord {
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume?: number;
}

interface TradingChartProps {
  ohlcv: OHLCVRecord[];
  equityCurve?: EquityCurvePoint[];
  trades?: TradeRecord[];
  height?: number;
  showLiveIndicator?: boolean;
}

export default function TradingChart({
  ohlcv,
  equityCurve = [],
  trades = [],
  height = 400,
  showLiveIndicator = false,
}: TradingChartProps) {
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<any>(null);
  const theme = useThemeStore((s) => s.theme);
  const currency = useBacktestStore((s) => s.currency);
  const [chartReady, setChartReady] = useState(false);

  // Setup theme-based styles
  const isDark = theme === "dark";
  const colors = {
    bgColor: showLiveIndicator ? "#131722" : "transparent",
    textColor: showLiveIndicator ? "#787b86" : "#9ca3af",
    gridColor: showLiveIndicator ? "#202431" : "rgba(75, 85, 99, 0.15)",
    equityColor: "#06b6d4",
    volumeColor: "rgba(6, 182, 212, 0.2)",
    upColor: "#10b981",
    downColor: "#ef4444",
  };

  const chartHeight = showLiveIndicator ? height - 40 : height;


  useEffect(() => {
    if (!chartContainerRef.current) return;

    // 1. Create Chart
    const chart = createChart(chartContainerRef.current, {
      width: chartContainerRef.current.clientWidth,
      height: chartHeight,
      layout: {
        background: { type: ColorType.Solid, color: colors.bgColor },
        textColor: colors.textColor,
        fontFamily: "Inter, sans-serif",
      },
      grid: {
        vertLines: { color: colors.gridColor },
        horzLines: { color: colors.gridColor },
      },
      timeScale: {
        borderVisible: false,
        timeVisible: true,
        secondsVisible: false,
      },
      leftPriceScale: {
        visible: equityCurve.length > 0, // only show left scale if we have an equity curve overlay
        borderVisible: false,
      },
      rightPriceScale: {
        visible: true,
        borderVisible: false,
      },
    });

    chartRef.current = chart;

    // 2. Add Candlestick Series
    const mainSeries = chart.addSeries(CandlestickSeries, {
      upColor: colors.upColor,
      downColor: colors.downColor,
      borderUpColor: colors.upColor,
      borderDownColor: colors.downColor,
      wickUpColor: colors.upColor,
      wickDownColor: colors.downColor,
    });



    // Format and set Candlestick data
    const formattedOhlcv = ohlcv
      .map((r) => ({
        time: r.date.slice(0, 10) as Time,
        open: Number(r.open),
        high: Number(r.high),
        low: Number(r.low),
        close: Number(r.close),
      }))
      .sort((a, b) => (a.time > b.time ? 1 : -1));

    // Remove duplicates to prevent lightweight-charts errors
    const uniqueOhlcv = formattedOhlcv.filter(
      (v, i, self) => self.findIndex((t) => t.time === v.time) === i
    );

    mainSeries.setData(uniqueOhlcv);


    // 3. Add Volume Pane (if volume data is present)
    const hasVolume = ohlcv.some((r) => r.volume != null && r.volume > 0);
    let volumeSeries: ISeriesApi<"Histogram"> | null = null;
    if (hasVolume) {
      volumeSeries = chart.addSeries(HistogramSeries, {
        color: colors.volumeColor,
        priceFormat: {
          type: "volume",
        },
        priceScaleId: "volume-pane", // custom pane scale
      });



      // Overlay volume on the bottom 25% of the chart
      chart.priceScale("volume-pane").applyOptions({
        scaleMargins: {
          top: 0.75,
          bottom: 0,
        },
        visible: false,
      });

      const formattedVolume = ohlcv
        .map((r) => ({
          time: r.date.slice(0, 10) as Time,
          value: Number(r.volume || 0),
          color: Number(r.close) >= Number(r.open) ? colors.upColor + "40" : colors.downColor + "40",
        }))
        .sort((a, b) => (a.time > b.time ? 1 : -1))
        .filter((v, i, self) => self.findIndex((t) => t.time === v.time) === i);

      volumeSeries.setData(formattedVolume);
    }

    // 4. Add Equity Curve Overlay (on Left Y-axis)
    let equitySeries: ISeriesApi<"Line"> | null = null;
    if (equityCurve && equityCurve.length > 0) {
      equitySeries = chart.addSeries(LineSeries, {
        color: colors.equityColor,
        lineWidth: 2,
        priceScaleId: "left",
        title: "Portfolio Equity",
      });



      const formattedEquity = equityCurve
        .map((r) => ({
          time: r.date.slice(0, 10) as Time,
          value: Number(r.value),
        }))
        .sort((a, b) => (a.time > b.time ? 1 : -1))
        .filter((v, i, self) => self.findIndex((t) => t.time === v.time) === i);

      equitySeries.setData(formattedEquity);

      // Margin for Left Equity Scale
      chart.priceScale("left").applyOptions({
        scaleMargins: {
          top: 0.1,
          bottom: 0.3, // keeps it separate from volume
        },
      });
    }

    // Margin for Right Price Scale
    chart.priceScale("right").applyOptions({
      scaleMargins: {
        top: 0.1,
        bottom: 0.3,
      },
    });

    // 5. Add Trade Markers
    if (trades && trades.length > 0) {
      const markers: SeriesMarker<Time>[] = [];

      trades.forEach((trade) => {
        if (trade.entry_date) {
          markers.push({
            time: trade.entry_date.slice(0, 10) as Time,
            position: "belowBar",
            color: colors.upColor,
            shape: "arrowUp",
            text: `Buy @ ${currency}${trade.entry_price.toFixed(1)}`,
          });
        }
        if (trade.exit_date) {
          markers.push({
            time: trade.exit_date.slice(0, 10) as Time,
            position: "aboveBar",
            color: colors.downColor,
            shape: "arrowDown",
            text: `Sell @ ${currency}${trade.exit_price.toFixed(1)}`,
          });
        }
      });

      // Sort markers by date
      markers.sort((a, b) => (a.time > b.time ? 1 : -1));

      // Filter duplicates by time (lightweight-charts requires unique marker dates per series)
      const uniqueMarkers = markers.filter(
        (v, i, self) => self.findIndex((t) => t.time === v.time) === i
      );

      createSeriesMarkers(mainSeries, uniqueMarkers);
    }



    // 6. Handle resize responsiveness
    const handleResize = () => {
      if (chartContainerRef.current) {
        chart.resize(chartContainerRef.current.clientWidth, chartHeight);
      }
    };
    window.addEventListener("resize", handleResize);

    setChartReady(true);

    return () => {
      window.removeEventListener("resize", handleResize);
      chart.remove();
    };
  }, [ohlcv, equityCurve, trades, height]);

  // 7. Update options dynamically when theme changes
  useEffect(() => {
    if (!chartRef.current) return;
    chartRef.current.applyOptions({
      layout: {
        background: { type: ColorType.Solid, color: colors.bgColor },
        textColor: colors.textColor,
      },
      grid: {
        vertLines: { color: colors.gridColor },
        horzLines: { color: colors.gridColor },
      },
    });
  }, [theme]);

  if (showLiveIndicator) {
    return (
      <div className="flex flex-col w-full bg-[#131722] text-[#d1d4dc] border border-[#2a2e39] rounded-xl overflow-hidden font-sans shadow-lg select-none" style={{ height }}>
        {/* Top Toolbar */}
        <div className="h-10 border-b border-[#2a2e39] flex items-center px-3 justify-between select-none text-[13px] bg-[#1c2030] shrink-0">
          <div className="flex items-center gap-1.5 overflow-x-auto scrollbar-none py-1">
            {/* Timeframes */}
            <span className="px-2 py-1 rounded text-[#787b86] text-xs">1m</span>
            <span className="px-2 py-1 rounded text-[#787b86] text-xs">30m</span>
            <span className="px-2 py-1 rounded text-[#787b86] text-xs">1h</span>
            <span className="px-2.5 py-0.5 rounded bg-[#2a2e39] text-cyan-400 font-semibold text-xs border border-[#2a2e39]">D</span>
            <span className="px-2 py-1 rounded hover:bg-[#2a2e39] text-[#d1d4dc] text-xs cursor-pointer">W</span>
            <span className="px-2 py-1 rounded hover:bg-[#2a2e39] text-[#d1d4dc] text-xs cursor-pointer">M</span>
            
            <div className="w-px h-4 bg-[#2a2e39] mx-1.5" />
            
            {/* Candle type icon */}
            <span className="p-1 rounded bg-[#2a2e39] text-cyan-400 flex items-center">
              <svg className="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 24 24">
                <path d="M9 4h2v3h1v10h-1v3H9v-3H8V7h1V4zm6 2h2v2h1v10h-1v4h-2v-4h-1V8h1V6z" />
              </svg>
            </span>

            <div className="w-px h-4 bg-[#2a2e39] mx-1.5" />

            {/* Indicators button */}
            <span className="flex items-center gap-1.5 px-2 py-1 rounded hover:bg-[#2a2e39] text-[#d1d4dc] text-xs cursor-pointer">
              <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 002 2h2a2 2 0 002-2z" />
              </svg>
              <span>Indicators</span>
            </span>
          </div>

          <div className="flex items-center gap-2">
            <span className="p-1.5 rounded text-[#787b86] flex items-center">
              <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M3 9a2 2 0 012-2h.93a2 2 0 001.664-.89l.812-1.22A2 2 0 0110.07 4h3.86a2 2 0 011.664.89l.812 1.22A2 2 0 0018.07 7H19a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V9z" />
                <path strokeLinecap="round" strokeLinejoin="round" d="M15 13a3 3 0 11-6 0 3 3 0 016 0z" />
              </svg>
            </span>
          </div>
        </div>

        <div className="flex flex-1 min-h-0 relative">
          {/* Left Drawing Sidebar */}
          <div className="w-11 border-r border-[#2a2e39] bg-[#1c2030] flex flex-col items-center py-3 justify-between shrink-0 select-none text-[#787b86]">
            <div className="flex flex-col items-center gap-3">
              {/* Crosshair cursor */}
              <span className="p-1.5 rounded bg-[#2a2e39] text-cyan-400 flex items-center">
                <svg className="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M12 2a1 1 0 011 1v8h8a1 1 0 010 2h-8v8a1 1 0 01-2 0v-8H3a1 1 0 010-2h8V3a1 1 0 011-1z" />
                </svg>
              </span>

              {/* Trendline */}
              <span className="p-1.5 rounded hover:bg-[#2a2e39] hover:text-[#d1d4dc] flex items-center cursor-pointer">
                <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M5 19L19 5M5 19a2 2 0 110-4 2 2 0 010 4zm14-14a2 2 0 110-4 2 2 0 010 4z" />
                </svg>
              </span>

              {/* Fib Retracement */}
              <span className="p-1.5 rounded hover:bg-[#2a2e39] hover:text-[#d1d4dc] flex items-center cursor-pointer">
                <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M4 6h16M4 10h16M4 14h16M4 18h16" />
                </svg>
              </span>

              {/* Brush */}
              <span className="p-1.5 rounded hover:bg-[#2a2e39] hover:text-[#d1d4dc] flex items-center cursor-pointer">
                <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
                </svg>
              </span>

              {/* Text tool */}
              <span className="px-1.5 py-0.5 rounded hover:bg-[#2a2e39] hover:text-[#d1d4dc] font-serif font-bold text-xs cursor-pointer">
                T
              </span>

              {/* Ruler */}
              <span className="p-1.5 rounded hover:bg-[#2a2e39] hover:text-[#d1d4dc] flex items-center cursor-pointer">
                <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9h4m-4 3h4m-4-6h4" />
                </svg>
              </span>
            </div>

            {/* Settings gear at bottom */}
            <span className="p-1.5 rounded hover:bg-[#2a2e39] hover:text-[#d1d4dc] flex items-center cursor-pointer">
              <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                <path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
              </svg>
            </span>
          </div>

          {/* Canvas Content */}
          <div className="flex-1 min-w-0 bg-[#131722] p-2 relative flex items-center justify-center">
            <div ref={chartContainerRef} className="w-full h-full" />
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="relative w-full">
      {/* Delayed / Live indicator badge */}
      <div className="absolute top-3 right-3 z-10 flex items-center gap-2">
        {showLiveIndicator ? (
          <div className="flex items-center gap-1.5 px-2 py-1 rounded bg-emerald-500/10 dark:bg-emerald-500/20 border border-emerald-500/30 text-[10px] font-bold text-emerald-600 dark:text-emerald-400 uppercase tracking-wider">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
            Live (Delayed)
          </div>
        ) : (
          <div className="flex items-center gap-1 px-2 py-1 rounded bg-gray-500/10 dark:bg-gray-500/20 border border-gray-500/30 text-[10px] font-bold text-gray-600 dark:text-gray-400 uppercase tracking-wider">
            Backtest
          </div>
        )}
      </div>

      <div ref={chartContainerRef} className="w-full rounded-xl overflow-hidden" />

      {/* Lightweight-charts open source licensing notice */}
      <p className="mt-2 text-[10px] text-gray-400 dark:text-gray-500 italic text-right">
        Charts powered by TradingView Lightweight Charts™ (Apache-2.0).
      </p>
    </div>
  );
}
