"use client";
// frontend/src/components/WFAResultsTable.tsx
// Walk-Forward Analysis results v2:
//   - Aggregate efficiency ratio banner (green/amber/red)
//   - Per-fold table with color-coded Efficiency Ratio column
//   - Parameter Stability panel with CV bars
//   - Combined OOS equity chart
//   - Overfitting warning based on IS/OOS spread + efficiency ratio

import dynamic from "next/dynamic";
const Plot = dynamic(() => import("react-plotly.js"), { ssr: false });

import type { WFAWindowResult, EquityCurvePoint } from "@/types/backtest";

interface WFAResultsTableProps {
  windows: WFAWindowResult[];
  combinedOosEquity: EquityCurvePoint[];
  aggregateOosMetrics: Record<string, any>;
  totalWindows: number;
  inSampleDays: number;
  outOfSampleDays: number;
  windowType?: string;
  anchored?: boolean;
  objective: string;
  initialCapital?: number;
  aggregateEfficiencyRatio?: number | null;
  paramStability?: Record<string, number | null>;
}

// ─── Formatters ──────────────────────────────────────────────────────────────

function fmtPct(val: number | null | undefined): string {
  if (val == null || isNaN(val)) return "—";
  return (val * 100).toFixed(2) + "%";
}

function fmtNum(val: number | null | undefined, dp = 3): string {
  if (val == null || isNaN(val)) return "—";
  return val.toFixed(dp);
}

function fmtLabel(key: string): string {
  return key
    .split("_")
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(" ");
}

// ─── Efficiency ratio helpers ─────────────────────────────────────────────────

function erColor(ratio: number | null | undefined): string {
  if (ratio == null) return "#6b7280"; // gray — undefined
  if (ratio >= 0.7) return "#22c55e";  // green
  if (ratio >= 0.5) return "#f59e0b";  // amber
  return "#ef4444";                    // red
}

function erLabel(ratio: number | null | undefined): string {
  if (ratio == null) return "—";
  if (ratio >= 0.7) return "✓ Well-generalised";
  if (ratio >= 0.5) return "⚠ Moderate risk";
  return "✗ Likely overfit";
}

function erBannerClass(ratio: number | null | undefined): string {
  if (ratio == null) return "wfa-er-banner--neutral";
  if (ratio >= 0.7) return "wfa-er-banner--green";
  if (ratio >= 0.5) return "wfa-er-banner--amber";
  return "wfa-er-banner--red";
}

function erBannerLabel(ratio: number | null | undefined): string {
  if (ratio == null) return "Efficiency ratio not available (insufficient folds with positive IS metric)";
  if (ratio >= 0.7) return `🟢 Well-generalised — aggregate efficiency ratio: ${fmtNum(ratio, 3)}`;
  if (ratio >= 0.5) return `🟡 Moderate overfitting risk — aggregate efficiency ratio: ${fmtNum(ratio, 3)}`;
  return `🔴 Likely overfit — aggregate efficiency ratio: ${fmtNum(ratio, 3)} (< 0.5)`;
}

// ─── CV bar helpers ───────────────────────────────────────────────────────────

function cvColor(cv: number | null): string {
  if (cv == null) return "#6b7280";
  if (cv < 0.2) return "#22c55e";
  if (cv < 0.5) return "#f59e0b";
  return "#ef4444";
}

function cvLabel(cv: number | null): string {
  if (cv == null) return "—";
  if (cv < 0.2) return "Stable";
  if (cv < 0.5) return "Moderate";
  return "Unstable";
}

// ─── Overfitting detector ─────────────────────────────────────────────────────

function detectOverfitting(
  windows: WFAWindowResult[],
  objective: string,
  aggregateEfficiencyRatio?: number | null,
): { isOverfit: boolean; isAvg: number; oosAvg: number } {
  const success = windows.filter((w) => w.status === "SUCCESS");
  if (!success.length) return { isOverfit: false, isAvg: 0, oosAvg: 0 };
  const isVals = success.map((w) => (w.in_sample_metrics?.[objective] as number) ?? 0);
  const oosVals = success.map((w) => (w.out_of_sample_metrics?.[objective] as number) ?? 0);
  const isAvg = isVals.reduce((a, b) => a + b, 0) / isVals.length;
  const oosAvg = oosVals.reduce((a, b) => a + b, 0) / oosVals.length;
  // Overfit if IS > 2× OOS, or efficiency ratio < 0.5
  const spreadOverfit = isAvg > 0 && oosAvg < isAvg * 0.5;
  const erOverfit = aggregateEfficiencyRatio != null && aggregateEfficiencyRatio < 0.5;
  return { isOverfit: spreadOverfit || erOverfit, isAvg, oosAvg };
}


// ─── Main component ───────────────────────────────────────────────────────────

export default function WFAResultsTable({
  windows,
  combinedOosEquity,
  aggregateOosMetrics,
  totalWindows,
  inSampleDays,
  outOfSampleDays,
  windowType = "rolling",
  anchored = false,
  objective,
  initialCapital = 100000,
  aggregateEfficiencyRatio,
  paramStability,
}: WFAResultsTableProps) {
  const { isOverfit, isAvg, oosAvg } = detectOverfitting(windows, objective, aggregateEfficiencyRatio);

  // Build window-type label
  const windowLabel = anchored ? "Anchored Rolling" : windowType === "expanding" ? "Expanding" : "Rolling";

  // Aggregate metric keys to display
  const metricKeys = Object.keys(aggregateOosMetrics || {}).filter(
    (k) => typeof aggregateOosMetrics[k] === "number" && aggregateOosMetrics[k] !== null
  );

  const pctKeys = new Set([
    "total_return", "annualized_return", "max_drawdown", "win_rate",
  ]);



  const hasStability = paramStability && Object.keys(paramStability).length > 0;
  const maxCV = Math.max(
    ...Object.values(paramStability ?? {}).map((v) => v ?? 0),
    1,
  );

  return (
    <div className="wfa-root">
      {/* ── Header with window type badge ── */}
      <div className="wfa-header-row">
        <h3 className="wfa-title">Walk-Forward Analysis Results</h3>
        <span className="wfa-type-badge">{windowLabel}</span>
        {anchored && windowType === "rolling" && (
          <span className="wfa-anchored-badge">Anchored</span>
        )}
        <span className="wfa-meta">
          {totalWindows} folds · {inSampleDays}d IS / {outOfSampleDays}d OOS
        </span>
      </div>

      {/* ── Efficiency Ratio Banner ── */}
      <div className={`wfa-er-banner ${erBannerClass(aggregateEfficiencyRatio)}`}>
        {erBannerLabel(aggregateEfficiencyRatio)}
        {aggregateEfficiencyRatio != null && (
          <span className="wfa-er-banner-sub">
            &nbsp;· Interpretation: ≥0.7 good, 0.5–0.7 moderate, &lt;0.5 likely overfit
          </span>
        )}
      </div>

      {/* ── Overfitting Warning ── */}
      {isOverfit && (
        <div className="wfa-overfit-banner">
          <svg className="wfa-warn-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
              d="M12 9v4m0 4h.01M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z" />
          </svg>
          <div>
            <strong>Overfitting Warning:</strong> In-sample {fmtLabel(objective)} ({fmtNum(isAvg, 3)}) is
            more than twice the out-of-sample value ({fmtNum(oosAvg, 3)}). This is a strong signal
            that the strategy's edge is curve-fitted to historical data. Consider simplifying the parameter
            grid or using different validation periods.
          </div>
        </div>
      )}

      {combinedOosEquity.length > 0 && (
        <div className="wfa-section">
          <h4 className="wfa-section-title">Combined Out-of-Sample Equity Curve</h4>
          <div className="wfa-chart-wrap">
            <Plot
              data={[
                {
                  x: combinedOosEquity.map((p) => p.date),
                  y: combinedOosEquity.map((p) => p.value),
                  type: "scatter",
                  mode: "lines",
                  name: "OOS Portfolio",
                  line: { color: "#6366f1", width: 2.5 },
                  hovertemplate: `%{x}<br>OOS Portfolio: $%{y:,.0f}<extra></extra>`,
                },
              ]}
              layout={{
                height: 250,
                margin: { t: 10, r: 20, b: 40, l: 60 },
                paper_bgcolor: "transparent",
                plot_bgcolor: "transparent",
                font: { color: "#9ca3af", family: "Inter, sans-serif", size: 10 },
                xaxis: {
                  gridcolor: "rgba(75, 85, 99, 0.15)",
                  type: "date",
                  tickfont: { size: 9 },
                },
                yaxis: {
                  gridcolor: "rgba(75, 85, 99, 0.15)",
                  tickformat: ",.0f",
                  tickprefix: "$",
                  tickfont: { size: 9 },
                },
                showlegend: false,
                hovermode: "x unified",
              }}
              config={{ responsive: true, displayModeBar: false }}
              className="w-full"
            />
          </div>
        </div>
      )}


      {/* ── Aggregate OOS Metrics ── */}
      {metricKeys.length > 0 && (
        <div className="wfa-section">
          <h4 className="wfa-section-title">Aggregate Out-of-Sample Metrics</h4>
          <div className="wfa-metrics-grid">
            {metricKeys.map((k) => (
              <div key={k} className="wfa-metric-card">
                <div className="wfa-metric-label">{fmtLabel(k)}</div>
                <div className="wfa-metric-value">
                  {pctKeys.has(k)
                    ? fmtPct(aggregateOosMetrics[k])
                    : fmtNum(aggregateOosMetrics[k])}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ── Per-Fold Table ── */}
      <div className="wfa-section">
        <h4 className="wfa-section-title">Per-Fold Results</h4>
        <div className="wfa-table-wrap">
          <table className="wfa-table">
            <thead>
              <tr>
                <th>Fold</th>
                <th>IS Period</th>
                <th>OOS Period</th>
                <th>Optimized Params</th>
                <th>IS {fmtLabel(objective)}</th>
                <th>OOS {fmtLabel(objective)}</th>
                <th>Efficiency Ratio</th>
                <th>OOS Return</th>
                <th>OOS Max DD</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {windows.map((w) => {
                const isVal = w.in_sample_metrics?.[objective] as number | null ?? null;
                const oosVal = w.out_of_sample_metrics?.[objective] as number | null ?? null;
                const er = w.efficiency_ratio ?? null;
                return (
                  <tr key={w.window_index} className={w.status !== "SUCCESS" ? "wfa-row-fail" : ""}>
                    <td className="wfa-fold-num">#{w.window_index + 1}</td>
                    <td>
                      <span className="wfa-date-range">
                        {w.in_sample_start.slice(0, 10)} – {w.in_sample_end.slice(0, 10)}
                      </span>
                    </td>
                    <td>
                      <span className="wfa-date-range">
                        {w.out_of_sample_start.slice(0, 10)} – {w.out_of_sample_end.slice(0, 10)}
                      </span>
                    </td>
                    <td>
                      {w.optimized_params
                        ? Object.entries(w.optimized_params)
                            .map(([k, v]) => `${k}=${v}`)
                            .join(", ")
                        : "—"}
                    </td>
                    <td>{fmtNum(isVal)}</td>
                    <td>{fmtNum(oosVal)}</td>
                    <td>
                      <span className="wfa-er-cell" style={{ color: erColor(er) }}>
                        {er != null ? fmtNum(er) : "—"}
                      </span>
                    </td>
                    <td>{fmtPct(w.out_of_sample_metrics?.total_return as number)}</td>
                    <td>{fmtPct(w.out_of_sample_metrics?.max_drawdown as number)}</td>
                    <td>
                      <span className={`wfa-status-badge wfa-status-${w.status.toLowerCase()}`}>
                        {w.status}
                      </span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* ── Parameter Stability Panel ── */}
      {hasStability && (
        <div className="wfa-section">
          <h4 className="wfa-section-title">Parameter Stability</h4>
          <p className="wfa-hint">
            Coefficient of Variation (CV = σ/μ) per parameter across folds.
            High CV means the optimizer picked very different values each fold — a sign of
            unstable parameter sensitivity.
          </p>
          <div className="wfa-stability-list">
            {Object.entries(paramStability!).map(([param, cv]) => (
              <div key={param} className="wfa-stability-row">
                <div className="wfa-stability-param">{param}</div>
                <div className="wfa-stability-bar-wrap">
                  <div
                    className="wfa-stability-bar"
                    style={{
                      width: cv != null ? `${Math.min((cv / maxCV) * 100, 100)}%` : "0%",
                      background: cvColor(cv),
                    }}
                  />
                </div>
                <div className="wfa-stability-cv" style={{ color: cvColor(cv) }}>
                  {cv != null ? fmtNum(cv) : "—"}&nbsp;
                  <span className="wfa-stability-label">({cvLabel(cv)})</span>
                </div>
              </div>
            ))}
          </div>
          <div className="wfa-stability-legend">
            <span style={{ color: "#22c55e" }}>■ CV &lt; 0.2 Stable</span>
            <span style={{ color: "#f59e0b" }}>■ 0.2–0.5 Moderate</span>
            <span style={{ color: "#ef4444" }}>■ &gt; 0.5 Unstable</span>
          </div>
        </div>
      )}

      <style jsx>{`
        .wfa-root { display: flex; flex-direction: column; gap: 20px; }
        .wfa-header-row { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
        .wfa-title { font-size: 16px; font-weight: 700; color: #e5e7eb; margin: 0; }
        .wfa-type-badge {
          font-size: 10px; font-weight: 700; letter-spacing: 0.06em; text-transform: uppercase;
          background: rgba(99,102,241,0.15); border: 1px solid rgba(99,102,241,0.3);
          color: #a5b4fc; padding: 2px 8px; border-radius: 20px;
        }
        .wfa-anchored-badge {
          font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.06em;
          background: rgba(16,185,129,0.12); border: 1px solid rgba(16,185,129,0.3);
          color: #6ee7b7; padding: 2px 8px; border-radius: 20px;
        }
        .wfa-meta { font-size: 12px; color: #6b7280; }

        /* Efficiency Ratio banner */
        .wfa-er-banner {
          padding: 12px 16px; border-radius: 10px; border: 1px solid;
          font-size: 13px; font-weight: 600; line-height: 1.5;
        }
        .wfa-er-banner--green { background: rgba(34,197,94,0.08); border-color: rgba(34,197,94,0.3); color: #86efac; }
        .wfa-er-banner--amber { background: rgba(245,158,11,0.08); border-color: rgba(245,158,11,0.3); color: #fcd34d; }
        .wfa-er-banner--red { background: rgba(239,68,68,0.08); border-color: rgba(239,68,68,0.3); color: #fca5a5; }
        .wfa-er-banner--neutral { background: rgba(107,114,128,0.08); border-color: rgba(107,114,128,0.3); color: #9ca3af; }
        .wfa-er-banner-sub { font-size: 11px; font-weight: 400; opacity: 0.8; }

        /* Overfitting warning */
        .wfa-overfit-banner {
          display: flex; gap: 12px; align-items: flex-start;
          padding: 14px 16px; border-radius: 10px;
          background: rgba(245,158,11,0.07); border: 1px solid rgba(245,158,11,0.25);
          color: #fcd34d; font-size: 13px; line-height: 1.6;
        }
        .wfa-warn-icon { width: 20px; height: 20px; flex-shrink: 0; margin-top: 2px; }

        /* Sections */
        .wfa-section { display: flex; flex-direction: column; gap: 10px; }
        .wfa-section-title {
          font-size: 11px; font-weight: 700; letter-spacing: 0.08em; text-transform: uppercase;
          color: #6b7280; margin: 0;
        }
        .wfa-hint { font-size: 12px; color: #6b7280; margin: 0; line-height: 1.5; }

        /* Chart */
        .wfa-chart-wrap { border-radius: 12px; background: rgba(255,255,255,0.02); padding: 8px 0; }

        /* Aggregate metrics grid */
        .wfa-metrics-grid {
          display: grid; grid-template-columns: repeat(auto-fill, minmax(130px, 1fr)); gap: 10px;
        }
        .wfa-metric-card {
          background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.07);
          border-radius: 10px; padding: 12px 14px;
        }
        .wfa-metric-label { font-size: 10px; font-weight: 600; color: #6b7280; text-transform: uppercase; letter-spacing: 0.06em; }
        .wfa-metric-value { font-size: 17px; font-weight: 700; color: #e5e7eb; margin-top: 4px; }

        /* Table */
        .wfa-table-wrap { overflow-x: auto; border-radius: 10px; border: 1px solid rgba(255,255,255,0.07); }
        .wfa-table { width: 100%; border-collapse: collapse; font-size: 12px; }
        .wfa-table th {
          padding: 10px 12px; text-align: left; font-size: 10px; font-weight: 700;
          letter-spacing: 0.07em; text-transform: uppercase; color: #6b7280;
          border-bottom: 1px solid rgba(255,255,255,0.07); white-space: nowrap;
          background: rgba(0,0,0,0.2);
        }
        .wfa-table td { padding: 9px 12px; border-bottom: 1px solid rgba(255,255,255,0.05); color: #d1d5db; }
        .wfa-table tr:last-child td { border-bottom: none; }
        .wfa-table tr:hover td { background: rgba(255,255,255,0.02); }
        .wfa-row-fail td { opacity: 0.5; }
        .wfa-fold-num { font-weight: 700; color: #6366f1; }
        .wfa-date-range { font-family: monospace; font-size: 11px; color: #9ca3af; }
        .wfa-er-cell { font-weight: 700; font-size: 13px; }
        .wfa-status-badge {
          font-size: 10px; font-weight: 700; padding: 2px 7px; border-radius: 20px;
          text-transform: uppercase; letter-spacing: 0.06em;
        }
        .wfa-status-success { background: rgba(34,197,94,0.12); color: #86efac; }
        .wfa-status-failure { background: rgba(239,68,68,0.12); color: #fca5a5; }
        .wfa-status-pending { background: rgba(107,114,128,0.12); color: #9ca3af; }

        /* Parameter Stability */
        .wfa-stability-list { display: flex; flex-direction: column; gap: 8px; }
        .wfa-stability-row { display: grid; grid-template-columns: 90px 1fr 120px; align-items: center; gap: 10px; }
        .wfa-stability-param { font-size: 12px; font-weight: 600; color: #e5e7eb; }
        .wfa-stability-bar-wrap { height: 8px; background: rgba(255,255,255,0.06); border-radius: 4px; overflow: hidden; }
        .wfa-stability-bar { height: 100%; border-radius: 4px; transition: width 0.4s ease; }
        .wfa-stability-cv { font-size: 12px; font-weight: 600; }
        .wfa-stability-label { font-weight: 400; color: #6b7280; }
        .wfa-stability-legend { display: flex; gap: 14px; font-size: 11px; margin-top: 4px; flex-wrap: wrap; }

        /* Tooltip */
        .wfa-tooltip {
          background: rgba(15,17,26,0.95); border: 1px solid rgba(99,102,241,0.3);
          border-radius: 8px; padding: 8px 12px;
        }
        .wfa-tooltip-date { font-size: 11px; color: #9ca3af; margin: 0 0 4px; }
        .wfa-tooltip-val { font-size: 14px; font-weight: 700; color: #a5b4fc; margin: 0; }
      `}</style>
    </div>
  );
}
