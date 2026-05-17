"""add is_admin to users

Revision ID: a3f8c9d12e44
Revises: 7314f58ba532
Create Date: 2026-05-17 14:30:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a3f8c9d12e44"
down_revision: Union[str, None] = "7314f58ba532"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "is_admin",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "is_admin")
