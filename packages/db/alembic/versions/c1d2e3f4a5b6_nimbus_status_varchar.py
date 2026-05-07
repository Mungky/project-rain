"""nimbus_status_to_varchar

Change nimbus_documents.status from enum to VARCHAR for flexibility.
Adds: queued, processing states.

Revision ID: c1d2e3f4a5b6
Revises: b0c1d2e3f4a5
Create Date: 2026-05-07

"""
from typing import Sequence, Union
from alembic import op

revision: str = 'c1d2e3f4a5b6'
down_revision: Union[str, Sequence[str], None] = 'b0c1d2e3f4a5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE nimbus_documents
        ALTER COLUMN status TYPE VARCHAR(30) USING status::text
    """)
    op.execute("""
        ALTER TABLE nimbus_documents
        ALTER COLUMN status SET DEFAULT 'pending'
    """)
    op.execute("DROP TYPE IF EXISTS nimbus_status")


def downgrade() -> None:
    op.execute("""
        DO $$ BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'nimbus_status') THEN
                CREATE TYPE nimbus_status AS ENUM (
                    'pending','queued','processing','archived','failed',
                    'access_requested','access_approved','access_denied'
                );
            END IF;
        END $$
    """)
    op.execute("""
        ALTER TABLE nimbus_documents
        ALTER COLUMN status TYPE nimbus_status
        USING status::nimbus_status
    """)
