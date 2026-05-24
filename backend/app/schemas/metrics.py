# backend/app/schemas/metrics.py
"""Pydantic model for performance metrics."""

from pydantic import BaseModel, Field


class PerformanceMetrics(BaseModel):
    """Comprehensive performance metrics for a backtest run.

    All percentage values are expressed as decimals (e.g. 0.15 = 15%).
    All values are rounded to 4 decimal places.
    """

    total_return: float = Field(description="Total portfolio return as a decimal")
    annualized_return: float = Field(description="Annualized return assuming 252 trading days")
    sharpe_ratio: float = Field(description="Annualized Sharpe ratio (risk-free rate = 4%)")
    sortino_ratio: float = Field(description="Annualized Sortino ratio (risk-free rate = 4%)")
    max_drawdown: float = Field(description="Maximum peak-to-trough drawdown as negative percentage")
    calmar_ratio: float = Field(description="Annualized return / |max drawdown|")
    win_rate: float = Field(description="Percentage of profitable trades")
    profit_factor: float = Field(description="Gross profit / gross loss")
    total_trades: int = Field(description="Total number of completed trades")
    avg_holding_period: float = Field(description="Average trade holding period in days")
