"""Service for the Few-Shot Library (few_shot_entries table + Qdrant)."""

import logging
from uuid import UUID
from datetime import datetime, UTC
from typing import Sequence
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import PointStruct

from db.schemas.few_shot import FewShotEntry
from rain_brain.services.conversation_service import DEFAULT_USER_ID

logger = logging.getLogger(__name__)

FEW_SHOT_COLLECTION = "few_shot_library"


class FewShotService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ── Read ──────────────────────────────────────────────────────────────────

    async def list_entries(
        self,
        task_type: str | None = None,
        language: str | None = None,
        min_quality: float = 0.0,
        limit: int = 50,
    ) -> Sequence[FewShotEntry]:
        q = (
            select(FewShotEntry)
            .where(FewShotEntry.user_id == DEFAULT_USER_ID)
            .where(FewShotEntry.quality_score >= min_quality)
        )
        if task_type:
            q = q.where(FewShotEntry.task_type == task_type)
        if language:
            q = q.where(FewShotEntry.language == language)
        q = q.order_by(FewShotEntry.quality_score.desc(), FewShotEntry.times_used.desc()).limit(limit)
        result = await self.db.execute(q)
        return result.scalars().all()

    async def get_entry(self, entry_id: UUID) -> FewShotEntry | None:
        result = await self.db.execute(
            select(FewShotEntry).where(
                FewShotEntry.id == entry_id,
                FewShotEntry.user_id == DEFAULT_USER_ID,
            )
        )
        return result.scalar_one_or_none()

    async def semantic_search(
        self,
        query: str,
        embed_provider,
        qdrant_client: AsyncQdrantClient,
        task_type: str | None = None,
        language: str | None = None,
        limit: int = 3,
        min_quality: float = 0.7,
    ) -> list[dict]:
        """Retrieve semantically similar few-shot examples from Qdrant.

        Returns list of dicts with keys: id, query_pattern, response_structure,
        response_sample, task_type, language, quality_score, score.
        """
        try:
            vectors = await embed_provider.embed([query])
            if not vectors or not vectors[0]:
                return []

            filter_conditions = []
            if task_type:
                filter_conditions.append({
                    "key": "task_type",
                    "match": {"value": task_type},
                })
            if language:
                filter_conditions.append({
                    "key": "language",
                    "match": {"value": language},
                })

            from qdrant_client.models import Filter, FieldCondition, MatchValue, Range
            qdrant_filter = None
            conditions = []
            if task_type:
                conditions.append(FieldCondition(key="task_type", match=MatchValue(value=task_type)))
            if min_quality > 0:
                conditions.append(FieldCondition(key="quality_score", range=Range(gte=min_quality)))
            if conditions:
                qdrant_filter = Filter(must=conditions)

            hits = await qdrant_client.query_points(
                collection_name=FEW_SHOT_COLLECTION,
                query=vectors[0],
                limit=limit,
                with_payload=True,
                query_filter=qdrant_filter,
            )

            results = []
            for point in hits.points:
                payload = point.payload or {}
                results.append({
                    "id": str(point.id),
                    "query_pattern": payload.get("query_pattern", ""),
                    "response_structure": payload.get("response_structure", ""),
                    "response_sample": payload.get("response_sample", ""),
                    "task_type": payload.get("task_type", "general_chat"),
                    "language": payload.get("language", "en"),
                    "quality_score": payload.get("quality_score", 0.8),
                    "score": getattr(point, "score", 0.0),
                })
            return results

        except Exception as e:
            logger.warning("FewShotService.semantic_search failed: %s", e)
            return []

    # ── Write ─────────────────────────────────────────────────────────────────

    async def save_pattern(
        self,
        query_pattern: str,
        response_structure: str,
        response_sample: str,
        task_type: str = "general_chat",
        domain_tags: list[str] | None = None,
        language: str = "en",
        complexity: str = "medium",
        source_ai: str = "rain",
        quality_score: float = 0.8,
        qdrant_client: AsyncQdrantClient | None = None,
        embed_provider=None,
    ) -> FewShotEntry:
        estimated_tokens = len(response_sample) // 4

        entry = FewShotEntry(
            user_id=DEFAULT_USER_ID,
            source_ai=source_ai,
            query_pattern=query_pattern,
            response_structure=response_structure,
            response_sample=response_sample,
            task_type=task_type,
            domain_tags=domain_tags or [],
            language=language,
            complexity=complexity,
            quality_score=quality_score,
            times_used=0,
            was_helpful=None,
            estimated_tokens=estimated_tokens,
        )
        self.db.add(entry)
        await self.db.commit()
        await self.db.refresh(entry)

        await self._upsert_vector(entry, qdrant_client, embed_provider)
        return entry

    async def mark_helpful(
        self,
        entry_id: UUID,
        helpful: bool,
        qdrant_client: AsyncQdrantClient | None = None,
    ) -> FewShotEntry | None:
        entry = await self.get_entry(entry_id)
        if entry is None:
            return None

        entry.was_helpful = helpful
        # Adjust quality score: helpful → +0.05 (cap 1.0), not helpful → -0.15 (floor 0.1)
        if helpful:
            entry.quality_score = min(1.0, entry.quality_score + 0.05)
        else:
            entry.quality_score = max(0.1, entry.quality_score - 0.15)
        entry.updated_at = datetime.now(UTC)

        await self.db.commit()
        await self.db.refresh(entry)

        logger.debug("few_shot: feedback recorded for %s (helpful=%s, new_score=%.2f)", entry_id, helpful, entry.quality_score)

        # Sync updated quality_score to Qdrant payload so filter queries use fresh value
        if qdrant_client:
            try:
                from qdrant_client.models import PointIdsList
                await qdrant_client.set_payload(
                    collection_name=FEW_SHOT_COLLECTION,
                    payload={"quality_score": entry.quality_score, "was_helpful": helpful},
                    points=PointIdsList(points=[str(entry_id)]),
                )
            except Exception as e:
                logger.warning("Failed to sync quality_score to Qdrant for %s: %s", entry_id, e)

        return entry

    async def increment_usage(self, entry_id: UUID) -> None:
        await self.db.execute(
            update(FewShotEntry)
            .where(FewShotEntry.id == entry_id, FewShotEntry.user_id == DEFAULT_USER_ID)
            .values(times_used=FewShotEntry.times_used + 1)
        )
        await self.db.commit()

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

    # ── Qdrant helpers ────────────────────────────────────────────────────────

    async def _upsert_vector(
        self,
        entry: FewShotEntry,
        qdrant_client: AsyncQdrantClient | None,
        embed_provider,
    ) -> None:
        if not qdrant_client or not embed_provider:
            return
        try:
            vectors = await embed_provider.embed([entry.query_pattern])
            if not vectors or not vectors[0]:
                return
            await qdrant_client.upsert(
                collection_name=FEW_SHOT_COLLECTION,
                points=[
                    PointStruct(
                        id=str(entry.id),
                        vector=vectors[0],
                        payload={
                            "query_pattern": entry.query_pattern,
                            "response_structure": entry.response_structure,
                            "response_sample": entry.response_sample[:1000],
                            "task_type": entry.task_type,
                            "language": entry.language,
                            "quality_score": entry.quality_score,
                            "source_ai": entry.source_ai,
                        },
                    )
                ],
            )
        except Exception as e:
            logger.warning("Failed to upsert few-shot vector for %s: %s", entry.id, e)

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
                collection_name=FEW_SHOT_COLLECTION,
                points_selector=PointIdsList(points=[str(entry_id)]),
            )
        except Exception as e:
            logger.warning("Failed to delete few-shot vector for %s: %s", entry_id, e)
