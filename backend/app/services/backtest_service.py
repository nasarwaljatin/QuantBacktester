# backend/app/services/backtest_service.py
"""High-level backtest orchestration service."""

from datetime import date
from typing import Any, Optional, Dict, List
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
    tickers: Optional[list[str]] = None,
    ticker_weights: Optional[dict[str, float]] = None,
) -> dict[str, Any]:
    """Execute a complete backtest pipeline.

    Steps:
        1. Fetch OHLCV data (with caching) for all tickers
        2. Compile user strategy code in sandbox
        3. Run backtest via Backtrader (multi-asset data feeds)
        4. Compute performance metrics on portfolio equity curve
        5. Run Monte Carlo simulation
        6. Generate portfolio buy-and-hold benchmark

    Args:
        strategy_code: Python source code for UserStrategy class.
        ticker: Stock ticker symbol (backward compatibility).
        start_date: Backtest start date.
        end_date: Backtest end date.
        config: Dict with initial_capital, commission, slippage.
        db: SQLAlchemy session for data caching.
        tickers: Optional list of stock ticker symbols.
        ticker_weights: Optional weights allocation per ticker.

    Returns:
        Complete result dict with equity_curve, benchmark, trades, metrics, monte_carlo.
    """
    # Resolve tickers
    if not tickers:
        tickers = [ticker] if ticker else []

    # Step 1: Fetch OHLCV data for all tickers
    ohlcv_dfs = {}
    for t in tickers:
        ohlcv_dfs[t] = get_ohlcv(t, start_date, end_date, db)

    # Step 2: Compile user strategy
    strategy_class = compile_user_strategy(strategy_code)

    # Step 3: Run backtest
    backtest_result = run_backtest(strategy_class, ohlcv_dfs, config, ticker_weights)

    # Step 4: Compute performance metrics
    equity_values = [point["value"] for point in backtest_result["equity_curve"]]
    trades = backtest_result["trades"]
    metrics = compute_all_metrics(equity_values, trades)

    # Step 5: Run Monte Carlo simulation
    initial_capital = config.get("initial_capital", 100000.0)
    monte_carlo = run_monte_carlo(trades, n_simulations=1000, initial_capital=initial_capital)

    # Step 6: Generate buy-and-hold benchmark (aggregate portfolio benchmark)
    benchmark_curve = _compute_portfolio_benchmark(ohlcv_dfs, initial_capital, ticker_weights)

    return {
        "equity_curve": backtest_result["equity_curve"],
        "benchmark_curve": benchmark_curve,
        "trades": trades,
        "metrics": metrics.model_dump(),
        "monte_carlo": monte_carlo,
        "analyzer_results": backtest_result["analyzer_results"],
        "allocation_pct": config.get("allocation_pct", 100.0),
        "position_sizing": "cash_percentage",
        "ticker_weights": ticker_weights or {},
        "sizing_model": config.get("sizing_model", "all_in"),
        "sizing_params": config.get("sizing_params", {}),
    }


def _compute_portfolio_benchmark(
    ohlcv_dfs: dict[str, Any],
    initial_capital: float,
    ticker_weights: Optional[dict[str, float]] = None,
) -> list[dict[str, Any]]:
    """Compute an aggregate buy-and-hold benchmark curve for multiple assets."""
    if not ohlcv_dfs:
        return []

    tickers = list(ohlcv_dfs.keys())
    if not ticker_weights:
        # Equal weights
        weights = {t: 1.0 / len(tickers) for t in tickers}
    else:
        # Normalise weights to sum to 1.0
        total_w = sum(ticker_weights.values())
        if total_w > 0:
            weights = {t: ticker_weights.get(t, 0.0) / total_w for t in tickers}
        else:
            weights = {t: 1.0 / len(tickers) for t in tickers}

    benchmarks_by_date = {}
    for t, df in ohlcv_dfs.items():
        allocated_cap = initial_capital * weights.get(t, 0.0)
        ticker_bench = _compute_benchmark(df, allocated_cap)
        for pt in ticker_bench:
            date_str = pt["date"]
            benchmarks_by_date[date_str] = benchmarks_by_date.get(date_str, 0.0) + pt["value"]

    sorted_dates = sorted(benchmarks_by_date.keys())
    return [{"date": d, "value": round(benchmarks_by_date[d], 2)} for d in sorted_dates]


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
