"""alter-nullable

Revision ID: a98003368f20
Revises: 2e896f63cdef
Create Date: 2024-12-05 18:13:20.268855

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'a98003368f20'
down_revision: Union[str, None] = '2e896f63cdef'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# sqlalchemy.exc.ProgrammingError: (psycopg2.errors.DuplicateObject) constraint "game_results_game_id_fkey" for relation "game_results" already exists
#
# [SQL: ALTER TABLE game_results ADD CONSTRAINT game_results_game_id_fkey FOREIGN KEY(game_id) REFERENCES games (id) ON DELETE CASCADE]


def upgrade() -> None:
    op.drop_constraint('game_results_game_id_fkey',
                       'game_results',
                       type_='foreignkey')
    op.drop_constraint('game_results_user_id_fkey',
                       'game_results',
                       type_='foreignkey')
    op.create_foreign_key("game_results_game_id_fkey",
                          'game_results',
                          'users', ['user_id'], ['id'],
                          ondelete='CASCADE')
    op.create_foreign_key("game_results_game_id_fkey",
                          'game_results',
                          'games', ['game_id'], ['id'],
                          ondelete='CASCADE')
    op.alter_column('games',
                    'start_at',
                    existing_type=postgresql.TIMESTAMP(timezone=True),
                    nullable=True)
    op.alter_column('games',
                    'end_at',
                    existing_type=postgresql.TIMESTAMP(timezone=True),
                    nullable=True)
    op.alter_column('games',
                    'invite_token',
                    existing_type=sa.TEXT(),
                    nullable=True)


def downgrade() -> None:
    op.alter_column('games',
                    'invite_token',
                    existing_type=sa.TEXT(),
                    nullable=False)
    op.alter_column('games',
                    'end_at',
                    existing_type=postgresql.TIMESTAMP(timezone=True),
                    nullable=False)
    op.alter_column('games',
                    'start_at',
                    existing_type=postgresql.TIMESTAMP(timezone=True),
                    nullable=False)
    op.drop_constraint("game_results_game_id_fkey",
                       'game_results',
                       type_='foreignkey')
    op.drop_constraint("game_results_game_id_fkey",
                       'game_results',
                       type_='foreignkey')
    op.create_foreign_key('game_results_user_id_fkey', 'game_results', 'users',
                          ['user_id'], ['id'])
    op.create_foreign_key('game_results_game_id_fkey', 'game_results', 'games',
                          ['game_id'], ['id'])
