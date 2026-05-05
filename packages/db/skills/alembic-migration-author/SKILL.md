---
name: alembic-migration-author
description: Use this skill when the DB Agent needs to write or refine an Alembic migration. Triggers after a schema change in /db/schemas/ or when a contract change requires a data backfill. Enforces reversibility, descriptive titles, idempotent backfills, and the two-phase rule for breaking changes. NEVER use this skill for non-Alembic SQL — those go in /db/scripts/.
---

# Skill: alembic-migration-author

## Purpose
Every database change ships as an Alembic migration that: (a) upgrades cleanly, (b) downgrades cleanly, (c) is safe to run on a populated database, (d) names itself descriptively in the version log.

## When to use
- After updating a SQLAlchemy model in `/db/schemas/`.
- For data-only migrations (backfills, default value updates).
- For introducing extensions (pg_trgm, pgcrypto) or types.

## When NOT to use
- One-off DBA scripts → put in `/db/scripts/` and don't track via Alembic.
- Schema changes Backend hasn't agreed to → write the WO reply first.

## Generating a migration

1. Update SQLAlchemy model first.
2. Run `alembic revision --autogenerate -m "add_messages_token_count_columns"`.
3. **NEVER trust autogenerate output blindly.** Open the file, read every line, fix:
   - Missing `comment=` on columns (autogenerate often drops them).
   - `op.drop_index` followed by `op.create_index` for the same index — usually a naming-convention false positive; remove both.
   - Type changes that should be done as add-column-then-backfill-then-drop.
4. Write a real `downgrade` — not `pass`.
5. Test: `alembic upgrade head && alembic downgrade -1 && alembic upgrade head`.

## Migration title conventions

`<verb>_<subject>_<detail>` — short, lowercase, snake_case.

✓ Good:
- `create_initial_tables`
- `add_messages_token_count_columns`
- `rename_skills_active_to_enabled`
- `backfill_conversation_titles_from_first_message`

❌ Bad:
- `update_things`
- `fix`
- `migration_2024_03_15`

## Migration file template

```python
"""add_messages_token_count_columns

Revision ID: 0007
Revises: 0006
Create Date: 2026-04-25 14:30:00.000000

Backend ref: WO-024
PRD/CONTRACTS: Contract 3 (messages table)

Reason: Backend needs to record prompt/completion token counts
for usage analytics in Phase 2.

Safety:
- Both columns nullable on add → safe on populated DB.
- Backfill in same migration: existing rows get 0.
- Downgrade: drop both columns. No data loss concern (analytics-only).
"""
from alembic import op
import sqlalchemy as sa

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "messages",
        sa.Column(
            "tokens_in",
            sa.Integer(),
            nullable=True,
            server_default="0",
            comment="Prompt token count reported by provider, 0 if unknown.",
        ),
    )
    op.add_column(
        "messages",
        sa.Column(
            "tokens_out",
            sa.Integer(),
            nullable=True,
            server_default="0",
            comment="Completion token count reported by provider, 0 if unknown.",
        ),
    )
    # Backfill any existing rows.
    op.execute("UPDATE messages SET tokens_in = 0 WHERE tokens_in IS NULL")
    op.execute("UPDATE messages SET tokens_out = 0 WHERE tokens_out IS NULL")
    # Now make NOT NULL.
    op.alter_column("messages", "tokens_in", nullable=False)
    op.alter_column("messages", "tokens_out", nullable=False)


def downgrade() -> None:
    op.drop_column("messages", "tokens_out")
    op.drop_column("messages", "tokens_in")
```

Key elements every migration must have:
- [ ] Top-of-file docstring with: WO ref, contract ref, reason, safety analysis.
- [ ] Real `downgrade` (not `pass`).
- [ ] Backfills written as raw SQL via `op.execute`, not Python loops.
- [ ] Default values added on `add_column`, then made NOT NULL after backfill.
- [ ] `comment=` preserved on every new column.

## The "Add → Backfill → Constrain" pattern (use this for every NOT NULL column)

```python
# Step 1: add as nullable with server_default
op.add_column("t", sa.Column("c", sa.Integer(), nullable=True, server_default="0"))
# Step 2: backfill
op.execute("UPDATE t SET c = COALESCE(c, 0)")
# Step 3: tighten
op.alter_column("t", "c", nullable=False)
```

Doing it in one step (`nullable=False` from the start) fails on populated tables.

## The Two-Phase Pattern for Breaking Changes

When renaming or retyping a column Backend reads from:

**Migration A (this PR, ships now):**
```python
def upgrade():
    op.add_column("skills", sa.Column("enabled", sa.Boolean(), nullable=True))
    op.execute("UPDATE skills SET enabled = active")
    op.alter_column("skills", "enabled", nullable=False, server_default="true")
    # leave 'active' in place — Backend still reads it
    # add a trigger to keep them in sync (optional belt-and-suspenders):
    op.execute("""
        CREATE OR REPLACE FUNCTION sync_skills_active_enabled()
        RETURNS trigger AS $$
        BEGIN
          NEW.enabled := NEW.active;
          RETURN NEW;
        END $$ LANGUAGE plpgsql;
        CREATE TRIGGER trg_skills_sync BEFORE INSERT OR UPDATE ON skills
        FOR EACH ROW EXECUTE FUNCTION sync_skills_active_enabled();
    """)

def downgrade():
    op.execute("DROP TRIGGER IF EXISTS trg_skills_sync ON skills")
    op.execute("DROP FUNCTION IF EXISTS sync_skills_active_enabled")
    op.drop_column("skills", "enabled")
```

**Wait for Backend Agent's PR landing on main.**

**Migration B (next PR, ships later):**
```python
def upgrade():
    op.execute("DROP TRIGGER IF EXISTS trg_skills_sync ON skills")
    op.execute("DROP FUNCTION IF EXISTS sync_skills_active_enabled")
    op.drop_column("skills", "active")

def downgrade():
    op.add_column("skills", sa.Column("active", sa.Boolean(), nullable=True))
    op.execute("UPDATE skills SET active = enabled")
    op.alter_column("skills", "active", nullable=False)
    # re-add trigger... (full reverse of Migration A's trigger setup)
```

## Data-only migrations

Backfills, lookups, fixes. No schema changes. Same Alembic file format, but:
- Title prefix `data_` (`data_normalize_skill_names_lowercase`).
- Always idempotent — running twice should not corrupt.
- Always reversible (or document loudly why not — and require Parent approval for non-reversible).

## Extensions

```python
def upgrade():
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")

def downgrade():
    # Don't drop extensions in downgrade — other things may depend on them.
    pass  # explicitly: leave it
```

This is the ONLY acceptable use of `pass` in a downgrade, and it must be commented as such.

## Testing migrations

In `/db/tests/test_migrations.py`:

```python
import pytest
from alembic.config import Config
from alembic import command


def test_upgrade_downgrade_upgrade(empty_postgres_url):
    cfg = Config("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", empty_postgres_url)

    command.upgrade(cfg, "head")
    command.downgrade(cfg, "base")
    command.upgrade(cfg, "head")  # must succeed twice through


def test_upgrade_on_seeded_db(seeded_postgres_url):
    cfg = Config("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", seeded_postgres_url)
    command.upgrade(cfg, "head")
    # assert: existing data still queryable, new columns have expected defaults
```

CI runs both. A failure blocks merge.

## Quality bar
- Migration title is descriptive enough that `alembic history` reads like a changelog.
- Header docstring cites WO and contract.
- Downgrade actually downgrades.
- Add → Backfill → Constrain pattern used for all new NOT NULL columns.
- Two-phase used for all rename/retype operations.

## Anti-patterns
- ❌ `def downgrade(): pass` (except for extensions, with comment).
- ❌ Trusting `alembic revision --autogenerate` output without reading it.
- ❌ One migration that does five unrelated things.
- ❌ Adding a NOT NULL column without server_default + backfill.
- ❌ Renaming a column Backend reads in a single migration.
- ❌ Python loops for backfills on large tables (use SQL).
- ❌ Migrations with no docstring or context.
