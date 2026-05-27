"""Service for the Neural Context library (context_entries table + Qdrant)."""

import logging
from uuid import UUID, uuid4
from datetime import datetime, UTC
from typing import Sequence
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import PointStruct

from db.schemas import ContextEntry
from rain_brain.services.conversation_service import DEFAULT_USER_ID

logger = logging.getLogger(__name__)

CONTEXT_COLLECTION = "context_library"


class ContextService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ── Read ──────────────────────────────────────────────────────────────────

    async def list_entries(
        self,
        category: str | None = None,
        active_only: bool = True,
    ) -> Sequence[ContextEntry]:
        q = select(ContextEntry).where(ContextEntry.user_id == DEFAULT_USER_ID)
        if active_only:
            q = q.where(ContextEntry.is_active.is_(True))
        if category:
            q = q.where(ContextEntry.category == category)
        q = q.order_by(ContextEntry.category, ContextEntry.created_at.desc())
        result = await self.db.execute(q)
        return result.scalars().all()

    async def get_entry(self, entry_id: UUID) -> ContextEntry | None:
        result = await self.db.execute(
            select(ContextEntry).where(
                ContextEntry.id == entry_id,
                ContextEntry.user_id == DEFAULT_USER_ID,
            )
        )
        return result.scalar_one_or_none()

    # ── Write ─────────────────────────────────────────────────────────────────

    async def create_entry(
        self,
        title: str,
        content: str,
        category: str | None = None,
        subcategory: str | None = None,
        source_type: str = "manual",
        source_id: str | None = None,
        qdrant_client: AsyncQdrantClient | None = None,
        embed_provider=None,
    ) -> ContextEntry:
        entry = ContextEntry(
            user_id=DEFAULT_USER_ID,
            title=title,
            content=content,
            category=category,
            subcategory=subcategory,
            source_type=source_type,
            source_id=source_id,
            is_active=True,
        )
        self.db.add(entry)
        await self.db.commit()
        await self.db.refresh(entry)

        await self._upsert_vector(entry, qdrant_client, embed_provider)
        return entry

    async def update_entry(
        self,
        entry_id: UUID,
        title: str | None = None,
        content: str | None = None,
        category: str | None = None,
        subcategory: str | None = None,
        is_active: bool | None = None,
        qdrant_client: AsyncQdrantClient | None = None,
        embed_provider=None,
    ) -> ContextEntry | None:
        entry = await self.get_entry(entry_id)
        if entry is None:
            return None

        if title is not None:
            entry.title = title
        if content is not None:
            entry.content = content
        if category is not None:
            entry.category = category
        if subcategory is not None:
            entry.subcategory = subcategory
        if is_active is not None:
            entry.is_active = is_active
        entry.updated_at = datetime.now(UTC)

        await self.db.commit()
        await self.db.refresh(entry)

        if qdrant_client and embed_provider and entry.is_active:
            await self._upsert_vector(entry, qdrant_client, embed_provider)
        elif qdrant_client and not entry.is_active:
            await self._delete_vector(entry_id, qdrant_client)

        return entry

    async def delete_entry(
        self,
        entry_id: UUID,
        qdrant_client: AsyncQdrantClient | None = None,
    ) -> bool:
        entry = await self.get_entry(entry_id)
        if entry is None:
            return False

        await self.db.delete(entry)
        await self.db.commit()
        await self._delete_vector(entry_id, qdrant_client)
        return True

    # ── Session extraction ────────────────────────────────────────────────────

    async def extract_from_session(
        self,
        conversation_id: UUID,
        entries: list[dict],
        qdrant_client: AsyncQdrantClient | None = None,
        embed_provider=None,
    ) -> list[ContextEntry]:
        """Batch-create entries extracted from a conversation.

        Deduplicates against existing rows by case-insensitive title match
        for the active user, so re-asking similar questions doesn't pile up
        identical "Rayleigh Scattering" fragments in the side panel.
        """
        # Snapshot existing titles once, then guard against intra-batch dupes too.
        existing_titles_q = select(ContextEntry.title).where(
            ContextEntry.user_id == DEFAULT_USER_ID,
            ContextEntry.is_active.is_(True),
        )
        existing_rows = await self.db.execute(existing_titles_q)
        seen: set[str] = {(t or "").strip().lower() for (t,) in existing_rows.all()}

        created = []
        for e in entries:
            title = (e.get("title") or "").strip()
            key = title.lower()
            if not title or key in seen:
                logger.info("skip duplicate context fragment: %r", title)
                continue
            seen.add(key)
            entry = await self.create_entry(
                title=title,
                content=e["content"],
                category=e.get("category"),
                subcategory=e.get("subcategory"),
                source_type="session",
                source_id=str(conversation_id),
                qdrant_client=qdrant_client,
                embed_provider=embed_provider,
            )
            created.append(entry)
        return created

    # ── Qdrant helpers ────────────────────────────────────────────────────────

    async def _upsert_vector(
        self,
        entry: ContextEntry,
        qdrant_client: AsyncQdrantClient | None,
        embed_provider,
    ) -> None:
        if not qdrant_client or not embed_provider:
            return
        try:
            vectors = await embed_provider.embed([entry.content])
            if not vectors or not vectors[0]:
                return
            await qdrant_client.upsert(
                collection_name=CONTEXT_COLLECTION,
                points=[
                    PointStruct(
                        id=str(entry.id),
                        vector=vectors[0],
                        payload={
                            "title": entry.title,
                            "content": entry.content,
                            "category": entry.category,
                            "subcategory": entry.subcategory,
                            "source_type": entry.source_type,
                        },
                    )
                ],
            )
        except Exception as e:
            logger.warning("Failed to upsert context vector for %s: %s", entry.id, e)

    async def _delete_vector(
        self,
        entry_id: UUID,
        qdrant_client: AsyncQdrantClient | None,
    ) -> None:
        if not qdrant_client:
            return
        try:
            from qdrant_client.models import PointIdsList
            await qdrant_client.delete(
                collection_name=CONTEXT_COLLECTION,
                points_selector=PointIdsList(points=[str(entry_id)]),
            )
        except Exception as e:
            logger.warning("Failed to delete context vector for %s: %s", entry_id, e)
