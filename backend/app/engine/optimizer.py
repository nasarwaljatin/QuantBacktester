# backend/app/engine/optimizer.py
"""Parameter grid generation, walk-forward window splitting, and diagnostic utilities.

Walk-forward validation checks for *parameter overfitting* — whether parameters
selected during in-sample optimization generalize to unseen out-of-sample data.
An efficiency ratio (OOS metric / IS metric) consistently below 0.5 is a strong
signal that the strategy's edge is curve-fitted rather than structural.

NOTE: Walk-forward validation does NOT detect look-ahead bias inside the strategy's
next() method. If future data is accessed there, that bias will appear in both IS
and OOS results and will not be surfaced here. Eliminating look-ahead bias is the
user's responsibility.
"""

import itertools
import statistics
from datetime import date, timedelta
from typing import Any, Literal, Optional


# ---------------------------------------------------------------------------
# Parameter grid
# ---------------------------------------------------------------------------

def generate_param_combinations(grid: dict[str, list[Any]]) -> list[dict[str, Any]]:
    """Generate all combinations of parameters from a grid dict.

    Args:
        grid: Dict mapping parameter names to lists of candidate values.
              Example: {"fast": [3, 5, 10], "slow": [20, 30, 50]}

    Returns:
        List of dicts, each representing one parameter combination.
        Example: [{"fast": 3, "slow": 20}, {"fast": 3, "slow": 30}, ...]

    Raises:
        ValueError: If grid is empty or any value list is empty.
    """
    if not grid:
        raise ValueError("Parameter grid must not be empty.")
    for key, values in grid.items():
        if not values:
            raise ValueError(f"Parameter '{key}' has no candidate values.")

    keys = list(grid.keys())
    value_lists = [grid[k] for k in keys]
    combinations = []
    for combo in itertools.product(*value_lists):
        combinations.append(dict(zip(keys, combo)))
    return combinations


# ---------------------------------------------------------------------------
# Window splitting
# ---------------------------------------------------------------------------

def split_walk_forward_windows(
    start_date: date,
    end_date: date,
    in_sample_days: int = 365,
    out_of_sample_days: int = 90,
    window_type: str = "rolling",
    anchored: bool = False,
) -> list[dict[str, date]]:
    """Split a date range into walk-forward IS/OOS windows.

    Supports three modes:

    **Rolling (non-anchored, default)**
        Both IS and OOS periods slide forward by out_of_sample_days each fold.
        IS length stays constant. No overlap between consecutive OOS periods.

    **Rolling (anchored)**
        The OOS window slides forward as normal, but the IS window always starts
        from the same first fold's IS start date — i.e. the IS period *grows*
        with each fold. Equivalent to anchored walk-forward. anchored=True is
        only meaningful for window_type="rolling".

    **Expanding**
        The IS period always starts at start_date and grows with each fold.
        The OOS period has a fixed length of out_of_sample_days. Functionally
        equivalent to rolling-anchored when the first IS start equals start_date.

    Args:
        start_date: Overall start date of the full date range.
        end_date: Overall end date of the full date range.
        in_sample_days: Length of the IS period in calendar days (rolling only;
            for expanding, IS always grows from start_date).
        out_of_sample_days: Length of the OOS period in calendar days.
        window_type: "rolling" or "expanding".
        anchored: If True (rolling only), pin the IS start to the first fold's
            IS start date so the IS window grows rather than slides.

    Returns:
        List of dicts with keys:
            - in_sample_start: date
            - in_sample_end: date
            - out_of_sample_start: date
            - out_of_sample_end: date

    Raises:
        ValueError: If parameters are invalid or date range is too short for
            at least 2 complete windows.
    """
    if in_sample_days <= 0:
        raise ValueError("in_sample_days must be positive.")
    if out_of_sample_days <= 0:
        raise ValueError("out_of_sample_days must be positive.")

    total_days = (end_date - start_date).days
    # Need at least IS + 2*OOS for 2 folds (both rolling and expanding)
    min_required = in_sample_days + 2 * out_of_sample_days
    if total_days < min_required:
        raise ValueError(
            f"Date range ({total_days} days) is too short for 2 windows "
            f"(requires at least {min_required} days = {in_sample_days} IS + "
            f"2×{out_of_sample_days} OOS)."
        )

    windows: list[dict[str, date]] = []

    if window_type == "expanding":
        # IS always starts at start_date; grows each fold
        oos_start = start_date + timedelta(days=in_sample_days)
        while True:
            oos_end = oos_start + timedelta(days=out_of_sample_days - 1)
            if oos_end > end_date:
                break
            windows.append({
                "in_sample_start": start_date,
                "in_sample_end": oos_start - timedelta(days=1),
                "out_of_sample_start": oos_start,
                "out_of_sample_end": oos_end,
            })
            oos_start += timedelta(days=out_of_sample_days)

    else:
        # Rolling (anchored or non-anchored)
        first_oos_start = start_date + timedelta(days=in_sample_days)
        anchored_is_start = start_date  # pinned start for anchored mode

        oos_start = first_oos_start
        while True:
            oos_end = oos_start + timedelta(days=out_of_sample_days - 1)
            if oos_end > end_date:
                break

            if anchored:
                is_start = anchored_is_start
            else:
                is_start = oos_start - timedelta(days=in_sample_days)

            windows.append({
                "in_sample_start": is_start,
                "in_sample_end": oos_start - timedelta(days=1),
                "out_of_sample_start": oos_start,
                "out_of_sample_end": oos_end,
            })
            oos_start += timedelta(days=out_of_sample_days)

    if len(windows) < 2:
        raise ValueError(
            f"Configuration produces only {len(windows)} fold(s); at least 2 are required "
            f"for a meaningful walk-forward analysis. Extend the date range or reduce the "
            f"IS/OOS period lengths."
        )

    return windows


# ---------------------------------------------------------------------------
# Best-params selection
# ---------------------------------------------------------------------------

def select_best_params(
    sweep_results: list[dict[str, Any]],
    objective: str = "sharpe_ratio",
) -> dict[str, Any]:
    """Select the parameter combination with the highest objective metric.

    Args:
        sweep_results: List of dicts with 'parameters' and 'metrics' keys.
        objective: The metric key to maximize (default: 'sharpe_ratio').

    Returns:
        The parameter dict from the best-performing combination.

    Raises:
        ValueError: If sweep_results is empty or no successful results exist.
    """
    if not sweep_results:
        raise ValueError("sweep_results must not be empty.")

    successful = [r for r in sweep_results if r.get("status") == "SUCCESS" and r.get("metrics")]
    if not successful:
        raise ValueError("No successful sweep results to select from.")

    best = max(
        successful,
        key=lambda r: (r["metrics"].get(objective) or float("-inf")),
    )
    return best["parameters"]


# ---------------------------------------------------------------------------
# Efficiency ratio
# ---------------------------------------------------------------------------

def compute_efficiency_ratio(
    is_metric: Optional[float],
    oos_metric: Optional[float],
) -> Optional[float]:
    """Compute the walk-forward efficiency ratio: OOS metric / IS metric.

    An efficiency ratio >= 0.7 suggests good generalisation.
    A ratio < 0.5 is a strong overfitting signal.

    Args:
        is_metric: In-sample (training) objective metric value.
        oos_metric: Out-of-sample (testing) objective metric value.

    Returns:
        The ratio OOS/IS, or None if IS metric is zero, None, or non-positive
        (ratio would be undefined or misleading).
    """
    if is_metric is None or oos_metric is None:
        return None
    if is_metric <= 0:
        return None
    return round(oos_metric / is_metric, 4)


# ---------------------------------------------------------------------------
# Parameter stability
# ---------------------------------------------------------------------------

def compute_param_stability(
    param_values_per_fold: list[dict[str, Any]],
) -> dict[str, Optional[float]]:
    """Compute the Coefficient of Variation (CV = std/mean) for each parameter.

    A high CV indicates the optimizer chose very different parameter values
    across folds, suggesting unstable parameter sensitivity — a red flag even
    if OOS metrics look acceptable.

    Interpretation guide:
        CV < 0.2  -> stable (green)
        0.2-0.5   -> moderate instability (amber)
        > 0.5     -> highly unstable (red)

    Args:
        param_values_per_fold: List of parameter dicts, one per fold.
            Example: [{"fast": 3, "slow": 20}, {"fast": 10, "slow": 50}]

    Returns:
        Dict mapping parameter name to CV (or None if CV is undefined,
        e.g. only one fold or mean is zero).
    """
    if not param_values_per_fold:
        return {}

    all_params: set[str] = set()
    for d in param_values_per_fold:
        all_params.update(d.keys())

    result: dict[str, Optional[float]] = {}
    for param in sorted(all_params):
        values: list[float] = []
        for fold_params in param_values_per_fold:
            v = fold_params.get(param)
            if v is not None:
                try:
                    values.append(float(v))
                except (TypeError, ValueError):
                    pass  # non-numeric params skipped

        if len(values) < 2:
            result[param] = None
            continue

        mean = statistics.mean(values)
        if abs(mean) < 1e-9:
            result[param] = None
            continue

        stdev = statistics.stdev(values)
        result[param] = round(abs(stdev / mean), 4)

    return result


# ---------------------------------------------------------------------------
# Guardrails
# ---------------------------------------------------------------------------

def validate_wfa_config(
    n_folds: int,
    n_combinations: int,
    max_combinations: int = 200,
) -> None:
    """Validate walk-forward configuration before launching any backtests.

    Args:
        n_folds: Number of walk-forward folds.
        n_combinations: Number of parameter combinations per fold.
        max_combinations: Hard cap on total backtest runs (n_folds x n_combinations).

    Raises:
        ValueError: If fewer than 2 folds, or total runs exceed the cap.
    """
    if n_folds < 2:
        raise ValueError(
            f"Walk-forward analysis requires at least 2 folds; got {n_folds}. "
            "Extend the date range or reduce the IS/OOS period lengths."
        )
    if n_combinations < 1:
        raise ValueError(
            "Walk-forward analysis requires at least 1 parameter combination; "
            "the parameter grid appears to be empty."
        )
    total_runs = n_folds * n_combinations
    if total_runs > max_combinations:
        raise ValueError(
            f"This configuration would run {total_runs:,} backtests "
            f"({n_folds} folds x {n_combinations} combinations), which exceeds the "
            f"cap of {max_combinations:,}. Reduce the parameter grid size, the number "
            f"of folds, or increase the max_combinations limit."
        )
