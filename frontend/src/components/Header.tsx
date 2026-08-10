// frontend/src/components/Header.tsx
"use client";

import Link from "next/link";
import { useEffect } from "react";


export default function Header() {
  useEffect(() => {
    // Ensure dark mode is active on mount
    document.documentElement.classList.add("dark");
  }, []);

  return (
    <header className="sticky top-0 z-50 w-full glass-card border-b border-gray-200/50 dark:border-gray-800/50 backdrop-blur-md">
      <div className="max-w-6xl mx-auto px-4 h-16 flex items-center justify-between">
        <Link href="/" className="flex items-center gap-2 group">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-cyan-500 to-blue-600 flex items-center justify-center text-white font-bold text-lg shadow-md shadow-cyan-500/10 group-hover:scale-105 transition-all">
            Q
          </div>
          <span className="text-xl font-bold bg-gradient-to-r from-gray-900 via-gray-700 to-gray-900 dark:from-white dark:via-cyan-100 dark:to-white bg-clip-text text-transparent group-hover:opacity-90 transition-opacity">
            QuantBacktester
          </span>
        </Link>
      </div>
    </header>
  );
}
