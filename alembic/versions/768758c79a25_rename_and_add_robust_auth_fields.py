"""rename_and_add_robust_auth_fields

Revision ID: 768758c79a25
Revises: bdd7775c5d8d
Create Date: 2026-04-02 16:00:19.164822

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '768758c79a25'
down_revision: Union[str, Sequence[str], None] = 'bdd7775c5d8d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # 1. Rename existing columns (to prevent data loss)
    op.alter_column('users', 'email_verified', new_column_name='is_email_verified')
    op.alter_column('users', 'two_factor_enabled', new_column_name='mfa_enabled')

    # 2. Add new robust security columns
    op.add_column('users', sa.Column('mfa_secret', sa.String(length=255), nullable=True))
    op.add_column('users', sa.Column('locked_until', sa.DateTime(), nullable=True))
    op.add_column('users', sa.Column('reset_token_expires_at', sa.DateTime(), nullable=True))
    op.add_column('users', sa.Column('verify_token_expires_at', sa.DateTime(), nullable=True))
    op.add_column('users', sa.Column('password_changed_at', sa.DateTime(), nullable=False, server_default=sa.func.now()))
    op.add_column('users', sa.Column('refresh_token_version', sa.Integer(), nullable=False, server_default='1'))


def downgrade() -> None:
    """Downgrade schema."""
    # 1. Rename columns back
    op.alter_column('users', 'is_email_verified', new_column_name='email_verified')
    op.alter_column('users', 'mfa_enabled', new_column_name='two_factor_enabled')

    # 2. Drop new robust security columns
    op.drop_column('users', 'refresh_token_version')
    op.drop_column('users', 'password_changed_at')
    op.drop_column('users', 'verify_token_expires_at')
    op.drop_column('users', 'reset_token_expires_at')
    op.drop_column('users', 'locked_until')
    op.drop_column('users', 'mfa_secret')
