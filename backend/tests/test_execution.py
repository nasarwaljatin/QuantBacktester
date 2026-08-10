# backend/tests/test_execution.py
"""Unit tests for realistic execution modeling in Backtrader."""

import pytest
import backtrader as bt
import pandas as pd
from app.engine.runner import run_backtest


class SingleTradeStrategy(bt.Strategy):
    """Strategy that buys on Day 1 and closes on Day 3."""
    def next(self):
        if len(self) == 1:
            self.buy()
        elif len(self) == 3:
            self.close()


class SizedTradeStrategy(bt.Strategy):
    """Strategy that buys a fixed size of 1500 shares on Day 1 and closes when fully filled."""
    def next(self):
        if len(self) == 1:
            self.buy(size=1500)
        elif self.position.size == 1500:
            self.close()


def create_ohlcv_data(prices, volumes=None):
    """Create OHLCV DataFrame from lists of prices and optional volumes."""
    dates = pd.date_range("2023-01-01", periods=len(prices))
    df = pd.DataFrame({
        "date": dates,
        "open": prices,
        "high": [p * 1.2 for p in prices],
        "low": [p * 0.8 for p in prices],
        "close": prices,
        "volume": volumes if volumes is not None else [10000] * len(prices)
    })
    return df


def test_points_slippage():
    """Verify points-based slippage modifies execution prices correctly."""
    # Prices = constant 100.
    # Slippage value = 0.5 points.
    # Buy price should be 100.5.
    # Sell price should be 99.5.
    prices = [100.0, 100.0, 100.0, 100.0]
    df = create_ohlcv_data(prices)

    config = {
        "initial_capital": 100000.0,
        "commission_type": "percent",
        "commission_value": 0.0,
        "slippage_type": "points",
        "slippage_value": 0.5,
        "allocation_pct": 10.0,  # $10k -> 100 shares
    }

    result = run_backtest(SingleTradeStrategy, df, config)
    trades = result["trades"]
    assert len(trades) == 1
    assert trades[0]["entry_price"] == 100.5
    assert trades[0]["exit_price"] == 99.5


def test_percentage_slippage():
    """Verify percentage-based slippage scales with price."""
    # Prices: Entry day open = 100, Exit day open = 200.
    # Slippage rate = 1.0% (0.01).
    # Buy price: 100 * (1 + 0.01) = 101.0.
    # Sell price: 200 * (1 - 0.01) = 198.0.
    prices = [100.0, 100.0, 200.0, 200.0]
    df = create_ohlcv_data(prices)

    config = {
        "initial_capital": 100000.0,
        "commission_type": "percent",
        "commission_value": 0.0,
        "slippage_type": "percent",
        "slippage_value": 0.01,
        "allocation_pct": 10.0,
    }

    result = run_backtest(SingleTradeStrategy, df, config)
    trades = result["trades"]
    assert len(trades) == 1
    assert trades[0]["entry_price"] == 101.0
    assert trades[0]["exit_price"] == 198.0


def test_per_share_commission():
    """Verify per-share commission rates calculate commissions based on shares traded."""
    # Capital = 100k, Allocation = 10% -> $10,000 allocated.
    # Price = 100. Size = 100 shares.
    # Commission rate = $0.05 per share.
    # Commission on entry = 100 shares * $0.05 = $5.0.
    # Commission on exit = 100 shares * $0.05 = $5.0.
    # Total commission = $10.0.
    prices = [100.0, 100.0, 100.0, 100.0]
    df = create_ohlcv_data(prices)

    config = {
        "initial_capital": 100000.0,
        "commission_type": "per_share",
        "commission_value": 0.05,
        "slippage_value": 0.0,
        "allocation_pct": 10.0,
    }

    result = run_backtest(SingleTradeStrategy, df, config)
    trades = result["trades"]
    assert len(trades) == 1
    assert trades[0]["commission"] == 10.0


def test_tiered_commission():
    """Verify tiered commission breakpoint calculations."""
    # Buy 1500 shares.
    # Base rate = $0.01/share for first 1000 shares -> $10.0.
    # Tier rate = $0.005/share for remaining 500 shares -> $2.5.
    # Entry commission = $12.5.
    # Exit commission (1500 shares) = $12.5.
    # Total commission = $25.0.
    prices = [100.0, 100.0, 100.0, 100.0, 100.0]
    df = create_ohlcv_data(prices)

    config = {
        "initial_capital": 200000.0,
        "commission_type": "tiered",
        "commission_value": 0.01,
        "commission_tier_limit": 1000,
        "commission_tier_value": 0.005,
        "slippage_value": 0.0,
        "allocation_pct": 100.0,
    }

    result = run_backtest(SizedTradeStrategy, df, config)
    trades = result["trades"]
    assert len(trades) == 1
    assert trades[0]["commission"] == 25.0


def test_bid_ask_spread():
    """Verify bid-ask spread adjusts buy entry and sell exit execution prices."""
    # Prices = 100.
    # Spread = 0.10.
    # Half spread = 0.05.
    # Buy execution price: 100 + 0.05 = 100.05.
    # Sell execution price: 100 - 0.05 = 99.95.
    prices = [100.0, 100.0, 100.0, 100.0]
    df = create_ohlcv_data(prices)

    config = {
        "initial_capital": 100000.0,
        "commission_type": "percent",
        "commission_value": 0.0,
        "slippage_value": 0.0,
        "spread": 0.10,
        "allocation_pct": 10.0,
    }

    result = run_backtest(SingleTradeStrategy, df, config)
    trades = result["trades"]
    assert len(trades) == 1
    assert abs(trades[0]["entry_price"] - 100.05) < 1e-5
    assert abs(trades[0]["exit_price"] - 99.95) < 1e-5


def test_volume_limit_partial_fills():
    """Verify volume limit restricts single-bar fill size."""
    # Order size = 1500 shares.
    # Volume Day 2 (entry execution day) = 5000.
    # Volume Day 4 (exit execution day) = 5000.
    # Volume Limit = 10% -> Max fill size per bar = 500 shares.
    # Day 2: 500 shares filled (order remains active for 1000 shares).
    # Day 3: 500 shares filled (order remains active for 500 shares).
    # Day 4: 500 shares filled (order fully filled at 1500 shares).
    # Day 4 next(): submits close.
    # Day 5: 500 shares sold (position 1000).
    # Day 6: 500 shares sold (position 500).
    # Day 7: 500 shares sold (position 0) -> trade closed.
    prices = [100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0]
    volumes = [5000, 5000, 5000, 5000, 5000, 5000, 5000, 5000]
    df = create_ohlcv_data(prices, volumes)

    config = {
        "initial_capital": 200000.0,
        "commission_type": "percent",
        "commission_value": 0.0,
        "slippage_value": 0.0,
        "allocation_pct": 100.0,
        "volume_limit_pct": 10.0,
    }

    result = run_backtest(SizedTradeStrategy, df, config)
    trades = result["trades"]
    assert len(trades) == 1
    assert trades[0]["size"] == 500.0  # size of first partial fill
    assert trades[0]["entry_date"] == "2023-01-02"
    assert trades[0]["exit_date"] == "2023-01-07"
