# backend/app/models/optimization.py
"""SQLAlchemy models for parameter sweep and walk-forward analysis results."""

from sqlalchemy import String, Integer, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class SweepResult(Base):
    """Stores the result of a single parameter combination in a sweep run."""

    __tablename__ = "sweep_results"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    task_id: Mapped[str] = mapped_column(
        String(255), nullable=False, index=True
    )
    combo_index: Mapped[int] = mapped_column(Integer, nullable=False)
    parameters: Mapped[dict] = mapped_column(JSON, nullable=True)
    metrics: Mapped[dict] = mapped_column(JSON, nullable=True)
    equity_curve: Mapped[list] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="PENDING")
    error_message: Mapped[str] = mapped_column(Text, nullable=True)

    def __repr__(self) -> str:
        return f"<SweepResult(task_id={self.task_id}, combo={self.combo_index}, status={self.status})>"


class WFAWindow(Base):
    """Stores the result of a single window in a walk-forward analysis run."""

    __tablename__ = "wfa_windows"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    task_id: Mapped[str] = mapped_column(
        String(255), nullable=False, index=True
    )
    window_index: Mapped[int] = mapped_column(Integer, nullable=False)
    in_sample_start: Mapped[str] = mapped_column(String(10), nullable=True)
    in_sample_end: Mapped[str] = mapped_column(String(10), nullable=True)
    out_of_sample_start: Mapped[str] = mapped_column(String(10), nullable=True)
    out_of_sample_end: Mapped[str] = mapped_column(String(10), nullable=True)
    optimized_params: Mapped[dict] = mapped_column(JSON, nullable=True)
    in_sample_metrics: Mapped[dict] = mapped_column(JSON, nullable=True)
    out_of_sample_metrics: Mapped[dict] = mapped_column(JSON, nullable=True)
    out_of_sample_equity: Mapped[list] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="PENDING")
    error_message: Mapped[str] = mapped_column(Text, nullable=True)

    def __repr__(self) -> str:
        return f"<WFAWindow(task_id={self.task_id}, window={self.window_index}, status={self.status})>"
