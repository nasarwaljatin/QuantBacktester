# backend/app/services/metrics_service.py
"""Service for computing comprehensive performance metrics from backtest results."""

import numpy as np
from datetime import datetime
from app.schemas.metrics import PerformanceMetrics


def sharpe_ratio(returns: np.ndarray, risk_free_rate: float = 0.04) -> float:
    """Calculate the annualized Sharpe ratio."""
    if len(returns) < 2 or np.std(returns) < 1e-9:
        return 0.0
    daily_rf = risk_free_rate / 252
    excess_returns = returns - daily_rf
    return float(np.mean(excess_returns) / np.std(excess_returns) * np.sqrt(252))


def sortino_ratio(returns: np.ndarray, risk_free_rate: float = 0.04) -> float:
    """Calculate the annualized Sortino ratio (downside deviation only)."""
    if len(returns) < 2:
        return 0.0
    daily_rf = risk_free_rate / 252
    excess_returns = returns - daily_rf
    downside_returns = excess_returns[excess_returns < 0]
    if len(downside_returns) == 0 or np.std(downside_returns) < 1e-9:
        return 0.0
    return float(np.mean(excess_returns) / np.std(downside_returns) * np.sqrt(252))


def max_drawdown(equity_curve: np.ndarray) -> float:
    """Calculate maximum peak-to-trough drawdown as a negative percentage."""
    if len(equity_curve) < 2:
        return 0.0
    peak = np.maximum.accumulate(equity_curve)
    drawdowns = (equity_curve - peak) / peak
    return float(np.min(drawdowns))


def calmar_ratio(annual_return: float, max_dd: float) -> float:
    """Calculate Calmar ratio (annualized return / |max drawdown|)."""
    if max_dd == 0:
        return 0.0
    return float(annual_return / abs(max_dd))


def win_rate(trades: list[dict]) -> float:
    """Calculate percentage of profitable trades."""
    if not trades:
        return 0.0
    winners = sum(1 for t in trades if t.get("pnl", 0) > 0)
    return float(winners / len(trades))


def profit_factor(trades: list[dict]) -> float:
    """Calculate gross profit / gross loss."""
    if not trades:
        return 0.0
    gross_profit = sum(t["pnl"] for t in trades if t.get("pnl", 0) > 0)
    gross_loss = abs(sum(t["pnl"] for t in trades if t.get("pnl", 0) < 0))
    if gross_loss == 0:
        return float("inf") if gross_profit > 0 else 0.0
    return float(gross_profit / gross_loss)


def avg_holding_period(trades: list[dict]) -> float:
    """Calculate average holding period in days."""
    if not trades:
        return 0.0
    periods = []
    for t in trades:
        try:
            entry = datetime.strptime(t["entry_date"], "%Y-%m-%d")
            exit_dt = datetime.strptime(t["exit_date"], "%Y-%m-%d")
            periods.append((exit_dt - entry).days)
        except (ValueError, KeyError):
            continue
    return float(np.mean(periods)) if periods else 0.0


def total_return(equity_curve: np.ndarray) -> float:
    """Calculate total portfolio return as a decimal."""
    if len(equity_curve) < 2:
        return 0.0
    return float((equity_curve[-1] - equity_curve[0]) / equity_curve[0])


def annualized_return(equity_curve: np.ndarray, periods_per_year: int = 252) -> float:
    """Calculate annualized return."""
    if len(equity_curve) < 2:
        return 0.0
    total_ret = equity_curve[-1] / equity_curve[0]
    n_periods = len(equity_curve) - 1
    if n_periods == 0 or total_ret <= 0:
        return 0.0
    years = n_periods / periods_per_year
    return float(total_ret ** (1 / years) - 1) if years > 0 else 0.0


def compute_all_metrics(
    equity_curve: list[float], trades: list[dict], risk_free_rate: float = 0.04
) -> PerformanceMetrics:
    """Compute all performance metrics from equity curve and trades."""
    eq = np.array(equity_curve, dtype=float)
    daily_returns = np.diff(eq) / eq[:-1] if len(eq) > 1 else np.array([0.0])
    tot_ret = total_return(eq)
    ann_ret = annualized_return(eq)
    max_dd = max_drawdown(eq)
    pf = profit_factor(trades)
    if pf == float("inf"):
        pf = 999.9999

    return PerformanceMetrics(
        total_return=round(tot_ret, 4),
        annualized_return=round(ann_ret, 4),
        sharpe_ratio=round(sharpe_ratio(daily_returns, risk_free_rate), 4),
        sortino_ratio=round(sortino_ratio(daily_returns, risk_free_rate), 4),
        max_drawdown=round(max_dd, 4),
        calmar_ratio=round(calmar_ratio(ann_ret, max_dd), 4),
        win_rate=round(win_rate(trades), 4),
        profit_factor=round(pf, 4),
        total_trades=len(trades),
        avg_holding_period=round(avg_holding_period(trades), 4),
    )
