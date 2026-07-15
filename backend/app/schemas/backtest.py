# backend/app/schemas/backtest.py
"""Pydantic models for backtest request/response validation."""

from datetime import date
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, model_validator
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
    ticker: Optional[str] = Field(
        default=None,
        max_length=20,
        description="Stock ticker symbol (e.g. AAPL, RELIANCE.NS) - deprecated, use tickers instead",
    )
    tickers: Optional[List[str]] = Field(
        default=None,
        description="List of stock ticker symbols for portfolio backtesting",
    )
    ticker_weights: Optional[Dict[str, float]] = Field(
        default=None,
        description="Target allocations/weights per ticker (must sum to 100 or be proportions)",
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

    @model_validator(mode="after")
    def validate_tickers(self) -> "BacktestRequest":
        if not self.ticker and not self.tickers:
            raise ValueError("Either 'ticker' or 'tickers' must be specified.")
        if not self.tickers and self.ticker:
            self.tickers = [self.ticker]
        if self.tickers:
            self.tickers = [t.upper() for t in self.tickers]
            # Set default single ticker for backward compatibility in DB if not set
            if not self.ticker:
                self.ticker = self.tickers[0]
        if self.ticker_weights:
            self.ticker_weights = {k.upper(): v for k, v in self.ticker_weights.items()}
            for t in self.ticker_weights:
                if t not in self.tickers:
                    raise ValueError(f"Weight specified for ticker '{t}' not in tickers list.")
        return self


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
    ticker: Optional[str] = None


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
    tickers: Optional[List[str]] = None
    ticker_weights: Optional[Dict[str, float]] = None
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
