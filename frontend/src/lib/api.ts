// frontend/src/lib/api.ts
// API client functions for communicating with the FastAPI backend

import type {
  BacktestRequest,
  BacktestResponse,
  TickerResult,
  StrategyTemplate,
  SweepRequest,
  SweepResponse,
  WFARequest,
  WFAResponse,
  WFAEstimateRequest,
  WFAEstimateResponse,
} from "@/types/backtest";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

/**
 * Submit a new backtest for execution.
 * Returns the task_id for polling.
 */
export async function submitBacktest(
  request: BacktestRequest
): Promise<{ task_id: string }> {
  const res = await fetch(`${API_BASE}/api/backtest`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: "Unknown error" }));
    throw new Error(err.detail?.error || err.error || `HTTP ${res.status}`);
  }

  return res.json();
}

/**
 * Poll for backtest result status and data.
 */
export async function getBacktestResult(
  taskId: string
): Promise<BacktestResponse> {
  const res = await fetch(`${API_BASE}/api/backtest/${taskId}`);

  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: "Unknown error" }));
    throw new Error(err.detail?.error || err.error || `HTTP ${res.status}`);
  }

  return res.json();
}

/**
 * Get Monte Carlo results (lazy loading).
 */
export async function getMonteCarloResult(
  taskId: string
): Promise<BacktestResponse> {
  const res = await fetch(`${API_BASE}/api/backtest/${taskId}/montecarlo`);

  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: "Unknown error" }));
    throw new Error(err.detail?.error || err.error || `HTTP ${res.status}`);
  }

  return res.json();
}

/**
 * Search for tickers matching a query string.
 */
export async function searchTickers(
  query: string
): Promise<{ results: TickerResult[] }> {
  const res = await fetch(
    `${API_BASE}/api/tickers/search?q=${encodeURIComponent(query)}`
  );

  if (!res.ok) {
    return { results: [] };
  }

  return res.json();
}

/**
 * Get all available strategy templates.
 */
export async function getStrategyTemplates(): Promise<{
  templates: Record<string, StrategyTemplate>;
}> {
  const res = await fetch(`${API_BASE}/api/strategies/templates`);

  if (!res.ok) {
    return { templates: {} };
  }

  return res.json();
}

/**
 * Health check.
 */
export async function healthCheck(): Promise<{ status: string }> {
  const res = await fetch(`${API_BASE}/api/health`);
  return res.json();
}

/**
 * Submit a parameter sweep for execution.
 */
export async function submitSweep(
  request: SweepRequest
): Promise<{ task_id: string }> {
  const res = await fetch(`${API_BASE}/api/backtest/sweep`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: "Unknown error" }));
    throw new Error(err.detail?.error || err.error || `HTTP ${res.status}`);
  }
  return res.json();
}

/**
 * Poll for parameter sweep results.
 */
export async function getSweepResult(taskId: string): Promise<SweepResponse> {
  const res = await fetch(`${API_BASE}/api/backtest/${taskId}/sweep`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: "Unknown error" }));
    throw new Error(err.detail?.error || err.error || `HTTP ${res.status}`);
  }
  return res.json();
}

/**
 * Submit a walk-forward analysis for execution.
 */
export async function submitWalkForward(
  request: WFARequest
): Promise<{ task_id: string }> {
  const res = await fetch(`${API_BASE}/api/backtest/walkforward`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: "Unknown error" }));
    throw new Error(err.detail?.error || err.error || `HTTP ${res.status}`);
  }
  return res.json();
}

/**
 * Poll for walk-forward analysis results.
 */
export async function getWalkForwardResult(taskId: string): Promise<WFAResponse> {
  const res = await fetch(`${API_BASE}/api/backtest/${taskId}/walkforward`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: "Unknown error" }));
    throw new Error(err.detail?.error || err.error || `HTTP ${res.status}`);
  }
  return res.json();
}

/**
 * Pre-flight estimate: how many backtests will this WFA config produce?
 * Does not launch any tasks or write to the DB.
 */
export async function estimateWFA(
  request: WFAEstimateRequest
): Promise<WFAEstimateResponse> {
  const res = await fetch(`${API_BASE}/api/backtest/walkforward/estimate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: "Unknown error" }));
    throw new Error(err.detail?.error || err.error || `HTTP ${res.status}`);
  }
  return res.json();
}

/**
 * Retrieve OHLCV price history for a ticker and date range.
 */
export async function getOhlcvData(
  ticker: string,
  start: string,
  end: string
): Promise<{ data: any[]; count: number }> {
  const res = await fetch(
    `${API_BASE}/api/ohlcv?ticker=${encodeURIComponent(ticker)}&start=${encodeURIComponent(start.slice(0, 10))}&end=${encodeURIComponent(end.slice(0, 10))}`
  );
  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: "Failed to fetch price data" }));
    throw new Error(err.detail?.error || err.error || `HTTP ${res.status}`);
  }
  return res.json();
}

