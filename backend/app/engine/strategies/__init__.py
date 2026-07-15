# backend/app/engine/strategies/__init__.py
"""Built-in strategy templates package."""

from app.engine.strategies.base import BaseStrategy
from app.engine.strategies.sma_crossover import SMACrossoverStrategy, TEMPLATE_CODE as SMA_TEMPLATE
from app.engine.strategies.ema_crossover import EMACrossoverStrategy, TEMPLATE_CODE as EMA_TEMPLATE
from app.engine.strategies.rsi_mean_reversion import RSIMeanReversionStrategy, TEMPLATE_CODE as RSI_TEMPLATE
from app.engine.strategies.bollinger_bands import BollingerBandsStrategy, TEMPLATE_CODE as BB_TEMPLATE
from app.engine.strategies.macd import MACDStrategy, TEMPLATE_CODE as MACD_TEMPLATE

STRATEGY_TEMPLATES = {
    "ema_crossover": {"name": "3/30 EMA Crossover", "code": EMA_TEMPLATE},
    "sma_crossover": {"name": "SMA Crossover", "code": SMA_TEMPLATE},
    "rsi_mean_reversion": {"name": "RSI Mean Reversion", "code": RSI_TEMPLATE},
    "bollinger_bands": {"name": "Bollinger Bands", "code": BB_TEMPLATE},
    "macd": {"name": "MACD", "code": MACD_TEMPLATE},
}

__all__ = [
    "BaseStrategy", "SMACrossoverStrategy", "EMACrossoverStrategy", "RSIMeanReversionStrategy",
    "BollingerBandsStrategy", "MACDStrategy", "STRATEGY_TEMPLATES",
]
