"""add all SEC codes to transactioncode enum

Revision ID: f84f2be491f7
Revises: 1ba9d6c71dc0
Create Date: 2026-10-11 10:33:44.434639

"""
from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f84f2be491f7"
down_revision: str | None = "1ba9d6c71dc0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

NEW_CODES = ("V", "D", "I", "C", "E", "H", "O", "X", "L", "W", "Z", "J", "K", "U")


def upgrade() -> None:
    with op.get_context().autocommit_block():
        for code in NEW_CODES:
            op.execute(f"ALTER TYPE transactioncode ADD VALUE IF NOT EXISTS '{code}'")


def downgrade() -> None:
    # Postgres can't remove an enum value without rebuilding the whole type.
    pass
