---
name: schema-modeller
description: Use this skill when the DB Agent needs to design or modify a SQLAlchemy 2.x async ORM model. Triggers on any new table, column addition, FK relationship, or refactor of /db/schemas/. Enforces the project's naming conventions, required columns, indexing rules, and the modern Mapped/mapped_column syntax that Backend Agent imports from.
---

# Skill: schema-modeller

## Purpose
Design SQLAlchemy 2.x async models that are: (a) correctly typed for Python, (b) properly indexed for the workload, (c) consistent with project naming conventions, (d) safely importable from the Backend Agent.

## When to use
- New table being added per a WO.
- Adding a column or FK to an existing table.
- Refactoring schema after a contract change.

## When NOT to use
- Writing the migration itself → use `alembic-migration-author`.
- Designing Qdrant payloads → use `vector-collection-designer`.
- Writing query helpers → that's Backend Agent's territory.

## File structure

Each entity in its own file under `/db/schemas/`:

```
schemas/
├── __init__.py        # re-exports for backend convenience
├── base.py            # DeclarativeBase + naming convention + common mixins
├── user.py
├── conversation.py
├── message.py
└── ...
```

`__init__.py` keeps Backend's import surface clean:
```python
from db.schemas.base import Base
from db.schemas.user import User
from db.schemas.conversation import Conversation
from db.schemas.message import Message

__all__ = ["Base", "User", "Conversation", "Message"]
```

## base.py (write once, never touch)

```python
from datetime import datetime
from uuid import UUID, uuid4
from sqlalchemy import MetaData, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
        nullable=False,
        comment="Row creation time (UTC).",
    )
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
        server_onupdate=func.now(),
        nullable=False,
        comment="Last modification time (UTC).",
    )


class SoftDeleteMixin:
    deleted_at: Mapped[datetime | None] = mapped_column(
        nullable=True,
        comment="Soft-delete timestamp; NULL means active.",
    )


class UUIDPKMixin:
    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        default=uuid4,
        comment="Primary key (UUIDv4).",
    )
```

## Entity template

```python
from datetime import datetime
from uuid import UUID
from sqlalchemy import ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from db.schemas.base import Base, UUIDPKMixin, TimestampMixin, SoftDeleteMixin


class Conversation(Base, UUIDPKMixin, TimestampMixin, SoftDeleteMixin):
    """A user's chat session. Holds an ordered list of messages."""

    __tablename__ = "conversations"

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        comment="Owner user.",
    )
    title: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
        comment="User-provided or auto-generated title.",
    )

    messages: Mapped[list["Message"]] = relationship(
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="Message.created_at",
    )
    user: Mapped["User"] = relationship(back_populates="conversations")

    __table_args__ = (
        Index("ix_conversations_user_id_created_at", "user_id", "created_at"),
        {"comment": "User chat sessions. Soft-deleted via deleted_at."},
    )
```

## Required ingredients on every entity

- [ ] Inherits `Base, UUIDPKMixin, TimestampMixin` (and `SoftDeleteMixin` if deletable)
- [ ] `__tablename__` set to plural snake_case
- [ ] Class docstring explaining purpose
- [ ] Every column has `comment=`
- [ ] Every FK has explicit `ondelete=` (`CASCADE`, `SET NULL`, or `RESTRICT`)
- [ ] Every FK column gets an index (in `__table_args__`)
- [ ] Composite indices added for known query patterns
- [ ] `__table_args__` includes a table-level `{"comment": "..."}`
- [ ] Relationships use `back_populates` (not `backref`)
- [ ] String columns have an explicit `String(N)` length unless they're truly unbounded → use `Text`

## FK ondelete decisions (be deliberate)

| Relationship | Recommended |
|---|---|
| Conversation → User | CASCADE (delete user → delete their conversations) |
| Message → Conversation | CASCADE |
| AgentRun → Conversation | CASCADE |
| AgentTask → AgentRun | CASCADE |
| SkillExecution → Skill | RESTRICT (don't allow skill deletion if executions reference it) |
| SkillExecution → Conversation | SET NULL (preserve audit trail even if convo deleted) |
| Document → User | CASCADE |

Decide explicitly per FK. Document the choice in a comment if non-obvious.

## Indexing decisions

Index every FK. Then ask: what queries does Backend run on this table?

| Query pattern | Index |
|---|---|
| "List user's conversations newest first" | `(user_id, created_at DESC)` partial WHERE deleted_at IS NULL |
| "Get all messages in conversation ordered" | `(conversation_id, created_at)` |
| "Find skill by name" | `UNIQUE(name, version)` |
| "Active agent runs" | partial index on `status` WHERE status IN ('running', 'pending') |

Don't over-index. Each index slows writes. Aim for ≤ 4 indices per table unless justified.

## Async-specific rules

- All entities use `Mapped[T]` and `mapped_column(...)` — never the legacy `Column()` standalone.
- For relationships: `Mapped[list["Other"]]` for collections, `Mapped["Other"]` for single, `Mapped["Other | None"]` for nullable single.
- Avoid `lazy="select"` (sync-style lazy loading). Use `selectinload`/`joinedload` in Backend's queries instead, or set `lazy="raise"` to force explicit loading.

## Enums

Use Python `enum.Enum` with `SQLAlchemy.Enum` (creates a proper Postgres ENUM type):

```python
import enum
from sqlalchemy import Enum

class MessageRole(str, enum.Enum):
    user = "user"
    assistant = "assistant"
    system = "system"
    tool = "tool"

# in the model:
role: Mapped[MessageRole] = mapped_column(
    Enum(MessageRole, name="message_role", create_constraint=True),
    nullable=False,
    comment="Sender role.",
)
```

`name="message_role"` is the Postgres type name. `create_constraint=True` adds a CHECK constraint as belt-and-suspenders.

## JSONB columns

Use sparingly. When you must:

```python
from sqlalchemy.dialects.postgresql import JSONB

manifest: Mapped[dict] = mapped_column(
    JSONB,
    nullable=False,
    comment="Skill manifest, validated against /backend/schemas/skill_manifest.schema.json on insert.",
)
```

Always:
- Document the JSON shape in the comment with a path to the JSON Schema if any.
- Add a GIN index if you'll query into the JSON: `Index("ix_skills_manifest_gin", "manifest", postgresql_using="gin")`.

## Quality bar
- `from db.schemas import X, Y, Z` works without surprises.
- `mypy --strict` passes on every file in `schemas/`.
- Every column comment is a complete sentence with a period.
- No raw `Column()` calls — only `mapped_column`.
- All FKs have an explicit `ondelete`.

## Anti-patterns
- ❌ Reusing strings for column names that should be enums.
- ❌ `nullable=True` by default (be intentional).
- ❌ Forgetting `back_populates` on the inverse side of a relationship.
- ❌ `String` without a length.
- ❌ `lazy="select"` on collections (causes N+1 in async code).
- ❌ Putting business logic in `__init__` of an entity.
