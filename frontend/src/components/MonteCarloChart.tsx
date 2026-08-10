import dynamic from "next/dynamic";
import { useThemeStore } from "@/lib/themeStore";
import type { MonteCarloResult, EquityCurvePoint } from "@/types/backtest";

const Plot = dynamic(() => import("react-plotly.js"), { ssr: false });

interface MonteCarloChartProps {
  monteCarlo: MonteCarloResult;
  actualCurve: EquityCurvePoint[];
}

export default function MonteCarloChart({
  monteCarlo,
  actualCurve,
}: MonteCarloChartProps) {
  const theme = useThemeStore((s) => s.theme);
  const isDark = theme === "dark";
  const textColor = isDark ? "#9ca3af" : "#374151";
  const gridColor = isDark ? "rgba(75, 85, 99, 0.2)" : "rgba(229, 231, 235, 0.8)";

  const tradeIndices = Array.from(
    { length: monteCarlo.percentile_50.length },
    (_, i) => i
  );

  // Build traces for sampled paths (thin gray lines)
  const pathTraces = monteCarlo.paths.slice(0, 50).map((path, i) => ({
    x: Array.from({ length: path.length }, (_, j) => j),
    y: path,
    type: "scatter" as const,
    mode: "lines" as const,
    line: { color: isDark ? "rgba(156, 163, 175, 0.1)" : "rgba(156, 163, 175, 0.2)", width: 0.8 },
    showlegend: false,
    hoverinfo: "skip" as const,
    name: `Path ${i + 1}`,
  }));

  return (
    <div className="bg-white dark:bg-gray-800/40 backdrop-blur-sm rounded-2xl border border-gray-200 dark:border-gray-700/50 p-6 shadow-xl transition-colors duration-300">
      <div className="flex items-center gap-3 mb-4">
        <div className="w-2 h-2 rounded-full bg-amber-400" />
        <h3 className="text-lg font-semibold text-slate-900 dark:text-white">Monte Carlo Simulation</h3>
      </div>

      <Plot
        data={[
          ...pathTraces,
          // 5th-95th percentile band
          {
            x: [...tradeIndices, ...tradeIndices.slice().reverse()],
            y: [
              ...monteCarlo.percentile_5,
              ...monteCarlo.percentile_95.slice().reverse(),
            ],
            fill: "toself",
            fillcolor: isDark ? "rgba(6, 182, 212, 0.08)" : "rgba(6, 182, 212, 0.05)",
            line: { color: "transparent" },
            type: "scatter",
            mode: "lines",
            name: "5th-95th Percentile",
            showlegend: true,
            hoverinfo: "skip",
          },
          // 5th percentile line
          {
            x: tradeIndices,
            y: monteCarlo.percentile_5,
            type: "scatter",
            mode: "lines",
            line: { color: "#ef4444", width: 1.5, dash: "dot" },
            name: "5th Percentile",
            hovertemplate: "Trade %{x}<br>5th %%ile: $%{y:,.0f}<extra></extra>",
          },
          // Median line
          {
            x: tradeIndices,
            y: monteCarlo.percentile_50,
            type: "scatter",
            mode: "lines",
            line: { color: "#f59e0b", width: 2 },
            name: "Median",
            hovertemplate: "Trade %{x}<br>Median: $%{y:,.0f}<extra></extra>",
          },
          // 95th percentile line
          {
            x: tradeIndices,
            y: monteCarlo.percentile_95,
            type: "scatter",
            mode: "lines",
            line: { color: "#22c55e", width: 1.5, dash: "dot" },
            name: "95th Percentile",
            hovertemplate: "Trade %{x}<br>95th %%ile: $%{y:,.0f}<extra></extra>",
          },
          // Actual curve
          {
            x: Array.from({ length: actualCurve.length }, (_, i) => i),
            y: actualCurve.map((p) => p.value),
            type: "scatter",
            mode: "lines",
            line: { color: "#06b6d4", width: 3 },
            name: "Actual",
            hovertemplate: "Trade %{x}<br>Actual: $%{y:,.0f}<extra></extra>",
          },
        ]}
        layout={{
          height: 400,
          margin: { t: 10, r: 30, b: 60, l: 80 },
          paper_bgcolor: "transparent",
          plot_bgcolor: "transparent",
          font: { color: textColor, family: "Inter, sans-serif" },
          xaxis: {
            gridcolor: gridColor,
            title: { text: "Trade Sequence" },
          },
          yaxis: {
            gridcolor: gridColor,
            title: { text: "Portfolio Value ($)" },
            tickformat: "$,.0f",
          },
          legend: {
            orientation: "h",
            x: 0.5,
            xanchor: "center",
            y: 1.15,
            bgcolor: "transparent",
          },
          hovermode: "x",
        }}
        config={{ responsive: true, displayModeBar: false }}
        className="w-full"
      />

      <div className="mt-4 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
        <div className="flex items-center gap-4">
          <div className="bg-gray-100 dark:bg-gray-700/40 rounded-xl px-4 py-2.5">
            <p className="text-xs text-gray-500 dark:text-gray-400">Probability of Profit</p>
            <p className={`text-xl font-bold ${monteCarlo.prob_profit >= 50 ? "text-emerald-500" : "text-red-500"}`}>
              {monteCarlo.prob_profit.toFixed(1)}%
            </p>
          </div>
        </div>
        <p className="text-xs text-gray-500 italic max-w-md">
          Each path shows what could have happened if your trades occurred in a different order.
          Based on 1,000 simulations.
        </p>
      </div>
    </div>

  );
}
