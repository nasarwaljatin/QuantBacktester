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
    <div className="flex flex-col gap-4">
      {/* Core Backtest Config */}
      <div className="grid grid-cols-5 gap-3">
        <div>
          <label htmlFor="currency" className="block text-xs font-medium text-gray-400 mb-1.5">
            Currency
          </label>
          <select
            id="currency"
            value={currency}
            onChange={(e) => setCurrency(e.target.value)}
            className="w-full bg-gray-800/80 border border-gray-600/50 rounded-lg px-3 py-2.5 text-sm text-white focus:outline-none focus:ring-2 focus:ring-cyan-500/50 focus:border-cyan-500/50 backdrop-blur-sm transition-all"
          >
            {currencyOptions.map((opt) => (
              <option key={opt.value} value={opt.value} className="bg-gray-900">
                {opt.label}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label htmlFor="initial-capital" className="block text-xs font-medium text-gray-400 mb-1.5">
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
            className="w-full bg-gray-800/80 border border-gray-600/50 rounded-lg px-3 py-2.5 text-sm text-white focus:outline-none focus:ring-2 focus:ring-cyan-500/50 focus:border-cyan-500/50 backdrop-blur-sm transition-all"
          />
        </div>
        <div>
          <label htmlFor="commission" className="block text-xs font-medium text-gray-400 mb-1.5">
            Commission (%)
          </label>
          <input
            id="commission"
            type="number"
            value={(config.commission * 100).toFixed(2)}
            onChange={(e) => setConfig({ commission: Number(e.target.value) / 100 })}
            min={0}
            max={10}
            step={0.01}
            className="w-full bg-gray-800/80 border border-gray-600/50 rounded-lg px-3 py-2.5 text-sm text-white focus:outline-none focus:ring-2 focus:ring-cyan-500/50 focus:border-cyan-500/50 backdrop-blur-sm transition-all"
          />
        </div>
        <div>
          <label htmlFor="slippage" className="block text-xs font-medium text-gray-400 mb-1.5">
            Slippage (%)
          </label>
          <input
            id="slippage"
            type="number"
            value={(config.slippage * 100).toFixed(2)}
            onChange={(e) => setConfig({ slippage: Number(e.target.value) / 100 })}
            min={0}
            max={5}
            step={0.01}
            className="w-full bg-gray-800/80 border border-gray-600/50 rounded-lg px-3 py-2.5 text-sm text-white focus:outline-none focus:ring-2 focus:ring-cyan-500/50 focus:border-cyan-500/50 backdrop-blur-sm transition-all"
          />
        </div>
        <div>
          <label htmlFor="allocation-pct" className="block text-xs font-medium text-gray-400 mb-1.5">
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
            className="w-full bg-gray-800/80 border border-gray-600/50 rounded-lg px-3 py-2.5 text-sm text-white focus:outline-none focus:ring-2 focus:ring-cyan-500/50 focus:border-cyan-500/50 backdrop-blur-sm transition-all"
          />
        </div>
      </div>

      {/* Position Sizing Selector Card */}
      <div className="bg-gray-900/40 border border-gray-800 rounded-xl p-4 flex flex-col md:flex-row gap-4 items-start md:items-center justify-between backdrop-blur-md">
        <div className="w-full md:w-1/3">
          <label htmlFor="sizing-model" className="block text-xs font-medium text-cyan-400/80 uppercase tracking-wider mb-1.5">
            Position Sizing Model
          </label>
          <select
            id="sizing-model"
            value={sizingModel}
            onChange={(e) => handleSizingModelChange(e.target.value)}
            className="w-full bg-gray-800/80 border border-gray-600/30 rounded-lg px-3 py-2.5 text-sm text-white focus:outline-none focus:ring-2 focus:ring-cyan-500/50 focus:border-cyan-500/50 backdrop-blur-sm transition-all"
          >
            {sizingModelOptions.map((opt) => (
              <option key={opt.value} value={opt.value} className="bg-gray-900">
                {opt.label}
              </option>
            ))}
          </select>
        </div>

        {/* Dynamic Model Parameters */}
        <div className="flex-1 w-full grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">
          {sizingModel === "fixed_fractional" && (
            <div>
              <label htmlFor="risk-pct" className="block text-xs font-medium text-gray-400 mb-1.5">
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
                className="w-full bg-gray-800/60 border border-gray-700/50 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:ring-1 focus:ring-cyan-500/50 focus:border-cyan-500/50 backdrop-blur-sm transition-all"
              />
            </div>
          )}

          {sizingModel === "volatility_targeted" && (
            <>
              <div>
                <label htmlFor="target-risk-pct" className="block text-xs font-medium text-gray-400 mb-1.5">
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
                  className="w-full bg-gray-800/60 border border-gray-700/50 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:ring-1 focus:ring-cyan-500/50 focus:border-cyan-500/50 backdrop-blur-sm transition-all"
                />
              </div>
              <div>
                <label htmlFor="atr-period" className="block text-xs font-medium text-gray-400 mb-1.5">
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
                  className="w-full bg-gray-800/60 border border-gray-700/50 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:ring-1 focus:ring-cyan-500/50 focus:border-cyan-500/50 backdrop-blur-sm transition-all"
                />
              </div>
            </>
          )}

          {sizingModel === "kelly" && (
            <>
              <div>
                <label htmlFor="kelly-multiplier" className="block text-xs font-medium text-gray-400 mb-1.5">
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
                  className="w-full bg-gray-800/60 border border-gray-700/50 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:ring-1 focus:ring-cyan-500/50 focus:border-cyan-500/50 backdrop-blur-sm transition-all"
                />
              </div>
              <div>
                <label htmlFor="max-fraction" className="block text-xs font-medium text-gray-400 mb-1.5">
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
                  className="w-full bg-gray-800/60 border border-gray-700/50 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:ring-1 focus:ring-cyan-500/50 focus:border-cyan-500/50 backdrop-blur-sm transition-all"
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
    </div>
  );
}
