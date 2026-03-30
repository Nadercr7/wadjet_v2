"""add_oauth_email_fields

Revision ID: a2567ef8fdbb
Revises: a1b2c3d4e5f6
Create Date: 2026-03-30 19:17:40.593384

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a2567ef8fdbb'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create email_tokens table
    op.create_table('email_tokens',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('user_id', sa.String(), nullable=False),
    sa.Column('token_hash', sa.String(), nullable=False),
    sa.Column('token_type', sa.String(), nullable=False),
    sa.Column('expires_at', sa.DateTime(), nullable=False),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('token_hash')
    )
    op.create_index(op.f('ix_email_tokens_user_id'), 'email_tokens', ['user_id'], unique=False)

    # SQLite requires batch mode for ALTER COLUMN operations
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.add_column(sa.Column('google_id', sa.String(), nullable=True))
        batch_op.add_column(sa.Column('auth_provider', sa.String(), server_default='email', nullable=True))
        batch_op.add_column(sa.Column('email_verified', sa.Boolean(), server_default=sa.text('0'), nullable=True))
        batch_op.add_column(sa.Column('avatar_url', sa.String(), nullable=True))
        batch_op.alter_column('password_hash', existing_type=sa.VARCHAR(), nullable=True)
        batch_op.create_index(batch_op.f('ix_users_google_id'), ['google_id'], unique=True)


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_users_google_id'))
        batch_op.alter_column('password_hash', existing_type=sa.VARCHAR(), nullable=False)
        batch_op.drop_column('avatar_url')
        batch_op.drop_column('email_verified')
        batch_op.drop_column('auth_provider')
        batch_op.drop_column('google_id')

    op.drop_index(op.f('ix_email_tokens_user_id'), table_name='email_tokens')
    op.drop_table('email_tokens')
