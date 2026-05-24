# backend/app/models/ohlcv.py
"""OHLCVCache SQLAlchemy model for caching historical price data."""

from datetime import date, datetime
from sqlalchemy import String, Float, BigInteger, Date, DateTime, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class OHLCVCache(Base):
    """Cached OHLCV (Open-High-Low-Close-Volume) data from yfinance.

    Keyed on (ticker, date) to allow efficient lookups and upserts.
    """

    __tablename__ = "ohlcv_cache"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    ticker: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    open: Mapped[float] = mapped_column(Float, nullable=False)
    high: Mapped[float] = mapped_column(Float, nullable=False)
    low: Mapped[float] = mapped_column(Float, nullable=False)
    close: Mapped[float] = mapped_column(Float, nullable=False)
    volume: Mapped[int] = mapped_column(BigInteger, nullable=False)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )

    __table_args__ = (
        UniqueConstraint("ticker", "date", name="uq_ticker_date"),
    )

    def __repr__(self) -> str:
        return f"<OHLCVCache(ticker={self.ticker}, date={self.date}, close={self.close})>"
