# backend/app/engine/strategies/bollinger_bands.py
"""Bollinger Bands strategy — buy below lower band, sell above upper band."""

import backtrader as bt
from app.engine.strategies.base import BaseStrategy


class BollingerBandsStrategy(BaseStrategy):
    """Bollinger Bands mean reversion strategy."""
    params = dict(period=20, devfactor=2.0)

    def __init__(self):
        self.bband = bt.ind.BollingerBands(period=self.p.period, devfactor=self.p.devfactor)

    def next(self):
        if not self.position:
            if self.data.close[0] < self.bband.lines.bot[0]:
                self.buy()
        else:
            if self.data.close[0] > self.bband.lines.top[0]:
                self.close()


TEMPLATE_CODE = '''class UserStrategy(bt.Strategy):
    params = dict(period=20, devfactor=2.0)

    def __init__(self):
        self.bband = bt.ind.BollingerBands(period=self.p.period, devfactor=self.p.devfactor)

    def next(self):
        if not self.position:
            if self.data.close[0] < self.bband.lines.bot[0]:
                self.buy()
        else:
            if self.data.close[0] > self.bband.lines.top[0]:
                self.close()
'''
