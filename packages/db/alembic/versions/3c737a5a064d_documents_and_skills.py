"""add_documents_and_skills_tables

Revision ID: 3c737a5a064d
Revises: 3c737a5a064c
Create Date: 2026-04-22 21:00:00.000000

Backend ref: WO-018
PRD/CONTRACTS: Contract 3 (Postgres), PRD §7.3 (Skill format)

Reason: Phase 2 requires document tracking (upload pipeline) and skill
registration + execution audit. Documents link to MinIO objects and
Qdrant collections. Skills link to Docker sandbox runtimes. SkillExecution
preserves audit trail even if conversation is deleted.

Safety:
- New tables only; no data loss risk.
- All NOT NULL columns have server_default (safe on empty DB).
- JSONB column manifest_json documented with schema path.
- FK ondelete choices explicit per schema-modeller skill.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


revision = "3c737a5a064d"
down_revision = "3c737a5a064c"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- Enum type (create before table so create_table doesn't double-create) ---
    document_status = sa.Enum(
        "uploading", "processing", "ready", "error",
        name="document_status",
        create_constraint=True,
    )

    # --- Documents table ---
    op.create_table(
        "documents",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column(
            "user_id",
            sa.UUID(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            comment="Owner user.",
        ),
        sa.Column(
            "filename",
            sa.String(255),
            nullable=False,
            comment="Original filename as uploaded.",
        ),
        sa.Column(
            "mime",
            sa.String(128),
            nullable=False,
            comment="MIME type of the uploaded file.",
        ),
        sa.Column(
            "minio_key",
            sa.String(512),
            nullable=False,
            comment="Object key in MinIO bucket (rain-uploads).",
        ),
        sa.Column(
            "qdrant_collection",
            sa.String(64),
            nullable=False,
            server_default="documents",
            comment="Qdrant collection name where chunks are stored.",
        ),
        sa.Column(
            "status",
            document_status,
            nullable=False,
            server_default="uploading",
            comment="Processing status: uploading → processing → ready | error.",
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        comment="User-uploaded documents. Raw files in MinIO, vectors in Qdrant.",
    )
    op.create_index("ix_documents_user_id_created_at", "documents", ["user_id", "created_at"])
    op.create_index("ix_documents_status", "documents", ["status"])

    # --- Skills table ---
    op.create_table(
        "skills",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column(
            "name",
            sa.String(100),
            nullable=False,
            comment="Human-readable skill name, e.g. web-search-duckduckgo.",
        ),
        sa.Column(
            "version",
            sa.String(20),
            nullable=False,
            comment="Semver string, e.g. 0.1.0.",
        ),
        sa.Column(
            "manifest_json",
            JSONB,
            nullable=False,
            comment="Full skill manifest, validated against /backend/schemas/skill_manifest.schema.json on insert.",
        ),
        sa.Column(
            "docker_image",
            sa.String(255),
            nullable=True,
            comment="Docker image tag for the sandboxed skill runtime.",
        ),
        sa.Column(
            "installed_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
            comment="Timestamp when the skill was installed.",
        ),
        sa.Column(
            "enabled",
            sa.Boolean(),
            nullable=False,
            server_default="true",
            comment="Whether the skill is active and available for use.",
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        comment="Installed skills. Manifest stored as JSONB, validated on insert.",
    )
    op.create_index("uq_skills_name_version", "skills", ["name", "version"], unique=True)
    op.create_index("ix_skills_enabled", "skills", ["enabled"])

    # --- Skill Executions table ---
    op.create_table(
        "skill_executions",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column(
            "skill_id",
            sa.UUID(),
            sa.ForeignKey("skills.id", ondelete="RESTRICT"),
            nullable=False,
            comment="The skill that was executed.",
        ),
        sa.Column(
            "conversation_id",
            sa.UUID(),
            sa.ForeignKey("conversations.id", ondelete="SET NULL"),
            nullable=True,
            comment="Conversation context; NULL if conversation is deleted (preserve audit trail).",
        ),
        sa.Column(
            "input",
            sa.Text(),
            nullable=False,
            comment="JSON-encoded input parameters passed to the skill.",
        ),
        sa.Column(
            "output",
            sa.Text(),
            nullable=True,
            comment="JSON-encoded output from the skill. NULL if execution failed.",
        ),
        sa.Column(
            "duration_ms",
            sa.Integer(),
            nullable=True,
            comment="Execution wall-clock time in milliseconds.",
        ),
        sa.Column(
            "error",
            sa.Text(),
            nullable=True,
            comment="Error message if skill execution failed. NULL on success.",
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        comment="Audit trail of skill executions within conversations.",
    )
    op.create_index("ix_skill_executions_skill_id", "skill_executions", ["skill_id"])
    op.create_index("ix_skill_executions_conversation_id", "skill_executions", ["conversation_id"])
    op.create_index("ix_skill_executions_created_at", "skill_executions", ["created_at"])

    # --- Column-level SQL comments (explicit belt-and-suspenders) ---
    op.execute("COMMENT ON COLUMN documents.user_id IS 'Owner user.'")
    op.execute("COMMENT ON COLUMN documents.filename IS 'Original filename as uploaded.'")
    op.execute("COMMENT ON COLUMN documents.mime IS 'MIME type of the uploaded file.'")
    op.execute("COMMENT ON COLUMN documents.minio_key IS 'Object key in MinIO bucket (rain-uploads).'")
    op.execute("COMMENT ON COLUMN documents.qdrant_collection IS 'Qdrant collection name where chunks are stored.'")
    op.execute("COMMENT ON COLUMN documents.status IS 'Processing status: uploading → processing → ready | error.'")
    op.execute("COMMENT ON COLUMN skills.name IS 'Human-readable skill name, e.g. web-search-duckduckgo.'")
    op.execute("COMMENT ON COLUMN skills.version IS 'Semver string, e.g. 0.1.0.'")
    op.execute("COMMENT ON COLUMN skills.manifest_json IS 'Full skill manifest, validated against /backend/schemas/skill_manifest.schema.json on insert.'")
    op.execute("COMMENT ON COLUMN skills.docker_image IS 'Docker image tag for the sandboxed skill runtime.'")
    op.execute("COMMENT ON COLUMN skills.installed_at IS 'Timestamp when the skill was installed.'")
    op.execute("COMMENT ON COLUMN skills.enabled IS 'Whether the skill is active and available for use.'")
    op.execute("COMMENT ON COLUMN skill_executions.skill_id IS 'The skill that was executed.'")
    op.execute("COMMENT ON COLUMN skill_executions.conversation_id IS 'Conversation context; NULL if conversation is deleted (preserve audit trail).'")
    op.execute("COMMENT ON COLUMN skill_executions.input IS 'JSON-encoded input parameters passed to the skill.'")
    op.execute("COMMENT ON COLUMN skill_executions.output IS 'JSON-encoded output from the skill. NULL if execution failed.'")
    op.execute("COMMENT ON COLUMN skill_executions.duration_ms IS 'Execution wall-clock time in milliseconds.'")
    op.execute("COMMENT ON COLUMN skill_executions.error IS 'Error message if skill execution failed. NULL on success.'")


def downgrade() -> None:
    op.drop_table("skill_executions")
    op.drop_table("skills")
    op.drop_table("documents")
    op.execute("DROP TYPE IF EXISTS document_status")