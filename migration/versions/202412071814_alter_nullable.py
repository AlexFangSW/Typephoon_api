"""alter-nullable

Revision ID: f7cbea688205
Revises: 2e896f63cdef
Create Date: 2024-12-05 21:36:45.946373

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "f7cbea688205"
down_revision: Union[str, None] = "2e896f63cdef"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint("game_results_game_id_fkey", "game_results", type_="foreignkey")
    op.drop_constraint("game_results_user_id_fkey", "game_results", type_="foreignkey")
    op.create_foreign_key(
        "game_results_game_id_fkey",
        "game_results",
        "games",
        ["game_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "game_results_user_id_fkey",
        "game_results",
        "users",
        ["user_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.alter_column(
        "games",
        "start_at",
        existing_type=postgresql.TIMESTAMP(timezone=True),
        nullable=True,
    )
    op.alter_column(
        "games",
        "end_at",
        existing_type=postgresql.TIMESTAMP(timezone=True),
        nullable=True,
    )
    op.alter_column("games", "invite_token", existing_type=sa.TEXT(), nullable=True)


def downgrade() -> None:
    pass
