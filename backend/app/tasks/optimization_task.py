# backend/app/tasks/optimization_task.py
"""Background tasks for parameter sweeps and walk-forward analysis."""

import uuid
from datetime import date, datetime
from typing import Optional

from app.tasks.celery_app import celery_app
from app.database import SessionLocal
from app.models.backtest import BacktestResult
from app.services.optimization_service import run_parameter_sweep, run_walk_forward_analysis


# ---------------------------------------------------------------------------
# Celery tasks
# ---------------------------------------------------------------------------

@celery_app.task(bind=True, name="run_sweep_task", max_retries=0)
def run_sweep_task(
    self,
    strategy_code: str,
    tickers: list,
    start_date: str,
    end_date: str,
    param_grid: dict,
    base_config: dict,
    ticker_weights: Optional[dict] = None,
    objective: str = "sharpe_ratio",
) -> dict:
    """Celery task: run a full parameter sweep."""
    task_id = self.request.id
    db = SessionLocal()
    try:
        self.update_state(state="STARTED", meta={"step": "Fetching data..."})
        start = date.fromisoformat(start_date)
        end = date.fromisoformat(end_date)

        record = db.query(BacktestResult).filter(BacktestResult.task_id == task_id).first()
        if record:
            record.status = "RUNNING"
            record.run_type = "sweep"
            db.commit()

        self.update_state(state="STARTED", meta={"step": "Running sweep..."})

        result = run_parameter_sweep(
            task_id=task_id,
            strategy_code=strategy_code,
            tickers=tickers,
            start_date=start,
            end_date=end,
            param_grid=param_grid,
            base_config=base_config,
            db=db,
            ticker_weights=ticker_weights,
            objective=objective,
        )

        if record:
            record.status = "SUCCESS"
            record.result_json = result
            record.completed_at = datetime.utcnow()
            db.commit()

        return result
    except Exception as e:
        try:
            record = db.query(BacktestResult).filter(BacktestResult.task_id == task_id).first()
            if record:
                record.status = "FAILURE"
                record.error_message = str(e)
                record.completed_at = datetime.utcnow()
                db.commit()
        except Exception:
            pass
        raise
    finally:
        db.close()


@celery_app.task(bind=True, name="run_walkforward_task", max_retries=0)
def run_walkforward_task(
    self,
    strategy_code: str,
    tickers: list,
    start_date: str,
    end_date: str,
    param_grid: dict,
    base_config: dict,
    ticker_weights: Optional[dict] = None,
    in_sample_days: int = 365,
    out_of_sample_days: int = 90,
    objective: str = "sharpe_ratio",
    window_type: str = "rolling",
    anchored: bool = False,
    max_combinations: int = 200,
) -> dict:
    """Celery task: run a full walk-forward analysis."""

    task_id = self.request.id
    db = SessionLocal()
    try:
        self.update_state(state="STARTED", meta={"step": "Splitting windows..."})
        start = date.fromisoformat(start_date)
        end = date.fromisoformat(end_date)

        record = db.query(BacktestResult).filter(BacktestResult.task_id == task_id).first()
        if record:
            record.status = "RUNNING"
            record.run_type = "walk_forward"
            db.commit()

        result = run_walk_forward_analysis(
            task_id=task_id,
            strategy_code=strategy_code,
            tickers=tickers,
            start_date=start,
            end_date=end,
            param_grid=param_grid,
            base_config=base_config,
            db=db,
            ticker_weights=ticker_weights,
            in_sample_days=in_sample_days,
            out_of_sample_days=out_of_sample_days,
            objective=objective,
            window_type=window_type,
            anchored=anchored,
            max_combinations=max_combinations,
        )


        if record:
            record.status = "SUCCESS"
            record.result_json = result
            record.completed_at = datetime.utcnow()
            db.commit()

        return result
    except Exception as e:
        try:
            record = db.query(BacktestResult).filter(BacktestResult.task_id == task_id).first()
            if record:
                record.status = "FAILURE"
                record.error_message = str(e)
                record.completed_at = datetime.utcnow()
                db.commit()
        except Exception:
            pass
        raise
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Local (FastAPI BackgroundTask) versions
# ---------------------------------------------------------------------------

def run_sweep_local(
    task_id: str,
    strategy_code: str,
    tickers: list,
    start_date: str,
    end_date: str,
    param_grid: dict,
    base_config: dict,
    ticker_weights: Optional[dict] = None,
    objective: str = "sharpe_ratio",
) -> None:
    """Local background function: run a full parameter sweep."""
    db = SessionLocal()
    try:
        start = date.fromisoformat(start_date)
        end = date.fromisoformat(end_date)

        record = db.query(BacktestResult).filter(BacktestResult.task_id == task_id).first()
        if record:
            record.status = "RUNNING"
            record.run_type = "sweep"
            db.commit()

        result = run_parameter_sweep(
            task_id=task_id,
            strategy_code=strategy_code,
            tickers=tickers,
            start_date=start,
            end_date=end,
            param_grid=param_grid,
            base_config=base_config,
            db=db,
            ticker_weights=ticker_weights,
            objective=objective,
        )

        if record:
            record.status = "SUCCESS"
            record.result_json = result
            record.completed_at = datetime.utcnow()
            db.commit()

    except Exception as e:
        try:
            record = db.query(BacktestResult).filter(BacktestResult.task_id == task_id).first()
            if record:
                record.status = "FAILURE"
                record.error_message = str(e)
                record.completed_at = datetime.utcnow()
                db.commit()
        except Exception:
            pass
    finally:
        db.close()


def run_walkforward_local(
    task_id: str,
    strategy_code: str,
    tickers: list,
    start_date: str,
    end_date: str,
    param_grid: dict,
    base_config: dict,
    ticker_weights: Optional[dict] = None,
    in_sample_days: int = 365,
    out_of_sample_days: int = 90,
    objective: str = "sharpe_ratio",
    window_type: str = "rolling",
    anchored: bool = False,
    max_combinations: int = 200,
) -> None:
    """Local background function: run a full walk-forward analysis."""

    db = SessionLocal()
    try:
        start = date.fromisoformat(start_date)
        end = date.fromisoformat(end_date)

        record = db.query(BacktestResult).filter(BacktestResult.task_id == task_id).first()
        if record:
            record.status = "RUNNING"
            record.run_type = "walk_forward"
            db.commit()

        result = run_walk_forward_analysis(
            task_id=task_id,
            strategy_code=strategy_code,
            tickers=tickers,
            start_date=start,
            end_date=end,
            param_grid=param_grid,
            base_config=base_config,
            db=db,
            ticker_weights=ticker_weights,
            in_sample_days=in_sample_days,
            out_of_sample_days=out_of_sample_days,
            objective=objective,
            window_type=window_type,
            anchored=anchored,
            max_combinations=max_combinations,
        )


        if record:
            record.status = "SUCCESS"
            record.result_json = result
            record.completed_at = datetime.utcnow()
            db.commit()

    except Exception as e:
        try:
            record = db.query(BacktestResult).filter(BacktestResult.task_id == task_id).first()
            if record:
                record.status = "FAILURE"
                record.error_message = str(e)
                record.completed_at = datetime.utcnow()
                db.commit()
        except Exception:
            pass
    finally:
        db.close()
