// frontend/src/components/BacktestConfig.tsx
"use client";

import { useBacktestStore } from "@/lib/store";

export default function BacktestConfig() {
  const config = useBacktestStore((s) => s.config);
  const setConfig = useBacktestStore((s) => s.setConfig);
  const currency = useBacktestStore((s) => s.currency);
  const setCurrency = useBacktestStore((s) => s.setCurrency);

  const currencyOptions = [
    { value: "$", label: "USD ($)" },
    { value: "₹", label: "INR (₹)" },
    { value: "€", label: "EUR (€)" },
    { value: "£", label: "GBP (£)" },
    { value: "¥", label: "JPY (¥)" },
  ];

  const sizingModelOptions = [
    { value: "all_in", label: "All-in (Default)" },
    { value: "fixed_fractional", label: "Fixed Fractional" },
    { value: "volatility_targeted", label: "Volatility-Targeted" },
    { value: "kelly", label: "Kelly Criterion" },
  ];

  const commissionTypeOptions = [
    { value: "percent", label: "Percentage (%)" },
    { value: "per_share", label: "Per Share / Contract" },
    { value: "tiered", label: "Tiered Per Share" },
  ];

  const slippageTypeOptions = [
    { value: "percent", label: "Percentage (%)" },
    { value: "points", label: "Price Points / Ticks" },
  ];

  const handleSizingModelChange = (model: string) => {
    let defaultParams: Record<string, any> = {};
    if (model === "fixed_fractional") {
      defaultParams = { risk_pct: 2.0 };
    } else if (model === "volatility_targeted") {
      defaultParams = { target_risk_pct: 1.0, atr_period: 14 };
    } else if (model === "kelly") {
      defaultParams = {
        kelly_multiplier: 0.5,
        max_fraction: 0.20,
        default_win_rate: 0.50,
        default_win_loss: 1.5,
      };
    }
    setConfig({ sizing_model: model, sizing_params: defaultParams });
  };

  const updateParam = (key: string, value: number) => {
    setConfig({
      sizing_params: {
        ...(config.sizing_params || {}),
        [key]: value,
      },
    });
  };

  const sizingModel = config.sizing_model || "all_in";
  const sizingParams = config.sizing_params || {};

  return (
    <div className="flex flex-col gap-5">
      {/* 1. Core Capital & Allocation Config */}
      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
        <div>
          <label htmlFor="currency" className="block text-xs font-semibold text-gray-500 dark:text-gray-400 mb-1.5 uppercase tracking-wide">
            Currency
          </label>
          <select
            id="currency"
            value={currency}
            onChange={(e) => setCurrency(e.target.value)}
            className="backtest-input"
          >
            {currencyOptions.map((opt) => (
              <option key={opt.value} value={opt.value} className="bg-white dark:bg-gray-900 text-slate-800 dark:text-white">
                {opt.label}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label htmlFor="initial-capital" className="block text-xs font-semibold text-gray-500 dark:text-gray-400 mb-1.5 uppercase tracking-wide">
            Initial Capital ({currency})
          </label>
          <input
            id="initial-capital"
            type="number"
            value={config.initial_capital}
            onChange={(e) => setConfig({ initial_capital: Number(e.target.value) })}
            min={1000}
            max={100000000}
            step={1000}
            className="backtest-input"
          />
        </div>
        <div>
          <label htmlFor="allocation-pct" className="block text-xs font-semibold text-gray-500 dark:text-gray-400 mb-1.5 uppercase tracking-wide">
            Capital Allocation (%)
          </label>
          <input
            id="allocation-pct"
            type="number"
            value={config.allocation_pct ?? 100}
            onChange={(e) => setConfig({ allocation_pct: Number(e.target.value) })}
            min={1}
            max={100}
            step={1}
            className="backtest-input"
          />
        </div>
      </div>

      {/* 2. Position Sizing Model Card */}
      <div className="bg-slate-100/80 dark:bg-gray-900/40 border border-gray-200 dark:border-gray-800/80 rounded-xl p-4 flex flex-col lg:flex-row gap-4 items-start lg:items-center justify-between backdrop-blur-md transition-colors duration-300">
        <div className="w-full lg:w-1/3">
          <label htmlFor="sizing-model" className="block text-xs font-semibold text-cyan-600 dark:text-cyan-400/80 uppercase tracking-wider mb-1.5">
            Position Sizing Model
          </label>
          <select
            id="sizing-model"
            value={sizingModel}
            onChange={(e) => handleSizingModelChange(e.target.value)}
            className="backtest-input"
          >
            {sizingModelOptions.map((opt) => (
              <option key={opt.value} value={opt.value} className="bg-white dark:bg-gray-900 text-slate-800 dark:text-white">
                {opt.label}
              </option>
            ))}
          </select>
        </div>

        {/* Dynamic Model Parameters */}
        <div className="flex-1 w-full grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">
          {sizingModel === "fixed_fractional" && (
            <div>
              <label htmlFor="risk-pct" className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1.5">
                Risk % per Trade
              </label>
              <input
                id="risk-pct"
                type="number"
                value={sizingParams.risk_pct ?? 2.0}
                onChange={(e) => updateParam("risk_pct", Number(e.target.value))}
                min={0.1}
                max={10.0}
                step={0.1}
                className="backtest-input py-2"
              />
            </div>
          )}

          {sizingModel === "volatility_targeted" && (
            <>
              <div>
                <label htmlFor="target-risk-pct" className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1.5">
                  Target Risk %
                </label>
                <input
                  id="target-risk-pct"
                  type="number"
                  value={sizingParams.target_risk_pct ?? 1.0}
                  onChange={(e) => updateParam("target_risk_pct", Number(e.target.value))}
                  min={0.1}
                  max={5.0}
                  step={0.1}
                  className="backtest-input py-2"
                />
              </div>
              <div>
                <label htmlFor="atr-period" className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1.5">
                  ATR Period (days)
                </label>
                <input
                  id="atr-period"
                  type="number"
                  value={sizingParams.atr_period ?? 14}
                  onChange={(e) => updateParam("atr_period", Number(e.target.value))}
                  min={2}
                  max={100}
                  step={1}
                  className="backtest-input py-2"
                />
              </div>
            </>
          )}

          {sizingModel === "kelly" && (
            <>
              <div>
                <label htmlFor="kelly-multiplier" className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1.5">
                  Kelly Multiplier (Half Kelly = 0.5)
                </label>
                <input
                  id="kelly-multiplier"
                  type="number"
                  value={sizingParams.kelly_multiplier ?? 0.5}
                  onChange={(e) => updateParam("kelly_multiplier", Number(e.target.value))}
                  min={0.05}
                  max={2.0}
                  step={0.05}
                  className="backtest-input py-2"
                />
              </div>
              <div>
                <label htmlFor="max-fraction" className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1.5">
                  Max Equity Fraction (%)
                </label>
                <input
                  id="max-fraction"
                  type="number"
                  value={((sizingParams.max_fraction ?? 0.20) * 100).toFixed(0)}
                  onChange={(e) => updateParam("max_fraction", Number(e.target.value) / 100)}
                  min={1}
                  max={100}
                  step={1}
                  className="backtest-input py-2"
                />
              </div>
            </>
          )}

          {sizingModel === "all_in" && (
            <div className="col-span-3 flex items-center h-full pt-4">
              <p className="text-xs text-gray-500 italic">
                Allocates the full global Capital Allocation percentage per trade.
              </p>
            </div>
          )}
        </div>
      </div>

      {/* 3. Execution Modeling (Commissions, Slippage, Bid-Ask, Fills) */}
      <div className="bg-gray-900/40 border border-gray-800 rounded-xl p-4 flex flex-col gap-4 backdrop-blur-md">
        <h4 className="text-xs font-semibold text-cyan-600 dark:text-cyan-400/80 uppercase tracking-wider">
          Realistic Execution Modeling
        </h4>

        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4">
          {/* Commission Configuration */}
          <div className="flex flex-col gap-3 p-3 bg-gray-900/30 border border-gray-800/60 rounded-lg">
            <div>
              <label htmlFor="commission-type" className="block text-xs text-gray-500 dark:text-gray-400 mb-1">
                Commission Type
              </label>
              <select
                id="commission-type"
                value={config.commission_type || "percent"}
                onChange={(e) => setConfig({ commission_type: e.target.value })}
                className="backtest-sub-input"
              >
                {commissionTypeOptions.map((opt) => (
                  <option key={opt.value} value={opt.value} className="bg-white dark:bg-gray-900 text-slate-800 dark:text-white">
                    {opt.label}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label htmlFor="commission-value" className="block text-xs text-gray-500 dark:text-gray-400 mb-1">
                {config.commission_type === "percent"
                  ? "Commission Rate (%)"
                  : `Comm. per Share (${currency})`}
              </label>
              <input
                id="commission-value"
                type="number"
                value={
                  config.commission_type === "percent"
                    ? ((config.commission_value ?? 0.001) * 100).toFixed(2)
                    : (config.commission_value ?? 0.005)
                }
                onChange={(e) =>
                  setConfig({
                    commission_value:
                      config.commission_type === "percent"
                        ? Number(e.target.value) / 100
                        : Number(e.target.value),
                    // Keep the backward-compatible variable in sync if percent type
                    commission:
                      config.commission_type === "percent"
                        ? Number(e.target.value) / 100
                        : config.commission,
                  })
                }
                min={0}
                step={config.commission_type === "percent" ? 0.01 : 0.001}
                className="backtest-sub-input"
              />
            </div>
          </div>

          {/* Conditional Tiered Fields */}
          {config.commission_type === "tiered" && (
            <div className="flex flex-col gap-3 p-3 bg-gray-900/30 border border-gray-800/60 rounded-lg">
              <div>
                <label htmlFor="commission-tier-limit" className="block text-xs text-gray-500 dark:text-gray-400 mb-1">
                  Tier Threshold (shares)
                </label>
                <input
                  id="commission-tier-limit"
                  type="number"
                  value={config.commission_tier_limit ?? 1000}
                  onChange={(e) => setConfig({ commission_tier_limit: Number(e.target.value) })}
                  min={0}
                  step={100}
                  className="backtest-sub-input"
                />
              </div>
              <div>
                <label htmlFor="commission-tier-value" className="block text-xs text-gray-500 dark:text-gray-400 mb-1">
                  Tier Rate per Share ({currency})
                </label>
                <input
                  id="commission-tier-value"
                  type="number"
                  value={config.commission_tier_value ?? 0.003}
                  onChange={(e) => setConfig({ commission_tier_value: Number(e.target.value) })}
                  min={0}
                  step={0.001}
                  className="backtest-sub-input"
                />
              </div>
            </div>
          )}

          {/* Slippage Configuration */}
          <div className="flex flex-col gap-3 p-3 bg-gray-900/30 border border-gray-800/60 rounded-lg">
            <div>
              <label htmlFor="slippage-type" className="block text-xs text-gray-500 dark:text-gray-400 mb-1">
                Slippage Model
              </label>
              <select
                id="slippage-type"
                value={config.slippage_type || "percent"}
                onChange={(e) => setConfig({ slippage_type: e.target.value })}
                className="backtest-sub-input"
              >
                {slippageTypeOptions.map((opt) => (
                  <option key={opt.value} value={opt.value} className="bg-white dark:bg-gray-900 text-slate-800 dark:text-white">
                    {opt.label}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label htmlFor="slippage-value" className="block text-xs text-gray-500 dark:text-gray-400 mb-1">
                {config.slippage_type === "percent"
                  ? "Slippage Rate (%)"
                  : `Slippage in Points (${currency})`}
              </label>
              <input
                id="slippage-value"
                type="number"
                value={
                  config.slippage_type === "percent"
                    ? ((config.slippage_value ?? 0.0005) * 100).toFixed(4)
                    : (config.slippage_value ?? 0.05)
                }
                onChange={(e) =>
                  setConfig({
                    slippage_value:
                      config.slippage_type === "percent"
                        ? Number(e.target.value) / 100
                        : Number(e.target.value),
                    // Keep the backward-compatible variable in sync if percent type
                    slippage:
                      config.slippage_type === "percent"
                        ? Number(e.target.value) / 100
                        : config.slippage,
                  })
                }
                min={0}
                step={config.slippage_type === "percent" ? 0.001 : 0.01}
                className="backtest-sub-input"
              />
            </div>
          </div>

          {/* Bid-Ask Spread & Partial Fill volume limit */}
          <div className="flex flex-col gap-3 p-3 bg-gray-900/30 border border-gray-800/60 rounded-lg">
            <div>
              <label htmlFor="spread" className="block text-xs text-gray-500 dark:text-gray-400 mb-1">
                Bid-Ask Spread (price points)
              </label>
              <input
                id="spread"
                type="number"
                value={config.spread ?? 0.0}
                onChange={(e) => setConfig({ spread: Number(e.target.value) })}
                min={0}
                step={0.01}
                placeholder="e.g. 0.02"
                className="backtest-sub-input"
              />
            </div>
            <div>
              <label htmlFor="volume-limit-pct" className="block text-xs text-gray-500 dark:text-gray-400 mb-1">
                Volume limit per Bar (%)
              </label>
              <input
                id="volume-limit-pct"
                type="number"
                value={config.volume_limit_pct === null ? "" : config.volume_limit_pct}
                onChange={(e) =>
                  setConfig({
                    volume_limit_pct: e.target.value === "" ? null : Number(e.target.value),
                  })
                }
                min={0.1}
                max={100}
                step={0.1}
                placeholder="Unlimited"
                className="backtest-sub-input"
              />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
