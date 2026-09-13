"""add F to transactioncode enum

Revision ID: db397de26357
Revises: ec7d3fdf276a
Create Date: 2026-09-12 22:35:41.440096

"""
from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'db397de26357'
down_revision: str | None = 'ec7d3fdf276a'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("ALTER TYPE transactioncode ADD VALUE IF NOT EXISTS 'F'")


def downgrade() -> None:
    # Postgres doesn't support removing a value from an enum type directly;
    # would require rebuilding the type from scratch. Not worth it for a downgrade.
    pass
