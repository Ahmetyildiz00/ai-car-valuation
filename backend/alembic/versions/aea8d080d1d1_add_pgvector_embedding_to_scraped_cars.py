"""add pgvector embedding to scraped_cars

Revision ID: aea8d080d1d1
Revises: a3f8c9d12e44
Create Date: 2026-05-17 19:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector


revision: str = "aea8d080d1d1"
down_revision: Union[str, None] = "a3f8c9d12e44"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


EMBEDDING_DIM = 384  # sentence-transformers/all-MiniLM-L6-v2


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.add_column(
        "scraped_cars",
        sa.Column("embedding", Vector(EMBEDDING_DIM), nullable=True),
    )
    # ivfflat would be ideal but requires data + lists tuning; HNSW works
    # well on empty tables and scales to our size.
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_scraped_cars_embedding_hnsw "
        "ON scraped_cars USING hnsw (embedding vector_l2_ops)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_scraped_cars_embedding_hnsw")
    op.drop_column("scraped_cars", "embedding")
