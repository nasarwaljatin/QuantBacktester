// frontend/src/components/DateRangePicker.tsx
"use client";

import { useBacktestStore } from "@/lib/store";

export default function DateRangePicker() {
  const startDate = useBacktestStore((s) => s.startDate);
  const endDate = useBacktestStore((s) => s.endDate);
  const setStartDate = useBacktestStore((s) => s.setStartDate);
  const setEndDate = useBacktestStore((s) => s.setEndDate);

  return (
    <div className="grid grid-cols-2 gap-3">
      <div>
        <label htmlFor="start-date" className="block text-xs font-medium text-gray-400 mb-1.5">
          Start Date
        </label>
        <input
          id="start-date"
          type="date"
          value={startDate}
          onChange={(e) => setStartDate(e.target.value)}
          className="w-full bg-gray-800/80 border border-gray-600/50 rounded-lg px-3 py-2.5 text-sm text-white focus:outline-none focus:ring-2 focus:ring-cyan-500/50 focus:border-cyan-500/50 backdrop-blur-sm transition-all"
        />
      </div>
      <div>
        <label htmlFor="end-date" className="block text-xs font-medium text-gray-400 mb-1.5">
          End Date
        </label>
        <input
          id="end-date"
          type="date"
          value={endDate}
          onChange={(e) => setEndDate(e.target.value)}
          className="w-full bg-gray-800/80 border border-gray-600/50 rounded-lg px-3 py-2.5 text-sm text-white focus:outline-none focus:ring-2 focus:ring-cyan-500/50 focus:border-cyan-500/50 backdrop-blur-sm transition-all"
        />
      </div>
    </div>
  );
}
