# backend/tests/test_celery_dispatch.py
"""Celery wiring: task registration and dispatch ordering.

Regression tests for two bugs:
  * celery_app only included backtest_task, so a worker started with
    `celery -A app.tasks.celery_app worker` rejected sweep and walk-forward tasks
    as unregistered;
  * the API dispatched the task before inserting its DB row, so a fast worker could
    start first (the single-backtest task then created its own row and the API's
    insert failed; sweep/WFA tasks found no row and never stored their result).
"""

import os
import subprocess
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.database import Base, SessionLocal, engine
from app.main import app
from app.models.backtest import BacktestResult
from app.routers import backtest as backtest_router

BACKEND_DIR = Path(__file__).resolve().parents[1]
CODE = "class UserStrategy(bt.Strategy):\n    params = dict(fast=5)\n    def next(self):\n        pass"
WINDOW = {"start_date": "2020-01-01", "end_date": "2022-01-01"}

ENDPOINTS = [
    ("/api/backtest", "run_backtest_task", "single",
     {"strategy_code": CODE, "ticker": "AAPL", **WINDOW}),
    ("/api/backtest/sweep", "run_sweep_task", "sweep",
     {"strategy_code": CODE, "tickers": ["AAPL"], "param_grid": {"fast": [3, 5]}, **WINDOW}),
    ("/api/backtest/walkforward", "run_walkforward_task", "walk_forward",
     {"strategy_code": CODE, "tickers": ["AAPL"], "param_grid": {"fast": [3, 5]}, **WINDOW}),
]


@pytest.fixture
def client():
    Base.metadata.create_all(bind=engine)
    return TestClient(app)


def find_record(task_id: str):
    session = SessionLocal()
    try:
        return session.query(BacktestResult).filter(BacktestResult.task_id == task_id).first()
    finally:
        session.close()


def test_worker_registers_every_task():
    """Import exactly what a worker imports (the app + its `include` list) in a fresh process."""
    script = (
        "from app.tasks.celery_app import celery_app\n"
        "celery_app.loader.import_default_modules()\n"
        "print(' '.join(sorted(n for n in celery_app.tasks if n.startswith('run_'))))\n"
    )
    out = subprocess.run(
        [sys.executable, "-c", script], cwd=BACKEND_DIR, env=os.environ.copy(),
        capture_output=True, text=True, timeout=120,
    )
    assert out.returncode == 0, out.stderr
    assert set(out.stdout.split()) >= {"run_backtest_task", "run_sweep_task", "run_walkforward_task"}


@pytest.mark.parametrize("url,task_name,run_type,payload", ENDPOINTS)
def test_row_exists_before_task_is_dispatched(monkeypatch, client, url, task_name, run_type, payload):
    monkeypatch.setattr(settings, "USE_CELERY", True)
    dispatched = {}

    def fake_apply_async(kwargs=None, task_id=None, **_):
        record = find_record(task_id)  # what a worker starting right now would see
        dispatched.update(task_id=task_id, kwargs=kwargs, row_status=record.status if record else None)

    monkeypatch.setattr(getattr(backtest_router, task_name), "apply_async", fake_apply_async)

    response = client.post(url, json=payload)

    assert response.status_code == 200, response.text
    assert dispatched["row_status"] == "PENDING"
    assert dispatched["task_id"] == response.json()["task_id"]
    assert dispatched["kwargs"]["strategy_code"] == CODE
    assert find_record(dispatched["task_id"]).run_type == run_type


@pytest.mark.parametrize("url,task_name,run_type,payload", ENDPOINTS)
def test_failed_dispatch_marks_row_failed(monkeypatch, client, url, task_name, run_type, payload):
    monkeypatch.setattr(settings, "USE_CELERY", True)
    seen = {}

    def broken_apply_async(kwargs=None, task_id=None, **_):
        seen["task_id"] = task_id
        raise ConnectionError("broker unreachable")

    monkeypatch.setattr(getattr(backtest_router, task_name), "apply_async", broken_apply_async)

    response = client.post(url, json=payload)

    assert response.status_code == 500
    record = find_record(seen["task_id"])
    assert record.status == "FAILURE"
    assert "broker unreachable" in record.error_message
