# backend/app/schemas/backtest.py
"""Pydantic models for backtest request/response validation."""

from datetime import date
from typing import Optional, List, Dict, Any, Literal
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
    sizing_model: str = Field(
        default="all_in",
        description="Position sizing model to use (all_in, fixed_fractional, volatility_targeted, kelly)",
    )
    sizing_params: Dict[str, Any] = Field(
        default_factory=dict,
        description="Parameters for the selected sizing model",
    )
    commission_type: str = Field(
        default="percent",
        description="Commission type: percent, per_share, tiered",
    )
    commission_value: float = Field(
        default=0.001,
        ge=0.0,
        description="Commission value (rate or per-share charge)",
    )
    commission_tier_limit: int = Field(
        default=1000,
        ge=0,
        description="Threshold of shares for tiered commission",
    )
    commission_tier_value: float = Field(
        default=0.003,
        ge=0.0,
        description="Commission rate for shares above tier threshold",
    )
    slippage_type: str = Field(
        default="percent",
        description="Slippage type: percent, points",
    )
    slippage_value: float = Field(
        default=0.0005,
        ge=0.0,
        description="Slippage value",
    )
    spread: float = Field(
        default=0.0,
        ge=0.0,
        description="Bid-ask spread in price points",
    )
    volume_limit_pct: Optional[float] = Field(
        default=None,
        ge=0.1,
        le=100.0,
        description="Volume limit percentage for partial fills",
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
    commission: float = 0.0


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
    sizing_model: Optional[str] = None
    sizing_params: Optional[Dict[str, Any]] = None
    commission_type: Optional[str] = None
    commission_value: Optional[float] = None
    commission_tier_limit: Optional[int] = None
    commission_tier_value: Optional[float] = None
    slippage_type: Optional[str] = None
    slippage_value: Optional[float] = None
    spread: Optional[float] = None
    volume_limit_pct: Optional[float] = None


class BacktestStatusResponse(BaseModel):
    """Lightweight status response while polling for results."""

    task_id: str
    status: str
    error: Optional[str] = None


# ---------------------------------------------------------------------------
# Phase 4: Parameter Sweep & Walk-Forward Optimization schemas
# ---------------------------------------------------------------------------

class SweepRequest(BaseModel):
    """Request body for submitting a parameter sweep."""

    strategy_code: str = Field(
        ...,
        min_length=10,
        description="Python source code defining a UserStrategy class extending bt.Strategy",
    )
    tickers: List[str] = Field(
        ...,
        min_length=1,
        description="List of stock ticker symbols",
    )
    ticker_weights: Optional[Dict[str, float]] = Field(
        default=None,
        description="Optional per-ticker weight allocations",
    )
    start_date: date = Field(..., description="Backtest start date (YYYY-MM-DD)")
    end_date: date = Field(..., description="Backtest end date (YYYY-MM-DD)")
    param_grid: Dict[str, List[Any]] = Field(
        ...,
        description="Parameter grid, e.g. {\"fast\": [3, 5, 10], \"slow\": [20, 30]}",
    )
    config: BacktestConfig = Field(
        default_factory=BacktestConfig,
        description="Base backtest configuration",
    )
    objective: str = Field(
        default="sharpe_ratio",
        description="Metric to maximize when selecting best parameters",
    )

    @model_validator(mode="after")
    def validate_dates_and_grid(self) -> "SweepRequest":
        if self.start_date >= self.end_date:
            raise ValueError("start_date must be before end_date")
        if not self.param_grid:
            raise ValueError("param_grid must not be empty")
        self.tickers = [t.upper() for t in self.tickers]
        return self


class WFARequest(BaseModel):
    """Request body for submitting a walk-forward analysis."""

    strategy_code: str = Field(
        ...,
        min_length=10,
        description="Python source code defining a UserStrategy class extending bt.Strategy",
    )
    tickers: List[str] = Field(
        ...,
        min_length=1,
        description="List of stock ticker symbols",
    )
    ticker_weights: Optional[Dict[str, float]] = Field(
        default=None,
        description="Optional per-ticker weight allocations",
    )
    start_date: date = Field(..., description="Backtest start date (YYYY-MM-DD)")
    end_date: date = Field(..., description="Backtest end date (YYYY-MM-DD)")
    param_grid: Dict[str, List[Any]] = Field(
        ...,
        description="Parameter grid, e.g. {\"fast\": [3, 5, 10], \"slow\": [20, 30]}",
    )
    config: BacktestConfig = Field(
        default_factory=BacktestConfig,
        description="Base backtest configuration",
    )
    in_sample_days: int = Field(
        default=365,
        ge=30,
        description="Length of in-sample (training) period in calendar days",
    )
    out_of_sample_days: int = Field(
        default=90,
        ge=7,
        description="Length of out-of-sample (testing) period in calendar days",
    )
    window_type: str = Field(
        default="rolling",
        description="Window type: 'rolling' (fixed IS length) or 'expanding' (IS grows from start)",
    )
    anchored: bool = Field(
        default=False,
        description="If True (rolling only), pin IS start to first fold's IS start so IS grows each fold",
    )
    max_combinations: int = Field(
        default=200,
        ge=1,
        le=5000,
        description="Hard cap on total backtest runs (n_folds x n_combinations)",
    )
    objective: str = Field(
        default="sharpe_ratio",
        description="Metric to maximize when selecting best parameters in-sample",
    )

    @model_validator(mode="after")
    def validate_dates_and_grid(self) -> "WFARequest":
        if self.start_date >= self.end_date:
            raise ValueError("start_date must be before end_date")
        if not self.param_grid:
            raise ValueError("param_grid must not be empty")
        self.tickers = [t.upper() for t in self.tickers]
        return self


class SweepResultItem(BaseModel):
    """Result of a single parameter combination in a sweep."""

    combo_index: int
    parameters: Dict[str, Any]
    metrics: Optional[Dict[str, Any]] = None
    equity_curve: Optional[List[EquityCurvePoint]] = None
    status: str
    error_message: Optional[str] = None


class WFAWindowResult(BaseModel):
    """Result of a single walk-forward window."""

    window_index: int
    in_sample_start: str
    in_sample_end: str
    out_of_sample_start: str
    out_of_sample_end: str
    optimized_params: Optional[Dict[str, Any]] = None
    in_sample_metrics: Optional[Dict[str, Any]] = None
    out_of_sample_metrics: Optional[Dict[str, Any]] = None
    efficiency_ratio: Optional[float] = Field(
        default=None,
        description="OOS objective / IS objective ratio; >= 0.7 is well-generalised, < 0.5 signals overfitting",
    )
    status: str


class SweepResponse(BaseModel):
    """Response for a parameter sweep task."""

    task_id: str
    status: str
    run_type: str = "sweep"
    progress: Optional[str] = None
    sweep_results: Optional[List[SweepResultItem]] = None
    best_params: Optional[Dict[str, Any]] = None
    total_combinations: Optional[int] = None
    objective: Optional[str] = None
    param_grid: Optional[Dict[str, List[Any]]] = None
    error: Optional[str] = None


class WFAResponse(BaseModel):
    """Response for a walk-forward analysis task."""

    task_id: str
    status: str
    run_type: str = "walk_forward"
    progress: Optional[str] = None
    wfa_windows: Optional[List[WFAWindowResult]] = None
    combined_oos_equity: Optional[List[EquityCurvePoint]] = None
    aggregate_oos_metrics: Optional[Dict[str, Any]] = None
    total_windows: Optional[int] = None
    in_sample_days: Optional[int] = None
    out_of_sample_days: Optional[int] = None
    window_type: Optional[str] = "rolling"
    anchored: Optional[bool] = False
    param_grid: Optional[Dict[str, List[Any]]] = None
    objective: Optional[str] = None
    efficiency_ratios: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description="Per-fold efficiency ratios (OOS/IS for the objective metric)",
    )
    aggregate_efficiency_ratio: Optional[float] = Field(
        default=None,
        description="Mean efficiency ratio across all folds; < 0.5 is an overfitting warning",
    )
    param_stability: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Coefficient of Variation per parameter across folds; high CV = unstable",
    )
    error: Optional[str] = None


class WFAEstimateRequest(BaseModel):
    """Request body for the pre-flight WFA run-count estimate endpoint.

    No strategy_code is required — this is purely arithmetic based on the
    date range, IS/OOS lengths, window type, and parameter grid size.
    """

    tickers: List[str] = Field(..., min_length=1)
    start_date: date
    end_date: date
    param_grid: Dict[str, List[Any]] = Field(
        ...,
        description="Parameter grid, e.g. {\"fast\": [3, 5, 10], \"slow\": [20, 30]}",
    )
    in_sample_days: int = Field(default=365, ge=1)
    out_of_sample_days: int = Field(default=90, ge=1)
    window_type: str = Field(default="rolling")
    anchored: bool = Field(default=False)
    max_combinations: int = Field(default=200, ge=1, le=5000)


class WFAEstimateResponse(BaseModel):
    """Response from the pre-flight WFA run-count estimate endpoint."""

    n_folds: int = Field(description="Number of walk-forward folds")
    n_combinations: int = Field(description="Number of parameter combinations per fold")
    total_runs: int = Field(description="Total backtest runs = n_folds x n_combinations")
    feasible: bool = Field(description="True if total_runs <= max_combinations")
    error: Optional[str] = Field(default=None, description="Human-readable error if config is invalid")
