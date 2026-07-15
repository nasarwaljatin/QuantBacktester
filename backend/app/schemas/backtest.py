# backend/app/schemas/backtest.py
"""Pydantic models for backtest request/response validation."""

from datetime import date
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from app.schemas.metrics import PerformanceMetrics


class BacktestConfig(BaseModel):
    """Configuration parameters for a backtest run."""

    initial_capital: float = Field(
        default=100000.0,
        ge=1000.0,
        le=100000000.0,
        description="Initial portfolio capital in USD",
    )
    commission: float = Field(
        default=0.001,
        ge=0.0,
        le=0.1,
        description="Commission rate per trade (e.g. 0.001 = 0.1%)",
    )
    slippage: float = Field(
        default=0.0005,
        ge=0.0,
        le=0.05,
        description="Slippage rate per trade (e.g. 0.0005 = 0.05%)",
    )
    allocation_pct: float = Field(
        default=100.0,
        ge=1.0,
        le=100.0,
        description="Capital allocation percentage (1 to 100)",
    )


class BacktestRequest(BaseModel):
    """Request body for submitting a new backtest."""

    strategy_code: str = Field(
        ...,
        min_length=10,
        description="Python source code defining a UserStrategy class extending bt.Strategy",
    )
    ticker: str = Field(
        ...,
        min_length=1,
        max_length=20,
        description="Stock ticker symbol (e.g. AAPL, RELIANCE.NS)",
    )
    start_date: date = Field(
        ...,
        description="Backtest start date (YYYY-MM-DD)",
    )
    end_date: date = Field(
        ...,
        description="Backtest end date (YYYY-MM-DD)",
    )
    config: BacktestConfig = Field(
        default_factory=BacktestConfig,
        description="Backtest configuration parameters",
    )


class EquityCurvePoint(BaseModel):
    """Single point on the equity curve."""

    date: str
    value: float


class TradeRecord(BaseModel):
    """Record of a single completed trade."""

    entry_date: str
    exit_date: str
    size: float
    entry_price: float
    exit_price: float
    pnl: float
    pnl_pct: float


class MonteCarloResult(BaseModel):
    """Results of a Monte Carlo simulation on trade returns."""

    paths: List[List[float]] = Field(
        description="50 sampled equity curve paths for chart rendering"
    )
    percentile_5: List[float] = Field(
        description="5th percentile equity curve (downside scenario)"
    )
    percentile_50: List[float] = Field(
        description="Median equity curve"
    )
    percentile_95: List[float] = Field(
        description="95th percentile equity curve (upside scenario)"
    )
    final_values: List[float] = Field(
        description="All 1000 final portfolio values for histogram"
    )
    prob_profit: float = Field(
        description="Percentage of simulations ending above initial capital"
    )


class BacktestResponse(BaseModel):
    """Full backtest result response."""

    task_id: str
    status: str
    ticker: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    equity_curve: Optional[List[EquityCurvePoint]] = None
    benchmark_curve: Optional[List[EquityCurvePoint]] = None
    trades: Optional[List[TradeRecord]] = None
    metrics: Optional[PerformanceMetrics] = None
    monte_carlo: Optional[MonteCarloResult] = None
    error: Optional[str] = None
    allocation_pct: Optional[float] = None
    position_sizing: Optional[str] = None


class BacktestStatusResponse(BaseModel):
    """Lightweight status response while polling for results."""

    task_id: str
    status: str
    error: Optional[str] = None
