"""add_indexes_and_cascades

Revision ID: 39ff51de9207
Revises: 0288e8e7712c
Create Date: 2026-03-29 08:15:43.170160

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '39ff51de9207'
down_revision: Union[str, Sequence[str], None] = '0288e8e7712c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # SQLite requires batch_alter_table for FK changes (table rebuild).
    # naming_convention lets Alembic identify unnamed reflected FK constraints.
    nc = {"fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s"}

    with op.batch_alter_table('favorites', naming_convention=nc) as batch_op:
        batch_op.create_index(batch_op.f('ix_favorites_user_id'), ['user_id'], unique=False)
        batch_op.drop_constraint('fk_favorites_user_id_users', type_='foreignkey')
        batch_op.create_foreign_key('fk_favorites_user_id_users', 'users', ['user_id'], ['id'], ondelete='CASCADE')

    with op.batch_alter_table('refresh_tokens', naming_convention=nc) as batch_op:
        batch_op.create_index(batch_op.f('ix_refresh_tokens_user_id'), ['user_id'], unique=False)
        batch_op.drop_constraint('fk_refresh_tokens_user_id_users', type_='foreignkey')
        batch_op.create_foreign_key('fk_refresh_tokens_user_id_users', 'users', ['user_id'], ['id'], ondelete='CASCADE')

    with op.batch_alter_table('scan_history', naming_convention=nc) as batch_op:
        batch_op.drop_constraint('fk_scan_history_user_id_users', type_='foreignkey')
        batch_op.create_foreign_key('fk_scan_history_user_id_users', 'users', ['user_id'], ['id'], ondelete='CASCADE')

    with op.batch_alter_table('story_progress', naming_convention=nc) as batch_op:
        batch_op.create_index(batch_op.f('ix_story_progress_user_id'), ['user_id'], unique=False)
        batch_op.drop_constraint('fk_story_progress_user_id_users', type_='foreignkey')
        batch_op.create_foreign_key('fk_story_progress_user_id_users', 'users', ['user_id'], ['id'], ondelete='CASCADE')


def downgrade() -> None:
    """Downgrade schema."""
    nc = {"fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s"}

    with op.batch_alter_table('story_progress', naming_convention=nc) as batch_op:
        batch_op.drop_constraint('fk_story_progress_user_id_users', type_='foreignkey')
        batch_op.create_foreign_key('fk_story_progress_user_id_users', 'users', ['user_id'], ['id'])
        batch_op.drop_index(batch_op.f('ix_story_progress_user_id'))

    with op.batch_alter_table('scan_history', naming_convention=nc) as batch_op:
        batch_op.drop_constraint('fk_scan_history_user_id_users', type_='foreignkey')
        batch_op.create_foreign_key('fk_scan_history_user_id_users', 'users', ['user_id'], ['id'])

    with op.batch_alter_table('refresh_tokens', naming_convention=nc) as batch_op:
        batch_op.drop_constraint('fk_refresh_tokens_user_id_users', type_='foreignkey')
        batch_op.create_foreign_key('fk_refresh_tokens_user_id_users', 'users', ['user_id'], ['id'])
        batch_op.drop_index(batch_op.f('ix_refresh_tokens_user_id'))

    with op.batch_alter_table('favorites', naming_convention=nc) as batch_op:
        batch_op.drop_constraint('fk_favorites_user_id_users', type_='foreignkey')
        batch_op.create_foreign_key('fk_favorites_user_id_users', 'users', ['user_id'], ['id'])
        batch_op.drop_index(batch_op.f('ix_favorites_user_id'))
