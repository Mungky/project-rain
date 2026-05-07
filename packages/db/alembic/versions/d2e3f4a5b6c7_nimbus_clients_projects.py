"""nimbus_clients_projects

Revision ID: d2e3f4a5b6c7
Revises: c1d2e3f4a5b6
Create Date: 2026-05-07
"""
from typing import Sequence, Union
from alembic import op

revision: str = 'd2e3f4a5b6c7'
down_revision: Union[str, Sequence[str], None] = 'c1d2e3f4a5b6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS nimbus_clients (
            id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            code         VARCHAR(30)  UNIQUE NOT NULL,
            name         VARCHAR(200) NOT NULL,
            aliases      TEXT[]       NOT NULL DEFAULT '{}',
            active       BOOLEAN      NOT NULL DEFAULT true,
            created_at   TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
            updated_at   TIMESTAMPTZ  NOT NULL DEFAULT NOW()
        )
    """)
    op.execute("""
        CREATE TABLE IF NOT EXISTS nimbus_projects (
            id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            client_code             VARCHAR(30)  NOT NULL
                                    REFERENCES nimbus_clients(code)
                                    ON DELETE CASCADE ON UPDATE CASCADE,
            code                    VARCHAR(60)  NOT NULL,
            name                    VARCHAR(200) NOT NULL,
            default_folder_category VARCHAR(20)  NOT NULL DEFAULT 'MISC',
            active                  BOOLEAN      NOT NULL DEFAULT true,
            created_at              TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
            updated_at              TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
            UNIQUE(client_code, code)
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_nimbus_projects_client ON nimbus_projects(client_code)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS nimbus_projects")
    op.execute("DROP TABLE IF EXISTS nimbus_clients")
