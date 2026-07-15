# backend/tests/test_position_sizing.py
"""Unit tests for capital-based position sizing in Backtrader."""

import pytest
import backtrader as bt
import pandas as pd
import numpy as np
from app.engine.runner import run_backtest


class SimpleTradeStrategy(bt.Strategy):
    """Strategy that buys on Day 1 and closes on Day 2."""
    def next(self):
        if len(self) == 1:
            self.buy()
        elif len(self) == 2:
            self.close()


class CompoundingStrategy(bt.Strategy):
    """Strategy that buys on Day 1, closes on Day 3, and buys again on Day 4."""
    def next(self):
        if len(self) == 1:
            self.buy()
        elif len(self) == 3:
            self.close()
        elif len(self) == 4:
            self.buy()


def create_ohlcv_data(prices):
    """Create OHLCV DataFrame from list of prices."""
    dates = pd.date_range("2023-01-01", periods=len(prices))
    df = pd.DataFrame({
        "date": dates,
        "open": prices,
        "high": prices,
        "low": prices,
        "close": prices,
        "volume": [1000] * len(prices)
    })
    return df


def test_100_percent_allocation():
    """Verify that 100% allocation buys maximum possible shares."""
    prices = [200.0, 200.0, 200.0]
    df = create_ohlcv_data(prices)
    
    config = {
        "initial_capital": 100000.0,
        "commission": 0.0,
        "slippage": 0.0,
        "allocation_pct": 100.0
    }
    
    result = run_backtest(SimpleTradeStrategy, df, config)
    trades = result["trades"]
    assert len(trades) == 1
    # Cash (100k) * 100% / Close Price (200) = 500 shares
    assert trades[0]["size"] == 500.0


def test_50_percent_allocation():
    """Verify that 50% allocation buys half-sized positions."""
    prices = [200.0, 200.0, 200.0]
    df = create_ohlcv_data(prices)
    
    config = {
        "initial_capital": 100000.0,
        "commission": 0.0,
        "slippage": 0.0,
        "allocation_pct": 50.0
    }
    
    result = run_backtest(SimpleTradeStrategy, df, config)
    trades = result["trades"]
    assert len(trades) == 1
    # Cash (100k) * 50% / Close Price (200) = 250 shares
    assert trades[0]["size"] == 250.0


def test_10_percent_allocation():
    """Verify that 10% allocation buys smaller positions."""
    prices = [200.0, 200.0, 200.0]
    df = create_ohlcv_data(prices)
    
    config = {
        "initial_capital": 100000.0,
        "commission": 0.0,
        "slippage": 0.0,
        "allocation_pct": 10.0
    }
    
    result = run_backtest(SimpleTradeStrategy, df, config)
    trades = result["trades"]
    assert len(trades) == 1
    # Cash (100k) * 10% / Close Price (200) = 50 shares
    assert trades[0]["size"] == 50.0


def test_insufficient_cash():
    """Verify that insufficient cash results in no order being placed."""
    prices = [150000.0, 150000.0, 150000.0]
    df = create_ohlcv_data(prices)
    
    config = {
        "initial_capital": 100000.0,
        "commission": 0.0,
        "slippage": 0.0,
        "allocation_pct": 50.0
    }
    
    result = run_backtest(SimpleTradeStrategy, df, config)
    trades = result["trades"]
    # Available cash (100k) * 50% / Close Price (150k) = 0 shares (floor).
    # Since size is 0, no order should be placed.
    assert len(trades) == 0


def test_compounding_profitable_trade():
    """Verify that position sizing increases correctly after a profitable trade."""
    dates = pd.date_range("2023-01-01", periods=6)
    df = pd.DataFrame({
        "date": dates,
        "open":  [200.0, 200.0, 200.0, 240.0, 200.0, 200.0],
        "high":  [200.0, 200.0, 200.0, 240.0, 200.0, 200.0],
        "low":   [200.0, 200.0, 200.0, 240.0, 200.0, 200.0],
        "close": [200.0, 200.0, 200.0, 200.0, 200.0, 200.0],
        "volume": [1000] * 6
    })
    
    config = {
        "initial_capital": 100000.0,
        "commission": 0.0,
        "slippage": 0.0,
        "allocation_pct": 50.0
    }
    
    result = run_backtest(CompoundingStrategy, df, config)
    trades = result["trades"]
    
    # We expect 1 completed closed trade in this list (the first one)
    # and the second trade is opened but not closed (so it is not in result["trades"])
    # Let's inspect the first trade size (should be 250).
    assert len(trades) == 1
    assert trades[0]["size"] == 250.0
    # Entry price 200, exit price 240 -> PnL = (240 - 200) * 250 = +10,000.
    assert trades[0]["pnl"] == 10000.0
    
    # To check the second trade's size, since it was open and not closed,
    # we can run a version where we also close the second trade on Day 5.
    class DoubleTradeStrategy(bt.Strategy):
        def next(self):
            if len(self) == 1:
                self.buy()
            elif len(self) == 3:
                self.close()
            elif len(self) == 4:
                self.buy()
            elif len(self) == 5:
                self.close()

    result_double = run_backtest(DoubleTradeStrategy, df, config)
    trades_double = result_double["trades"]
    assert len(trades_double) == 2
    
    # First trade: 250 shares
    assert trades_double[0]["size"] == 250.0
    
    # Second trade: Sized using cash after profit (110k) * 50% / Close Price (200) = 275 shares
    assert trades_double[1]["size"] == 275.0


def test_compounding_losing_trade():
    """Verify that position sizing decreases correctly after a losing trade."""
    dates = pd.date_range("2023-01-01", periods=6)
    df = pd.DataFrame({
        "date": dates,
        "open":  [200.0, 200.0, 200.0, 160.0, 200.0, 200.0],
        "high":  [200.0, 200.0, 200.0, 160.0, 200.0, 200.0],
        "low":   [200.0, 200.0, 200.0, 160.0, 200.0, 200.0],
        "close": [200.0, 200.0, 200.0, 200.0, 200.0, 200.0],
        "volume": [1000] * 6
    })
    
    config = {
        "initial_capital": 100000.0,
        "commission": 0.0,
        "slippage": 0.0,
        "allocation_pct": 50.0
    }
    
    class DoubleTradeStrategy(bt.Strategy):
        def next(self):
            if len(self) == 1:
                self.buy()
            elif len(self) == 3:
                self.close()
            elif len(self) == 4:
                self.buy()
            elif len(self) == 5:
                self.close()

    result = run_backtest(DoubleTradeStrategy, df, config)
    trades = result["trades"]
    assert len(trades) == 2
    
    # First trade: 250 shares
    assert trades[0]["size"] == 250.0
    # Entry price 200, exit price 160 -> PnL = (160 - 200) * 250 = -10,000.
    assert trades[0]["pnl"] == -10000.0
    
    # Second trade: Sized using cash after loss (90k) * 50% / Close Price (200) = 225 shares
    assert trades[1]["size"] == 225.0
