# backend/alembic/versions/004_wfa_v2.py
"""Add window_type, anchored, efficiency_ratio columns for WFA v2

Revision ID: 004_wfa_v2
Revises: 003_add_optimization
Create Date: 2026-08-10 06:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = "004_wfa_v2"
down_revision = "003_add_optimization"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add window_type, anchored, and efficiency_ratio columns for WFA v2."""
    # Add window_type + anchored to backtest_results (for search/filter later)
    with op.batch_alter_table("backtest_results", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("anchored", sa.Boolean(), nullable=True, server_default=sa.false())
        )

    # Add efficiency_ratio + window_type + anchored to wfa_windows
    with op.batch_alter_table("wfa_windows", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("window_type", sa.String(20), nullable=True, server_default="rolling")
        )
        batch_op.add_column(
            sa.Column("anchored", sa.Boolean(), nullable=True, server_default=sa.false())
        )
        batch_op.add_column(
            sa.Column("efficiency_ratio", sa.Float(), nullable=True)
        )


def downgrade() -> None:
    """Remove WFA v2 columns."""
    with op.batch_alter_table("wfa_windows", schema=None) as batch_op:
        batch_op.drop_column("efficiency_ratio")
        batch_op.drop_column("anchored")
        batch_op.drop_column("window_type")

    with op.batch_alter_table("backtest_results", schema=None) as batch_op:
        batch_op.drop_column("anchored")
