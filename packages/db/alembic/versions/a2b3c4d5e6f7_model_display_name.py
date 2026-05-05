"""Add display_name to model_capability_overrides.

Revision ID: a2b3c4d5e6f7
Revises: f1a2b3c4d5e6
Create Date: 2026-04-25
"""

from alembic import op
import sqlalchemy as sa

revision = "a2b3c4d5e6f7"
down_revision = "f1a2b3c4d5e6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "model_capability_overrides",
        sa.Column("display_name", sa.String(200), nullable=True,
                  comment="Optional human-friendly label shown in the UI instead of model_id."),
    )


def downgrade() -> None:
    op.drop_column("model_capability_overrides", "display_name")
