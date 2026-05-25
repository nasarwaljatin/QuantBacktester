// frontend/src/components/EquityCurveChart.tsx
"use client";

import dynamic from "next/dynamic";
import { useBacktestStore } from "@/lib/store";
import type { EquityCurvePoint } from "@/types/backtest";

const Plot = dynamic(() => import("react-plotly.js"), { ssr: false });

interface EquityCurveChartProps {
  equityCurve: EquityCurvePoint[];
  benchmarkCurve: EquityCurvePoint[];
}

export default function EquityCurveChart({
  equityCurve,
  benchmarkCurve,
}: EquityCurveChartProps) {
  const currency = useBacktestStore((s) => s.currency);
  const strategyDates = equityCurve.map((p) => p.date);
  const strategyValues = equityCurve.map((p) => p.value);
  const benchmarkDates = benchmarkCurve.map((p) => p.date);
  const benchmarkValues = benchmarkCurve.map((p) => p.value);

  return (
    <div className="bg-gray-800/40 backdrop-blur-sm rounded-2xl border border-gray-700/50 p-6 shadow-xl">
      <div className="flex items-center gap-3 mb-4">
        <div className="w-2 h-2 rounded-full bg-cyan-400" />
        <h3 className="text-lg font-semibold text-white">Equity Curve</h3>
      </div>
      <Plot
        data={[
          {
            x: strategyDates,
            y: strategyValues,
            type: "scatter",
            mode: "lines",
            name: "Strategy",
            line: { color: "#06b6d4", width: 2.5 },
            hovertemplate: `%{x}<br>Strategy: ${currency}%{y:,.0f}<extra></extra>`,
          },
          {
            x: benchmarkDates,
            y: benchmarkValues,
            type: "scatter",
            mode: "lines",
            name: "Buy & Hold",
            line: { color: "#6b7280", width: 1.5, dash: "dash" },
            hovertemplate: `%{x}<br>Buy & Hold: ${currency}%{y:,.0f}<extra></extra>`,
          },
        ]}
        layout={{
          height: 400,
          margin: { t: 10, r: 30, b: 60, l: 80 },
          paper_bgcolor: "transparent",
          plot_bgcolor: "transparent",
          font: { color: "#9ca3af", family: "Inter, sans-serif" },
          xaxis: {
            gridcolor: "rgba(75, 85, 99, 0.3)",
            rangeslider: { visible: true },
            type: "date",
          },
          yaxis: {
            gridcolor: "rgba(75, 85, 99, 0.3)",
            title: { text: `Portfolio Value (${currency})` },
            tickformat: ",.0f",
            tickprefix: currency,
          },
          legend: {
            orientation: "h",
            x: 0.5,
            xanchor: "center",
            y: 1.12,
            bgcolor: "transparent",
          },
          hovermode: "x unified",
        }}
        config={{ responsive: true, displayModeBar: false }}
        className="w-full"
      />
    </div>
  );
}
