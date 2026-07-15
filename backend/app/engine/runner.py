# backend/app/engine/runner.py
"""Backtrader cerebro setup and execution runner."""

import backtrader as bt
import pandas as pd
from datetime import datetime
from typing import Any

from app.engine.strategy_sandbox import run_cerebro_with_timeout


def run_backtest(
    strategy_class: type,
    ohlcv_data: pd.DataFrame | dict[str, pd.DataFrame],
    config: dict[str, Any],
    ticker_weights: dict[str, float] = None,
) -> dict[str, Any]:
    """Run a backtest using Backtrader and return structured results.

    Args:
        strategy_class: A bt.Strategy subclass to backtest.
        ohlcv_data: Single DataFrame or dict of {ticker: DataFrame} with columns [date, open, high, low, close, volume].
        config: Dict with initial_capital, commission, slippage.
        ticker_weights: Dict of {ticker: weight_pct} for portfolio sizing.

    Returns:
        Dict with equity_curve, trades, and analyzer_results.
    """
    initial_capital = config.get("initial_capital", 100000.0)
    commission = config.get("commission", 0.001)
    slippage = config.get("slippage", 0.0005)

    if isinstance(ohlcv_data, dict):
        ohlcv_dfs = ohlcv_data
    else:
        ohlcv_dfs = {"DEFAULT": ohlcv_data}

    # Create Cerebro engine
    cerebro = bt.Cerebro(tradehistory=True)

    # Configure broker
    cerebro.broker.setcash(initial_capital)
    cerebro.broker.setcommission(commission=commission)
    if slippage > 0:
        cerebro.broker.set_slippage_perc(slippage)

    # Prepare and add data feeds
    for name, ohlcv_df in ohlcv_dfs.items():
        df = ohlcv_df.copy()
        df["date"] = pd.to_datetime(df["date"])
        df = df.set_index("date")
        df = df.sort_index()
        df.columns = [c.lower() for c in df.columns]

        data_feed = bt.feeds.PandasData(dataname=df)
        cerebro.adddata(data_feed, name=name)

    # Determine normalised weights for custom position sizing
    tickers = list(ohlcv_dfs.keys())
    if ticker_weights:
        total_w = sum(ticker_weights.values())
        if total_w > 0:
            weights = {k.upper(): v / total_w for k, v in ticker_weights.items()}
        else:
            weights = {k: 1.0 / len(tickers) for k in tickers}
    else:
        weights = {k: 1.0 / len(tickers) for k in tickers}

    # Apply position sizing logic at the engine execution layer
    strategy_class._qbt_allocation_pct = config.get("allocation_pct", 100.0)
    strategy_class._qbt_weights = weights

    if not getattr(strategy_class.buy, "_is_qbt_patched", False):
        original_buy = strategy_class.buy

        def custom_buy(self, *args, **kwargs):
            # Identify which data feed is being traded
            data = kwargs.get('data')
            if data is None:
                if args and isinstance(args[0], bt.DataBase):
                    data = args[0]
                else:
                    data = self.data
            pos_size = self.getposition(data).size

            # 1. Single-position mode rules (per asset):
            if pos_size > 0:
                # Long position active, block additional buys (no scaling in)
                return None
            elif pos_size < 0:
                # Short position active, allow buy to cover/close
                return original_buy(self, *args, **kwargs)

            # 2. Calculate the order size using the selected allocation percentage
            # of currently available cash scaled by asset weight.
            cash = self.broker.getcash()
            price = data.close[0]

            if price <= 0:
                return None

            alloc_pct = getattr(self, "_qbt_allocation_pct", 100.0)
            allocation = alloc_pct / 100.0

            weights = getattr(self, "_qbt_weights", {})
            asset_weight = weights.get(data._name, 1.0)

            position_value = cash * allocation * asset_weight
            size = int(position_value // price)

            # 3. Only place a buy order if size > 0.
            if size > 0:
                kwargs['size'] = size
                return original_buy(self, *args, **kwargs)
            return None

        custom_buy._is_qbt_patched = True
        strategy_class.buy = custom_buy

    # Add strategy
    cerebro.addstrategy(strategy_class)

    # Add analyzers
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name="trade_analyzer")
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name="sharpe", riskfreerate=0.04/252)
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name="drawdown")
    cerebro.addanalyzer(bt.analyzers.Returns, _name="returns")

    # Add observer for tracking portfolio value
    cerebro.addobserver(bt.observers.Value)

    # Run the backtest with a hard timeout (30s)
    results = run_cerebro_with_timeout(cerebro, timeout=30.0)
    strategy_result = results[0]

    # Extract equity curve from the broker value observer
    equity_curve = _extract_equity_curve(strategy_result, ohlcv_dfs)

    # Extract trades
    trades = _extract_trades(strategy_result)

    # Extract analyzer results
    analyzer_results = _extract_analyzer_results(strategy_result)

    return {
        "equity_curve": equity_curve,
        "trades": trades,
        "analyzer_results": analyzer_results,
    }


def _extract_equity_curve(
    strategy: bt.Strategy, ohlcv_dfs: dict[str, pd.DataFrame]
) -> list[dict[str, Any]]:
    """Extract portfolio value series from the strategy's observers.

    Args:
        strategy: Completed Backtrader strategy instance.
        ohlcv_dfs: Original OHLCV dict for date reference.

    Returns:
        List of {date, value} dicts.
    """
    equity_curve = []
    
    # Gather all unique sorted dates across all data feeds
    all_dates = set()
    for df in ohlcv_dfs.values():
        all_dates.update(df["date"].tolist())
    dates = sorted(list(all_dates))

    # Get portfolio values from the value observer
    try:
        values = strategy.observers.value.lines.value.array
        for i, val in enumerate(values):
            if i < len(dates) and val is not None and val != 0:
                dt = dates[i]
                if hasattr(dt, "strftime"):
                    date_str = dt.strftime("%Y-%m-%d")
                else:
                    date_str = str(dt)[:10]
                equity_curve.append({"date": date_str, "value": float(val)})
    except (AttributeError, IndexError):
        # Fallback: use broker value at end
        fallback_date = "unknown"
        if dates:
            dt = dates[-1]
            fallback_date = dt.strftime("%Y-%m-%d") if hasattr(dt, "strftime") else str(dt)[:10]
        equity_curve.append({
            "date": fallback_date,
            "value": float(strategy.broker.getvalue()),
        })

    return equity_curve


def _extract_trades(strategy: bt.Strategy) -> list[dict[str, Any]]:
    """Extract completed trade records from the strategy.

    Args:
        strategy: Completed Backtrader strategy instance.

    Returns:
        List of trade record dicts.
    """
    trades = []
    analyzer = strategy.analyzers.trade_analyzer

    try:
        analysis = analyzer.get_analysis()
    except Exception:
        return trades

    # Extract from the strategy's trade history
    for trade in strategy._trades.values():
        for t_list in trade.values():
            for t in t_list:
                if t.isclosed:
                    entry_dt = bt.num2date(t.dtopen)
                    exit_dt = bt.num2date(t.dtclose)
                    ticker = t.data._name if hasattr(t, "data") and hasattr(t.data, "_name") else "unknown"
                    
                    # Extract size and exit price from history if available
                    if hasattr(t, 'history') and t.history:
                        try:
                            # First history update is the entry
                            entry_update = t.history[0]
                            size = abs(entry_update.status.size)
                            
                            # Average entry price is t.price
                            entry_price = t.price
                            
                            # Last history update is the exit
                            exit_update = t.history[-1]
                            exit_price = exit_update.event.price
                            pnl = t.pnlcomm
                            pnl_pct = (pnl / (size * entry_price)) * 100 if (size != 0 and entry_price != 0) else 0.0
                        except Exception:
                            # Fallback if history extraction fails
                            size = 0.0
                            entry_price = t.price
                            exit_price = entry_price
                            pnl = t.pnlcomm
                            pnl_pct = 0.0
                    else:
                        size = 0.0
                        entry_price = t.price
                        exit_price = entry_price
                        pnl = t.pnlcomm
                        pnl_pct = 0.0

                    trades.append({
                        "entry_date": entry_dt.strftime("%Y-%m-%d"),
                        "exit_date": exit_dt.strftime("%Y-%m-%d"),
                        "size": float(size),
                        "entry_price": round(float(entry_price), 4),
                        "exit_price": round(float(exit_price), 4),
                        "pnl": round(float(pnl), 2),
                        "pnl_pct": round(float(pnl_pct), 4),
                        "ticker": ticker,
                    })

    return trades


def _extract_analyzer_results(strategy: bt.Strategy) -> dict[str, Any]:
    """Extract all analyzer results into a clean dict.

    Args:
        strategy: Completed Backtrader strategy instance.

    Returns:
        Dict of analyzer results.
    """
    results = {}

    # Sharpe Ratio
    try:
        sharpe = strategy.analyzers.sharpe.get_analysis()
        results["sharpe_ratio"] = sharpe.get("sharperatio", 0.0)
    except Exception:
        results["sharpe_ratio"] = 0.0

    # Drawdown
    try:
        dd = strategy.analyzers.drawdown.get_analysis()
        results["max_drawdown"] = dd.get("max", {}).get("drawdown", 0.0)
        results["max_drawdown_len"] = dd.get("max", {}).get("len", 0)
    except Exception:
        results["max_drawdown"] = 0.0

    # Returns
    try:
        ret = strategy.analyzers.returns.get_analysis()
        results["total_return"] = ret.get("rtot", 0.0)
        results["avg_return"] = ret.get("ravg", 0.0)
    except Exception:
        results["total_return"] = 0.0

    # Trade Analyzer
    try:
        ta = strategy.analyzers.trade_analyzer.get_analysis()
        results["total_trades"] = ta.get("total", {}).get("total", 0)
        results["won_trades"] = ta.get("won", {}).get("total", 0)
        results["lost_trades"] = ta.get("lost", {}).get("total", 0)
    except Exception:
        results["total_trades"] = 0

    return results
