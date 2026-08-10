# backend/app/services/optimization_service.py
"""High-level orchestration for parameter sweeps and walk-forward analysis."""

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date
from typing import Any, Optional
from sqlalchemy.orm import Session

from app.engine.optimizer import (
    generate_param_combinations,
    split_walk_forward_windows,
    select_best_params,
    compute_efficiency_ratio,
    compute_param_stability,
    validate_wfa_config,
)
from app.engine.strategy_sandbox import compile_user_strategy
from app.engine.runner import run_backtest
from app.services.data_service import get_ohlcv
from app.services.metrics_service import compute_all_metrics
from app.models.optimization import SweepResult, WFAWindow
from app.models.backtest import BacktestResult


def _run_single_combination(
    combo_index: int,
    parameters: dict[str, Any],
    strategy_code: str,
    ohlcv_dfs: dict,
    base_config: dict,
    ticker_weights: Optional[dict],
) -> dict[str, Any]:
    """Run one backtest with a specific parameter combination.

    Args:
        combo_index: Index of the combination in the sweep.
        parameters: Strategy parameter values to inject.
        strategy_code: User strategy source code.
        ohlcv_dfs: Pre-fetched OHLCV data for all tickers.
        base_config: Base config dict (capital, commission, slippage, etc.).
        ticker_weights: Optional per-ticker weight allocations.

    Returns:
        Dict with combo_index, parameters, metrics, equity_curve, status.
    """
    try:
        strategy_class = compile_user_strategy(strategy_code)

        # Inject sweep params into strategy class
        for key, value in parameters.items():
            if hasattr(strategy_class, "params"):
                # Backtrader uses a params tuple — we patch via class attribute
                strategy_class.params = tuple(
                    (k, value if k == key else v)
                    for k, v in dict(strategy_class.params._getitems()).items()
                )

        result = run_backtest(strategy_class, ohlcv_dfs, base_config, ticker_weights)
        equity_values = [p["value"] for p in result["equity_curve"]]
        metrics = compute_all_metrics(equity_values, result["trades"])

        return {
            "combo_index": combo_index,
            "parameters": parameters,
            "metrics": metrics.model_dump(),
            "equity_curve": result["equity_curve"],
            "status": "SUCCESS",
            "error_message": None,
        }
    except Exception as e:
        return {
            "combo_index": combo_index,
            "parameters": parameters,
            "metrics": None,
            "equity_curve": None,
            "status": "FAILURE",
            "error_message": str(e),
        }


def run_parameter_sweep(
    task_id: str,
    strategy_code: str,
    tickers: list[str],
    start_date: date,
    end_date: date,
    param_grid: dict[str, list[Any]],
    base_config: dict[str, Any],
    db: Session,
    ticker_weights: Optional[dict[str, float]] = None,
    max_workers: int = 4,
    objective: str = "sharpe_ratio",
) -> dict[str, Any]:
    """Run a full parameter sweep, persisting each combination result to the DB.

    Args:
        task_id: The parent backtest task ID.
        strategy_code: User strategy source code.
        tickers: List of tickers.
        start_date: Backtest start date.
        end_date: Backtest end date.
        param_grid: Dict of {param_name: [candidate_values]}.
        base_config: Base configuration dict.
        db: SQLAlchemy session.
        ticker_weights: Optional per-ticker weights.
        max_workers: Max parallel threads.
        objective: Metric to identify the best combination.

    Returns:
        Dict with all sweep results and best parameter combination.
    """
    # Fetch data once for all tickers
    ohlcv_dfs = {t: get_ohlcv(t, start_date, end_date, db) for t in tickers}

    # Generate all parameter combinations
    combinations = generate_param_combinations(param_grid)
    total = len(combinations)

    # Update progress in DB record
    record = db.query(BacktestResult).filter(BacktestResult.task_id == task_id).first()
    if record:
        record.progress = f"0 / {total} combinations"
        db.commit()

    all_results = []
    completed = 0

    # Run combinations in parallel
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(
                _run_single_combination,
                idx,
                combo,
                strategy_code,
                ohlcv_dfs,
                base_config,
                ticker_weights,
            ): idx
            for idx, combo in enumerate(combinations)
        }

        for future in as_completed(futures):
            combo_result = future.result()
            all_results.append(combo_result)
            completed += 1

            # Persist sweep result to DB
            sweep_row = SweepResult(
                task_id=task_id,
                combo_index=combo_result["combo_index"],
                parameters=combo_result["parameters"],
                metrics=combo_result["metrics"],
                equity_curve=combo_result["equity_curve"],
                status=combo_result["status"],
                error_message=combo_result.get("error_message"),
            )
            db.add(sweep_row)

            # Update progress
            if record:
                record.progress = f"{completed} / {total} combinations"
            db.commit()

    # Sort by combo_index for stable ordering
    all_results.sort(key=lambda r: r["combo_index"])

    # Find best parameters
    try:
        best_params = select_best_params(all_results, objective=objective)
    except ValueError:
        best_params = combinations[0] if combinations else {}

    return {
        "sweep_results": all_results,
        "best_params": best_params,
        "total_combinations": total,
        "objective": objective,
        "param_grid": param_grid,
    }


def run_walk_forward_analysis(
    task_id: str,
    strategy_code: str,
    tickers: list[str],
    start_date: date,
    end_date: date,
    param_grid: dict[str, list[Any]],
    base_config: dict[str, Any],
    db: Session,
    ticker_weights: Optional[dict[str, float]] = None,
    in_sample_days: int = 365,
    out_of_sample_days: int = 90,
    max_workers: int = 4,
    objective: str = "sharpe_ratio",
    window_type: str = "rolling",
    anchored: bool = False,
    max_combinations: int = 200,
) -> dict[str, Any]:
    """Run a full walk-forward analysis.

    For each rolling/expanding window:
        1. Run in-sample parameter sweep to find the best parameters.
        2. Evaluate those parameters on the out-of-sample period (no re-fitting).
        3. Persist window results to the DB.

    After all windows:
        - Compute per-fold efficiency ratios (OOS metric / IS metric).
        - Compute aggregate efficiency ratio (mean across folds).
        - Compute parameter stability (CV per parameter across folds).
        - Stitch OOS equity curves into one continuous series.

    Args:
        task_id: The parent backtest task ID.
        strategy_code: User strategy source code.
        tickers: List of tickers.
        start_date: Overall start date.
        end_date: Overall end date.
        param_grid: Dict of {param_name: [candidate_values]}.
        base_config: Base configuration dict.
        db: SQLAlchemy session.
        ticker_weights: Optional per-ticker weights.
        in_sample_days: Length of in-sample period in calendar days.
        out_of_sample_days: Length of out-of-sample period in calendar days.
        max_workers: Max threads per window's in-sample sweep.
        objective: Metric to maximize during in-sample optimization.
        window_type: "rolling" or "expanding".
        anchored: If True (rolling only), pin IS start to first fold's IS start.
        max_combinations: Hard cap on total backtest runs (n_folds x n_combos).

    Returns:
        Dict with window results, efficiency ratios, param stability,
        combined out-of-sample equity curve, and aggregate OOS metrics.
    """
    # Pre-flight validation: ensure the config is feasible before any data fetch
    combinations = generate_param_combinations(param_grid)
    windows_preview = split_walk_forward_windows(
        start_date, end_date, in_sample_days, out_of_sample_days,
        window_type=window_type, anchored=anchored,
    )
    validate_wfa_config(
        n_folds=len(windows_preview),
        n_combinations=len(combinations),
        max_combinations=max_combinations,
    )

    windows = windows_preview
    total_windows = len(windows)

    record = db.query(BacktestResult).filter(BacktestResult.task_id == task_id).first()
    if record:
        record.progress = f"0 / {total_windows} windows"
        db.commit()

    window_results = []
    combined_oos_equity: list[dict[str, Any]] = []
    all_optimized_params: list[dict[str, Any]] = []

    for idx, window in enumerate(windows):
        is_start = window["in_sample_start"]
        is_end = window["in_sample_end"]
        oos_start = window["out_of_sample_start"]
        oos_end = window["out_of_sample_end"]

        # --- In-sample sweep ---
        is_ohlcv = {t: get_ohlcv(t, is_start, is_end, db) for t in tickers}
        is_sweep_results = []

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(
                    _run_single_combination,
                    combo_idx,
                    combo,
                    strategy_code,
                    is_ohlcv,
                    base_config,
                    ticker_weights,
                ): combo_idx
                for combo_idx, combo in enumerate(combinations)
            }
            for future in as_completed(futures):
                is_sweep_results.append(future.result())

        # Select best params from in-sample sweep
        try:
            best_params = select_best_params(is_sweep_results, objective=objective)
            best_is_result = next(
                (r for r in is_sweep_results if r["parameters"] == best_params and r["status"] == "SUCCESS"),
                None,
            )
            is_metrics = best_is_result["metrics"] if best_is_result else None
        except ValueError:
            best_params = combinations[0] if combinations else {}
            is_metrics = None

        all_optimized_params.append(best_params)

        # --- Out-of-sample evaluation ---
        oos_result = _run_single_combination(
            combo_index=idx,
            parameters=best_params,
            strategy_code=strategy_code,
            ohlcv_dfs={t: get_ohlcv(t, oos_start, oos_end, db) for t in tickers},
            base_config=base_config,
            ticker_weights=ticker_weights,
        )

        oos_equity = oos_result.get("equity_curve") or []
        oos_metrics = oos_result.get("metrics") or {}

        # Compute per-window efficiency ratio
        is_obj_value = is_metrics.get(objective) if is_metrics else None
        oos_obj_value = oos_metrics.get(objective) if oos_metrics else None
        efficiency_ratio = compute_efficiency_ratio(is_obj_value, oos_obj_value)

        # Accumulate OOS equity curve (normalised continuation)
        if oos_equity:
            if combined_oos_equity:
                last_combined_val = combined_oos_equity[-1]["value"]
                first_oos_val = oos_equity[0]["value"]
                if first_oos_val and first_oos_val > 0:
                    scale = last_combined_val / first_oos_val
                    scaled = [{"date": p["date"], "value": round(p["value"] * scale, 2)} for p in oos_equity]
                    combined_oos_equity.extend(scaled)
                else:
                    combined_oos_equity.extend(oos_equity)
            else:
                combined_oos_equity.extend(oos_equity)

        # Persist WFA window to DB
        wfa_row = WFAWindow(
            task_id=task_id,
            window_index=idx,
            in_sample_start=is_start.isoformat(),
            in_sample_end=is_end.isoformat(),
            out_of_sample_start=oos_start.isoformat(),
            out_of_sample_end=oos_end.isoformat(),
            optimized_params=best_params,
            in_sample_metrics=is_metrics,
            out_of_sample_metrics=oos_metrics,
            out_of_sample_equity=oos_equity,
            status=oos_result["status"],
            error_message=oos_result.get("error_message"),
        )
        db.add(wfa_row)

        window_results.append({
            "window_index": idx,
            "in_sample_start": is_start.isoformat(),
            "in_sample_end": is_end.isoformat(),
            "out_of_sample_start": oos_start.isoformat(),
            "out_of_sample_end": oos_end.isoformat(),
            "optimized_params": best_params,
            "in_sample_metrics": is_metrics,
            "out_of_sample_metrics": oos_metrics,
            "efficiency_ratio": efficiency_ratio,
            "status": oos_result["status"],
        })

        # Update progress
        if record:
            record.progress = f"{idx + 1} / {total_windows} windows"
        db.commit()

    # --- Aggregate OOS metrics ---
    oos_equity_values = [p["value"] for p in combined_oos_equity]
    try:
        agg_metrics = compute_all_metrics(oos_equity_values, [])
        agg_metrics_dict = agg_metrics.model_dump()
    except Exception:
        agg_metrics_dict = {}

    # --- Efficiency ratios summary ---
    efficiency_ratios = [
        {
            "window_index": w["window_index"],
            "is_value": (w["in_sample_metrics"] or {}).get(objective),
            "oos_value": (w["out_of_sample_metrics"] or {}).get(objective),
            "ratio": w["efficiency_ratio"],
        }
        for w in window_results
    ]

    valid_ratios = [r["ratio"] for r in efficiency_ratios if r["ratio"] is not None]
    aggregate_efficiency_ratio = round(sum(valid_ratios) / len(valid_ratios), 4) if valid_ratios else None

    # --- Parameter stability ---
    param_stability = compute_param_stability(all_optimized_params)

    return {
        "wfa_windows": window_results,
        "combined_oos_equity": combined_oos_equity,
        "aggregate_oos_metrics": agg_metrics_dict,
        "total_windows": total_windows,
        "param_grid": param_grid,
        "in_sample_days": in_sample_days,
        "out_of_sample_days": out_of_sample_days,
        "objective": objective,
        "window_type": window_type,
        "anchored": anchored,
        "efficiency_ratios": efficiency_ratios,
        "aggregate_efficiency_ratio": aggregate_efficiency_ratio,
        "param_stability": param_stability,
    }
