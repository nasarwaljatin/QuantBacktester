# backend/tests/test_sweep_execution.py
"""End-to-end tests for parameter sweeps and walk-forward runs.

Regression tests for sweep parameter injection: the old code replaced Backtrader's
params class with a tuple, so every combination failed with
"TypeError: 'tuple' object is not callable".
"""

import math
import uuid
from datetime import date, timedelta

import backtrader as bt
import pandas as pd
import pytest

from app.database import Base, SessionLocal, engine
from app.engine.runner import run_backtest
from app.models.backtest import BacktestResult
from app.models.optimization import SweepResult
from app.schemas.backtest import BacktestConfig
from app.services import optimization_service

START = date(2020, 1, 1)
END = date(2021, 6, 30)

SMA_CODE = '''class UserStrategy(bt.Strategy):
    params = dict(fast=5, slow=20)

    def __init__(self):
        self.crossover = bt.ind.CrossOver(
            bt.ind.SMA(period=self.p.fast), bt.ind.SMA(period=self.p.slow)
        )

    def next(self):
        if not self.position and self.crossover > 0:
            self.buy()
        elif self.position and self.crossover < 0:
            self.close()
'''


def make_ohlcv(start: date = START, end: date = END) -> pd.DataFrame:
    """Daily bars with two overlapping cycles, so moving averages cross often."""
    rows = []
    d, i = start, 0
    while d <= end:
        price = 100 + 8 * math.sin(i / 9) + 4 * math.sin(i / 23)
        rows.append({
            "date": pd.Timestamp(d), "open": price, "high": price + 1,
            "low": price - 1, "close": price, "volume": 1_000_000,
        })
        d += timedelta(days=1)
        i += 1
    return pd.DataFrame(rows)


def ohlcv_slice(ticker, start, end, db):
    """Stand-in for get_ohlcv: synthetic data for the requested range, no network."""
    df = make_ohlcv()
    mask = (df["date"] >= pd.Timestamp(start)) & (df["date"] <= pd.Timestamp(end))
    return df[mask].reset_index(drop=True)


@pytest.fixture
def config() -> dict:
    # 90%, not the default 100%: all-in sizing spends all cash at the close, and the
    # next-bar fill plus commission/slippage then exceeds cash, so Backtrader rejects
    # the order (Margin). Headroom keeps these tests about parameter handling.
    return BacktestConfig(allocation_pct=90.0).model_dump()


@pytest.fixture
def db():
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    yield session
    session.close()


def new_task(db, run_type: str) -> str:
    task_id = uuid.uuid4().hex
    db.add(BacktestResult(
        task_id=task_id, status="RUNNING", strategy_code=SMA_CODE,
        start_date=START.isoformat(), end_date=END.isoformat(), run_type=run_type,
    ))
    db.commit()
    return task_id


# --- run_backtest(strategy_params=...) ---------------------------------------

def test_run_backtest_applies_strategy_params(config):
    seen = {}

    class Recorder(bt.Strategy):
        params = dict(fast=5, slow=20)

        def __init__(self):
            seen["fast"], seen["slow"] = self.p.fast, self.p.slow

        def next(self):
            pass

    run_backtest(Recorder, {"AAPL": make_ohlcv()}, config, strategy_params={"fast": 3, "slow": 40})
    assert seen == {"fast": 3, "slow": 40}


def test_run_backtest_without_params_uses_defaults(config):
    seen = {}

    class Recorder(bt.Strategy):
        params = dict(fast=5, slow=20)

        def __init__(self):
            seen["fast"], seen["slow"] = self.p.fast, self.p.slow

    run_backtest(Recorder, {"AAPL": make_ohlcv()}, config)
    assert seen == {"fast": 5, "slow": 20}


def test_run_backtest_rejects_unknown_param(config):
    class Plain(bt.Strategy):
        params = dict(fast=5)

    with pytest.raises(ValueError, match="Unknown strategy parameter"):
        run_backtest(Plain, {"AAPL": make_ohlcv()}, config, strategy_params={"window": 10})


# --- _run_single_combination ---------------------------------------------------

def test_single_combination_with_two_params_succeeds(config):
    result = optimization_service._run_single_combination(
        0, {"fast": 3, "slow": 12}, SMA_CODE, {"AAPL": make_ohlcv()}, config, None
    )
    assert result["status"] == "SUCCESS", result["error_message"]
    assert result["metrics"]["total_trades"] > 0


def test_different_params_give_different_results(config):
    data = {"AAPL": make_ohlcv()}
    a = optimization_service._run_single_combination(0, {"fast": 3, "slow": 12}, SMA_CODE, data, config, None)
    b = optimization_service._run_single_combination(1, {"fast": 10, "slow": 40}, SMA_CODE, data, config, None)
    assert a["status"] == b["status"] == "SUCCESS"
    assert (a["metrics"]["total_trades"], a["equity_curve"][-1]["value"]) != (
        b["metrics"]["total_trades"], b["equity_curve"][-1]["value"]
    )


def test_unknown_param_is_reported_not_crashing(config):
    result = optimization_service._run_single_combination(
        0, {"window": 3}, SMA_CODE, {"AAPL": make_ohlcv()}, config, None
    )
    assert result["status"] == "FAILURE"
    assert "Unknown strategy parameter" in result["error_message"]


# --- full sweep and walk-forward ----------------------------------------------

def test_parameter_sweep_end_to_end(monkeypatch, db, config):
    monkeypatch.setattr(optimization_service, "get_ohlcv", ohlcv_slice)
    task_id = new_task(db, "sweep")
    grid = {"fast": [3, 5], "slow": [12, 30]}

    out = optimization_service.run_parameter_sweep(
        task_id, SMA_CODE, ["AAPL"], START, END, grid, config, db, max_workers=2
    )

    statuses = [r["status"] for r in out["sweep_results"]]
    assert statuses == ["SUCCESS"] * 4, [r["error_message"] for r in out["sweep_results"]]
    assert out["best_params"] in [r["parameters"] for r in out["sweep_results"]]
    assert db.query(SweepResult).filter(SweepResult.task_id == task_id).count() == 4
    record = db.query(BacktestResult).filter(BacktestResult.task_id == task_id).first()
    assert record.progress == "4 / 4 combinations"


def test_walk_forward_end_to_end(monkeypatch, db, config):
    monkeypatch.setattr(optimization_service, "get_ohlcv", ohlcv_slice)
    task_id = new_task(db, "walk_forward")
    grid = {"fast": [3, 5], "slow": [12, 20]}

    out = optimization_service.run_walk_forward_analysis(
        task_id, SMA_CODE, ["AAPL"], START, END, grid, config, db,
        in_sample_days=180, out_of_sample_days=90, max_workers=2,
    )

    assert out["total_windows"] >= 2
    combos = [{"fast": f, "slow": s} for f in grid["fast"] for s in grid["slow"]]
    for window in out["wfa_windows"]:
        assert window["status"] == "SUCCESS"
        assert window["in_sample_metrics"] is not None  # a real IS winner, not the fallback
        assert window["optimized_params"] in combos
    assert len(out["combined_oos_equity"]) > 0
