"use client";
// frontend/src/components/SweepHeatmap.tsx
// 2D heatmap visualisation of parameter sweep results

import { useMemo } from "react";
import type { SweepResultItem } from "@/types/backtest";

interface SweepHeatmapProps {
  sweepResults: SweepResultItem[];
  bestParams: Record<string, any>;
  paramGrid: Record<string, any[]>;
  objective: string;
  totalCombinations: number;
}

function formatMetricLabel(key: string): string {
  return key
    .split("_")
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(" ");
}

function formatMetricValue(val: number | null | undefined, key: string): string {
  if (val == null || isNaN(val)) return "—";
  if (key.includes("return") || key.includes("drawdown") || key === "win_rate")
    return (val * 100).toFixed(2) + "%";
  return val.toFixed(3);
}

function getColor(val: number, min: number, max: number): string {
  if (max === min) return "rgba(99, 102, 241, 0.5)";
  const norm = (val - min) / (max - min); // 0..1
  // Interpolate: low → red(220°), mid → gold(45°), high → indigo(240°)
  const h = norm < 0.5 ? 0 + norm * 2 * 45 : 45 + (norm - 0.5) * 2 * 195;
  const s = 80;
  const l = 30 + norm * 20;
  return `hsl(${h}, ${s}%, ${l}%)`;
}

export default function SweepHeatmap({
  sweepResults,
  bestParams,
  paramGrid,
  objective,
  totalCombinations,
}: SweepHeatmapProps) {
  const paramKeys = Object.keys(paramGrid);
  const successResults = sweepResults.filter((r) => r.status === "SUCCESS" && r.metrics);

  // Determine axis params for 2D view (up to first 2 param keys)
  const xKey = paramKeys[0] ?? null;
  const yKey = paramKeys[1] ?? null;

  // Compute metric value range
  const metricValues = successResults
    .map((r) => r.metrics?.[objective] as number | undefined)
    .filter((v): v is number => v != null && !isNaN(v));
  const minVal = Math.min(...metricValues);
  const maxVal = Math.max(...metricValues);

  // Build heatmap data: for 1D or 2D grids
  const xValues = xKey ? [...new Set(successResults.map((r) => r.parameters[xKey]))] : [];
  const yValues = yKey ? [...new Set(successResults.map((r) => r.parameters[yKey]))] : [];

  // Best metric value
  const bestResult = successResults.reduce<SweepResultItem | null>((best, r) => {
    const v = r.metrics?.[objective] as number | undefined;
    const bv = best?.metrics?.[objective] as number | undefined;
    if (v == null) return best;
    if (bv == null || v > bv) return r;
    return best;
  }, null);

  const failedCount = sweepResults.filter((r) => r.status === "FAILURE").length;

  // Sorted results for table
  const sortedResults = useMemo(
    () =>
      [...successResults].sort(
        (a, b) =>
          ((b.metrics?.[objective] as number) ?? -Infinity) -
          ((a.metrics?.[objective] as number) ?? -Infinity)
      ),
    [successResults, objective]
  );

  if (sweepResults.length === 0) return null;

  return (
    <div className="sweep-wrap">
      {/* Summary header */}
      <div className="sweep-header">
        <div className="sweep-stat">
          <span className="sweep-stat-val">{totalCombinations}</span>
          <span className="sweep-stat-label">Total Combos</span>
        </div>
        <div className="sweep-stat">
          <span className="sweep-stat-val sweep-stat-success">{successResults.length}</span>
          <span className="sweep-stat-label">Succeeded</span>
        </div>
        {failedCount > 0 && (
          <div className="sweep-stat">
            <span className="sweep-stat-val sweep-stat-fail">{failedCount}</span>
            <span className="sweep-stat-label">Failed</span>
          </div>
        )}
        {bestResult && (
          <div className="sweep-stat sweep-stat-best">
            <span className="sweep-stat-val sweep-stat-gold">
              {formatMetricValue(bestResult.metrics?.[objective] as number, objective)}
            </span>
            <span className="sweep-stat-label">Best {formatMetricLabel(objective)}</span>
          </div>
        )}
      </div>

      {/* Best params pill */}
      {bestParams && Object.keys(bestParams).length > 0 && (
        <div className="best-params-row">
          <span className="best-params-label">Best Parameters:</span>
          {Object.entries(bestParams).map(([k, v]) => (
            <span key={k} className="best-param-pill">
              {k} = <strong>{String(v)}</strong>
            </span>
          ))}
        </div>
      )}

      {/* 2D Heatmap (when 2 params) */}
      {xKey && yKey && xValues.length > 0 && yValues.length > 0 && (
        <div className="heatmap-section">
          <h4 className="heatmap-title">
            {formatMetricLabel(objective)} Heatmap — {xKey} × {yKey}
          </h4>
          <div className="heatmap-scroll">
            <table className="heatmap-table">
              <thead>
                <tr>
                  <th className="heatmap-corner">
                    {yKey} ↓ / {xKey} →
                  </th>
                  {xValues.map((xv) => (
                    <th key={String(xv)} className="heatmap-th">
                      {String(xv)}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {yValues.map((yv) => (
                  <tr key={String(yv)}>
                    <td className="heatmap-row-header">{String(yv)}</td>
                    {xValues.map((xv) => {
                      const match = successResults.find(
                        (r) =>
                          r.parameters[xKey] == xv && r.parameters[yKey] == yv
                      );
                      const val = match?.metrics?.[objective] as number | undefined;
                      const isBest =
                        bestParams &&
                        bestParams[xKey] == xv &&
                        bestParams[yKey] == yv;
                      return (
                        <td
                          key={String(xv)}
                          className={`heatmap-cell ${isBest ? "heatmap-cell--best" : ""}`}
                          style={{
                            background:
                              val != null
                                ? getColor(val, minVal, maxVal)
                                : "rgba(255,255,255,0.03)",
                          }}
                          title={`${xKey}=${xv}, ${yKey}=${yv}: ${formatMetricValue(val, objective)}`}
                        >
                          {formatMetricValue(val, objective)}
                          {isBest && <span className="heatmap-star">★</span>}
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* 1D chart for single param */}
      {xKey && !yKey && xValues.length > 0 && (
        <div className="heatmap-section">
          <h4 className="heatmap-title">
            {formatMetricLabel(objective)} vs {xKey}
          </h4>
          <div className="bar-chart">
            {xValues.map((xv) => {
              const match = successResults.find((r) => r.parameters[xKey] == xv);
              const val = match?.metrics?.[objective] as number | undefined;
              const norm = val != null && maxVal !== minVal ? (val - minVal) / (maxVal - minVal) : 0;
              const isBest = bestParams && bestParams[xKey] == xv;
              return (
                <div key={String(xv)} className="bar-item">
                  <div className="bar-label">{String(xv)}</div>
                  <div className="bar-track">
                    <div
                      className={`bar-fill ${isBest ? "bar-fill--best" : ""}`}
                      style={{ width: `${Math.max(norm * 100, 2)}%`, background: getColor(val ?? minVal, minVal, maxVal) }}
                    />
                  </div>
                  <div className="bar-val">{formatMetricValue(val, objective)}</div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Results table */}
      <div className="heatmap-section">
        <h4 className="heatmap-title">All Combinations (Top {Math.min(sortedResults.length, 50)})</h4>
        <div className="sweep-table-wrap">
          <table className="sweep-table">
            <thead>
              <tr>
                <th>#</th>
                {paramKeys.map((k) => <th key={k}>{k}</th>)}
                <th>{formatMetricLabel(objective)}</th>
                <th>Total Return</th>
                <th>Max DD</th>
                <th>Trades</th>
              </tr>
            </thead>
            <tbody>
              {sortedResults.slice(0, 50).map((r, i) => {
                const isBest = r.parameters === bestParams ||
                  JSON.stringify(r.parameters) === JSON.stringify(bestParams);
                return (
                  <tr key={r.combo_index} className={isBest ? "sweep-row--best" : ""}>
                    <td className="sweep-td-rank">{i + 1}</td>
                    {paramKeys.map((k) => (
                      <td key={k} className="sweep-td-param">
                        {String(r.parameters[k] ?? "—")}
                      </td>
                    ))}
                    <td className="sweep-td-metric">
                      {formatMetricValue(r.metrics?.[objective] as number, objective)}
                      {isBest && <span className="sweep-best-star">★</span>}
                    </td>
                    <td className="sweep-td-metric">
                      {formatMetricValue(r.metrics?.total_return as number, "total_return")}
                    </td>
                    <td className="sweep-td-metric">
                      {formatMetricValue(r.metrics?.max_drawdown as number, "max_drawdown")}
                    </td>
                    <td className="sweep-td-metric">{r.metrics?.total_trades ?? "—"}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      <style jsx>{`
        .sweep-wrap {
          display: flex;
          flex-direction: column;
          gap: 24px;
        }
        .sweep-header {
          display: flex;
          flex-wrap: wrap;
          gap: 20px;
        }
        .sweep-stat {
          display: flex;
          flex-direction: column;
          align-items: center;
          background: rgba(255,255,255,0.04);
          border: 1px solid rgba(255,255,255,0.08);
          border-radius: 10px;
          padding: 12px 20px;
          min-width: 90px;
        }
        .sweep-stat-best {
          border-color: rgba(250,204,21,0.3);
          background: rgba(250,204,21,0.06);
        }
        .sweep-stat-val {
          font-size: 22px;
          font-weight: 700;
          color: #e5e7eb;
        }
        .sweep-stat-success { color: #34d399; }
        .sweep-stat-fail { color: #f87171; }
        .sweep-stat-gold { color: #fbbf24; }
        .sweep-stat-label {
          font-size: 11px;
          color: #6b7280;
          margin-top: 2px;
        }
        .best-params-row {
          display: flex;
          flex-wrap: wrap;
          align-items: center;
          gap: 8px;
          padding: 10px 14px;
          background: rgba(99,102,241,0.1);
          border: 1px solid rgba(99,102,241,0.25);
          border-radius: 8px;
        }
        .best-params-label {
          font-size: 12px;
          color: #a5b4fc;
          font-weight: 600;
        }
        .best-param-pill {
          font-size: 12px;
          background: rgba(99,102,241,0.2);
          border-radius: 12px;
          padding: 3px 10px;
          color: #c7d2fe;
        }
        .heatmap-section {
          display: flex;
          flex-direction: column;
          gap: 10px;
        }
        .heatmap-title {
          font-size: 12px;
          font-weight: 700;
          letter-spacing: 0.06em;
          text-transform: uppercase;
          color: #9ca3af;
          margin: 0;
        }
        .heatmap-scroll {
          overflow-x: auto;
        }
        .heatmap-table {
          border-collapse: collapse;
          font-size: 12px;
        }
        .heatmap-corner,
        .heatmap-th {
          padding: 6px 12px;
          background: rgba(255,255,255,0.04);
          color: #9ca3af;
          font-weight: 600;
          text-align: center;
          border: 1px solid rgba(255,255,255,0.06);
        }
        .heatmap-row-header {
          padding: 6px 12px;
          background: rgba(255,255,255,0.04);
          color: #9ca3af;
          font-weight: 600;
          text-align: right;
          border: 1px solid rgba(255,255,255,0.06);
        }
        .heatmap-cell {
          padding: 8px 14px;
          text-align: center;
          font-size: 12px;
          font-weight: 500;
          color: #fff;
          border: 1px solid rgba(255,255,255,0.06);
          transition: opacity 0.15s;
          position: relative;
          cursor: default;
        }
        .heatmap-cell--best {
          outline: 2px solid #fbbf24;
          outline-offset: -2px;
        }
        .heatmap-star {
          position: absolute;
          top: 2px;
          right: 4px;
          font-size: 9px;
          color: #fbbf24;
        }
        /* 1D bar chart */
        .bar-chart {
          display: flex;
          flex-direction: column;
          gap: 6px;
        }
        .bar-item {
          display: grid;
          grid-template-columns: 60px 1fr 70px;
          align-items: center;
          gap: 8px;
        }
        .bar-label {
          font-size: 12px;
          color: #9ca3af;
          text-align: right;
        }
        .bar-track {
          height: 18px;
          background: rgba(255,255,255,0.05);
          border-radius: 4px;
          overflow: hidden;
        }
        .bar-fill {
          height: 100%;
          border-radius: 4px;
          transition: width 0.3s;
          opacity: 0.85;
        }
        .bar-fill--best {
          outline: 2px solid #fbbf24;
          outline-offset: -2px;
          opacity: 1;
        }
        .bar-val {
          font-size: 12px;
          color: #e5e7eb;
          text-align: left;
        }
        /* Results table */
        .sweep-table-wrap {
          overflow-x: auto;
        }
        .sweep-table {
          width: 100%;
          border-collapse: collapse;
          font-size: 12px;
        }
        .sweep-table th {
          padding: 8px 12px;
          background: rgba(255,255,255,0.04);
          color: #9ca3af;
          font-weight: 700;
          text-align: left;
          border-bottom: 1px solid rgba(255,255,255,0.08);
          white-space: nowrap;
        }
        .sweep-table tr:hover td {
          background: rgba(255,255,255,0.03);
        }
        .sweep-row--best td {
          background: rgba(99,102,241,0.1) !important;
        }
        .sweep-td-rank {
          padding: 7px 12px;
          color: #6b7280;
          font-size: 11px;
          border-bottom: 1px solid rgba(255,255,255,0.04);
        }
        .sweep-td-param {
          padding: 7px 12px;
          color: #c7d2fe;
          font-weight: 600;
          border-bottom: 1px solid rgba(255,255,255,0.04);
        }
        .sweep-td-metric {
          padding: 7px 12px;
          color: #e5e7eb;
          border-bottom: 1px solid rgba(255,255,255,0.04);
          position: relative;
        }
        .sweep-best-star {
          color: #fbbf24;
          margin-left: 4px;
          font-size: 10px;
        }
      `}</style>
    </div>
  );
}
