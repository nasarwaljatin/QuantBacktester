# backend/app/models/backtest.py
"""BacktestResult SQLAlchemy model for storing backtest outcomes."""

from datetime import datetime
from sqlalchemy import String, DateTime, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class BacktestResult(Base):
    """Stores the full result of a backtest run, keyed by Celery task ID.

    The result_json column contains the complete backtest output including
    equity curve, trades, metrics, and Monte Carlo simulation results.
    """

    __tablename__ = "backtest_results"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    task_id: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="PENDING"
    )
    ticker: Mapped[str] = mapped_column(String(255), nullable=True)
    tickers: Mapped[list] = mapped_column(JSON, nullable=True)
    strategy_code: Mapped[str] = mapped_column(Text, nullable=False)
    start_date: Mapped[str] = mapped_column(String(10), nullable=False)
    end_date: Mapped[str] = mapped_column(String(10), nullable=False)
    config_json: Mapped[dict] = mapped_column(JSON, nullable=True)
    result_json: Mapped[dict] = mapped_column(JSON, nullable=True)
    error_message: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )
    completed_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    def __repr__(self) -> str:
        return f"<BacktestResult(task_id={self.task_id}, status={self.status})>"
