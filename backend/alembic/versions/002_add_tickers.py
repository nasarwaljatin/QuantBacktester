# backend/alembic/versions/002_add_tickers.py
"""Add tickers column and make ticker column nullable

Revision ID: 002_add_tickers
Revises: 001_initial
Create Date: 2026-07-15 12:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = "002_add_tickers"
down_revision = "001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Alter ticker to nullable String(255) and add tickers JSON column."""
    with op.batch_alter_table('backtest_results', schema=None) as batch_op:
        batch_op.alter_column('ticker',
               existing_type=sa.String(20),
               type_=sa.String(255),
               nullable=True)
        batch_op.add_column(sa.Column('tickers', sa.JSON(), nullable=True))


def downgrade() -> None:
    """Revert changes by dropping tickers and restoring ticker constraint."""
    with op.batch_alter_table('backtest_results', schema=None) as batch_op:
        batch_op.drop_column('tickers')
        batch_op.alter_column('ticker',
               existing_type=sa.String(255),
               type_=sa.String(20),
               nullable=False)
