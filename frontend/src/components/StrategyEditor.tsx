// frontend/src/components/StrategyEditor.tsx
"use client";

import dynamic from "next/dynamic";
import { useBacktestStore } from "@/lib/store";
import StrategyTemplates from "./StrategyTemplates";

const MonacoEditor = dynamic(() => import("@monaco-editor/react"), {
  ssr: false,
  loading: () => (
    <div className="h-[320px] bg-gray-900/50 rounded-xl flex items-center justify-center border border-gray-700/50">
      <div className="flex items-center gap-3">
        <div className="w-5 h-5 border-2 border-cyan-400 border-t-transparent rounded-full animate-spin" />
        <span className="text-gray-400 text-sm">Loading editor...</span>
      </div>
    </div>
  ),
});

export default function StrategyEditor() {
  const strategyCode = useBacktestStore((s) => s.strategyCode);
  const setStrategyCode = useBacktestStore((s) => s.setStrategyCode);

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-2 h-2 rounded-full bg-cyan-400 animate-pulse" />
          <h2 className="text-lg font-semibold text-white">Strategy Editor</h2>
        </div>
        <StrategyTemplates />
      </div>
      <div className="rounded-xl overflow-hidden border border-gray-700/50 shadow-2xl shadow-cyan-500/5">
        <MonacoEditor
          height="320px"
          language="python"
          theme="vs-dark"
          value={strategyCode}
          onChange={(value) => setStrategyCode(value || "")}
          options={{
            fontSize: 14,
            minimap: { enabled: false },
            lineNumbers: "on",
            scrollBeyondLastLine: false,
            padding: { top: 16, bottom: 16 },
            roundedSelection: true,
            cursorBlinking: "smooth",
            cursorSmoothCaretAnimation: "on",
            smoothScrolling: true,
            fontFamily: "'JetBrains Mono', 'Fira Code', monospace",
            fontLigatures: true,
          }}
        />
      </div>
    </div>
  );
}
