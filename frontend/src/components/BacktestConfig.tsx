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

  return (
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
  );
}
