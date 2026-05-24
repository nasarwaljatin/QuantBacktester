# backend/app/engine/strategies/base.py
"""Base strategy class for QuantBacktester built-in strategies."""

import backtrader as bt


class BaseStrategy(bt.Strategy):
    """Base class for all built-in strategies. Provides trade logging."""

    def log(self, txt: str) -> None:
        """Log a message with the current date."""
        dt = self.datas[0].datetime.date(0)
        print(f"[{dt.isoformat()}] {txt}")

    def notify_order(self, order: bt.Order) -> None:
        """Handle order notifications."""
        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(f"BUY @ {order.executed.price:.2f}, Size: {order.executed.size}")
            elif order.issell():
                self.log(f"SELL @ {order.executed.price:.2f}, Size: {order.executed.size}")

    def notify_trade(self, trade: bt.Trade) -> None:
        """Handle trade close notifications."""
        if trade.isclosed:
            self.log(f"TRADE PnL: Gross={trade.pnl:.2f}, Net={trade.pnlcomm:.2f}")
