# backend/tests/test_sizers.py
"""Unit tests for pluggable position sizing models in Backtrader."""

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


class MultiTradeStrategy(bt.Strategy):
    """Strategy that makes multiple trades to test trailing Kelly metrics."""
    def next(self):
        # Trade 1 (win)
        if len(self) == 1:
            self.buy()
        elif len(self) == 2:
            self.close()
        
        # Trade 2 (win)
        elif len(self) == 3:
            self.buy()
        elif len(self) == 4:
            self.close()

        # Trade 3 (win)
        elif len(self) == 5:
            self.buy()
        elif len(self) == 6:
            self.close()


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


def test_fixed_fractional_sizer():
    """Verify Fixed Fractional sizing risks a fixed percentage of total equity."""
    # Price is constant $100.
    # Capital = $100k.
    # Risk % = 2.0% -> Risk Value = $2,000.
    # Target size = $2,000 // 100 = 20 shares.
    prices = [100.0, 100.0, 100.0, 100.0]
    df = create_ohlcv_data(prices)

    config = {
        "initial_capital": 100000.0,
        "commission": 0.0,
        "slippage": 0.0,
        "allocation_pct": 100.0,
        "sizing_model": "fixed_fractional",
        "sizing_params": {
            "risk_pct": 2.0
        }
    }

    result = run_backtest(SingleTradeStrategy, df, config)
    trades = result["trades"]
    assert len(trades) == 1
    assert trades[0]["size"] == 20


def test_volatility_targeted_sizer():
    """Verify Volatility-Targeted sizing scales position inversely to ATR."""
    # Prices list with a specific ATR.
    # Let's say:
    # Day 1 close = 100.
    # Since we want ATR lookback, we need enough bars.
    # Let's provide 20 bars of constant price $100, then one bar with high volatility to check.
    # To keep it simple, we can test fallback to default 2% price if lookback ATR is too small,
    # or we can check with a stable ATR.
    # Let's use constant prices.
    # With period = 5, prices = [100] * 10.
    # Since prices are constant, TR = 0.
    # Fallback to 2% of price: 2% of $100 = $2.0.
    # Target Risk = 1.0% -> Risk Value = $1,000.
    # Size = Risk Value // ATR = 1,000 // 2.0 = 500 shares.
    prices = [100.0] * 10
    df = create_ohlcv_data(prices)

    config = {
        "initial_capital": 100000.0,
        "commission": 0.0,
        "slippage": 0.0,
        "allocation_pct": 100.0,
        "sizing_model": "volatility_targeted",
        "sizing_params": {
            "target_risk_pct": 1.0,
            "atr_period": 5
        }
    }

    result = run_backtest(SingleTradeStrategy, df, config)
    trades = result["trades"]
    assert len(trades) == 1
    assert trades[0]["size"] == 500


def test_kelly_criterion_sizer_fallback():
    """Verify Kelly Criterion uses fallback default parameters when no trades have closed."""
    # Capital = $100k.
    # Fallback win rate = 0.60, win-loss = 2.0.
    # Kelly % = 0.60 - (1 - 0.60) / 2.0 = 0.60 - 0.20 = 0.40.
    # Multiplier = 0.5 (Half Kelly) -> 0.20 fraction.
    # Cap = 0.15 (Max fraction 15%) -> Max allocation = 15% of $100k = $15,000.
    # Price = 100.
    # Target size = $15,000 // 100 = 150 shares.
    prices = [100.0, 100.0, 100.0, 100.0]
    df = create_ohlcv_data(prices)

    config = {
        "initial_capital": 100000.0,
        "commission": 0.0,
        "slippage": 0.0,
        "allocation_pct": 100.0,
        "sizing_model": "kelly",
        "sizing_params": {
            "kelly_multiplier": 0.5,
            "max_fraction": 0.15,
            "default_win_rate": 0.60,
            "default_win_loss": 2.0
        }
    }

    result = run_backtest(SingleTradeStrategy, df, config)
    trades = result["trades"]
    assert len(trades) == 1
    assert trades[0]["size"] == 150


def test_kelly_criterion_sizer_trailing():
    """Verify Kelly Criterion adjusts sizing dynamically based on completed trades."""
    # We run MultiTradeStrategy.
    # Trade 1: Buy Day 1 at 100, close Day 2 at 110 (+10% win).
    # Trade 2: Buy Day 3 at 110, close Day 4 at 120 (+9% win).
    # Since first 2 trades are wins, win rate is 1.0 (100%).
    # Win-loss ratio uses fallback 1.5 since there are no losses.
    # Kelly % = 1.0 - 0 = 1.0.
    # Multiplier = 0.5 -> 0.50 fraction.
    # Cap = 0.25 -> 25% of Equity on Trade 3.
    # Equity on Day 5 is approximately $100k + $10k + $9k = $119k.
    # Max allocation = 25% of 119k = $29,750.
    # Price on Day 5 is 120.
    # Size = 29,750 // 120 = 247 shares.
    prices = [100.0, 110.0, 120.0, 130.0, 140.0, 150.0, 160.0]
    df = create_ohlcv_data(prices)

    config = {
        "initial_capital": 100000.0,
        "commission": 0.0,
        "slippage": 0.0,
        "allocation_pct": 100.0,
        "sizing_model": "kelly",
        "sizing_params": {
            "kelly_multiplier": 0.5,
            "max_fraction": 0.25,
            "default_win_rate": 0.50,
            "default_win_loss": 1.5
        }
    }

    result = run_backtest(MultiTradeStrategy, df, config)
    trades = result["trades"]
    
    # We should have 3 trades executed
    assert len(trades) == 3
    # Trade 1 size: 100,000 * 0.08333 // 100 = 83.
    # Trade 2 size: 100,830 * 0.25 // 120 = 210.
    # Trade 3 size: 102,930 * 0.25 // 140 = 183.
    assert trades[2]["size"] == 183
