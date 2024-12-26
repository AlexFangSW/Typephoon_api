"""alter_game_and_game_result

Revision ID: e73c920ce493
Revises: adfab6b02824
Create Date: 2024-12-26 17:53:09.144747

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'e73c920ce493'
down_revision: Union[str, None] = 'adfab6b02824'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column('game_results', 'status')
    op.drop_column('game_results', 'role')
    op.add_column(
        'games',
        sa.Column('player_count',
                  sa.Integer(),
                  server_default=sa.text('0'),
                  nullable=False))
    op.add_column(
        'games',
        sa.Column('finish_count',
                  sa.Integer(),
                  server_default=sa.text('0'),
                  nullable=False))


def downgrade() -> None:
    op.drop_column('games', 'finish_count')
    op.drop_column('games', 'player_count')
    op.add_column(
        'game_results',
        sa.Column('role', sa.INTEGER(), autoincrement=False, nullable=False))
    op.add_column(
        'game_results',
        sa.Column('status', sa.INTEGER(), autoincrement=False, nullable=False))
