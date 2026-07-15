# backend/app/tasks/backtest_task.py
"""Celery task for running backtests asynchronously."""

import json
from datetime import date, datetime
from typing import Optional
from fastapi import HTTPException
from app.tasks.celery_app import celery_app
from app.database import SessionLocal
from app.models.backtest import BacktestResult
from app.services.backtest_service import execute_backtest


@celery_app.task(bind=True, name="run_backtest_task", max_retries=0)
def run_backtest_task(
    self,
    strategy_code: str,
    ticker: str,
    start_date: str,
    end_date: str,
    config_dict: dict,
    tickers: Optional[list] = None,
    ticker_weights: Optional[dict] = None,
) -> dict:
    """Celery task that runs a full backtest pipeline.

    Args:
        strategy_code: Python source code for UserStrategy class.
        ticker: Stock ticker symbol.
        start_date: ISO format start date string.
        end_date: ISO format end date string.
        config_dict: Dict with initial_capital, commission, slippage.
        tickers: Optional list of stock ticker symbols.
        ticker_weights: Optional weights allocation per ticker.

    Returns:
        Dict with complete backtest results or error information.
    """
    task_id = self.request.id
    db = SessionLocal()

    try:
        # Update task state
        self.update_state(state="STARTED", meta={"step": "Fetching data..."})

        # Parse dates
        start = date.fromisoformat(start_date)
        end = date.fromisoformat(end_date)

        # Create or update the DB record
        result_record = db.query(BacktestResult).filter(
            BacktestResult.task_id == task_id
        ).first()

        if not result_record:
            result_record = BacktestResult(
                task_id=task_id,
                status="RUNNING",
                ticker=ticker,
                tickers=tickers,
                strategy_code=strategy_code,
                start_date=start_date,
                end_date=end_date,
                config_json=config_dict,
            )
            db.add(result_record)
            db.commit()
        else:
            result_record.status = "RUNNING"
            db.commit()

        # Update state: running backtest
        self.update_state(state="STARTED", meta={"step": "Running backtest..."})

        # Execute the backtest
        result = execute_backtest(
            strategy_code=strategy_code,
            ticker=ticker,
            start_date=start,
            end_date=end,
            config=config_dict,
            db=db,
            tickers=tickers,
            ticker_weights=ticker_weights,
        )

        # Update state: computing metrics
        self.update_state(state="STARTED", meta={"step": "Computing metrics..."})

        # Store result in DB
        result_record.status = "SUCCESS"
        result_record.result_json = result
        result_record.completed_at = datetime.utcnow()
        db.commit()

        return result

    except Exception as e:
        error_msg = str(e)

        # Update DB with error
        try:
            result_record = db.query(BacktestResult).filter(
                BacktestResult.task_id == task_id
            ).first()
            if result_record:
                result_record.status = "FAILURE"
                result_record.error_message = error_msg
                result_record.completed_at = datetime.utcnow()
                db.commit()
        except Exception:
            pass

        # Re-raise so Celery marks the task as failed
        raise

    finally:
        db.close()


def run_backtest_local(
    task_id: str,
    strategy_code: str,
    ticker: str,
    start_date: str,
    end_date: str,
    config_dict: dict,
    tickers: Optional[list] = None,
    ticker_weights: Optional[dict] = None,
) -> dict:
    """Run a backtest synchronously in a local thread (FastAPI background task).

    Args:
        task_id: Unique task ID.
        strategy_code: Python source code for UserStrategy class.
        ticker: Stock ticker symbol.
        start_date: ISO format start date string.
        end_date: ISO format end date string.
        config_dict: Dict with initial_capital, commission, slippage.
        tickers: Optional list of stock ticker symbols.
        ticker_weights: Optional weights allocation per ticker.

    Returns:
        Dict with complete backtest results.
    """
    db = SessionLocal()

    try:
        # Parse dates
        start = date.fromisoformat(start_date)
        end = date.fromisoformat(end_date)

        # Create or update the DB record
        result_record = db.query(BacktestResult).filter(
            BacktestResult.task_id == task_id
        ).first()

        if not result_record:
            result_record = BacktestResult(
                task_id=task_id,
                status="RUNNING",
                ticker=ticker,
                tickers=tickers,
                strategy_code=strategy_code,
                start_date=start_date,
                end_date=end_date,
                config_json=config_dict,
            )
            db.add(result_record)
            db.commit()
        else:
            result_record.status = "RUNNING"
            db.commit()

        # Execute the backtest
        result = execute_backtest(
            strategy_code=strategy_code,
            ticker=ticker,
            start_date=start,
            end_date=end,
            config=config_dict,
            db=db,
            tickers=tickers,
            ticker_weights=ticker_weights,
        )

        # Store result in DB
        result_record.status = "SUCCESS"
        result_record.result_json = result
        result_record.completed_at = datetime.utcnow()
        db.commit()

        return result

    except HTTPException as he:
        error_msg = he.detail
        if isinstance(error_msg, dict) and "error" in error_msg:
            error_msg = error_msg["error"]
        elif isinstance(error_msg, dict):
            error_msg = str(error_msg)

        try:
            result_record = db.query(BacktestResult).filter(
                BacktestResult.task_id == task_id
            ).first()
            if result_record:
                result_record.status = "FAILURE"
                result_record.error_message = str(error_msg)
                result_record.completed_at = datetime.utcnow()
                db.commit()
        except Exception:
            pass

    except Exception as e:
        error_msg = str(e)

        try:
            result_record = db.query(BacktestResult).filter(
                BacktestResult.task_id == task_id
            ).first()
            if result_record:
                result_record.status = "FAILURE"
                result_record.error_message = error_msg
                result_record.completed_at = datetime.utcnow()
                db.commit()
        except Exception:
            pass

    finally:
        db.close()

