// frontend/src/components/BacktestConfig.tsx
"use client";

import { useBacktestStore } from "@/lib/store";

export default function BacktestConfig() {
  const config = useBacktestStore((s) => s.config);
  const setConfig = useBacktestStore((s) => s.setConfig);

  return (
    <div className="grid grid-cols-3 gap-3">
      <div>
        <label htmlFor="initial-capital" className="block text-xs font-medium text-gray-400 mb-1.5">
          Initial Capital ($)
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
    </div>
  );
}
