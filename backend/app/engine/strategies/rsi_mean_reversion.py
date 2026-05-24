# backend/app/engine/strategies/rsi_mean_reversion.py
"""RSI Mean Reversion strategy — buy when RSI < 30, sell when RSI > 70."""

import backtrader as bt
from app.engine.strategies.base import BaseStrategy


class RSIMeanReversionStrategy(BaseStrategy):
    """RSI-based mean reversion strategy."""
    params = dict(rsi_period=14, oversold=30, overbought=70)

    def __init__(self):
        self.rsi = bt.ind.RSI(period=self.p.rsi_period)

    def next(self):
        if not self.position:
            if self.rsi < self.p.oversold:
                self.buy()
        else:
            if self.rsi > self.p.overbought:
                self.close()


TEMPLATE_CODE = '''class UserStrategy(bt.Strategy):
    params = dict(rsi_period=14, oversold=30, overbought=70)

    def __init__(self):
        self.rsi = bt.ind.RSI(period=self.p.rsi_period)

    def next(self):
        if not self.position:
            if self.rsi < self.p.oversold:
                self.buy()
        else:
            if self.rsi > self.p.overbought:
                self.close()
'''
