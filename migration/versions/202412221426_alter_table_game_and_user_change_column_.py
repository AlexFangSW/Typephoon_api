"""alter_table_game_and_user_change_column_name

Revision ID: 51e14fba0e84
Revises: f569c92ad183
Create Date: 2024-12-22 14:26:41.609729

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "51e14fba0e84"
down_revision: Union[str, None] = "f569c92ad183"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column("games", "type", new_column_name="game_type")
    op.alter_column("users", "type", new_column_name="user_type")


def downgrade() -> None:
    op.alter_column("games", "game_type", new_column_name="type")
    op.alter_column("users", "user_type", new_column_name="type")
