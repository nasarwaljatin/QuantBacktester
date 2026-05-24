# backend/app/engine/strategies/macd.py
"""MACD strategy — buy when MACD crosses above signal, sell when below."""

import backtrader as bt
from app.engine.strategies.base import BaseStrategy


class MACDStrategy(BaseStrategy):
    """MACD crossover strategy."""
    params = dict(fast=12, slow=26, signal=9)

    def __init__(self):
        self.macd = bt.ind.MACD(
            period_me1=self.p.fast,
            period_me2=self.p.slow,
            period_signal=self.p.signal,
        )
        self.crossover = bt.ind.CrossOver(self.macd.macd, self.macd.signal)

    def next(self):
        if not self.position:
            if self.crossover > 0:
                self.buy()
        elif self.crossover < 0:
            self.close()


TEMPLATE_CODE = '''class UserStrategy(bt.Strategy):
    params = dict(fast=12, slow=26, signal=9)

    def __init__(self):
        self.macd = bt.ind.MACD(
            period_me1=self.p.fast,
            period_me2=self.p.slow,
            period_signal=self.p.signal,
        )
        self.crossover = bt.ind.CrossOver(self.macd.macd, self.macd.signal)

    def next(self):
        if not self.position:
            if self.crossover > 0:
                self.buy()
        elif self.crossover < 0:
            self.close()
'''
