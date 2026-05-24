# backend/app/services/montecarlo_service.py
"""Monte Carlo simulation service for analyzing trade return distributions."""

import numpy as np
from typing import Any


def run_monte_carlo(
    trades: list[dict],
    n_simulations: int = 1000,
    initial_capital: float = 100000.0,
) -> dict[str, Any]:
    """Run a Monte Carlo simulation by shuffling trade return sequences.

    Args:
        trades: List of trade records with 'pnl' field.
        n_simulations: Number of simulation paths to generate.
        initial_capital: Starting portfolio value.

    Returns:
        Dict with paths, percentile curves, final_values, and prob_profit.
    """
    if not trades:
        return {
            "paths": [],
            "percentile_5": [initial_capital],
            "percentile_50": [initial_capital],
            "percentile_95": [initial_capital],
            "final_values": [initial_capital],
            "prob_profit": 0.0,
        }

    # Extract PnL from each trade as return multiples
    pnl_values = np.array([t.get("pnl", 0.0) for t in trades], dtype=float)

    # Generate all simulation paths
    all_paths = np.zeros((n_simulations, len(pnl_values) + 1))
    all_paths[:, 0] = initial_capital

    rng = np.random.default_rng(seed=42)

    for i in range(n_simulations):
        shuffled_pnl = rng.permutation(pnl_values)
        cumulative = initial_capital + np.cumsum(shuffled_pnl)
        all_paths[i, 1:] = cumulative

    # Extract final values
    final_values = all_paths[:, -1].tolist()

    # Calculate percentile curves
    percentile_5 = np.percentile(all_paths, 5, axis=0).tolist()
    percentile_50 = np.percentile(all_paths, 50, axis=0).tolist()
    percentile_95 = np.percentile(all_paths, 95, axis=0).tolist()

    # Sample 50 paths for chart rendering
    sample_indices = rng.choice(n_simulations, size=min(50, n_simulations), replace=False)
    sampled_paths = all_paths[sample_indices].tolist()

    # Probability of profit
    prob_profit = float(np.sum(np.array(final_values) > initial_capital) / n_simulations * 100)

    return {
        "paths": sampled_paths,
        "percentile_5": percentile_5,
        "percentile_50": percentile_50,
        "percentile_95": percentile_95,
        "final_values": final_values,
        "prob_profit": round(prob_profit, 2),
    }
