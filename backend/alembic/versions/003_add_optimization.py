# backend/alembic/versions/003_add_optimization.py
"""Add sweep_results, wfa_windows tables and run_type column to backtest_results

Revision ID: 003_add_optimization
Revises: 002_add_tickers
Create Date: 2026-07-15 14:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = "003_add_optimization"
down_revision = "002_add_tickers"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add run_type to backtest_results and create sweep/wfa tables."""
    # Add run_type to backtest_results
    with op.batch_alter_table("backtest_results", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("run_type", sa.String(20), nullable=True, server_default="single")
        )
        batch_op.add_column(
            sa.Column("progress", sa.String(255), nullable=True)
        )

    # Create sweep_results table
    op.create_table(
        "sweep_results",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("task_id", sa.String(255), nullable=False, index=True),
        sa.Column("combo_index", sa.Integer(), nullable=False),
        sa.Column("parameters", sa.JSON(), nullable=True),
        sa.Column("metrics", sa.JSON(), nullable=True),
        sa.Column("equity_curve", sa.JSON(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="PENDING"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create wfa_windows table
    op.create_table(
        "wfa_windows",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("task_id", sa.String(255), nullable=False, index=True),
        sa.Column("window_index", sa.Integer(), nullable=False),
        sa.Column("in_sample_start", sa.String(10), nullable=True),
        sa.Column("in_sample_end", sa.String(10), nullable=True),
        sa.Column("out_of_sample_start", sa.String(10), nullable=True),
        sa.Column("out_of_sample_end", sa.String(10), nullable=True),
        sa.Column("optimized_params", sa.JSON(), nullable=True),
        sa.Column("in_sample_metrics", sa.JSON(), nullable=True),
        sa.Column("out_of_sample_metrics", sa.JSON(), nullable=True),
        sa.Column("out_of_sample_equity", sa.JSON(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="PENDING"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    """Remove optimization tables and columns."""
    op.drop_table("wfa_windows")
    op.drop_table("sweep_results")
    with op.batch_alter_table("backtest_results", schema=None) as batch_op:
        batch_op.drop_column("progress")
        batch_op.drop_column("run_type")
