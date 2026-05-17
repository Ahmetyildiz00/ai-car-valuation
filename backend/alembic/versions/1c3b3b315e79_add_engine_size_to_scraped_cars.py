"""add engine_size to scraped_cars

Revision ID: 1c3b3b315e79
Revises: aea8d080d1d1
Create Date: 2026-05-17 21:30:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "1c3b3b315e79"
down_revision: Union[str, None] = "aea8d080d1d1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "scraped_cars",
        sa.Column("engine_size", sa.String(length=20), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("scraped_cars", "engine_size")
