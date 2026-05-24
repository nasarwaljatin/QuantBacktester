# backend/app/services/backtest_service.py
"""High-level backtest orchestration service."""

from datetime import date
from typing import Any
from sqlalchemy.orm import Session

from app.services.data_service import get_ohlcv
from app.services.metrics_service import compute_all_metrics
from app.services.montecarlo_service import run_monte_carlo
from app.engine.strategy_sandbox import compile_user_strategy
from app.engine.runner import run_backtest


def execute_backtest(
    strategy_code: str,
    ticker: str,
    start_date: date,
    end_date: date,
    config: dict[str, Any],
    db: Session,
) -> dict[str, Any]:
    """Execute a complete backtest pipeline.

    Steps:
        1. Fetch OHLCV data (with caching)
        2. Compile user strategy code in sandbox
        3. Run backtest via Backtrader
        4. Compute performance metrics
        5. Run Monte Carlo simulation
        6. Generate buy-and-hold benchmark

    Args:
        strategy_code: Python source code for UserStrategy class.
        ticker: Stock ticker symbol.
        start_date: Backtest start date.
        end_date: Backtest end date.
        config: Dict with initial_capital, commission, slippage.
        db: SQLAlchemy session for data caching.

    Returns:
        Complete result dict with equity_curve, benchmark, trades, metrics, monte_carlo.
    """
    # Step 1: Fetch OHLCV data
    ohlcv_df = get_ohlcv(ticker, start_date, end_date, db)

    # Step 2: Compile user strategy
    strategy_class = compile_user_strategy(strategy_code)

    # Step 3: Run backtest
    backtest_result = run_backtest(strategy_class, ohlcv_df, config)

    # Step 4: Compute performance metrics
    equity_values = [point["value"] for point in backtest_result["equity_curve"]]
    trades = backtest_result["trades"]
    metrics = compute_all_metrics(equity_values, trades)

    # Step 5: Run Monte Carlo simulation
    initial_capital = config.get("initial_capital", 100000.0)
    monte_carlo = run_monte_carlo(trades, n_simulations=1000, initial_capital=initial_capital)

    # Step 6: Generate buy-and-hold benchmark
    benchmark_curve = _compute_benchmark(ohlcv_df, initial_capital)

    return {
        "equity_curve": backtest_result["equity_curve"],
        "benchmark_curve": benchmark_curve,
        "trades": trades,
        "metrics": metrics.model_dump(),
        "monte_carlo": monte_carlo,
        "analyzer_results": backtest_result["analyzer_results"],
    }


def _compute_benchmark(
    ohlcv_df: "pd.DataFrame", initial_capital: float
) -> list[dict[str, Any]]:
    """Compute a buy-and-hold benchmark equity curve.

    Args:
        ohlcv_df: OHLCV DataFrame with date and close columns.
        initial_capital: Starting capital for the benchmark.

    Returns:
        List of {date, value} dicts representing the benchmark curve.
    """
    import pandas as pd

    df = ohlcv_df.copy()
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date")

    if df.empty:
        return []

    first_close = float(df.iloc[0]["close"])
    if first_close == 0:
        return []

    shares = initial_capital / first_close
    benchmark = []
    for _, row in df.iterrows():
        dt = row["date"]
        date_str = dt.strftime("%Y-%m-%d") if hasattr(dt, "strftime") else str(dt)
        benchmark.append({
            "date": date_str,
            "value": round(float(row["close"]) * shares, 2),
        })

    return benchmark
