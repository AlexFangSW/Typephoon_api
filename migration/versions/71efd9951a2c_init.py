"""init

Revision ID: 71efd9951a2c
Revises: 
Create Date: 2024-12-01 18:19:28.531941

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from src.typephoon_api.models.util import BigSerial

# revision identifiers, used by Alembic.
revision: str = '71efd9951a2c'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'games',
        sa.Column('id', BigSerial(), nullable=False),
        sa.Column('created_at',
                  sa.DateTime(timezone=True),
                  server_default=sa.text('CURRENT_TIMESTAMP'),
                  nullable=False),
        sa.Column('start_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('end_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('status', sa.Integer(), nullable=False),
        sa.Column('invite_token', sa.Text(), nullable=False),
        sa.Column('type', sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        if_not_exists=True,
    )
    op.create_table(
        'users',
        sa.Column('id', sa.Text(), nullable=False),
        sa.Column('name', sa.Text(), nullable=False),
        sa.Column('registered_at',
                  sa.DateTime(timezone=True),
                  server_default=sa.text('CURRENT_TIMESTAMP'),
                  nullable=False),
        sa.Column('type', sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        if_not_exists=True,
    )
    op.create_table(
        'game_results',
        sa.Column('game_id', sa.BigInteger(), nullable=False),
        sa.Column('user_id', sa.Text(), nullable=False),
        sa.Column('rank', sa.Integer(), nullable=False),
        sa.Column('wpm_raw', sa.Float(), nullable=False),
        sa.Column('wpm_correct', sa.Float(), nullable=False),
        sa.Column('accuracy', sa.Float(), nullable=False),
        sa.Column('status', sa.Integer(), nullable=False),
        sa.Column('finished_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('role', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ['game_id'],
            ['games.id'],
        ),
        sa.ForeignKeyConstraint(
            ['user_id'],
            ['users.id'],
        ),
        sa.PrimaryKeyConstraint('game_id', 'user_id'),
        if_not_exists=True,
    )


def downgrade() -> None:
    op.drop_table('game_results', if_exists=True)
    op.drop_table('users', if_exists=True)
    op.drop_table('games', if_exists=True)
