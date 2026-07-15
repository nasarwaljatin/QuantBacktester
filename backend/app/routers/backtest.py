# backend/app/routers/backtest.py
"""Backtest API endpoints — submit, poll, and retrieve results."""

import uuid
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.schemas.backtest import BacktestRequest, BacktestResponse
from app.models.backtest import BacktestResult
from app.tasks.backtest_task import run_backtest_task, run_backtest_local
from app.engine.strategies import STRATEGY_TEMPLATES

router = APIRouter(prefix="/api", tags=["backtest"])


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
        - If SUCCESS: Full BacktestResponse with equity_curve, metrics, trades, monte_carlo
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
            return {"task_id": task_id, "status": "running", "step": "Running backtest..."}

        if db_record.status == "FAILURE":
            return {
                "task_id": task_id,
                "status": "failed",
                "error": db_record.error_message or "Unknown error",
            }

        if db_record.status == "SUCCESS":
            result = db_record.result_json or {}
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
            }

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

        return {
            "task_id": task_id,
            "status": "success",
            "ticker": db_record.ticker if db_record else "",
            "tickers": db_record.tickers if db_record else None,
            "ticker_weights": result.get("ticker_weights", {}),
            "start_date": db_record.start_date if db_record else "",
            "end_date": db_record.end_date if db_record else "",
            "equity_curve": result.get("equity_curve", []),
            "benchmark_curve": result.get("benchmark_curve", []),
            "trades": result.get("trades", []),
            "metrics": result.get("metrics", {}),
            "monte_carlo": result.get("monte_carlo", {}),
            "allocation_pct": result.get("allocation_pct", 100.0),
            "position_sizing": result.get("position_sizing", "cash_percentage"),
            "sizing_model": result.get("sizing_model", "all_in"),
            "sizing_params": result.get("sizing_params", {}),
        }

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


@router.get("/strategies/templates")
async def get_strategy_templates() -> dict:
    """Get all available strategy templates."""
    return {"templates": STRATEGY_TEMPLATES}
