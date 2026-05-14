"""add source to daily_equity and purge backtest rows

Revision ID: a1b2c3d4e5f6
Revises: 075ff1519165
Create Date: 2026-05-13 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = '075ff1519165'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add the source column, defaulting existing rows to 'live'
    op.add_column(
        'daily_equity',
        sa.Column('source', sa.String(), nullable=False, server_default='live')
    )

    # Remove all rows that pre-date the project start (Jan 1 2026) —
    # these are exclusively from backtests that ran against historical data.
    op.execute(
        "DELETE FROM daily_equity WHERE date < '2026-01-01 00:00:00'"
    )


def downgrade() -> None:
    op.drop_column('daily_equity', 'source')
