"""Add persona column to model_capability_overrides.

Revision ID: e8f9a0b1c2d3
Revises: d6e7f8a9b0c1
Create Date: 2026-04-26 01:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'e8f9a0b1c2d3'
down_revision: Union[str, Sequence[str], None] = 'd6e7f8a9b0c1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "model_capability_overrides",
        sa.Column(
            "persona",
            sa.String(20),
            server_default="drizzle",
            nullable=False,
            comment="Persona: drizzle, nimbus, or storm.",
        ),
    )


def downgrade() -> None:
    op.drop_column("model_capability_overrides", "persona")
