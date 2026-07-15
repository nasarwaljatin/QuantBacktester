# backend/app/engine/strategies/ema_crossover.py
"""EMA Crossover strategy — buy when fast EMA crosses above slow EMA."""

import backtrader as bt
from app.engine.strategies.base import BaseStrategy


class EMACrossoverStrategy(BaseStrategy):
    """Exponential Moving Average crossover strategy."""
    params = dict(fast=3, slow=30)

    def __init__(self):
        self.fast_ma = bt.ind.EMA(period=self.p.fast)
        self.slow_ma = bt.ind.EMA(period=self.p.slow)
        self.crossover = bt.ind.CrossOver(self.fast_ma, self.slow_ma)

    def next(self):
        if not self.position:
            if self.crossover > 0:
                self.buy()
        elif self.crossover < 0:
            self.close()


TEMPLATE_CODE = '''class UserStrategy(bt.Strategy):
    params = dict(fast=3, slow=30)

    def __init__(self):
        self.fast_ma = bt.ind.EMA(period=self.p.fast)
        self.slow_ma = bt.ind.EMA(period=self.p.slow)
        self.crossover = bt.ind.CrossOver(self.fast_ma, self.slow_ma)

    def next(self):
        if not self.position:
            if self.crossover > 0:
                self.buy()
        elif self.crossover < 0:
            self.close()
'''
