# INSTRUCTIONS.md — DB Agent

## Required Reading Before You Migrate Anything
1. `/PRD.md` — full
2. `/CONTRACTS.md` — Contracts 1, 3, 4, 5 are yours
3. `/db/SYSTEM_PROMPT.md`
4. This file
5. The latest WO in `/db/INBOX/`

## Your Folder Layout (build it as you go)

```
/db
├── INBOX/                              # WOs from Parent
├── README.md                           # bring up, migrate, reset, backup
├── docker-compose.snippet.yaml         # Parent merges into root compose
├── pyproject.toml                      # SQLAlchemy + Alembic deps for Backend to install
├── alembic.ini
├── alembic/
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
│       └── 0001_initial.py
├── schemas/                            # SQLAlchemy 2.x async models — public to Backend
│   ├── __init__.py
│   ├── base.py                         # DeclarativeBase
│   ├── user.py
│   ├── conversation.py
│   ├── message.py
│   ├── document.py                     # Phase 2
│   ├── skill.py                        # Phase 2
│   ├── skill_execution.py              # Phase 2
│   ├── agent_run.py                    # Phase 3
│   └── agent_task.py                   # Phase 3
├── qdrant_collections.yaml             # Phase 2 — collection definitions
├── REDIS_KEYS.md                       # key naming conventions, human-readable
├── seeds/                              # idempotent seeders
│   ├── seed_default_user.py
│   └── seed_qdrant_collections.py
├── scripts/
│   ├── reset.sh                        # tear down + bring up + migrate
│   ├── backup.sh                       # pg_dump + qdrant snapshot + redis save
│   └── restore.sh
└── tests/
    ├── conftest.py                     # testcontainers spin-up
    ├── test_migrations.py              # upgrade head, downgrade base, upgrade head again
    └── test_schema_invariants.py       # FK consistency, indices present
```

## Skills You Have Loaded
See `/db/skills/`. Currently:
- `schema-modeller` — design SQLAlchemy 2.x async models with proper indices, FKs, comments
- `alembic-migration-author` — write reversible migrations
- `vector-collection-designer` — design Qdrant collections for the workload
- `compose-and-tune` — write docker-compose snippets with appropriate resource limits

## Standard Operating Procedures

### SOP-1: Adding a Table
1. Confirm the table is in PRD §7 / Contract 3, or open a CONTRACTS.md change request.
2. Use `schema-modeller` skill to draft the SQLAlchemy model in `schemas/`.
3. Use `alembic-migration-author` skill to generate and refine the migration.
4. Run `alembic upgrade head` then `alembic downgrade base` then `alembic upgrade head` — must succeed.
5. Add migration test that asserts post-upgrade state has expected columns.
6. Update `db/README.md` if the table is user-facing.
7. CHANGELOG entry mentioning Backend Agent's import path remains stable (or has changed).

### SOP-2: Modifying an Existing Column
**Two-phase rule** for any column rename/retype that Backend reads:

Phase A:
1. Add new column with new name/type. Backfill from old.
2. Migration sets default / writes both via trigger if needed.
3. Notify Backend Agent in WO reply: "Switch reads to new column."
4. Wait for Backend's confirmation (their PR landed using new column).

Phase B:
1. New migration drops old column.
2. Update CHANGELOG: "BREAKING: column X removed (deprecated since YYYY-MM-DD)."

Never collapse to one phase. The hour you "save" is the hour Backend's tests turn red on main.

### SOP-3: Adding a Qdrant Collection (Phase 2+)
1. Add to `qdrant_collections.yaml` under `collections:`.
2. Add a seed entry in `seeds/seed_qdrant_collections.py` (idempotent: check `client.collection_exists` first).
3. Document the payload schema in a comment in the YAML.
4. Tests bring up Qdrant via testcontainers, run seed, assert collection exists with right vector size.

### SOP-4: Adding a Redis Key Pattern
1. Add to `REDIS_KEYS.md` with: pattern, what's stored, TTL, who writes, who reads.
2. NEVER add a key without a TTL.
3. Backend's code review will reference this file via the `contract-reviewer` skill.

### SOP-5: Performance Investigation
When Backend reports a slow query:
1. Get the exact SQL from Backend (via SQLAlchemy echo or pg_stat_statements).
2. `EXPLAIN ANALYZE` it in psql.
3. Add the missing index in a new migration.
4. Verify before-and-after timing on a populated test DB.
5. Document the finding in CHANGELOG.

### SOP-6: Phase 1 Walking Skeleton — Build Order
Do these in this order. Backend Agent is blocked on each step.

1. `docker-compose.snippet.yaml` — Postgres 16, Redis 7, with healthchecks and tuned mem_limit.
2. `schemas/base.py` — DeclarativeBase, naming convention for constraints.
3. `schemas/user.py` — single-row "default user" table.
4. `schemas/conversation.py` — id, user_id (FK), title, soft_delete via deleted_at, timestamps.
5. `schemas/message.py` — id, conversation_id (FK), role enum, content text, model, tokens_in, tokens_out, created_at.
6. `alembic/versions/0001_initial.py` — creates all three tables, all FKs, indices on (conversation_id, created_at) for messages.
7. `seeds/seed_default_user.py` — inserts row into users with deterministic UUID.
8. `tests/test_migrations.py` — upgrade/downgrade/upgrade green.
9. `db/README.md` — quick start: `./scripts/reset.sh` brings up clean state.
10. `REDIS_KEYS.md` — Phase 1 keys: `rain:session:*`, `rain:cache:llm:*`.

## Schema Conventions

### Naming
- Table names: plural snake_case (`conversations`, `agent_runs`)
- Column names: snake_case (`created_at`, `tokens_in`)
- PK: always `id UUID DEFAULT gen_random_uuid()` — never serial integers
- FK columns: `<referenced_table_singular>_id` (`conversation_id`)
- Constraint naming convention (in base.py):
  ```python
  metadata = MetaData(naming_convention={
      "ix": "ix_%(column_0_label)s",
      "uq": "uq_%(table_name)s_%(column_0_name)s",
      "ck": "ck_%(table_name)s_%(constraint_name)s",
      "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
      "pk": "pk_%(table_name)s",
  })
  ```

### Required columns on every table
- `id UUID PK`
- `created_at TIMESTAMPTZ NOT NULL DEFAULT now()`
- `updated_at TIMESTAMPTZ NOT NULL DEFAULT now()` (with trigger to auto-update)
- For deletable entities: `deleted_at TIMESTAMPTZ NULL` (soft delete)

### Indices
- Every FK gets an index. Postgres does NOT create one automatically.
- Composite indices for known query patterns (e.g., `(conversation_id, created_at DESC)` on messages).
- Use partial indices for soft-deleted patterns: `WHERE deleted_at IS NULL`.

### Comments
Every table and every column has a SQL comment. Alembic syntax:
```python
op.create_table(
    "conversations",
    sa.Column("id", sa.UUID, primary_key=True),
    ...
    comment="A user's chat session. Soft-deleted via deleted_at.",
)
op.execute("COMMENT ON COLUMN conversations.title IS 'User-provided or auto-generated title.'")
```

## Quality Bar
- Every migration upgrades AND downgrades cleanly on an empty DB.
- Every migration upgrades cleanly on a DB containing realistic data (test with seeds).
- No `Column(JSON)` without a Pydantic shape documented in a comment.
- All FKs have `ondelete=` specified explicitly (CASCADE, SET NULL, or RESTRICT — your call, but explicit).
- Every async model uses Mapped/mapped_column (SQLAlchemy 2.x style), never the old `Column()`-only pattern.

## Anti-Patterns
- ❌ `id` as `int` autoincrement — use UUID.
- ❌ Storing JSON blobs as a workaround for not designing the schema.
- ❌ FK without an index.
- ❌ Migration with `def downgrade(): pass`.
- ❌ Unbounded text fields with no length sanity check.
- ❌ Putting business logic in DB triggers (except `updated_at`).
- ❌ Using Postgres as a queue (use Redis).
- ❌ Using Redis as a database (use Postgres).
- ❌ Using Qdrant for relational data (use Postgres).

## When Stuck
1. Re-read the WO and Contracts 3/4/5.
2. Check existing migrations for prior patterns.
3. If a contract is ambiguous, write a comment to Parent in the WO. Do not invent.
