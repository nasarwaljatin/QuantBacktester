"use client";
// frontend/src/components/OptimizationConfig.tsx
// Parameter grid input panel and walk-forward settings for Phase 4

import { useBacktestStore, OptimizationMode } from "@/lib/store";
import { useState, useEffect, useCallback, useRef } from "react";
import { estimateWFA } from "@/lib/api";

/** Parse strategy code to extract param names from the `params = dict(...)` line. */
function extractParamNames(code: string): string[] {
  const match = code.match(/params\s*=\s*dict\(([^)]+)\)/);
  if (!match) return [];
  return match[1]
    .split(",")
    .map((kv) => kv.trim().split("=")[0].trim())
    .filter(Boolean);
}

/** Parse a raw string like "3, 5, 10" into an array of numbers/strings. */
export function parseRawValues(raw: string): (number | string)[] {
  return raw
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean)
    .map((v) => {
      const n = Number(v);
      return isNaN(n) ? v : n;
    });
}

/** Build a parsed param grid from raw strings. */
export function buildParamGrid(
  rawGrid: Record<string, string>
): Record<string, (number | string)[]> {
  const grid: Record<string, (number | string)[]> = {};
  for (const [k, v] of Object.entries(rawGrid)) {
    const parsed = parseRawValues(v);
    if (parsed.length > 0) grid[k] = parsed;
  }
  return grid;
}

const OBJECTIVES = [
  { value: "sharpe_ratio", label: "Sharpe Ratio" },
  { value: "total_return", label: "Total Return" },
  { value: "sortino_ratio", label: "Sortino Ratio" },
  { value: "calmar_ratio", label: "Calmar Ratio" },
  { value: "profit_factor", label: "Profit Factor" },
];

const MODE_OPTIONS: { value: OptimizationMode; label: string; desc: string }[] = [
  {
    value: "single",
    label: "Single Run",
    desc: "Run one backtest with fixed parameters",
  },
  {
    value: "sweep",
    label: "Parameter Sweep",
    desc: "Grid search all combinations — find the best parameters",
  },
  {
    value: "walk_forward",
    label: "Walk-Forward Analysis",
    desc: "Rolling IS/OOS windows — test for over-fitting",
  },
];

export default function OptimizationConfig() {
  const {
    strategyCode,
    optimizationMode,
    setOptimizationMode,
    paramGridRaw,
    setParamGridRaw,
    inSampleDays,
    setInSampleDays,
    outOfSampleDays,
    setOutOfSampleDays,
    wfaObjective,
    setWfaObjective,
    wfaWindowType,
    setWfaWindowType,
    wfaAnchored,
    setWfaAnchored,
    wfaMaxCombinations,
    setWfaMaxCombinations,
    wfaEstimate,
    setWfaEstimate,
    tickers,
    startDate,
    endDate,
  } = useBacktestStore();

  const [detectedParams, setDetectedParams] = useState<string[]>([]);
  const estimateTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Re-detect params whenever strategy code changes
  useEffect(() => {
    const names = extractParamNames(strategyCode);
    setDetectedParams(names);
    // Seed empty raw entries for newly detected params
    setParamGridRaw(
      Object.fromEntries(
        names.map((n) => [n, paramGridRaw[n] ?? ""])
      )
    );
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [strategyCode]);

  // Debounced pre-flight estimate (only in WFA mode)
  const runEstimate = useCallback(() => {
    if (optimizationMode !== "walk_forward") return;
    const paramGrid: Record<string, (number | string)[]> = {};
    for (const [k, v] of Object.entries(paramGridRaw)) {
      const vals = parseRawValues(v);
      if (vals.length > 0) paramGrid[k] = vals;
    }
    if (Object.keys(paramGrid).length === 0) {
      setWfaEstimate(null);
      return;
    }
    estimateWFA({
      tickers: tickers.length > 0 ? tickers : ["AAPL"],
      start_date: startDate,
      end_date: endDate,
      param_grid: paramGrid,
      in_sample_days: inSampleDays,
      out_of_sample_days: outOfSampleDays,
      window_type: wfaWindowType,
      anchored: wfaAnchored,
      max_combinations: wfaMaxCombinations,
    })
      .then(setWfaEstimate)
      .catch(() => setWfaEstimate(null));
  }, [
    optimizationMode, paramGridRaw, tickers, startDate, endDate,
    inSampleDays, outOfSampleDays, wfaWindowType, wfaAnchored, wfaMaxCombinations,
    setWfaEstimate,
  ]);

  useEffect(() => {
    if (estimateTimerRef.current) clearTimeout(estimateTimerRef.current);
    estimateTimerRef.current = setTimeout(runEstimate, 600);
    return () => {
      if (estimateTimerRef.current) clearTimeout(estimateTimerRef.current);
    };
  }, [runEstimate]);

  const totalCombinations = Object.values(paramGridRaw).reduce((acc, raw) => {
    const cnt = parseRawValues(raw).length || 1;
    return acc * cnt;
  }, 1);

  if (optimizationMode === "single") {
    // Only show mode selector
    return (
      <div className="opt-config">
        <ModeSelector />
      </div>
    );
  }

  return (
    <div className="opt-config">
      <ModeSelector />

      {/* Parameter grid */}
      <div className="opt-section">
        <h4 className="opt-section-title">Parameter Grid</h4>
        {detectedParams.length === 0 ? (
          <p className="opt-hint">
            No <code>params = dict(...)</code> detected in strategy. Add named
            params to use the optimizer.
          </p>
        ) : (
          <>
            <p className="opt-hint">
              Enter comma-separated candidate values for each parameter
              (e.g.&nbsp;<code>3, 5, 10</code>).
            </p>
            <div className="opt-grid-inputs">
              {detectedParams.map((param) => (
                <div key={param} className="opt-grid-row">
                  <label className="opt-param-label">{param}</label>
                  <input
                    id={`param-grid-${param}`}
                    className="opt-param-input"
                    type="text"
                    placeholder="e.g. 3, 5, 10, 20"
                    value={paramGridRaw[param] ?? ""}
                    onChange={(e) =>
                      setParamGridRaw({ ...paramGridRaw, [param]: e.target.value })
                    }
                  />
                </div>
              ))}
            </div>
            <div className="opt-combos-badge">
              <span className="opt-combos-num">{totalCombinations}</span>
              &nbsp;combination{totalCombinations !== 1 ? "s" : ""} total
            </div>
          </>
        )}
      </div>

      {/* Objective */}
      <div className="opt-section">
        <h4 className="opt-section-title">Optimization Objective</h4>
        <select
          id="opt-objective"
          className="opt-select"
          value={wfaObjective}
          onChange={(e) => setWfaObjective(e.target.value)}
        >
          {OBJECTIVES.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </select>
      </div>

      {/* Walk-Forward specific settings */}
      {optimizationMode === "walk_forward" && (
        <div className="opt-section">
          <h4 className="opt-section-title">Walk-Forward Settings</h4>
          <div className="opt-wfa-grid">
            <div className="opt-wfa-row">
              <label htmlFor="wfa-is-days" className="opt-param-label">
                In-Sample Days
              </label>
              <input
                id="wfa-is-days"
                className="opt-param-input"
                type="number"
                min={30}
                step={30}
                value={inSampleDays}
                onChange={(e) => setInSampleDays(Number(e.target.value))}
              />
            </div>
            <div className="opt-wfa-row">
              <label htmlFor="wfa-oos-days" className="opt-param-label">
                Out-of-Sample Days
              </label>
              <input
                id="wfa-oos-days"
                className="opt-param-input"
                type="number"
                min={7}
                step={7}
                value={outOfSampleDays}
                onChange={(e) => setOutOfSampleDays(Number(e.target.value))}
              />
            </div>
            <div className="opt-wfa-row">
              <label className="opt-param-label">Window Type</label>
              <div className="wfa-pill-row">
                {(["rolling", "expanding"] as const).map((t) => (
                  <button
                    key={t}
                    id={`wfa-window-type-${t}`}
                    className={`wfa-pill ${wfaWindowType === t ? "wfa-pill--active" : ""}`}
                    onClick={() => setWfaWindowType(t)}
                  >
                    {t.charAt(0).toUpperCase() + t.slice(1)}
                  </button>
                ))}
              </div>
            </div>
            {wfaWindowType === "rolling" && (
              <div className="opt-wfa-row">
                <label htmlFor="wfa-anchored" className="opt-param-label">
                  Anchored
                  <span
                    className="wfa-tooltip-anchor"
                    title="Anchored rolling: IS start is pinned to the first fold. IS grows each fold instead of sliding. Equivalent to anchored walk-forward."
                  >
                    &nbsp;ⓘ
                  </span>
                </label>
                <label className="wfa-toggle">
                  <input
                    id="wfa-anchored"
                    type="checkbox"
                    checked={wfaAnchored}
                    onChange={(e) => setWfaAnchored(e.target.checked)}
                  />
                  <span className="wfa-toggle-track" />
                  <span className="wfa-toggle-label">
                    {wfaAnchored ? "On" : "Off"}
                  </span>
                </label>
              </div>
            )}
            <div className="opt-wfa-row">
              <label htmlFor="wfa-max-combos" className="opt-param-label">
                Max Runs Cap
                <span
                  className="wfa-tooltip-anchor"
                  title="Hard cap on total backtest runs (folds × combos). Submissions exceeding this cap are rejected."
                >
                  &nbsp;ⓘ
                </span>
              </label>
              <input
                id="wfa-max-combos"
                className="opt-param-input"
                type="number"
                min={1}
                max={5000}
                step={50}
                value={wfaMaxCombinations}
                onChange={(e) => setWfaMaxCombinations(Number(e.target.value))}
              />
            </div>
          </div>

          {/* Pre-flight estimate badge */}
          {wfaEstimate && (
            <div
              className={`wfa-estimate-badge ${
                wfaEstimate.error
                  ? "wfa-estimate-badge--error"
                  : !wfaEstimate.feasible
                  ? "wfa-estimate-badge--warn"
                  : "wfa-estimate-badge--ok"
              }`}
            >
              {wfaEstimate.error ? (
                <span>⚠ {wfaEstimate.error}</span>
              ) : (
                <span>
                  {!wfaEstimate.feasible ? "🔴 " : "🟢 "}
                  <strong>~{wfaEstimate.total_runs.toLocaleString()}</strong> backtests
                  &nbsp;({wfaEstimate.n_folds} folds × {wfaEstimate.n_combinations} combos)
                  {!wfaEstimate.feasible && ` — exceeds cap of ${wfaMaxCombinations}`}
                </span>
              )}
            </div>
          )}

          <p className="opt-hint">
            Each window uses <strong>{inSampleDays}</strong> in-sample days to
            find the best parameters, then evaluates them on the following{" "}
            <strong>{outOfSampleDays}</strong> out-of-sample days.
            {wfaWindowType === "expanding" && (
              <> The IS period <strong>grows</strong> from the start date each fold.
              &nbsp;OOS length stays fixed.</>)}
            {wfaWindowType === "rolling" && wfaAnchored && (
              <> IS start is <strong>anchored</strong> to fold 1; IS grows while OOS slides.</>)}
          </p>
        </div>
      )}

      <style jsx>{`
        .opt-config {
          display: flex;
          flex-direction: column;
          gap: 16px;
        }
        .opt-section {
          display: flex;
          flex-direction: column;
          gap: 8px;
        }
        .opt-section-title {
          font-size: 11px;
          font-weight: 700;
          letter-spacing: 0.08em;
          text-transform: uppercase;
          color: var(--color-muted, #9ca3af);
          margin: 0;
        }
        .opt-hint {
          font-size: 12px;
          color: var(--color-muted, #9ca3af);
          margin: 0;
          line-height: 1.5;
        }
        .opt-hint code {
          background: rgba(99, 102, 241, 0.12);
          padding: 1px 4px;
          border-radius: 3px;
          font-size: 11px;
        }
        .opt-grid-inputs {
          display: flex;
          flex-direction: column;
          gap: 8px;
        }
        .opt-grid-row,
        .opt-wfa-row {
          display: grid;
          grid-template-columns: 100px 1fr;
          align-items: center;
          gap: 8px;
        }
        .opt-param-label {
          font-size: 12px;
          font-weight: 600;
          color: var(--color-text, #e5e7eb);
        }
        .opt-param-input {
          background: rgba(255, 255, 255, 0.05);
          border: 1px solid rgba(255, 255, 255, 0.1);
          border-radius: 6px;
          padding: 6px 10px;
          font-size: 12px;
          color: var(--color-text, #e5e7eb);
          outline: none;
          transition: border-color 0.2s;
          width: 100%;
          box-sizing: border-box;
        }
        .opt-param-input:focus {
          border-color: #6366f1;
        }
        .opt-combos-badge {
          font-size: 12px;
          color: #a5b4fc;
          margin-top: 4px;
          display: flex;
          align-items: center;
          gap: 4px;
        }
        .opt-combos-num {
          font-size: 16px;
          font-weight: 700;
          color: #6366f1;
        }
        .opt-select {
          background: rgba(255, 255, 255, 0.05);
          border: 1px solid rgba(255, 255, 255, 0.1);
          border-radius: 6px;
          padding: 7px 10px;
          font-size: 13px;
          color: var(--color-text, #e5e7eb);
          outline: none;
          cursor: pointer;
          transition: border-color 0.2s;
        }
        .opt-select:focus {
          border-color: #6366f1;
        }
        .opt-wfa-grid {
          display: flex;
          flex-direction: column;
          gap: 8px;
        }
        .wfa-pill-row {
          display: flex;
          gap: 6px;
        }
        .wfa-pill {
          padding: 4px 12px;
          border-radius: 20px;
          border: 1px solid rgba(255,255,255,0.12);
          background: transparent;
          color: #9ca3af;
          font-size: 11px;
          font-weight: 600;
          cursor: pointer;
          transition: all 0.2s;
        }
        .wfa-pill:hover { border-color: #6366f1; color: #a5b4fc; }
        .wfa-pill--active {
          background: linear-gradient(135deg, #4f46e5, #7c3aed);
          border-color: transparent;
          color: #fff;
        }
        .wfa-toggle {
          display: flex;
          align-items: center;
          gap: 8px;
          cursor: pointer;
          user-select: none;
        }
        .wfa-toggle input { display: none; }
        .wfa-toggle-track {
          width: 36px; height: 20px;
          border-radius: 10px;
          background: rgba(255,255,255,0.1);
          border: 1px solid rgba(255,255,255,0.15);
          position: relative;
          transition: background 0.2s;
        }
        .wfa-toggle input:checked + .wfa-toggle-track {
          background: linear-gradient(135deg, #4f46e5, #7c3aed);
          border-color: transparent;
        }
        .wfa-toggle-track::after {
          content: '';
          position: absolute;
          top: 2px; left: 2px;
          width: 14px; height: 14px;
          border-radius: 50%;
          background: #fff;
          transition: transform 0.2s;
        }
        .wfa-toggle input:checked + .wfa-toggle-track::after {
          transform: translateX(16px);
        }
        .wfa-toggle-label { font-size: 12px; color: #9ca3af; }
        .wfa-tooltip-anchor { color: #6366f1; cursor: help; font-size: 11px; }
        .wfa-estimate-badge {
          font-size: 12px;
          padding: 8px 12px;
          border-radius: 8px;
          margin-top: 6px;
          border: 1px solid;
          line-height: 1.5;
        }
        .wfa-estimate-badge--ok {
          background: rgba(34,197,94,0.08);
          border-color: rgba(34,197,94,0.25);
          color: #86efac;
        }
        .wfa-estimate-badge--warn {
          background: rgba(239,68,68,0.08);
          border-color: rgba(239,68,68,0.25);
          color: #fca5a5;
        }
        .wfa-estimate-badge--error {
          background: rgba(245,158,11,0.08);
          border-color: rgba(245,158,11,0.25);
          color: #fcd34d;
        }
      `}</style>
    </div>
  );
}

function ModeSelector() {
  const { optimizationMode, setOptimizationMode } = useBacktestStore();
  return (
    <div className="mode-selector">
      {MODE_OPTIONS.map((opt) => (
        <button
          key={opt.value}
          id={`opt-mode-${opt.value}`}
          className={`mode-btn ${optimizationMode === opt.value ? "mode-btn--active" : ""}`}
          onClick={() => setOptimizationMode(opt.value)}
          title={opt.desc}
        >
          {opt.label}
        </button>
      ))}
      <style jsx>{`
        .mode-selector {
          display: flex;
          gap: 6px;
          flex-wrap: wrap;
        }
        .mode-btn {
          padding: 6px 12px;
          border-radius: 20px;
          border: 1px solid rgba(255, 255, 255, 0.12);
          background: transparent;
          color: #9ca3af;
          font-size: 12px;
          font-weight: 500;
          cursor: pointer;
          transition: all 0.2s;
          white-space: nowrap;
        }
        .mode-btn:hover {
          border-color: #6366f1;
          color: #a5b4fc;
        }
        .mode-btn--active {
          background: linear-gradient(135deg, #4f46e5, #7c3aed);
          border-color: transparent;
          color: #fff;
          box-shadow: 0 2px 8px rgba(99, 102, 241, 0.4);
        }
      `}</style>
    </div>
  );
}
