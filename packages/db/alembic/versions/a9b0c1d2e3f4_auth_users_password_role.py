"""auth_users_password_role

Revision ID: a9b0c1d2e3f4
Revises: 39b10c768130
Create Date: 2026-05-07

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'a9b0c1d2e3f4'
down_revision: Union[str, Sequence[str], None] = 'f5a2b1c9d8e7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add password_hash — nullable for now so existing rows are not broken
    op.execute("""
        ALTER TABLE users
        ADD COLUMN IF NOT EXISTS password_hash VARCHAR(255)
    """)
    # Add role column with default 'admin' so the existing default user becomes admin
    op.execute("""
        ALTER TABLE users
        ADD COLUMN IF NOT EXISTS role VARCHAR(20) NOT NULL DEFAULT 'admin'
    """)
    # Add is_active flag
    op.execute("""
        ALTER TABLE users
        ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT TRUE
    """)
    # Any user created AFTER this migration should default to 'user', not 'admin'.
    # Change the column default now that the existing row has 'admin'.
    op.execute("""
        ALTER TABLE users ALTER COLUMN role SET DEFAULT 'user'
    """)
    # Unique index on email (for login by email later)
    op.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS ix_users_email ON users (email)
        WHERE email IS NOT NULL
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_users_email")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS is_active")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS role")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS password_hash")
