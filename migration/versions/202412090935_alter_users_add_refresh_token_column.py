"""alter_users_add_refresh_token_column

Revision ID: f569c92ad183
Revises: f7cbea688205
Create Date: 2024-12-09 09:35:38.799433

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "f569c92ad183"
down_revision: Union[str, None] = "f7cbea688205"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("refresh_token", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "refresh_token")
