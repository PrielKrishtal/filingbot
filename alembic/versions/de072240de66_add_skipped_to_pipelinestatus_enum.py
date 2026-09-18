"""add SKIPPED to pipelinestatus enum

Revision ID: de072240de66
Revises: db397de26357
Create Date: 2026-09-18 14:16:23.109162

"""
from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'de072240de66'
down_revision: str | None = 'db397de26357'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("ALTER TYPE pipelinestatus ADD VALUE IF NOT EXISTS 'SKIPPED'")


def downgrade() -> None:
    # Postgres doesn't support removing a value from an enum type directly;
    # would require rebuilding the type from scratch. Not worth it for a downgrade.
    pass
