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
    bgColor: isDark ? "rgba(17, 24, 39, 0.4)" : "#ffffff",
    textColor: isDark ? "#9ca3af" : "#374151",
    gridColor: isDark ? "rgba(75, 85, 99, 0.15)" : "#e5e7eb",
    equityColor: "#06b6d4",
    volumeColor: isDark ? "rgba(6, 182, 212, 0.2)" : "rgba(6, 182, 212, 0.3)",
    upColor: "#22c55e",
    downColor: "#ef4444",
  };

  useEffect(() => {
    if (!chartContainerRef.current) return;

    // 1. Create Chart
    const chart = createChart(chartContainerRef.current, {
      width: chartContainerRef.current.clientWidth,
      height: height,
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
        chart.resize(chartContainerRef.current.clientWidth, height);
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
