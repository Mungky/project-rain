"""initial_schema_with_tz

Revision ID: 3c737a5a064c
Revises: 
Create Date: 2026-04-22 20:03:17.561301

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '3c737a5a064c'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Bootstrap: create base tables if running on a completely fresh database.
    # IF NOT EXISTS makes this safe for databases that already have these tables.
    op.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id UUID PRIMARY KEY,
            username VARCHAR(50) NOT NULL,
            email VARCHAR(255),
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)
    op.execute("""
        DO $$ BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'message_role') THEN
                CREATE TYPE message_role AS ENUM ('user', 'assistant', 'system', 'tool');
            END IF;
        END $$
    """)
    op.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            id UUID PRIMARY KEY,
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            title VARCHAR(200),
            model VARCHAR(100) NOT NULL DEFAULT 'kimi-k2.6:cloud',
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            deleted_at TIMESTAMPTZ
        )
    """)
    op.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id UUID PRIMARY KEY,
            conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
            role message_role NOT NULL,
            content TEXT NOT NULL,
            tokens_in INTEGER NOT NULL DEFAULT 0,
            tokens_out INTEGER NOT NULL DEFAULT 0,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)

    # Ensure timestamp columns are TIMESTAMPTZ (no-op on fresh DBs, fixes old ones)
    for table in ['conversations', 'messages', 'users']:
        op.execute(f"ALTER TABLE {table} ALTER COLUMN created_at TYPE TIMESTAMPTZ USING created_at AT TIME ZONE 'UTC'")
        op.execute(f"ALTER TABLE {table} ALTER COLUMN updated_at TYPE TIMESTAMPTZ USING updated_at AT TIME ZONE 'UTC'")

    op.execute("ALTER TABLE conversations ALTER COLUMN deleted_at TYPE TIMESTAMPTZ USING deleted_at AT TIME ZONE 'UTC'")


def downgrade() -> None:
    for table in ['conversations', 'messages', 'users']:
        op.execute(f'ALTER TABLE {table} ALTER COLUMN created_at TYPE TIMESTAMP WITHOUT TIME ZONE')
        op.execute(f'ALTER TABLE {table} ALTER COLUMN updated_at TYPE TIMESTAMP WITHOUT TIME ZONE')
        
    op.execute('ALTER TABLE conversations ALTER COLUMN deleted_at TYPE TIMESTAMP WITHOUT TIME ZONE')
