# backend/tests/test_multi_asset.py
"""Unit tests for multi-asset / portfolio backtesting."""

import pytest
import backtrader as bt
import pandas as pd
from app.engine.runner import run_backtest


class MultiAssetTestStrategy(bt.Strategy):
    """Strategy designed to trade multiple assets independently."""
    def __init__(self):
        # Save reference to datas by name
        self.aapl = self.getdatabyname("AAPL")
        self.msft = self.getdatabyname("MSFT")

    def next(self):
        # On Day 1, buy both assets
        if len(self) == 1:
            self.buy(data=self.aapl)
            self.buy(data=self.msft)
        # On Day 3, close both assets
        elif len(self) == 3:
            self.close(data=self.aapl)
            self.close(data=self.msft)


class MultiAssetSinglePositionStrategy(bt.Strategy):
    """Verify single-position mode behaves per-asset."""
    def next(self):
        # Day 1: Buy AAPL
        if len(self) == 1:
            self.buy(data=self.getdatabyname("AAPL"))
        # Day 2: Try to buy AAPL again (should be blocked), buy MSFT (should be allowed)
        elif len(self) == 2:
            self.buy(data=self.getdatabyname("AAPL"))
            self.buy(data=self.getdatabyname("MSFT"))
        # Day 4: Close all
        elif len(self) == 4:
            self.close(data=self.getdatabyname("AAPL"))
            self.close(data=self.getdatabyname("MSFT"))


def create_ticker_data(prices, start_date="2023-01-01"):
    """Create OHLCV DataFrame from list of prices."""
    dates = pd.date_range(start_date, periods=len(prices))
    df = pd.DataFrame({
        "date": dates,
        "open": prices,
        "high": prices,
        "low": prices,
        "close": prices,
        "volume": [1000] * len(prices)
    })
    return df


def test_multi_asset_named_feeds():
    """Verify that multiple data feeds are correctly added and named."""
    aapl_prices = [100.0, 100.0, 100.0, 100.0]
    msft_prices = [200.0, 200.0, 200.0, 200.0]
    
    ohlcv_data = {
        "AAPL": create_ticker_data(aapl_prices),
        "MSFT": create_ticker_data(msft_prices)
    }

    config = {
        "initial_capital": 100000.0,
        "commission": 0.0,
        "slippage": 0.0,
        "allocation_pct": 100.0
    }

    # Run backtest
    result = run_backtest(MultiAssetTestStrategy, ohlcv_data, config)
    trades = result["trades"]

    # Verify trades occurred on both assets
    assert len(trades) >= 2
    aapl_trades = [t for t in trades if t["ticker"] == "AAPL"]
    msft_trades = [t for t in trades if t["ticker"] == "MSFT"]
    assert len(aapl_trades) == 1
    assert len(msft_trades) == 1


def test_multi_asset_equal_weight_sizing():
    """Verify default equal-weight sizing splits capital equally."""
    aapl_prices = [100.0, 100.0, 100.0, 100.0]
    msft_prices = [200.0, 200.0, 200.0, 200.0]
    
    ohlcv_data = {
        "AAPL": create_ticker_data(aapl_prices),
        "MSFT": create_ticker_data(msft_prices)
    }

    # Capital = 100k, Allocation = 100%
    # Default equal weights: 50% AAPL ($50k), 50% MSFT ($50k)
    # AAPL target size = 50,000 / 100 = 500 shares
    # MSFT target size = 50,000 / 200 = 250 shares
    config = {
        "initial_capital": 100000.0,
        "commission": 0.0,
        "slippage": 0.0,
        "allocation_pct": 100.0
    }

    result = run_backtest(MultiAssetTestStrategy, ohlcv_data, config)
    trades = result["trades"]

    aapl_trade = next(t for t in trades if t["ticker"] == "AAPL")
    msft_trade = next(t for t in trades if t["ticker"] == "MSFT")

    assert aapl_trade["size"] == 500
    assert msft_trade["size"] == 250


def test_multi_asset_custom_weight_sizing():
    """Verify that custom ticker weights scale order sizes correctly."""
    aapl_prices = [100.0, 100.0, 100.0, 100.0]
    msft_prices = [200.0, 200.0, 200.0, 200.0]
    
    ohlcv_data = {
        "AAPL": create_ticker_data(aapl_prices),
        "MSFT": create_ticker_data(msft_prices)
    }

    # Capital = 100k, Allocation = 80% (Total active capital = $80,000)
    # Weights: AAPL = 60%, MSFT = 40% (Sum = 100%)
    # AAPL allocation = $80,000 * 60% = $48,000 -> 48,000 / 100 = 480 shares
    # MSFT allocation = $80,000 * 40% = $32,000 -> 32,000 / 200 = 160 shares
    config = {
        "initial_capital": 100000.0,
        "commission": 0.0,
        "slippage": 0.0,
        "allocation_pct": 80.0
    }
    ticker_weights = {
        "AAPL": 60.0,
        "MSFT": 40.0
    }

    result = run_backtest(MultiAssetTestStrategy, ohlcv_data, config, ticker_weights=ticker_weights)
    trades = result["trades"]

    aapl_trade = next(t for t in trades if t["ticker"] == "AAPL")
    msft_trade = next(t for t in trades if t["ticker"] == "MSFT")

    assert aapl_trade["size"] == 480
    assert msft_trade["size"] == 160


def test_multi_asset_single_position_per_asset():
    """Verify that single-position mode locks buys independently per-asset."""
    aapl_prices = [100.0, 100.0, 100.0, 100.0, 100.0]
    msft_prices = [200.0, 200.0, 200.0, 200.0, 200.0]
    
    ohlcv_data = {
        "AAPL": create_ticker_data(aapl_prices),
        "MSFT": create_ticker_data(msft_prices)
    }

    config = {
        "initial_capital": 100000.0,
        "commission": 0.0,
        "slippage": 0.0,
        "allocation_pct": 50.0
    }

    # Run backtest
    result = run_backtest(MultiAssetSinglePositionStrategy, ohlcv_data, config)
    trades = result["trades"]

    # AAPL should have 1 trade (Day 2 buy was blocked because Day 1 position is active)
    aapl_trades = [t for t in trades if t["ticker"] == "AAPL"]
    assert len(aapl_trades) == 1

    # MSFT should have 1 trade (Day 2 buy was allowed because MSFT was flat)
    msft_trades = [t for t in trades if t["ticker"] == "MSFT"]
    assert len(msft_trades) == 1
