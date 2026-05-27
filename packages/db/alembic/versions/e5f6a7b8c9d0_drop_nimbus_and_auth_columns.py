"""drop nimbus tables and auth columns from users

Revision ID: e5f6a7b8c9d0
Revises: d2e3f4a5b6c7
Create Date: 2026-05-08
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'e5f6a7b8c9d0'
down_revision: Union[str, Sequence[str], None] = 'd2e3f4a5b6c7'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop nimbus tables (order matters due to FK)
    op.drop_table('nimbus_documents')
    op.drop_table('nimbus_projects')
    op.drop_table('nimbus_clients')

    # Drop nimbus sequence
    op.execute('DROP SEQUENCE IF EXISTS nimbus_seq_global')

    # Drop auth-related columns from users
    op.drop_index('ix_users_email', table_name='users', postgresql_where=sa.text('email IS NOT NULL'))
    op.drop_column('users', 'is_active')
    op.drop_column('users', 'role')
    op.drop_column('users', 'password_hash')
    op.drop_column('users', 'email')


def downgrade() -> None:
    # Re-add auth columns
    op.add_column('users', sa.Column('email', sa.String(255), nullable=True))
    op.add_column('users', sa.Column('password_hash', sa.String(255), nullable=True))
    op.add_column('users', sa.Column('role', sa.String(20), nullable=False, server_default='user'))
    op.add_column('users', sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'))
    op.create_index(
        'ix_users_email', 'users', ['email'],
        unique=True,
        postgresql_where=sa.text('email IS NOT NULL'),
    )

    # Re-create nimbus tables would require full schema — omitted for brevity