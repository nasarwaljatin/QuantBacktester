# backend/app/routers/backtest.py
"""Backtest API endpoints — submit, poll, and retrieve results."""

import uuid
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.schemas.backtest import (
    BacktestRequest,
    BacktestResponse,
    SweepRequest,
    SweepResponse,
    WFARequest,
    WFAResponse,
    WFAEstimateRequest,
    WFAEstimateResponse,
)
from app.models.backtest import BacktestResult
from app.models.optimization import SweepResult, WFAWindow
from app.tasks.backtest_task import run_backtest_task, run_backtest_local
from app.tasks.optimization_task import (
    run_sweep_task,
    run_sweep_local,
    run_walkforward_task,
    run_walkforward_local,
)
from app.engine.strategies import STRATEGY_TEMPLATES
from app.services.walk_forward_service import estimate_wfa_runs

router = APIRouter(prefix="/api", tags=["backtest"])


# ---------------------------------------------------------------------------
# Helper: build success payload from a BacktestResult DB record
# ---------------------------------------------------------------------------

def _build_success_payload(task_id: str, db_record: BacktestResult, result: dict) -> dict:
    """Build the standard success response payload."""
    return {
        "task_id": task_id,
        "status": "success",
        "ticker": db_record.ticker,
        "tickers": db_record.tickers,
        "ticker_weights": result.get("ticker_weights", {}),
        "start_date": db_record.start_date,
        "end_date": db_record.end_date,
        "equity_curve": result.get("equity_curve", []),
        "benchmark_curve": result.get("benchmark_curve", []),
        "trades": result.get("trades", []),
        "metrics": result.get("metrics", {}),
        "monte_carlo": result.get("monte_carlo", {}),
        "allocation_pct": result.get("allocation_pct", 100.0),
        "position_sizing": result.get("position_sizing", "cash_percentage"),
        "sizing_model": result.get("sizing_model", "all_in"),
        "sizing_params": result.get("sizing_params", {}),
        "commission_type": result.get("commission_type", "percent"),
        "commission_value": result.get("commission_value", 0.001),
        "commission_tier_limit": result.get("commission_tier_limit", 1000),
        "commission_tier_value": result.get("commission_tier_value", 0.003),
        "slippage_type": result.get("slippage_type", "percent"),
        "slippage_value": result.get("slippage_value", 0.0005),
        "spread": result.get("spread", 0.0),
        "volume_limit_pct": result.get("volume_limit_pct", None),
    }


# ---------------------------------------------------------------------------
# Single Backtest
# ---------------------------------------------------------------------------

@router.post("/backtest")
async def submit_backtest(
    request: BacktestRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> dict:
    """Submit a new backtest for asynchronous execution.

    Validates inputs, dispatches a Celery task or FastAPI BackgroundTask,
    and returns a task_id that can be used to poll for results.
    """
    # Validate date range
    if request.start_date >= request.end_date:
        raise HTTPException(
            status_code=400,
            detail={"error": "start_date must be before end_date"},
        )

    try:
        config_dict = request.config.model_dump()

        if settings.USE_CELERY:
            # Dispatch Celery task
            task = run_backtest_task.delay(
                strategy_code=request.strategy_code,
                ticker=request.ticker,
                start_date=request.start_date.isoformat(),
                end_date=request.end_date.isoformat(),
                config_dict=config_dict,
                tickers=request.tickers,
                ticker_weights=request.ticker_weights,
            )
            task_id = task.id
            status = "PENDING"
        else:
            # Dispatch FastAPI background task
            task_id = uuid.uuid4().hex
            status = "PENDING"
            background_tasks.add_task(
                run_backtest_local,
                task_id=task_id,
                strategy_code=request.strategy_code,
                ticker=request.ticker,
                start_date=request.start_date.isoformat(),
                end_date=request.end_date.isoformat(),
                config_dict=config_dict,
                tickers=request.tickers,
                ticker_weights=request.ticker_weights,
            )

        # Create DB record
        db_record = BacktestResult(
            task_id=task_id,
            status=status,
            ticker=request.ticker,
            tickers=request.tickers,
            strategy_code=request.strategy_code,
            start_date=request.start_date.isoformat(),
            end_date=request.end_date.isoformat(),
            config_json=config_dict,
            run_type="single",
        )
        db.add(db_record)
        db.commit()

        return {"task_id": task_id}

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={"error": f"Failed to submit backtest: {str(e)}"},
        )


@router.get("/backtest/{task_id}")
async def get_backtest_result(
    task_id: str,
    db: Session = Depends(get_db),
) -> dict:
    """Get the status and results of a backtest task.

    Returns:
        - If PENDING: {status: "pending"}
        - If RUNNING: {status: "running", step, progress}
        - If SUCCESS (single): Full BacktestResponse
        - If SUCCESS (sweep): SweepResponse with sweep_results and best_params
        - If SUCCESS (walk_forward): WFAResponse with wfa_windows and combined OOS equity
        - If FAILURE: {status: "failed", error: str}
    """
    if not settings.USE_CELERY:
        db_record = db.query(BacktestResult).filter(
            BacktestResult.task_id == task_id
        ).first()

        if not db_record:
            raise HTTPException(
                status_code=404,
                detail={"error": "Backtest result not found"},
            )

        if db_record.status == "PENDING":
            return {"task_id": task_id, "status": "pending"}

        if db_record.status == "RUNNING":
            return {
                "task_id": task_id,
                "status": "running",
                "step": "Running...",
                "progress": db_record.progress,
                "run_type": db_record.run_type or "single",
            }

        if db_record.status == "FAILURE":
            return {
                "task_id": task_id,
                "status": "failed",
                "error": db_record.error_message or "Unknown error",
            }

        if db_record.status == "SUCCESS":
            result = db_record.result_json or {}
            run_type = db_record.run_type or "single"

            if run_type == "sweep":
                return _build_sweep_payload(task_id, db_record, result)
            elif run_type == "walk_forward":
                return _build_wfa_payload(task_id, db_record, result)
            else:
                return _build_success_payload(task_id, db_record, result)

        return {"task_id": task_id, "status": db_record.status.lower()}

    # Check Celery task state first
    task = run_backtest_task.AsyncResult(task_id)

    if task.state == "PENDING":
        return {"task_id": task_id, "status": "pending"}

    if task.state == "STARTED":
        meta = task.info or {}
        step = meta.get("step", "Running...")
        return {"task_id": task_id, "status": "running", "step": step}

    if task.state == "FAILURE":
        error_msg = str(task.result) if task.result else "Unknown error"
        return {"task_id": task_id, "status": "failed", "error": error_msg}

    if task.state == "SUCCESS":
        # Try to get from DB first
        db_record = db.query(BacktestResult).filter(
            BacktestResult.task_id == task_id
        ).first()

        if db_record and db_record.result_json:
            result = db_record.result_json
        else:
            result = task.result or {}

        run_type = (db_record.run_type or "single") if db_record else "single"
        if run_type == "sweep":
            return _build_sweep_payload(task_id, db_record, result)
        elif run_type == "walk_forward":
            return _build_wfa_payload(task_id, db_record, result)
        else:
            return _build_success_payload(task_id, db_record, result)

    return {"task_id": task_id, "status": task.state.lower()}


@router.get("/backtest/{task_id}/montecarlo")
async def get_monte_carlo(
    task_id: str,
    db: Session = Depends(get_db),
) -> dict:
    """Get only the Monte Carlo simulation results for lazy loading."""
    db_record = db.query(BacktestResult).filter(
        BacktestResult.task_id == task_id
    ).first()

    if not db_record:
        raise HTTPException(status_code=404, detail={"error": "Backtest not found"})

    if db_record.status != "SUCCESS" or not db_record.result_json:
        raise HTTPException(
            status_code=400,
            detail={"error": "Backtest not yet complete"},
        )

    monte_carlo = db_record.result_json.get("monte_carlo", {})
    return {"task_id": task_id, "monte_carlo": monte_carlo}


# ---------------------------------------------------------------------------
# Parameter Sweep
# ---------------------------------------------------------------------------

@router.post("/backtest/sweep")
async def submit_sweep(
    request: SweepRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> dict:
    """Submit a parameter sweep for asynchronous execution.

    Runs a grid search over all combinations of provided parameter values
    and returns the task_id for polling.
    """
    try:
        config_dict = request.config.model_dump()

        if settings.USE_CELERY:
            task = run_sweep_task.delay(
                strategy_code=request.strategy_code,
                tickers=request.tickers,
                start_date=request.start_date.isoformat(),
                end_date=request.end_date.isoformat(),
                param_grid=request.param_grid,
                base_config=config_dict,
                ticker_weights=request.ticker_weights,
                objective=request.objective,
            )
            task_id = task.id
            status = "PENDING"
        else:
            task_id = uuid.uuid4().hex
            status = "PENDING"
            background_tasks.add_task(
                run_sweep_local,
                task_id=task_id,
                strategy_code=request.strategy_code,
                tickers=request.tickers,
                start_date=request.start_date.isoformat(),
                end_date=request.end_date.isoformat(),
                param_grid=request.param_grid,
                base_config=config_dict,
                ticker_weights=request.ticker_weights,
                objective=request.objective,
            )

        db_record = BacktestResult(
            task_id=task_id,
            status=status,
            ticker=request.tickers[0] if request.tickers else None,
            tickers=request.tickers,
            strategy_code=request.strategy_code,
            start_date=request.start_date.isoformat(),
            end_date=request.end_date.isoformat(),
            config_json=config_dict,
            run_type="sweep",
        )
        db.add(db_record)
        db.commit()

        return {"task_id": task_id}

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={"error": f"Failed to submit sweep: {str(e)}"},
        )


@router.get("/backtest/{task_id}/sweep")
async def get_sweep_result(
    task_id: str,
    db: Session = Depends(get_db),
) -> dict:
    """Get the status and results of a parameter sweep task."""
    db_record = db.query(BacktestResult).filter(
        BacktestResult.task_id == task_id
    ).first()

    if not db_record:
        raise HTTPException(status_code=404, detail={"error": "Task not found"})

    if db_record.status == "PENDING":
        return {"task_id": task_id, "status": "pending", "run_type": "sweep"}

    if db_record.status == "RUNNING":
        return {
            "task_id": task_id,
            "status": "running",
            "run_type": "sweep",
            "progress": db_record.progress,
        }

    if db_record.status == "FAILURE":
        return {
            "task_id": task_id,
            "status": "failed",
            "error": db_record.error_message or "Unknown error",
        }

    if db_record.status == "SUCCESS":
        result = db_record.result_json or {}
        return _build_sweep_payload(task_id, db_record, result)

    return {"task_id": task_id, "status": db_record.status.lower()}


# ---------------------------------------------------------------------------
# Walk-Forward Analysis
# ---------------------------------------------------------------------------

@router.post("/backtest/walkforward")
async def submit_walkforward(
    request: WFARequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> dict:
    """Submit a walk-forward analysis for asynchronous execution."""
    try:
        config_dict = request.config.model_dump()

        if settings.USE_CELERY:
            task = run_walkforward_task.delay(
                strategy_code=request.strategy_code,
                tickers=request.tickers,
                start_date=request.start_date.isoformat(),
                end_date=request.end_date.isoformat(),
                param_grid=request.param_grid,
                base_config=config_dict,
                ticker_weights=request.ticker_weights,
                in_sample_days=request.in_sample_days,
                out_of_sample_days=request.out_of_sample_days,
                objective=request.objective,
                window_type=request.window_type,
                anchored=request.anchored,
                max_combinations=request.max_combinations,
            )
            task_id = task.id
            status = "PENDING"
        else:
            task_id = uuid.uuid4().hex
            status = "PENDING"
            background_tasks.add_task(
                run_walkforward_local,
                task_id=task_id,
                strategy_code=request.strategy_code,
                tickers=request.tickers,
                start_date=request.start_date.isoformat(),
                end_date=request.end_date.isoformat(),
                param_grid=request.param_grid,
                base_config=config_dict,
                ticker_weights=request.ticker_weights,
                in_sample_days=request.in_sample_days,
                out_of_sample_days=request.out_of_sample_days,
                objective=request.objective,
                window_type=request.window_type,
                anchored=request.anchored,
                max_combinations=request.max_combinations,
            )


        db_record = BacktestResult(
            task_id=task_id,
            status=status,
            ticker=request.tickers[0] if request.tickers else None,
            tickers=request.tickers,
            strategy_code=request.strategy_code,
            start_date=request.start_date.isoformat(),
            end_date=request.end_date.isoformat(),
            config_json=config_dict,
            run_type="walk_forward",
        )
        db.add(db_record)
        db.commit()

        return {"task_id": task_id}

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={"error": f"Failed to submit walk-forward: {str(e)}"},
        )


@router.get("/backtest/{task_id}/walkforward")
async def get_walkforward_result(
    task_id: str,
    db: Session = Depends(get_db),
) -> dict:
    """Get the status and results of a walk-forward analysis task."""
    db_record = db.query(BacktestResult).filter(
        BacktestResult.task_id == task_id
    ).first()

    if not db_record:
        raise HTTPException(status_code=404, detail={"error": "Task not found"})

    if db_record.status == "PENDING":
        return {"task_id": task_id, "status": "pending", "run_type": "walk_forward"}

    if db_record.status == "RUNNING":
        return {
            "task_id": task_id,
            "status": "running",
            "run_type": "walk_forward",
            "progress": db_record.progress,
        }

    if db_record.status == "FAILURE":
        return {
            "task_id": task_id,
            "status": "failed",
            "error": db_record.error_message or "Unknown error",
        }

    if db_record.status == "SUCCESS":
        result = db_record.result_json or {}
        return _build_wfa_payload(task_id, db_record, result)

    return {"task_id": task_id, "status": db_record.status.lower()}


# ---------------------------------------------------------------------------
# Walk-Forward Pre-flight Estimate
# ---------------------------------------------------------------------------

@router.post("/backtest/walkforward/estimate")
async def estimate_walkforward(
    request: WFAEstimateRequest,
) -> dict:
    """Estimate the number of backtests a WFA config will run without launching any.

    Used by the frontend to show a pre-flight badge (e.g. '~36 backtests') before
    the user submits, and to disable the Run button if the cap is exceeded.

    Returns:
        WFAEstimateResponse with n_folds, n_combinations, total_runs, feasible, error.
    """
    result = estimate_wfa_runs(
        start_date=request.start_date,
        end_date=request.end_date,
        in_sample_days=request.in_sample_days,
        out_of_sample_days=request.out_of_sample_days,
        window_type=request.window_type,
        anchored=request.anchored,
        param_grid=request.param_grid,
        max_combinations=request.max_combinations,
    )
    return result


# ---------------------------------------------------------------------------
# Strategy Templates
# ---------------------------------------------------------------------------

@router.get("/strategies/templates")
async def get_strategy_templates() -> dict:
    """Get all available strategy templates."""
    return {"templates": STRATEGY_TEMPLATES}


# ---------------------------------------------------------------------------
# Response payload builders
# ---------------------------------------------------------------------------

def _build_sweep_payload(task_id: str, db_record: BacktestResult, result: dict) -> dict:
    """Build the sweep success response payload."""
    return {
        "task_id": task_id,
        "status": "success",
        "run_type": "sweep",
        "sweep_results": result.get("sweep_results", []),
        "best_params": result.get("best_params", {}),
        "total_combinations": result.get("total_combinations", 0),
        "objective": result.get("objective", "sharpe_ratio"),
        "param_grid": result.get("param_grid", {}),
    }


def _build_wfa_payload(task_id: str, db_record: BacktestResult, result: dict) -> dict:
    """Build the walk-forward success response payload."""
    return {
        "task_id": task_id,
        "status": "success",
        "run_type": "walk_forward",
        "wfa_windows": result.get("wfa_windows", []),
        "combined_oos_equity": result.get("combined_oos_equity", []),
        "aggregate_oos_metrics": result.get("aggregate_oos_metrics", {}),
        "total_windows": result.get("total_windows", 0),
        "in_sample_days": result.get("in_sample_days", 365),
        "out_of_sample_days": result.get("out_of_sample_days", 90),
        "window_type": result.get("window_type", "rolling"),
        "anchored": result.get("anchored", False),
        "param_grid": result.get("param_grid", {}),
        "objective": result.get("objective", "sharpe_ratio"),
        "efficiency_ratios": result.get("efficiency_ratios", []),
        "aggregate_efficiency_ratio": result.get("aggregate_efficiency_ratio"),
        "param_stability": result.get("param_stability", {}),
    }
