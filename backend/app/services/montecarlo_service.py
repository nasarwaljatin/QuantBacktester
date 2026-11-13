# backend/app/services/montecarlo_service.py
"""Monte Carlo simulation service for analyzing trade return distributions."""

import numpy as np
from typing import Any


def run_monte_carlo(
    trades: list[dict],
    n_simulations: int = 1000,
    initial_capital: float = 100000.0,
    seed: int = 42,
) -> dict[str, Any]:
    """Run a bootstrap Monte Carlo simulation over the strategy's trade P&L.

    Each path draws len(trades) trades *with replacement* from the observed P&L, so a
    path can contain more winners or more losers than the backtest did. Shuffling the
    same trades instead would keep their sum fixed, so every path would end at the
    same value and the probability of profit could only be 0% or 100%.

    Args:
        trades: List of trade records with 'pnl' field.
        n_simulations: Number of simulation paths to generate.
        initial_capital: Starting portfolio value.
        seed: Random seed, so the same trades always give the same result.

    Returns:
        Dict with paths, percentile curves, final_values, prob_profit, and the
        median / 95th-percentile maximum drawdown across paths (in percent).
    """
    if not trades:
        return {
            "paths": [],
            "percentile_5": [initial_capital],
            "percentile_50": [initial_capital],
            "percentile_95": [initial_capital],
            "final_values": [initial_capital],
            "prob_profit": 0.0,
            "max_drawdown_pct_p50": 0.0,
            "max_drawdown_pct_p95": 0.0,
            "method": "bootstrap",
        }

    pnl_values = np.array([t.get("pnl", 0.0) for t in trades], dtype=float)
    rng = np.random.default_rng(seed=seed)

    # One row per simulation: trades resampled with replacement, then accumulated.
    samples = rng.choice(pnl_values, size=(n_simulations, len(pnl_values)), replace=True)
    all_paths = np.empty((n_simulations, len(pnl_values) + 1))
    all_paths[:, 0] = initial_capital
    all_paths[:, 1:] = initial_capital + np.cumsum(samples, axis=1)

    final_values = all_paths[:, -1]

    # Percentile curves across simulations, step by step
    percentile_5 = np.percentile(all_paths, 5, axis=0).tolist()
    percentile_50 = np.percentile(all_paths, 50, axis=0).tolist()
    percentile_95 = np.percentile(all_paths, 95, axis=0).tolist()

    # Worst peak-to-trough fall of each path, as a positive percentage of the peak
    peaks = np.maximum.accumulate(all_paths, axis=1)
    max_drawdowns_pct = ((peaks - all_paths) / peaks).max(axis=1) * 100

    # Sample 50 paths for chart rendering
    sample_indices = rng.choice(n_simulations, size=min(50, n_simulations), replace=False)
    sampled_paths = all_paths[sample_indices].tolist()

    prob_profit = float(np.mean(final_values > initial_capital) * 100)

    return {
        "paths": sampled_paths,
        "percentile_5": percentile_5,
        "percentile_50": percentile_50,
        "percentile_95": percentile_95,
        "final_values": final_values.tolist(),
        "prob_profit": round(prob_profit, 2),
        "max_drawdown_pct_p50": round(float(np.percentile(max_drawdowns_pct, 50)), 2),
        "max_drawdown_pct_p95": round(float(np.percentile(max_drawdowns_pct, 95)), 2),
        "method": "bootstrap",
    }
