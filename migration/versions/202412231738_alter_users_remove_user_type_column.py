"""alter_users_remove_user_type_column

Revision ID: adfab6b02824
Revises: 51e14fba0e84
Create Date: 2024-12-23 17:38:29.238223

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'adfab6b02824'
down_revision: Union[str, None] = '51e14fba0e84'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column('users', 'user_type')


def downgrade() -> None:
    op.add_column(
        'users',
        sa.Column('user_type', sa.INTEGER(), autoincrement=False,
                  nullable=True))
