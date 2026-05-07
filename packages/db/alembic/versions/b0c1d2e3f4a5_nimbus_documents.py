"""nimbus_documents

Revision ID: b0c1d2e3f4a5
Revises: a9b0c1d2e3f4
Create Date: 2026-05-07

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'b0c1d2e3f4a5'
down_revision: Union[str, Sequence[str], None] = 'a9b0c1d2e3f4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_STATUS = "('pending', 'archived', 'failed', 'access_requested', 'access_approved', 'access_denied')"


def upgrade() -> None:
    op.execute(f"""
        DO $$ BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'nimbus_status') THEN
                CREATE TYPE nimbus_status AS ENUM {_STATUS};
            END IF;
        END $$
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS nimbus_documents (
            id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            original_filename  VARCHAR(500)  NOT NULL,
            archived_filename  VARCHAR(500)  NOT NULL,
            doc_type           VARCHAR(20)   NOT NULL,
            sequence_number    INTEGER       NOT NULL,
            client_code        VARCHAR(50)   NOT NULL,
            project_code       VARCHAR(50)   NOT NULL,
            folder_category    VARCHAR(20)   NOT NULL,
            drive_file_id      VARCHAR(200),
            drive_path         VARCHAR(1000) NOT NULL DEFAULT '',
            status             nimbus_status NOT NULL DEFAULT 'pending',
            version            VARCHAR(10)   NOT NULL DEFAULT 'V1',
            uploaded_by_user_id UUID REFERENCES users(id) ON DELETE SET NULL,
            uploaded_by_name    VARCHAR(100),
            access_token        VARCHAR(64),
            access_token_expires_at TIMESTAMPTZ,
            notified_at         TIMESTAMPTZ,
            created_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at         TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)

    op.execute("CREATE INDEX IF NOT EXISTS ix_nimbus_docs_status ON nimbus_documents (status)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_nimbus_docs_client ON nimbus_documents (client_code, project_code)")
    op.execute("CREATE SEQUENCE IF NOT EXISTS nimbus_seq_global START 1")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS nimbus_documents")
    op.execute("DROP TYPE IF EXISTS nimbus_status")
    op.execute("DROP SEQUENCE IF EXISTS nimbus_seq_global")
