// frontend/src/components/TradeLogTable.tsx
"use client";

import { useState } from "react";
import type { TradeRecord } from "@/types/backtest";

interface TradeLogTableProps {
  trades: TradeRecord[];
}

const PAGE_SIZE = 20;

export default function TradeLogTable({ trades }: TradeLogTableProps) {
  const [page, setPage] = useState(0);
  const totalPages = Math.ceil(trades.length / PAGE_SIZE);
  const paginated = trades.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE);

  return (
    <div className="bg-gray-800/40 backdrop-blur-sm rounded-2xl border border-gray-700/50 p-6 shadow-xl">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <div className="w-2 h-2 rounded-full bg-violet-400" />
          <h3 className="text-lg font-semibold text-white">Trade Log</h3>
          <span className="text-xs px-2 py-0.5 rounded-full bg-gray-700/50 text-gray-400">
            {trades.length} trades
          </span>
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-700/50">
              <th className="text-left py-3 px-3 text-xs font-medium text-gray-400 uppercase tracking-wider">#</th>
              <th className="text-left py-3 px-3 text-xs font-medium text-gray-400 uppercase tracking-wider">Entry Date</th>
              <th className="text-left py-3 px-3 text-xs font-medium text-gray-400 uppercase tracking-wider">Exit Date</th>
              <th className="text-right py-3 px-3 text-xs font-medium text-gray-400 uppercase tracking-wider">Size</th>
              <th className="text-right py-3 px-3 text-xs font-medium text-gray-400 uppercase tracking-wider">Entry Price</th>
              <th className="text-right py-3 px-3 text-xs font-medium text-gray-400 uppercase tracking-wider">Exit Price</th>
              <th className="text-right py-3 px-3 text-xs font-medium text-gray-400 uppercase tracking-wider">PnL</th>
              <th className="text-right py-3 px-3 text-xs font-medium text-gray-400 uppercase tracking-wider">PnL %</th>
            </tr>
          </thead>
          <tbody>
            {paginated.map((trade, i) => (
              <tr
                key={`${trade.entry_date}-${i}`}
                className="border-b border-gray-800/50 hover:bg-gray-700/20 transition-colors"
              >
                <td className="py-2.5 px-3 text-gray-500">{page * PAGE_SIZE + i + 1}</td>
                <td className="py-2.5 px-3 text-gray-300 font-mono text-xs">{trade.entry_date}</td>
                <td className="py-2.5 px-3 text-gray-300 font-mono text-xs">{trade.exit_date}</td>
                <td className="py-2.5 px-3 text-right text-gray-300">{trade.size.toFixed(0)}</td>
                <td className="py-2.5 px-3 text-right text-gray-300 font-mono">${trade.entry_price.toFixed(2)}</td>
                <td className="py-2.5 px-3 text-right text-gray-300 font-mono">${trade.exit_price.toFixed(2)}</td>
                <td className={`py-2.5 px-3 text-right font-semibold font-mono ${trade.pnl >= 0 ? "text-emerald-400" : "text-red-400"}`}>
                  {trade.pnl >= 0 ? "+" : ""}${trade.pnl.toFixed(2)}
                </td>
                <td className={`py-2.5 px-3 text-right font-mono ${trade.pnl_pct >= 0 ? "text-emerald-400" : "text-red-400"}`}>
                  {trade.pnl_pct >= 0 ? "+" : ""}{trade.pnl_pct.toFixed(2)}%
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {totalPages > 1 && (
        <div className="flex items-center justify-between mt-4 pt-4 border-t border-gray-700/50">
          <p className="text-xs text-gray-500">
            Page {page + 1} of {totalPages}
          </p>
          <div className="flex gap-2">
            <button
              onClick={() => setPage((p) => Math.max(0, p - 1))}
              disabled={page === 0}
              className="px-3 py-1.5 text-xs rounded-lg bg-gray-700/50 text-gray-300 hover:bg-gray-600/50 disabled:opacity-40 disabled:cursor-not-allowed transition-all"
            >
              Previous
            </button>
            <button
              onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))}
              disabled={page >= totalPages - 1}
              className="px-3 py-1.5 text-xs rounded-lg bg-gray-700/50 text-gray-300 hover:bg-gray-600/50 disabled:opacity-40 disabled:cursor-not-allowed transition-all"
            >
              Next
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
