# backend/app/services/walk_forward_service.py
"""Pre-flight estimation service for walk-forward analysis.

Provides lightweight computation of the number of backtests a given WFA
configuration will produce — without fetching data or running any backtests.
Used by the /walkforward/estimate endpoint so the frontend can surface a
run-count badge before the user submits.
"""

from datetime import date
from typing import Any

from app.engine.optimizer import (
    generate_param_combinations,
    split_walk_forward_windows,
)


def estimate_wfa_runs(
    start_date: date,
    end_date: date,
    in_sample_days: int,
    out_of_sample_days: int,
    window_type: str,
    anchored: bool,
    param_grid: dict[str, list[Any]],
    max_combinations: int = 200,
) -> dict[str, Any]:
    """Estimate the total number of backtest runs for a WFA configuration.

    Performs no data fetching and launches no tasks. Pure arithmetic used
    exclusively for the pre-flight UI badge.

    Args:
        start_date: Overall backtest start date.
        end_date: Overall backtest end date.
        in_sample_days: IS period length in calendar days.
        out_of_sample_days: OOS period length in calendar days.
        window_type: "rolling" or "expanding".
        anchored: Whether to use anchored rolling windows.
        param_grid: Parameter grid dict {param: [values]}.
        max_combinations: Cap on total runs (n_folds x n_combos).

    Returns:
        Dict with keys:
            n_folds: int — number of walk-forward folds
            n_combinations: int — number of param combos per fold
            total_runs: int — n_folds * n_combinations
            feasible: bool — True if total_runs <= max_combinations
            error: str | None — human-readable error if config is invalid
    """
    try:
        windows = split_walk_forward_windows(
            start_date=start_date,
            end_date=end_date,
            in_sample_days=in_sample_days,
            out_of_sample_days=out_of_sample_days,
            window_type=window_type,
            anchored=anchored,
        )
        n_folds = len(windows)
    except ValueError as e:
        return {
            "n_folds": 0,
            "n_combinations": 0,
            "total_runs": 0,
            "feasible": False,
            "error": str(e),
        }

    try:
        combos = generate_param_combinations(param_grid)
        n_combinations = len(combos)
    except ValueError as e:
        return {
            "n_folds": n_folds,
            "n_combinations": 0,
            "total_runs": 0,
            "feasible": False,
            "error": str(e),
        }

    total_runs = n_folds * n_combinations
    feasible = total_runs <= max_combinations

    return {
        "n_folds": n_folds,
        "n_combinations": n_combinations,
        "total_runs": total_runs,
        "feasible": feasible,
        "error": None,
    }
