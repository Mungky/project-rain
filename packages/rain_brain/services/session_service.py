"""Service for the Session Registry (cross-AI session state + handoffs)."""

import logging
from uuid import UUID
from datetime import datetime, UTC
from typing import Sequence
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from db.schemas.session_state import SessionState
from rain_brain.services.conversation_service import DEFAULT_USER_ID

logger = logging.getLogger(__name__)


class SessionService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ── Read ──────────────────────────────────────────────────────────────────

    async def get_active_session(self) -> SessionState | None:
        """Return the current active session for the default user."""
        result = await self.db.execute(
            select(SessionState)
            .where(
                SessionState.user_id == DEFAULT_USER_ID,
                SessionState.is_active.is_(True),
            )
            .order_by(SessionState.updated_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def list_sessions(self, limit: int = 20) -> Sequence[SessionState]:
        result = await self.db.execute(
            select(SessionState)
            .where(SessionState.user_id == DEFAULT_USER_ID)
            .order_by(SessionState.updated_at.desc())
            .limit(limit)
        )
        return result.scalars().all()

    async def get_session(self, session_id: UUID) -> SessionState | None:
        result = await self.db.execute(
            select(SessionState).where(
                SessionState.id == session_id,
                SessionState.user_id == DEFAULT_USER_ID,
            )
        )
        return result.scalar_one_or_none()

    # ── Write ─────────────────────────────────────────────────────────────────

    async def handoff(
        self,
        source_ai: str,
        context_summary: str,
        active_task: str | None = None,
        key_decisions: list[dict] | None = None,
        next_steps: list[str] | None = None,
        artifacts: dict | None = None,
        hand_off_to: str | None = None,
        session_key: str | None = None,
        expires_at: datetime | None = None,
    ) -> SessionState:
        """Create or update the active session state for handoff to another AI.

        Deactivates any previous active session before creating the new one.
        """
        # Deactivate all previous active sessions
        await self.db.execute(
            update(SessionState)
            .where(
                SessionState.user_id == DEFAULT_USER_ID,
                SessionState.is_active.is_(True),
            )
            .values(is_active=False, updated_at=datetime.now(UTC))
        )

        _key = session_key or f"{source_ai}-{datetime.now(UTC).strftime('%Y-%m-%d-%H%M')}"

        state = SessionState(
            user_id=DEFAULT_USER_ID,
            session_key=_key,
            source_ai=source_ai,
            context_summary=context_summary,
            active_task=active_task,
            key_decisions=key_decisions or [],
            next_steps=next_steps or [],
            artifacts=artifacts or {},
            hand_off_to=hand_off_to,
            is_active=True,
            expires_at=expires_at,
        )
        self.db.add(state)
        await self.db.commit()
        await self.db.refresh(state)

        logger.info(
            "session_handoff: %s → %s (key=%s)",
            source_ai,
            hand_off_to or "unspecified",
            _key,
        )
        return state

    async def update_session(
        self,
        session_id: UUID,
        context_summary: str | None = None,
        active_task: str | None = None,
        key_decisions: list[dict] | None = None,
        next_steps: list[str] | None = None,
        artifacts: dict | None = None,
        hand_off_to: str | None = None,
        is_active: bool | None = None,
    ) -> SessionState | None:
        state = await self.get_session(session_id)
        if state is None:
            return None

        if context_summary is not None:
            state.context_summary = context_summary
        if active_task is not None:
            state.active_task = active_task
        if key_decisions is not None:
            state.key_decisions = key_decisions
        if next_steps is not None:
            state.next_steps = next_steps
        if artifacts is not None:
            state.artifacts = artifacts
        if hand_off_to is not None:
            state.hand_off_to = hand_off_to
        if is_active is not None:
            state.is_active = is_active
        state.updated_at = datetime.now(UTC)

        await self.db.commit()
        await self.db.refresh(state)
        return state

    async def close_session(self, session_id: UUID) -> bool:
        state = await self.get_session(session_id)
        if state is None:
            return False
        state.is_active = False
        state.updated_at = datetime.now(UTC)
        await self.db.commit()
        return True

    async def delete_session(self, session_id: UUID) -> bool:
        state = await self.get_session(session_id)
        if state is None:
            return False
        await self.db.delete(state)
        await self.db.commit()
        return True

    def format_for_prompt(self, state: SessionState) -> str:
        """Format a SessionState as a system-prompt injection block."""
        lines = [f"SESSION HANDOFF from {state.source_ai}:"]
        lines.append(f"Summary: {state.context_summary}")

        if state.active_task:
            lines.append(f"Active task: {state.active_task}")

        if state.key_decisions:
            lines.append("Key decisions:")
            for d in state.key_decisions[:5]:
                if isinstance(d, dict):
                    lines.append(f"  • {d.get('decision', d)}")
                else:
                    lines.append(f"  • {d}")

        if state.next_steps:
            lines.append("Next steps:")
            for i, step in enumerate(state.next_steps[:5], 1):
                lines.append(f"  {i}. {step}")

        if state.hand_off_to:
            lines.append(f"Intended for: {state.hand_off_to}")

        return "\n".join(lines)
