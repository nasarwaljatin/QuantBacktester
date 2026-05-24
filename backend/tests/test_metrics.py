# backend/tests/test_metrics.py
"""Unit tests for the metrics service."""

import pytest
import numpy as np
from app.services.metrics_service import (
    sharpe_ratio,
    sortino_ratio,
    max_drawdown,
    calmar_ratio,
    win_rate,
    profit_factor,
    avg_holding_period,
    compute_all_metrics,
)


def test_empty_or_zero_trades():
    """Verify metrics return fallback values when no trades are made."""
    assert win_rate([]) == 0.0
    assert profit_factor([]) == 0.0
    assert avg_holding_period([]) == 0.0


def test_sharpe_ratio():
    """Verify Sharpe ratio calculations for standard returns."""
    # std deviation is zero
    assert sharpe_ratio(np.zeros(10)) == 0.0
    # Positive returns
    returns = np.array([0.01, 0.02, 0.015, -0.005, 0.01])
    sr = sharpe_ratio(returns, risk_free_rate=0.04)
    assert isinstance(sr, float)
    assert sr > 0


def test_sortino_ratio():
    """Verify Sortino ratio calculations and tolerance fixes."""
    # std deviation of downside returns is zero
    assert sortino_ratio(np.zeros(10)) == 0.0
    
    returns = np.array([0.01, 0.02, -0.01, -0.02, 0.015])
    sor = sortino_ratio(returns, risk_free_rate=0.04)
    assert isinstance(sor, float)
    assert sor != 0.0  # should produce a non-zero ratio with mixed returns


def test_max_drawdown():
    """Verify max drawdown returns correct negative percentage."""
    assert max_drawdown([]) == 0.0
    equity = np.array([100.0, 105.0, 95.0, 110.0, 88.0, 115.0])
    # Peak is 110.0, drop to 88.0 is 22.0. Drawdown is -22/110 = -20%
    md = max_drawdown(equity)
    assert md == pytest.approx(-0.20)


def test_calmar_ratio():
    """Verify Calmar ratio calculation."""
    assert calmar_ratio(0.10, 0.0) == 0.0
    assert calmar_ratio(0.10, -0.20) == 0.50


def test_win_rate_and_profit_factor():
    """Verify win rate and profit factor calculation."""
    trades = [
        {"pnl": 100.0},
        {"pnl": -50.0},
        {"pnl": 200.0},
        {"pnl": -100.0},
    ]
    # 2 winners out of 4
    assert win_rate(trades) == 0.50
    # Gross profit = 300, gross loss = 150. Profit factor = 2.0
    assert profit_factor(trades) == 2.0


def test_profit_factor_no_losses():
    """Verify profit factor maps division by zero to fallback bound."""
    trades = [{"pnl": 100.0}]
    # Gross profit = 100, gross loss = 0. Profit factor should be inf, which maps to 999.9999 in compute_all_metrics
    assert profit_factor(trades) == float("inf")


def test_avg_holding_period():
    """Verify average holding period calculations from date strings."""
    trades = [
        {"entry_date": "2023-01-01", "exit_date": "2023-01-05"},  # 4 days
        {"entry_date": "2023-01-10", "exit_date": "2023-01-16"},  # 6 days
    ]
    assert avg_holding_period(trades) == 5.0


def test_compute_all_metrics():
    """Verify compute_all_metrics compiles PerformanceMetrics correctly."""
    equity = [100.0, 101.0, 102.0, 101.5, 103.0]
    trades = [{"entry_date": "2023-01-01", "exit_date": "2023-01-02", "pnl": 150.0}]
    
    metrics = compute_all_metrics(equity, trades)
    assert metrics.total_return == 0.03
    assert metrics.total_trades == 1
    assert metrics.win_rate == 1.0
    assert metrics.profit_factor == 999.9999
