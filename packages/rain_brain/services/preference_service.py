"""Service layer for user episodic memory (user_preferences.user_context)."""

import json
import logging
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from db.schemas import UserPreference

logger = logging.getLogger(__name__)


class PreferenceService:
    """Reads and writes user episodic memory stored in user_preferences."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def _get_or_create(self, user_id: UUID) -> UserPreference:
        result = await self.db.execute(
            select(UserPreference).where(UserPreference.user_id == user_id)
        )
        pref = result.scalar_one_or_none()
        if pref is None:
            pref = UserPreference(user_id=user_id)
            self.db.add(pref)
            await self.db.flush()
        return pref

    async def update_memory(self, user_id: UUID, key: str, value: str) -> dict:
        """Upsert one key-value pair into the user's episodic memory blob."""
        try:
            pref = await self._get_or_create(user_id)

            raw = pref.user_context or "{}"
            try:
                memory: dict = json.loads(raw)
            except json.JSONDecodeError:
                # Migrate legacy plain-text context into JSON
                memory = {"notes": raw}

            memory[key] = value
            pref.user_context = json.dumps(memory, ensure_ascii=False)

            await self.db.commit()
            logger.info("Episodic memory updated: user=%s key=%s", user_id, key)
            return {"status": "saved", "key": key, "value": value}
        except Exception as e:
            await self.db.rollback()
            logger.error("Failed to update episodic memory: %s", e)
            return {"status": "error", "message": str(e)}

    @staticmethod
    def format_for_prompt(user_context: str | None) -> str:
        """Render user_context as a bullet list for injection into system prompt."""
        if not user_context:
            return ""
        try:
            memory: dict = json.loads(user_context)
            lines = [f"- {k}: {v}" for k, v in memory.items()]
            return "\n".join(lines)
        except json.JSONDecodeError:
            return user_context
